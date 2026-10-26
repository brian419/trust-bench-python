"""Native desktop interface for TrustBench."""

from pathlib import Path
from queue import Empty, Queue
from shlex import join
from subprocess import TimeoutExpired
from sys import platform
from tempfile import TemporaryDirectory
from threading import Lock, Thread
from time import monotonic
from tkinter import BooleanVar, END, Listbox, StringVar, TclError, Tk, WORD
from tkinter.filedialog import askopenfilename
from tkinter.messagebox import askyesno, showerror, showinfo, showwarning
from tkinter.scrolledtext import ScrolledText
from tkinter.ttk import (
    Button,
    Checkbutton,
    Combobox,
    Entry,
    Frame,
    Label,
    LabelFrame,
    Notebook,
    Progressbar,
)
from webbrowser import open as open_browser

from comparison_formatter import generate_comparison_text
from evaluation_launcher import (
    build_live_command,
    run_live_command,
    stop_evaluation_group,
)
from evaluation_progress import EvaluationProgress, ProgressReader
from generate_report import generate_text_report
from ollama_readiness import check_ollama_readiness, OllamaReadiness
from report_browser import list_saved_reports
from report_loader import load_report as load_saved_report
from report_summary import summarize_live_report
from runtime_paths import reports_directory, resource_directory
from spoken_guidance import SpokenGuidance


PROJECT_ROOT = resource_directory()
REPORTS_DIRECTORY = reports_directory(source_root=PROJECT_ROOT)
OLLAMA_DOWNLOAD_URL = "https://ollama.com/download/mac"
KEYBOARD_HINT = (
    "Keyboard: Tab/Shift-Tab moves focus; Down Arrow opens dropdowns; "
    "Enter/Return confirms a choice; Space activates buttons. F1 opens keyboard help."
)


class TrustBenchDesktop:
    """Display saved TrustBench live-evaluation reports."""

    def __init__(self, root: Tk):
        self.root = root
        self.root.title("TrustBench Desktop")
        height = min(800, max(680, self.root.winfo_screenheight() - 120))
        self.root.geometry(f"900x{height}")
        self.root.minsize(760, 680)

        self.report_path = StringVar(value="No report selected")

        self.evaluation_running = False
        self.evaluation_events = Queue()
        self.latest_evaluation_report = None
        self.active_evaluation_process = None
        self.stop_requested = False
        self.shutdown_pending = False
        self.shutdown_unverified = False
        self.close_requested = False
        self.evaluation_finished = False
        self.shutdown_lock = Lock()
        self.shutdown_attempted = False
        self.shutdown_verified = False
        self.readiness_pending = False
        self.readiness_request_id = 0
        self.pending_readiness_command = None
        self.event_poll_scheduled = False
        self.event_poll_id = None
        self.window_closed = False
        self.progress = EvaluationProgress()
        self.narrator = SpokenGuidance()
        self.speech_timer = None
        self.speech_poll_timer = None
        self._last_announced_status = None
        self.root.protocol("WM_DELETE_WINDOW", self.on_window_close)

        self.build_interface()

    def build_interface(self):
        """Create separate report and comparison tabs."""

        frame = Frame(self.root, padding=15)
        frame.pack(fill="both", expand=True)

        title = Label(
            frame,
            text="TrustBench",
            font=("Helvetica", 22, "bold"),
        )
        title.pack(anchor="w")

        subtitle = Label(
            frame,
            text="AI Evaluation and Reliability Testing",
        )
        subtitle.pack(anchor="w", pady=(0, 12))

        accessibility_controls = Frame(frame)
        accessibility_controls.pack(fill="x", pady=(0, 6))
        self.speech_enabled = BooleanVar(value=False)
        self.speech_toggle = Checkbutton(
            accessibility_controls, text="Spoken guidance (off by default)",
            variable=self.speech_enabled, command=self.toggle_spoken_guidance,
            takefocus=True,
        )
        self.speech_toggle.pack(side="left")
        self.speech_toggle.bind("<Return>", lambda event: self._toggle_speech_key())
        self.read_view_button = Button(
            accessibility_controls, text="Read current view",
            command=self.read_current_view, state="disabled",
        )
        self.read_view_button.pack(side="left", padx=(8, 0))
        Button(
            accessibility_controls, text="Keyboard Help", command=self.show_keyboard_help,
        ).pack(side="right")

        # Tabs keep each workflow in its own space.
        self.notebook = Notebook(frame)
        self.notebook.pack(fill="both", expand=True)

        self.reports_tab = Frame(self.notebook, padding=10)
        self.compare_tab = Frame(self.notebook, padding=10)
        self.evaluate_tab = Frame(self.notebook, padding=10)

        self.notebook.add(self.reports_tab, text="Reports")
        self.notebook.add(self.compare_tab, text="Compare")
        self.notebook.add(self.evaluate_tab, text="Evaluate")
        self.notebook.enable_traversal()
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)
        self.notebook.bind("<FocusIn>", lambda event: self._set_keyboard_hint(
            "Keyboard focus: workflow tabs. Use the tab shortcuts below or Control+Tab."
        ))
        modifier = "Command" if platform == "darwin" else "Control"
        Label(
            frame,
            text=f"Tabs: {modifier}+1 Reports; {modifier}+2 Compare; "
            f"{modifier}+3 Evaluate. Control+Tab moves to the next tab.",
            wraplength=680, justify="left",
        ).pack(fill="x", pady=(4, 0))
        for index in range(3):
            self.root.bind(
                f"<{modifier}-Key-{index + 1}>",
                lambda event, tab=index: self._select_tab(tab),
            )
        self.root.bind("<Control-Tab>", lambda event: self._switch_tab(1))
        self.root.bind("<Control-Shift-Tab>", lambda event: self._switch_tab(-1))
        self.root.bind("<F1>", lambda event: self.show_keyboard_help())

        # --------------------
        # Reports tab
        # --------------------

        browser_frame = LabelFrame(
            self.reports_tab,
            text="Saved Evaluation Reports",
            padding=10,
        )
        browser_frame.pack(fill="x", pady=(0, 10))

        Button(
            browser_frame,
            text="Refresh Reports",
            command=self.refresh_reports,
        ).pack(anchor="w", pady=(0, 8))

        self.report_list = Listbox(
            browser_frame,
            height=5,
            exportselection=False,
        )
        self.report_list.pack(fill="x", expand=True)
        Label(
            browser_frame,
            text="Up/Down Arrow chooses and scrolls reports; Enter/Return opens one. "
            "Tab leaves the list, regardless of how many reports it contains.",
            wraplength=680, justify="left",
        ).pack(fill="x", pady=(4, 0))

        self.report_list.bind(
            "<Double-Button-1>",
            self.open_selected_report,
        )

        Button(
            browser_frame,
            text="View Selected Report",
            command=self.open_selected_report,
        ).pack(anchor="w", pady=(8, 0))

        Button(
            self.reports_tab,
            text="Open Evaluation Report",
            command=self.open_report,
        ).pack(anchor="w", pady=(0, 8))

        Label(
            self.reports_tab,
            textvariable=self.report_path,
            wraplength=740,
        ).pack(anchor="w", pady=(0, 8))

        self.report_display = ScrolledText(
            self.reports_tab,
            wrap=WORD,
            font=("Menlo", 12),
            state="disabled",
            height=8,
        )
        self.report_display.pack(fill="both", expand=True)

        # --------------------
        # Compare tab
        # --------------------

        comparison_frame = LabelFrame(
            self.compare_tab,
            text="Compare Evaluation Reports",
            padding=10,
        )
        comparison_frame.pack(fill="x", pady=(0, 10))

        Label(
            comparison_frame,
            text="Previous report:",
        ).pack(anchor="w")

        self.previous_report = Combobox(
            comparison_frame,
            state="readonly",
        )
        self.previous_report.pack(fill="x", pady=(0, 8))

        Label(
            comparison_frame,
            text="Current report:",
        ).pack(anchor="w")

        self.current_report = Combobox(
            comparison_frame,
            state="readonly",
        )
        self.current_report.pack(fill="x", pady=(0, 8))
        Label(
            comparison_frame,
            text="Dropdowns: Down Arrow opens; arrow keys move; Enter/Return selects; "
            "Escape cancels. Space is for activating buttons.",
            wraplength=680, justify="left",
        ).pack(fill="x", pady=(0, 6))

        Button(
            comparison_frame,
            text="Compare Reports",
            command=self.compare_selected_reports,
        ).pack(anchor="w")

        Label(
            self.compare_tab,
            text="Comparison Results",
        ).pack(anchor="w", pady=(0, 8))

        self.comparison_display = ScrolledText(
            self.compare_tab,
            wrap=WORD,
            font=("Menlo", 12),
            state="disabled",
            height=8,
        )

        self.comparison_display.pack(fill="both", expand=True)

        # --------------------
        # Evaluate tab
        # --------------------

        evaluation_frame = LabelFrame(
            self.evaluate_tab,
            text="Live Ollama Evaluation",
            padding=10,
        )
        evaluation_frame.pack(fill="x", pady=(0, 10))

        Label(
            evaluation_frame,
            text="Dataset:",
        ).pack(anchor="w")

        self.dataset_path = StringVar(
            value=str(PROJECT_ROOT / "eval-read-live.json")
        )

        dataset_controls = Frame(evaluation_frame)
        dataset_controls.pack(fill="x", pady=(0, 10))
        self.dataset_entry = Entry(
            dataset_controls,
            textvariable=self.dataset_path,
        )
        self.dataset_entry.pack(side="left", fill="x", expand=True)

        Button(
            dataset_controls,
            text="Browse Dataset",
            command=self.browse_dataset,
        ).pack(side="left", padx=(8, 0))

        Label(
            evaluation_frame,
            text="Ollama model (Down Arrow opens choices; Enter/Return selects):",
        ).pack(anchor="w")

        self.model_name = StringVar(value="gemma3:1b")

        model_controls = Frame(evaluation_frame)
        model_controls.pack(fill="x", pady=(0, 10))
        self.model_selector = Combobox(
            model_controls,
            textvariable=self.model_name,
            state="normal",
        )
        self.model_selector.pack(side="left", fill="x", expand=True)
        self.refresh_models_button = Button(
            model_controls,
            text="Refresh Models",
            command=self.check_ollama,
        )
        self.refresh_models_button.pack(side="left", padx=(8, 0))

        readiness_controls = Frame(evaluation_frame)
        readiness_controls.pack(fill="x", pady=(0, 6))
        self.check_ollama_button = Button(
            readiness_controls,
            text="Check Ollama",
            command=self.check_ollama,
        )
        self.check_ollama_button.pack(side="left")
        Button(
            readiness_controls,
            text="Setup Help",
            command=self.show_ollama_setup,
        ).pack(side="left", padx=(8, 0))
        Button(
            readiness_controls,
            text="Get Ollama (website)",
            command=self.open_ollama_download,
        ).pack(side="left", padx=(8, 0))
        self.ollama_status = StringVar(
            value="Choose Refresh Models to list models from Ollama on this computer. "
            "You can also type a model name."
        )
        Label(
            evaluation_frame,
            textvariable=self.ollama_status,
            wraplength=680,
            justify="left",
        ).pack(fill="x", pady=(0, 8))

        Label(
            evaluation_frame,
            text=f"Official Ollama download: {OLLAMA_DOWNLOAD_URL}",
            wraplength=680,
            justify="left",
        ).pack(fill="x", pady=(0, 8))

        actions = Frame(evaluation_frame)
        actions.pack(fill="x")
        Button(
            actions,
            text="Preview Command",
            command=self.preview_evaluation,
        ).pack(side="left")

        self.start_button = Button(
            actions,
            text="Start Evaluation",
            command=self.check_and_start_evaluation,
        )
        self.start_button.pack(side="left", padx=(8, 0))

        self.stop_button = Button(
            actions,
            text="Stop Evaluation",
            command=self.stop_evaluation,
            state="disabled",
        )
        self.stop_button.pack(side="left", padx=(8, 0))

        self.progress_status = StringVar(value=self.progress.status)
        self.progress_counts = StringVar(value=self.progress.count_text())
        self.progress_elapsed = StringVar(value=self.progress.elapsed_text())
        progress_frame = Frame(self.evaluate_tab)
        progress_frame.pack(fill="x", pady=(0, 8))
        Label(
            progress_frame, textvariable=self.progress_status,
            wraplength=680, justify="left",
        ).pack(anchor="w")
        self.progress_bar = Progressbar(progress_frame, mode="determinate", maximum=1)
        self.progress_bar.pack(fill="x", pady=(4, 4))
        details = Frame(progress_frame)
        details.pack(fill="x")
        Label(details, textvariable=self.progress_counts).pack(side="left")
        Label(details, textvariable=self.progress_elapsed).pack(side="right")

        Label(
            self.evaluate_tab,
            text="Evaluation Output",
        ).pack(anchor="w", pady=(0, 8))

        self.evaluation_display = ScrolledText(
            self.evaluate_tab,
            wrap=WORD,
            font=("Menlo", 12),
            state="disabled",
            height=8,
        )
        self.evaluation_display.pack(fill="both", expand=True)
        for display in (
            self.report_display, self.comparison_display, self.evaluation_display,
        ):
            display.bind("<Tab>", self._focus_next)
            display.bind("<Shift-Tab>", self._focus_previous)
            display.bind("<Control-Tab>", lambda event: self._switch_tab(1))
            display.bind("<Control-Shift-Tab>", lambda event: self._switch_tab(-1))

        self.keyboard_hint = StringVar(value=KEYBOARD_HINT)
        Label(
            frame, textvariable=self.keyboard_hint, wraplength=680, justify="left",
        ).pack(fill="x", pady=(6, 0))
        self._configure_button_keys(frame)
        for widget, name in (
            (self.previous_report, "Previous report"),
            (self.current_report, "Current report"),
            (self.model_selector, "Ollama model"),
        ):
            widget.configure(takefocus=True)
            widget.bind("<Return>", self._open_dropdown)
            widget.bind("<KP_Enter>", self._open_dropdown)
            widget.bind("<space>", self._dropdown_space)
            widget.bind("<FocusIn>", lambda event, label=name: self._set_keyboard_hint(
                f"Keyboard focus: {label}. Down Arrow or Enter/Return opens choices; "
                "Up/Down Arrow moves through choices; Enter/Return confirms; Escape closes."
            ))
            widget.bind("<FocusOut>", self._clear_keyboard_hint)
            widget.bind("<<ComboboxSelected>>", lambda event, label=name: self._announce(
                f"{label}: {event.widget.get()}"
            ))
        for widget, name in (
            (self.dataset_entry, "Dataset path"),
            (self.report_display, "Report text"),
            (self.comparison_display, "Comparison results"),
            (self.evaluation_display, "Evaluation Output"),
        ):
            widget.configure(takefocus=True)
            widget.bind("<FocusIn>", lambda event, label=name: self._set_keyboard_hint(
                f"Keyboard focus: {label}. Tab/Shift-Tab moves to another control."
            ))
            widget.bind("<FocusOut>", self._clear_keyboard_hint)
        self.report_list.bind("<Return>", self.open_selected_report)
        self.report_list.bind("<KP_Enter>", self.open_selected_report)
        self.report_list.configure(takefocus=True)
        self.report_list.bind("<FocusIn>", lambda event: self._set_keyboard_hint(
            "Keyboard focus: Saved reports. Up/Down Arrow chooses a report and scrolls "
            "the list; Enter/Return opens it. Tab moves to the next control, not the next report."
        ))
        self.report_list.bind("<FocusOut>", self._clear_keyboard_hint)
        self.report_list.bind("<<ListboxSelect>>", self._announce_report_selection)
        self.speech_toggle.bind("<FocusIn>", lambda event: self._set_keyboard_hint(
            "Keyboard focus: Spoken guidance. Space or Enter/Return toggles speech on or off."
        ))
        self.speech_toggle.bind("<KP_Enter>", lambda event: self._toggle_speech_key())
        self.speech_toggle.bind("<FocusOut>", self._clear_keyboard_hint)
        self.progress_bar.configure(takefocus=False)
        self.refresh_reports()

    def _configure_button_keys(self, parent):
        """Use explicit traversal/activation instead of platform-dependent defaults."""
        for widget in parent.winfo_children():
            kind = widget.winfo_class()
            if kind == "TButton":
                widget.configure(takefocus=lambda widget_path=None, button=widget: (
                    not button.instate(["disabled"]) and bool(button.winfo_viewable())
                ))
                widget.bind("<FocusIn>", self._button_focus_in)
                widget.bind("<FocusOut>", self._button_focus_out)
                # Consume both halves so the class binding cannot invoke twice.
                for key in ("space", "Return", "KP_Enter"):
                    widget.bind(f"<KeyPress-{key}>", self._press_button)
                    widget.bind(f"<KeyRelease-{key}>", self._activate_button)
            elif kind in ("Scrollbar", "TScrollbar"):
                widget.configure(takefocus=False)
            self._configure_button_keys(widget)

    def _button_focus_in(self, event):
        event.widget.configure(default="active")
        self._set_keyboard_hint(
            f"Keyboard focus: {event.widget.cget('text')}. "
            "Press Space or Enter/Return to activate."
        )

    def _button_focus_out(self, event):
        self._keyboard_pressed_button = None
        event.widget.configure(default="normal")
        self._clear_keyboard_hint(event)

    def _clear_keyboard_hint(self, event):
        self.keyboard_hint.set(KEYBOARD_HINT)

    def _set_keyboard_hint(self, text):
        self.keyboard_hint.set(text)
        self._announce(text)

    def _press_button(self, event):
        self._keyboard_pressed_button = (event.widget, event.keysym)
        return "break"

    def _activate_button(self, event):
        pressed = getattr(self, "_keyboard_pressed_button", None)
        self._keyboard_pressed_button = None
        if pressed == (event.widget, event.keysym) and not event.widget.instate(["disabled"]):
            event.widget.invoke()
        return "break"

    def _open_dropdown(self, event):
        if not event.widget.instate(["disabled"]):
            # Forward to Tk's public Down-key binding, including Aqua popdowns.
            event.widget.event_generate("<Down>")
        return "break"

    def _dropdown_space(self, event):
        if event.widget.instate(["readonly"]):
            return self._open_dropdown(event)
        return None  # Keep ordinary editing in the model-name entry.

    def _focus_next(self, event):
        event.widget.tk_focusNext().focus_set()
        return "break"

    def _focus_previous(self, event):
        event.widget.tk_focusPrev().focus_set()
        return "break"

    def _switch_tab(self, direction):
        current = self.notebook.index("current")
        count = self.notebook.index("end")
        return self._select_tab((current + direction) % count)

    def _select_tab(self, index):
        self.notebook.select(index)
        self._queue_tab_focus(index)
        return "break"

    def _on_tab_changed(self, event):
        self._queue_tab_focus(self.notebook.index("current"))

    def _queue_tab_focus(self, index):
        generation = getattr(self, "_tab_focus_generation", 0) + 1
        self._tab_focus_generation = generation
        self.root.after_idle(lambda: self._focus_tab_entry(index, generation))

    def _focus_tab_entry(self, index, generation):
        if self.window_closed or generation != self._tab_focus_generation:
            return
        if self.notebook.index("current") != index:
            return
        target = (self.report_list, self.previous_report, self.dataset_entry)[index]
        target.focus_set()

    def _dialog(self, callback, *args, **kwargs):
        """Parent every native dialog and restore a usable application focus."""
        root = getattr(self, "root", None)
        try:
            origin = root.focus_get() if root is not None else None
        except (KeyError, TclError):
            origin = None
        if root is not None:
            kwargs["parent"] = root
        if args:
            self._announce(". ".join(str(value) for value in args[:2]), immediate=True)
        try:
            return callback(*args, **kwargs)
        finally:
            if root is not None and not getattr(self, "window_closed", False):
                try:
                    root.focus_set()
                    usable = origin is not None and origin.winfo_exists() and origin.winfo_viewable()
                    if usable and origin.winfo_class() in ("TButton", "TCombobox", "TEntry"):
                        usable = not origin.instate(["disabled"])
                    if usable:
                        origin.focus_set()
                    elif hasattr(self, "notebook"):
                        index = self.notebook.index("current")
                        (self.report_list, self.previous_report, self.dataset_entry)[index].focus_set()
                except TclError:
                    pass

    def show_keyboard_help(self):
        modifier = "Command" if platform == "darwin" else "Control"
        self._dialog(
            showinfo, "Keyboard Help",
            f"Jump directly to tabs: {modifier}+1 Reports, {modifier}+2 Compare, "
            f"{modifier}+3 Evaluate. Control+Tab goes forward; Control+Shift+Tab goes back.\n\n"
            "Tab/Shift+Tab moves between controls. In Saved reports, Up/Down Arrow "
            "chooses and scrolls reports; Enter/Return opens the selected report. "
            "The list is one Tab stop, regardless of how many reports it contains.\n\n"
            "Dropdowns: Down Arrow or Enter/Return opens choices. Up/Down Arrow moves "
            "between choices; Enter/Return confirms; Escape cancels. Space may open "
            "readonly report choices, but Enter/Return confirms the choice.\n\n"
            "Buttons: Space or Enter/Return activates the focused button. The hint "
            "below the tabs names the focused control.\n\n"
            "Spoken guidance is optional and off at startup. Enable its checkbox "
            "for local macOS speech of hints, selections, dialogs and evaluation status. "
            "Read current view reads an excerpt of the displayed text. It does not "
            "require enabling system VoiceOver and does not replace a screen reader.",
        )
        return "break"

    def _toggle_speech_key(self):
        self.speech_enabled.set(not self.speech_enabled.get())
        self.toggle_spoken_guidance()
        return "break"

    def toggle_spoken_guidance(self):
        enabled = bool(self.speech_enabled.get())
        self._cancel_speech_callbacks()
        if not self.narrator.set_enabled(enabled):
            self.speech_enabled.set(False)
            self.read_view_button.configure(state="disabled")
            self._dialog(showinfo, "Spoken Guidance Unavailable",
                         "Local macOS speech is unavailable. Keyboard navigation still works.")
            return
        self.read_view_button.configure(state="normal" if enabled else "disabled")
        if enabled:
            self._announce("Spoken guidance on. " + KEYBOARD_HINT)
            self._poll_speech()

    def _announce(self, text, immediate=False):
        narrator = getattr(self, "narrator", None)
        if narrator is None or not narrator.enabled or getattr(self, "window_closed", False):
            return
        if self.speech_timer is not None:
            self.root.after_cancel(self.speech_timer)
            self.speech_timer = None
        if immediate:
            narrator.speak(text)
        else:
            self.speech_timer = self.root.after(250, lambda: self._deliver_speech(text))

    def _deliver_speech(self, text):
        self.speech_timer = None
        if not self.window_closed:
            self.narrator.speak(text)

    def _poll_speech(self):
        self.speech_poll_timer = None
        if self.window_closed:
            return
        if self.narrator.failed:
            self.narrator.stop()
            self.speech_enabled.set(False)
            self.read_view_button.configure(state="disabled")
            self._cancel_speech_callbacks()
            self.keyboard_hint.set("Spoken guidance could not run and was turned off. Keyboard navigation still works.")
        elif self.narrator.enabled:
            self.speech_poll_timer = self.root.after(500, self._poll_speech)

    def _cancel_speech_callbacks(self):
        for name in ("speech_timer", "speech_poll_timer"):
            timer = getattr(self, name, None)
            if timer is not None:
                self.root.after_cancel(timer)
            setattr(self, name, None)

    def _close_accessibility(self):
        self._cancel_speech_callbacks()
        narrator = getattr(self, "narrator", None)
        if narrator is not None:
            narrator.close()

    def _announce_report_selection(self, event):
        selection = self.report_list.curselection()
        if selection:
            self._announce("Selected report: " + Path(self.saved_reports[selection[0]]).name)

    def read_current_view(self):
        index = self.notebook.index("current")
        display = (self.report_display, self.comparison_display, self.evaluation_display)[index]
        text = display.get("1.0", END).strip()
        if len(text) > 3600:
            text = text[:3600] + ". End of excerpt. More text is available in the view."
        self._announce(text or "No text is displayed in this view.", immediate=True)

    def _render_progress(self):
        """Update persistent text and case counts without inferring model health."""
        self.progress.tick(monotonic())
        self.progress_status.set(self.progress.status)
        self.progress_counts.set(self.progress.count_text())
        self.progress_elapsed.set(self.progress.elapsed_text())
        self.progress_bar.configure(
            maximum=max(1, self.progress.total or 0), value=self.progress.completed,
        )
        if self.progress.status != getattr(self, "_last_announced_status", None):
            self._last_announced_status = self.progress.status
            self._announce(self.progress.status + ". " + self.progress.count_text())

    def browse_dataset(self):
        """Select a JSON dataset for live evaluation."""

        filename = self._dialog(askopenfilename,
            title="Select Evaluation Dataset",
            initialdir=str(PROJECT_ROOT),
            filetypes=[
                ("JSON datasets", "*.json"),
                ("All files", "*.*"),
            ],
        )

        if filename:
            self.dataset_path.set(filename)

    def preview_evaluation(self):
        """Validate inputs and display the evaluation command."""

        try:
            command = build_live_command(
                self.dataset_path.get(),
                self.model_name.get(),
            )
        except ValueError as error:
            self._dialog(showerror,
                "Invalid Evaluation Settings",
                str(error),
            )
            return False

        output = join(command)

        self.evaluation_display.configure(state="normal")
        self.evaluation_display.delete("1.0", END)
        self.evaluation_display.insert(END, output)
        self.evaluation_display.configure(state="disabled")
        self.evaluation_display.see("1.0")

        return True

    def open_ollama_download(self):
        """Open the official download page only when the user requests it."""
        if not self._dialog(askyesno,
            "Open Ollama Website?",
            "Open the official Ollama download page in your browser?\n\n"
            f"{OLLAMA_DOWNLOAD_URL}\n\n"
            "Ollama is separate software maintained by the Ollama project. "
            "On its website, choose Download manually for the macOS installer. "
            "TrustBench will not run an installer or a shell command.",
            parent=self.root,
        ):
            return False
        try:
            opened = open_browser(OLLAMA_DOWNLOAD_URL)
        except OSError:
            opened = False
        if not opened:
            self._dialog(showerror,
                "Browser Could Not Open",
                f"Open this address in your browser: {OLLAMA_DOWNLOAD_URL}",
                parent=self.root,
            )
        return opened

    def show_ollama_setup(self):
        """Explain separate setup without installing software or models."""
        self._dialog(showinfo,
            "Ollama Setup",
            "1. Use Get Ollama (website) to open the official download page:\n"
            f"{OLLAMA_DOWNLOAD_URL}\n"
            "Choose Download manually for the macOS installer, then install and open it.\n"
            "2. Choose a local model in Ollama and download it if needed.\n"
            "3. In TrustBench, choose Refresh Models and select a model from the "
            "dropdown. You can also type a model name.\n"
            "4. Choose Start Evaluation.\n\n"
            "You can also download a model in Terminal: ollama pull gemma3:1b\n"
            "Model downloads need internet and disk space. TrustBench does not "
            "install Ollama or download models automatically.\n\n"
            "Reports and Compare work without Ollama.\n\n"
            + self.ollama_status.get(),
        )

    def check_ollama(self):
        """Check readiness without starting an evaluation."""
        return self._begin_ollama_check()

    def check_and_start_evaluation(self):
        """Validate settings and require a fresh readiness check for a UI start."""
        if self._evaluation_controls_busy():
            return False
        try:
            command = build_live_command(self.dataset_path.get(), self.model_name.get())
        except ValueError as error:
            self._dialog(showerror, "Invalid Evaluation Settings", str(error))
            return False
        return self._begin_ollama_check(command)

    def _evaluation_controls_busy(self):
        return (
            self.evaluation_running or self.shutdown_pending or self.shutdown_unverified
            or self.close_requested or self.readiness_pending or self.window_closed
        )

    def _begin_ollama_check(self, command=None):
        if self._evaluation_controls_busy():
            return False
        model = self.model_name.get().strip()
        self.readiness_request_id += 1
        request_id = self.readiness_request_id
        self.readiness_pending = True
        self.pending_readiness_command = command
        self.start_button.configure(state="disabled")
        self.check_ollama_button.configure(state="disabled")
        self.refresh_models_button.configure(state="disabled")
        self.ollama_status.set("Checking Ollama and the selected model...")
        worker = Thread(
            target=self._check_ollama_worker, args=(request_id, model), daemon=True,
        )
        try:
            worker.start()
        except RuntimeError:
            self.readiness_pending = False
            self.pending_readiness_command = None
            self.start_button.configure(state="normal")
            self.check_ollama_button.configure(state="normal")
            self.refresh_models_button.configure(state="normal")
            self.ollama_status.set(
                "Could not start the Ollama check. Please try again."
            )
            return False
        self._schedule_event_poll()
        return True

    def _check_ollama_worker(self, request_id, model):
        """Only enqueue data here; every Tkinter operation stays on its thread."""
        try:
            result = (
                check_ollama_readiness(model) if model
                else check_ollama_readiness(model, allow_empty=True)
            )
        except Exception:
            result = OllamaReadiness(
                "CHECK_FAILED", model, "Could not verify Ollama. Please check again.",
            )
        self.evaluation_events.put(("readiness", (request_id, model, result)))

    def _handle_ollama_result(self, request_id, model, result):
        if (
            request_id != self.readiness_request_id
            or self.window_closed
            or not self.readiness_pending
        ):
            return
        command = self.pending_readiness_command
        self.pending_readiness_command = None
        self.readiness_pending = False
        self.start_button.configure(state="normal")
        self.check_ollama_button.configure(state="normal")
        self.refresh_models_button.configure(state="normal")
        if self.close_requested:
            return
        self.model_selector.configure(values=result.models or ())
        if model != self.model_name.get().strip():
            self.ollama_status.set("The model changed. Choose Check Ollama again.")
            return
        self.ollama_status.set(result.message)
        self._announce(result.message)
        if command is not None and result.status == "READY":
            try:
                current = build_live_command(
                    self.dataset_path.get(), self.model_name.get()
                )
            except ValueError:
                current = None
            if current != command:
                self.ollama_status.set(
                    "Evaluation settings changed. Choose Start Evaluation again."
                )
                return
            self.start_evaluation()

    def _schedule_event_poll(self):
        if not self.event_poll_scheduled and not self.window_closed:
            self.event_poll_scheduled = True
            self.event_poll_id = self.root.after(100, self._drain_evaluation_events)

    def _cancel_event_poll(self):
        if self.event_poll_scheduled and self.event_poll_id is not None:
            self.root.after_cancel(self.event_poll_id)
        self.event_poll_scheduled = False
        self.event_poll_id = None

    def start_evaluation(self):
        """Start a live evaluation while keeping the GUI responsive."""

        if (
            self.evaluation_running
            or self.shutdown_pending
            or self.shutdown_unverified
            or self.close_requested
            or self.readiness_pending
            or self.window_closed
        ):
            return False

        try:
            command = build_live_command(
                self.dataset_path.get(),
                self.model_name.get(),
            )
        except ValueError as error:
            self._dialog(showerror,
                "Invalid Evaluation Settings",
                str(error),
            )
            return False

        self.evaluation_running = True
        self.progress.start(monotonic())
        self._render_progress()
        self.latest_evaluation_report = None
        self.active_evaluation_process = None
        self.stop_requested = False
        self.evaluation_finished = False
        self.shutdown_attempted = False
        self.shutdown_verified = False

        self.start_button.configure(state="disabled")
        self.check_ollama_button.configure(state="disabled")
        self.refresh_models_button.configure(state="disabled")
        self.stop_button.configure(state="normal")

        self.evaluation_display.configure(state="normal")
        self.evaluation_display.delete("1.0", END)
        self.evaluation_display.insert(
            END,
            "Starting live evaluation...\n",
        )
        self.evaluation_display.configure(state="disabled")

        worker = Thread(
            target=self._run_evaluation_worker,
            args=(command,),
            daemon=True,
        )
        try:
            worker.start()
        except RuntimeError as error:
            self.evaluation_events.put(("error", str(error)))

        self._schedule_event_poll()
        return True

    def on_window_close(self):
        """Close safely, stopping an active evaluation first."""

        if self.shutdown_unverified:
            self._dialog(showwarning,
                "Shutdown Not Verified",
                "The previous evaluation may still be running. "
                "The window will remain open.",
            )
            return

        if self.evaluation_running or self.shutdown_pending:
            self.close_requested = True

            if self.evaluation_running and not self.stop_requested:
                self.stop_evaluation()

            return

        self.readiness_request_id += 1
        self.readiness_pending = False
        self.pending_readiness_command = None
        self.window_closed = True
        self._cancel_event_poll()
        self._close_accessibility()
        self.root.destroy()

    def _finish_window_close(self):
        """Close after evaluation and shutdown workers finish."""

        if not self.close_requested:
            return

        if self.shutdown_unverified:
            self.close_requested = False
            self._dialog(showwarning,
                "Shutdown Not Verified",
                "Evaluation shutdown could not be verified. "
                "The window will remain open.",
            )
            return

        if self.evaluation_running or self.shutdown_pending:
            return

        self.close_requested = False
        self.window_closed = True
        self._cancel_event_poll()
        self._close_accessibility()
        self.root.destroy()

    def stop_evaluation(self):
        """Request cancellation without blocking Tkinter."""

        if (
            not self.evaluation_running
            or self.stop_requested
            or self.evaluation_finished
        ):
            return False

        self.stop_requested = True
        self.progress.request_stop()
        self._render_progress()
        self.stop_button.configure(state="disabled")

        self.evaluation_display.configure(state="normal")
        self.evaluation_display.insert(
            END,
            "\nStop requested. Ending evaluation...\n",
        )
        self.evaluation_display.configure(state="disabled")
        self.evaluation_display.see(END)

        if self.active_evaluation_process is not None:
            self._begin_evaluation_shutdown(self.active_evaluation_process)

        return True

    def _begin_evaluation_shutdown(self, process):
        """Start bounded process-group shutdown in a worker thread."""

        if self.shutdown_pending:
            return

        self.shutdown_pending = True

        worker = Thread(
            target=self._shutdown_evaluation_worker,
            args=(process,),
            daemon=True,
        )
        worker.start()

    def _stop_process_once(self, process):
        """Attempt process-group shutdown at most once per evaluation."""

        with self.shutdown_lock:
            if self.shutdown_attempted:
                return self.shutdown_verified

            self.shutdown_attempted = True

            try:
                verified = stop_evaluation_group(process)
            except OSError as error:
                self.shutdown_verified = False
                self.evaluation_events.put(("shutdown_error", str(error)))
                return False

            self.shutdown_verified = verified
            self.evaluation_events.put(("shutdown_complete", verified))
            return verified

    def _shutdown_evaluation_worker(self, process):
        """Request shutdown without blocking Tkinter."""

        self._stop_process_once(process)

    def _run_evaluation_worker(self, command: list[str]):
        """Run the subprocess and place its output into a queue."""

        process = None
        progress_directory = None

        try:
            progress_directory = TemporaryDirectory(prefix="trustbench-progress-")
            progress_file = Path(progress_directory.name) / "events.jsonl"
            progress_file.touch()
            reader = ProgressReader(progress_file)
            process = run_live_command(command, progress_file=progress_file)
            self.evaluation_events.put(("process", process))

            if process.stdout is not None:
                for line in process.stdout:
                    for event in reader.read():
                        self.evaluation_events.put(("progress", event))
                    self.evaluation_events.put(("output", line))

                    if line.startswith("Report saved to: "):
                        report_path = line.removeprefix("Report saved to: ").strip()
                        self.evaluation_events.put(("report_path", report_path))

            return_code = process.wait()
            for event in reader.read():
                self.evaluation_events.put(("progress", event))
            self.evaluation_finished = True
            self.evaluation_events.put(("done", return_code))

        except (OSError, UnicodeError) as error:
            if process is not None:
                verified = self._stop_process_once(process)

                if verified:
                    try:
                        process.wait(timeout=1.0)
                    except (OSError, TimeoutExpired) as shutdown_error:
                        self.evaluation_events.put(
                            ("shutdown_error", str(shutdown_error))
                        )

            self.evaluation_events.put(("error", str(error)))
        finally:
            if progress_directory is not None:
                try:
                    progress_directory.cleanup()
                except OSError:
                    pass

    def _evaluation_completion_message(self, return_code: int) -> str:
        """Describe process completion and recorded evaluation outcomes."""

        if return_code != 0:
            return f"\nEvaluation process exited with code {return_code}.\n"

        if not self.latest_evaluation_report:
            return (
                "\nEvaluation process finished, but no saved report "
                "was identified. Results could not be verified.\n"
            )

        try:
            path = Path(self.latest_evaluation_report)

            if not path.is_absolute():
                path = PROJECT_ROOT / path

            report = load_saved_report(str(path))
            summary = summarize_live_report(report)

        except (OSError, ValueError) as error:
            return (
                "\nEvaluation process finished, but its report "
                f"could not be verified: {error}\n"
            )

        passed = summary["passed"]
        failed = summary["failed"]
        errors = summary["errors"]

        if errors:
            status = "Completed with request errors"
        else:
            status = "Completed without request errors"

        return (
            f"\n{status}.\n"
            f"Passed: {passed}\n"
            f"Failed: {failed}\n"
            f"Request errors: {errors}\n"
        )

    def _drain_evaluation_events(self):
        """Process queued events safely on Tkinter's main thread."""

        self.event_poll_scheduled = False
        self.event_poll_id = None
        if self.window_closed:
            return

        while True:
            try:
                event_type, value = self.evaluation_events.get_nowait()
            except Empty:
                break

            if event_type == "readiness":
                self._handle_ollama_result(*value)

            elif event_type == "process":
                self.active_evaluation_process = value
                if self.progress.total is None and not self.stop_requested:
                    self.progress.status = "Evaluation running; waiting for progress details"

                if self.stop_requested and not self.evaluation_finished:
                    self._begin_evaluation_shutdown(value)

            elif event_type == "progress":
                self.progress.apply(value)

            elif event_type == "output":
                self.evaluation_display.configure(state="normal")
                self.evaluation_display.insert(END, value)
                self.evaluation_display.configure(state="disabled")
                self.evaluation_display.see(END)

            elif event_type == "report_path":
                self.latest_evaluation_report = value

            elif event_type == "shutdown_complete":
                self.shutdown_pending = False
                self.shutdown_unverified = not value

                if not value:
                    self.evaluation_display.configure(state="normal")
                    self.evaluation_display.insert(
                        END,
                        "\nShutdown could not be verified. "
                        "The evaluation process group may still be running. "
                        "Starting another evaluation is disabled.\n",
                    )
                    self.evaluation_display.configure(state="disabled")

                if not self.evaluation_running:
                    self.start_button.configure(
                        state=("disabled" if self.shutdown_unverified else "normal")
                    )

            elif event_type == "shutdown_error":
                self.shutdown_pending = False
                self.shutdown_unverified = True

                self.evaluation_display.configure(state="normal")
                self.evaluation_display.insert(
                    END,
                    f"\nShutdown signaling error: {value}\n",
                )
                self.evaluation_display.configure(state="disabled")

                self.start_button.configure(state="disabled")

            elif event_type == "done":
                self.evaluation_running = False
                self.active_evaluation_process = None
                self.start_button.configure(
                    state=(
                        "disabled"
                        if self.shutdown_pending or self.shutdown_unverified
                        else "normal"
                    )
                )
                self.stop_button.configure(state="disabled")

                if self.stop_requested:
                    message = (
                        "\nStop was requested. "
                        f"Evaluation process exited with code {value}.\n"
                    )
                else:
                    message = self._evaluation_completion_message(value)

                self.evaluation_display.configure(state="normal")
                self.evaluation_display.insert(END, message)
                self.evaluation_display.configure(state="disabled")

                if value == 0:
                    self.refresh_reports()
                self.progress.finish(message.strip().splitlines()[0], monotonic())

            elif event_type == "error":
                self.evaluation_running = False
                self.active_evaluation_process = None
                self.start_button.configure(
                    state=(
                        "disabled"
                        if self.shutdown_pending or self.shutdown_unverified
                        else "normal"
                    )
                )
                self.stop_button.configure(state="disabled")

                self.evaluation_display.configure(state="normal")
                self.evaluation_display.insert(
                    END,
                    f"\nEvaluation startup/read error: {value}\n",
                )
                self.evaluation_display.configure(state="disabled")
                self.progress.finish("Evaluation failed; see Evaluation Output", monotonic())

        if not self.window_closed:
            if self.shutdown_unverified:
                self.progress.status = "Shutdown not verified; evaluation may still be running"
            elif self.shutdown_pending:
                self.progress.status = "Stopping evaluation; waiting for process cleanup"
            elif self.stop_requested and not self.evaluation_running:
                self.progress.status = "Evaluation stopped"
            self._render_progress()
        self._finish_window_close()

        if not self.window_closed:
            self.check_ollama_button.configure(
                state=("disabled" if self._evaluation_controls_busy() else "normal")
            )
            self.refresh_models_button.configure(
                state=("disabled" if self._evaluation_controls_busy() else "normal")
            )
        if self.evaluation_running or self.shutdown_pending or self.readiness_pending:
            self._schedule_event_poll()

    def refresh_reports(self):
        """Refresh the list of saved evaluation reports."""

        try:
            reports = list_saved_reports(str(REPORTS_DIRECTORY))
        except (OSError, ValueError) as error:
            self._dialog(showerror,
                "Unable to List Reports",
                str(error),
            )
            return False

        self.saved_reports = reports

        self.report_list.delete(0, END)

        report_names = [Path(path).name for path in reports]

        self.previous_report["values"] = report_names
        self.current_report["values"] = report_names

        self.previous_report.set("")
        self.current_report.set("")

        for path in reports:
            self.report_list.insert(
                END,
                Path(path).name,
            )

        return True

    def open_selected_report(self, event=None):
        """Display the currently selected saved report."""

        selection = self.report_list.curselection()

        if not selection:
            return False

        index = selection[0]
        filename = self.saved_reports[index]

        return self.load_report(filename)

    def compare_selected_reports(self):
        """Compare two selected saved evaluation reports."""

        previous_index = self.previous_report.current()
        current_index = self.current_report.current()

        if previous_index < 0 or current_index < 0:
            self._dialog(showwarning,
                "Select Two Reports",
                "Choose a previous and current report first.",
            )
            return False

        if previous_index == current_index:
            self._dialog(showwarning,
                "Select Two Reports",
                "Choose two different reports to compare.",
            )
            return False

        previous_path = self.saved_reports[previous_index]
        current_path = self.saved_reports[current_index]

        try:
            output = generate_comparison_text(
                previous_path,
                current_path,
            )
        except (OSError, ValueError) as error:
            self._dialog(showerror,
                "Unable to Compare Reports",
                str(error),
            )
            return False

        self.comparison_display.configure(state="normal")
        self.comparison_display.delete("1.0", END)
        self.comparison_display.insert(END, output)
        self.comparison_display.configure(state="disabled")
        self.comparison_display.see("1.0")

        return True

    def open_report(self):
        """Ask the user to select a JSON evaluation report."""

        filename = self._dialog(askopenfilename,
            title="Select TrustBench Evaluation Report",
            filetypes=[
                ("JSON reports", "*.json"),
                ("All files", "*.*"),
            ],
        )

        if not filename:
            return

        self.load_report(filename)

    def load_report(self, filename: str):
        """Load a report and update the display if successful."""

        try:
            output = generate_text_report(filename)
        except (OSError, ValueError) as error:
            self._dialog(showerror,
                "Unable to Open Report",
                str(error),
            )
            return False

        self.report_path.set(filename)

        self.report_display.configure(state="normal")
        self.report_display.delete("1.0", END)
        self.report_display.insert(END, output)
        self.report_display.configure(state="disabled")
        self.report_display.see("1.0")

        return True


def main():
    root = Tk()
    TrustBenchDesktop(root)
    root.mainloop()


if __name__ == "__main__":
    main()

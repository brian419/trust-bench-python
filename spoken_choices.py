"""An app-owned chooser exposes highlighted options to optional speech."""

from tkinter import END, Listbox, TclError, Toplevel
from tkinter.ttk import Frame, Label, Scrollbar


class SpokenChoices:
    """Browse without committing; announce highlights rather than guessing native menus."""

    def __init__(self, root, combo, label, announce, on_close, *, describe=None):
        self.combo = combo
        self.announce = announce
        self.on_close = on_close
        self.describe = describe
        self.values = tuple(combo.cget("values"))
        self.closed = False
        self.last_highlight = None
        self.focus_timer = None
        self.pointer_pressed = False
        self.window = Toplevel(root)
        self.window.withdraw()
        self.window.title(f"Choose {label}")
        self.window.transient(root)
        self.window.protocol("WM_DELETE_WINDOW", self.cancel)
        body = Frame(self.window, padding=8)
        body.pack(fill="both", expand=True)
        Label(body, text=f"Choose {label}").pack(anchor="w")
        Label(
            body,
            text="Arrow keys browse; Enter/Return or Space chooses; Escape cancels.",
            wraplength=520,
            justify="left",
        ).pack(fill="x", pady=(4, 6))
        choices = Frame(body)
        choices.pack(fill="both", expand=True)
        self.listbox = Listbox(choices, exportselection=False, height=8, takefocus=True)
        scrollbar = Scrollbar(
            choices, orient="vertical", command=self.listbox.yview, takefocus=False
        )
        self.listbox.configure(yscrollcommand=scrollbar.set)
        self.listbox.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        for value in self.values:
            self.listbox.insert(END, value)
        index = combo.current()
        if self.values:
            index = index if 0 <= index < len(self.values) else 0
            self.listbox.selection_set(index)
            self.listbox.activate(index)
            self.listbox.see(index)
        self.listbox.bind("<<ListboxSelect>>", self.highlight)
        self.listbox.bind("<Motion>", self.pointer_highlight)
        self.listbox.bind("<ButtonPress-1>", self._pointer_press)
        self.listbox.bind("<ButtonRelease-1>", self._pointer_release)
        for key in ("Return", "KP_Enter", "space"):
            self.window.bind(f"<{key}>", self.commit)
        self.window.bind("<Escape>", self.cancel)
        self.window.bind("<Tab>", lambda event: self.traverse(1))
        self.window.bind("<Shift-Tab>", lambda event: self.traverse(-1))
        self.window.bind("<FocusOut>", self._schedule_focus_check)
        self.window.bind("<Deactivate>", self._schedule_focus_check)
        self.window.bind("<ButtonPress-1>", self._outside_click, add="+")
        width = min(max(combo.winfo_width(), 540), root.winfo_screenwidth() - 40)
        x = min(combo.winfo_rootx(), root.winfo_screenwidth() - width - 20)
        y = min(combo.winfo_rooty(), root.winfo_screenheight() - 340)
        self.window.geometry(f"{width}x300+{max(0, x)}+{max(0, y)}")
        self.window.deiconify()
        self.window.wait_visibility()
        if self.closed:
            return
        self.window.grab_set()
        self.window.focus_set()
        self.listbox.focus_set()
        self.highlight()

    def highlight(self, event=None):
        if self.closed:
            return
        selection = self.listbox.curselection()
        if not selection or selection[0] == self.last_highlight:
            return
        index = selection[0]
        self.last_highlight = index
        describe = getattr(self, "describe", None)
        text = (
            describe(index, self.values[index])
            if describe is not None
            else (f"{index + 1} of {len(self.values)}. {self.values[index]}")
        )
        self.announce(text)

    def pointer_highlight(self, event):
        if self.closed or not self.values:
            return
        index = self.listbox.nearest(event.y)
        self.listbox.selection_clear(0, END)
        self.listbox.selection_set(index)
        self.listbox.activate(index)
        self.highlight()

    def _pointer_press(self, event):
        if not self.closed:
            self.pointer_pressed = True

    def _pointer_release(self, event):
        if self.closed:
            return "break"
        pressed = getattr(self, "pointer_pressed", False)
        self.pointer_pressed = False
        if pressed:
            return self.commit(event)
        return "break"

    def commit(self, event=None):
        if self.closed:
            return "break"
        selection = self.listbox.curselection()
        if selection:
            value = self.values[selection[0]]
            current_values = tuple(self.combo.cget("values"))
            if value not in current_values:
                self.cancel()
                self.announce(
                    "That choice is no longer available. Refresh and try again."
                )
                return "break"
            self.combo.current(current_values.index(value))
            self.cancel()
            self.combo.event_generate("<<ComboboxSelected>>", when="tail")
        return "break"

    def cancel(self, event=None, *, restore_focus=True):
        if not self.closed:
            self.closed = True
            if self.focus_timer is not None:
                self.window.after_cancel(self.focus_timer)
                self.focus_timer = None
            self.window.grab_release()
            self.window.destroy()
            self.on_close()
            if restore_focus:
                self.combo.focus_set()
        return "break"

    def traverse(self, direction):
        if self.closed:
            return "break"
        self.cancel()
        target = (
            self.combo.tk_focusNext() if direction > 0 else self.combo.tk_focusPrev()
        )
        target.focus_set()
        return "break"

    def _check_focus(self):
        self.focus_timer = None
        if self.closed:
            return
        try:
            focus = self.window.focus_get()
        except (KeyError, TclError):
            focus = None
        # Cocoa can transiently report no focus, or restore the originating
        # combobox while completing its click. Neither is an outside action.
        # Explicit outside clicks and Escape still close; transient activation
        # changes are checked after the native event completes.
        if (
            focus is not None
            and focus is not self.combo
            and focus.winfo_toplevel() != self.window
        ):
            self.cancel()

    def _schedule_focus_check(self, event):
        if not self.closed and self.focus_timer is None:
            self.focus_timer = self.window.after_idle(self._check_focus)

    def _outside_click(self, event):
        if self.closed:
            return
        x, y = self.window.winfo_rootx(), self.window.winfo_rooty()
        if not (
            x <= event.x_root < x + self.window.winfo_width()
            and y <= event.y_root < y + self.window.winfo_height()
        ):
            self.cancel()
            return "break"

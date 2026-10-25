"""Native desktop interface for TrustBench."""

import queue
import shlex
import threading
import tkinter as tk
import subprocess
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

from comparison_formatter import generate_comparison_text
from evaluation_launcher import (
    build_live_command,
    run_live_command,
    stop_evaluation_group,
)
from generate_report import generate_text_report
from report_browser import list_saved_reports
from report_loader import load_report as load_saved_report
from report_summary import summarize_live_report


PROJECT_ROOT = Path(__file__).resolve().parent
REPORTS_DIRECTORY = PROJECT_ROOT / "reports"


class TrustBenchDesktop:
    """Display saved TrustBench live-evaluation reports."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("TrustBench Desktop")
        self.root.geometry("850x600")
        self.root.minsize(600, 400)

        self.report_path = tk.StringVar(value="No report selected")

        self.evaluation_running = False
        self.evaluation_events = queue.Queue()
        self.latest_evaluation_report = None
        self.active_evaluation_process = None
        self.stop_requested = False
        self.shutdown_pending = False
        self.shutdown_unverified = False
        self.close_requested = False
        self.evaluation_finished = False
        self.shutdown_lock = threading.Lock()
        self.shutdown_attempted = False
        self.shutdown_verified = False
        self.root.protocol("WM_DELETE_WINDOW", self.on_window_close)

        self.build_interface()

    def build_interface(self):
        """Create separate report and comparison tabs."""

        frame = ttk.Frame(self.root, padding=15)
        frame.pack(fill="both", expand=True)

        title = ttk.Label(
            frame,
            text="TrustBench",
            font=("Helvetica", 22, "bold"),
        )
        title.pack(anchor="w")

        subtitle = ttk.Label(
            frame,
            text="AI Evaluation and Reliability Testing",
        )
        subtitle.pack(anchor="w", pady=(0, 12))

        # Tabs keep each workflow in its own space.
        self.notebook = ttk.Notebook(frame)
        self.notebook.pack(fill="both", expand=True)

        self.reports_tab = ttk.Frame(self.notebook, padding=10)
        self.compare_tab = ttk.Frame(self.notebook, padding=10)
        self.evaluate_tab = ttk.Frame(self.notebook, padding=10)

        self.notebook.add(self.reports_tab, text="Reports")
        self.notebook.add(self.compare_tab, text="Compare")
        self.notebook.add(self.evaluate_tab, text="Evaluate")

        # --------------------
        # Reports tab
        # --------------------

        browser_frame = ttk.LabelFrame(
            self.reports_tab,
            text="Saved Evaluation Reports",
            padding=10,
        )
        browser_frame.pack(fill="x", pady=(0, 10))

        ttk.Button(
            browser_frame,
            text="Refresh Reports",
            command=self.refresh_reports,
        ).pack(anchor="w", pady=(0, 8))

        self.report_list = tk.Listbox(
            browser_frame,
            height=5,
            exportselection=False,
        )
        self.report_list.pack(fill="x", expand=True)

        self.report_list.bind(
            "<Double-Button-1>",
            self.open_selected_report,
        )

        ttk.Button(
            browser_frame,
            text="View Selected Report",
            command=self.open_selected_report,
        ).pack(anchor="w", pady=(8, 0))

        ttk.Button(
            self.reports_tab,
            text="Open Evaluation Report",
            command=self.open_report,
        ).pack(anchor="w", pady=(0, 8))

        ttk.Label(
            self.reports_tab,
            textvariable=self.report_path,
            wraplength=740,
        ).pack(anchor="w", pady=(0, 8))

        self.report_display = scrolledtext.ScrolledText(
            self.reports_tab,
            wrap=tk.WORD,
            font=("Menlo", 12),
            state="disabled",
            height=8,
        )
        self.report_display.pack(fill="both", expand=True)

        # --------------------
        # Compare tab
        # --------------------

        comparison_frame = ttk.LabelFrame(
            self.compare_tab,
            text="Compare Evaluation Reports",
            padding=10,
        )
        comparison_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(
            comparison_frame,
            text="Previous report:",
        ).pack(anchor="w")

        self.previous_report = ttk.Combobox(
            comparison_frame,
            state="readonly",
        )
        self.previous_report.pack(fill="x", pady=(0, 8))

        ttk.Label(
            comparison_frame,
            text="Current report:",
        ).pack(anchor="w")

        self.current_report = ttk.Combobox(
            comparison_frame,
            state="readonly",
        )
        self.current_report.pack(fill="x", pady=(0, 8))

        ttk.Button(
            comparison_frame,
            text="Compare Reports",
            command=self.compare_selected_reports,
        ).pack(anchor="w")

        ttk.Label(
            self.compare_tab,
            text="Comparison Results",
        ).pack(anchor="w", pady=(0, 8))

        self.comparison_display = scrolledtext.ScrolledText(
            self.compare_tab,
            wrap=tk.WORD,
            font=("Menlo", 12),
            state="disabled",
            height=8,
        )

        self.comparison_display.pack(fill="both", expand=True)

        # --------------------
        # Evaluate tab
        # --------------------

        evaluation_frame = ttk.LabelFrame(
            self.evaluate_tab,
            text="Live Ollama Evaluation",
            padding=10,
        )
        evaluation_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(
            evaluation_frame,
            text="Dataset:",
        ).pack(anchor="w")

        self.dataset_path = tk.StringVar(
            value=str(PROJECT_ROOT / "eval-read-live.json")
        )

        ttk.Entry(
            evaluation_frame,
            textvariable=self.dataset_path,
        ).pack(fill="x", pady=(0, 8))

        ttk.Button(
            evaluation_frame,
            text="Browse Dataset",
            command=self.browse_dataset,
        ).pack(anchor="w", pady=(0, 10))

        ttk.Label(
            evaluation_frame,
            text="Ollama model:",
        ).pack(anchor="w")

        self.model_name = tk.StringVar(value="gemma3:1b")

        ttk.Entry(
            evaluation_frame,
            textvariable=self.model_name,
        ).pack(fill="x", pady=(0, 10))

        ttk.Button(
            evaluation_frame,
            text="Preview Command",
            command=self.preview_evaluation,
        ).pack(anchor="w", pady=(0, 8))

        self.start_button = ttk.Button(
            evaluation_frame,
            text="Start Evaluation",
            command=self.start_evaluation,
        )
        self.start_button.pack(anchor="w", pady=(0, 8))

        self.stop_button = ttk.Button(
            evaluation_frame,
            text="Stop Evaluation",
            command=self.stop_evaluation,
            state="disabled",
        )
        self.stop_button.pack(anchor="w")

        ttk.Label(
            self.evaluate_tab,
            text="Evaluation Output",
        ).pack(anchor="w", pady=(0, 8))

        self.evaluation_display = scrolledtext.ScrolledText(
            self.evaluate_tab,
            wrap=tk.WORD,
            font=("Menlo", 12),
            state="disabled",
            height=8,
        )
        self.evaluation_display.pack(fill="both", expand=True)

        self.refresh_reports()

    def browse_dataset(self):
        """Select a JSON dataset for live evaluation."""

        filename = filedialog.askopenfilename(
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
            messagebox.showerror(
                "Invalid Evaluation Settings",
                str(error),
            )
            return False

        output = shlex.join(command)

        self.evaluation_display.configure(state="normal")
        self.evaluation_display.delete("1.0", tk.END)
        self.evaluation_display.insert(tk.END, output)
        self.evaluation_display.configure(state="disabled")
        self.evaluation_display.see("1.0")

        return True

    def start_evaluation(self):
        """Start a live evaluation while keeping the GUI responsive."""

        if (
            self.evaluation_running
            or self.shutdown_pending
            or self.shutdown_unverified
            or self.close_requested
        ):
            return False

        try:
            command = build_live_command(
                self.dataset_path.get(),
                self.model_name.get(),
            )
        except ValueError as error:
            messagebox.showerror(
                "Invalid Evaluation Settings",
                str(error),
            )
            return False

        self.evaluation_running = True
        self.latest_evaluation_report = None
        self.active_evaluation_process = None
        self.stop_requested = False
        self.evaluation_finished = False
        self.shutdown_attempted = False
        self.shutdown_verified = False

        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")

        self.evaluation_display.configure(state="normal")
        self.evaluation_display.delete("1.0", tk.END)
        self.evaluation_display.insert(
            tk.END,
            "Starting live evaluation...\n",
        )
        self.evaluation_display.configure(state="disabled")

        worker = threading.Thread(
            target=self._run_evaluation_worker,
            args=(command,),
            daemon=True,
        )
        worker.start()

        self.root.after(100, self._drain_evaluation_events)
        return True

    def on_window_close(self):
        """Close safely, stopping an active evaluation first."""

        if self.shutdown_unverified:
            messagebox.showwarning(
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

        self.root.destroy()

    def _finish_window_close(self):
        """Close after evaluation and shutdown workers finish."""

        if not self.close_requested:
            return

        if self.shutdown_unverified:
            self.close_requested = False
            messagebox.showwarning(
                "Shutdown Not Verified",
                "Evaluation shutdown could not be verified. "
                "The window will remain open.",
            )
            return

        if self.evaluation_running or self.shutdown_pending:
            return

        self.close_requested = False
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
        self.stop_button.configure(state="disabled")

        self.evaluation_display.configure(state="normal")
        self.evaluation_display.insert(
            tk.END,
            "\nStop requested. Ending evaluation...\n",
        )
        self.evaluation_display.configure(state="disabled")
        self.evaluation_display.see(tk.END)

        if self.active_evaluation_process is not None:
            self._begin_evaluation_shutdown(self.active_evaluation_process)

        return True

    def _begin_evaluation_shutdown(self, process):
        """Start bounded process-group shutdown in a worker thread."""

        if self.shutdown_pending:
            return

        self.shutdown_pending = True

        worker = threading.Thread(
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

        try:
            process = run_live_command(command)
            self.evaluation_events.put(("process", process))

            if process.stdout is not None:
                for line in process.stdout:
                    self.evaluation_events.put(("output", line))

                    if line.startswith("Report saved to: "):
                        report_path = line.removeprefix("Report saved to: ").strip()
                        self.evaluation_events.put(("report_path", report_path))

            return_code = process.wait()
            self.evaluation_finished = True
            self.evaluation_events.put(("done", return_code))

        except (OSError, UnicodeError) as error:
            if process is not None:
                verified = self._stop_process_once(process)

                if verified:
                    try:
                        process.wait(timeout=1.0)
                    except (OSError, subprocess.TimeoutExpired) as shutdown_error:
                        self.evaluation_events.put(
                            ("shutdown_error", str(shutdown_error))
                        )

            self.evaluation_events.put(("error", str(error)))

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

        while True:
            try:
                event_type, value = self.evaluation_events.get_nowait()
            except queue.Empty:
                break

            if event_type == "process":
                self.active_evaluation_process = value

                if self.stop_requested and not self.evaluation_finished:
                    self._begin_evaluation_shutdown(value)

            elif event_type == "output":
                self.evaluation_display.configure(state="normal")
                self.evaluation_display.insert(tk.END, value)
                self.evaluation_display.configure(state="disabled")
                self.evaluation_display.see(tk.END)

            elif event_type == "report_path":
                self.latest_evaluation_report = value

            elif event_type == "shutdown_complete":
                self.shutdown_pending = False
                self.shutdown_unverified = not value

                if not value:
                    self.evaluation_display.configure(state="normal")
                    self.evaluation_display.insert(
                        tk.END,
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
                    tk.END,
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
                self.evaluation_display.insert(tk.END, message)
                self.evaluation_display.configure(state="disabled")

                if value == 0:
                    self.refresh_reports()

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
                    tk.END,
                    f"\nEvaluation startup/read error: {value}\n",
                )
                self.evaluation_display.configure(state="disabled")

        self._finish_window_close()

        if self.evaluation_running or self.shutdown_pending:
            self.root.after(100, self._drain_evaluation_events)

    def refresh_reports(self):
        """Refresh the list of saved evaluation reports."""

        try:
            reports = list_saved_reports(str(REPORTS_DIRECTORY))
        except (OSError, ValueError) as error:
            messagebox.showerror(
                "Unable to List Reports",
                str(error),
            )
            return False

        self.saved_reports = reports

        self.report_list.delete(0, tk.END)

        report_names = [Path(path).name for path in reports]

        self.previous_report["values"] = report_names
        self.current_report["values"] = report_names

        self.previous_report.set("")
        self.current_report.set("")

        for path in reports:
            self.report_list.insert(
                tk.END,
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
            messagebox.showwarning(
                "Select Two Reports",
                "Choose a previous and current report first.",
            )
            return False

        if previous_index == current_index:
            messagebox.showwarning(
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
            messagebox.showerror(
                "Unable to Compare Reports",
                str(error),
            )
            return False

        self.comparison_display.configure(state="normal")
        self.comparison_display.delete("1.0", tk.END)
        self.comparison_display.insert(tk.END, output)
        self.comparison_display.configure(state="disabled")
        self.comparison_display.see("1.0")

        return True

    def open_report(self):
        """Ask the user to select a JSON evaluation report."""

        filename = filedialog.askopenfilename(
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
            messagebox.showerror(
                "Unable to Open Report",
                str(error),
            )
            return False

        self.report_path.set(filename)

        self.report_display.configure(state="normal")
        self.report_display.delete("1.0", tk.END)
        self.report_display.insert(tk.END, output)
        self.report_display.configure(state="disabled")
        self.report_display.see("1.0")

        return True


def main():
    root = tk.Tk()
    TrustBenchDesktop(root)
    root.mainloop()


if __name__ == "__main__":
    main()

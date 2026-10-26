"""Optional desktop progress telemetry, separate from human-readable output."""

from dataclasses import dataclass
from json import dumps, loads
from os import environ
from pathlib import Path

PROGRESS_FILE_ENV = "TRUSTBENCH_PROGRESS_FILE"


def emit_progress(stage: str, **values):
    """Append a small event only when a desktop launcher supplies a file.

    Telemetry failure must not change scoring or prevent report saving.
    The path is supplied by our launcher, never by dataset/model content.
    """
    filename = environ.get(PROGRESS_FILE_ENV)
    if not filename:
        return
    try:
        with open(filename, "a", encoding="utf-8") as output:
            output.write(dumps({"stage": stage, **values}) + "\n")
    except OSError:
        pass


class ProgressReader:
    """Read appended records in bounded chunks, retaining incomplete lines."""

    def __init__(self, path: Path):
        self.path = path
        self.offset = 0
        self.pending = ""

    def read(self):
        try:
            with self.path.open(encoding="utf-8") as source:
                source.seek(self.offset)
                chunk = source.read(65536)
                self.offset = source.tell()
        except (OSError, UnicodeError):
            return []
        records = (self.pending + chunk).split("\n")
        self.pending = records.pop()
        if len(self.pending) > 65536:
            self.pending = ""
        events = []
        for record in records:
            try:
                event = loads(record)
            except ValueError:
                continue
            if isinstance(event, dict):
                events.append(event)
        return events


@dataclass
class EvaluationProgress:
    """Track case completion without estimating inference time or health."""

    total: int | None = None
    completed: int = 0
    current: int = 0
    status: str = "Ready to evaluate"
    started_at: float | None = None
    elapsed_seconds: int = 0
    active: bool = False
    stopping: bool = False

    def start(self, now: float):
        self.total = None
        self.completed = self.current = self.elapsed_seconds = 0
        self.status = "Starting evaluation; validating dataset"
        self.started_at = now
        self.active = True
        self.stopping = False

    def tick(self, now: float):
        if self.active and self.started_at is not None:
            self.elapsed_seconds = max(0, int(now - self.started_at))

    def apply(self, event: dict):
        if not self.active:
            return
        stage = event.get("stage")
        if stage == "started" and self.total is None:
            total = event.get("total")
            if type(total) is not int or total < 0:
                return
            self.total = total
            self.status = "Dataset validated; preparing requests"
        elif stage == "case_started" and self.total is not None:
            index = event.get("index")
            if (
                type(index) is not int
                or index != self.completed + 1
                or index > self.total
            ):
                return
            self.current = index
            self.status = (
                f"Waiting for Ollama response for case {index} of {self.total}"
            )
        elif stage == "case_completed" and self.total is not None:
            count = event.get("completed")
            if (
                type(count) is not int
                or count != self.completed + 1
                or count != self.current
                or count > self.total
                or event.get("outcome") not in ("PASS", "FAIL", "ERROR")
            ):
                return
            self.completed = count
            self.status = (
                f"Case {count} finished ({event['outcome']}); preparing next step"
            )
        elif stage == "saving" and self.total == self.completed:
            self.status = "Cases finished; preparing and saving report"
        elif stage == "saved" and self.total == self.completed:
            self.status = "Report saved; waiting for evaluation process to finish"
        if self.stopping:
            self.status = "Stopping evaluation; waiting for process cleanup"

    def request_stop(self):
        self.stopping = True
        self.status = "Stopping evaluation; waiting for process cleanup"

    def finish(self, status: str, now: float):
        self.tick(now)
        self.active = False
        self.status = status

    def elapsed_text(self) -> str:
        minutes, seconds = divmod(self.elapsed_seconds, 60)
        return f"Elapsed: {minutes:02d}:{seconds:02d}"

    def count_text(self) -> str:
        if self.total is None:
            return "Completed cases: total not yet available"
        return f"{self.completed} of {self.total} cases completed"

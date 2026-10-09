"""Optional collection feedback; failures in the UI never affect collection."""

from __future__ import annotations

import os
import sys
from typing import Optional

from pylistall.names import visible_name


class CollectionProgress:
    def __init__(self, disabled: bool = False):
        self.enabled = (
            not disabled
            and os.environ.get("TERM") != "dumb"
            and bool(getattr(sys.stderr, "isatty", lambda: False)())
        )
        self.progress = None
        self.task: Optional[int] = None
        self.stage = ""
        self.counts = {"discovered": 0, "total": 0, "checked": 0, "collected": 0}

    def __enter__(self):
        if not self.enabled:
            return self
        try:
            from rich.console import Console
            from rich.progress import (
                BarColumn,
                Progress,
                SpinnerColumn,
                TextColumn,
            )
            from rich.table import Column

            self.progress = Progress(
                SpinnerColumn(),
                TextColumn(
                    "{task.description}",
                    markup=False,
                    table_column=Column(ratio=3, no_wrap=True, overflow="ellipsis"),
                ),
                BarColumn(bar_width=None, table_column=Column(ratio=1, min_width=8)),
                TextColumn("{task.fields[counts]}", markup=False),
                console=Console(file=sys.stderr, markup=False, highlight=False),
                transient=True,
                refresh_per_second=10,
                redirect_stdout=False,
                redirect_stderr=False,
                expand=True,
            )
            self.progress.start()
        except Exception:
            self._stop()
        except KeyboardInterrupt:
            self._stop()
            raise
        return self

    def update(self, stage: str, path: str = "", **counts: int) -> None:
        self.counts.update(counts)
        if self.progress is None:
            return
        try:
            if stage != self.stage:
                if self.task is not None:
                    self.progress.remove_task(self.task)
                self.stage = stage
                self.task = self.progress.add_task("", total=None, counts="")
            file_stage = stage == "files"
            total = self.counts["total"] if file_stage else None
            counter = (
                f"{self.counts['checked']}/{total} checked; "
                f"{self.counts['collected']} collected"
                if file_stage
                else f"{self.counts['discovered']} discovered"
            )
            self.progress.update(
                self.task,
                total=total,
                completed=self.counts["checked"] if file_stage else 0,
                description=f"{stage}: {visible_name(path)}",
                counts=counter,
            )
        except Exception:
            self._stop()

    def _stop(self) -> None:
        progress, self.progress = self.progress, None
        if progress is not None:
            try:
                progress.stop()
            except Exception:
                pass

    def __exit__(self, *args):
        self._stop()

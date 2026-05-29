from __future__ import annotations

from contextlib import AbstractContextManager, contextmanager
from typing import Protocol

from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)


class ProgressTask(Protocol):
    def advance(self, amount: int = 1) -> None: ...


class ProgressReporter(Protocol):
    def task(
        self,
        description: str,
        *,
        total: int | None = None,
    ) -> AbstractContextManager[ProgressTask]: ...


class NullProgressTask:
    def advance(self, amount: int = 1) -> None:
        return None


class NullProgressReporter:
    @contextmanager
    def task(self, description: str, *, total: int | None = None):
        yield NullProgressTask()


class RichProgressTask:
    def __init__(self, progress: Progress, task_id: int) -> None:
        self.progress = progress
        self.task_id = task_id

    def advance(self, amount: int = 1) -> None:
        self.progress.advance(self.task_id, amount)


class RichProgressReporter:
    def __init__(self, console: Console) -> None:
        self.console = console

    @contextmanager
    def task(self, description: str, *, total: int | None = None):
        columns = (
            (
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                TimeElapsedColumn(),
            )
            if total is None
            else (
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                MofNCompleteColumn(),
                TimeElapsedColumn(),
                TimeRemainingColumn(),
            )
        )
        with Progress(
            *columns,
            console=self.console,
            transient=True,
        ) as progress:
            task_id = progress.add_task(description, total=total)
            yield RichProgressTask(progress, task_id)

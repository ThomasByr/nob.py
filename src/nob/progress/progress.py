from dataclasses import dataclass
from datetime import timedelta

from rich.console import RenderableType
from rich.progress import (
    BarColumn,
    ProgressColumn,
    Task,
    TextColumn,
)
from rich.style import Style
from rich.text import Text


@dataclass
class RichProgressBarTheme:
    """Styles to associate to different base components.

    Args:
        description: Style for the progress bar description. For eg., Epoch x, Testing, etc.
        progress_bar: Style for the bar in progress.
        progress_bar_finished: Style for the finished progress bar.
        progress_bar_pulse: Style for the progress bar when `IterableDataset` is being processed.
        batch_progress: Style for the progress tracker (i.e 10/50 batches completed).
        time: Style for the processed time and estimate time remaining.
        processing_speed: Style for the speed of the batches being processed.
        metrics: Style for the metrics

    https://rich.readthedocs.io/en/stable/style.html

    """

    description: str | Style = ""
    progress_bar: str | Style = "#6206E0"
    progress_bar_finished: str | Style = "#6206E0"
    progress_bar_pulse: str | Style = "#6206E0"
    batch_progress: str | Style = ""
    time: str | Style = "dim"
    processing_speed: str | Style = "dim underline"
    metrics: str | Style = "italic"
    metrics_text_delimiter: str = " "
    metrics_format: str = ".3f"


class CustomTimeColumn(ProgressColumn):
    # Only refresh twice a second to prevent jitter
    max_refresh = 0.5

    def __init__(self, style: str | Style) -> None:
        self.style = style
        super().__init__()

    def render(self, task: "Task") -> Text:
        elapsed = task.finished_time if task.finished else task.elapsed
        remaining = task.time_remaining
        elapsed_delta = "-:--:--" if elapsed is None else str(timedelta(seconds=int(elapsed)))
        remaining_delta = "-:--:--" if remaining is None else str(timedelta(seconds=int(remaining)))
        return Text(f"{elapsed_delta} • {remaining_delta}", style=self.style)


class BatchesProcessedColumn(ProgressColumn):
    def __init__(self, style: str | Style):
        self.style = style
        super().__init__()

    def render(self, task: "Task") -> RenderableType:
        total = task.total if task.total != float("inf") else "--"
        return Text(f"{int(task.completed)}/{total}", style=self.style)


class ProcessedColumn(ProgressColumn):
    def __init__(self, style: str | Style):
        self.style = style
        super().__init__()

    def render(self, task: "Task") -> RenderableType:
        return Text(f"{int(task.completed)}", style=self.style)


class ProcessingSpeedColumn(ProgressColumn):
    def __init__(self, style: str | Style):
        self.style = style
        super().__init__()

    def render(self, task: "Task") -> RenderableType:
        task_speed = f"{task.speed:>.2f}" if task.speed is not None else "0.00"
        return Text(f"{task_speed}it/s", style=self.style)


theme = RichProgressBarTheme()


def default_columns(known_total: bool = True) -> list[ProgressColumn]:
    return (
        [
            TextColumn("[progress.description]{task.description}"),
            BarColumn(
                bar_width=20,
                complete_style=theme.progress_bar,
                finished_style=theme.progress_bar_finished,
                pulse_style=theme.progress_bar_pulse,
            ),
        ]
        + (
            [BatchesProcessedColumn(style=theme.batch_progress)]
            if known_total
            else [ProcessedColumn(style=theme.batch_progress)]
        )
        + [
            CustomTimeColumn(style=theme.time),
            ProcessingSpeedColumn(style=theme.processing_speed),
        ]
    )

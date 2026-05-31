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
from typing_extensions import override

from .. import human


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

    def __init__(self, style: str | Style, known_total: bool) -> None:
        self.style = style
        self.__known_total = known_total
        super().__init__()

    @override
    def render(self, task: "Task") -> Text:
        elapsed = task.finished_time if task.finished else task.elapsed
        remaining = task.time_remaining
        elapsed_delta = "-:--:--" if elapsed is None else str(timedelta(seconds=int(elapsed)))
        remaining_delta = "-:--:--" if remaining is None else str(timedelta(seconds=int(remaining)))
        if self.__known_total:
            return Text(f"{elapsed_delta} • {remaining_delta}", style=self.style)
        return Text(f"{elapsed_delta}", style=self.style)


class BatchesProcessedColumn(ProgressColumn):
    def __init__(self, style: str | Style, hfmt: bool = True, unit: str = ""):
        self.style = style
        self.__hfmt = hfmt
        self.__unit = unit
        super().__init__()

    @override
    def render(self, task: "Task") -> RenderableType:
        completed = int(task.completed)
        total = int(task.total) if task.total is not None and task.total != float("inf") else "--"
        if self.__hfmt:
            if isinstance(total, int):
                total = str(human.count(total, self.__unit))
            return Text(f"{human.count(completed, self.__unit)}/{total}", style=self.style)
        return Text(f"{completed}{self.__unit}/{total}{self.__unit}", style=self.style)


class ProcessedColumn(ProgressColumn):
    def __init__(self, style: str | Style, hfmt: bool = True, unit: str = ""):
        self.style = style
        self.__hfmt = hfmt
        self.__unit = unit
        super().__init__()

    @override
    def render(self, task: "Task") -> RenderableType:
        completed = int(task.completed)
        if self.__hfmt:
            return Text(str(human.count(completed, self.__unit)), style=self.style)
        return Text(f"{completed}{self.__unit}", style=self.style)


class PercentageColumn(ProgressColumn):
    def __init__(self, style: str | Style):
        self.style = style
        super().__init__()

    @override
    def render(self, task: "Task") -> RenderableType:
        percentage = f"{task.percentage:>.2f}%" if task.percentage is not None else "0.00%"
        return Text(percentage, style=self.style)


class ProcessingSpeedColumn(ProgressColumn):
    def __init__(self, style: str | Style, hfmt: bool = True, unit: str = ""):
        self.style = style
        self.__hfmt = hfmt
        self.__unit = unit
        super().__init__()

    @override
    def render(self, task: "Task") -> RenderableType:
        if self.__hfmt:
            task_speed = (
                str(human.throughput(task.speed, self.__unit))
                if task.speed is not None
                else f"0.00{self.__unit}/s"
            )
        else:
            task_speed = (
                f"{task.speed:.2f}{self.__unit}/s" if task.speed is not None else f"0.00{self.__unit}/s"
            )
        return Text(task_speed, style=self.style)


theme = RichProgressBarTheme()


def create_columns(
    known_total: bool = True,
    show_percentage: bool = False,
    hide_time: bool = False,
    hide_processing_speed: bool = False,
    human_format: bool = True,
    unit: str = "",
) -> list[ProgressColumn]:
    """Create a list of defaults columns for your `rich.progress.Progress` object.

    Args:
        known_total (bool, optional): If the total number of items will be known when the progress starts. Defaults to True.
        show_percentage (bool, optional): To show percentage instead of `completed/total`. Can be useful for large items. Defaults to False.
        hide_time (bool, optional): Whether to hide the time column. Defaults to False.
        hide_processing_speed (bool, optional): Whether to hide the processing speed column. Defaults to False.
        human_format (bool, optional): Whether to use human readable format for numbers. Defaults to True.
        unit (str, optional): Unit to use for human readable format. Defaults to "".

    Returns:
        list[ProgressColumn]: _description_
    """

    def get_batches_column():
        if show_percentage:
            return [PercentageColumn(theme.metrics)]
        if known_total:
            return [BatchesProcessedColumn(theme.batch_progress, human_format, unit)]
        return [ProcessedColumn(theme.batch_progress, human_format, unit)]

    def get_time_column():
        if hide_time:
            return []
        return [CustomTimeColumn(theme.time, known_total)]

    def get_processing_speed_column():
        if hide_processing_speed:
            return []
        return [ProcessingSpeedColumn(theme.processing_speed, human_format, unit)]

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
        + get_batches_column()
        + get_time_column()
        + get_processing_speed_column()
    )

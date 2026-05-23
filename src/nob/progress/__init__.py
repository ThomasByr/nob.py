from collections.abc import Callable, Iterable
from typing import TypeVar

from rich.progress import Console, Progress

from .progress import create_columns

__all__ = ["track", "progress"]

T = TypeVar("T")


def track(
    sequence: Iterable[T],
    description: str = "Working...",
    total: float | None = -1,
    show_percentage: bool = False,
    hide_time: bool = False,
    hide_processing_speed: bool = False,
    completed: int = 0,
    auto_refresh: bool = True,
    transient: bool = False,
    get_time: Callable[[], float] | None = None,
    console: Console | None = None,
    refresh_per_second: float = 10,
    update_period: float = 0.1,
    disable: bool = False,
) -> Iterable[T]:
    """Track progress by iterating over a sequence.

    You can also track progress of an iterable, which might require that you additionally specify ``total``.

    Args:
        sequence (Iterable[T]): Values you wish to iterate over and track progress.
        description (str, optional): Description of task show next to progress bar. Defaults to "Working".
        total: (float, optional): Total number of steps. Set to `-1` to use default, deactivate with `None`. Default is len(sequence).
        show_percentage (bool, optional): To show percentage instead of `completed/total`. Can be useful for large items. Defaults to False.
        hide_time (bool, optional): Whether to hide the time column. Defaults to False.
        hide_processing_speed (bool, optional): Whether to hide the processing speed column. Defaults to False.
        completed (int, optional): Number of steps completed so far. Defaults to 0.
        auto_refresh (bool, optional): Automatic refresh, disable to force a refresh after each iteration. Default is True.
        transient: (bool, optional): Clear the progress on exit. Defaults to False.
        get_time: (Callable, optional): A callable that gets the current time, or None to use Console.get_time. Defaults to None.
        console (Console, optional): Console to write to. Default creates internal Console instance.
        refresh_per_second (float): Number of times per second to refresh the progress information. Defaults to 10.
        update_period (float, optional): Minimum time (in seconds) between calls to update(). Defaults to 0.1.
        disable (bool, optional): Disable display of progress.

    Returns:
        Iterable[T]: An iterable of the values in the sequence.
    """

    progress = Progress(
        *create_columns(total is not None, show_percentage, hide_time, hide_processing_speed),
        auto_refresh=auto_refresh,
        console=console,
        transient=transient,
        get_time=get_time,
        refresh_per_second=refresh_per_second or 10,
        disable=disable,
    )

    with progress:
        yield from progress.track(
            sequence,
            total=None if total is None or total < 0 else total,
            completed=completed,
            description=description,
            update_period=update_period,
        )


def progress(
    known_total: bool = True,
    show_percentage: bool = False,
    hide_time: bool = False,
    hide_processing_speed: bool = False,
    auto_refresh: bool = True,
    transient: bool = False,
    get_time: Callable[[], float] | None = None,
    console: Console | None = None,
    refresh_per_second: float = 10,
    disable: bool = False,
) -> Progress:
    """Creates a new custom `rich.progress.Progress` object.

    Args:
        known_total (bool, optional): If the program will assure the total number of elements to track progress for will be available when the tracking starts. Defaults to True.
        show_percentage (bool, optional): To show percentage instead of `completed/total`. Can be useful for large items. Defaults to False.
        hide_time (bool, optional): Whether to hide the time column. Defaults to False.
        hide_processing_speed (bool, optional): Whether to hide the processing speed column. Defaults to False.
        auto_refresh (bool, optional): Automatic refresh, disable to force a refresh after each iteration. Defaults to True.
        transient (bool, optional): Clear the progress on exit. Defaults to False.
        get_time (Callable[[], float] | None, optional): A callable that gets the current time, or None to use Console.get_time. Defaults to None.
        console (Console | None, optional): Console to write to. Defaults to None.
        refresh_per_second (float): Number of times per second to refresh the progress information. Defaults to 10.
        disable (bool, optional): Disable display of progress.

    Returns:
        Progress: A Progress object with custom colors and columns.
    """
    return Progress(
        *create_columns(known_total, show_percentage, hide_time, hide_processing_speed),
        auto_refresh=auto_refresh,
        console=console,
        transient=transient,
        get_time=get_time,
        refresh_per_second=refresh_per_second or 10,
        disable=disable,
    )

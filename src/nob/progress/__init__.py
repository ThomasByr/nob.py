from collections.abc import Callable
from typing import Iterable, TypeVar

from rich.progress import Console, Progress

from .progress import default_columns

__all__ = ["track", "progress"]


T = TypeVar("T")


def track(
    sequence: Iterable[T],
    description: str = "Working...",
    total: float | None = None,
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
        total: (float, optional): Total number of steps. Default is len(sequence).
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
        *default_columns(total is not None),
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
            total=total,
            completed=completed,
            description=description,
            update_period=update_period,
        )


def progress(
    known_total: bool = True,
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
        *default_columns(known_total),
        auto_refresh=auto_refresh,
        console=console,
        transient=transient,
        get_time=get_time,
        refresh_per_second=refresh_per_second or 10,
        disable=disable,
    )

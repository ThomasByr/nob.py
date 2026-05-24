from collections import deque
from collections.abc import Iterable
from datetime import datetime, timedelta
from time import perf_counter, sleep
from typing import TypeVar, overload

__all__ = ["tick"]

T = TypeVar("T")
IntoTimeDelta = timedelta | datetime | float | int


class TimeDelta:
    def __init__(self, value: IntoTimeDelta):
        if isinstance(value, timedelta):
            self.value = value.total_seconds()
        elif isinstance(value, datetime):
            self.value = (value - datetime.now()).total_seconds()
        elif isinstance(value, (float, int)):
            self.value = float(value)
        else:
            raise ValueError(f"Unsupported type for IntoTimeDelta: {type(value)}")

    def __str__(self) -> str:
        return f"{self.value}s"

    def into(self) -> float:
        return self.value


class TickRateCounter:
    def __init__(self, mean_over: IntoTimeDelta = 1):
        self.mean_over = TimeDelta(mean_over).into()
        self.tick_times: deque[float] = deque()

    def tick(self):
        """Record a tick and update the tick times deque."""
        now = perf_counter()
        self.tick_times.append(now)

        while self.tick_times and now - self.tick_times[0] > self.mean_over:
            self.tick_times.popleft()

    def rate(self):
        """Calculate the current tick rate based on the recorded tick times. Unit is always ticks per second."""
        if len(self.tick_times) < 2:
            return 0
        duration = self.tick_times[-1] - self.tick_times[0]
        return (len(self.tick_times) - 1) / duration if duration > 0 else float("inf")


@overload
def tick(rate: int = 100) -> None: ...
@overload
def tick(rate: int = 100, mean_over: IntoTimeDelta = 1) -> None: ...
@overload
def tick(sequence: Iterable[T], rate: int = 100) -> Iterable[T]: ...
@overload
def tick(sequence: Iterable[T], rate: int = 100, mean_over: IntoTimeDelta = 1) -> Iterable[T]: ...


def tick(
    sequence: Iterable[T] | int = 100, rate: int = 100, /, *, mean_over: IntoTimeDelta = 1
) -> Iterable[T] | None:
    """Sleep to maintain a consistent tick rate.

    Args:
        sequence (Iterable[T] | int, optional): An optional iterable to wrap. If an integer is provided, it is treated as the rate and the function operates in standalone mode. Defaults to 100.
        rate (int, optional): Desired tick rate in ticks per second. Ignored if `sequence` is an integer. Defaults to 100.
        mean_over (IntoTimeDelta, optional): Time window to calculate the mean tick rate over. Defaults to 1 second.

    Returns:
        Iterable[T] | None: If `sequence` is provided, returns an iterable that yields items from `sequence` while maintaining the tick rate. If `sequence` is an integer, returns None and operates in standalone mode, where each call to `tick()` will sleep as necessary to maintain the tick rate.

    Examples:
        ```
        # 100 ticks per second, called with a sequence
        for _ in tick(range(100)):
            ...
        # 100 ticks per second, called without a sequence
        for _ in range(100):
            tick()
        # both are equivalent and should ensure that the loop runs at 100 ticks per second
        ```
    """
    if isinstance(sequence, int):
        actual_rate = sequence
        iterable_seq = None
    else:
        actual_rate = rate
        iterable_seq = sequence

    interval = 1.0 / actual_rate

    if iterable_seq is None:
        import sys

        # Identify the call site to detect when we enter a new loop
        try:
            frame = sys._getframe(1)
            call_site = (id(frame.f_code), frame.f_lasti)
        except (ValueError, AttributeError) as e:
            raise RuntimeError("`tick` must be called from a Python frame") from e

        # Standalone mode: we use attributes on the function itself to "remember" state
        is_new_call_site = not hasattr(tick, "__last_call_site") or tick.__last_call_site != call_site

        if is_new_call_site or not hasattr(tick, "__next_tick"):
            tick.__next_tick = perf_counter()  # ty:ignore[unresolved-attribute]
            tick.__last_call_site = call_site  # ty:ignore[unresolved-attribute]
            tick.counter = TickRateCounter(mean_over)  # ty:ignore[unresolved-attribute]

        now = perf_counter()
        if now < tick.__next_tick:  # ty:ignore[unresolved-attribute]
            sleep(tick.__next_tick - now)  # ty:ignore[unresolved-attribute]
            tick.__next_tick += interval  # ty:ignore[unresolved-attribute]
        else:
            tick.__next_tick = now + interval  # ty:ignore[unresolved-attribute]

        tick.counter.tick()  # ty:ignore[unresolved-attribute]
        return None

    # Wrapping mode: use a generator to preserve state between iterations
    tick.counter = TickRateCounter(mean_over)  # ty:ignore[unresolved-attribute]

    def generator():
        next_tick = perf_counter()
        for item in iterable_seq:
            now = perf_counter()
            if now < next_tick:
                sleep(next_tick - now)
                next_tick += interval
            else:
                next_tick = now + interval

            tick.counter.tick()  # ty:ignore[unresolved-attribute]
            yield item

    return generator()

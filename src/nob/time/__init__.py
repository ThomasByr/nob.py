from contextlib import AbstractContextManager
from time import perf_counter, sleep
from typing import Callable, Iterable, TypeVar, overload

from .about import Handle, HandleResult, HandleStats, context_timing
from .tick import IntoTimeDelta, TickRateCounter

__all__ = ["about", "tick"]

T = TypeVar("T")


@overload
def about(func: Callable[..., T], *args, **kwargs) -> "HandleResult[T]": ...
@overload
def about(it: Iterable[T]) -> "HandleStats": ...
@overload
def about() -> "AbstractContextManager[Handle]": ...


def about(func_or_it: Callable[..., T] | Iterable[T] | None = None, *args, **kwargs):
    """Measure timing and throughput of code blocks, with beautiful
    human friendly representations.

    There are three modes of operation: context manager, callable and
    throughput.

    1. Use it like a context manager:

    >>> with about() as t:
    ....    # code block.

    2. Use it with a callable:

    >>> def func(a, b): ...
    >>> t = about(func, 1, b=2)  # send arguments at will.

    3. Use it with an iterable or generator:

    >>> t = about(it)  # any iterable or generator.
    >>> for item in t:
    ....    # use item
    """

    timings = [0.0, 0.0]

    # Use as a context manager
    if func_or_it is None:
        return context_timing(timings, Handle(timings))

    # Use as a callable
    if callable(func_or_it):
        with context_timing(timings):
            result = func_or_it(*args, **kwargs)  # ty:ignore[call-top-callable]
        return HandleResult(timings, result)

    try:
        it = iter(func_or_it)
    except TypeError as e:
        raise UserWarning("param should be callable or iterable.") from e

    # Use as a counter/throughput iterator
    def it_closure():
        with context_timing(timings):
            # Iterators are iterable
            for it_closure.count, elem in enumerate(it, 1):  # ty:ignore[unresolved-attribute]
                yield elem

    # The count will only be updated after starting iterating.
    it_closure.count = 0  # ty:ignore[unresolved-attribute]
    return HandleStats(timings, it_closure)


@overload
def tick(
    rate: int = 100, *, mean_over: IntoTimeDelta = 1, safe_counter: TickRateCounter | None = None
) -> None: ...
@overload
def tick(
    sequence: Iterable[T],
    rate: int = 100,
    *,
    mean_over: IntoTimeDelta = 1,
    safe_counter: TickRateCounter | None = None,
) -> Iterable[T]: ...


def tick(
    sequence: Iterable[T] | int = 100,
    rate: int = 100,
    /,
    *,
    mean_over: IntoTimeDelta = 1,
    safe_counter: TickRateCounter | None = None,
) -> Iterable[T] | None:
    """Sleep to maintain a consistent tick rate.

    Args:
        sequence (Iterable[T] | int, optional): An optional iterable to wrap. If an integer is provided, it is treated as the rate and the function operates in standalone mode. Defaults to 100.
        rate (int, optional): Desired tick rate in ticks per second. Ignored if `sequence` is an integer. Defaults to 100.
        mean_over (IntoTimeDelta, optional): Time window to calculate the mean tick rate over. Defaults to 1 second.
        safe_counter (TickRateCounter | None, optional): An optional `TickRateCounter` instance to use for tracking tick rates. If not provided, a new instance will be created and stored as an attribute on the function for standalone mode, or used directly for wrapping mode. Automated new instances creation are subject to bugs in some cases. Defaults to None.

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
            if safe_counter is None:
                tick.counter = TickRateCounter(mean_over)  # ty:ignore[unresolved-attribute]

        now = perf_counter()
        if now < tick.__next_tick:  # ty:ignore[unresolved-attribute]
            sleep(tick.__next_tick - now)  # ty:ignore[unresolved-attribute]
            tick.__next_tick += interval  # ty:ignore[unresolved-attribute]
        else:
            tick.__next_tick = now + interval  # ty:ignore[unresolved-attribute]

        counter_to_use = safe_counter if safe_counter is not None else tick.counter  # ty:ignore[unresolved-attribute]
        counter_to_use.tick()
        return None

    # Wrapping mode: use a generator to preserve state between iterations
    if safe_counter is None:
        tick.counter = TickRateCounter(mean_over)  # ty:ignore[unresolved-attribute]

    counter_to_use = safe_counter if safe_counter is not None else tick.counter  # ty:ignore[unresolved-attribute]

    def generator():
        next_tick = perf_counter()
        for item in iterable_seq:
            now = perf_counter()
            if now < next_tick:
                sleep(next_tick - now)
                next_tick += interval
            else:
                next_tick = now + interval

            counter_to_use.tick()
            yield item

    return generator()

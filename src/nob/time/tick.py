from collections import deque
from datetime import datetime, timedelta
from time import perf_counter
from typing import TypeVar

from ..human import duration

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
        return str(duration(self.value))

    def into(self) -> float:
        return self.value


class TickRateCounter:
    MIN_LEN_FOR_RATE_CALC = 2

    def __init__(self, mean_over: IntoTimeDelta = 1):
        self.__mean_over = TimeDelta(mean_over).into()
        self.__tick_times: deque[float] = deque()

    def tick(self):
        """Record a tick and update the tick times deque."""
        now = perf_counter()
        self.__tick_times.append(now)

        while self.__tick_times and now - self.__tick_times[0] > self.__mean_over:
            self.__tick_times.popleft()

    def rate(self):
        """Calculate the current tick rate based on the recorded tick times. Unit is always ticks per second."""
        if len(self.__tick_times) < self.MIN_LEN_FOR_RATE_CALC:
            return 0
        duration = self.__tick_times[-1] - self.__tick_times[0]
        return (len(self.__tick_times) - 1) / duration if duration > 0 else float("inf")

    def reset(self):
        """Reset the tick times."""
        self.__tick_times.clear()

    @property
    def mean_over(self) -> float:
        """Get the time window over which the tick rate is averaged, in seconds."""
        return self.__mean_over

    @mean_over.setter
    def mean_over(self, value: IntoTimeDelta):
        """Set the time window over which the tick rate is averaged, in seconds."""
        self.__mean_over = TimeDelta(value).into()

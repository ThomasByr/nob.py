from collections import deque
from datetime import datetime, timedelta
from time import perf_counter
from typing import TypeVar

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

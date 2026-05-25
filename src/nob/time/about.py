from contextlib import contextmanager
from time import perf_counter
from typing import Generic, TypeVar

from ..human.count import HumanCount
from ..human.duration import HumanDuration
from ..human.throughput import HumanThroughput

T = TypeVar("T")


@contextmanager
def context_timing(timings, handle=None):
    timings[0] = perf_counter()
    yield handle
    timings[1] = perf_counter()


class Handle(object):
    def __init__(self, timings):
        self.__timings = timings

    @property
    def duration(self) -> float:
        """Return the actual duration in seconds.
        This is dynamically updated in real time.

        Returns:
            the number of seconds.

        """
        return (self.__timings[1] or perf_counter()) - self.__timings[0]

    @property
    def duration_human(self) -> HumanDuration:
        """Return a beautiful representation of the duration.
        It dynamically calculates the best unit to use.

        Returns:
            the human representation.

        """
        return HumanDuration(self.duration)


class HandleResult(Generic[T], Handle):
    def __init__(self, timings, result: T):
        super(HandleResult, self).__init__(timings)
        self.__result = result

    @property
    def result(self):
        """Return the result of the callable.

        Returns:
            the result of the callable.

        """
        return self.__result


class HandleStats(Handle):
    def __init__(self, timings, it_closure):
        super(HandleStats, self).__init__(timings)
        self.__it = it_closure

    def __iter__(self):
        return self.__it()

    @property
    def count(self) -> int:
        """Return the current iteration count.
        This is dynamically updated in real time.

        Returns:
            the current iteration count.

        """
        return self.__it.count

    @property
    def count_human(self) -> HumanCount:
        """Return a beautiful representation of the current iteration count.
        This is dynamically updated in real time.

        Returns:
            the human representation.

        """
        return self.count_human_as("")

    def count_human_as(self, unit: str) -> HumanCount:
        """Return a beautiful representation of the current iteration count.
        This is dynamically updated in real time.

        Args:
            unit: what is being measured

        Returns:
            the human representation.

        """
        return HumanCount(self.count, unit)

    @property
    def throughput(self) -> float:
        """Return the current throughput in items per second.
        This is dynamically updated in real time.

        Returns:
            the number of items per second.

        """
        try:
            return self.count / self.duration
        except ZeroDivisionError:
            return float("nan")

    @property
    def throughput_human(self) -> HumanThroughput:
        """Return a beautiful representation of the current throughput.
        It dynamically calculates the best unit to use.

        Returns:
            the human representation.

        """
        return self.throughput_human_as("")

    def throughput_human_as(self, unit: str) -> HumanThroughput:
        """Return a beautiful representation of the current throughput.
        It dynamically calculates the best unit to use.

        Args:
            unit: what is being measured

        Returns:
            the human representation.

        """
        return HumanThroughput(self.throughput, unit)

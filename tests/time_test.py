import random
from datetime import datetime
from decimal import Decimal
from itertools import chain, repeat, tee
from unittest import mock

import pytest

from nob import time

# Tick counting below 1*mean_over are less reliable
EPSILON = 8e-3  # Tolerances for tick estimations, since they happen with few iterations


class VirtualTime:
    def __init__(self):
        self.time = 0.0

    def perf_counter(self):
        return self.time

    def sleep(self, seconds):
        if seconds > 0:
            self.time += seconds


@pytest.fixture
def virtual_time():
    vt = VirtualTime()
    with (
        mock.patch("nob.time.perf_counter", side_effect=vt.perf_counter),
        mock.patch("nob.time.sleep", side_effect=vt.sleep),
        mock.patch("nob.time.tick.perf_counter", side_effect=vt.perf_counter),
    ):
        yield vt


@pytest.fixture
def rand_offset():
    return random.random() * 1000


@pytest.fixture
def mock_timer():
    with mock.patch("nob.time.about.perf_counter") as mt:
        yield mt


def test_tick_iterator_timing(virtual_time):
    # rate = 20, interval = 0.05
    # 5 iterations (0 to 4) should pause 4 times
    # Target duration: 4 * 0.05 = 0.2 seconds
    start = virtual_time.perf_counter()
    for _ in time.tick(range(5), 20):
        pass
    end = virtual_time.perf_counter()
    duration = end - start
    assert duration == pytest.approx(0.2, abs=EPSILON)


def test_tick_standalone_timing(virtual_time):
    # rate = 20, interval = 0.05
    # 5 iterations should pause 4 times
    # Target duration: 4 * 0.05 = 0.2 seconds
    start = virtual_time.perf_counter()
    for _ in range(5):
        time.tick(20)
    end = virtual_time.perf_counter()
    duration = end - start
    assert duration == pytest.approx(0.2, abs=EPSILON)


def test_tick_standalone_distinct_loops(virtual_time):
    # Two independent loops where the second should not try to maintain cadence from the first
    for in_between_sleep in [0.0, 0.1, 0.2, 0.5]:
        # Loop 1: 5 iterations at 20Hz -> ~0.2s
        start1 = virtual_time.perf_counter()
        for _ in range(5):
            time.tick(20)
        end1 = virtual_time.perf_counter()

        # Simulate a pause between loops
        virtual_time.sleep(in_between_sleep)

        # Loop 2: 5 iterations at 20Hz -> ~0.2s
        # If the frame inspection trick failed, this loop might sleep an awkward amount
        # or skip sleeping entirely to "catch up" instantly. We want consistent timing.
        start2 = virtual_time.perf_counter()
        for _ in range(5):
            time.tick(20)
        end2 = virtual_time.perf_counter()

        duration1 = end1 - start1
        duration2 = end2 - start2

        assert duration1 == pytest.approx(0.2, abs=EPSILON)
        assert duration2 == pytest.approx(0.2, abs=EPSILON)


def test_tick_long_workload(virtual_time):
    # When business logic takes longer than the interval, tick should fall behind and
    # not double-sleep, resulting in purely the duration of the workload
    start = virtual_time.perf_counter()
    for _ in range(3):
        time.tick(20)  # interval = 0.05
        virtual_time.sleep(0.08)  # Takes longer than the interval
    end = virtual_time.perf_counter()
    duration = end - start

    # 3 iterations. Inter-tick sleep wouldn't happen because workload takes longer.
    # Total time should just be 3 * 0.08 = 0.24 seconds + setup time.
    assert duration == pytest.approx(0.24, abs=EPSILON)


def test_tick_counter_rate(virtual_time):
    # Loop 15 times at 50Hz, takes ~0.3s
    # The rate counter should be approximately 50
    for _ in time.tick(range(16), 50):
        pass
    rate = time.tick.counter.rate()  # ty:ignore[unresolved-attribute]
    assert rate == pytest.approx(50, abs=1)  # Allow some more tolerance


def test_tick_safe_counter_standalone(virtual_time):
    my_counter = time.TickRateCounter(mean_over=1)

    for _ in range(16):
        time.tick(50, safe_counter=my_counter)

    rate = my_counter.rate()
    assert rate == pytest.approx(50, abs=1)


def test_tick_safe_counter_iterator(virtual_time):
    my_counter = time.TickRateCounter(mean_over=2)

    for _ in time.tick(range(16), 50, safe_counter=my_counter):
        pass

    rate = my_counter.rate()
    assert rate == pytest.approx(50, abs=1)


def test_duration_context_manager_mode(rand_offset, mock_timer):
    start, end = 1.4 + rand_offset, 2.65 + rand_offset
    mock_timer.side_effect = start, end

    with time.about() as at:
        pass

    assert at.duration == pytest.approx(end - start)


def test_duration_callable_mode(rand_offset, mock_timer):
    start, end = 1.4 + rand_offset, 2.65 + rand_offset
    mock_timer.side_effect = start, end

    at = time.about(lambda: 1)

    assert at.duration == pytest.approx(end - start)


def test_duration_counter_throughput_mode(rand_offset, mock_timer):
    start, end = 1.4 + rand_offset, 2.65 + rand_offset
    mock_timer.side_effect = start, end

    at = time.about(range(2))
    for _ in at:
        pass

    assert at.duration == pytest.approx(end - start)


@pytest.mark.parametrize(
    "call, args, kwargs, expected",
    [
        (lambda: 123, (), {}, 123),
        (str, (), {}, ""),
        (list, (), {}, []),
        (lambda x: x + 1, (123,), {}, 124),
        (str, ("cool",), {}, "cool"),
        (list, ((1, 2, 3),), {}, [1, 2, 3]),
        (lambda x: x + 1, (), {"x": 123}, 124),
    ],
)
def test_callable_mode_result(call, args, kwargs, expected):
    at = time.about(call, *args, **kwargs)
    assert at.result == expected


@pytest.mark.parametrize(
    "it",
    [
        [],
        [1, 2, 3],
        range(0),
        range(12),
        "string",
        (x**2 for x in range(8)),
    ],
)
def test_counter_throughput_mode(it, rand_offset, mock_timer):
    start, end = 1.4 + rand_offset, 2.65 + rand_offset
    mock_timer.side_effect = chain((start,), repeat(end))
    it_see, it_copy = tee(it)

    at = time.about(it_see)
    assert at.count == 0  # count should work even before starting iterating.

    i = 0
    for i, elem in enumerate(at, 1):
        assert elem == next(it_copy)
        assert at.count == i  # count works in real time now!
        assert at.duration > 0  # ensure the timing ending is also updated in real time.

    assert at.throughput == pytest.approx(i / 1.25)


@pytest.mark.parametrize(
    "field",
    [
        "result",
        "count",
        "count_human",
        "count_human_as",
        "throughput",
        "throughput_human",
        "throughput_human_as",
    ],
)
def test_context_manager_mode_dont_have_field(field):
    with time.about() as at:
        pass

    with pytest.raises(AttributeError):
        getattr(at, field)


@pytest.mark.parametrize(
    "field",
    [
        "count",
        "count_human",
        "count_human_as",
        "throughput",
        "throughput_human",
        "throughput_human_as",
    ],
)
def test_callable_mode_dont_have_field(field):
    at = time.about(lambda: 1)

    with pytest.raises(AttributeError):
        getattr(at, field)


@pytest.mark.parametrize(
    "field",
    [
        "result",
    ],
)
def test_counter_throughput_mode_dont_have_field(field):
    at = time.about(range(2))

    with pytest.raises(AttributeError):
        getattr(at, field)


@pytest.mark.parametrize(
    "value",
    [
        123,
        0.1,
        object(),
        datetime.now(),
        Decimal(),
    ],
)
def test_wrong_params_must_complain(value):
    with pytest.raises(UserWarning):
        time.about(value)


def test_handle_duration_human():
    from nob.time.about import Handle

    h = Handle([1, 2])
    assert h.duration_human.value == 1


def test_handle_count_human():
    from nob.time.about import HandleStats

    def it_closure():
        pass

    it_closure.count = 1  # ty:ignore[unresolved-attribute]
    h = HandleStats([1, 2], it_closure)
    assert h.count_human.value == 1


def test_handle_throughput_human():
    from nob.time.about import HandleStats

    def it_closure():
        pass

    it_closure.count = 1  # ty:ignore[unresolved-attribute]
    h = HandleStats([1, 2], it_closure)
    assert h.throughput_human.value == 1

import time

import pytest

from nob.utils.tick import tick

# Tick counting bellow 1*mean_over are less reliable
EPSILON = 8e-3  # Tolerances for sleep inaccuracy and slow test environments


def test_tick_iterator_timing():
    # rate = 20, interval = 0.05
    # 5 iterations (0 to 4) should pause 4 times
    # Target duration: 4 * 0.05 = 0.2 seconds
    start = time.perf_counter()
    for _ in tick(range(5), 20):
        pass
    end = time.perf_counter()
    duration = end - start
    assert duration == pytest.approx(0.2, abs=EPSILON)


def test_tick_standalone_timing():
    # rate = 20, interval = 0.05
    # 5 iterations should pause 4 times
    # Target duration: 4 * 0.05 = 0.2 seconds
    start = time.perf_counter()
    for _ in range(5):
        tick(20)
    end = time.perf_counter()
    duration = end - start
    assert duration == pytest.approx(0.2, abs=EPSILON)


def test_tick_standalone_distinct_loops():
    # Two independent loops where the second should not try to maintain cadence from the first
    for in_between_sleep in [0.0, 0.1, 0.2, 0.5]:
        # Loop 1: 5 iterations at 20Hz -> ~0.2s
        start1 = time.perf_counter()
        for _ in range(5):
            tick(20)
        end1 = time.perf_counter()

        # Simulate a pause between loops
        time.sleep(in_between_sleep)

        # Loop 2: 5 iterations at 20Hz -> ~0.2s
        # If the frame inspection trick failed, this loop might sleep an awkward amount
        # or skip sleeping entirely to "catch up" instantly. We want consistent timing.
        start2 = time.perf_counter()
        for _ in range(5):
            tick(20)
        end2 = time.perf_counter()

        duration1 = end1 - start1
        duration2 = end2 - start2

        assert duration1 == pytest.approx(0.2, abs=EPSILON)
        assert duration2 == pytest.approx(0.2, abs=EPSILON)


def test_tick_long_workload():
    # When business logic takes longer than the interval, tick should fall behind and
    # not double-sleep, resulting in purely the duration of the workload
    start = time.perf_counter()
    for _ in range(3):
        tick(20)  # interval = 0.05
        time.sleep(0.08)  # Takes longer than the interval
    end = time.perf_counter()
    duration = end - start

    # 3 iterations. Inter-tick sleep wouldn't happen because workload takes longer.
    # Total time should just be 3 * 0.08 = 0.24 seconds + setup time.
    assert duration == pytest.approx(0.24, abs=EPSILON)


def test_tick_counter_rate():
    # Loop 15 times at 50Hz, takes ~0.3s
    # The rate counter should be approximately 50
    for _ in tick(range(16), 50):
        pass
    rate = tick.counter.rate()  # ty:ignore[unresolved-attribute]
    assert rate == pytest.approx(50, abs=1)  # Allow some more tolerance

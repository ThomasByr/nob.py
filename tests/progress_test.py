import pytest
from pytest import CaptureFixture

from nob import progress


@pytest.fixture
def run_progress(capsys: CaptureFixture[str]):
    """Helper to run progress in either mode and capture the output."""

    def _run(
        mode: str,
        sequence_len: int = 1,
        description: str = "Working...",
        total: float | int | None = -1,
        show_percentage: bool = False,
        hide_time: bool = False,
        hide_processing_speed: bool = False,
        human_format: bool = True,
        unit: str = "",
    ):

        if mode == "track":
            kwargs = {
                "description": description,
                "show_percentage": show_percentage,
                "hide_time": hide_time,
                "hide_processing_speed": hide_processing_speed,
                "human_format": human_format,
                "unit": unit,
            }
            if total != -1:
                kwargs["total"] = total  # ty:ignore[invalid-assignment]

            for _ in progress.track(range(sequence_len), **kwargs):  # ty:ignore[invalid-argument-type]
                pass
        else:
            known_total = total is not None
            bar = progress.progress(
                known_total=known_total,
                show_percentage=show_percentage,
                hide_time=hide_time,
                hide_processing_speed=hide_processing_speed,
                human_format=human_format,
                unit=unit,
            )
            task_total = sequence_len if total == -1 else total
            task = bar.add_task(description, total=task_total)
            with bar:
                if sequence_len > 0:
                    bar.advance(task, sequence_len)

        return capsys.readouterr().out

    return _run


@pytest.mark.parametrize("mode", ["track", "progress"])
@pytest.mark.parametrize("description", ["Working...", "Custom description", "Epoch 1/5"])
def test_descriptions(run_progress, mode, description):
    out = run_progress(mode, description=description)
    assert description in out


@pytest.mark.parametrize("mode", ["track", "progress"])
@pytest.mark.parametrize(
    "sequence_len, total, show_percentage, expected_in, expected_not_in",
    [
        # Auto/Default total
        (19, -1, False, ["19/19"], ["%"]),
        (35, -1, False, ["35/35"], ["%"]),
        # Explicit known total
        (1, 123, False, ["1/123"], ["%"]),
        (42, 121, False, ["42/121"], ["%"]),
        # Unknown total
        (700, None, False, ["700"], ["700/", "%"]),
        (42, None, False, ["42"], ["42/", "%"]),
        # With percentage - known total
        (42, -1, True, ["100.00%"], ["42/"]),
        (7, 7, True, ["100.00%"], ["7/"]),
        (1, 7, True, ["14.29%"], ["1/"]),
        (2, 4, True, ["50.00%"], ["2/"]),
        # With percentage - unknown total
        (42, None, True, ["100.00%"], ["42/"]),
    ],
)
def test_total_and_percentages(
    run_progress, mode, sequence_len, total, show_percentage, expected_in, expected_not_in
):
    out = run_progress(mode, sequence_len=sequence_len, total=total, show_percentage=show_percentage)

    # Handle special case where indeterminate progress bar percentage defaults to 0
    if mode == "progress" and total is None and show_percentage:
        assert "0.00%" in out
        assert "42/" not in out
        return

    for expected in expected_in:
        assert expected in out
    for not_in in expected_not_in:
        assert not_in not in out


@pytest.mark.parametrize("mode", ["track", "progress"])
@pytest.mark.parametrize(
    "hide_time, expected_in, expected_not_in",
    [
        (True, [], ["•"]),
        (False, ["•"], []),
    ],
)
def test_hide_time(run_progress, mode, hide_time, expected_in, expected_not_in):
    out = run_progress(mode, sequence_len=42, hide_time=hide_time)
    for expected in expected_in:
        assert expected in out
    for not_in in expected_not_in:
        assert not_in not in out


@pytest.mark.parametrize("mode", ["track", "progress"])
@pytest.mark.parametrize(
    "hide_processing_speed, expected_in, expected_not_in",
    [
        (True, [], ["it/s", "it/m"]),  # Hides speed text entirely
        (False, ["it/"], []),  # Leaves the throughput suffix
    ],
)
def test_hide_processing_speed(run_progress, mode, hide_processing_speed, expected_in, expected_not_in):
    out = run_progress(mode, sequence_len=42, hide_processing_speed=hide_processing_speed, unit="it")
    for expected in expected_in:
        assert expected in out
    for not_in in expected_not_in:
        assert not_in not in out


@pytest.mark.parametrize("mode", ["track", "progress"])
@pytest.mark.parametrize(
    "sequence_len, total, human_format, unit, expected_in, expected_not_in",
    [
        # With human formatting, unit is appended and numbers are simplified
        (2500, -1, True, "req", ["2.5kreq/2.5kreq", "req/s"], ["2500req/2500req", "2500/2500"]),

        # Without human_format, numbers strictly use completed/total formatting but keep the unit
        (2500, -1, False, "req", ["2500req/2500req", "req/s"], ["2.5kreq"]),

        # Human format enabled, no unit provided
        (1000, -1, True, "", ["1k/1k"], ["1000/1000"]),

        # Human format disabled, no unit provided
        (1000, -1, False, "", ["1000/1000", "/s"], ["1k"]),

        # Unknown total with human formatting
        (4500, None, True, "B", ["4.5kB"], ["4500B", "4.5kB/"]),

        # Unknown total without human formatting
        (4500, None, False, "B", ["4500B"], ["4.5kB", "4500B/"]),
    ],
)
def test_human_formatting_and_units(run_progress, mode, sequence_len, total, human_format, unit, expected_in, expected_not_in):
    out = run_progress(mode, sequence_len=sequence_len, total=total, human_format=human_format, unit=unit)
    for expected in expected_in:
        assert expected in out
    for not_in in expected_not_in:
        assert not_in not in out

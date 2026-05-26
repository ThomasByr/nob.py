import unittest.mock

import pytest
from pytest import CaptureFixture
from rich._spinners import SPINNERS

import nob.status


@pytest.fixture
def mock_terminal():
    """Emulate an interactive terminal so rich Status actually renders and outputs ANSI."""
    with unittest.mock.patch("sys.stdout.isatty", return_value=True):
        yield


@pytest.mark.parametrize(
    "text, spinner, expected_in",
    [
        ("Loading...", "dots", "Loading..."),
        ("Processing data...", "bouncingBar", "Processing data..."),
        ("Custom status", "line", "Custom status"),
    ],
)
def test_status_new_context_manager(capsys: CaptureFixture[str], mock_terminal, text, spinner, expected_in):
    status = nob.status.new(text=text, spinner=spinner)

    # We must set transient=False so rich doesn't erase the terminal on exit,
    # allowing capsys to safely capture the terminal output block.
    status._live.transient = False

    with status:
        pass

    out = capsys.readouterr().out
    assert expected_in in out


@pytest.mark.parametrize(
    "initial_text, update_kwargs, expected_in",
    [
        ("Start...", {"text": "Finished"}, "Finished"),
        ("Data 1", {"text": "Data 2"}, "Data 2"),
    ],
)
def test_status_update_global(
    capsys: CaptureFixture[str], mock_terminal, initial_text, update_kwargs, expected_in
):
    status = nob.status.new(text=initial_text)
    status._live.transient = False

    with status:
        nob.status.update(**update_kwargs)

    out = capsys.readouterr().out
    assert expected_in in out


def test_status_update_specific(capsys: CaptureFixture[str], mock_terminal):
    status = nob.status.new(text="Worker 1")
    status._live.transient = False

    with status:
        nob.status.update_status(status, text="Worker 1 Done")

    out = capsys.readouterr().out
    assert "Worker 1 Done" in out
    assert "Worker 1" in out


def test_status_imperative_start_stop(capsys: CaptureFixture[str], mock_terminal):
    status = nob.status.new(text="Imperative Mode")
    status._live.transient = False

    nob.status.start()
    # Emulate work here if desired
    nob.status.stop()

    out = capsys.readouterr().out
    assert "Imperative Mode" in out


@pytest.mark.parametrize(
    "invalid_spinner",
    [
        "not_a_real_spinner",
        "___invalid___",
        "",
    ],
)
def test_invalid_spinner_raises_value_error(invalid_spinner):
    with pytest.raises(ValueError, match="Invalid spinner"):
        nob.status.new(spinner=invalid_spinner)


@pytest.mark.parametrize("spinner", list(SPINNERS.keys()))
def test_all_valid_spinners(capsys: CaptureFixture[str], mock_terminal, spinner):
    status = nob.status.new(text=f"Testing {spinner}", spinner=spinner)
    status._live.transient = False

    with status:
        pass

    out = capsys.readouterr().out
    assert f"Testing {spinner}" in out

    frames: list[str] | str = SPINNERS[spinner]["frames"]  # ty:ignore[invalid-assignment]
    # Frames can be a string of characters or a list of strings
    if isinstance(frames, str):
        frame_list = list(frames)
    else:
        frame_list = frames

    assert any(frame in out for frame in frame_list), f"No frame from spinner '{spinner}' found in output."


def test_update_status_raises_value_error_for_invalid_spinner():
    status = nob.status.new()
    with pytest.raises(ValueError, match="Invalid spinner"):
        nob.status.update_status(status, spinner="does_not_exist")

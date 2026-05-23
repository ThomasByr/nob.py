from pytest import CaptureFixture

from nob.progress import progress, track


def test_default_description(capsys: CaptureFixture[str]):
    for _ in track(range(1)):
        pass
    captured = capsys.readouterr()
    assert captured.out.startswith("Working...")


def test_set_description(capsys: CaptureFixture[str]):
    d0 = "Some non-default description"
    d1 = "Some other description text"

    for _ in track(range(1), d0):
        pass
    captured = capsys.readouterr()
    assert captured.out.startswith(d0)

    bar = progress()
    task = bar.add_task(d1)
    with bar:
        bar.advance(task)
    captured = capsys.readouterr()
    assert captured.out.startswith(d1)


def test_set_total(capsys: CaptureFixture[str]):
    for _ in track(range(1), total=123):
        pass
    captured = capsys.readouterr()
    assert "1/123" in captured.out

    bar = progress()
    task = bar.add_task("", total=7)
    with bar:
        bar.advance(task)
    captured = capsys.readouterr()
    assert "1/7" in captured.out


def test_no_known_total(capsys: CaptureFixture[str]):
    for _ in track(range(42), total=None):
        pass
    captured = capsys.readouterr()
    assert "42" in captured.out and "42/" not in captured.out

    bar = progress(known_total=False)
    task = bar.add_task("", total=None)
    with bar:
        bar.advance(task, 700)
    captured = capsys.readouterr()
    assert "700" in captured.out and "700/" not in captured.out


def test_auto_total(capsys: CaptureFixture[str]):
    for _ in track(range(19)):
        pass
    captured = capsys.readouterr()
    assert "19/19" in captured.out

    for _ in track(range(35)):
        pass
    captured = capsys.readouterr()
    assert "35/35" in captured.out


def test_show_percentage(capsys: CaptureFixture[str]):
    for _ in track(range(42), show_percentage=True):
        pass
    captured = capsys.readouterr()
    assert "100.00%" in captured.out

    bar = progress(show_percentage=True)
    task = bar.add_task("", total=7)
    with bar:
        bar.advance(task)
    captured = capsys.readouterr()
    assert "14.29%" in captured.out

    for _ in track(range(42), total=None, show_percentage=True):
        pass
    captured = capsys.readouterr()
    assert "100.00%" in captured.out

    for _ in track(range(42), total=None, show_percentage=False):
        pass
    captured = capsys.readouterr()
    assert "42" in captured.out and "%" not in captured.out

    for _ in track(range(42), total=121, show_percentage=False):
        pass
    captured = capsys.readouterr()
    assert "42/121" in captured.out and "%" not in captured.out


def test_hide_time(capsys: CaptureFixture[str]):
    for _ in track(range(42), hide_time=True):
        pass
    captured = capsys.readouterr()
    assert "•" not in captured.out

    bar = progress(hide_time=True)
    task = bar.add_task("")
    with bar:
        bar.advance(task)
    captured = capsys.readouterr()
    assert "•" not in captured.out

    for _ in track(range(42), hide_time=False):
        pass
    captured = capsys.readouterr()
    assert "•" in captured.out


def test_hide_processing_speed(capsys: CaptureFixture[str]):
    for _ in track(range(42), hide_processing_speed=True):
        pass
    captured = capsys.readouterr()
    assert "it/s" not in captured.out

    bar = progress(hide_processing_speed=True)
    task = bar.add_task("")
    with bar:
        bar.advance(task)
    captured = capsys.readouterr()
    assert "it/s" not in captured.out

    for _ in track(range(42), hide_processing_speed=False):
        pass
    captured = capsys.readouterr()
    assert "it/s" in captured.out

from rich._spinners import SPINNERS
from rich.status import Status
from rich.style import Style

__all__ = ["new", "update", "update_status", "start", "stop"]


__GLOBAL_STATUS: Status | None = None


def __check_spinner(spinner: str) -> None:
    if spinner not in SPINNERS:
        raise ValueError(f"Invalid spinner: {spinner!r}. Valid options are: {', '.join(SPINNERS.keys())}")


def new(
    text: str = "Loading...",
    spinner: str = "dots",
    style: str | Style = "status.spinner",
    refresh_per_second: float = 12.5,
    speed_factor: float = 1.0,
) -> Status:
    """Create a status and set it as the global.

    Args:
        text: The text to display in the status. Defaults to "Loading...".
        spinner: The spinner to use. Defaults to "dots".
        style: The style of the status text. Defaults to "status.spinner".
        refresh_per_second: The number of times to refresh the status per second. Defaults to 12.5.
        speed_factor: The factor by which to adjust the speed of the spinner. Defaults to 1.0.

    Returns:
        Status: The created status object.
    """
    global __GLOBAL_STATUS
    __check_spinner(spinner)
    status = Status(
        text,
        spinner=spinner,
        spinner_style=style,
        refresh_per_second=refresh_per_second,
        speed=speed_factor,
    )
    __GLOBAL_STATUS = status
    return status


def update(
    text: str | None = None,
    spinner: str | None = None,
    style: str | Style | None = None,
    speed_factor: float | None = None,
) -> None:
    """Update the global status if it exists.\\
    To update a given status, call the `.update` method on the status returned from `new()` itself instead of this function.

    Args:
        text: The new text to display in the status. If None, the text will not be updated.
        spinner: The new spinner to use. If None, the spinner will not be updated.
        style: The new style of the status text. If None, the style will not be updated.
        speed_factor: The new factor by which to adjust the speed of the spinner. If None, the speed factor will not be updated.
    """
    global __GLOBAL_STATUS
    if __GLOBAL_STATUS is not None:
        update_status(
            __GLOBAL_STATUS,
            text=text,
            spinner=spinner,
            style=style,
            speed_factor=speed_factor,
        )


def update_status(
    status: Status,
    text: str | None = None,
    spinner: str | None = None,
    style: str | Style | None = None,
    speed_factor: float | None = None,
) -> None:
    """Update a given status.\\
    Alias for calling the `.update` method on the status itself, but with added validation for the spinner argument.

    Args:
        status: The status to update.
        text: The new text to display in the status. If None, the text will not be updated.
        spinner: The new spinner to use. If None, the spinner will not be updated.
        style: The new style of the status text. If None, the style will not be updated.
        speed_factor: The new factor by which to adjust the speed of the spinner. If None, the speed factor will not be updated.
    """
    assert isinstance(status, Status) and status is not None
    if spinner is not None:
        __check_spinner(spinner)
    status.update(
        status=text,
        spinner=spinner,
        spinner_style=style,
        speed=speed_factor,
    )


def start():
    """Start the global status if it exists.\\
    Preferred method is to use a context manager with the status returned from `new()`, which will automatically start and stop the status.
    """
    global __GLOBAL_STATUS
    if __GLOBAL_STATUS is not None:
        __GLOBAL_STATUS.start()


def stop():
    """Stop the global status if it exists."""
    global __GLOBAL_STATUS
    if __GLOBAL_STATUS is not None:
        __GLOBAL_STATUS.stop()

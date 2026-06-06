import logging
from logging.handlers import RotatingFileHandler

from rich.logging import RichHandler

__all__ = ["init_handler", "mute_logger"]


def mute_logger(*names: str) -> None:
    """Mute the specified logger by setting its level to WARNING.

    Args:
        names (str): The names of the logger to mute.
    """
    for name in names:
        logger = logging.getLogger(name)
        logger.setLevel(logging.WARNING)
        logger.propagate = False  # prevent logs from propagating to root logger


def init_handler(
    log_level: int = logging.INFO,
    log_file: str | None = None,
    max_bytes: int | None = None,
    backup_count: int | None = None,
) -> None:
    """Initialize logging handlers for the application.

    Args:
        log_level (int, optional): The logging level to set. Defaults to logging.INFO.
        log_file (str, optional): The path where logs will be written (using `RotatingFileHandler`). If None, logs will not be written to a file.
        max_bytes (int, optional): The maximum size of the log file before it is rotated. Defaults to 10 MB per file.
        backup_count (int, optional): The number of backup log files to keep. Defaults to 5.
    """
    if isinstance(max_bytes, int) and max_bytes < 0:
        raise ValueError("max_bytes must be a positive integer")
    if isinstance(backup_count, int) and backup_count < 0:
        raise ValueError("backup_count must be a positive integer")
    handlers: list = [RichHandler()]  # modifies the record first for RotatingFileHandler
    max_bytes = max_bytes if max_bytes is not None else 10 * 1024 * 1024
    backup_count = backup_count if backup_count is not None else 5
    if log_file:
        handlers.append(RotatingFileHandler(log_file, maxBytes=max_bytes, backupCount=backup_count))
    logging.basicConfig(
        level=log_level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=handlers,
        force=True,
    )

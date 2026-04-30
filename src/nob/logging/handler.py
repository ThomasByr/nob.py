import logging
from logging.handlers import RotatingFileHandler

from rich.logging import RichHandler

__all__ = ["init_handler"]


def mute_logger(*names: str) -> None:
    """Mute the specified logger by setting its level to WARNING.

    Args:
        name (str): The name of the logger to mute.
    """
    log = logging.getLogger("mute_logger")
    for name in names:
        log.debug("Muting logger: %s", name)
        logger = logging.getLogger(name)
        logger.setLevel(logging.WARNING)
        logger.propagate = False  # prevent logs from propagating to root logger


def init_handler(log_level: int = logging.INFO, log_file: str | None = None):
    """Initialize logging handlers for the application.

    Args:
        log_level (int, optional): The logging level to set. Defaults to logging.INFO.
        log_file (str, optional): The path where logs will be written. If None, logs will not be written to a file.
    """
    handlers: list = [RichHandler()]  # modifies the record first for RotatingFileHandler
    if log_file:
        handlers.append(RotatingFileHandler(log_file, maxBytes=1024 * 1024 * 100, backupCount=5))
    logging.basicConfig(
        level=log_level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=handlers,
        force=True,
    )

    # mute overly verbose loggers
    mute_logger("urllib3", "rich")

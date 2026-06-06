import logging
from collections.abc import Callable
from logging import Logger  # noqa: F401
from typing import ParamSpec, TypeVar

import rich_click as click
from rich_click import Context  # noqa: F401

from . import types  # noqa: F401
from .config import AliasedGroup, CLIMutex, Config, pass_config

all = ["opt", "cmd", "grp", "pass_config", "pass_context", "types", "Logger", "Context", "Config"]

P = ParamSpec("P")
Q = ParamSpec("Q")
R = TypeVar("R")
S = TypeVar("S")


def __read_config(ctx: click.Context, _, value: str | None):
    """Callback that is used whenever Config is passed. We use this to always
    load the correct config. This means that the config is loaded even if the
    group itself never executes so everything always stays available.
    """
    cfg = ctx.ensure_object(Config)
    cfg.read_config(value)
    return value


def __read_log_file(ctx: click.Context, _, value: str | None):
    cfg = ctx.ensure_object(Config)
    if value:
        cfg.log_file = value
    return value


def __read_verbosity(level: int):

    def callback(ctx: click.Context, _, value: bool):
        cfg = ctx.ensure_object(Config)
        if value:
            cfg.log_level = level
        return value

    return callback


def __read_log_file_max_bytes(ctx: click.Context, _, value: int | None):
    cfg = ctx.ensure_object(Config)
    if value is not None:
        cfg.log_file_max_bytes = value
    return value


def __read_log_file_backup_count(ctx: click.Context, _, value: int | None):
    cfg = ctx.ensure_object(Config)
    if value is not None:
        cfg.log_file_backup_count = value
    return value


def __install_rich_traceback():
    import os

    from rich.traceback import install

    DEBUG_TRACE = os.environ.get("DEBUG_TRACE", "0") == "1"

    extra_lines = 3 if DEBUG_TRACE else 0
    max_frames = 100 if DEBUG_TRACE else 1
    show_locals = DEBUG_TRACE

    install(
        show_locals=show_locals,
        extra_lines=extra_lines,
        max_frames=max_frames,
        suppress=["click", "rich"],
    )


def __add_config_options(grp: click.RichGroup | None):
    return (
        [
            click.option(
                "-v",
                "--verbose",
                is_flag=True,
                help="Enable verbose logging (DEBUG min level).",
                callback=__read_verbosity(logging.DEBUG),
                expose_value=False,
                cls=CLIMutex,
                not_required_if=["quiet"],
            ),
            click.option(
                "-q",
                "--quiet",
                is_flag=True,
                help="Enable quiet logging (WARNING min level).",
                callback=__read_verbosity(logging.WARNING),
                expose_value=False,
                cls=CLIMutex,
                not_required_if=["verbose"],
            ),
            click.option(
                "-c",
                "--config",
                type=click.Path(exists=True, dir_okay=False),
                help="Path to a custom config file to load instead of the default (defaults to assets/cfg/default.yml).",
                callback=__read_config,
                expose_value=False,
            ),
            click.option(
                "-l",
                "--log-file",
                type=click.Path(dir_okay=False),
                help="Specify the path where the RotatingFileHandler will write its outputs.",
                callback=__read_log_file,
                expose_value=False,
            ),
            click.option(
                "--log-file-max-bytes",
                type=int,
                help="The maximum size of the log file before it is rotated. Defaults to 10 MB per file.",
                callback=__read_log_file_max_bytes,
                expose_value=False,
            ),
            click.option(
                "--log-file-backup-count",
                type=int,
                help="The number of backup log files to keep. Defaults to 5.",
                callback=__read_log_file_backup_count,
                expose_value=False,
            ),
        ]
        if grp is None
        else []
    )


def __preserve_click_params(func: Callable[P, R], wrapper: Callable[Q, S]):
    """Modifies the wrapper function in-place to have the same Click parameters as the original function.\\
    It ensures that the decorators can be used in any order without breaking the underlying Click parameters.

    Args:
        func (Callable[P, R]): The original function with the correct Click parameters.
        wrapper (Callable[Q, S]): The wrapper function that needs to have the Click parameters of the original function.

    Returns:
        Callable[Q, S]: wrapper (so that this function can be nicely chained)
    """
    # https://stackoverflow.com/q/57773853#comment101986419_57773853
    if hasattr(func, "__click_params__"):
        assert isinstance(func.__click_params__, list)
        # Actually creates the attribute on the wrapper if it doesn't exist
        wrapper.__click_params__ = func.__click_params__  # ty:ignore[unresolved-attribute]
    return wrapper


def __set_config_on_function(func: Callable, cfg: Config):
    """Sets the config on the function so that it can be accessed by other decorators without needing to pass it through the parameters.

    Args:
        func (Callable): The function to set the config on.
        cfg (Config): The config to set on the function.
    """
    setattr(func, "__nob_cli_config", cfg)


def __get_config_from_function(func: Callable) -> Config | None:
    """Gets the config from the function if it exists. This is useful for example for the grp decorator to have access to the config without needing to pass it through the parameters.

    Args:
        func (Callable): The function to get the config from.

    Returns:
        Config | None: The config if it exists, otherwise None.
    """
    return getattr(func, "__nob_cli_config", None)


def __merge_configs(parent_cfg: Config, child_cfg: Config) -> Config:
    """Merges the parent config with the child config. The child config takes precedence over the parent config.

    Args:
        parent_cfg (Config): The parent config.
        child_cfg (Config): The child config.

    Returns:
        Config: The merged config.
    """
    merged = Config()
    merged.aliases = {**parent_cfg.aliases, **child_cfg.aliases}
    merged.log_level = child_cfg.log_level if child_cfg.log_level != logging.INFO else parent_cfg.log_level
    merged.log_file = child_cfg.log_file or parent_cfg.log_file
    merged.log_file_max_bytes = (
        child_cfg.log_file_max_bytes
        if child_cfg.log_file_max_bytes is not None
        else parent_cfg.log_file_max_bytes
    )
    merged.log_file_backup_count = (
        child_cfg.log_file_backup_count
        if child_cfg.log_file_backup_count is not None
        else parent_cfg.log_file_backup_count
    )
    return merged


def grp(
    grp: click.RichGroup | None = None,
    default: Callable[[], click.RichCommand] | None = None,
    *default_args,
    **default_kwargs,
) -> click.RichGroup:
    """Registers the decorated function as a Click group and adds the common options to it.\\
    Please provide default arguments (that don't have defaults defined) since you won't be able to do so in the CLI.

    Args:
        grp (click.RichGroup, optional): Parent group to attach the group to. Defaults to None.
        default (() -> RichCommand, optional): Factory of the default command to run if nothing is passed. Defaults to None.
        *default_args (): Default arguments.
        **default_kwargs (): Default named arguments.
    """

    entity = grp or click

    def inner(main: Callable[P, R]):
        dec = (
            [
                entity.group(
                    name=main.__name__,  # ty:ignore[unresolved-attribute]
                    help=main.__doc__,
                    cls=AliasedGroup,
                    context_settings={"help_option_names": ["-h", "--help"]},
                    invoke_without_command=default is not None,
                )
            ]
            + __add_config_options(grp)
            + [
                click.pass_context,
            ]
        )

        def wrapper(ctx: click.Context, *args, **kwargs):
            if default is not None and ctx.invoked_subcommand is None:
                ctx.forward(default(), *default_args, **default_kwargs)
            return main(*args, **kwargs)

        __preserve_click_params(main, wrapper)
        for d in reversed(dec):
            wrapper = d(wrapper)
        return wrapper

    return inner  # ty:ignore[invalid-return-type]


def cmd(
    grp: click.RichGroup | None = None,
    log_file: str | None = None,
    log_file_max_bytes: int | None = None,
    log_file_backup_count: int | None = None,
) -> click.RichCommand:
    """Decorator to create a command. Can be attached to a group.\\
    Adds the following parameters to the command if they are present in the function signature or if the function accepts `**kwargs`:
    - `cfg`: The Config object `nob.cli.Config`
    - `ctx`: The Click context object `nob.cli.Context` (alias for `rich_click.Context`)
    - `lg`: A logger with the name of the command `nob.cli.Logger` (alias for `logging.Logger`)

    Args:
        grp (click.RichGroup, optional): Parent group to attach the command to. Defaults to None.
        log_file (str | None, optional): The path where the RotatingFileHandler will write its outputs. Defaults to None. Can be set via the CLI with `--log-file`.
        log_file_max_bytes (int | None, optional): The maximum size of the log file before it is rotated. Defaults to 10 MB per file. Can be set via the CLI with `--log-file-max-bytes`.
        log_file_backup_count (int | None, optional): The number of backup log files to keep. Defaults to 5. Can be set via the CLI with `--log-file-backup-count`.
    """
    entity = grp or click

    def inner(func: Callable[P, R]):
        dec = (
            [
                entity.command(
                    name=(name := func.__name__),  # ty:ignore[unresolved-attribute]
                    help=func.__doc__,
                    context_settings={"help_option_names": ["-h", "--help"]},
                ),
            ]
            + __add_config_options(grp)
            + [
                click.pass_context,
                pass_config,
            ]
        )

        def wrapper(cfg: Config, ctx: click.Context, **kwargs):
            import inspect

            from nob.logging import init_handler

            lg = logging.getLogger(name)
            config_from_command = __get_config_from_function(inner)
            if config_from_command:
                cfg = __merge_configs(config_from_command, cfg)
            init_handler(cfg.log_level, cfg.log_file, cfg.log_file_max_bytes, cfg.log_file_backup_count)

            sig = inspect.signature(func)
            has_kwargs = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())

            kw = dict(kwargs)
            if has_kwargs or "cfg" in sig.parameters:
                kw["cfg"] = cfg
            if has_kwargs or "ctx" in sig.parameters:
                kw["ctx"] = ctx
            if has_kwargs or "lg" in sig.parameters:
                kw["lg"] = lg

            return func(**kw)  # ty:ignore[missing-argument]

        __preserve_click_params(func, wrapper)
        for d in reversed(dec):
            wrapper = d(wrapper)
        return wrapper

    __set_config_on_function(
        inner,
        Config(
            log_file=log_file,
            log_file_max_bytes=log_file_max_bytes,
            log_file_backup_count=log_file_backup_count,
        ),
    )
    __install_rich_traceback()
    return inner  # ty:ignore[invalid-return-type]


opt = click.option
arg = click.argument


def pass_context(func):
    return click.pass_context(func)

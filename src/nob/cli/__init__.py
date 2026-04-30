import logging
from collections.abc import Callable
from typing import ParamSpec, TypeVar

import rich_click as click

from .config import AliasedGroup, CLIMutex, Config, pass_config

all = ["opt", "cmd", "grp", "pass_config", "pass_context"]

P = ParamSpec("P")
R = TypeVar("R")


def read_config(ctx: click.Context, _, value: str | None):
    """Callback that is used whenever Config is passed. We use this to always
    load the correct config. This means that the config is loaded even if the
    group itself never executes so everything always stays available.
    """
    cfg = ctx.ensure_object(Config)
    cfg.read_config(value)
    return value


def read_log_file(ctx: click.Context, _, value: str | None):
    cfg = ctx.ensure_object(Config)
    if value:
        cfg.log_file = value
    return value


def read_verbosity(level: int):

    def callback(ctx: click.Context, _, value: bool):
        cfg = ctx.ensure_object(Config)
        if value:
            cfg.log_level = level
        return value

    return callback


def grp(main: Callable[P, R]) -> click.RichGroup:
    """Registers the decorated function as a Click group and adds the common options to it."""
    dec = [
        click.group(cls=AliasedGroup, context_settings={"help_option_names": ["-h", "--help"]}),
        click.option(
            "-v",
            "--verbose",
            is_flag=True,
            help="Enable verbose logging (DEBUG level).",
            callback=read_verbosity(logging.DEBUG),
            expose_value=False,
            cls=CLIMutex,
            not_required_if=["quiet"],
        ),
        click.option(
            "-q",
            "--quiet",
            is_flag=True,
            help="Enable quiet logging (WARNING level).",
            callback=read_verbosity(logging.WARNING),
            expose_value=False,
            cls=CLIMutex,
            not_required_if=["verbose"],
        ),
        click.option(
            "-c",
            "--config",
            type=click.Path(exists=True, dir_okay=False),
            help="Path to a custom config file to load instead of the default (defaults to assets/cfg/default.yml).",
            callback=read_config,
            expose_value=False,
        ),
        click.option(
            "-l",
            "--log-file",
            type=click.Path(dir_okay=False),
            help="Specify the path where the RotatingFileHandler will write its outputs.",
            callback=read_log_file,
            expose_value=False,
        ),
    ]

    def wrapper(*args, **kwargs):
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
        return main(*args, **kwargs)

    for d in reversed(dec):
        wrapper = d(wrapper)  # ty:ignore
    return wrapper  # ty:ignore


def cmd(grp: click.RichGroup):
    """Decorator to create a command with the given group.\\
    Adds the following parameters to the command if they are present in the function signature or if the function accepts `**kwargs`:
    - `cfg`: The Config object `nob.cli.config.Config`
    - `ctx`: The Click context object `click.Context`
    - `lg`: A logger with the name of the command `logging.Logger`
    """

    def wrapper(func: Callable[P, R]):
        @grp.command(
            name=(name := func.__name__),  # ty:ignore
            help=func.__doc__,
        )
        @click.pass_context
        @pass_config
        def runner(cfg: Config, ctx: click.Context, **kwargs):
            import inspect

            from nob.logging.handler import init_handler

            lg = logging.getLogger(name)
            init_handler(cfg.log_level, cfg.log_file)

            sig = inspect.signature(func)
            has_kwargs = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())

            kw = dict(kwargs)
            if has_kwargs or "cfg" in sig.parameters:
                kw["cfg"] = cfg
            if has_kwargs or "ctx" in sig.parameters:
                kw["ctx"] = ctx
            if has_kwargs or "lg" in sig.parameters:
                kw["lg"] = lg

            return func(**kw)  # ty:ignore

        return runner

    return wrapper


opt = click.option
arg = click.argument


def pass_context(func):
    return click.pass_context(func)

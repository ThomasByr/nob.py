import rich_click as click

from .config import AliasedGroup, pass_config  # noqa: F401

all = ["group", "pass_config", "pass_context"]


def group(func):
    return click.group(cls=AliasedGroup, context_settings={"help_option_names": ["-h", "--help"]})(func)


def pass_context(func):
    return click.pass_context(func)

import logging
import os
from typing import Any

import rich_click as click
import yaml
from pydantic import BaseModel, Field
from typing_extensions import override

__all__ = ["AliasedGroup", "Config", "pass_config", "CLIMutex"]


class Config(BaseModel):
    """The config."""

    DEFAULT_CONFIG_PATH: str = os.path.join("assets", "cfg", "default.yml")

    aliases: dict[str, str] = Field(default_factory=dict)
    log_level: int = logging.INFO
    log_file: str | None = None

    def add_alias(self, alias: str, cmd: str):
        self.aliases[alias] = cmd

    def read_config(self, filename: str | None):
        try:
            with open(self.DEFAULT_CONFIG_PATH) as f:
                config_data: dict[str, Any] = yaml.safe_load(f) or {}
        except FileNotFoundError:
            config_data = {}
        if filename and os.path.abspath(filename) != os.path.abspath(self.DEFAULT_CONFIG_PATH):
            with open(filename) as f:
                user_config = yaml.safe_load(f)
                if user_config:
                    config_data.update(user_config)

        if not config_data:
            return

        # aliases
        self.aliases.update(config_data.get("aliases", {}))

        # options
        options: dict[str, Any] = config_data.get("options", {})  # noqa: F841


pass_config = click.make_pass_decorator(Config, ensure=True)


class AliasedGroup(click.RichGroup):
    """Aliased rich-click.Group"""

    @override
    def get_command(self, ctx, cmd_name):
        rv = click.Group.get_command(self, ctx, cmd_name)
        if rv is not None:
            return rv

        cfg = ctx.ensure_object(Config)

        if cmd_name in cfg.aliases:
            actual_cmd = cfg.aliases[cmd_name]
            return click.Group.get_command(self, ctx, actual_cmd)

        matches = [x for x in self.list_commands(ctx) if x.lower().startswith(cmd_name.lower())]
        if not matches:
            return None
        elif len(matches) == 1:
            return click.Group.get_command(self, ctx, matches[0])
        ctx.fail(f"Too many matches: {', '.join(sorted(matches))}")

    @override
    def resolve_command(self, ctx, args):
        _, cmd, args = super().resolve_command(ctx, args)
        assert cmd is not None
        return cmd.name, cmd, args


class CLIMutex(click.Option):
    def __init__(self, *args, **kwargs):
        self.not_required_if: list = kwargs.pop("not_required_if")

        assert self.not_required_if, "'not_required_if' parameter required"
        help = f"{h} " if (h := kwargs.get("help", "")) else ""
        kwargs["help"] = f"{help}Mutually exclusive with {', '.join(self.not_required_if)}.".strip()
        super().__init__(*args, **kwargs)

    @override
    def handle_parse_result(self, ctx, opts, args):
        current_opt: bool = self.name in opts
        for mutex_opt in self.not_required_if:
            if mutex_opt in opts:
                if current_opt:
                    raise click.UsageError(
                        "Illegal usage: '"
                        + str(self.name)
                        + "' is mutually exclusive with "
                        + str(mutex_opt)
                        + "."
                    )
                else:
                    self.prompt = None
        return super().handle_parse_result(ctx, opts, args)

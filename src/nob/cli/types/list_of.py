from typing import Generic, TypeVar

import rich_click as click

__all__ = ["ListOf"]

T = TypeVar("T")


class ListOf(click.ParamType, Generic[T]):
    """A click parameter type that parses a comma-separated string into a list
    of a given inner type (e.g. ListOf(int), ListOf(float))."""

    name = "list"

    def __init__(self, inner_type: type):
        self.inner_type = inner_type

    def convert(self, value, param, ctx) -> list[T] | None:
        if value is None:
            return None

        # Already converted (e.g. default value is already a list)
        if isinstance(value, list):
            return value

        parts = [p.strip() for p in value.split(",")]
        try:
            return [self.inner_type(p) for p in parts]
        except (ValueError, TypeError) as e:
            self.fail(f"Could not convert {value!r} to list of {self.inner_type.__name__}: {e}", param, ctx)

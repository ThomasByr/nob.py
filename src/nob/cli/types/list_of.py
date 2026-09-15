from collections.abc import Callable
from typing import Generic, TypeVar

import rich_click as click

__all__ = ["ListOf"]

T = TypeVar("T")


def call_verify(verify: Callable[[T], bool] | None, el: list[T]) -> bool:
    """Verify that all elements in the list pass the given verification function."""
    if verify is None:
        return True
    for i, v in enumerate(el):
        if not verify(v):
            raise ValueError(f"Element at index {i} failed verification: {v}")
    return True


class ListOf(click.ParamType, Generic[T]):
    """A click parameter type that parses a comma-separated string into a list
    of a given inner type (e.g. ListOf(int), ListOf(float))."""

    name = "list"

    def __init__(
        self,
        inner_type: type[T] | click.ParamType[T] | None = None,
        min_length: int = 1,
        max_length: int | None = None,
        length: int | None = None,
        verify: Callable[[T], bool] | None = None,
        separator: str = ",",
    ):
        """Generate a new ListOf parameter type.

        Args:
            inner_type (type[T] | click.ParamType[T] | None, optional): The type of each element in the list.
                If None, returns the raw string parts. Defaults to None.
            min_length (int, optional): Minimum number of elements in the list. Defaults to 1.
            max_length (int | None, optional): Maximum number of elements in the list. Defaults to None.
            length (int | None, optional): Exact number of elements in the list. Defaults to None.
            verify (Callable[[T], bool] | None, optional): A function to verify each element. Defaults to None.
            separator (str, optional): The separator to use when splitting the input string. Defaults to ",".
        """
        self.inner_type = inner_type
        self.min_length = min_length
        self.max_length = max_length
        self.length = length
        self.verify = verify
        self.separator = separator
        # Cannot have negative lengths
        if self.min_length < 0:
            raise ValueError("min_length cannot be negative")
        if self.length is not None and self.length < 0:
            raise ValueError("length cannot be negative")
        if self.max_length is not None and self.max_length < 0:
            raise ValueError("max_length cannot be negative")
        # Cannot split on an empty separator
        if not separator:
            raise ValueError("separator cannot be empty")
        # Cannot specify both length and min/max length
        if self.length is not None and (self.min_length != 1 or self.max_length is not None):
            raise ValueError("Cannot specify both length and min/max length")

    def __convert_part(self, part: str) -> T:
        """Convert a single string part to the inner type."""
        inner = self.inner_type
        if isinstance(inner, click.ParamType):
            return inner.convert(part, None, None)
        assert inner is not None
        return inner(part)  # ty:ignore[too-many-positional-arguments]

    def convert(self, value: str | list | None, param, ctx):
        if value is None:
            return None

        # Already converted (e.g. default value is already a list)
        if isinstance(value, list):
            return value

        if self.separator.isspace():
            # Splitting on whitespace already trims and collapses it
            parts = value.split()
        else:
            parts = [p.strip() for p in value.split(self.separator)]

        # Validate length constraints
        if self.length is not None and len(parts) != self.length:
            self.fail(f"Expected exactly {self.length} elements, got {len(parts)}", param, ctx)
        if len(parts) < self.min_length:
            self.fail(f"Expected at least {self.min_length} elements, got {len(parts)}", param, ctx)
        if self.max_length is not None and len(parts) > self.max_length:
            self.fail(f"Expected at most {self.max_length} elements, got {len(parts)}", param, ctx)

        try:
            if self.inner_type is None:
                # Special case for None inner_type, we could still want to verify the raw string parts
                call_verify(self.verify, parts)  # ty:ignore[invalid-argument-type]
                return parts
            # Regular verify and conversion
            converted: list[T] = [self.__convert_part(p) for p in parts]
            call_verify(self.verify, converted)
            return converted
        except (ValueError, TypeError) as e:
            name = getattr(self.inner_type, "__name__", str(self.inner_type))
            self.fail(f"Could not convert {value!r} to list of {name}: {e}", param, ctx)

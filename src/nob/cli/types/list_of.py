import rich_click as click

__all__ = ["ListOf"]


class ListOf(click.ParamType):
    """A click parameter type that parses a comma-separated string into a list
    of a given inner type (e.g. ListOf(int), ListOf(float))."""

    name = "list"

    def __init__(self, inner_type: type | click.ParamType | None = None):
        """Generate a new ListOf parameter type.

        Args:
            inner_type (type | click.ParamType | None, optional): The type of each element in the list.
                If None, returns the raw string parts. Defaults to None.
        """
        self.inner_type = inner_type

    def convert(self, value: str | list | None, param, ctx):
        if value is None:
            return None

        # Already converted (e.g. default value is already a list)
        if isinstance(value, list):
            return value

        parts = [p.strip() for p in value.split(",")]
        try:
            if self.inner_type is None:
                return parts
            return [self.inner_type(p) for p in parts]
        except (ValueError, TypeError) as e:
            name = getattr(self.inner_type, "__name__", str(self.inner_type))
            self.fail(f"Could not convert {value!r} to list of {name}: {e}", param, ctx)

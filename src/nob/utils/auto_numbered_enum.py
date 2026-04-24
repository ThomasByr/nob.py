from enum import Enum

__all__ = ["AutoNumberedEnum"]


class AutoNumberedEnum(Enum):
    """
    An enum that automatically assigns values to its members.\\
    Just inherit from this class instead of `Enum` and you're good to go.

    ## Note
    C-style numbering starts at `1` (0 is never picked),\\
    so that implicit boolean representation of a valid member always evaluate to `True`

    ## Example
    ```py
    >>> class MyEnum(AutoNumberedEnum):
    ...   FOO = ()
    ...   BAR = ()
    ...   BAZ = ()
    ...
    >>> MyEnum.FOO
    <MyEnum.FOO: 1>
    >>> MyEnum.BAR
    <MyEnum.BAR: 2>
    >>> MyEnum.BAZ
    <MyEnum.BAZ: 3>
    ```
    """

    def __new__(cls, *args) -> "AutoNumberedEnum":
        """Creates a new enum member with an automatically assigned value.

        Returns:
            AutoNumberedEnum
        """
        value = len(cls.__members__) + 1
        obj = object.__new__(cls)
        obj._value_ = value
        return obj

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}.{self.name}: {self.value}>"

    def __str__(self) -> str:
        return f"{self.__class__.__name__}.{self.name}"

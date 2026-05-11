from collections.abc import Iterable
from typing import TypeVar

__all__ = ["join"]


T = TypeVar("T")


def join(
    sequence: Iterable[T],
    blob: str = ", ",
    final_and: bool = True,
    final_dot: bool = True,
    nothing_when_empty: bool = True,
) -> str:
    """Creates a new string that joins elements of the iterable with `blob`,\\
    optionally replacing the last separator with " and " and adding a final dot.

    Does not assume `sequence` has __getitem__ or __len__ implemented.

    Args:
        sequence (Iterable[T]): Sequence of representable object to join.
        blob (str, optional): Separator as a string. Defaults to ", ".
        final_and (bool, optional): If you want to replace the last separator with " and ". Defaults to True.
        final_dot (bool, optional): If you want to add "." to the end. Defaults to True.
        nothing_when_empty (bool, optional): If you want to return "nothing" when sequence is empty. `final_dot` applies. Defaults to True.

    Returns:
        str: The new formatted string.
    """
    n = 0
    r: list[str] = []
    for e in sequence:
        n += 1
        r.append(str(e))
        r.append(blob)
    if n == 0 and nothing_when_empty:
        r.append("nothing")
    elif n > 0:
        assert r.pop() == blob
        if n > 1 and final_and:
            r[-2] = " and "
    if final_dot:
        r.append(".")
    return "".join(r)

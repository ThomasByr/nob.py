from .count import HumanCount
from .duration import HumanDuration
from .features import FEATURES
from .throughput import HumanThroughput

__all__ = ["FEATURES", "count", "duration", "throughput"]
# revival of https://github.com/rsalmei/about-time and pending PRs


def count(value: int | float, unit: str = "", /):
    """Get a renderable human-friendly representation of a count.

    Args:
        value (int | float): The count value to be represented in a human-friendly format. Must be a non-negative integer or float.
        unit (str, optional): The unit of the count. Defaults to "".

    Returns:
        HumanCount: A human-friendly representation of the count.

    Example:
        >>> from nob import human
        >>> print(human.count(123456789))
        123.46M
    """
    return HumanCount(value, unit)


def duration(value: int | float, /):
    """Get a renderable human-friendly representation of a duration in seconds.

    Args:
        value (int | float): The duration value in seconds to be represented in a human-friendly format. Must be a non-negative integer or float.

    Returns:
        HumanDuration: A human-friendly representation of the duration.

    Example:
        >>> from nob import human
        >>> print(human.duration(123.456))
        2:03.5
    """
    return HumanDuration(value)


def throughput(value: int | float, unit: str = "it", /):
    """Get a renderable human-friendly representation of a throughput in units per second.

    Args:
        value (int | float): The throughput value in units per second to be represented in a human-friendly format. Must be a non-negative integer or float.
        unit (str, optional): The unit of the throughput. Defaults to "it".

    Returns:
        HumanThroughput: A human-friendly representation of the throughput.

    Example:
        >>> from nob import human
        >>> print(human.throughput(0.123))
        7.4it/m
    """
    return HumanThroughput(value, unit)

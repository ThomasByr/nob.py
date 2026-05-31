from typing_extensions import override

from .count import fn_human_count
from .features import FEATURES, HumanWithUnit, conv_space

__all__ = ["HumanThroughput"]


SPEC = (
    (24.0, "/d", 2),
    (60.0, "/h", 1),
    (60.0, "/m", 1),
    # "/s" in code.
)


def __human_throughput(val: float, unit: str, prec: int | None, space: str, fn_count, /) -> str:
    val *= 60.0 * 60.0 * 24.0
    for size, scale, dec in SPEC:
        r = round(val, dec)
        if r >= size:
            val /= size
            continue

        if prec is not None:
            r = round(val, prec)
        elif r % 1.0 == 0.0:
            prec = 0
        elif (r * 10.0) % 1.0 == 0.0:
            prec = 1
        else:
            prec = 2
        return "{:.{}f}{}{}{}".format(r, prec, space, unit, scale)

    return "{}/s".format(fn_count(val, unit, prec))


def fn_human_throughput(show_space: bool, d1024: bool, iec: bool, /):
    def run(val: float, unit: str, prec: int | None = None, /):
        return __human_throughput(val, unit, prec, space, fn_count)

    fn_count = fn_human_count(show_space, d1024, iec)
    space = conv_space(show_space)
    return run


class HumanThroughput(HumanWithUnit):
    @override
    def str(self, prec: int | None = None) -> str:
        return fn_human_throughput(FEATURES.feature_space, FEATURES.feature_1024, FEATURES.feature_iec)(
            self.value, self.unit, prec
        )

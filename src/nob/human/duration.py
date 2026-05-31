from typing_extensions import override

from .features import FEATURES, Human, conv_space

__all__ = ["HumanDuration"]

SPEC = (
    (1e3, 1e3, "ns", 1),
    (1e3, 1e3, "µs", 1),  # Uses non-ASCII “µs” suffix
    (1e3, 1e3, "ms", 1),
    (60.0, 1.0, "s", 2),
    # 1:01.1 (minutes in code, 1 decimal).
    # 1:01:01 (hours in code, 0 decimal).
)


def __human_duration(val: float, prec: int | None, space: str, /) -> str:
    val *= 1e9
    for size, div_next, scale, dec in SPEC:
        r = round(val, dec)
        if r >= size:
            val /= div_next
            continue

        if prec is not None:
            r = round(val, prec)
        elif r % 1.0 == 0.0:
            prec = 0
        elif (r * 10.0) % 1.0 == 0.0:
            prec = 1
        else:
            prec = 2
        return "{:.{}f}{}{}".format(r, prec, space, scale)

    val = round(val, 1)
    m = val / 60.0
    if m < 60.0:
        r = val % 60.0
        if prec is not None:
            pass
        elif r % 1.0 == 0.0:
            prec = 0

        if prec == 0:
            return "{:.0f}:{:02.0f}".format(m // 1.0, r)
        return "{:.0f}:{:04.1f}".format(m // 1.0, round(r, 1))

    return "{:.0f}:{:02.0f}:{:02.0f}".format(m / 60.0 // 1.0, m % 60.0 // 1.0, val % 60.0 // 1.0)


def fn_human_duration(show_space: bool, /):
    def run(val, prec: int | None = None, /):
        return __human_duration(val, prec, space)

    space = conv_space(show_space)
    return run


class HumanDuration(Human):
    @override
    def str(self, prec: int | None = None) -> str:
        return fn_human_duration(FEATURES.feature_space)(self.value, prec)

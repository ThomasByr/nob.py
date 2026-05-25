from typing_extensions import override

from .features import FEATURES, HumanWithUnit, conv_space

__all__ = ["HumanCount"]

SI_1000_SPEC = ("", "k", "M", "G", "T", "P", "E", "Z", "Y")
SI_1024_SPEC = ("", "K", "M", "G", "T", "P", "E", "Z", "Y")
IEC_1024_SPEC = ("", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi", "Yi")
DECIMALS = [1, 1, 1, 2, 2, 2, 2, 2, 2]


def __human_count(val: float, unit: str, prec: int | None, space: str, divisor: int, spec: tuple) -> str:
    for scale, dec in zip(spec, DECIMALS, strict=True):  # noqa: B007
        r = round(val, dec)
        if r >= divisor:
            val /= divisor
            continue
        break
    else:
        r, scale = val, "+"

    if prec is not None:
        r = round(val, prec)
    elif r % 1.0 == 0.0:
        prec = 0
    elif (r * 10.0) % 1.0 == 0.0:
        prec = 1
    else:
        prec = 2
    return "{:.{}f}{}{}{}".format(r, prec, space, scale, unit)


def fn_human_count(show_space: bool, d1024: bool, iec: bool):
    def run(val: float, unit: str, prec: int | None = None):
        return __human_count(val, unit, prec, space, divisor, spec)

    space = conv_space(show_space)
    divisor, spec = 1024, IEC_1024_SPEC
    if not iec:
        divisor, spec = 1024 if d1024 else 1000, SI_1000_SPEC
    return run


class HumanCount(HumanWithUnit):
    @override
    def str(self, prec: int | None = None) -> str:
        return fn_human_count(FEATURES.feature_space, FEATURES.feature_1024, FEATURES.feature_iec)(
            self.value, self.unit, prec
        )

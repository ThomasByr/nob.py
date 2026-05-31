from abc import ABC, abstractmethod


class Features:
    def __init__(self):
        self._feature_space = False
        self._feature_1024 = False
        self._feature_iec = False

    @property
    def feature_space(self) -> bool:
        return self._feature_space

    @property
    def feature_1024(self) -> bool:
        return self._feature_1024

    @property
    def feature_iec(self) -> bool:
        return self._feature_iec

    @feature_space.setter
    def feature_space(self, value: bool):
        self._feature_space = bool(value)

    @feature_1024.setter
    def feature_1024(self, value: bool):
        self._feature_1024 = bool(value)

    @feature_iec.setter
    def feature_iec(self, value: bool):
        self._feature_iec = bool(value)
        self.feature_1024 = value


def conv_space(space: bool) -> str:
    return " " if space else ""


FEATURES = Features()


class Human(ABC):
    def __init__(self, value: int | float, /):
        assert value >= 0.0
        self.__value = value

    @property
    def value(self):
        return self.__value

    @abstractmethod
    def str(self, prec: int | None = None, /) -> str:
        """Return a human-friendly representation of the value. It dynamically calculates the best scale to use.\\
        You don't need to call this method directly, just use `str()` or `print()` on the object.

        Args:
            prec: an optional custom precision to use in the representation. Defaults to None.

        Returns:
            str: A human-friendly representation of the value.
        """
        pass

    def __str__(self):
        return self.str()

    def __repr__(self):
        return "{}{{ value={} }} -> {}".format(self.__class__.__name__, self.__value, self)

    def __eq__(self, other):
        return self.__str__() == other


class HumanWithUnit(Human):
    def __init__(self, value: int | float, unit: str = "", /):
        super().__init__(value)
        self.__unit = unit

    @property
    def unit(self) -> str:
        return self.__unit

    def with_unit(self, value: str, /):
        """Return a new instance of the same class with the same value but a different unit."""
        return self.__class__(self.value, value)

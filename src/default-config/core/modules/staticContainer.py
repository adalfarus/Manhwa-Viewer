# Standard typing imports for aps
import collections.abc as _a
import abc as _abc
import typing as _ty
import types as _ts

T = _ty.TypeVar('T')


class StaticContainer(_ty.Generic[T]):

    def __init__(self, value: T | None = None) -> None:
        self._value: T | None = value

    def get_value(self) -> T:
        """
        Get the value stored in the Container
        :return: (T) returns the current value stored
        """
        return self._value

    def set_value(self, new_value: T) -> None:
        """
        Sets a new value to store in the Container
        :param new_value: T
        :return: None
        """
        self._value = new_value

    def has_value(self) -> bool:
        """
        Returns a bool to indicate if the container stores a value
        :return: True, if the Container stores a value
        """
        return self._value is not None

    def clear_value(self) -> None:
        """
        Clears the value stored
        :return: None
        """
        self._value = None

"""TBA"""

import collections.abc as _a
import typing as _ty
import types as _ts


class Widget:
    ...


_T = _ty.TypeVar("_T")
class Input(_ty.Generic[_T]):
    def __init__(self, label: str, gl_type: str, widget: Widget, default: _T,
                 preprocessing_func: _ty.Callable[[_T], _ty.Any] = lambda x: x) -> None:
        self.label: str = label
        self.gl_type: str = gl_type
        self.widget: Widget = widget
        self.default: _T = default
        self.preprocessing_func: _ty.Callable[[_T], _ty.Any] = preprocessing_func


class Checkbox(Widget):
    def __init__(self, label: str) -> None: self.label = label


class Slider(Widget):
    def __init__(self, min_: int | float, max_: int | float, step: int | float, type_: _ty.Type[float | int]) -> None:
        self.min: int | float = type_(min_)
        self.max: int | float = type_(max_)
        self.step: int | float = type_(step)
        self.type: _ty.Type[float | int] = type_


class Spinbox(Widget):
    def __init__(self, min_: int | float, max_: int | float, step: int | float, type_: _ty.Type[float | int]) -> None:
        self.min: int | float = type_(min_)
        self.max: int | float = type_(max_)
        self.step: int | float = type_(step)
        self.type: _ty.Type[float | int] = type_


class ColorPicker(Widget): pass


class NoGui(Widget):
    def __int__(self) -> None:
        self._value: _ty.Any = None

    def set_value(self, new_value: _ty.Any) -> None:
        self._value = new_value

    def get_value(self) -> _ty.Any:
        return self._value


class Combobox(Widget):
    def __init__(self, options: dict[str, int]) -> None:
        self.options: dict[str, int] = options  # e.g., {"Full": 0, "Red Only": 1}


class KeyboardInput(Widget):
    def __init__(self, multiline: bool = False, placeholder: str = "",
                validation_func: _ty.Callable[[str], str] = lambda x: x) -> None:
        self.multiline: bool = multiline
        self.placeholder: str = placeholder
        self.validation_func: _ty.Callable[[str], str] = validation_func


class VectorInput(Widget):
    def __init__(self, dims: int = 3, min_: float | int | None = None, max_: float | int | None = None,
                 step: float | int = 0.1, type_: _ty.Type[float | int] = float, labels: bool = True) -> None:
        assert 1 <= dims <= 4, "VectorInput supports only 1D to 4D vectors"
        self.dims: int = dims
        self.min: float | int | None = type_(min_) if min_ is not None else min_
        self.max: float | int | None = type_(max_) if max_ is not None else max_
        self.step: float | int = type_(step)
        self.type: _ty.Type[float | int] = type_
        self.labels: bool = labels

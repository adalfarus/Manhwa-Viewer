"""TBA"""

import collections.abc as _a
import typing as _ty
import types as _ts


class Widget:
    ...


_T = _ty.TypeVar("_T")
class Input(_T):
    def __init__(self, label: str, gl_type: str, widget: Widget, default: _T) -> None:
        self.label: str = label
        self.gl_type: str = gl_type
        self.widget: Widget = widget
        self.default: _T = default


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


class NoGui(Widget): pass


class Combobox(Widget):
    def __init__(self, options: dict[str, int]) -> None:
        self.options: dict[str, int] = options  # e.g., {"Full": 0, "Red Only": 1}

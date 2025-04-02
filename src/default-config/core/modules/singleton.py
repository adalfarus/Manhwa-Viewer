"""TBA"""

import threading

# Standard typing imports for aps
import collections.abc as _a
import abc as _abc
import typing as _ty
import types as _ts


def singleton(cls) -> _ty.Callable:  # cls is a reference of the decorated class
    _instances = {}
    _lock = threading.Lock()

    def get_instance(*args, **kwargs):
        if cls not in _instances:
            with _lock:
                if cls not in _instances:  # Doppelte Überprüfung
                    _instances[cls] = cls(*args, **kwargs)
        return _instances[cls]

    return get_instance

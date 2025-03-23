from oaplustools.package import install_dependencies_lst as _install_dependencies_lst
from typing import Iterable, Iterator, Callable, Any


def reverse_map(functions: Iterable[Callable], *args, **kwargs):
    return [func(*args, **kwargs) for func in functions]


def gen_map(functions: Iterable[Callable], args_iter: Iterator[Any], kwargs_iter: Iterator[dict]):
    for func, args, kwargs in zip(functions, args_iter, kwargs_iter):
        yield func(*args, **kwargs)


def install_dependencies():
    success = _install_dependencies_lst(["Pillow==10.2.0", "cryptography==42.0.5", "brotli==1.1.0", "zstandard==0.22.0",
                                         "py7zr==0.21.0"])
    if not success:
        return
    print("Done, all possible dependencies for the utils module installed ...")

import subprocess as _subprocess
import sys as _sys
import os as _os
import warnings as _warnings
from oaplustools.package import install_dependencies_lst as _install_dependencies_lst


def execute_python_command(arguments: list = None, *args, **kwargs) -> _subprocess.CompletedProcess[str]:
    if arguments is None:
        arguments = []
    print(' '.join([_sys.executable] + arguments))
    # Added to remain consistent with executing in the same python environment
    return _subprocess.run([_sys.executable] + arguments, *args, **kwargs)


def interruptCTRL():
    """Simulates a hard user CTRL+C exit. This means it skips any try ... except KeyboardInterrupts"""
    exit(-1073741510)  # 130 / 0xC000013A


def install_all_dependencies():
    success = _install_dependencies_lst(["requests==2.31.0", "Pillow==10.3.0", "BeautifulSoup4==4.12.3",
                                         "duckduckgo_search==3.9.3", "cryptography==42.0.5", "PySide6==6.6.1",
                                         "aiohttp==3.9.3", "opencv-python==4.9.0.80", "brotli==1.1.0",
                                         "zstandard==0.22.0", "py7zr==0.21.0", "pillow_heif==0.15.0", "numpy==1.26.4"])
    if not success:
        return
    print("Done, all possible dependencies installed ...")


def set_dir_to_ex():
    import __main__
    # Get the directory where the main script (or frozen exe) is located
    if getattr(_sys, 'frozen', False):
        # If the script is running as a bundled executable created by e.g. PyInstaller
        main_dir = _os.path.dirname(_sys.executable)
    else:
        # If the script is running as a normal Python script
        if hasattr(__main__, '__file__'):
            main_dir = _os.path.dirname(_os.path.abspath(__main__.__file__))
        else:
            main_dir = _os.path.dirname(_os.getcwd())
            _warnings.warn(
                "Could not set the current working directory to the location of the main script or executable",
                RuntimeWarning,
                stacklevel=2
            )
    # Change the current working directory to the main script directory
    _os.chdir(main_dir)

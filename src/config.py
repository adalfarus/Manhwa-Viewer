"""TBA"""
import os
import sys as _sys
import os as _os
import shutil as _shutil
import platform as _platform
import typing as _ty
from pathlib import Path as _PLPath


INDEV: bool = True
INDEV_KEEP_RUNTIME_FILES: bool = True
OLD_CWD: str = _os.getcwd()
PROGRAM_NAME: str = "SMV"
VERSION: int = 175
VERSION_ADD: str = "b1"
PROGRAM_NAME_NORMALIZED: str = "manhwa_viewer"
PROGRAM_NAME_NORMALIZED_VERSION: str = f"smv_{VERSION}{VERSION_ADD}"
OS_LIST: list[str] = ["Windows"]
OS_VERSIONS_LIST: list[tuple[str, ...]] = [("any",)]
MAJOR_OS_VERSIONS_LIST: list[tuple[str, ...]] = [("10", "11")]
PY_VERSIONS: list[tuple[int, int]] = [(3, 10), (3, 11), (3, 12)]

if "CONFIG_DONE" not in locals():
    CONFIG_DONE: bool = False
if "CHECK_DONE" not in locals():
    CHECK_DONE: bool = False

exported_logs: str
base_app_dir: str
old_cwd: str

exit_code: int
exit_message: str

def _is_compiled() -> bool:
    """  # From aps.io.env
    Detects if the code is running in a compiled environment and identifies the compiler used.

    This function checks for the presence of attributes and environment variables specific
    to common Python compilers, including PyInstaller, cx_Freeze, and py2exe.
    :return: bool
    """
    return getattr(_sys, "frozen", False) and (hasattr(_sys, "_MEIPASS") or _sys.executable.endswith(".exe"))

def _clean_path(path: str, remove_for: _ty.Iterable[tuple[str, ...]], remove_from_src_dir: str) -> str:
    p = _PLPath(path)
    parts = list(p.parts)

    # Step 1: Remove filename if it has an extension
    filename = None
    if '.' in parts[-1]:  # crude file check
        filename = parts.pop()

    # Step 2: Check if path ends with any pattern
    for pattern in remove_for:
        if tuple(parts[-len(pattern):]) == pattern:
            # Step 3: Remove first occurrence of "src" from the *back*
            for i in reversed(range(len(parts))):
                if parts[i] == remove_from_src_dir:
                    parts.pop(i)
                    break
            break  # we only process the first matching pattern

    # Step 4: Reattach filename if needed
    if filename:
        parts.append(filename)

    return str(_PLPath(*parts))


def _configure() -> dict[str, str]:
    if _is_compiled():
        _os.chdir(_os.path.dirname(_os.path.abspath(__file__)))
        if not _sys.stdout:
            _sys.stdout = open(_os.devnull, "w")
        if not _sys.stderr:
            _sys.stderr = open(_os.devnull, "w")
    accumulated_logs = "Starting cloning of defaults ...\n"
    old_cwd = _os.getcwd()
    install_dir = _os.path.join(old_cwd, "default-config")
    base_app_dir = _os.path.join(_os.environ.get("LOCALAPPDATA", ""), PROGRAM_NAME_NORMALIZED)
    base_version_dir = _os.path.join(base_app_dir, f"{VERSION}{VERSION_ADD}")

    if INDEV and _os.path.exists(base_app_dir):  # Remove everything to simulate a fresh install
        if not INDEV_KEEP_RUNTIME_FILES:
            _shutil.rmtree(base_app_dir)
            _os.mkdir(base_app_dir)
        else:  # Skip only .db or .log files
            for root, dirs, files in _os.walk(base_app_dir, topdown=False):
                for file in files:
                    if not file.lower().endswith((".db", ".log", ".png", ".webp", ".jpg", ".jpeg", ".gif", ".heif", ".heic", ".bmp")):
                        _os.remove(_os.path.join(root, file))
                for directory in dirs:
                    dir_path = _os.path.join(root, directory)
                    if not any(f.lower().endswith((".db", ".log", ".png", ".webp", ".jpg", ".jpeg", ".gif", ".heif", ".heic", ".bmp")) or _os.path.isdir(_os.path.join(dir_path, f)) for f in _os.listdir(dir_path)):
                        _shutil.rmtree(dir_path)

    dirs_to_create = []
    dir_structure = (
            ("data", ("logs",)),
            ("caches", ()),
            (f"{VERSION}{VERSION_ADD}", (
                ("models", ()),
                ("core", ("libs", "modules")),
                ("extensions", ())
            ))
    )  # Use a stack to iteratively traverse the directory structure
    remove_from_src_dir = f"{VERSION}{VERSION_ADD}"
    remove_for = (("core",), ("core", "libs"), ("core", "modules"), ("extensions",), ("models",))
    stack: list[tuple[str, tuple[str, ...] | tuple]] = [(base_app_dir, item) for item in dir_structure]
    while stack:
        base_path, (dir_name, subdirs) = stack.pop()
        current_path = _os.path.join(base_path, dir_name)

        # if not subdirs:
        #     dirs_to_create.append(current_path)
        #     accumulated_logs += f"Cloning {current_path}\n"
        if subdirs:  # Subdirectories; it's not a leaf
            for subdir in subdirs:  # Add each subdirectory to the stack for further processing
                if isinstance(subdir, tuple):
                    stack.append((current_path, subdir))  # Nested structure
                else:  # Direct leaf under the current directory
                    dirs_to_create.append(_os.path.join(current_path, subdir))
                    accumulated_logs += f"Cloning {_os.path.join(current_path, subdir)}\n"
        dirs_to_create.append(current_path)
        accumulated_logs += f"Cloning {current_path}\n"
    for dir_to_create in dirs_to_create:
        _os.makedirs(dir_to_create, exist_ok=True)

    # _sys.path.insert(0, _os.path.join(base_app_dir, "core", "modules"))
    _sys.path.insert(0, base_version_dir)  # To bug-fix some problem, I think with std libs
    _sys.path.insert(0, _os.path.join(base_version_dir, "core", "libs"))

    for directory in dirs_to_create:
        base_directory = _clean_path(directory.replace(base_app_dir, install_dir), remove_for, remove_from_src_dir)
        for dirpath, dirnames, filenames in os.walk(base_directory):
            dirpath = os.path.relpath(dirpath, base_directory)
            for filename in filenames:
                file_path = _os.path.join(base_directory, dirpath, filename)
                stripped_filename = _os.path.relpath(_os.path.join(directory, dirpath, filename), base_app_dir)
                alternate_file_location = _os.path.join(base_app_dir, stripped_filename)
                if not _os.path.exists(alternate_file_location) or INDEV:  # Replace all for indev
                    # accumulated_logs += f"{file_path} -> {alternate_file_location}\n"  # To flush config prints in main
                    _os.makedirs(_os.path.dirname(alternate_file_location), exist_ok=True)

                    # Remove dir from src
                    _shutil.copyfile(file_path, alternate_file_location)
                # else:
                #     accumulated_logs += f"{alternate_file_location} Already exists\n"  # To flush config prints in main

    _os.chdir(base_app_dir)
    return {
        "accumulated_logs": accumulated_logs, "old_cwd": old_cwd, "install_dir": install_dir,
        "base_app_dir": base_app_dir,
    }


def check() -> None:
    """Check if environment is suitable. Can raise RuntimeError"""
    global CHECK_DONE, exit_code, exit_message

    if CHECK_DONE:
        return None
    CHECK_DONE = True

    exit_code, exit_message = 0, "An unknown error occurred"
    platform_idx = OS_LIST.index(_platform.system())
    os_versions = OS_VERSIONS_LIST[platform_idx]
    major_os_versions = MAJOR_OS_VERSIONS_LIST[platform_idx]
    if _platform.system() not in OS_LIST:
        exit_code, exit_message = 1, (f"You are currently on {_platform.system()}. "
                                      f"Please run this on a supported OS ({', '.join(OS_LIST)}).")
    elif _platform.version() not in os_versions and os_versions != ("any",):
        exit_code, exit_message = 1, (f"You are currently on {_platform.version()}. "
                                      f"Please run this on a supported OS version ({', '.join(os_versions)}).")
    elif not _platform.release() in major_os_versions:
        exit_code, exit_message = 1, (f"You are currently on {_platform.release()}. "
                                      f"Please run this on a supported major OS version ({', '.join(major_os_versions)}).")
    elif _sys.version_info[:2] not in PY_VERSIONS:
        py_versions_strs = [f"{major}.{minor}" for (major, minor) in PY_VERSIONS]
        exit_code, exit_message = 1, (f"You are currently on {'.'.join([str(x) for x in _sys.version_info])}. "
                                      f"Please run this using a supported python version ({', '.join(py_versions_strs)}).")
    if exit_code:
        raise RuntimeError(exit_message)
    return None


def setup() -> None:
    """Setup the app, this does not include checking for compatibility"""
    global CONFIG_DONE, exported_logs, base_app_dir, old_cwd
    if CONFIG_DONE or not CHECK_DONE:
        return None
    CONFIG_DONE = True
    exported_vars = _configure()
    exported_logs, base_app_dir, old_cwd = (exported_vars["accumulated_logs"], exported_vars["base_app_dir"],
                                            exported_vars["old_cwd"])
    return None

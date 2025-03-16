# environment.py
from typing import Union, Optional, Callable, Any, Type, cast
from types import FrameType
import subprocess
import warnings
import platform
import tempfile
import inspect
import shutil
import sys
import os


try:
    import winreg
except ImportError:
    winreg = None  # winreg is not available on non-Windows platforms


def get_temp():
    return tempfile.gettempdir()


def set_working_dir_to_main_script_location():
    """
    Set the current working directory to the location of the main script
    or executable. It considers whether the script is frozen using PyInstaller
    or is running as a normal Python script.
    """
    import __main__
    try:
        # Get the directory where the main script (or frozen exe) is located
        if getattr(sys, 'frozen', False):
            # If the script is running as a bundled executable created by PyInstaller
            main_dir = os.path.dirname(sys.executable)
        else:
            # If the script is running as a normal Python script
            if hasattr(__main__, '__file__'):
                main_dir = os.path.dirname(os.path.abspath(__main__.__file__))
            else:
                main_dir = os.path.dirname(os.getcwd())
                warnings.warn(
                    "Could not set the current working directory to the location of the main script or executable.",
                    RuntimeWarning,
                    stacklevel=2
                    )

        # Change the current working directory to the main script directory
        os.chdir(main_dir)
        print(f"Working directory set to {main_dir}")

    except Exception as e:
        print(f"An error occurred while changing the working directory: {e}")
        raise  # Re-raise the error


def change_working_dir_to_script_location():
    if getattr(sys, 'frozen', False):
        # If the script is running as a bundled executable created by PyInstaller
        script_dir = os.path.dirname(sys.executable)
    else:
        # Get the path of the caller of this function
        frame = inspect.currentframe()
        caller_frame = frame.f_back
        caller_file = caller_frame.f_globals["__file__"]
        script_dir = os.path.dirname(os.path.abspath(caller_file))

    # Change the current working directory to the script directory
    os.chdir(script_dir)


def change_working_dir_to_temp_folder():
    os.chdir(tempfile.gettempdir())


def change_working_dir_to_userprofile_folder(folder: str):
    system = os.name
    if system == 'posix':
        home_dir = os.path.join(os.path.join(os.path.expanduser('~')), folder)  # os.path.expanduser("~/Desktop")
    elif system == 'nt':
        home_dir = os.path.join(os.path.join(os.environ['USERPROFILE']), folder)
    else:
        raise OSError(f"System {system} isn't supported by this function.")
    os.chdir(home_dir)


def inject_file_path(func: Callable):
    def wrapper(relative_path: str):
        frame = inspect.currentframe().f_back
        module = inspect.getmodule(frame)
        if module is not None:
            file_path = module.__file__
        else:
            file_path = __file__  # Fallback to the current script
        return func(relative_path, file_path)
    return wrapper


@inject_file_path
def absolute_path(relative_path: str, file_path: str) -> str:
    base_dir = os.path.dirname(os.path.abspath(file_path))
    return os.path.join(base_dir, relative_path)


def remv(paths: Union[str, list]):
    if not isinstance(paths, list):
        paths = [paths]
    for path in paths:
        if os.path.exists(path):
            if is_accessible(path):
                if os.path.isfile(path):
                    os.remove(path)
                elif os.path.isdir(path):
                    if len(os.listdir(path)) == 0:
                        os.rmdir(path)
                    elif is_empty_directory(path):
                        shutil.rmtree(path)
                    else:
                        shutil.rmtree(path)
                else:
                    print("Bug, please report")
            else:
                print("Path not accessible")
        else:
            print("Path doesn't exist")


def contains_only_directories(path: str) -> bool:
    for item in os.listdir(path):
        if not os.path.isdir(os.path.join(path, item)):
            return False
    return True


def is_accessible(path: str):
    return os.access(path, os.R_OK)


def is_empty_directory(path: str) -> bool:
    if os.path.isfile(path):
        return False
    elif os.path.isdir(path):
        try:
            with os.scandir(path) as entries:
                for entry in entries:
                    if entry.is_file():
                        return False
                    elif entry.is_dir():
                        if not is_empty_directory(entry.path):
                            return False
        except PermissionError:
            print(f"Permission denied: {path}")
            return False
        return True
    else:
        raise FileNotFoundError(f"No such file or directory '{path}'")


class Path:
    def __init__(self, path: str):
        self.path = os.path.abspath(path)

    def exists(self) -> bool:
        """Check if the path exists."""
        return os.path.exists(self.path)

    def is_file(self) -> bool:
        """Check if the path is a file."""
        return os.path.isfile(self.path)

    def is_directory(self) -> bool:
        """Check if the path is a directory."""
        return os.path.isdir(self.path)

    def create_directory(self):
        """Create a directory at the path."""
        try:
            if not self.exists():
                os.makedirs(self.path)
                print(f"Directory {self.path} created.")
            else:
                print(f"Directory {self.path} already exists.")
        except Exception as e:
            print(f"An error occurred: {e}")
            raise  # Reraise the exception after logging or printing the error message
        
    def mkdir(self, new_inner_dir: str):
        own_dir = self.path
        new_dir = os.path.join(self.path, new_inner_dir)
        self.path = new_dir
        self.create_directory()
        self.path = own_dir
        return new_dir
        
    def join(self, rel_inner_path: str):
        self.path = os.path.join(self.path, rel_inner_path)

    def list_files(self) -> list:
        """List all files in the directory."""
        if self.is_directory():
            with os.scandir(self.path) as entries:
                return [entry.name for entry in entries if entry.is_file()]
        else:
            print(f"{self.path} is not a directory.")
            return []

    def list_subdirectories(self) -> list:
        """List all subdirectories in the directory."""
        if self.is_directory():
            with os.scandir(self.path) as entries:
                return [entry.name for entry in entries if entry.is_dir()]
        else:
            print(f"{self.path} is not a directory.")
            return []

    def get_size(self) -> Optional[int]:
        """Get the size of a file in bytes."""
        if self.is_file():
            return os.path.getsize(self.path)
        else:
            print(f"{self.path} is not a file.")
            return None

    def rename(self, new_path: str):
        """Rename the path to a new path."""
        os.rename(self.path, new_path)
        print(f"{self.path} renamed to {new_path}.")
        self.path = new_path

    def __str__(self):
        return self.path
    
    def __iter__(self):
        if self.is_directory():
            with os.scandir(self.path) as entries:
                for entry in entries:
                    yield entry.path
        else:
            print(f"{self.path} is not a directory.")
            yield self.path
            
    def __len__(self):
        return len(self.path.split("\\"))


def copy(org_loc: str, new_loc: str):
    shutil.copy(org_loc, new_loc)


def move(org_loc: str, new_loc: str):
    shutil.move(org_loc, new_loc)


def rename(org_nam: str, new_nam: str) -> bool:
    try:
        os.rename(org_nam, new_nam)
        print(f"{org_nam} renamed to {new_nam}.")
        return True
    except Exception as e:
        print(f"An error occurred while renaming: {e}")
        return False


def functionize(cls):
    warnings.warn("This is still experimental and may not be working as expected. A finished version should be available in release 1.5",
                  UserWarning, 
                  stacklevel=2)

    def wrapper(*args, **kwargs):
        # Creating an instance of the class
        instance = cls(*args, **kwargs)

        # Collecting the instance attributes (variables) and their values
        attrs = {attr: getattr(instance, attr) for attr in instance.__dict__ if not attr.startswith("_")}  # instance.__dict__.copy()

        # Collecting methods and converting them to standalone functions
        methods = {
            name: getattr(instance, name)
            for name, method in inspect.getmembers(cls, predicate=inspect.isfunction) if not name.startswith("_")
        }

        # Combining attributes and methods
        return {**attrs, **methods}

    return wrapper


def strict(cls: Type[Any]):
    class_name = cls.__name__ + "Cover"
    original_setattr = cls.__setattr__

    # Overridden __setattr__ for the original class
    def new_setattr(self, name, value):
        original_setattr(self, name, value)
        # Update the cover class if attribute is public
        if not name.startswith('_') and hasattr(self, '_cover') and getattr(self._cover, name) != value:
            setattr(self._cover, name, value)

    # Replace __setattr__ in the original class
    cls.__setattr__ = new_setattr

    # Define new __init__ for the cover class
    def new_init(self, *args, **kwargs):
        # Create an instance of the original class
        original_instance = cls(*args, **kwargs)
        original_instance._cover = self  # Reference to the cover class

        # Bind public methods and attributes to the cover class instance
        for attr_name in dir(original_instance):
            if not attr_name.startswith('_'):  # or attr_name in ('__dict__', '__module__'):
                attr_value = getattr(original_instance, attr_name)
                if inspect.isfunction(attr_value):
                    setattr(self, attr_name, attr_value.__get__(self, cls))
                else:
                    setattr(self, attr_name, attr_value)

        def custom_setattr(instance, name, value):
            object.__setattr__(instance, name, value)
            if not name.startswith('_') and getattr(original_instance, name) != value:
                setattr(original_instance, name, value)

        self._dynamic_setattr = custom_setattr

        # Remove reference to original instance
        # del original_instance

    def setattr_overwrite(self, name, value):
        if hasattr(self, '_dynamic_setattr'):
            self._dynamic_setattr(self, name, value)
        else:
            object.__setattr__(self, name, value)

    # Create a new cover class with the new __init__ and other methods/attributes
    cover_class_attrs = {
        '__init__': new_init,
        '__class__': cls,
        '__setattr__': setattr_overwrite,
    }
    for attr_name in dir(cls):
        if callable(getattr(cls, attr_name)) and not attr_name.startswith('_'):
            cover_class_attrs[attr_name] = getattr(cls, attr_name)

    CoverClass = type(class_name, (object,), cover_class_attrs)
    return CoverClass


def privatize(cls: Type[Any]):
    """A class decorator that protects private attributes."""

    original_getattr = cls.__getattribute__
    original_setattr = cls.__setattr__

    def _get_caller_name() -> str:
        """Return the calling function's name."""
        return cast(FrameType, cast(FrameType, inspect.currentframe()).f_back).f_code.co_name

    def protected_getattr(self, name: str) -> Any:
        if name.startswith('_') and _get_caller_name() not in dir(cls):
            raise AttributeError(f"Access to private attribute {name} is forbidden")
        return original_getattr(self, name)

    def protected_setattr(self, name: str, value: Any) -> None:
        if name.startswith('_') and _get_caller_name() not in dir(cls):
            raise AttributeError(f"Modification of private attribute {name} is forbidden")
        original_setattr(self, name, value)

    cls.__getattribute__ = protected_getattr
    cls.__setattr__ = protected_setattr

    return cls


def auto_repr(cls):
    """
    Decorator that automatically generates a __repr__ method for a class.
    """
    if cls.__repr__ is object.__repr__:
        def __repr__(self):
            attributes = ', '.join(f"{key}={getattr(self, key)}" for key in self.__dict__)
            return f"{cls.__name__}({attributes})"

        cls.__repr__ = __repr__
    return cls


class System:
    def __init__(self):
        self.os = self.get_os()
        self.os_version = self.get_os_version()
        self.cpu_arch = self.get_cpu_arch()
        self.cpu_brand = self.get_cpu_brand()
        # GPU information retrieval can be complex and platform-dependent
        # self.gpu_info = self.get_gpu_info()
        self.theme = self.get_system_theme()

    def get_os(self):
        """Get the name of the operating system."""
        return platform.system()

    def get_os_version(self):
        """Get the version of the operating system."""
        return platform.version()
    
    def get_major_os_version(self):
        return platform.release()

    def get_cpu_arch(self):
        """Get the architecture of the CPU (e.g., x86_64, ARM)."""
        return platform.machine()

    def get_cpu_brand(self):
        """Get the brand and model of the CPU."""
        if self.os == 'Windows':
            return platform.processor()
        elif self.os == 'Linux' or self.os == 'Darwin':
            command = "cat /proc/cpuinfo | grep 'model name' | uniq"
            return subprocess.check_output(command, shell=True).decode().split(': ')[1].strip()
        return "Unknown"

    # GPU information retrieval is more complex and may require third-party libraries or specific system commands

    def get_system_theme(self):
        if self.os == 'Windows':
            return self.get_windows_theme()
        elif self.os == 'Darwin':
            return self.get_macos_theme()
        elif self.os == 'Linux':
            return self.get_linux_theme()
        return "Unknown"

    def get_windows_theme(self):
        if not winreg:
            return None

        key = r'SOFTWARE\Microsoft\Windows\CurrentVersion\Themes\Personalize'
        value = 'AppsUseLightTheme'
        try:
            reg_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key)
            theme_value, _ = winreg.QueryValueEx(reg_key, value)
            winreg.CloseKey(reg_key)
            return 'Dark' if theme_value == 0 else 'Light'
        except Exception:
            return None

    def get_macos_theme(self):
        try:
            theme = subprocess.check_output("defaults read -g AppleInterfaceStyle", shell=True).decode().strip()
            return 'Dark' if theme == 'Dark' else 'Light'
        except subprocess.CalledProcessError:
            return 'Light'  # Default to Light since Dark mode is not set

    def get_linux_theme(self):
        # This method is very basic and might not work on all Linux distributions.
        # Linux theme detection can be very varied depending on the desktop environment.
        try:
            theme = subprocess.check_output("gsettings get org.gnome.desktop.interface gtk-theme", shell=True).decode().strip()
            return 'Dark' if 'dark' in theme.lower() else 'Light'
        except Exception:
            return None


def print_system_info():
    sys_info = System()
    print(f"Operating System: {sys_info.os}")
    print(f"OS Version: {sys_info.os_version}")
    print(f"CPU Architecture: {sys_info.cpu_arch}")
    print(f"CPU Brand: {sys_info.cpu_brand}")
    print(f"System Theme: {sys_info.theme}")


def local_test():
    try:
        print_system_info()

        @strict
        class MyCls:
            _attr = ""
        var = MyCls()._attr

        # @functionize
        # class MyClass:
        #     def __init__(self, value):
        #         self.my_attribute = value
        #         self._my_attr = 1

        #     def adder(self):
        #         self.my_attribute = 3

        #     def my_method(self, plus):
        #         return "The value is " + str(self.my_attribute + plus)

        # Creating an instance as a function
        # my_instance = MyClass(10)

        # print(my_instance['my_attribute'])  # Accessing attribute
        # print(my_instance['my_method'](3))  # Calling method
        # my_instance['adder']()
        # print(my_instance['my_attribute'])
    except AttributeError:
        print("Test completed successfully.")
        return True
    except Exception as e:
        print(f"Exception occurred {e}.")
        return False
    print("Strict decorator not working.")
    return False


if __name__ == "__main__":
    local_test()

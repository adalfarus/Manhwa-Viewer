import platform
from typing import Literal, Union
import warnings

# For Windows Systems
try:
    import winreg
    import wmi
    from win10toast import ToastNotifier
except ImportError:
    winreg = wmi = ToastNotifier = None


class _BaseSystem:
    def __init__(self):
        self.os = platform.system()
        self.os_version = platform.version()
        self.major_os_version = platform.release()
        self.cpu_arch = platform.machine()
        self.cpu_brand = self.get_cpu_brand()
        self.gpu_info = None
        self.theme = None

    def get_cpu_brand(self):
        """Get the brand and model of the CPU."""
        if self.os == 'Windows':
            return platform.processor()
        elif self.os == 'Linux' or self.os == 'Darwin':
            command = "cat /proc/cpuinfo | grep 'model name' | uniq"
            return subprocess.check_output(command, shell=True).decode().split(': ')[1].strip()
        return "Unknown"

    def schedule_event(self, event: Literal["startup", "login"]):
        pass

    def send_notification(self, title, message):
        raise NotImplementedError("send_notification is not implemented")

    def get_gpu_info(self):
        raise NotImplementedError("get_gpu_info is not implemented")


class _WindowsSystem(_BaseSystem):
    def __init__(self):
        super().__init__()
        self.gpu_info = self.get_gpu_info()
        self.theme = self.get_system_theme()

    def get_gpu_info(self):
        c = wmi.WMI()
        gpulist = []
        for gpu in c.Win32_VideoController():
            gpulist.append(gpu.Name)
        return gpulist

    def get_system_theme(self):
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

    def schedule_event(self, event: Literal["startup", "login"]):
        pass

    def send_notification(self, title, message):
        toaster = ToastNotifier()
        toaster.show_toast(title, message)


class _DarwinSystem(_BaseSystem):
    def __init__(self):
        super().__init__()
        self.gpu_info = None
        self.theme = self.get_system_theme()

    def get_gpu_info(self):
        result = subprocess.check_output(['system_profiler', 'SPDisplaysDataType'])
        return result.decode()

    def get_system_theme(self):
        try:
            theme = subprocess.check_output("defaults read -g AppleInterfaceStyle", shell=True).decode().strip()
            return 'Dark' if theme == 'Dark' else 'Light'
        except subprocess.CalledProcessError:
            return 'Light'  # Default to Light since Dark mode is not set

    def schedule_event(self, event: Literal["startup", "login"]):
        pass

    def send_notification(self, title, message):
        script = f'display notification "{message}" with title "{title}"'
        subprocess.run(["osascript", "-e", script])


class _LinuxSystem(_BaseSystem):
    def __init__(self):
        super().__init__()
        self.gpu_info = None
        self.theme = self.get_system_theme()

    def get_gpu_info(self):
        result = subprocess.check_output(['lspci', '|', 'grep', 'VGA'])
        return result.decode()

    def get_system_theme(self):
        # This method is very basic and might not work on all Linux distributions.
        # Linux theme detection can be very varied depending on the desktop environment.
        try:
            theme = subprocess.check_output("gsettings get org.gnome.desktop.interface gtk-theme",
                                            shell=True).decode().strip()
            return 'Dark' if 'dark' in theme.lower() else 'Light'
        except Exception:
            return None

    def schedule_event(self, event: Literal["startup", "login"]):
        pass

    def send_notification(self, title, message):
        subprocess.run(["notify-send", title, message])


class System:
    @staticmethod
    def system() -> Union[_WindowsSystem, _DarwinSystem, _LinuxSystem, _BaseSystem]:
        os_name = platform.system()
        if os_name == 'Windows':
            return _WindowsSystem()
        elif os_name == 'Darwin':
            return _DarwinSystem()
        elif os_name == 'Linux':
            return _LinuxSystem()
        else:
            warnings.warn("Unsupported Operating System, returning _BaseSystem instance.", RuntimeWarning, 2)
            return _BaseSystem()

def print_system_info():
    sys_info = System.system()
    print(f"Operating System: {sys_info.os}")
    print(f"OS Version: {sys_info.major_os_version}")
    print(f"CPU Architecture: {sys_info.cpu_arch}")
    print(f"CPU Brand: {sys_info.cpu_brand}")
    print(f"System Theme: {sys_info.theme}")

print_system_info()


import os
import sys
import time
import subprocess
import win32api
import win32con
import win32gui


class WindowsBalloonTip:
    def __init__(self, title, msg, app_path, app_args, icon_path=None):
        message_map = {
            win32con.WM_DESTROY: self.OnDestroy,
            win32con.WM_USER + 20: self.OnUserClick
        }
        wc = win32gui.WNDCLASS()
        hinst = wc.hInstance = win32api.GetModuleHandle(None)
        wc.lpszClassName = "PythonTaskbar"
        wc.lpfnWndProc = message_map
        classAtom = win32gui.RegisterClass(wc)
        style = win32con.WS_OVERLAPPED | win32con.WS_SYSMENU
        self.hwnd = win32gui.CreateWindow(classAtom, "Taskbar", style, 0, 0, win32con.CW_USEDEFAULT,
                                          win32con.CW_USEDEFAULT, 0, 0, hinst, None)
        win32gui.UpdateWindow(self.hwnd)

        self.app_path = app_path
        self.app_args = app_args

        # Load icon
        if icon_path and os.path.isfile(icon_path):
            icon = win32gui.LoadImage(hinst, icon_path, win32con.IMAGE_ICON, 0, 0,
                                      win32con.LR_LOADFROMFILE | win32con.LR_DEFAULTSIZE)
        else:
            icon = win32gui.LoadIcon(0, win32con.IDI_APPLICATION)

        flags = win32gui.NIF_ICON | win32gui.NIF_MESSAGE | win32gui.NIF_TIP
        nid = (self.hwnd, 0, flags, win32con.WM_USER + 20, icon, "tooltip")
        win32gui.Shell_NotifyIcon(win32gui.NIM_ADD, nid)
        win32gui.Shell_NotifyIcon(win32gui.NIM_MODIFY, (
        self.hwnd, 0, win32gui.NIF_INFO, win32con.WM_USER + 20, icon, "Balloon tooltip", msg, 200, title))

        time.sleep(10)
        win32gui.DestroyWindow(self.hwnd)

    def OnUserClick(self, hwnd, msg, wparam, lparam):
        subprocess.Popen([self.app_path] + self.app_args)
        return 0  # Ensure that an integer is returned

    def OnDestroy(self, hwnd, msg, wparam, lparam):
        nid = (self.hwnd, 0)
        win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, nid)
        win32gui.PostQuitMessage(0)
        return 0  # Ensure that an integer is returned


if __name__ == '__main__':
    small_icon = "./balloontip.ico"  # Adjust or leave None for default
    large_icon = None  # Adjust or leave None for no large icon
    app_path = "./__init__.py"  # Adjust to your application's path
    app_args = ["arg1", "arg2"]  # Adjust to your application's arguments
    WindowsBalloonTip("Test Title", "Test Message", app_path, app_args, small_icon)

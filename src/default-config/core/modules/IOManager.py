"""TBA"""   # Copyright zScout
from pathlib import Path as PLPath
import os.path
import logging, sys, re

from core.modules.OrderedSet import OrderedSet
from aplustools.io import ActLogger
from queue import Queue
from core.modules.staticContainer import StaticContainer
from logging import ERROR, WARNING, INFO, DEBUG
# import src.config as configg
from core.modules.singleton import singleton

# Standard typing imports for aps
import collections.abc as _a
import abc as _abc
import typing as _ty
import types as _ts


@singleton
class IOManager:
    """TBA"""
    _do_not_show_again: OrderedSet[str] = OrderedSet()
    _currently_displayed: OrderedSet[str] = OrderedSet()
    _button_display_callable: StaticContainer[_ty.Callable] = StaticContainer()
    _is_indev: StaticContainer[bool] = StaticContainer()
    _popup_queue: _ty.List[_ty.Callable[[_ty.Any], _ty.Any]] = []

    _logger: ActLogger

    def has_cached_errors(self) -> bool:
        """
        Returns if there are popups cached which have not been displayed yet
        :return: bool
        """
        return len(self._popup_queue) > 0

    def invoke_popup(self) -> None:
        """

        :return:
        """
        if not self.has_cached_errors():
            return

        popup_callable: _ty.Callable = self._popup_queue[0]
        self._popup_queue.pop(0)

        popup_callable()

    def init(self, popup_creation_callable: _ty.Callable, logs_folder_path: str, is_indev: bool) -> None:
        """
        Initializes the ErrorCache with a popup creation callable and development mode flag.
        :param popup_creation_callable: Callable used to create popups.
        :param logs_folder_path: File path to the logs folder.
        :param is_indev: Boolean indicating whether the application is in development mode.
        :return: None
        """
        self._button_display_callable.set_value(popup_creation_callable)
        self._order_logs(logs_folder_path)
        self._logger = ActLogger(log_to_file=True, filename=os.path.join(logs_folder_path, "latest.log"))
        self._logger.monitor_pipe(sys.stdout, level=logging.DEBUG)
        self._logger.monitor_pipe(sys.stderr, level=logging.ERROR)
        # Replace fancy characters
        self._is_indev.set_value(is_indev)

    def set_logging_level(self, level: int) -> None:
        """
        Sets the logging level of the Logger
        :param level: Logging level to set to.
        :return: None
        """
        self._logger.setLevel(level)

    def get_logging_level(self) -> int:
        return self._logger.logging_level

    @staticmethod
    def _order_logs(directory: str) -> None:
        logs_dir = PLPath(directory)
        to_log_file = logs_dir / "latest.log"

        if not to_log_file.exists():
            print("Logfile missing")
            return

        with open(to_log_file, "rb") as f:
            # (solution from https://stackoverflow.com/questions/46258499/how-to-read-the-last-line-of-a-file-in-python)
            first_line = f.readline().decode()
            try:  # catch OSError in case of a one line file
                f.seek(-2, os.SEEK_END)
                while f.read(1) != b"\n":
                    f.seek(-2, os.SEEK_CUR)
            except OSError:
                f.seek(0)
            last_line = f.readline().decode()

        try:
            date_pattern = r"^[\[(](\d{4}-\d{2}-\d{2})"
            start_date = re.search(date_pattern, first_line).group(1)  # type: ignore
            end_date = re.search(date_pattern, last_line).group(1)  # type: ignore
        except AttributeError:
            print("Removing malformed latest.log")
            os.remove(to_log_file)
            return

        date_name = f"{start_date}_{end_date}"
        date_logs = list(logs_dir.rglob(f"{date_name}*.log"))

        if not date_logs:
            new_log_file_name = logs_dir / f"{date_name}.log"
        else:
            try:
                max_num = max(
                    (int(re.search(r"#(\d+)$", p.stem).group(1)) for p in date_logs if  # type: ignore
                     re.search(r"#(\d+)$", p.stem)),
                    default=0
                )
            except AttributeError:
                print("AttribError")
                return
            max_num += 1
            base_log_file = logs_dir / f"{date_name}.log"
            if base_log_file.exists():
                os.rename(base_log_file, logs_dir / f"{date_name}#{max_num}.log")
                max_num += 1
            new_log_file_name = logs_dir / f"{date_name}#{max_num}.log"

        os.rename(to_log_file, new_log_file_name)
        print(f"Renamed latest.log to {new_log_file_name}")

    def _show_dialog(self, title: str, text: str, description: str,
                     icon: _ty.Literal["Information", "Critical", "Question", "Warning", "NoIcon"],
                     custom_buttons: _ty.Dict[str, _ty.Callable] | None = None) -> None:
        """
        Displays a dialog box with the provided information.
        :param title: Title of the dialog box.
        :param text: Main text content of the dialog box.
        :param description: Additional description text.
        :param icon: Type of icon to display in the dialog box.
        :return: None
        """
        if text in self._currently_displayed:
            # Error is currently displayed
            return

        if text in self._do_not_show_again:
            # Error should not be displayed again
            return

        if not self._button_display_callable.has_value():
            return

        self._currently_displayed.add(text)

        checkbox_text: str = "Do not show again"
        buttons_list: _ty.List[str] = ["Ok"]
        default_button: str = buttons_list[0]

        # add custom buttons
        if custom_buttons is not None:
            for key in list(custom_buttons.keys()):
                buttons_list.append(key)

        popup_creation_callable: _ty.Callable = self._button_display_callable.get_value()
        popup_return: tuple[str | None, bool] = popup_creation_callable("[N.E.F.S] " + title, text, description, icon,
                                                                        buttons_list, default_button, checkbox_text)

        if popup_return[1]:
            self._do_not_show_again.add(text)
        self._currently_displayed.remove(text)

        # invoke button commands
        button_name: str = popup_return[0]
        if custom_buttons is not None:
            if button_name in custom_buttons:
                custom_buttons[button_name]()

    def _handle_dialog(self, show_dialog: bool, title: str, log_message: str, description: str,
                       icon: _ty.Literal["Information", "Critical", "Question", "Warning", "NoIcon"],
                       custom_buttons: _ty.Dict[str, _ty.Callable] | None = None) -> None:
        """
        Handles the process of displaying a dialog based on parameters.
        :param show_dialog: Boolean indicating whether to show the dialog.
        :param title: Title of the dialog.
        :param log_message: Log message associated with the dialog.
        :param description: Additional description text.
        :param icon: Type of icon to display in the dialog.
        :return: None
        """
        if not show_dialog:
            return

        self._popup_queue.append(lambda: self._show_dialog(title, log_message, description, icon, custom_buttons))

    # "Errors"

    def warn(self, log_message: str, description: str = "", show_dialog: bool = False,
             print_log: bool = True,
             popup_title: str | None = None,
             custom_buttons: _ty.Dict[str, _ty.Callable] | None = None) -> None:
        """
        Logs a warning message and optionally displays a warning dialog.
        :param popup_title: Sets the popup window title
        :param custom_buttons: Defines additional buttons for the popup window
        :param log_message: The warning message to log.
        :param description: Additional description of the warning.
        :param show_dialog: Whether to show a dialog for the warning.
        :param print_log: Whether to print the log message.
        :return: None
        """
        return self.warning(log_message, description, show_dialog, print_log, popup_title, custom_buttons)

    def info(self, log_message: str, description: str = "", show_dialog: bool = False,
             print_log: bool = True,
             popup_title: str | None = None,
             custom_buttons: _ty.Dict[str, _ty.Callable] | None = None) -> None:
        """
        Logs an informational message and optionally displays an information dialog.
        :param log_message: The informational message to log.
        :param description: Additional description of the information.
        :param show_dialog: Whether to show a dialog for the information.
        :param print_log: Whether to print the log message.
        :param popup_title: Sets the popup window title
        :param custom_buttons: Defines additional buttons for the popup window
        :return: None
        """
        title: str = "Information"
        if popup_title is not None:
            title += f": {popup_title}"

        if print_log:
            self._logger.info(f"{log_message} {f'({description})' if description else ''}")

        if ActLogger().logging_level > INFO:
            return

        self._handle_dialog(show_dialog, title, log_message, description, "Information", custom_buttons)

    def warning(self, log_message: str, description: str = "", show_dialog: bool = False,
                print_log: bool = True,
                popup_title: str | None = None,
                custom_buttons: _ty.Dict[str, _ty.Callable] | None = None) -> None:
        """
        Logs a warning message and optionally displays a warning dialog.
        :param log_message: The warning message to log.
        :param description: Additional description of the warning.
        :param show_dialog: Whether to show a dialog for the warning.
        :param print_log: Whether to print the log message.
        :param popup_title: Sets the popup window title
        :param custom_buttons: Defines additional buttons for the popup window
        :return: None
        """
        title: str = "Warning"
        if popup_title is not None:
            title += f": {popup_title}"

        if print_log:
            self._logger.warning(f"{log_message} {f'({description})' if description else ''}")

        if ActLogger().logging_level > WARNING:
            return

        self._handle_dialog(show_dialog, title, log_message, description, "Warning", custom_buttons)

    def fatal_error(self, log_message: str, description: str = "", show_dialog: bool = False,
              print_log: bool = True,
              popup_title: str | None = None,
              custom_buttons: _ty.Dict[str, _ty.Callable] | None = None) -> None:
        """
        Logs a fatal error message and optionally displays an error dialog.
        :param log_message: The error message to log.
        :param description: Additional description of the error.
        :param show_dialog: Whether to show a dialog for the error.
        :param print_log: Whether to print the log message.
        :param popup_title: Sets the popup window title
        :param custom_buttons: Defines additional buttons for the popup window
        :return: None
        """
        self.error(log_message, description, show_dialog, print_log, popup_title, custom_buttons, error_severity="FATAL")

    def error(self, log_message: str, description: str = "", show_dialog: bool = False,
              print_log: bool = True,
              popup_title: str | None = None,
              custom_buttons: _ty.Dict[str, _ty.Callable] | None = None, *_,
              error_severity: str = "NORMAL") -> None:
        """
        Logs an error message and optionally displays an error dialog.
        :param log_message: The error message to log.
        :param description: Additional description of the error.
        :param show_dialog: Whether to show a dialog for the error.
        :param print_log: Whether to print the log message.
        :param popup_title: Sets the popup window title
        :param custom_buttons: Defines additional buttons for the popup window
        :param error_severity: Defined a custom error name.
        :return: None
        """
        title: str = f"{str(error_severity).capitalize()} Error"
        if popup_title is not None:
            title += f": {popup_title}"

        if print_log:
            self._logger.error(f"{str(error_severity)}: {log_message} {f'({description})' if description else ''}")

        if ActLogger().logging_level > ERROR:
            return

        self._handle_dialog(show_dialog, title, log_message, description, "Critical", custom_buttons)

    def debug(self, log_message: str, description: str = "", show_dialog: bool = False,
              print_log: bool = True,
              popup_title: str | None = None,
              custom_buttons: _ty.Dict[str, _ty.Callable] | None = None) -> None:
        """
        Logs a debug message and optionally displays a debug dialog, only if in development mode.
        :param log_message: The debug message to log.
        :param description: Additional description of the debug information.
        :param show_dialog: Whether to show a dialog for the debug information.
        :param print_log: Whether to print the log message.
        :param popup_title: Sets the popup window title
        :param custom_buttons: Defines additional buttons for the popup window
        :return: None
        """
        if not self._is_indev.has_value():
            return

        INDEV: bool = self._is_indev.get_value()  # config.INDEV
        if not INDEV:
            return

        title: str = "Debug"
        if popup_title is not None:
            title += f": {popup_title}"

        if print_log:
            self._logger.debug(f"{log_message} {f'({description})' if description else ''}")

        if ActLogger().logging_level > DEBUG:
            return

        self._handle_dialog(show_dialog, title, log_message, description, "NoIcon", custom_buttons)

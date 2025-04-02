"""TBA"""

# Built-in
from traceback import format_exc
from importlib.machinery import ModuleSpec
import importlib.util
import sqlite3
import shutil
import json
import time
import math
import os

# 3rd-party imports
from PySide6.QtWidgets import (QApplication, QVBoxLayout, QHBoxLayout, QWidget, QDialog, QLineEdit, QPushButton,
                               QDialogButtonBox, QLabel, QGroupBox, QFormLayout, QRadioButton, QCheckBox, QSpinBox,
                               QProgressDialog, QListWidget, QListWidgetItem, QStyledItemDelegate, QComboBox,
                               QToolButton, QFileDialog, QFontComboBox, QGraphicsProxyWidget, QGraphicsItem,
                               QProgressBar, QScrollArea, QFrame, QGraphicsPixmapItem, QStyleOptionGraphicsItem,
                               QGraphicsView, QScrollBar, QGraphicsScene, QSizePolicy)
from PySide6.QtCore import (QThread, Slot, QObject, Signal, Qt, QRectF, QPropertyAnimation, QByteArray, QEasingCurve,
                            QSize, QTimer)
from PySide6.QtGui import (QIcon, QPixmap, QTransform, QPen, QFont, QTextOption, QPainter, QWheelEvent, QResizeEvent,
                           QSurfaceFormat)
from PySide6.QtOpenGLWidgets import QOpenGLWidget

from aplustools.io.qtquick import QNoSpacingBoxLayout, QBoxDirection
from aplustools.io.concurrency import LazyDynamicThreadPoolExecutor

# Standard typing imports for aps
from abc import abstractmethod, ABCMeta
import collections.abc as _a
import typing as _ty
import types as _ts


class DBManager:
    def __init__(self, path: str):
        self._path = path
        self.conn = sqlite3.connect(path)
        self.cursor = self.conn.cursor()

    def create_table(self, table_name: str, columns: list):
        query = f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(columns)})"
        try:
            self.cursor.execute(query)
            self.conn.commit()
        except Exception as e:
            print(f"Error creating table: {e}")

    def update_info(self, info: list, table: str, columns: list):
        if len(info) != len(columns):
            raise ValueError("Length of info must match the number of columns.")

        # Assuming first column is a unique identifier like ID
        query_check = f"SELECT COUNT(*) FROM {table} WHERE {columns[0]} = ?"
        self.cursor.execute(query_check, (info[0],))
        exists = self.cursor.fetchone()[0]

        if exists:
            placeholders = ', '.join([f"{column} = ?" for column in columns])
            query = f"UPDATE {table} SET {placeholders} WHERE {columns[0]} = ?"
            try:
                self.cursor.execute(query, (*info, info[0]))
                self.conn.commit()
            except Exception as e:
                print(f"Error updating info: {e}")
        else:
            query = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join('?' for _ in info)})"
            try:
                self.cursor.execute(query, info)
                self.conn.commit()
            except Exception as e:
                print(f"Error updating info: {e}")

    def get_info(self, table: str, columns: list) -> list:
        query = f"SELECT {', '.join(columns)} FROM {table}"
        try:
            self.cursor.execute(query)
            return self.cursor.fetchall()
        except Exception as e:
            print(f"Error getting infor: {e}")
            return []

    def connect(self):
        try:
            self.conn = sqlite3.connect(self._path)
            self.cursor = self.conn.cursor()
        except Exception as e:
            print(f"Error connection to the database: {e}")

    def close(self):
        try:
            self.conn.commit()
            self.conn.close()
        except Exception as e:
            print(f"Error closing the database: {e}")


class QSmoothScrollingList(QListWidget):
    def __init__(self, parent=None, sensitivity: int = 1):
        super().__init__(parent)
        # self.setWidgetResizable(True)

        # Scroll animation setup
        self.scroll_animation = QPropertyAnimation(self.verticalScrollBar(), b"value")
        self.scroll_animation.setEasingCurve(QEasingCurve.OutCubic)  # Smoother deceleration
        self.scroll_animation.setDuration(50)  # Duration of the animation in milliseconds

        self.sensitivity = sensitivity
        self.toScroll = 0  # Total amount left to scroll

    def wheelEvent(self, event: QWheelEvent):
        angle_delta = event.angleDelta().y()
        steps = angle_delta / 120  # Standard steps calculation for a wheel event
        pixel_step = int(self.verticalScrollBar().singleStep() * self.sensitivity)

        if self.scroll_animation.state() == QPropertyAnimation.Running:
            self.scroll_animation.stop()
            self.toScroll += self.scroll_animation.endValue() - self.verticalScrollBar().value()

        current_value = self.verticalScrollBar().value()
        max_value = self.verticalScrollBar().maximum()
        min_value = self.verticalScrollBar().minimum()

        # Adjust scroll direction and calculate proposed scroll value
        self.toScroll -= pixel_step * steps
        proposed_value = current_value + self.toScroll

        # Prevent scrolling beyond the available range
        if proposed_value > max_value and steps > 0:
            self.toScroll = 0
        elif proposed_value < min_value and steps < 0:
            self.toScroll = 0

        new_value = current_value + self.toScroll
        self.scroll_animation.setStartValue(current_value)
        self.scroll_animation.setEndValue(new_value)
        self.scroll_animation.start()
        self.toScroll = 0
        event.accept()  # Mark the event as handled


class AdvancedSettingsDialog(QDialog):
    def __init__(self, parent=None, current_settings: dict = None, default_settings: dict = None, master=None, available_themes=None, export_settings_func=None):
        super().__init__(parent, Qt.WindowCloseButtonHint | Qt.WindowTitleHint)

        if default_settings is None:
            self.default_settings = {"recent_titles": [],
                                     "themes": {"light": "light_light", "dark": "dark", "font": "Segoe UI"},
                                     "settings_file_path": "",
                                     "settings_file_mode": "overwrite",
                                     "misc": {"auto_export": False, "quality_preset": "quality", "max_cached_chapters": -1}}
        else:
            self.default_settings = default_settings
        if current_settings is None:
            current_settings = self.default_settings
        self.current_settings = current_settings
        self.selected_settings = None
        self.master = master
        self.export_settings_func = export_settings_func

        if available_themes is None:
            available_themes = ('light', 'light_light', 'dark', 'light_dark', 'modern', 'old', 'default')
        self.available_themes = tuple(self._format_theme_name(theme_name) for theme_name in available_themes)

        self.setWindowTitle("Advanced Settings")
        self.resize(600, 300)

        self.mainLayout = QVBoxLayout()
        self.setLayout(self.mainLayout)

        # Recent Titles List
        self.recentTitlesGroupBox = QGroupBox("Recent Titles", self)
        self.recentTitlesLayout = QVBoxLayout(self.recentTitlesGroupBox)
        self.recentTitlesList = QSmoothScrollingList(self.recentTitlesGroupBox)
        self.recentTitlesList.itemActivated.connect(self.selected_title)
        self.recentTitlesList.verticalScrollBar().setSingleStep(1)
        self.recentTitlesLayout.addWidget(self.recentTitlesList)
        self.mainLayout.addWidget(self.recentTitlesGroupBox)

        # Theme Selection
        self.themeGroupBox = QGroupBox("Styling", self)
        self.themeLayout = QFormLayout(self.themeGroupBox)
        self.lightThemeComboBox = QComboBox(self.themeGroupBox)
        self.darkThemeComboBox = QComboBox(self.themeGroupBox)
        self.lightThemeComboBox.addItems(self.available_themes)
        self.darkThemeComboBox.addItems(self.available_themes)
        self.fontComboBox = QFontComboBox(self.themeGroupBox)
        self.fontComboBox.currentFontChanged.connect(self.change_font)
        self.themeLayout.addRow(QLabel("Light Mode Theme:"), self.lightThemeComboBox)
        self.themeLayout.addRow(QLabel("Dark Mode Theme:"), self.darkThemeComboBox)
        self.themeLayout.addRow(QLabel("Font:"), self.fontComboBox)
        self.mainLayout.addWidget(self.themeGroupBox)

        # Settings File Handling
        self.fileHandlingGroupBox = QGroupBox("Settings File Handling", self)
        self.fileHandlingLayout = QVBoxLayout(self.fileHandlingGroupBox)
        self.fileLocationLineEdit = QLineEdit(self.fileHandlingGroupBox)
        self.fileLocationLineEdit.setPlaceholderText("File Location")
        self.fileLocationToolButton = QToolButton(self.fileHandlingGroupBox)
        self.fileLocationToolButton.setText("...")
        self.fileLocationToolButton.clicked.connect(self.get_file_location)
        self.fileLocationLayout = QHBoxLayout()
        self.fileLocationLayout.addWidget(self.fileLocationLineEdit)
        self.fileLocationLayout.addWidget(self.fileLocationToolButton)
        self.overwriteRadioButton = QRadioButton("Overwrite", self.fileHandlingGroupBox)
        self.modifyRadioButton = QRadioButton("Modify", self.fileHandlingGroupBox)
        self.createNewRadioButton = QRadioButton("Create New", self.fileHandlingGroupBox)
        self.overwriteRadioButton.setChecked(True)
        self.exportSettingsPushButton = QPushButton("Export Settings-file")
        self.exportSettingsPushButton.clicked.connect(self.export_settings)
        # self.exportSettingsPushButton.setEnabled(False)
        self.loadSettingsPushButton = QPushButton("Load Settings-file")
        self.loadSettingsPushButton.clicked.connect(self.load_settings_file)
        last_layout = QHBoxLayout()
        last_layout.setContentsMargins(0, 0, 0, 0)
        last_layout.addWidget(self.createNewRadioButton)
        last_layout.addStretch()
        last_layout.addWidget(self.exportSettingsPushButton)
        last_layout.addWidget(self.loadSettingsPushButton)
        self.fileHandlingLayout.addLayout(self.fileLocationLayout)
        self.fileHandlingLayout.addWidget(self.overwriteRadioButton)
        self.fileHandlingLayout.addWidget(self.modifyRadioButton)
        self.fileHandlingLayout.addLayout(last_layout)
        self.mainLayout.addWidget(self.fileHandlingGroupBox)

        # Auto-Export and Workers
        self.miscSettingsGroupBox = QGroupBox("Chapter Management Settings", self)
        self.miscSettingsLayout = QFormLayout(self.miscSettingsGroupBox)
        self.autoExportCheckBox = QCheckBox("Enable Auto-Transfer", self.miscSettingsGroupBox)
        # self.autoExportCheckBox.setEnabled(False)
        # self.workersSpinBox = QSpinBox(self.miscSettingsGroupBox)
        # self.workersSpinBox.setRange(1, 20)
        # self.workersSpinBox.setValue(10)
        # self.workersSpinBox.setEnabled(False)
        self.quality_combo = QComboBox(self.miscSettingsGroupBox)
        self.quality_combo.addItems([
            "Best Quality",
            "Quality",
            "Size",
            "Smallest Size"
        ])
        self.miscSettingsLayout.addRow(self.autoExportCheckBox)
        # self.miscSettingsLayout.addRow(QLabel("Number of Workers:"), self.workersSpinBox)
        self.miscSettingsLayout.addRow(QLabel("Auto-Transfer Quality preset:"), self.quality_combo)
        self.max_cached_chapters_spinbox = QSpinBox(self.miscSettingsGroupBox, minimum=-1, singleStep=1)
        self.miscSettingsLayout.addRow(QLabel("Max cached chapters:"), self.max_cached_chapters_spinbox)

        self.mainLayout.addWidget(self.miscSettingsGroupBox)

        self.load_settings(self.current_settings)

        # Buttons for actions
        self.buttonsLayout = QHBoxLayout()

        self.revertLastButton = QPushButton("Revert to Last Saved", self)
        self.defaultButton = QPushButton("Revert to Default", self)
        self.buttonsLayout.addWidget(self.revertLastButton)
        self.buttonsLayout.addWidget(self.defaultButton)

        self.buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.buttonsLayout.addWidget(self.buttonBox)

        self.mainLayout.addLayout(self.buttonsLayout)

        # Connect revert buttons
        self.revertLastButton.clicked.connect(self.revert_last_saved)
        self.defaultButton.clicked.connect(self.revert_to_default)

        QTimer.singleShot(10, self.fix_size)

    def fix_size(self):
        self.setFixedSize(self.size())

    def selected_title(self, item: QListWidgetItem):
        name = item.text()
        idx = self.recentTitlesList.row(item)
        if not self.master.settings.is_open:
            self.master.settings.connect()
        self.reject()
        self.master.selected_chosen_item(self.current_settings["recent_titles"][idx], toggle_search_bar=False)
        self.master.toggle_side_menu()

    def get_file_location(self):
        file_path, _ = QFileDialog.getSaveFileName(self, 'Choose/Save File', self.fileLocationLineEdit.text(),
                                                  'DataBase Files (*.db);;Json Files (*.json *.yaml *.yml)',
                                                  'Json Files (*.json *.yaml *.yml)'
                                                   if self.fileLocationLineEdit.text().endswith((".json", ".yaml", ".yml"))
                                                   else 'DataBase Files (*.db)')
        if not file_path:  # No file was selected
            return
        self.fileLocationLineEdit.setText(file_path)

    def export_settings(self):
        if self.export_settings_func is not None:
            self.export_settings_func({
            "recent_titles": self.current_settings["recent_titles"],
            "themes": {
                "light": self._save_theme(self.lightThemeComboBox.currentText()),
                "dark": self._save_theme(self.darkThemeComboBox.currentText()),
                "font": self.fontComboBox.currentText()},
            "settings_file_path": self.fileLocationLineEdit.text(),
            "settings_file_mode": "overwrite" if self.overwriteRadioButton.isChecked() else "modify" if self.modifyRadioButton.isChecked() else "create_new",
            "misc": {"auto_export": self.autoExportCheckBox.isChecked(), "quality_preset": self.quality_combo.currentText().lower().replace(" ", "_"),
                     "max_cached_chapters": self.max_cached_chapters_spinbox.value()}})
                     #"num_workers": self.workersSpinBox.value()}})

    def load_settings_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, 'Choose File', self.fileLocationLineEdit.text(),
                                                  'DataBase Files (*.db);;Json Files (*.json *.yaml *.yml)',
                                                  'Json Files (*.json *.yaml *.yml)'
                                                   if self.fileLocationLineEdit.text().endswith((".json", ".yaml", ".yml"))
                                                   else 'DataBase Files (*.db)')
        if not file_path:  # No file was selected
            return

        if file_path.endswith(".db"):
            self.replace_database(file_path)
        elif file_path.endswith((".json", ".yaml")):
            self.import_settings_from_json(file_path)

        if not self.master.settings.is_open:
            self.master.settings.connect()
        self.master.reload_window_title()
        self.master.reload_gui()
        self.reject()

    def replace_database(self, new_db_path):
        """Replace the existing settings database with a new one."""
        temp_path = os.path.join(self.master.data_folder, "temp_data.db")
        try:
            # Safely attempt to replace the database
            shutil.copyfile(new_db_path, temp_path)
            os.remove(os.path.join(self.master.data_folder, "data.db"))
            shutil.move(temp_path, os.path.join(self.master.data_folder, "data.db"))
        except Exception as e:
            print(f"Failed to replace the database: {e}")
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def import_settings_from_json(self, json_path):
        """Import settings from a JSON file into the SQLite database."""
        try:
            with open(json_path, 'r') as file:
                settings_data = json.load(file).get("settings")

            db_path = os.path.join(self.master.data_folder, "data.db")
            connection = sqlite3.connect(db_path)
            cursor = connection.cursor()

            # Assuming the table and columns for settings already exist and are named appropriately
            for dic in settings_data:
                key, value = dic["key"], dic["value"]
                cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))

            connection.commit()
        except json.JSONDecodeError:
            print("Invalid JSON file.")
        except Exception as e:
            print(f"Error while importing settings from JSON: {e}")
        finally:
            cursor.close()
            connection.close()

    def _format_theme_name(self, theme_name: str):
        """
        Formats the theme name by adding parentheses if needed and appending ' Theme' if the name includes 'light' or 'dark'.

        Args:
        theme (str): The theme name.

        Returns:
        str: The formatted theme name.
        """
        # Add parentheses to the first word if there are more than 2
        formatted_name = ("(" if "_" in theme_name else "") + theme_name.replace("_", ") ", 1).replace("_", " ").title()

        # Append 'Theme' if 'light' or 'dark' is part of the theme name
        if "light" in theme_name or "dark" in theme_name:
            formatted_name += " Theme"

        return formatted_name

    def format_title(self, title: str) -> str:
        return ' '.join(word[0].upper() + word[1:] if word else '' for word in title.lower().split())

    def load_settings(self, settings: dict) -> None:
        self.recentTitlesList.clear()
        recent_titles: list[str] = settings.get("recent_titles")
        recent_titles.reverse()
        for recent_title in recent_titles:
            prov, title, chap, *_ = recent_title.split("\x00") + ["", ""]
            if not _:
                title = prov
                prov = ""
                chap = "0"
            self.recentTitlesList.addItem(f"{prov}: {self.format_title(title)}, Ch {chap}")

        light_theme = settings.get("themes").get("light")
        dark_theme = settings.get("themes").get("dark")
        self.lightThemeComboBox.setCurrentText(self._format_theme_name(light_theme))
        self.darkThemeComboBox.setCurrentText(self._format_theme_name(dark_theme))
        self.fontComboBox.setCurrentText(settings.get("themes").get("font"))

        self.fileLocationLineEdit.setText(settings.get("settings_file_path", ""))

        sett_mode = settings.get("settings_file_mode")
        if sett_mode == "overwrite":
            self.overwriteRadioButton.setChecked(True)
            self.modifyRadioButton.setChecked(False)
            self.createNewRadioButton.setChecked(False)
        elif sett_mode == "modify":
            self.overwriteRadioButton.setChecked(False)
            self.modifyRadioButton.setChecked(True)
            self.createNewRadioButton.setChecked(False)
        else:
            self.overwriteRadioButton.setChecked(False)
            self.modifyRadioButton.setChecked(False)
            self.createNewRadioButton.setChecked(True)

        self.autoExportCheckBox.setChecked(settings.get("misc").get("auto_export") is True)
        # self.workersSpinBox.setValue(settings.get("misc").get("num_workers"))
        self.quality_combo.setCurrentText(settings.get("misc").get("quality_preset").replace("_", " ").title())
        self.max_cached_chapters_spinbox.setValue(settings.get("misc").get("max_cached_chapters"))

    def revert_last_saved(self):
        # Logic to revert settings to the last saved state
        self.load_settings(self.current_settings)

    def revert_to_default(self):
        # Logic to reset settings to their defaults
        self.load_settings(self.default_settings)

    def change_font(self, font):
        base_font_size = 8
        dpi = self.parent().app.primaryScreen().logicalDotsPerInch()
        scale_factor = dpi / 96
        scaled_font_size = base_font_size * scale_factor
        font = QFont(self.fontComboBox.currentText(), scaled_font_size)

        self.setFont(font)
        for child in self.findChildren(QWidget):
            child.setFont(font)
        self.update()
        self.repaint()

    def _save_theme(self, theme_display_name):
        stripped_theme_name = theme_display_name.lstrip("(").lower().replace(") ", "_")
        if "light" in stripped_theme_name or "dark" in stripped_theme_name:
            stripped_theme_name = stripped_theme_name.removesuffix(" theme")
        return stripped_theme_name.replace(" ", "_")

    def accept(self):
        # Collect all settings here for processing
        self.selected_settings = {
            "recent_titles": self.current_settings["recent_titles"],
            "themes": {
                "light": self._save_theme(self.lightThemeComboBox.currentText()),
                "dark": self._save_theme(self.darkThemeComboBox.currentText()),
                "font": self.fontComboBox.currentText()},
            "settings_file_path": self.fileLocationLineEdit.text(),
            "settings_file_mode": "overwrite" if self.overwriteRadioButton.isChecked() else "modify" if self.modifyRadioButton.isChecked() else "create_new",
            "misc": {"auto_export": self.autoExportCheckBox.isChecked(), "quality_preset": self.quality_combo.currentText().lower().replace(" ", "_"),
                     "max_cached_chapters": self.max_cached_chapters_spinbox.value()}}
                     # "num_workers": self.workersSpinBox.value()}}

        super().accept()

    def reject(self):
        super().reject()


class TaskRunner(QThread):
    task_completed = Signal(bool, object)
    progress_signal = Signal(int)

    def __init__(self, func: _ty.Callable[[_ty.Any], _ty.Any], args: tuple[_ty.Any, ...], kwargs: dict[str, _ty.Any] | None) -> None:
        super().__init__()
        self.func: _ty.Callable[[_ty.Any], _ty.Any] = func
        self.args: tuple[_ty.Any, ...] = args
        self.kwargs: dict[str, _ty.Any] = kwargs or {}
        self.is_running: bool = True
        self.result: _ty.Any | None = None
        self.success: bool = False

    class TaskCanceledException(Exception):
        """Exception to be raised when the task is canceled"""
        def __init__(self, message="A intended error occured"):
            self.message = message
            super().__init__(self.message)

    def run(self):
        if not self.is_running:
            return
        try:
            print("Directly executing")
            self.worker_func()
            self.task_completed.emit(self.success and self.result, self.result)  # As the result is a bool to check status

        except Exception as e:
            self.task_completed.emit(False, None)
            print(e)

    def worker_func(self):
        try:
            gen = self.func(*self.args, **self.kwargs, progress_signal=self.progress_signal)
            while True:
                try:
                    next(gen)
                except StopIteration as e:
                    result = e.value
                    break
            self.result = result
            self.success = True
        except SystemExit:
            self.success = False
            self.result = None
            print("Task was forcefully stopped.")
        except Exception as e:
            self.success = False
            self.result = None
            print(f"Error in TaskRunner: {format_exc()}")

    def stop(self):
        print("Task is stopping.")
        self.is_running = False
        if not self.isFinished():
            self.wait()


class SyncProgressEmitter(QObject):
    progress_signal = Signal(int)


class CustomProgressDialog(QProgressDialog):
    def __init__(self, parent: QWidget, window_title: str, window_label: str = "Doing a task...", button_text: str = "Cancel",
                 new_thread: bool = True, func: _ty.Callable[[_ty.Any], _ty.Any] = lambda _: None,
                 args: tuple[_ty.Any, ...] = (), kwargs: dict[str, _ty.Any] | None = None) -> None:
        super().__init__("", button_text, 0, 100, parent=parent)
        self.setWindowTitle(window_title)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setAutoClose(False)
        self.setAutoReset(False)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        self.task_successful: bool = False
        # self.current_value: int = 0
        # self.last_value: int = 0

        self.setup_gui(window_label)

        if new_thread:
            self.taskRunner = TaskRunner(func, args, kwargs)
            self.taskRunner.task_completed.connect(self.onTaskCompleted)
            self.taskRunner.progress_signal.connect(self.setValue)  # Connect progress updates
            QTimer.singleShot(50, self.taskRunner.start)
        else:
            self.sync_emitter = SyncProgressEmitter()
            self.sync_emitter.progress_signal.connect(self.setValue)
            QTimer.singleShot(50, lambda: self._run_sync_task(func, args, kwargs))
        self.canceled.connect(self.cancelTask)

        # self.timer = QTimer(self)
        # self.timer.timeout.connect(self.updateProgress)
        # self.timer.start(100)

    def setup_gui(self, window_label: str) -> None:
        layout = QVBoxLayout(self)
        self.window_label = QLabel(window_label, self)
        layout.addWidget(self.window_label)
        layout.setAlignment(self.window_label, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        self.setLayout(layout)

        # Set the dialog to be fixed size
        self.adjustSize()  # Adjust size based on layout and contents
        self.setFixedSize(self.size())  # Lock the current size after adjusting

    # def updateProgress(self):
    #     if self.value() <= 100 and not self.wasCanceled() and self.taskRunner.isRunning():
    #         if self.current_value == 0 and self.value() < 10:
    #             self.setValue(self.value() + 1)
    #             time.sleep(random.randint(2, 10) * 0.1)
    #         elif self.current_value >= 10:
    #             self.smooth_value()
    #         QApplication.processEvents()
    #
    # def smooth_value(self):
    #     # If the difference is significant, set the value immediately
    #     if abs(self.current_value - self.last_value) > 10:  # You can adjust this threshold
    #         self.setValue(self.current_value)
    #         self.last_value = self.current_value
    #         return
    #
    #     for i in range(max(10, self.last_value), self.current_value):
    #         self.setValue(i + 1)
    #         self.last_value = i + 1
    #         time.sleep(0.1)

    @Slot(bool, object)
    def onTaskCompleted(self, success, result):
        print("Task completed method called.")
        if hasattr(self, "taskRunner"):
            self.taskRunner.quit()
            self.taskRunner.wait()

        if not self.wasCanceled():
            if success:
                self.task_successful = True
                self.setValue(100)
                print("Task completed successfully! Result:" + str(
                    "Finished" if result else "Not finished"))  # Adjust as needed
                QTimer.singleShot(1000, self.accept)  # Close after 1 second if successful
            else:
                self.window_label.setText("Task failed!")
                self.setCancelButtonText("Close")
                QTimer.singleShot(1, self.accept)  # Close after 1 second if successful

    def _run_sync_task(self, func, args, kwargs):
        try:
            gen = func(*args, **(kwargs or {}), progress_signal=self.sync_emitter.progress_signal)
            while True:
                try:
                    next(gen)
                    QApplication.processEvents()
                except StopIteration as e:
                    result = e.value
                    break
            self.onTaskCompleted(True and result, result)
        except Exception:
            print("[Dialog] Sync task failed:")
            print(format_exc())
            self.onTaskCompleted(False, None)

    def cancelTask(self):
        if hasattr(self, "taskRunner"):
            if self.taskRunner.isRunning():
                self.taskRunner.terminate()
        else:  # Directly executing
            ...
        self.window_label.setText("Task cancelled")
        self.close()

    def closeEvent(self, event):
        self.cancelTask()
        event.accept()


class TaskWidget(QWidget):
    task_done = Signal(object)  # Signal to notify TaskBar that task is done

    def __init__(self, name: str, func, args=(), kwargs=None, new_thread=True):
        super().__init__()
        self.name = name
        self.func = func
        self.args = args
        self.kwargs = kwargs or {}
        # self.new_thread = new_thread
        self.task_successful = False
        self.task_canceled = False

        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(4, 2, 4, 2)
        self.main_layout.setSpacing(6)

        self.label = QLabel(f"{self.name}:")
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setTextVisible(True)
        self.progress.setValue(0)

        self.cancel_button = QPushButton("X")
        self.cancel_button.setFixedSize(20, 20)
        self.cancel_button.clicked.connect(self.cancelTask)

        self.main_layout.addWidget(self.label)
        self.main_layout.addWidget(self.progress)
        self.main_layout.addWidget(self.cancel_button)

        self.task_runner = TaskRunner(self.func, self.args, self.kwargs)
        self.task_runner.task_completed.connect(self.onTaskCompleted)
        self.task_runner.progress_signal.connect(self.set_value)

        self.last_value = 0
        self.current_value = 0
        self._smooth_timer = QTimer(self)
        self._smooth_timer.timeout.connect(self.updateProgressSmooth)
        self._smooth_timer.start(100)

        QTimer.singleShot(50, self.task_runner.start)

    def set_value(self, value: int):
        self.current_value = value

    def updateProgressSmooth(self):
        if not self.task_runner.isRunning():
            return

        if self.current_value == 0 and self.progress.value() < 10:
            self.progress.setValue(self.progress.value() + 1)
            time.sleep(0.1)
        elif self.current_value >= 10:
            self.smooth_value()

    def smooth_value(self):
        if abs(self.current_value - self.last_value) > 10:
            self.progress.setValue(self.current_value)
            self.last_value = self.current_value
            return

        for i in range(self.last_value + 1, self.current_value + 1):
            self.progress.setValue(i)
            self.last_value = i
            time.sleep(0.01)

    @Slot(bool, object)
    def onTaskCompleted(self, success: bool, result):
        self.task_runner.quit()
        self.task_runner.wait()
        self.progress.setValue(100)
        self._smooth_timer.stop()
        if not self.task_canceled:
            if success:
                self.task_successful = True
        self.task_done.emit(self)

    def cancelTask(self):
        if self.task_runner.isRunning():
            self.task_runner.stop()
            self.task_runner.wait()
        self.task_done.emit(self)
        self.task_canceled = True
        # self.deleteLater()


class TaskBar(QWidget):
    def __init__(self, parent=None, mode: str = "last"):
        super().__init__(parent)
        self.setFixedHeight(28)
        self.setVisible(False)

        self.mode = mode
        self.tasks: list[TaskWidget] = []
        self.current_display_task: TaskWidget | None = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(10)

        self.label = QLabel("")
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(14)

        layout.addWidget(self.label)
        layout.addWidget(self.progress)

        self.task_popup = TaskPopup(self)
        self.task_popup.setObjectName("TaskPopup")

    def mousePressEvent(self, event):
        if self.task_popup.isVisible():
            self.task_popup.hide()
        else:
            self.task_popup.reposition()
            self.task_popup.show()

    def add_task(self, name: str, func, args=(), kwargs=None) -> TaskWidget:
        task = TaskWidget(name, func=func, args=args, kwargs=kwargs)
        task.task_done.connect(lambda: self._remove_task(task))

        self.tasks.append(task)
        self.task_popup.add_task(task)
        self._update_display()
        self.setVisible(True)
        return task

    def _remove_task(self, task: TaskWidget):
        if task in self.tasks:
            self.tasks.remove(task)
        if task == self.current_display_task:
            self.current_display_task.progress.valueChanged.disconnect(self.progress.setValue)
            self.current_display_task = None
        self.task_popup.remove_task(task)
        self._update_display()

        if not self.tasks:
            self.setVisible(False)
            self.task_popup.hide()

    def active_tasks(self):
        return self.tasks# [t for t in self.tasks if not t.is_done]

    def task_count(self) -> int:
        return len(self.active_tasks())

    def _update_display(self) -> None:
        if not self.tasks:
            self.setVisible(False)
            return

        task_to_show: TaskWidget | None = None
        if self.mode == "first":
            task_to_show = self.tasks[0]
        elif self.mode == "last":
            task_to_show = self.tasks[-1]
        elif self.mode == "most_progressed":
            task_to_show = max(self.tasks, key=lambda t: t.progress.value(), default=None)

        if self.current_display_task is not None:
            self.current_display_task.progress.valueChanged.disconnect(self.progress.setValue)
        self.current_display_task = task_to_show
        if task_to_show is not None:
            self.label.setText(task_to_show.label.text())
            task_to_show.progress.valueChanged.connect(self.progress.setValue)


class TaskPopup(QWidget):
    MAX_VISIBLE_TASKS = 3

    def __init__(self, task_bar: QWidget):
        super().__init__(task_bar)
        self.task_bar = task_bar
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_StyledBackground, True)
        # self.setAttribute(Qt.WA_TranslucentBackground)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(4, 4, 4, 4)

        # Minimize/close button
        self.header = QHBoxLayout()
        self.header.setContentsMargins(0, 0, 0, 0)
        self.header.setSpacing(0)

        self.header.addStretch()
        self.minimize_btn = QPushButton("✕")
        self.minimize_btn.setFixedSize(18, 18)
        self.minimize_btn.setStyleSheet("QPushButton { border: none; }")
        self.minimize_btn.clicked.connect(self.hide)
        self.header.addWidget(self.minimize_btn)
        self.main_layout.addLayout(self.header)

        # Scroll area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.task_container = QWidget()
        self.task_layout = QVBoxLayout(self.task_container)
        self.task_layout.setContentsMargins(0, 0, 0, 0)
        self.task_layout.setSpacing(2)

        self.scroll_area.setWidget(self.task_container)
        self.main_layout.addWidget(self.scroll_area)

        self.setFixedWidth(300)

    def add_task(self, task: TaskWidget):
        self.task_layout.addWidget(task)
        self._adjust_height_and_reposition()

    def remove_task(self, task: TaskWidget):
        for i in reversed(range(self.task_layout.count())):
            item = self.task_layout.itemAt(i)
            if item.widget() == task:
                self.task_layout.removeWidget(task)
                task.deleteLater()
                break
        self._adjust_height_and_reposition()

    def _adjust_height_and_reposition(self):
        count = self.task_layout.count()
        if count == 0:
            self.hide()
            return

        max_tasks = min(count, self.MAX_VISIBLE_TASKS)

        height = 0
        for i in range(max_tasks):
            item = self.task_layout.itemAt(i)
            if item:
                height += item.widget().sizeHint().height()
        height += self.task_layout.spacing() * (max_tasks - 1)

        header_height = self.minimize_btn.sizeHint().height() + self.main_layout.spacing()
        self.setFixedHeight(header_height + height + 8)  # some padding

        if count > self.MAX_VISIBLE_TASKS:
            self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        else:
            self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.reposition()

    def reposition(self):
        """Move popup directly above the task bar"""
        global_pos = self.task_bar.mapToGlobal(self.task_bar.rect().bottomLeft())
        self.move(global_pos.x(), global_pos.y() - self.height() - 30)


class SearchResultItem(QWidget):
    def __init__(self, title, description, icon_path):
        super().__init__()

        self.layout = QHBoxLayout(self)

        self.icon_label = QLabel(self)
        self.icon_label.setPixmap(QPixmap(icon_path).scaledToWidth(50, Qt.SmoothTransformation))
        self.layout.addWidget(self.icon_label)

        self.text_layout = QVBoxLayout()
        self.title_label = QLabel(title)
        self.title_label.setFont(QFont('Arial', 14, QFont.Bold))
        self.text_layout.addWidget(self.title_label)

        self.description_label = QLabel(description)
        self.description_label.setFont(QFont('Arial', 10))
        self.text_layout.addWidget(self.description_label)

        self.layout.addLayout(self.text_layout)


class SearchWidget(QWidget):
    selectedItem = Signal(str)

    def __init__(self, search_results_func):
        super().__init__()
        self.initUI()
        self.search_results_func = search_results_func

    def set_search_results_func(self, new_func):
        self.search_results_func = new_func

    def sizeHint(self):
        search_bar_size_hint = self.search_bar.sizeHint()
        if self.results_list.isVisible():
            results_list_size_hint = self.results_list.sizeHint()
            # Combine the heights and take the maximum width
            combined_height = search_bar_size_hint.height() + results_list_size_hint.height()
            combined_width = max(search_bar_size_hint.width(), results_list_size_hint.width())
            return QSize(combined_width, combined_height)
        else:
            return search_bar_size_hint  # Return size hint of search_bar

    def minimumSizeHint(self):
        return self.search_bar.minimumSizeHint()

    def initUI(self):
        search_bar_layout = QHBoxLayout()
        search_bar_layout.setContentsMargins(0, 0, 0, 0)
        self.search_bar = QLineEdit(self)
        self.search_bar.setObjectName("search_widget_line_edit")
        self.search_bar.setPlaceholderText("[Enter] to search...")
        self.search_bar.editingFinished.connect(self.on_text_finished)
        self.search_bar.textChanged.connect(self.on_text_changed)
        self.search_bar.returnPressed.connect(self.on_return_pressed)
        search_bar_layout.addWidget(self.search_bar)
        search_button = QPushButton("Search")
        search_button.clicked.connect(self.on_text_finished)
        # search_button.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
        search_bar_layout.addWidget(search_button)

        self.results_list = QListWidget(self)
        self.results_list.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Ignored)
        self.results_list.hide()
        self.results_list.itemActivated.connect(self.on_item_activated)

        layout = QVBoxLayout(self)
        layout.addLayout(search_bar_layout)
        layout.addWidget(self.results_list)
        layout.setContentsMargins(0, 0, 0, 0)  # Set margins to zero
        layout.setSpacing(0)  # Set spacing to zero

    def on_text_changed(self) -> None:
        self.results_list.clear()
        self.results_list.hide()
        self.adjustSize()
        self.updateGeometry()  # Notify the layout system of potential size change
        self.results_list.updateGeometry()  # Notify the layout system of potential size change

    def on_text_finished(self):
        text = self.search_bar.text()
        self.results_list.clear()
        if text:  #  and self.search_bar.hasFocus()
            # Assume get_search_results is a function that returns a list of tuples with the result text and icon path.
            results = self.search_results_func(text)
            print("Search Results: ", results)
            for result_text, icon_path in results:
                item = QListWidgetItem(result_text)
                item.setIcon(QIcon(os.path.abspath(icon_path)))
                self.results_list.addItem(item)
            self.results_list.show()
        else:
            self.results_list.hide()

        self.adjustSize()
        self.updateGeometry()  # Notify the layout system of potential size change
        self.results_list.updateGeometry()  # Notify the layout system of potential size change
        # self.window().adjustSize()  # Adjust the size of the parent window

    def on_return_pressed(self):
        item = self.results_list.currentItem() or self.results_list.item(0)
        if item:
            self.select_item(item)

    def on_item_activated(self, item):
        self.select_item(item)

    def select_item(self, item):
        title = item.text()
        print(f'Selected: {title}')
        self.search_bar.setText('')
        self.results_list.hide()
        self.selectedItem.emit(title)


class QScalingGraphicPixmapItem(QGraphicsPixmapItem, QObject):
    """TBA"""
    _pixmapLoaded = Signal(QPixmap)

    def __init__(self, abs_pixmap_path: str, width_scaling_threshold: float = 0.1,
                 height_scaling_threshold: float = 0.1, lq_resize_count_threshold: int = 1000,
                 update_tick_lq_addition: int = 100, /, use_high_quality_transform: bool = True, load_now: bool = True) -> None:
        QGraphicsPixmapItem.__init__(self)
        QObject.__init__(self)
        self._abs_pixmap_path: str = os.path.abspath(abs_pixmap_path)
        self._width_scaling_threshold: float = max(0.0, min(0.99, width_scaling_threshold))
        self._height_scaling_threshold: float = max(0.0, min(0.99, height_scaling_threshold))
        self._lower_width_limit: int = 0
        self._upper_width_limit: int = 0
        self._lower_height_limit: int = 0
        self._upper_height_limit: int = 0

        self._int_attr: _ty.Literal["width", "height"] = "width"
        self.lq_resize_count_threshold: int = lq_resize_count_threshold
        self.update_tick_lq_addition: int = update_tick_lq_addition
        self._lq_resize_count: int = 0

        self._original_pixmap: QPixmap
        self._width: int
        self._height: int
        self._is_loaded: bool
        self._is_hidden: bool
        self._true_width: float
        self._true_height: float
        self._pixmap_width: int
        self._pixmap_height: int
        if load_now:
            self._original_pixmap = QPixmap(self._abs_pixmap_path)
            self._is_loaded = True
            self._is_hidden = True
            self._width = self.pixmap().width()
            self._height = self.pixmap().height()
            self._true_width = float(self.pixmap().width())
            self._true_height = float(self.pixmap().height())
            self._pixmap_width = self.pixmap().width()
            self._pixmap_height = self.pixmap().height()
        else:
            self._is_loaded = False
            self._is_hidden = True

        if use_high_quality_transform:
            self.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
        else:
            self.setTransformationMode(Qt.TransformationMode.FastTransformation)

        self._highlight: Qt.GlobalColor = Qt.GlobalColor.black
        self.idx: int = -1

        self._pixmapLoaded.connect(self.setPixmap)

    def get_width_scaling_threshold(self) -> float:
        """
        Get the current width scaling threshold.

        Returns:
            float: The width scaling threshold (0.0 to 0.99).
        """
        return self._width_scaling_threshold

    def set_width_scaling_threshold(self, threshold: float) -> None:
        """
        Set the width scaling threshold, ensuring it stays within valid bounds.

        Args:
            threshold (float): The desired width scaling threshold.
                              Must be between 0.0 and 0.99.
        """
        self._width_scaling_threshold = max(0.0, min(0.99, threshold))

    def get_height_scaling_threshold(self) -> float:
        """
        Get the current height scaling threshold.

        Returns:
            float: The height scaling threshold (0.0 to 0.99).
        """
        return self._height_scaling_threshold

    def set_height_scaling_threshold(self, threshold: float) -> None:
        """
        Set the height scaling threshold, ensuring it stays within valid bounds.

        Args:
            threshold (float): The desired height scaling threshold.
                               Must be between 0.0 and 0.99.
        """
        self._height_scaling_threshold = max(0.0, min(0.99, threshold))

    def get_is_loaded(self) -> bool:
        """
        Check if the image is loaded.

        Returns:
            bool: True if the image is loaded, False otherwise.
        """
        return self._is_loaded

    def get_is_hidden(self) -> bool:
        """
        Check if the image is currently hidden.

        Returns:
            bool: True if the image is hidden, False otherwise.
        """
        return self._is_hidden

    def get_width(self) -> int:
        """
        Get the current width of the item.

        Returns:
            int: The width of the item in pixels.
        """
        return self._width

    def get_height(self) -> int:
        """
        Get the current height of the item.

        Returns:
            int: The height of the item in pixels.
        """
        return self._height

    def get_true_width(self) -> float:
        """
        Get the actual width after transformations are applied.

        This reflects the width after any scaling transformations,
        meaning it may differ from the original pixmap width.

        Returns:
            float: The transformed width in pixels.
        """
        return self._true_width

    def get_true_height(self) -> float:
        """
        Get the actual height after transformations are applied.

        This reflects the height after any scaling transformations,
        meaning it may differ from the original pixmap height.

        Returns:
            float: The transformed height in pixels.
        """
        return self._true_height

    def get_pixmap_width(self) -> int:
        """
        Get the original (untransformed) width of the pixmap. Idk this is needed to keep the bounding box in check.

        Returns:
            float: The width of the underlying pixmap before any transformations.
        """
        return self._pixmap_width

    def get_pixmap_height(self) -> int:
        """
        Get the original (untransformed) height of the pixmap. Idk this is needed to keep the bounding box in check.

        Returns:
            float: The height of the underlying pixmap before any transformations.
        """
        return self._pixmap_height

    def load(self) -> None:
        """TBA"""
        if self._is_loaded:
            return None
        self._original_pixmap = QPixmap(self._abs_pixmap_path)
        self._is_loaded = True
        if self._original_pixmap.isNull():
            raise ValueError("Image could not be loaded.")
        self._pixmapLoaded.emit(self._original_pixmap.scaled(int(self._true_width), int(self._true_height)))
        return None

    def show_pixmap(self) -> None:
        """TBA"""
        if not self._is_loaded:
            self.load()
        if not self._is_hidden:
            return None
        self._is_hidden = False
        self._pixmapLoaded.emit(self._original_pixmap.scaled(int(self._true_width), int(self._true_height)))

    def unload(self) -> None:
        """TBA"""
        if not self._is_loaded:
            return None
        self._original_pixmap = QPixmap(self._original_pixmap.width(), self._original_pixmap.height())
        self._original_pixmap.fill(Qt.GlobalColor.transparent)
        self._pixmapLoaded.emit(self._original_pixmap.scaled(int(self._true_width), int(self._true_height)))
        self._is_loaded = False
        return None

    def hide_pixmap(self) -> None:
        """TBA"""
        if self._is_hidden:
            return None
        self._is_hidden = True
        # self._pixmapLoaded.emit(QPixmap(self._width, self._height))
        return None

    def ensure_loaded(self) -> None:
        """TBA"""
        if not self._is_loaded:
            self.load()
        return None

    def ensure_visible(self) -> None:
        """TBA"""
        if self._is_hidden:
            self.show_pixmap()
        return None

    def ensure_unloaded(self) -> None:
        """TBA"""
        if self._is_loaded:
            self.unload()
        return None

    def ensure_hidden(self) -> None:
        """TBA"""
        if not self._is_hidden:
            self.hide_pixmap()
        return None

    def first_load(self) -> None:
        """Loads all variables from the original pixmap, as done one a first load"""
        self._original_pixmap = QPixmap(self._abs_pixmap_path)
        self._is_loaded = True
        if self._original_pixmap.isNull():
            raise ValueError("Image could not be loaded.")
        self._width = self._original_pixmap.width()
        self._height = self._original_pixmap.height()
        self._true_width = float(self._original_pixmap.width())
        self._true_height = float(self._original_pixmap.height())
        self._pixmap_width = self._original_pixmap.width()
        self._pixmap_height = self._original_pixmap.height()

    def update_tick(self) -> None:
        """Does one update tick"""
        if self._lq_resize_count != 0:  # Last resize wasn't high quality
            self._lq_resize_count += self.update_tick_lq_addition
            if self._lq_resize_count > self.lq_resize_count_threshold:  # Resize if over limit
                scaled_pixmap = self._original_pixmap.scaled(math.ceil(self._true_width), math.ceil(self._true_height), mode=Qt.TransformationMode.SmoothTransformation)
                self._pixmapLoaded.emit(scaled_pixmap)
                self.resetTransform()
                self._lq_resize_count = 0

    def scale_original_size_to_old(self, width: int | None = None, height: int | None = None,
                                   keep_aspect_ratio: bool = False) -> tuple[int, int]:  # This method is just not dependable for actual gui, instead of estimations
        """TBA"""
        aspect_ratio = self._original_pixmap.width() / self._original_pixmap.height()
        if width is not None:
            return width, int(width / aspect_ratio)
        elif height is not None:
            return int(height * aspect_ratio), height
        elif width is not None and height is not None:
            if keep_aspect_ratio:
                if width < height:
                    return self.scale_original_size_to_old(width=width)
                else:
                    return self.scale_original_size_to_old(height=height)
            else:
                return width, height
        raise RuntimeError("")

    def scale_original_size_to(self, width: int | None = None, height: int | None = None) -> tuple[int, int]:
        """Inefficient, but precise"""
        if self._original_pixmap is None or self._original_pixmap.isNull():
            raise ValueError("Original pixmap is not loaded.")

        original_width = self._original_pixmap.width()
        original_height = self._original_pixmap.height()

        if original_width == 0 or original_height == 0:
            raise ValueError("Original pixmap has zero dimensions.")

        if height is not None and width is not None:
            return width, height
        elif height is not None:
            scaled_pixmap = self._original_pixmap.scaledToHeight(height, Qt.TransformationMode.SmoothTransformation)
            return scaled_pixmap.width(), scaled_pixmap.height()
        elif width is not None:
            scaled_pixmap = self._original_pixmap.scaledToWidth(width, Qt.TransformationMode.SmoothTransformation)
            return scaled_pixmap.width(), scaled_pixmap.height()

        raise ValueError("At least one of width or height must be provided.")

    def _get_true_width(self) -> float:
        """TBA"""
        return self.pixmap().width() * self.transform().m11()  # m11() is the horizontal scaling factor

    def _get_true_height(self) -> float:
        """TBA"""
        return self.pixmap().height() * self.transform().m22()  # m22() is the vertical scaling factor

    def scaledToWidth(self, width: int) -> None:
        """TBA"""
        if self._is_hidden or not self._is_loaded:
            width, height = self.scale_original_size_to(width=width)
            self._true_width = self._width = width
            self._true_height = self._height = height
            return None
        if (width < self._lower_width_limit or width > self._upper_width_limit
                or self._lq_resize_count > self.lq_resize_count_threshold):
            # Use high-quality pixmap scaling when significant downscaling is required
            scaled_pixmap = self._original_pixmap.scaledToWidth(width, self.transformationMode())
            self._pixmapLoaded.emit(scaled_pixmap)
            self.resetTransform()
            self._lower_width_limit = int(width * (1.0 - self._width_scaling_threshold))
            self._upper_width_limit = int(width * (1.0 + self._width_scaling_threshold))
            self._lq_resize_count = 0
        elif self._true_width != width:
            # Use transformations for minor scaling adjustments
            scale_factor = width / self._true_width
            new_transform = self.transform().scale(scale_factor, scale_factor)
            self.setTransform(new_transform)
            self._lq_resize_count += 1

        # Update width and height based on the transformation
        self._width = self._true_width = width
        self._true_height = self._get_true_height()
        self._height = int(self._true_height)
        return None

    def scaledToHeight(self, height: int) -> None:
        """TBA"""
        if self._is_hidden or not self._is_loaded:
            width, height = self.scale_original_size_to(height=height)
            self._true_width = self._width = width
            self._true_height = self._height = height
            return None
        if (height < self._lower_height_limit or height > self._upper_height_limit
                or self._lq_resize_count > self.lq_resize_count_threshold):
            # Use high-quality pixmap scaling when significant downscaling is required
            scaled_pixmap = self._original_pixmap.scaledToHeight(height, self.transformationMode())
            self._pixmapLoaded.emit(scaled_pixmap)
            self.resetTransform()
            self._lower_height_limit = int(height * (1.0 - self._height_scaling_threshold))
            self._upper_height_limit = int(height * (1.0 + self._height_scaling_threshold))
            self._lq_resize_count = 0
        elif self._true_height != height:
            # Use transformations for minor scaling adjustments
            scale_factor = height / self._true_height
            new_transform = self.transform().scale(scale_factor, scale_factor)
            self.setTransform(new_transform)
            self._lq_resize_count += 1

        # Update width and height based on the transformation
        self._height = self._true_height = height
        self._true_width = self._get_true_width()
        self._width = int(self._true_width)
        return None

    def scaled(self, width: int, height: int, keep_aspect_ratio: bool = False) -> None:
        """TBA"""
        if self._is_hidden or not self._is_loaded:
            self._true_width = self._width = width
            self._true_height = self._height = height
            return None
        # Check if either dimension requires high-quality scaling
        needs_width_scaling: bool = width < self._lower_width_limit or width > self._upper_width_limit
        needs_height_scaling: bool = height < self._lower_height_limit or height > self._upper_height_limit

        if needs_width_scaling or needs_height_scaling or self._lq_resize_count > self.lq_resize_count_threshold:
            # If either dimension is significantly reduced, use high-quality scaling
            aspect_mode = Qt.AspectRatioMode.KeepAspectRatio if keep_aspect_ratio else (
                Qt.AspectRatioMode.IgnoreAspectRatio)

            scaled_pixmap: QPixmap = self._original_pixmap.scaled(width, height, aspect_mode, self.transformationMode())
            self._pixmapLoaded.emit(scaled_pixmap)
            self.resetTransform()
            self._lower_width_limit = int(width * (1.0 - self._width_scaling_threshold))
            self._upper_width_limit = int(width * (1.0 + self._width_scaling_threshold))
            self._lower_height_limit = int(height * (1.0 - self._height_scaling_threshold))
            self._upper_height_limit = int(height * (1.0 + self._height_scaling_threshold))
            self._lq_resize_count = 0
        elif self._true_width != width or self._true_height != height:
            # Calculate scale factors for both dimensions
            scale_factor_width: float = width / self._true_width
            scale_factor_height: float = height / self._true_height
            if keep_aspect_ratio:
                # Apply the smallest scaling factor to maintain aspect ratio
                scale_factor_width = scale_factor_height = min(scale_factor_width, scale_factor_height)
            new_transform: QTransform = self.transform().scale(scale_factor_width, scale_factor_height)
            self.setTransform(new_transform)
            self._lq_resize_count += 1

        # Get all values, as the keep aspect ratio might have changed them
        self._true_width = self._get_true_width()
        self._width = int(self._true_width)
        self._true_height = self._get_true_height()
        self._height = int(self._true_height)
        return None

    def setInt(self, output: _ty.Literal["width", "height"]) -> None:
        """TBA"""
        if output in ["width", "height"]:
            self._int_attr = output
        else:
            raise ValueError("Output must be 'width' or 'height'")
        return None

    def setPixmap(self, pixmap, /):
        self._pixmap_width, self._pixmap_height = pixmap.width(), pixmap.height()
        super().setPixmap(pixmap)

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self._pixmap_width or self._width, self._pixmap_height or self._height)

    def highlight(self, global_color: Qt.GlobalColor) -> None:
        self._highlight = global_color

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget, /) -> None:
        if self._is_loaded and not self._is_hidden:
            super().paint(painter, option, widget)
        else:
            rect = self.boundingRect()  # Get the current bounding rectangle
            painter.setPen(QPen(self._highlight, 4, Qt.PenStyle.SolidLine))  # Set the pen for the border
            painter.drawRect(rect)  # Draw the placeholder rectangle

            # Set the painter for drawing text
            painter.setPen(Qt.GlobalColor.black)
            painter.setFont(QFont("Arial", 14, QFont.Weight.Bold))  # Set font size and style
            text_option = QTextOption(Qt.AlignmentFlag.AlignCenter)  # Align text to center
            painter.drawText(rect, f"Image {self.idx} not loaded", text_option)  # Draw the text within the rectangle

    def __int__(self):
        return getattr(self, f"_{self._int_attr}")

    def __lt__(self, other):
        if not isinstance(other, QScalingGraphicPixmapItem):
            return NotImplemented
        return getattr(self, f"_{self._int_attr}") < getattr(other, f"_{self._int_attr}")

    def __le__(self, other):
        if not isinstance(other, QScalingGraphicPixmapItem):
            return NotImplemented
        return getattr(self, f"_{self._int_attr}") <= getattr(other, f"_{self._int_attr}")

    def __eq__(self, other):
        if not isinstance(other, QScalingGraphicPixmapItem):
            return NotImplemented
        return getattr(self, f"_{self._int_attr}") == getattr(other, f"_{self._int_attr}")

    def __ne__(self, other):
        if not isinstance(other, QScalingGraphicPixmapItem):
            return NotImplemented
        return getattr(self, f"_{self._int_attr}") != getattr(other, f"_{self._int_attr}")

    def __gt__(self, other):
        if not isinstance(other, QScalingGraphicPixmapItem):
            return NotImplemented
        return getattr(self, f"_{self._int_attr}") > getattr(other, f"_{self._int_attr}")

    def __ge__(self, other):
        if not isinstance(other, QScalingGraphicPixmapItem):
            return NotImplemented
        return getattr(self, f"_{self._int_attr}") >= getattr(other, f"_{self._int_attr}")


class QAdvancedSmoothScrollingGraphicsView(QGraphicsView):
    """TBA"""
    onScroll = Signal()

    def __init__(self, sensitivity: int = 1, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.verticalScrollBar().valueChanged.connect(lambda _: self.onScroll.emit())
        self.horizontalScrollBar().valueChanged.connect(lambda _: self.onScroll.emit())

        # Scroll animations for both scrollbars
        self._v_scroll_animation = QPropertyAnimation(self.verticalScrollBar(), QByteArray(b"value"))
        self._h_scroll_animation = QPropertyAnimation(self.horizontalScrollBar(), QByteArray(b"value"))
        self._v_scroll_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._h_scroll_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._v_scroll_animation.setDuration(500)
        self._h_scroll_animation.setDuration(500)

        self.sensitivity: int = sensitivity

        # Scroll accumulators
        self._v_toScroll: int = 0
        self._h_toScroll: int = 0

        self._vert_scroll_rel_pos: float = 0.0
        self._hor_scroll_rel_pos: float = 0.0

        self._primary_scrollbar: Qt.Orientation = Qt.Orientation.Vertical

    def setPrimaryScrollbar(self, new_primary_scrollbar: Qt.Orientation) -> None:
        """TBA"""
        self._primary_scrollbar = new_primary_scrollbar

    def setScrollbarState(self, scrollbar: Qt.Orientation, on: bool = False) -> None:
        """TBA"""
        state: Qt.ScrollBarPolicy
        if on:
            state = Qt.ScrollBarPolicy.ScrollBarAsNeeded
        else:
            state = Qt.ScrollBarPolicy.ScrollBarAlwaysOff

        if scrollbar == Qt.Orientation.Vertical:
            self.setVerticalScrollBarPolicy(state)
        else:
            self.setHorizontalScrollBarPolicy(state)

    def wheelEvent(self, event: QWheelEvent) -> None:
        horizontal_event_dict: dict[str, QScrollBar | QPropertyAnimation | int] = {
            "scroll_bar": self.horizontalScrollBar(),
            "animation": self._h_scroll_animation,
            "toScroll": self._h_toScroll
        }
        vertical_event_dict: dict[str, QScrollBar | QPropertyAnimation | int] = {
            "scroll_bar": self.verticalScrollBar(),
            "animation": self._v_scroll_animation,
            "toScroll": self._v_toScroll
        }

        # Choose scroll bar based on right mouse button state
        # Qt.Orientation.Horizontal: 1 -> 0000 0001
        # Qt.Orientation.Vertical: 2 -> 0000 0010
        # Qt.MouseButton.RightButton: 2 -> 0000 0010
        # event.buttons() & Qt.MouseButton.RightButton = Qt.MouseButton.RightButton if it is inside .buttons()
        event_dict: dict[str, QScrollBar | QPropertyAnimation | int] = [
            {},  # Cannot be selected
            horizontal_event_dict, vertical_event_dict,  # Right mouse button is not pressed
            vertical_event_dict, horizontal_event_dict][  # Right mouse button is pressed
            (event.buttons() & Qt.MouseButton.RightButton).value + self._primary_scrollbar.value]
        scrollbar: QScrollBar = event_dict["scroll_bar"]  # type: ignore
        animation: QPropertyAnimation = event_dict["animation"]  # type: ignore
        # to_scroll: int = event_dict["to_scroll"]  # Cannot be used as this would copy ot

        angle_delta = event.angleDelta().y()
        steps = angle_delta / 120
        pixel_step = int(scrollbar.singleStep() * self.sensitivity)

        if animation.state() == QPropertyAnimation.State.Running:
            animation.stop()
            event_dict["toScroll"] += animation.endValue() - scrollbar.value()

        current_value: int = scrollbar.value()
        max_value: int = scrollbar.maximum()
        min_value: int = scrollbar.minimum()

        # Inverted scroll direction calculation
        event_dict["toScroll"] -= pixel_step * steps  # type: ignore
        proposed_value: int = current_value + event_dict["toScroll"]  # type: ignore # Reflecting changes

        if (proposed_value > max_value and steps > 0) or (proposed_value < min_value and steps < 0):
            event_dict["toScroll"] = 0

        new_value: int = current_value + event_dict["toScroll"]  # type: ignore
        animation.setStartValue(current_value)
        animation.setEndValue(new_value)
        animation.start()

        animation.finished.connect(self.onScroll.emit)
        self.onScroll.emit()

        event.accept()  # Prevent further processing of the event

    def resetCachedContent(self, /):
        for item in self.scene().items():
            if item.cacheMode() == QGraphicsItem.CacheMode.DeviceCoordinateCache:
                item.setCacheMode(QGraphicsItem.CacheMode.NoCache)
                item.update()
                item.setCacheMode(QGraphicsItem.CacheMode.DeviceCoordinateCache)
        super().resetCachedContent()

    def saveRelativeScrollPosition(self) -> None:
        """TBA"""
        if self._vert_scroll_rel_pos != 0 or self._hor_scroll_rel_pos != 0:
            return None
        if self.verticalScrollBar().maximum() != 0:
            self._vert_scroll_rel_pos = self.verticalScrollBar().value() / self.verticalScrollBar().maximum()
        if self.horizontalScrollBar().maximum() != 0:
            self._hor_scroll_rel_pos = self.horizontalScrollBar().value() / self.horizontalScrollBar().maximum()
        return None

    def restoreRelativeScrollPosition(self) -> None:
        """TBA"""
        if self._vert_scroll_rel_pos == 0 and self._hor_scroll_rel_pos == 0:
            return
        self.verticalScrollBar().setValue(int(self.verticalScrollBar().maximum() * self._vert_scroll_rel_pos))
        self.horizontalScrollBar().setValue(int(self.horizontalScrollBar().maximum() * self._hor_scroll_rel_pos))
        self._vert_scroll_rel_pos = 0
        self._hor_scroll_rel_pos = 0


class QGraphicsScrollView(QWidget):
    """TBA"""
    ScrollBarAsNeeded = Qt.ScrollBarPolicy.ScrollBarAsNeeded
    ScrollBarAlwaysOff = Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    ScrollBarAlwaysOn = Qt.ScrollBarPolicy.ScrollBarAlwaysOn

    def __init__(self, sensitivity: int = 1, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        # Create a layout for the widget
        layout = QNoSpacingBoxLayout(QBoxDirection.TopToBottom, apply_layout_to=self)

        # Create a QGraphicsView
        self.graphics_view = QAdvancedSmoothScrollingGraphicsView(sensitivity=sensitivity)
        self.graphics_view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.graphics_view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.graphics_view.setStyleSheet("QGraphicsView { border: 0px; }")

        # Set size policy to Ignored to allow resizing freely
        self.graphics_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._v_scrollbar = QScrollBar()
        self._v_scrollbar.setOrientation(Qt.Orientation.Vertical)
        self._v_scrollbar.setVisible(False)

        # Create a layout for the QGraphicsView with additional spacing
        graphics_layout = QNoSpacingBoxLayout(QBoxDirection.LeftToRight)

        graphics_layout.addWidget(self.graphics_view)
        graphics_layout.addWidget(self._v_scrollbar)
        layout.addLayout(graphics_layout)

        self._h_scrollbar = QScrollBar()
        self._h_scrollbar.setOrientation(Qt.Orientation.Horizontal)
        self._h_scrollbar.setVisible(False)

        self._corner_widget = QWidget()
        self._corner_widget.setAutoFillBackground(True)
        self._corner_widget.setFixedSize(self._v_scrollbar.width(), self._h_scrollbar.height())

        hor_scroll_layout = QNoSpacingBoxLayout(QBoxDirection.LeftToRight)
        hor_scroll_layout.addWidget(self._h_scrollbar)
        hor_scroll_layout.addWidget(self._corner_widget)

        # Add scrollbar to the layout
        layout.addLayout(hor_scroll_layout)

        # Connect scrollbar value changed signal to update content position
        self._v_scrollbar.valueChanged.connect(self.graphics_view.verticalScrollBar().setValue)
        self._h_scrollbar.valueChanged.connect(self.graphics_view.horizontalScrollBar().setValue)
        self.graphics_view.verticalScrollBar().valueChanged.connect(self._v_scrollbar.setValue)
        self.graphics_view.horizontalScrollBar().valueChanged.connect(self._h_scrollbar.setValue)

        self._scrollbars_background_redraw = False
        self._vert_scroll_pol: Qt.ScrollBarPolicy = Qt.ScrollBarPolicy.ScrollBarAsNeeded
        self._hor_scroll_pol: Qt.ScrollBarPolicy = Qt.ScrollBarPolicy.ScrollBarAsNeeded
        self.updateScrollBars()

    def verticalScrollBar(self) -> QScrollBar:
        """TBA"""
        return self._v_scrollbar

    def horizontalScrollBar(self) -> QScrollBar:
        """TBA"""
        return self._h_scrollbar

    def setVerticalScrollBarPolicy(self, policy: Qt.ScrollBarPolicy) -> None:
        """TBA"""
        self._vert_scroll_pol = policy
        self.updateScrollBars()
        return None

    def setHorizontalScrollBarPolicy(self, policy: Qt.ScrollBarPolicy) -> None:
        """TBa"""
        self._hor_scroll_pol = policy
        self.updateScrollBars()
        return None

    def verticalScrollBarPolicy(self) -> Qt.ScrollBarPolicy:
        """TBA"""
        return self._vert_scroll_pol

    def horizontalScrollBarPolicy(self) -> Qt.ScrollBarPolicy:
        """TBA"""
        return self._hor_scroll_pol

    def updateScrollBars(self, update_viewport_size: bool = True) -> None:
        """TBA"""
        # Sync with internal scrollbars
        viewport_size = self.graphics_view.size()
        self.verticalScrollBar().setRange(self.graphics_view.verticalScrollBar().minimum(),
                                          self.graphics_view.verticalScrollBar().maximum())
        self.horizontalScrollBar().setRange(self.graphics_view.horizontalScrollBar().minimum(),
                                            self.graphics_view.horizontalScrollBar().maximum())

        if self.graphics_view.scene() is None:
            self.verticalScrollBar().setVisible(False)
            self.horizontalScrollBar().setVisible(False)
            return

        if self._vert_scroll_pol == Qt.ScrollBarPolicy.ScrollBarAlwaysOn:
            self.verticalScrollBar().setVisible(True)
        elif self._vert_scroll_pol == Qt.ScrollBarPolicy.ScrollBarAlwaysOff:
            self.verticalScrollBar().setVisible(False)
        elif self._vert_scroll_pol == Qt.ScrollBarPolicy.ScrollBarAsNeeded:
            # Show or hide based on the content size
            self.verticalScrollBar().setVisible(self.verticalScrollBar().maximum() > 0)
        else:
            raise RuntimeError()

        if self._hor_scroll_pol == Qt.ScrollBarPolicy.ScrollBarAlwaysOn:
            self.horizontalScrollBar().setVisible(True)
        elif self._hor_scroll_pol == Qt.ScrollBarPolicy.ScrollBarAlwaysOff:
            self.horizontalScrollBar().setVisible(False)
        elif self._hor_scroll_pol == Qt.ScrollBarPolicy.ScrollBarAsNeeded:
            # Show or hide based on the content size
            self.horizontalScrollBar().setVisible(self.horizontalScrollBar().maximum() > 0)
        else:
            raise RuntimeError()

        if self._h_scrollbar.isVisible() and self._v_scrollbar.isVisible():
            self._corner_widget.show()
        else:
            self._corner_widget.hide()
        self._corner_widget.setFixedSize(self._v_scrollbar.width(), self._h_scrollbar.height())
        if update_viewport_size:
            self.graphics_view.resize(viewport_size)
        return None

    def scrollBarsBackgroundRedraw(self, value: bool) -> None:
        """TBA"""
        self._scrollbars_background_redraw = value
        self._corner_widget.setAutoFillBackground(not value)
        return None

    def resizeEvent(self, event: QResizeEvent) -> None:
        """TBA"""
        event_size: QSize = event.size()
        if not self._scrollbars_background_redraw:
            event_size.setWidth(event_size.width() - self._v_scrollbar.width())
            event_size.setHeight(event_size.height() - self._h_scrollbar.height())

        # Update scrollbar range and page step
        self.graphics_view.resize(event_size)
        self.updateScrollBars()

        super().resizeEvent(event)
        return None


class BaseManagement(metaclass=ABCMeta):
    """
    Abstract base class for managing image scaling, scene adjustments, and event handling
    within a TargetContainer. Subclasses must implement all methods.
    """

    @abstractmethod
    def __init__(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def initialize(self, target: "TargetContainer") -> None:
        """
        Initialize the management system for the given TargetContainer.

        Args:
            target (TargetContainer): The container that holds the graphics scene and images.

        Raises:
            NotImplementedError: Must be implemented by subclasses.
        """
        raise NotImplementedError

    @abstractmethod
    def addImageToScene(self, image: QScalingGraphicPixmapItem, target: "TargetContainer") -> None:
        """
        Add an image to the graphics scene in the target container.

        Args:
            image (QScalingGraphicPixmapItem): The image to be added.
            target (TargetContainer): The container managing the scene.

        Raises:
            NotImplementedError: Must be implemented by subclasses.
        """
        raise NotImplementedError

    @abstractmethod
    def rescaleImages(self, width: int, height: int, scene_items: list[QScalingGraphicPixmapItem], target: "TargetContainer") -> None:
        """
        Rescale all images in the scene to fit within the given width and height.

        Args:
            width (int): The target width for scaling.
            height (int): The target height for scaling.
            scene_items (list[QScalingGraphicPixmapItem]): The images to be rescaled.
            target (TargetContainer): The container managing the scene.

        Raises:
            NotImplementedError: Must be implemented by subclasses.
        """
        raise NotImplementedError

    @abstractmethod
    def adjustSceneBounds(self, items: list[QScalingGraphicPixmapItem], target: "TargetContainer") -> None:
        """
        Adjust the scene boundaries based on the positions and sizes of the images.

        Args:
            items (list[QScalingGraphicPixmapItem]): The images in the scene.
            target (TargetContainer): The container managing the scene.

        Raises:
            NotImplementedError: Must be implemented by subclasses.
        """
        raise NotImplementedError

    @abstractmethod
    def onScroll(self, images: list[QScalingGraphicPixmapItem], target: "TargetContainer") -> None:
        """
        Handle scrolling events and dynamically adjust image visibility or loading.

        Args:
            images (list[QScalingGraphicPixmapItem]): The images currently in the scene.
            target (TargetContainer): The container managing the scene.

        Raises:
            NotImplementedError: Must be implemented by subclasses.
        """
        raise NotImplementedError

    @abstractmethod
    def resizeEvent(self, target: "TargetContainer") -> None:
        """
        Handle resize events for the TargetContainer, ensuring the layout and image
        scaling adjust accordingly.

        Args:
            target (TargetContainer): The container that has been resized.

        Raises:
            NotImplementedError: Must be implemented by subclasses.
        """
        raise NotImplementedError


class TargetContainer(QGraphicsScrollView):  # https://stackoverflow.com/questions/43826317/how-to-optimize-qgraphicsviews-performance
    """ A container that holds the graphics view. """

    def __init__(self, sensitivity: int = 1, antialiasing_enabled: bool = True, timer_timeout_ms: int = 100, max_threadpool_workers: int = 10,
                 pixmap_transform_mode: _ty.Literal["smooth", "fast"] = "smooth", viewport_mode: _ty.Literal["default", "opengl"] = "default", parent: QWidget | None = None):
        super().__init__(sensitivity, parent=parent)
        self.scene: QGraphicsScene = QGraphicsScene(self)
        self.graphics_view.setScene(self.scene)

        self.graphics_view.setRenderHint(QPainter.RenderHint.Antialiasing, antialiasing_enabled)
        self.pixmap_transform_mode: _ty.Literal["smooth", "fast"] = pixmap_transform_mode
        self.graphics_view.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, pixmap_transform_mode == "smooth")
        self.graphics_view.setOptimizationFlags(
            QGraphicsView.OptimizationFlag.DontSavePainterState | QGraphicsView.OptimizationFlag.DontAdjustForAntialiasing)
        self.graphics_view.setCacheMode(QGraphicsView.CacheModeFlag.CacheBackground)

        if viewport_mode == "opengl":
            self.graphics_view.setViewport(QOpenGLWidget())
            self.graphics_view.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        else:
            self.graphics_view.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.BoundingRectViewportUpdate)

        # self.graphics_view.setInteractive(False)
        self.graphics_view.onScroll.connect(self._onScroll)

        self.resizing: bool = False
        self.force_rescaling: bool = False

        self.timer: QTimer = QTimer(self)
        if timer_timeout_ms > 0:
            self.timer.start(timer_timeout_ms)
        self.timer.timeout.connect(self.timer_tick)

        self.management: BaseManagement | None = None
        self.images: list[QScalingGraphicPixmapItem] = []
        self.thread_pool = LazyDynamicThreadPoolExecutor(max_workers=max(1, max_threadpool_workers))

        self.width_scaling_threshold: float = 0.1
        self.height_scaling_threshold: float = 0.1
        self.lq_resize_count_threshold: int = 1000
        self.update_tick_lq_addition: int = 100

    def setManagement(self, management: BaseManagement) -> None:
        self.management = management
        self.management.initialize(self)
        return None

    def addImagePath(self, image_path: str):
        if self.management is None:
            raise RuntimeError("Management is None so no image can be added")
        image = QScalingGraphicPixmapItem(image_path, self.width_scaling_threshold, self.height_scaling_threshold, self.lq_resize_count_threshold, self.update_tick_lq_addition, use_high_quality_transform=self.pixmap_transform_mode == "smooth", load_now=True)
        self._addImageToScene(image)

    # Management methods
    def _addImageToScene(self, image: QScalingGraphicPixmapItem) -> None:
        """TBA"""
        self.scene.addItem(image)
        self.updateScrollBars()
        image.idx = len(self.images)
        image.setCacheMode(QGraphicsPixmapItem.CacheMode.DeviceCoordinateCache)
        self.images.append(image)
        # image.ensure_unloaded()  # Unneeded
        self.management.addImageToScene(image, self)

    def _rescaleImages(self, event_size: QSize | None = None) -> None:
        event_size = event_size or self.graphics_view.viewport().size()
        self.management.rescaleImages(event_size.width(), event_size.height(), self.images.copy(), self)

    def _adjustSceneBounds(self) -> None:
        items: list[QScalingGraphicPixmapItem] = self.scene.items()  # TODO: fix
        self.management.adjustSceneBounds(items, self)

    def _onScroll(self) -> None:
        self.management.onScroll(self.images, self)

    def resizeEvent(self, event: QResizeEvent) -> None:
        if self.management is None:
            raise RuntimeError("Management is None so TargetContainer cannot be resized")
        self.resizing = self.force_rescaling = True
        self.graphics_view.saveRelativeScrollPosition()
        self._rescaleImages(self.size())
        self._adjustSceneBounds()
        self._onScroll()
        self.management.resizeEvent(self)
        super().resizeEvent(event)
        self.resizing = False
        self.graphics_view.resetCachedContent()
        self.graphics_view.restoreRelativeScrollPosition()

    # Rest
    def timer_tick(self) -> None:
        """TBA"""
        for image in self.images:
            image.update_tick()

    def __del__(self):
        self.thread_pool.shutdown()


class VerticalManagement(BaseManagement):
    def __init__(self, buttons_widget_proxy: QGraphicsProxyWidget, downscaling: bool = True, upscaling: bool = False,
                 base_width: int = 640, lazy_loading: bool = True) -> None:
        self.buttons_widget_proxy = buttons_widget_proxy
        self.downscaling: bool = downscaling
        self.upscaling: bool = upscaling
        self.base_width: int = base_width
        self.lazy_loading: bool = lazy_loading

    @staticmethod
    def initialize(target):
        target.graphics_view.setPrimaryScrollbar(Qt.Orientation.Vertical)

    @staticmethod
    def addImageToScene(image, target):
        # image.first_load()  # target.thread_pool.submit(image.first_load)
        image.setInt("width")

    def _get_wanted_size(self, target, item: QScalingGraphicPixmapItem, viewport_width: int, last_item: bool = False):
        base_image_width = self.base_width

        if target.force_rescaling:
            proposed_image_width = base_image_width

            if self.downscaling and base_image_width > viewport_width:
                proposed_image_width = viewport_width
            elif self.upscaling and base_image_width < viewport_width:
                proposed_image_width = viewport_width
            if last_item:
                target.force_rescaling = False
            return proposed_image_width
        return item.get_width()

    def rescaleImages(self, width, height, images, target):
        total_height = 0
        # images.reverse()
        target.force_rescaling = True
        # height += target.horizontalScrollBar().height()

        for i, item in enumerate(images):
            if isinstance(item, QScalingGraphicPixmapItem):
                wanted_width = self._get_wanted_size(target, item, width, True if i == len(images) - 1 else False)

                if abs(item.get_true_width() - wanted_width) >= 0.5:
                    # print(item.true_width, "->", wanted_width)
                    item.scaledToWidth(wanted_width)
                    item.setPos(0, total_height)

                total_height += item.get_true_height()
        self.buttons_widget_proxy.resize(target.graphics_view.scene().width(), self.buttons_widget_proxy.widget().height())
        self.buttons_widget_proxy.setPos(0, total_height)
            # target.scene.update()
            # target.graphics_view.update()

    def adjustSceneBounds(self, items, target):
        if not items:
            return
        items = list(filter(lambda x: isinstance(x, QScalingGraphicPixmapItem), items))
        if items:
            width = max(items).get_width()
            height = sum(item.get_height() for item in items if isinstance(item, QGraphicsPixmapItem)) + self.buttons_widget_proxy.widget().height()
        else:
            width = self.buttons_widget_proxy.widget().width()
            height = self.buttons_widget_proxy.widget().height()
        target.scene.setSceneRect(0, 0, width, height)
        self.buttons_widget_proxy.resize(target.graphics_view.scene().width(),
                                         self.buttons_widget_proxy.widget().height())

    @staticmethod
    def _isVisibleInViewport(target, item: QScalingGraphicPixmapItem):
        """Checks if an image is visible in the current viewport."""
        item_rect = item.mapToScene(item.boundingRect()).boundingRect()
        viewport_rect = target.graphics_view.mapToScene(target.graphics_view.viewport().rect()).boundingRect()
        return viewport_rect.intersects(item_rect)

    def _findVisibleImageRange(self, target: TargetContainer, images: list[QScalingGraphicPixmapItem]):
        """
        Finds the first and last visible image indices efficiently using binary search.
        Returns: (first_visible_idx, last_visible_idx)
        """
        imgs_len = len(images)
        low, high = 0, imgs_len - 1
        found_idx = -1

        # **1. Get the Y-coordinate of the viewport center**
        rect = target.graphics_view.mapToScene(target.graphics_view.viewport().rect()).boundingRect()
        viewport_center_y = rect.y() + (rect.height() // 2)

        # **2. Perform binary search to find a visible image**
        while low <= high:
            mid = (low + high) // 2
            real_idx = self._get_img_idx(mid, imgs_len - 1)  # Adjust for reverse order
            image = images[real_idx]

            if self._isVisibleInViewport(target, image):
                found_idx = mid
                break  # Stop once a visible image is found
            elif image.y() < viewport_center_y:
                low = mid + 1  # Search upwards
            else:
                high = mid - 1  # Search downwards

        # **3. If no visible image is found, fallback to a linear search**
        if found_idx == -1:
            for i, image in enumerate(images):
                if self._isVisibleInViewport(target, image):
                    found_idx = i
                    break

        # **4. Expand left to find the first visible image**
        first_visible_idx = found_idx
        while first_visible_idx > 0:
            real_idx = self._get_img_idx(first_visible_idx - 1, imgs_len - 1)
            if self._isVisibleInViewport(target, images[real_idx]):
                first_visible_idx -= 1
            else:
                break

        # **5. Expand right to find the last visible image**
        last_visible_idx = found_idx
        while last_visible_idx < imgs_len - 1:
            real_idx = self._get_img_idx(last_visible_idx + 1, imgs_len - 1)
            if self._isVisibleInViewport(target, images[real_idx]):
                last_visible_idx += 1
            else:
                break

        return first_visible_idx, last_visible_idx

    def _get_img_idx(self, idx: int, from_max: int) -> int:
        """Handles reversed order in RightToLeft or BottomToTop scrolling."""
        return idx

    def _loadImagesInViewport(self, target, images: list[QScalingGraphicPixmapItem]):
        """
        Loads images in the viewport using binary search and unloads others.
        """
        imgs_len = len(images)
        if imgs_len == 0:
            return  # No images to process

        # **Find first and last visible images**
        first_visible_idx, last_visible_idx = self._findVisibleImageRange(target, images)

        # **Add a buffer to preload images slightly ahead for smooth scrolling**
        buffer_count = 1
        range_start = max(0, first_visible_idx - 0)
        range_end = min(imgs_len - 1, last_visible_idx + buffer_count)

        # **Load only images in the visible range, unload others**
        for i, image in enumerate(images):
            if range_start <= i <= range_end:
                target.thread_pool.submit(image.ensure_visible)
            else:
                target.thread_pool.submit(image.ensure_hidden)

    def onScroll(self, images, target):
        """
        Handles scrolling and dynamically loads images in viewport.
        """
        if self.lazy_loading:
            self._loadImagesInViewport(target, images)
        else:
            # Load everything if lazy loading is disabled
            for image in images:
                image.ensure_visible()

    @staticmethod
    def resizeEvent(target):
        pass


class Settings:
    def __init__(self, db_path, overwrite_settings: _ty.Optional[dict] = None, export_settings_func=lambda: None):
        is_setup = os.path.isfile(db_path)
        self.db = DBManager(db_path)
        self.is_open = True
        self.default_settings = {
            "provider_id": "manhwa_clan",
            "title": "Thanks for using ManhwaViewer!",
            "chapter": "1",
            "libraries": '[]',  # json
            "current_lib_idx": "-1",
            "library_manager_id": "std_lib",
            "downscaling": "True",
            "upscaling": "False",
            "manual_content_width": "1200",
            "borderless": "True",
            "hide_titlebar": "False",
            "hover_effect_all": "True",
            "acrylic_menus": "True",
            "acrylic_background": "False",
            "hide_scrollbar": "False",
            "stay_on_top": "False",
            "geometry": "100, 100, 640, 480",
            "advanced_settings": '{"recent_titles": [], "themes": {"light": "light_light", "dark": "light_dark", "font": "Segoe UI"}, "settings_file_path": "", "settings_file_mode": "overwrite", "misc": {"auto_export": false, "quality_preset": "quality", "max_cached_chapters": -1}}',
            "chapter_rate": "1.0",
            "no_update_info": "True",
            "not_recommened_update_info": "True",
            "update_info": "True",
            "last_scroll_positions": "0, 0",
            "scrolling_sensitivity": "4.0",
            "lazy_loading": "True",
            "save_last_titles": "True",
            "show_provider_logo": "True",
            "show_tutorial": "True"
        }
        self.settings = self.default_settings.copy()
        if overwrite_settings:
            self.settings.update(overwrite_settings)
        if not is_setup:
            self.setup_database(self.settings)
        self.fetch_data()
        self.export_settings_func = export_settings_func

    def connect(self):
        self.db.connect()
        self.is_open = True
        self.fetch_data()

    def get_default_setting(self, setting: str):
        return self.default_settings.get(setting)

    def boolean(self, to_boolean: str) -> bool:
        return to_boolean.lower() == "true"

    def str_to_list(self, s: str) -> list[str]:
        return s.split(", ")

    def list_to_str(self, lst: list[str]) -> str:
        return ', '.join(lst)

    def ensure_keys(self, base: dict, modified: dict) -> dict:
        """
        Ensures all keys and nested keys in `base` exist in `modified`.
        If a key is missing in `modified`, it's added from `base`.
        """
        result = modified.copy()  # Make a shallow copy to avoid modifying the original

        for key, base_value in base.items():
            if key not in result:
                result[key] = base_value
            else:
                # If both are dicts, recurse
                if isinstance(base_value, dict) and isinstance(result[key], dict):
                    result[key] = self.ensure_keys(base_value, result[key])
        return result

    def get(self, key: str):
        value = self.settings.get(key)
        if key in ["blacklisted_websites"]:
            return self.str_to_list(value)
        elif key in ["chapter"]:
            return int(value) if float(value).is_integer() else float(value)
        elif key in ["chapter_rate", "scrolling_sensitivity"]:
            return float(value)
        elif key in ["downscaling", "upscaling", "borderless", "hide_titlebar", "hover_effect_all",
                     "acrylic_menus", "acrylic_background", "hide_scrollbar", "stay_on_top", "no_update_info",
                     "update_info", "lazy_loading", "save_last_titles", "show_provider_logo", "show_tutorial"]:
            return self.boolean(value)
        elif key in ["manual_content_width", "current_lib_idx", "max_cached_chapters"]:
            return int(value)
        elif key in ["geometry", "last_scroll_positions"]:
            return [int(x) for x in value.split(", ")]
        elif key in ["advanced_settings", "libraries"]:
            mod_val = json.loads(value)
            if not isinstance(mod_val, dict):
                return mod_val
            return self.ensure_keys(json.loads(self.default_settings.get(key)), mod_val)
        return value

    def set(self, key: str, value):
        if key in ["blacklisted_websites"]:
            value = self.list_to_str(value)
        elif key in ["chapter"]:
            value = str(int(value) if float(value).is_integer() else value)
        elif key in ["chapter_rate", "scrolling_sensitivity"]:
            value = str(float(value))
        elif key in ["downscaling", "upscaling", "borderless", "hide_titlebar", "hover_effect_all",
                     "acrylic_menus", "acrylic_background", "hide_scrollbar", "stay_on_top", "no_update_info",
                     "update_info", "lazy_loading", "save_last_titles", "show_provider_logo", "show_tutorial"]:
            value = str(value)
        elif key in ["manual_content_width", "current_lib_idx", "max_cached_chapters"]:
            value = str(int(value))
        elif key in ["geometry", "last_scroll_positions"]:
            value = ', '.join([str(x) for x in value])
        elif key in ["advanced_settings", "libraries"]:
            if isinstance(value, dict):
                base = json.loads(self.default_settings.get(key))
                value = json.dumps(self.ensure_keys(base, value))
            else:
                value = json.dumps(value)
        self.settings[key] = value
        self.update_data()
        # if self.get_advanced_settings()["misc"]["auto_export"]:
        #     self.export_settings_func()

    def get_provider_id(self):
        return self.get("provider_id")

    def set_provider_id(self, value):
        self.set("provider_id", value)

    def get_title(self):
        return self.get("title")

    def set_title(self, value):
        self.set("title", value)

    def get_chapter(self):
        return self.get("chapter")

    def set_chapter(self, value):
        self.set("chapter", value)

    def get_libraries(self):
        return self.get("libraries")

    def set_libraries(self, value):
        self.set("libraries", value)

    def get_current_lib_idx(self):
        return self.get("current_lib_idx")

    def set_current_lib_idx(self, value):
        self.set("current_lib_idx", value)

    def get_library_manager_id(self):
        return self.get("library_manager_id")

    def set_library_manager_id(self, value):
        self.set("library_manager_id", value)

    def get_downscaling(self):
        return self.get("downscaling")

    def set_downscaling(self, value):
        self.set("downscaling", value)

    def get_upscaling(self):
        return self.get("upscaling")

    def set_upscaling(self, value):
        self.set("upscaling", value)

    def get_manual_content_width(self):
        return self.get("manual_content_width")

    def set_manual_content_width(self, value):
        self.set("manual_content_width", value)

    def get_borderless(self):
        return self.get("borderless")

    def set_borderless(self, value):
        self.set("borderless", value)

    def get_hide_titlebar(self):
        return self.get("hide_titlebar")

    def set_hide_titlebar(self, value):
        self.set("hide_titlebar", value)

    def get_hover_effect_all(self):
        return self.get("hover_effect_all")

    def set_hover_effect_all(self, value):
        self.set("hover_effect_all", value)

    def get_acrylic_menus(self):
        return self.get("acrylic_menus")

    def set_acrylic_menus(self, value):
        self.set("acrylic_menus", value)

    def get_acrylic_background(self):
        return self.get("acrylic_background")

    def set_acrylic_background(self, value):
        self.set("acrylic_background", value)

    def get_hide_scrollbar(self):
        return self.get("hide_scrollbar")

    def set_hide_scrollbar(self, value):
        self.set("hide_scrollbar", value)

    def get_stay_on_top(self):
        return self.get("stay_on_top")

    def set_stay_on_top(self, value):
        self.set("stay_on_top", value)

    def get_geometry(self):
        return self.get("geometry")

    def set_geometry(self, value):
        self.set("geometry", value)

    def get_advanced_settings(self):
        return self.get("advanced_settings")

    def set_advanced_settings(self, value):
        self.set("advanced_settings", value)

    def get_chapter_rate(self):
        return self.get("chapter_rate")

    def set_chapter_rate(self, value):
        self.set("chapter_rate", value)

    def get_no_update_info(self):
        return self.get("no_update_info")

    def set_no_update_info(self, value):
        self.set("no_update_info", value)

    def get_not_recommened_update_info(self):
        return self.get("not_recommened_update_info")

    def set_not_recommened_update_info(self, value):
        self.set("not_recommened_update_info", value)

    def get_update_info(self):
        return self.get("update_info")

    def set_update_info(self, value):
        self.set("update_info", value)

    def get_last_scroll_positions(self):
        return self.get("last_scroll_positions")

    def set_last_scroll_positions(self, value):
        self.set("last_scroll_positions", value)

    def get_scrolling_sensitivity(self):
        return self.get("scrolling_sensitivity")

    def set_scrolling_sensitivity(self, value):
        self.set("scrolling_sensitivity", value)

    def get_lazy_loading(self):
        return self.get("lazy_loading")

    def set_lazy_loading(self, value):
        self.set("lazy_loading", value)

    def get_save_last_titles(self):
        return self.get("save_last_titles")

    def set_save_last_titles(self, value):
        self.set("save_last_titles", value)

    def get_show_provider_logo(self):
        return self.get("show_provider_logo")

    def set_show_provider_logo(self, value):
        self.set("show_provider_logo", value)

    def get_show_tutorial(self):
        return self.get("show_tutorial")

    def set_show_tutorial(self, value):
        self.set("show_tutorial", value)

    def setup_database(self, settings):
        # Define tables and their columns
        tables = {
            "settings": ["key TEXT", "value TEXT"]
        }
        # Code to set up the database, initialize password hashes, etc.
        for table_name, columns in tables.items():
            self.db.create_table(table_name, columns)
        for i in self.settings.items():
            self.db.update_info(i, "settings", ["key", "value"])

    def fetch_data(self):
        fetched_data = self.db.get_info("settings", ["key", "value"])
        for item in fetched_data:
            key, value = item
            self.settings[key] = value

    def update_data(self):
        for key, value in self.settings.items():
            self.db.update_info((key, value), "settings", ["key", "value"])

    def close(self):
        self.is_open = False
        self.db.close()


class AutoProviderManager:
    def __init__(self, path: str, absolute_base: _ty.Type) -> None:
        self.path: str = path
        self.absolute_base: _ty.Type = absolute_base
        self.providers: list[_ty.Type] = []

    def _load_providers(self) -> None:
        for file in os.listdir(self.path):
            if file.endswith('.py') or file.endswith('.pyd') and file != '__init__.py':
                module_name: str = file.split(".")[0]
                module_path: str = os.path.join(self.path, file)
                spec: ModuleSpec | None = importlib.util.spec_from_file_location(module_name, module_path)
                if spec is None:
                    continue
                module: _ts.ModuleType = importlib.util.module_from_spec(spec)
                if spec.loader is None:
                    continue
                spec.loader.exec_module(module)
                for attribute_name in dir(module):
                    attribute = getattr(module, attribute_name)
                    if not hasattr(attribute, "register_baseclass"):
                        continue
                    if isinstance(attribute, type) and issubclass(attribute, self.absolute_base) and attribute.register_baseclass != attribute_name:
                        self.providers.append(attribute)

    def get_providers(self) -> list[_ty.Type]:
        self.providers.clear()
        self._load_providers()
        return self.providers


class UnselectableDelegate(QStyledItemDelegate):
    def editorEvent(self, event, model, option, index):
        # Prevent selection of disabled items
        data = model.itemData(index)
        if Qt.UserRole in data and data[Qt.UserRole] == "disabled":
            return False
        return super().editorEvent(event, model, option, index)


class CustomComboBox(QComboBox):
    def __init__(self):
        super().__init__()
        self.setItemDelegate(UnselectableDelegate())
        self.currentIndexChanged.connect(self.handleIndexChanged)
        self.previousIndex = 0

    def handleIndexChanged(self, index):
        # If the newly selected item is disabled, revert to the previous item
        if index in range(self.count()):
            if self.itemData(index, Qt.UserRole) == "disabled":
                self.setCurrentIndex(self.previousIndex)
            else:
                self.previousIndex = index

    def setItemUnselectable(self, index):
        # Set data role to indicate item is disabled
        self.model().setData(self.model().index(index, 0), "disabled", Qt.UserRole)


if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    window = QAdvancedSmoothScrollingGraphicsView()
    window.setWindowTitle('Custom Scroll Area')
    window.setGeometry(100, 100, 300, 200)

    # Add some example content
    for i in range(20):
        label = QLabel(f"Item {i}" * 30)
        window.content_layout.addWidget(label)

    window.show()
    sys.exit(app.exec_())

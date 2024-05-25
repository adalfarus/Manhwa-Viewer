from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout, QDialog, QLineEdit, QPushButton, QDialogButtonBox,
                               QLabel, QScrollBar, QGroupBox, QFormLayout, QRadioButton, QCheckBox, QSpinBox,
                               QApplication, QProgressDialog, QWidget, QListWidget, QSizePolicy, QListWidgetItem,
                               QMessageBox, QStyledItemDelegate, QComboBox, QToolButton, QFileDialog, QLayout,
                               QFontComboBox)
from PySide6.QtCore import Qt, Signal, QThread, QTimer, Slot, QSize, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QPainter, QBrush, QColor, QPen, QPalette, QIcon, QPixmap, QFont, QWheelEvent
from aplustools.io import environment as env
from typing import Literal, Optional, List
import threading
import importlib
import sqlite3
import random
import ctypes
import shutil
import queue
import json
import time
import os
from aplustools.package.timid import TimidTimer


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
    def __init__(self, parent=None, current_settings: dict = None, default_settings: dict = None, master=None):
        super().__init__(parent, Qt.WindowCloseButtonHint | Qt.WindowTitleHint)

        if default_settings is None:
            self.default_settings = {"recent_titles": [],
                                     "themes": {"light": "light_light", "dark": "dark", "font": "Segoe UI"},
                                     "settings_file_path": "",
                                     "settings_file_mode": "overwrite",
                                     "misc": {"auto_export": False, "num_workers": 10}}
        else:
            self.default_settings = default_settings
        if current_settings is None:
            self.current_settings = self.default_settings
        else:
            self.current_settings = current_settings
        self.selected_settings = None
        self.master = master

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
        self.lightThemeComboBox.addItems(['Light Theme', '(Light) Light Theme', 'Dark Theme', '(Light) Dark Theme', 'Modern'])
        self.darkThemeComboBox.addItems(['Light Theme', '(Light) Light Theme', 'Dark Theme', '(Light) Dark Theme', 'Modern'])
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
        self.loadSettingsPushButton = QPushButton("Load Settings File")
        self.loadSettingsPushButton.clicked.connect(self.load_settings_file)
        last_layout = QNoSpacingHBoxLayout()
        last_layout.addWidget(self.createNewRadioButton)
        last_layout.addStretch()
        last_layout.addWidget(self.loadSettingsPushButton)
        self.fileHandlingLayout.addLayout(self.fileLocationLayout)
        self.fileHandlingLayout.addWidget(self.overwriteRadioButton)
        self.fileHandlingLayout.addWidget(self.modifyRadioButton)
        self.fileHandlingLayout.addLayout(last_layout)
        self.mainLayout.addWidget(self.fileHandlingGroupBox)

        # Auto-Export and Workers
        self.miscSettingsGroupBox = QGroupBox("Miscellaneous Settings", self)
        self.miscSettingsLayout = QFormLayout(self.miscSettingsGroupBox)
        self.autoExportCheckBox = QCheckBox("Enable Auto-Export", self.miscSettingsGroupBox)
        self.workersSpinBox = QSpinBox(self.miscSettingsGroupBox)
        self.workersSpinBox.setRange(1, 20)
        self.workersSpinBox.setValue(10)
        self.miscSettingsLayout.addRow(self.autoExportCheckBox)
        self.miscSettingsLayout.addRow(QLabel("Number of Workers:"), self.workersSpinBox)
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

    def selected_title(self, item):
        name = item.text()
        if not self.master.settings.is_open:
            self.master.settings.connect()
        self.reject()
        self.master.selected_chosen_result(name, toggle_search_bar=False)
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
        self.master.reload_gui()
        self.reject()

    def replace_database(self, new_db_path):
        """Replace the existing settings database with a new one."""
        temp_path = os.path.join(self.master.data_folder, "temp_data.db")
        try:
            # Safely attempt to replace the database
            shutil.copyfile(new_db_path, temp_path)
            os.remove(os.path.join(self.master.data_folder, "data2.db"))
            shutil.move(temp_path, os.path.join(self.master.data_folder, "data2.db"))
        except Exception as e:
            print(f"Failed to replace the database: {e}")
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def import_settings_from_json(self, json_path):
        """Import settings from a JSON file into the SQLite database."""
        try:
            with open(json_path, 'r') as file:
                settings_data = json.load(file).get("settings")

            db_path = os.path.join(self.master.data_folder, "data2.db")
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

    def load_settings(self, settings: dict):
        self.recentTitlesList.clear()
        recent_titles = settings.get("recent_titles")
        recent_titles.reverse()
        self.recentTitlesList.addItems((' '.join(word[0].upper() + word[1:] if word else '' for word in title.split()) for title in recent_titles))
        self.lightThemeComboBox.setCurrentText(("(" if "_" in settings.get("themes").get("light") else "") + settings.get("themes").get("light").replace("_", ") ").title() + (" Theme" if settings.get("themes").get("light") != "modern" else ""))
        self.darkThemeComboBox.setCurrentText(("(" if "_" in settings.get("themes").get("dark") else "") + settings.get("themes").get("dark").replace("_", ") ").title() + (" Theme" if settings.get("themes").get("dark") != "modern" else ""))
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
        self.workersSpinBox.setValue(settings.get("misc").get("num_workers"))

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

    def accept(self):
        # Collect all settings here for processing
        self.selected_settings = {
            "recent_titles": list(reversed([self.recentTitlesList.item(x).text().lower() for x in range(self.recentTitlesList.count())])),
            "themes": {
                "light": self.lightThemeComboBox.currentText().lstrip("(").lower().replace(") ", "_").removesuffix(
                    " theme"),
                "dark": self.darkThemeComboBox.currentText().lstrip("(").lower().replace(") ", "_").removesuffix(
                    " theme"),
                "font": self.fontComboBox.currentText()},
            "settings_file_path": self.fileLocationLineEdit.text(),
            "settings_file_mode": "overwrite" if self.overwriteRadioButton.isChecked() else "modify" if self.modifyRadioButton.isChecked() else "create_new",
            "misc": {"auto_export": self.autoExportCheckBox.isChecked(),
                     "num_workers": self.workersSpinBox.value()}}

        super().accept()

    def reject(self):
        super().reject()


class CustomLabel(QLabel):
    def paintEvent(self, event):
        painter = QPainter(self)

        if self.text():
            main_window = self.window()
            while main_window.parent() is not None:
                main_window = main_window.parent()
            # If the label has text, apply background color based on the current theme
            if main_window.theme == "light":
                painter.setBrush(QBrush(QColor('#d0d0d0')))
            else:
                painter.setBrush(QBrush(QColor('#555555')))

            painter.setPen(QPen(Qt.NoPen))  # No border outline
            radius = 5
            painter.drawRoundedRect(self.rect(), radius, radius)

        painter.end()
        # super().paintEvent(event)


class TaskRunner(QThread):
    task_completed = Signal(bool, object)
    progress_signal = Signal(int)

    def __init__(self, new_thread, func, *args, **kwargs):
        super().__init__()
        self.new_thread = new_thread
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.is_running = True
        self.worker_thread = None
        self.result = None
        self.success = False
        if new_thread:
            self.progress_queue = queue.Queue()

    class TaskCanceledException(Exception):
        """Exception to be raised when the task is canceled"""
        def __init__(self, message="A intended error occured"):
            self.message = message
            super().__init__(self.message)

    def run(self):
        if not self.is_running:
            return

        try:
            if self.new_thread:
                self.worker_thread = threading.Thread(target=self.worker_func)
                self.worker_thread.start()
                while self.worker_thread.is_alive():
                    try:
                        progress = self.progress_queue.get_nowait()
                        self.progress_signal.emit(progress)
                    except queue.Empty:
                        pass
                    self.worker_thread.join(timeout=0.1)
                print("Worker thread died. Emitting result now ...")
            else:
                print("Directly executing")
                update = False
                for update in self.func(*self.args, **self.kwargs)():
                    if isinstance(update, int):
                        self.progress_signal.emit(update)
                self.result = update
                print("RES", self.result)
            self.task_completed.emit(self.success, self.result)

        except Exception as e:
            self.task_completed.emit(False, None)
            print(e)

    def worker_func(self):
        try:
            if self.new_thread:
                self.result = self.func(*self.args, **self.kwargs, progress_queue=self.progress_queue)
            else:
                return self.func(*self.args, **self.kwargs)
            self.success = True
        except SystemExit:
            self.success = False
            self.result = None
            print("Task was forcefully stopped.")
        except Exception as e:
            self.success = False
            self.result = None
            print(f"Error in TaskRunner: {e}")

    def stop(self):
        print("Task is stopping.")
        self.is_running = False
        if not self.isFinished():
            self.raise_exception()
            self.wait()

    def get_thread_id(self):
        if self.worker_thread:
            return self.worker_thread.ident

    def raise_exception(self):
        thread_id = self.get_thread_id()
        if thread_id:
            res = ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(thread_id), ctypes.py_object(SystemExit))
            if res > 1:
                ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, 0)
                print("Exception raise failure")


class CustomProgressDialog(QProgressDialog):
    def __init__(self, parent, window_title, window_icon, window_label="Doing a task...", button_text="Cancel",
                 new_thread=True, func=lambda: None, *args, **kwargs):
        super().__init__(parent=parent, cancelButtonText=button_text, minimum=0, maximum=100)
        self.ttimer = TimidTimer()
        self.setWindowTitle(window_title)
        # self.setValue(0)
        # self.setWindowIcon(QIcon(window_icon))

        self.customLayout = QVBoxLayout(self)
        self.customLabel = QLabel(window_label, self)
        self.customLayout.addWidget(self.customLabel)
        self.customLayout.setAlignment(self.customLabel, Qt.AlignTop | Qt.AlignHCenter)

        self.taskRunner = TaskRunner(new_thread, func, *args, **kwargs)
        self.taskRunner.task_completed.connect(self.onTaskCompleted)
        self.taskRunner.progress_signal.connect(self.set_value)  # Connect progress updates
        self.task_successful = False

        self.setAutoClose(False)
        self.setAutoReset(False)
        self.setWindowModality(Qt.ApplicationModal)
        self.canceled.connect(self.cancelTask)
        self.show()

        self.last_value = 0
        self.current_value = 0
        QTimer.singleShot(50, self.taskRunner.start)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.updateProgress)
        self.timer.start(100)
        print(self.ttimer.tick(), "INIT DONE")

    def updateProgress(self):
        if self.value() <= 100 and not self.wasCanceled() and self.taskRunner.isRunning():
            if self.current_value == 0 and self.value() < 10:
                self.setValue(self.value() + 1)
                time.sleep(random.randint(2, 10) * 0.1)
            elif self.current_value >= 10:
                self.smooth_value()
            QApplication.processEvents()

    def set_value(self, v):
        self.current_value = v

    def smooth_value(self):
        # If the difference is significant, set the value immediately
        if abs(self.current_value - self.last_value) > 10:  # You can adjust this threshold
            self.setValue(self.current_value)
            self.last_value = self.current_value
            return

        for i in range(max(10, self.last_value), self.current_value):
            self.setValue(i + 1)
            self.last_value = i + 1
            time.sleep(0.1)
        # print(f"Exiting go_to_value with value {self.current_value} and last_value {self.last_value}") # Debug

    def resizeEvent(self, event):
        super(CustomProgressDialog, self).resizeEvent(event)

        # Attempt to find the label as a child widget
        label: QLabel = self.findChild(QLabel)
        if label:
            label.setStyleSheet("""background: transparent;""")

    @Slot(bool, object)
    def onTaskCompleted(self, success, result):
        print("Task completed method called.")
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
                palette = QPalette(self.palette())
                palette.setColor(QPalette.Highlight, QColor(Qt.red))
                self.setPalette(palette)
                self.customLabel.setText("Task failed!")
                self.setCancelButtonText("Close")
        print("DONE", self.ttimer.end())

    def cancelTask(self):
        self.taskRunner.stop()
        self.taskRunner.wait()
        self.setValue(0)
        self.customLabel.setText("Task cancelled")
        self.close()

    def closeEvent(self, event):
        if self.taskRunner.isRunning():
            self.cancelTask()
        event.accept()


class ImageLabel(QLabel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


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
        self.search_bar = QLineEdit(self)
        self.search_bar.setPlaceholderText("Search...")
        self.search_bar.textChanged.connect(self.on_text_changed)
        self.search_bar.returnPressed.connect(self.on_return_pressed)

        self.results_list = QListWidget(self)
        self.results_list.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Ignored)
        self.results_list.hide()
        self.results_list.itemActivated.connect(self.on_item_activated)

        layout = QVBoxLayout(self)
        layout.addWidget(self.search_bar)
        layout.addWidget(self.results_list)
        layout.setContentsMargins(0, 0, 0, 0)  # Set margins to zero
        layout.setSpacing(0)  # Set spacing to zero

    def on_text_changed(self, text):
        self.results_list.clear()
        if text and self.search_bar.hasFocus():
            # Assume get_search_results is a function that returns a list of tuples with the result text and icon path.
            results = self.search_results_func(text)
            for result_text, icon_path in results:
                item = QListWidgetItem(result_text)
                item.setIcon(QIcon(env.absolute_path(icon_path)))
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


class AdvancedQMessageBox(QMessageBox):
    def __init__(self, parent=None, icon=None, window_title='', text='', detailed_text='',
                 checkbox=None, standard_buttons=QMessageBox.StandardButton.Ok, default_button=None):
        """
        An advanced QMessageBox with additional configuration options.

        :param parent: The parent widget.
        :param icon: The icon to display.
        :param window_title: The title of the message box window.
        :param text: The text to display.
        :param detailed_text: The detailed text to display.
        :param checkbox: A QCheckBox instance.
        :param standard_buttons: The standard buttons to include.
        :param default_button: The default button.
        """
        super().__init__(parent)
        self.setStandardButtons(standard_buttons)
        for arg, func in zip([icon, window_title, text, detailed_text, checkbox, default_button],
                             ["setIcon", "setWindowTitle", "setText", "setDetailedText", "setCheckBox", "setDefaultButton"]):
            if arg:
                getattr(self, func)(arg)

        # Set the window to stay on top initially
        self.setWindowState(self.windowState() & ~Qt.WindowState.WindowMaximized)

        self.raise_()
        self.activateWindow()


class QNoSpacingVBoxLayout(QVBoxLayout):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setContentsMargins(0, 0, 0, 0)
        self.setSpacing(0)


class QNoSpacingHBoxLayout(QHBoxLayout):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setContentsMargins(0, 0, 0, 0)
        self.setSpacing(0)


class DummyViewport(QWidget):
    def __init__(self, widget, viewport):
        super().__init__()
        self.widget = widget
        self._viewport = viewport

    def width(self):
        return self._viewport.width() - self._viewport.verticalScrollBar().width()

    def height(self):
        return self._viewport.height() - self._viewport.horizontalScrollBar().height()

    def size(self):
        return QSize(self._viewport.width() - self._viewport.v_scrollbar.width(),
                     self._viewport.height() - self._viewport.h_scrollbar.height())

    def mapToGlobal(self, pos):
        return self.widget.mapToGlobal(pos)

    def grabGesture(self, gesture_type):
        return self.widget.grabGesture(gesture_type)


class CustomScrollArea(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.layout = QNoSpacingVBoxLayout()
        self.layout.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)
        self.setLayout(self.layout)

        # Create a content widget that will hold the scrollable content
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout()
        self.content_widget.setLayout(self.content_layout)

        # Set the size policy of the content widget to be Ignored
        self.content_widget.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Ignored
        )

        # Set the size policy of the content layout to be Ignored
        self.content_layout.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)

        # Create vertical scrollbar
        self._v_scrollbar = QScrollBar()
        self._v_scrollbar.setOrientation(Qt.Vertical)
        self._v_scrollbar.setVisible(False)

        # Create horizontal scrollbar
        self._h_scrollbar = QScrollBar()
        self._h_scrollbar.setOrientation(Qt.Horizontal)
        self._h_scrollbar.setVisible(False)

        self.corner_widget = QWidget()
        self.corner_widget.setStyleSheet("background: transparent;")
        # self.corner_widget.setAutoFillBackground(True)

        h_scrollbar_layout = QNoSpacingHBoxLayout()
        h_scrollbar_layout.addWidget(self._h_scrollbar)
        h_scrollbar_layout.addWidget(self.corner_widget)
        h_scrollbar_layout.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)

        self.corner_widget.setFixedSize(self._v_scrollbar.width(), self._h_scrollbar.height())

        hbox = QNoSpacingHBoxLayout()
        hbox.addWidget(self.content_widget)
        hbox.addWidget(self._v_scrollbar)
        hbox.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)

        vbox = QNoSpacingVBoxLayout()
        vbox.addLayout(hbox)
        vbox.addLayout(h_scrollbar_layout)
        vbox.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)

        self.layout.addLayout(vbox)

        # Connect scrollbar value changed signal to update content widget position
        self._v_scrollbar.valueChanged.connect(self.updateContentPosition)
        self._h_scrollbar.valueChanged.connect(self.updateContentPosition)

        self._view = DummyViewport(self.content_widget, self)

        self._vert_scroll_pol = "as"
        self._hor_scroll_pol = "as"

    def viewport(self):
        return self._view

    def setWidgetResizable(self, value: bool):
        return

    def contentWidget(self):
        return self.content_widget

    def verticalScrollBar(self):
        return self._v_scrollbar

    def horizontalScrollBar(self):
        return self._h_scrollbar

    def setVerticalScrollBarPolicy(self, policy):
        if policy == Qt.ScrollBarPolicy.ScrollBarAsNeeded:
            self._vert_scroll_pol = "as"
        elif policy == Qt.ScrollBarPolicy.ScrollBarAlwaysOff:
            self._vert_scroll_pol = "off"
        else:
            self._vert_scroll_pol = "on"
        self.reload_scrollbars()
        self.content_widget.resize(self.content_widget.sizeHint())

    def setHorizontalScrollBarPolicy(self, policy):
        if policy == Qt.ScrollBarPolicy.ScrollBarAsNeeded:
            self._hor_scroll_pol = "as"
        elif policy == Qt.ScrollBarPolicy.ScrollBarAlwaysOff:
            self._hor_scroll_pol = "off"
        else:
            self._hor_scroll_pol = "on"
        self.reload_scrollbars()
        self.content_widget.resize(self.content_widget.sizeHint())

    def verticalScrollBarPolicy(self):
        if self._vert_scroll_pol == "as":
            return Qt.ScrollBarPolicy.ScrollBarAsNeeded
        elif self._vert_scroll_pol == "off":
            return Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        else:
            return Qt.ScrollBarPolicy.ScrollBarAlwaysOn

    def horizontalScrollBarPolicy(self, policy):
        if self._hor_scroll_pol == "as":
            return Qt.ScrollBarPolicy.ScrollBarAsNeeded
        elif self._hor_scroll_pol == "off":
            return Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        else:
            return Qt.ScrollBarPolicy.ScrollBarAlwaysOn

    def updateContentPosition(self, value):
        # Update the position of the content widget based on the scrollbar values
        self.content_widget.move(-self._h_scrollbar.value(), -self._v_scrollbar.value())

    def reload_scrollbars(self):
        # print(self._v_scrollbar.value())
        # print(self._h_scrollbar.value())
        content_size = self.content_widget.sizeHint()
        content_size_2 = self.content_widget.size()

        # Check if scrollbars are needed
        if (content_size.height() > self.height() and self._vert_scroll_pol == "as") or self._vert_scroll_pol == "on":
            self._v_scrollbar.setVisible(True)
            self._v_scrollbar.setPageStep(self.height())
        else:
            self._v_scrollbar.setVisible(False)
        max_v_scroll = max(0, content_size.height() - self.height())
        self._v_scrollbar.setRange(0, max_v_scroll)

        if (content_size_2.width() > self.width() and self._hor_scroll_pol == "as") or self._hor_scroll_pol == "on":
            self._h_scrollbar.setVisible(True)
            self._h_scrollbar.setPageStep(self.width())
        else:
            self._h_scrollbar.setVisible(False)
        max_h_scroll = max(0, content_size_2.width() - self.width())
        self._h_scrollbar.setRange(0, max_h_scroll)

        if self._h_scrollbar.isVisible() and self._v_scrollbar.isVisible():
            self.corner_widget.show()
        else:
            self.corner_widget.hide()
        self.corner_widget.setFixedSize(self._v_scrollbar.width(), self._h_scrollbar.height())
        self.updateContentPosition(0)

    def resizeEvent(self, event):
        # Get the original size of the content widget
        original_content_size = self.content_widget.sizeHint()
        original_content_size.setWidth(event.size().width())

        self.recorded_default_size = original_content_size

        # Resize the content widget to match the original size
        self.content_widget.resize(original_content_size)

        #for widget in [self.content_widget.layout().itemAt(i).widget() for i in range(self.content_widget.layout().count())]:
        #    if hasattr(widget, "pixmap") and widget.pixmap():
        #        widget.resize(widget.pixmap().width(), widget.pixmap().height())

        self.reload_scrollbars()

        event.accept()

    def wheelEvent(self, event):
        # Scroll with the mouse wheel
        delta = event.angleDelta().y()
        self._v_scrollbar.setValue(self._v_scrollbar.value() - delta // 8)


class QAdvancedSmoothScrollingArea(CustomScrollArea):
    def __init__(self, parent=None, sensitivity: int = 1):
        super().__init__(parent)
        # self.setWidgetResizable(True)

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.horizontalScrollBar().setSingleStep(24)
        self.verticalScrollBar().setSingleStep(24)

        # Scroll animations for both scrollbars
        self.v_scroll_animation = QPropertyAnimation(self.verticalScrollBar(), b"value")
        self.h_scroll_animation = QPropertyAnimation(self.horizontalScrollBar(), b"value")
        for anim in (self.v_scroll_animation, self.h_scroll_animation):
            anim.setEasingCurve(QEasingCurve.OutCubic)
            anim.setDuration(500)

        self.sensitivity = sensitivity

        # Scroll accumulators
        self.v_toScroll = 0
        self.h_toScroll = 0

        self.primary_scrollbar = "vertical"

    def set_primary_scrollbar(self, new_primary_scrollbar: Literal["vertical", "horizontal"]):
        self.primary_scrollbar = new_primary_scrollbar

    def change_scrollbar_state(self, scrollbar: Literal["vertical", "horizontal"], state: bool = False):
        state = Qt.ScrollBarPolicy.ScrollBarAsNeeded if state else Qt.ScrollBarPolicy.ScrollBarAlwaysOff

        self.setVerticalScrollBarPolicy(state)
        self.setHorizontalScrollBarPolicy(state)

    def wheelEvent(self, event: QWheelEvent):
        horizontal_event_dict = {
            "scroll_bar": self.horizontalScrollBar(),
            "animation": self.h_scroll_animation,
            "toScroll": self.h_toScroll
        }
        vertical_event_dict = {
            "scroll_bar": self.verticalScrollBar(),
            "animation": self.v_scroll_animation,
            "toScroll": self.v_toScroll
        }

        # Choose scroll bar based on right mouse button state
        if event.buttons() & Qt.MouseButton.RightButton:
            event_dict = horizontal_event_dict if self.primary_scrollbar == "vertical" else vertical_event_dict
        else:
            event_dict = vertical_event_dict if self.primary_scrollbar == "vertical" else horizontal_event_dict

        angle_delta = event.angleDelta().y()
        steps = angle_delta / 120
        pixel_step = int(event_dict.get("scroll_bar").singleStep() * self.sensitivity)

        if event_dict.get("animation").state() == QPropertyAnimation.Running:
            event_dict.get("animation").stop()
            event_dict["toScroll"] += event_dict.get("animation").endValue() - event_dict.get("scroll_bar").value()

        current_value = event_dict.get("scroll_bar").value()
        max_value = event_dict.get("scroll_bar").maximum()
        min_value = event_dict.get("scroll_bar").minimum()

        # Inverted scroll direction calculation
        event_dict["toScroll"] -= pixel_step * steps
        proposed_value = current_value + event_dict["toScroll"]  # Reflecting changes

        if proposed_value > max_value and steps > 0:
            event_dict["toScroll"] = 0
        elif proposed_value < min_value and steps < 0:
            event_dict["toScroll"] = 0

        new_value = current_value + event_dict["toScroll"]
        event_dict.get("animation").setStartValue(current_value)
        event_dict.get("animation").setEndValue(new_value)
        event_dict.get("animation").start()

        event.accept()  # Prevent further processing of the event


class Settings:
    def __init__(self, db_path, overwrite_settings: Optional[dict] = None, export_settings_func=lambda: None):
        self.db = DBManager(db_path)
        self.is_open = True
        self.default_settings = {
            "provider": "ManhwaClan",
            "title": "Thanks for using ManhwaViewer!",
            "chapter": "1",
            "downscaling": "True",
            "upscaling": "False",
            "manual_content_width": "1200",
            "borderless": "True",
            "hide_titlebar": "False",
            "hover_effect_all": "True",
            "acrylic_menus": "True",
            "acrylic_background": "False",
            "hide_scrollbar": "True",
            "stay_on_top": "False",
            "geometry": "100, 100, 640, 480",
            "blacklisted_websites": "247manga.com, ww6.mangakakalot.tv, jimanga.com, mangapure.net, mangareader.mobi, onepiece.fandom.com, mangaowl.io",
            "advanced_settings": '{"recent_titles": [], "themes": {"light": "light_light", "dark": "dark", "font": "Segoe UI"}, "settings_file_path": "", "settings_file_mode": "overwrite", "misc": {"auto_export": false, "num_workers": 10}}',
            "provider_type": "direct",
            "chapter_rate": "0.5",
            "no_update_info": "True",
            "update_info": "True",
            "last_scroll_positions": "0, 0",
            "scrolling_sensitivity": "4.0",
            "lazy_loading": "True",
            "save_last_titles": "True"
        }
        self.settings = self.default_settings.copy()
        if overwrite_settings:
            self.settings.update(overwrite_settings)
        if not os.path.isfile(db_path):
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

    def str_to_list(self, s: str) -> List[str]:
        return s.split(", ")

    def list_to_str(self, lst: List[str]) -> str:
        return ', '.join(lst)

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
                     "update_info", "lazy_loading", "save_last_titles"]:
            return self.boolean(value)
        elif key in ["manual_content_width"]:
            return int(value)
        elif key in ["geometry", "last_scroll_positions"]:
            return [int(x) for x in value.split(", ")]
        elif key in ["advanced_settings"]:
            return json.loads(value)
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
                     "update_info", "lazy_loading", "save_last_titles"]:
            value = str(value)
        elif key in ["manual_content_width"]:
            value = str(int(value))
        elif key in ["geometry", "last_scroll_positions"]:
            value = ', '.join([str(x) for x in value])
        elif key in ["advanced_settings"]:
            value = json.dumps(value)
        self.settings[key] = value
        self.update_data()
        if self.get_advanced_settings()["misc"]["auto_export"]:
            self.export_settings_func()

    def get_provider(self):
        return self.get("provider")

    def set_provider(self, value):
        self.set("provider", value)

    def get_title(self):
        return self.get("title")

    def set_title(self, value):
        self.set("title", value)

    def get_chapter(self):
        return self.get("chapter")

    def set_chapter(self, value):
        self.set("chapter", value)

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

    def get_blacklisted_websites(self):
        return self.get("blacklisted_websites")

    def set_blacklisted_websites(self, value):
        self.set("blacklisted_websites", value)

    def get_advanced_settings(self):
        return self.get("advanced_settings")

    def set_advanced_settings(self, value):
        self.set("advanced_settings", value)

    def get_provider_type(self):
        return self.get("provider_type")

    def set_provider_type(self, value):
        self.set("provider_type", value)

    def get_chapter_rate(self):
        return self.get("chapter_rate")

    def set_chapter_rate(self, value):
        self.set("chapter_rate", value)

    def get_no_update_info(self):
        return self.get("no_update_info")

    def set_no_update_info(self, value):
        self.set("no_update_info", value)

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
    def __init__(self, path, prov_plug, prov_sub_plugs: list):
        self.path = path
        self.prov_plug = prov_plug
        self.prov_sub_plugs = prov_sub_plugs
        self.providers = self._load_providers()

    def _load_providers(self):
        providers = {}
        for file in os.listdir(self.path):
            if file.endswith('.py') or file.endswith('.pyd') and file != '__init__.py':
                module_name = file.split(".")[0]
                module_path = os.path.join(self.path, file)
                spec = importlib.util.spec_from_file_location(module_name, module_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                for attribute_name in dir(module):
                    attribute = getattr(module, attribute_name)
                    if (isinstance(attribute, type) and issubclass(attribute, self.prov_plug) and attribute not in
                            self.prov_sub_plugs):
                        providers[attribute_name] = attribute
        return providers

    def get_providers(self):
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
    window = QAdvancedSmoothScrollingArea()
    window.setWindowTitle('Custom Scroll Area')
    window.setGeometry(100, 100, 300, 200)

    # Add some example content
    for i in range(20):
        label = QLabel(f"Item {i}" * 30)
        window.content_layout.addWidget(label)

    window.show()
    sys.exit(app.exec_())

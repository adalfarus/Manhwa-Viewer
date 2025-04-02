"""TBA"""
from PySide6.QtWidgets import (QListWidget, QDialog, QStyledItemDelegate, QComboBox, QGroupBox, QVBoxLayout, QFormLayout,
                               QFontComboBox, QLabel, QLineEdit, QToolButton, QHBoxLayout, QRadioButton, QPushButton,
                               QCheckBox, QSpinBox, QDialogButtonBox, QListWidgetItem, QWidget, QFileDialog, QMenu,
                               QStyleOptionComboBox, QStyle, QDoubleSpinBox, QProgressBar, QSizePolicy, QMessageBox,
                               QTextEdit)
from PySide6.QtCore import QPropertyAnimation, QEasingCurve, QByteArray, Qt, QTimer, Signal, QPoint
from PySide6.QtGui import QWheelEvent, QFont, QPaintEvent, QPainter, QFontMetrics

from .tasks import CustomProgressDialog

import sqlite3
import shutil
import json
import os



class QSmoothScrollingList(QListWidget):
    def __init__(self, parent=None, sensitivity: int = 1):
        super().__init__(parent)
        # self.setWidgetResizable(True)

        # Scroll animation setup
        self.scroll_animation = QPropertyAnimation(self.verticalScrollBar(), QByteArray(b"value"))
        self.scroll_animation.setEasingCurve(QEasingCurve.Type.OutCubic)  # Smoother deceleration
        self.scroll_animation.setDuration(50)  # Duration of the animation in milliseconds

        self.sensitivity = sensitivity
        self.toScroll = 0  # Total amount left to scroll

    def wheelEvent(self, event: QWheelEvent):
        angle_delta = event.angleDelta().y()
        steps = angle_delta / 120  # Standard steps calculation for a wheel event
        pixel_step = int(self.verticalScrollBar().singleStep() * self.sensitivity)

        if self.scroll_animation.state() == QPropertyAnimation.State.Running:
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
    def __init__(self, parent: QWidget | None = None, current_settings: dict | None = None, default_settings: dict | None = None,
                 master=None, available_themes=None, export_settings_func=None) -> None:
        super().__init__(parent, Qt.WindowType.WindowCloseButtonHint | Qt.WindowType.WindowTitleHint)

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


# TODO: Determine if still needed
class UnselectableDelegate(QStyledItemDelegate):
    def editorEvent(self, event, model, option, index):
        # Prevent selection of disabled items
        data = model.itemData(index)
        if Qt.ItemDataRole.UserRole in data and data[Qt.ItemDataRole.UserRole] == "disabled":
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
            if self.itemData(index, Qt.ItemDataRole.UserRole) == "disabled":
                self.setCurrentIndex(self.previousIndex)
            else:
                self.previousIndex = index

    def setItemUnselectable(self, index):
        # Set data role to indicate item is disabled
        self.model().setData(self.model().index(index, 0), "disabled", Qt.ItemDataRole.UserRole)


class LibraryEdit(QComboBox):
    set_library_name = Signal(tuple)
    remove_library = Signal(tuple)

    def __init__(self, display_names: bool = True, show_path_end: bool = False, name_template: str = "{name}→", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self._display_names: bool = display_names
        self.show_path_end: bool = show_path_end
        self._name_template: str = name_template
        self._libraries: list[tuple[str, str]] = []

    def set_new_name_template(self, template: str) -> None:
        self._name_template = template

    def set_lib_name(self, library_path: str, new_name: str) -> None:
        for index, (name, path) in enumerate(self._libraries):
            if path == library_path:
                self._libraries[index] = (new_name, path)
                self.setItemText(index, f"{self._name_template.format(name=new_name)}{path}")
                self.setCurrentIndex(index)
                return  # Exit after updating

    def set_current_library_path(self, library_path: str) -> None:
        for index, (name, path) in enumerate(self._libraries):
            if path == library_path:
                self.setCurrentIndex(index)
                return

    def add_library_item(self, library_name: str, library_path: str) -> None:
        if any(p == library_path for _, p in self._libraries):
            return  # Already exists
        self._libraries.append((library_name, library_path))
        if self._display_names:
            self.addItem(f"{self._name_template.format(name=library_name)}{library_path}")
        else:
            self.addItem(library_path)
        self.setCurrentIndex(len(self._libraries) - 1)

    def clear(self, /) -> None:
        self._libraries.clear()
        super().clear()

    def _show_context_menu(self, pos: QPoint) -> None:
        """Shows the menu with a right-click"""
        if len(self._libraries) == 0:
            return
        menu = QMenu(self)
        set_name_action = menu.addAction("Set name")
        remove_action = menu.addAction("Remove")
        action = menu.exec(self.mapToGlobal(pos))
        if action == set_name_action:
            self.set_library_name.emit(self._libraries[self.currentIndex()])
        elif action == remove_action:
            idx = self.currentIndex()
            if 0 <= idx < len(self._libraries):
                item = self._libraries.pop(idx)
                self.removeItem(idx)
                self.remove_library.emit(item)

    def current_library(self) -> tuple[str, str]:
        if self.currentIndex() == -1:
            return "", ""
        return self._libraries[self.currentIndex()]

    def paintEvent(self, event: QPaintEvent):
        if self.isEditable() or not self.show_path_end:
            super().paintEvent(event)
            return

        painter = QPainter(self)

        # Prepare style option
        option = QStyleOptionComboBox()
        self.initStyleOption(option)

        # Get the area where the text should be drawn
        edit_rect = self.style().subControlRect(
            QStyle.ComplexControl.CC_ComboBox,
            option,
            QStyle.SubControl.SC_ComboBoxEditField,
            self
        )

        # Get elided text
        metrics = QFontMetrics(self.font())
        text = self.currentText()
        elided = metrics.elidedText(text, Qt.TextElideMode.ElideMiddle, edit_rect.width())

        # Draw full control first (background, arrow, etc.)
        self.style().drawComplexControl(QStyle.ComplexControl.CC_ComboBox, option, painter, self)

        # Draw elided text manually
        painter.drawText(edit_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, elided)


class TransferDialog(QDialog):
    def __init__(self, parent, current_chapter: float = 1.0, chapter_rate: float = 1.0):
        super().__init__(parent)
        self.setWindowTitle("Transfer chapter(s) from Provider to Library")
        self.setFixedWidth(400)
        self.setModal(True)

        self.chapter_rate = chapter_rate
        self.transfer_in_progress = False

        self.main_layout = QVBoxLayout(self)

        # Chapter range layout
        range_layout = QHBoxLayout()
        self.from_input = QDoubleSpinBox()
        self.from_input.setRange(0, 9999)
        self.from_input.setDecimals(2)
        self.from_input.setSingleStep(chapter_rate)
        self.from_input.setValue(current_chapter)

        self.to_input = QDoubleSpinBox()
        self.to_input.setRange(0, 9999)
        self.to_input.setDecimals(2)
        self.to_input.setSingleStep(chapter_rate)
        self.to_input.setValue(current_chapter)

        # Connect validation logic
        self.from_input.valueChanged.connect(self.sync_to_min)
        self.to_input.valueChanged.connect(self.sync_from_max)

        range_layout.addWidget(QLabel("Chapter range:"))
        range_layout.addWidget(self.from_input)
        range_layout.addWidget(self.to_input)
        self.main_layout.addLayout(range_layout)

        # Return checkbox
        self.return_checkbox = QCheckBox("Return to current chapter after finished")
        self.return_to_chapter = False
        self.return_checkbox.checkStateChanged.connect(
            lambda: setattr(self, "return_to_chapter", self.return_checkbox.isChecked())
        )
        self.main_layout.addWidget(self.return_checkbox)

        # Quality preset dropdown
        quality_layout = QHBoxLayout()
        quality_layout.addWidget(QLabel("Quality preset:"))
        self.quality_combo = QComboBox()
        self.quality_combo.addItems([
            "Best Quality",
            "Quality",
            "Size",
            "Smallest Size"
        ])
        quality_layout.addWidget(self.quality_combo)
        self.main_layout.addLayout(quality_layout)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(False)

        progress_container = QHBoxLayout()
        progress_container.setContentsMargins(0, 0, 0, 0)
        self.progress_label = QLabel("0 of 0 chapters transferred")
        self.progress_label.setVisible(False)
        progress_container.addWidget(self.progress_bar)
        progress_container.addWidget(self.progress_label)

        self.main_layout.addLayout(progress_container)

        # Transfer button
        self.transfer_button = QPushButton("Transfer")
        self.transfer_button.clicked.connect(self.start_transfer)
        self.main_layout.addWidget(self.transfer_button)

    def sync_to_min(self, from_val: float):
        to_val = self.to_input.value()
        if from_val > to_val or not self._is_multiple(to_val - from_val):
            steps = max(0, round((to_val - from_val) / self.chapter_rate))
            new_to = from_val + steps * self.chapter_rate
            self.to_input.blockSignals(True)
            self.to_input.setValue(round(new_to, 2))
            self.to_input.blockSignals(False)

    def sync_from_max(self, to_val: float):
        from_val = self.from_input.value()
        if to_val < from_val or not self._is_multiple(to_val - from_val):
            steps = max(0, round((to_val - from_val) / self.chapter_rate))
            new_from = to_val - steps * self.chapter_rate
            self.from_input.blockSignals(True)
            self.from_input.setValue(round(new_from, 2))
            self.from_input.blockSignals(False)

    def _is_multiple(self, diff: float) -> bool:
        return abs((diff / self.chapter_rate) - round(diff / self.chapter_rate)) < 1e-6

    def start_transfer(self):
        from_val = self.from_input.value()
        to_val = self.to_input.value()

        if self.parent().library_edit.current_library()[1] == "":
            QMessageBox.warning(self, "No library selected", "Please select a library to enable \nthe transfer of chapters.")
            return

        self.transfer_in_progress = True

        self.from_input.setEnabled(False)
        self.to_input.setEnabled(False)
        self.quality_combo.setEnabled(False)
        self.transfer_button.setEnabled(False)

        self.progress_bar.setVisible(True)
        self.progress_label.setVisible(True)
        self.progress_bar.setValue(0)

        self.transfer_chapters(from_val, to_val)

    def transfer_chapters(self, from_val: float, to_val: float):
        chapter_rate = self.chapter_rate

        self.quality_preset = self.quality_combo.currentText().lower().replace(" ", "_")

        num_chapters = int(round((to_val - from_val) / chapter_rate)) + 1
        self.total_chapters = num_chapters
        self.current_index = 0
        self.progress_label.setText(f"{self.current_index} of {self.total_chapters} chapters transferred")
        self.chapter_list = [round(from_val + i * chapter_rate, 2) for i in range(num_chapters)]
        self.first_chapter = True

        # if float(self.parent().chapter_selector.text()) != from_val:
        #     self.parent().reset_caches()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.transfer_next_chapter)
        self.timer.start(10)

    def transfer_next_chapter(self):
        if self.current_index >= len(self.chapter_list):
            self.timer.stop()
            self.finish_transfer()
            return

        chapter = self.chapter_list[self.current_index]
        self.current_index += 1

        parent = self.parent()
        # if self.first_chapter:
        #     self.first_chapter = False
        # else:
        #     parent.advance_cache()
        if parent:
            parent.chapter_selector.setText(str(chapter))
            parent.set_chapter()
            parent.ensure_loaded_chapter()
            args = (
                parent.provider,
                chapter,
                f"Chapter {chapter}",
                parent.cache_manager.get_cache_folder(chapter),
                self.quality_preset
            )
            kwargs = {}
            progress_dialog = CustomProgressDialog(
                parent=self,
                window_title="Transferring ...",
                window_label="Doing a task...",
                button_text="Cancel",
                new_thread=True,
                func=parent.saver.save_chapter,
                args=args,
                kwargs=kwargs)
            progress_dialog.exec()

            print("Transfer Task: ", progress_dialog.task_successful)
            if not progress_dialog.task_successful:
                QMessageBox.information(self, "Info", "Transferring of the chapter has failed!\nLook in the logs for more info.",
                                        QMessageBox.StandardButton.Ok,
                                        QMessageBox.StandardButton.Ok)

        progress = int((self.current_index / self.total_chapters) * 100)
        self.progress_bar.setValue(progress)
        self.progress_label.setText(f"{self.current_index} of {self.total_chapters} chapters transferred")

    def finish_transfer(self):
        self.transfer_in_progress = False

        self.accept()

        QMessageBox.information(
            self,
            "Transfer Complete",
            f"Transfer of chapter {self.chapter_list[0]:.2f}–{self.chapter_list[-1]:.2f} done.",
            QMessageBox.StandardButton.Ok
        )

    def closeEvent(self, event):
        if self.transfer_in_progress:
            event.ignore()
        else:
            event.accept()


class WaitingDialog(QDialog):
    def __init__(self, parent=None, message="Waiting for all tasks to finish..."):
        super().__init__(parent)
        self.setWindowTitle("Info")
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowTitleHint)
        self.setModal(True)

        layout = QVBoxLayout(self)
        label = QLabel(message, self)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)

        self.setFixedSize(300, 100)


class TutorialPopup(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setWindowTitle("Tutorial")

        layout = QVBoxLayout()
        self.setLayout(layout)

        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setHtml("""
<h1>Welcome to the Tutorial</h1>
<p>Scroll down to explore features and controls of the app.</p>
<hr>

<h2>📂 Basic Navigation</h2>
<p>➡️ On the <b>right</b>, you'll find the <b>Side Menu</b>:</p>

<ul>
  <li><b>Comic Provider:</b> where your images come from
    <ul>
      <li>⚫ Grayed-out = temporarily unavailable (e.g., site is down)</li>
      <li>❌ Not shown = unsupported (e.g., JS-loaded images)</li>
      <li>📚 For library providers, make sure the matching library manager is selected</li>
    </ul>
  </li>
  <li><b>Library Manager:</b> controls how chapters are stored</li>
  <ul>
    <li><b>Comic Book:</b> supports CBZ/CBR/CB7/CBT, writes CBZ. Resizes images based on quality level (100%, 75%, 50%, 25%)</li>
    <li><b>DeepC:</b> saves images as videos using ffmpeg (needs ffmpeg installed + on PATH)</li>
    <li><b>Std:</b> saves plain folders of images. Resizes images based on quality level (100%, 75%, 50%, 25%)</li>
    <li><b>Tiff:</b> uses TIFF format. Size per chapter depends on compression:<br>
      - Uncompressed ~300MB<br>
      - LZW ~200MB<br>
      - Deflate ~80MB<br>
      - JPEG-compressed ~30MB</li>
    <li><b>WebP:</b> stores .webp files, with quality settings: 50, 30, 10, 0 (100 = lossless)</li>
  </ul>
  <li><b>Chapter Settings:</b> title, number, and chapter increment rate</li>
  <li><b>Library:</b> where files are saved. Click the tool icon to add new ones</li>
</ul>

<h2>➡️ Navigation Buttons:</h2>
<ul>
  <li>⬅️ Previous / ➡️ Next chapter</li>
  <li>🔄 Re-download (clears cache & reloads from provider)</li>
  <li>♻️ Re-load app (resets GUI & backend. Double-click = resets window size & pos)</li>
</ul>

<h2>🛠 UI Options</h2>
<ul>
  <li>🏷 Provider logo toggle (top-left)</li>
  <li>🔍 Search All — triggers search across all searchable providers</li>
  <li>✨ Hover Effects</li>
  <li>🧱 Borderless Mode</li>
  <li>💧 Acrylic Menus + Background</li>
  <li>📐 Downscale / Upscale toggles</li>
  <li>🔃 Lazy Loading (can improve large image scroll)</li>
  <li>📏 Manual Width: base width of images</li>
  <li>🚫 Hide Titlebar / Scrollbar</li>
  <li>📌 Stay on Top (but popups may appear behind)</li>
  <li>🎚 Sensitivity Slider (controls scroll intensity: 100%, 1000%, 10000%)</li>
  <li>💾 Save Last Title</li>
  <li>📤 Transfer Chapter(s)</li>
  <li>⚙️ Advanced Settings</li>
</ul>

<h2>🔎 Search Bar</h2>
<p>Located at the <b>top</b> of the window:</p>
<ul>
  <li>Search the active provider (if supported)</li>
  <li>Press <b>Enter</b> or click the search icon</li>
  <li>If the search bar has a <b>gold border</b>, Search All is active</li>
</ul>

<h2>⚙️ Advanced Settings Overview</h2>
<ul>
  <li>🕘 Recent Titles (if enabled)</li>
  <li>🎨 Styling (themes & fonts)</li>
  <li>🧳 Settings Export/Import (optional)</li>
  <li>📦 Chapter Management (cache & transfer)</li>
</ul>
        """)
        # content.setHtml("""
        #     <h1>Welcome to the Tutorial</h1>
        #     <p>Scroll to explore features:</p>
        #     <hr>
        #     <p><b>Basic navigation</b>:</p>
        #     <p>- On the right you have the <b>Side-Menu</b>, here you can select the: </p>
        #     <p>   > Comic provider (where the images come from)</p>
        #     <p>      > If a provider currently does not work, it is grayed out (e.g. the website is down)</p>
        #     <p>      > If a provider can't work, it is not included in the list (e.g. using javascript to load images)</p>
        #     <p>      > If you select a library provider, you also need to use the corresponding library manager (otherwise it won't know what to search, ...)</p>
        #     <p>   > Library manager (to manage the saved images)</p>
        #     <p>      > If the currently select library isn't supported, it is deselected and you won't be able to select it again</p>
        #     <p>      > There are several default library managers included: </p>
        #     <p>         > Comic Book library (can read CBZ, CBR, CB7 and CBT, will write CBZ. Quality will resize the images to 100%, 75%, 50% and 25% respectively)</p>
        #     <p>         > DeepC library (uses ffmpeg binaries to encode chapter images into videos to enable massive space savings while preserving quality, needs ffmpeg to be installed on your system and be accessible through your PATH)</p>
        #     <p>         > Std library (will just save the plain images within a folder. Quality will resize the images to 100%, 75%, 50% and 25% respectively)</p>
        #     <p>         > Tiff library (uses the tiff file format, tuned for maximum quality but large files. Quality will change compression modes to uncompressed ~300mb per chapter, lossless compressed 200mb per chapter, good compression 80mb per chapter, jpeg lossy compression 30mb per chapter)</p>
        #     <p>         > WebP library (will save all images as .webp. Quality changes the quality attribute of the images, they are 50, 30, 10 and 0 with 100 being lossless and 0 being the worst)</p>
        #     <p>   > Title and chapter</p>
        #     <p>   > Chapter rate (how much the chapter is increased for every time you click next)</p>
        #     <p>   > Library (where the images are saved, click the tool button next to it to add a library. A library may not be compatible with all library managers.)</p>
        #     <p>   > Navigation buttons:</p>
        #     <p>      > Previous and next</p>
        #     <p>      > Re-download chapter (clears the caches and re gets the chapter from the provider)</p>
        #     <p>      > Re-load the app (reloads all gui and backend components of the app, clicking it twice within one second will also reset window position and size)</p>
        #     <p>   > Provider logo checkbox (this dis or enables the transparent provider logo in the top left)</p>
        #     <p>   > Search all button (this will search all providers that are capable of searching and display the first two results for each. This effect is active for as long as the search bar remains circled with gold)</p>
        #     <p>   > Hover effect all checkbox (adds a hover effect to all gui elements, sometimes bugged)</p>
        #     <p>   > Borderless checkbox (removes border between image area and window edge)</p>
        #     <p>   > Acrylic menus checkbox (makes all menus transparent)</p>
        #     <p>   > Acrylic background checkbox (makes the app background transparent)</p>
        #     <p>   > Downscale if larger than window checkbox (images that are larger than the window are downscaled to the window size)</p>
        #     <p>   > Upscale if smaller than window checkbox (images that are smaller than the window are upscaled to the window size)</p>
        #     <p>   > LL checkbox (enables or disabled lazy loading of images, may or may not make the experience better depending on the image dimensions)</p>
        #     <p>   > Manual width spinbox (sets the base width of all images, that means if the images aren't modied by down- or upscaling, what width should they have)</p>
        #     <p>   > Hide titlebar checkbox (hides the windows titlebar)</p>
        #     <p>   > Hide scrollbar checkbox (hides the image areas scrollbars)</p>
        #     <p>   > Stay on top checkbox (makes the window stay on top of all other windows, sadly popups will appear behind it)</p>
        #     <p>   > Current sensitivity slider (the current sensitivity of the image area, normal scroll = 100%, scrollbar scroll = 1000%, scrollbar click = 10000%)</p>
        #     <p>   > Save last titles checkbox (if the app should save the last titles + chapter + provider you've selected)</p>
        #     <p>   > Transfer chapter(s) (opens chapter transfer dialog, from the provider to the library)</p>
        #     <p>   > Adv settings (opens advanced settings dialog)</p>
        #     <p>- On the top you have the <b>Search-Bar</b></p>
        #     <p>   > Here you can search the provider, if it is supported</p>
        #     <p>   > Press [ENTER] or the search button to initiate the search</p>
        #     <p>   > If you've clicked the search all button, the search bar will have a golden border as long as you don't click away. This means it will search all providers.</p>
        #     <p><b>Advanced settings</b> are ... into several sections:</p>
        #     <p>- Recent titles (recent titles saved if the recent titles checkbox is checked)</p>
        #     <p>- Styling (here you can select different themes and fonts)</p>
        #     <p>- Settings file handling (not really necessary to use anymore, lets you export and import settings for the app)</p>
        #     <p>- Chapter management settings (transfer and cache settings)</p>
        #
        #     <p><b>Basic navigation</b>:</p>
        #     <p><b>25%</b>: Side menu usage and keyboard shortcuts.</p>
        #     <p><b>50%</b>: Library settings and import/export.</p>
        #     <p><b>75%</b>: Image formats and custom savers.</p>
        #     <p><b>100%</b>: You're ready to go!</p>
        # """)
        self.text_edit.setMaximumHeight(600)

        layout.addWidget(self.text_edit)

        # Checkbox + OK button
        self.checkbox = QCheckBox("Do not show again")
        layout.addWidget(self.checkbox)

        ok_button = QPushButton("Ok")
        ok_button.clicked.connect(self.accept)
        layout.addWidget(ok_button)

        self.text_edit.verticalScrollBar().valueChanged.connect(self.on_scroll)
        self.menu_opened = False

    def on_scroll(self):
        scrollbar = self.text_edit.verticalScrollBar()
        max_scroll = scrollbar.maximum()
        current = scrollbar.value()
        progress = current / max_scroll if max_scroll > 0 else 0.0
        self._on_tutorial_scroll(progress)

    def _on_tutorial_scroll(self, progress: float) -> None:
        parent = self.parent()

        if (0.1 <= progress < 0.9 or progress == 1.0) and not getattr(self, "menu_opened", False):
            self.menu_opened = True
            parent.toggle_side_menu()
        elif progress > 0.9 and progress != 1.0 and getattr(self, "menu_opened", False):
            self.menu_opened = False
            parent.toggle_side_menu()
        if 0.8 <= progress < 0.99 and not getattr(self, "search_bar_shown", False):
            self.search_bar_shown = True
            parent.toggle_search_bar()
        elif progress > 0.99 and getattr(self, "search_bar_shown", False):
            self.search_bar_shown = False
            parent.toggle_search_bar()
        if progress >= 0.9 and not getattr(self, "search_highlight_triggered", False):
            self.search_highlight_triggered = True
            parent.search_all()
        if progress == 1.0 and not getattr(self, "advanced", False):
            self.advanced = True
            parent.advanced_settings(blocking=False)
            self.raise_()
        # reset if scrolling back up
        if progress < 0.9:
            self.search_highlight_triggered = False
        # print(f"Tutorial scroll progress: {progress:.2f}")

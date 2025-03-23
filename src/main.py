<<<<<<<< Updated upstream:nmv.py
# Copyright xbyteW 2024
========
"""Copyright adalfarus 2025"""
>>>>>>>> Stashed changes:src/main.py
import config  # Configures python environment before anything else is done
config.check()
config.setup()

<<<<<<<< Updated upstream:nmv.py
from PySide6.QtWidgets import (QApplication, QLabel, QVBoxLayout, QWidget, QMainWindow, QCheckBox, QHBoxLayout,
                               QScroller, QSpinBox, QPushButton, QGraphicsOpacityEffect, QScrollerProperties, QFrame,
                               QComboBox, QFormLayout, QLineEdit, QMessageBox, QScrollBar, QSizePolicy)
from PySide6.QtGui import QDesktopServices, QPixmap, QIcon, QDoubleValidator, QFont, QImage
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QRect, QUrl
# from PySide6.QtMultimediaWidgets import QVideoWidget
# from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtGui import QColor

from modules.AutoProviderPlugin import AutoProviderPlugin, AutoProviderBaseLike, AutoProviderBaseLike2
from modules.Classes import (CustomProgressDialog, ImageLabel, SearchWidget, AdvancedQMessageBox,
                             CustomComboBox, Settings, QAdvancedSmoothScrollingArea, AutoProviderManager,
                             AdvancedSettingsDialog)
from modules.themes import Themes

# Apt stuff ( update to newer version )
from aplustools.io.loggers import monitor_stdout
from aplustools.data.updaters import VersionNumber
from aplustools.io.environment import System
from aplustools import set_dir_to_ex

from urllib.parse import urlparse
import requests
========
# Std Lib imports
from argparse import ArgumentParser
from traceback import format_exc
import multiprocessing
>>>>>>>> Stashed changes:src/main.py
import sqlite3
import logging
import random
import json
import math
import time
import sys
import os

# Third party imports
from packaging.version import Version, InvalidVersion
import stdlib_list
<<<<<<<< Updated upstream:nmv.py
multiprocessing.freeze_support()
hiddenimports = list(stdlib_list.stdlib_list())

set_dir_to_ex()
os.chdir(os.path.join(os.getcwd(), './_internal'))
========
import requests
import shutil
# PySide6
from PySide6.QtWidgets import (QApplication, QLabel, QVBoxLayout, QWidget, QMainWindow, QHBoxLayout, QScroller, QSpinBox,
                               QPushButton, QGraphicsOpacityEffect, QScrollerProperties, QFrame, QComboBox, QFormLayout,
                               QLineEdit, QMessageBox, QScrollBar, QGraphicsProxyWidget, QCheckBox, QToolButton,
                               QFileDialog, QMenu, QInputDialog, QSizePolicy, QStyleOptionComboBox, QStyle, QDialog,
                               QProgressBar, QDoubleSpinBox)
from PySide6.QtGui import (QDesktopServices, QPixmap, QIcon, QDoubleValidator, QFont, QImage, QPainter, QFontMetrics,
                           QPaintEvent)
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QRect, QUrl, QSize, Signal, QPoint
from PySide6.QtGui import QColor
# aplustools
from aplustools.io.env import diagnose_shutdown_blockers
from aplustools.io.qtquick import QQuickMessageBox
# Apt stuff ( update to newer version )
from oaplustools.io.loggers import monitor_stdout
from oaplustools.data.updaters import VersionNumber
from oaplustools.io.environment import System

# Internal imports
from core.modules.ProviderPlugin import CoreProvider, OfflineProvider
from core.modules.Classes import (CustomProgressDialog, SearchWidget, Settings, TargetContainer, VerticalManagement,
                                  AutoProviderManager, AdvancedSettingsDialog)
from core.modules.themes import Themes

# Standard typing imports for aps
import collections.abc as _a
import typing as _ty
import types as _ts

multiprocessing.freeze_support()
hiddenimports = list(stdlib_list.stdlib_list())


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
    def __init__(self, parent: "MainWindow", current_chapter: float = 1.0, chapter_rate: float = 1.0):
        super().__init__(parent)
        self.setWindowTitle("Transfer chapter(s) from Provider to Library")
        self.setFixedWidth(400)
        self.setModal(True)

        self.chapter_rate = chapter_rate
        self.transfer_in_progress = False

        self.layout = QVBoxLayout(self)

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
        self.layout.addLayout(range_layout)

        # Return checkbox
        self.return_checkbox = QCheckBox("Return to current chapter after finished")
        self.return_to_chapter = False
        self.return_checkbox.checkStateChanged.connect(
            lambda: setattr(self, "return_to_chapter", self.return_checkbox.isChecked())
        )
        self.layout.addWidget(self.return_checkbox)

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
        self.layout.addLayout(quality_layout)

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

        self.layout.addLayout(progress_container)

        # Transfer button
        self.transfer_button = QPushButton("Transfer")
        self.transfer_button.clicked.connect(self.start_transfer)
        self.layout.addWidget(self.transfer_button)

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

        if float(self.parent().chapter_selector.text()) != from_val:
            self.parent().reset_caches()
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
        if self.first_chapter:
            self.first_chapter = False
        else:
            parent.advance_cache()
        if parent:
            parent.chapter_selector.setText(str(chapter))
            parent.set_chapter()
            parent.ensure_loaded_chapter()
            args = (
                parent.provider,
                chapter,
                f"Chapter {chapter}",
                parent.cache_folder,
                self.quality_preset
            )
            kwargs = {}
            progress_dialog = CustomProgressDialog(
                parent=self,
                window_title="Transferring ...",
                window_icon="",
                window_label="Doing a task...",
                button_text="Cancel",
                new_thread=True,
                func=parent.saver.save_chapter,
                args=args,
                kwargs=kwargs)
            progress_dialog.exec()

            print("Transfer Task: ", progress_dialog.task_successful)
            if not progress_dialog.task_successful:
                QMessageBox.information(self, "Info | Transferring of the chapter has failed!", "Look in the logs for more info.",
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
            QMessageBox.Ok
        )

    def closeEvent(self, event):
        if self.transfer_in_progress:
            event.ignore()
        else:
            event.accept()


class CacheManager:
    def __init__(self, base_cache_folder: str) -> None:
        ...
>>>>>>>> Stashed changes:src/main.py


class MainWindow(QMainWindow):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.transferring = False

<<<<<<<< Updated upstream:nmv.py
        self.data_folder = os.path.abspath('./data').strip("/")
        self.cache_folder = os.path.abspath('./cache').strip("/")
========
        self.data_folder = os.path.abspath('default-config/data').strip("/")
        self.cache_folder = os.path.abspath('default-config/caches/cache').strip("/")
        self.last_cache_folder = os.path.abspath('default-config/caches/last_cache').strip("/")
        self.next_cache_folder = os.path.abspath('default-config/caches/next_cache').strip("/")
>>>>>>>> Stashed changes:src/main.py
        self.modules_folder = os.path.abspath('./modules').strip("/")
        self.extensions_folder = os.path.abspath('extensions').strip("/")

        self.logger = monitor_stdout(f"{self.data_folder}/logs.txt")

        self.system = System()

        self.setWindowTitle("Manhwa Viewer 166")
        self.setWindowIcon(QIcon(f"{self.data_folder}/Untitled-1-noBackground.png"))

        db_path = f"{self.data_folder}/data.db"

        if int(self.system.get_major_os_version()) <= 10:
            self.settings = Settings(db_path, {"geometry": "100, 100, 800, 630", "advanced_settings": '{"recent_titles": [], "themes": {"light": "light", "dark": "dark", "font": "Segoe UI"}, "settings_file_path": "", "settings_file_mode": "overwrite", "misc": {"auto_export": false, "num_workers": 10}}',}, self.export_settings)
        else:
            self.settings = Settings(db_path, {"geometry": "100, 100, 800, 630"}, self.export_settings)
        # self.settings.set_geometry([100, 100, 800, 630])

        self.os_theme = self.system.get_windows_theme() or os.environ.get('MV_THEME') or "light"
        self.theme = None
        self.update_theme(self.os_theme.lower())

        x, y, height, width = self.settings.get_geometry()
        self.setGeometry(x, y + 31, height, width)  # Somehow saves it as 31 pixels less
        self.setup_gui()

        # Advanced setup
        self.provider_dict = self.provider = None
        self.provider_combobox.currentIndexChanged.disconnect()
        self.known_working_searchers = []
        self.reload_providers()
        self.switch_provider(self.settings.get_provider())
        self.provider_combobox.currentIndexChanged.connect(self.change_provider)

        self.reload_window_title()

        # Scaling stuff
        self.previous_scrollarea_width = self.scrollarea.width()
        self.content_paths = self.get_content_paths()
        self.task_successful = False
        self.threading = False
        self.gui_changing = False  # So we don't clear caches if the gui is changing

        self.reload_gui()
        self.downscaling = self.downscale_checkbox.isChecked()
        self.upscaling = self.upscale_checkbox.isChecked()

        if not self.hover_effect_all_checkbox.isChecked():
            self.reload_hover_effect_all_setting()
            self.reload_acrylic_menus_setting(callback=True)
        else:
            self.reload_hover_effect_all_setting()
            self.reload_acrylic_menus_setting()
        self.reload_borderless_setting()
        self.reload_acrylic_background_setting()

        self.reload_hide_titlebar_setting()
        self.reload_hide_scrollbar_setting()
        self.reload_stay_on_top_setting()

        self.update_sensitivity(int(self.settings.get_scrolling_sensitivity() * 10))

        self.show()
        self.check_for_update()

        self.force_rescale = False
        self.content_widgets = []
        self.reload_content()
        self.force_rescale = True
        QTimer.singleShot(50, lambda: (
            self.scrollarea.verticalScrollBar().setValue(self.settings.get_last_scroll_positions()[0]),
            self.scrollarea.horizontalScrollBar().setValue(self.settings.get_last_scroll_positions()[1])
        ))
        self.last_reload_ts = time.time()

    def check_for_update(self):
        try:
            response = requests.get("https://raw.githubusercontent.com/adalfarus/update_check/main/mv/update.json",
                                    timeout=1)
        except Exception as e:
            title = "Info"
            text = "There was an error when checking for updates."
            description = f"{e}"
            msg_box = AdvancedQMessageBox(self, QMessageBox.Icon.Information, title, text, description,
                                          standard_buttons=QMessageBox.StandardButton.Ok,
                                          default_button=QMessageBox.StandardButton.Ok)

            msg_box.exec()
            return
        try:
            update_json = response.json()
        except (requests.exceptions.RequestException, requests.exceptions.JSONDecodeError, ValueError) as e:
            print(f"An error occurred: {e}")
            return

        # Initializing all variables
        newest_version = VersionNumber(update_json["metadata"]["newestVersion"])
        newest_version_data = update_json["versions"][-1]
        for release in update_json["versions"]:
            if release["versionNumber"] == newest_version:
                newest_version_data = release
        push = newest_version_data["push"].title() == "True"
        current_version = "166"
        found_version = None

        # Find a version bigger than the current version and prioritize versions with push
        for version_data in reversed(update_json["versions"]):
            this_version = VersionNumber(version_data['versionNumber'])
            push = version_data["push"].title() == "True"

            if this_version > current_version:
                found_version = version_data
                if push:
                    break

        if not found_version:
            found_version = newest_version_data
        push = found_version["push"].title() == "True"

        if found_version['versionNumber'] > current_version and self.settings.get_update_info() and push:
            title = "There is an update available"
            text = (f"There is a newer version ({found_version.get('versionNumber')}) "
                    f"available.\nDo you want to open the link to the update?")
            description = found_version.get("Description")
            checkbox = QCheckBox("Do not show again")
            msg_box = AdvancedQMessageBox(self, QMessageBox.Icon.Question, title, text, description, checkbox,
                                          QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                          QMessageBox.StandardButton.Yes)
            msg_box.raise_()
            retval = msg_box.exec()

            if checkbox.isChecked():
                print("Do not show again selected")
                self.settings.set_update_info(False)
            if retval == QMessageBox.StandardButton.Yes:
                if found_version.get("updateUrl", "None").title() == "None":
                    link = update_json["metadata"].get("sorryUrl", "https://example.com")
                else:
                    link = found_version.get("updateUrl")
                QDesktopServices.openUrl(QUrl(link))
        elif self.settings.get_no_update_info() and (push or found_version['versionNumber'] == current_version):
            title = "Info"
            text = (f"No new updates available.\nChecklist last updated "
                    f"{update_json['metadata']['lastUpdated'].replace('-', '.')}.")
            description = f"v{found_version['versionNumber']}\n{found_version.get('description')}"
            checkbox = QCheckBox("Do not show again")
            msg_box = AdvancedQMessageBox(self, QMessageBox.Icon.Information, title, text, description, checkbox,
                                          QMessageBox.StandardButton.Ok, QMessageBox.StandardButton.Ok)
            msg_box.raise_()
            msg_box.exec()

            if checkbox.isChecked():
                print("Do not show again selected")
                self.settings.set_no_update_info(False)
        elif self.settings.get_no_update_info() and not push:
            title = "Info"
            text = (f"New version available, but not recommended {found_version['versionNumber']}.\n"
                    f"Checklist last updated {update_json['metadata']['lastUpdated'].replace('-', '.')}.")
            description = found_version.get("description")
            checkbox = QCheckBox("Do not show again")
            msg_box = AdvancedQMessageBox(self, QMessageBox.Icon.Information, title, text, description,
                                          checkbox, QMessageBox.StandardButton.Ok, QMessageBox.StandardButton.Ok)
            msg_box.raise_()
            msg_box.exec()

            if checkbox.isChecked():
                print("Do not show again selected")
                self.settings.set_no_update_info(False)
<<<<<<<< Updated upstream:nmv.py
        else:
            print("Bug, please fix me.")

    def setup_gui(self):
        # Central Widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.window_layout = QVBoxLayout(central_widget)

        # Scroll Area
        self.scrollarea = QAdvancedSmoothScrollingArea(self, self.settings.get_scrolling_sensitivity())
        self.scrollarea.setWidgetResizable(True)
        self.scrollarea.verticalScrollBar().setSingleStep(24)
        self.window_layout.addWidget(self.scrollarea)

        # Content widgets
        # content_widget = QWidget()
        # self.scrollarea.setWidget(content_widget)
        self.content_layout = self.scrollarea.content_layout  # QVBoxLayout(content_widget)

        # Enable kinetic scrolling
        scroller = QScroller.scroller(self.scrollarea.viewport())
        scroller.grabGesture(self.scrollarea.viewport(), QScroller.ScrollerGestureType.TouchGesture)
        scroller_properties = QScrollerProperties(scroller.scrollerProperties())
        scroller_properties.setScrollMetric(QScrollerProperties.ScrollMetric.MaximumVelocity, 0.3)
        scroller.setScrollerProperties(scroller_properties)

        # Add buttons at the end of the content, side by side
        self.buttons_widget = QWidget()
        buttons_layout = QHBoxLayout(self.buttons_widget)
        previous_chapter_button = QPushButton("Previous")
        buttons_layout.addWidget(previous_chapter_button)
        next_chapter_button = QPushButton("Next")
        buttons_layout.addWidget(next_chapter_button)

        # Add a transparent image on the top left
        self.transparent_image = QLabel(self)
        self.transparent_image.setObjectName("transparentImage")
        self.transparent_image.setPixmap(QPixmap(os.path.abspath(f"{self.data_folder}/empty.png")))
        self.transparent_image.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        opacity = QGraphicsOpacityEffect(self.transparent_image)
        opacity.setOpacity(0.5)  # Adjust the opacity level
        self.transparent_image.setGraphicsEffect(opacity)
        self.transparent_image.setAttribute(Qt.WA_TransparentForMouseEvents, True)

        # Search Toggle Button
        self.search_bar_toggle_button = QPushButton("^", self)
        self.search_bar_toggle_button.setFixedHeight(20)  # Set fixed height, width will be set in resizeEvent
        self.search_bar_toggle_button.move(0, 0)

        # Search Bar
        self.search_widget = SearchWidget(lambda: None)
        self.search_widget.adjustSize()
        self.search_widget.search_bar.setMinimumHeight(30)
        self.search_widget.setMinimumHeight(30)
        self.search_widget.move(0, -self.search_widget.height())  # Initially hide the search bar
        self.search_widget.setParent(self)

        # Search Bar Animation
        self.search_bar_animation = QPropertyAnimation(self.search_widget, b"geometry")
        self.search_bar_animation.setDuration(300)

        # Side Menu
        self.side_menu = QFrame(self)
        self.side_menu.setObjectName("sideMenu")
        self.side_menu.setFrameShape(QFrame.Shape.StyledPanel)
        self.side_menu.setAutoFillBackground(True)
        self.side_menu.move(int(self.width() * 2 / 3), 0)
        self.side_menu.resize(int(self.width() / 3), self.height())

        # Animation for Side Menu
        self.side_menu_animation = QPropertyAnimation(self.side_menu, b"geometry")
        self.side_menu_animation.setDuration(500)

        # Side Menu Layout & Widgets
        side_menu_layout = QFormLayout(self.side_menu)
        self.side_menu.setLayout(side_menu_layout)

        self.provider_combobox = CustomComboBox()
        provider_layout = QHBoxLayout()
        provider_layout.addWidget(QLabel("Provider:"))
        provider_layout.addWidget(self.provider_combobox)
        side_menu_layout.addRow(provider_layout)

        title_layout = QHBoxLayout()
        title_layout.addWidget(QLabel("Title:"))
        self.title_selector = QLineEdit()
        self.title_selector.setMinimumWidth(120)
        title_layout.addWidget(self.title_selector)
        side_menu_layout.addRow(title_layout)

        self.chapter_selector = QLineEdit()
        side_menu_layout.addRow(QLabel("Chapter:"), self.chapter_selector)
        self.chapter_selector.setValidator(QDoubleValidator(0.5, 999.5, 1))

        self.chapter_rate_selector = QLineEdit()
        side_menu_layout.addRow(QLabel("Chapter Rate:"), self.chapter_rate_selector)
        self.chapter_selector.setValidator(QDoubleValidator(0.1, 2, 1))

        self.provider_type_combobox = QComboBox(self)
        self.provider_type_combobox.addItem("Indirect", 0)
        self.provider_type_combobox.addItem("Direct", 1)
        side_menu_layout.addRow(self.provider_type_combobox, QLabel("Provider Type"))

        previous_chapter_button_side_menu = QPushButton("Previous")
        next_chapter_button_side_menu = QPushButton("Next")
        self.reload_chapter_button = QPushButton(QIcon(f"{self.data_folder}/empty.png"), "")
        self.reload_content_button = QPushButton(QIcon(f"{self.data_folder}/empty.png"), "")

        side_menu_buttons_layout = QHBoxLayout()
        side_menu_buttons_layout.addWidget(previous_chapter_button_side_menu)
        side_menu_buttons_layout.addWidget(next_chapter_button_side_menu)
        side_menu_buttons_layout.addWidget(self.reload_chapter_button)
        side_menu_buttons_layout.addWidget(self.reload_content_button)
        side_menu_layout.addRow(side_menu_buttons_layout)

        [side_menu_layout.addRow(QWidget()) for _ in range(3)]

        blacklist_button = QPushButton("Blacklist Current URL")
        side_menu_layout.addRow(blacklist_button)

        [side_menu_layout.addRow(QWidget()) for _ in range(3)]

        self.hover_effect_all_checkbox = QCheckBox("Hover effect all")
        self.borderless_checkbox = QCheckBox("Borderless")
        hover_borderless_layout = QHBoxLayout()
        hover_borderless_layout.setContentsMargins(0, 0, 0, 0)
        hover_borderless_layout.addWidget(self.hover_effect_all_checkbox)
        hover_borderless_layout.addWidget(self.borderless_checkbox)
        self.acrylic_menus_checkbox = QCheckBox("Acrylic Menus")
        self.acrylic_background_checkbox = QCheckBox("Acrylic Background")
        acrylic_layout = QHBoxLayout()
        acrylic_layout.setContentsMargins(0, 0, 0, 0)
        acrylic_layout.addWidget(self.acrylic_menus_checkbox)
        acrylic_layout.addWidget(self.acrylic_background_checkbox)
        side_menu_layout.addRow(hover_borderless_layout)
        side_menu_layout.addRow(acrylic_layout)

        [side_menu_layout.addRow(QWidget()) for _ in range(3)]

        # Scale checkboxes
        self.downscale_checkbox = QCheckBox("Downscale if larger than window")
        self.upscale_checkbox = QCheckBox("Upscale if smaller than window")
        self.lazy_loading_checkbox = QCheckBox("LL")
        lazy_loading_layout = QHBoxLayout()
        lazy_loading_layout.setContentsMargins(0, 0, 0, 0)
        lazy_loading_layout.addWidget(self.upscale_checkbox)
        lazy_loading_layout.addWidget(self.lazy_loading_checkbox)
        side_menu_layout.addRow(self.downscale_checkbox)
        side_menu_layout.addRow(lazy_loading_layout)

        # SpinBox for manual width input and Apply Button
        self.manual_width_spinbox = QSpinBox()
        self.manual_width_spinbox.setRange(10, 2000)
        side_menu_layout.addRow(self.manual_width_spinbox)

        apply_manual_width_button = QPushButton("Apply Width")
        side_menu_layout.addRow(apply_manual_width_button)

        [side_menu_layout.addRow(QWidget()) for _ in range(3)]

        # Window style checkboxes
        self.hide_title_bar_checkbox = QCheckBox("Hide titlebar")
        self.hide_scrollbar_checkbox = QCheckBox("Hide Scrollbar")
        hide_layout = QHBoxLayout()
        hide_layout.setContentsMargins(0, 0, 0, 0)
        hide_layout.addWidget(self.hide_title_bar_checkbox)
        hide_layout.addWidget(self.hide_scrollbar_checkbox)
        side_menu_layout.addRow(hide_layout)
        self.stay_on_top_checkbox = QCheckBox("Stay on top")
        side_menu_layout.addRow(self.stay_on_top_checkbox)

        [side_menu_layout.addRow(QWidget()) for _ in range(3)]

        self.scroll_sensitivity_scroll_bar = QScrollBar(Qt.Orientation.Horizontal)
        self.scroll_sensitivity_scroll_bar.setMinimum(1)  # QScrollBar uses integer values
        self.scroll_sensitivity_scroll_bar.setMaximum(80)  # We multiply by 10 to allow decimal
        self.scroll_sensitivity_scroll_bar.setValue(10)  # Default value set to 1.0 (10 in this scale)
        self.scroll_sensitivity_scroll_bar.setSingleStep(1)
        self.scroll_sensitivity_scroll_bar.setPageStep(1)

        # Label to display the current sensitivity
        self.sensitivity_label = QLabel("Current Sensitivity: 1.0")
        side_menu_layout.addRow(self.sensitivity_label, self.scroll_sensitivity_scroll_bar)

        [side_menu_layout.addRow(QWidget()) for _ in range(3)]

        self.save_last_titles_checkbox = QCheckBox("Save last titles")
        side_menu_layout.addRow(self.save_last_titles_checkbox)
        export_settings_button = QPushButton("Export Settings")
        advanced_settings_button = QPushButton("Adv Settings")
        side_menu_layout.addRow(export_settings_button, advanced_settings_button)

        # Menu Button
        self.menu_button = QPushButton(QIcon(f"{self.data_folder}/empty.png"), "", self.centralWidget())
        self.menu_button.setFixedSize(40, 40)

        # Timer to regularly check for resizing needs
        timer = QTimer(self)
        timer.start(500)

        # Connect GUI components
        self.search_bar_toggle_button.clicked.connect(self.toggle_search_bar)
        # Checkboxes
        self.downscale_checkbox.toggled.connect(self.downscale_checkbox_toggled)
        self.upscale_checkbox.toggled.connect(self.upscale_checkbox_toggled)
        self.borderless_checkbox.toggled.connect(self.reload_borderless_setting)
        self.acrylic_menus_checkbox.toggled.connect(self.reload_acrylic_menus_setting)
        self.acrylic_background_checkbox.toggled.connect(self.reload_acrylic_background_setting)
        self.hide_scrollbar_checkbox.toggled.connect(self.reload_hide_scrollbar_setting)
        self.stay_on_top_checkbox.toggled.connect(self.reload_stay_on_top_setting)
        self.hide_title_bar_checkbox.toggled.connect(self.reload_hide_titlebar_setting)
        self.hover_effect_all_checkbox.toggled.connect(self.reload_hover_effect_all_setting)
        self.save_last_titles_checkbox.toggled.connect(self.toggle_save_last_titles_checkbox)
        # Selectors
        self.title_selector.textChanged.connect(self.set_title)
        self.chapter_selector.textChanged.connect(self.set_chapter)
        self.chapter_rate_selector.textChanged.connect(self.set_chapter_rate)
        # Menu components
        self.menu_button.clicked.connect(self.toggle_side_menu)  # Menu
        apply_manual_width_button.clicked.connect(self.apply_manual_content_width)  # Menu
        previous_chapter_button.clicked.connect(self.previous_chapter)  # Menu
        next_chapter_button.clicked.connect(self.next_chapter)  # Menu
        self.reload_chapter_button.clicked.connect(self.reload_chapter)  # Menu
        self.reload_content_button.clicked.connect(self.reload)  # Menu
        previous_chapter_button_side_menu.clicked.connect(self.previous_chapter)
        next_chapter_button_side_menu.clicked.connect(self.next_chapter)
        advanced_settings_button.clicked.connect(self.advanced_settings)  # Menu
        export_settings_button.clicked.connect(self.export_settings)  # Menu
        blacklist_button.clicked.connect(self.blacklist_current_url)  # Menu
        # Rest
        self.provider_combobox.currentIndexChanged.connect(self.change_provider)  # Menu
        self.provider_type_combobox.currentIndexChanged.connect(self.change_provider_type)
        self.side_menu_animation.valueChanged.connect(self.side_menu_animation_value_changed)  # Menu
        timer.timeout.connect(self.timer_tick)
        self.search_bar_animation.valueChanged.connect(self.search_bar_animation_value_changed)
        self.search_widget.selectedItem.connect(self.selected_chosen_result)
        self.scroll_sensitivity_scroll_bar.valueChanged.connect(self.update_sensitivity)

        # Style GUI components
        self.centralWidget().setStyleSheet("background: transparent;")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.content_layout.setSpacing(0)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.menu_button.setIcon(QIcon(f"{self.data_folder}/menu_icon.png"))
        if self.theme == "light":
            self.reload_chapter_button.setIcon(QIcon(f"{self.data_folder}/reload_chapter_icon_dark.png"))
            self.reload_content_button.setIcon(QIcon(f"{self.data_folder}/reload_icon_dark.png"))
        else:
            self.reload_chapter_button.setIcon(QIcon(f"{self.data_folder}/reload_chapter_icon_light.png"))
            self.reload_content_button.setIcon(QIcon(f"{self.data_folder}/reload_icon_light.png"))

        # Disable some components
        blacklist_button.setEnabled(False)
        # self.save_last_titles_checkbox.setEnabled(False)
        # export_settings_button.setEnabled(False)
        # advanced_settings_button.setEnabled(False)
========
        #else:
        #    self.button_popup("Update Info", "There was a logic-error when checking for updates.", "", "Information", ["Ok"], "Ok")

    def handle_search_all(self, text: str) -> None:
        provider_name, rest = text.split(": ", maxsplit=1)
        title, chapter = rest.rsplit(", Ch ", maxsplit=1)
        self.selected_chosen_item(f"{provider_name}\x00{title}\x00{chapter}")
>>>>>>>> Stashed changes:src/main.py

    def toggle_save_last_titles_checkbox(self):
        self.settings.set_save_last_titles(self.save_last_titles_checkbox.isChecked())

    def advanced_settings(self):
        settings = self.settings.get_advanced_settings()
        default_settings = json.loads(self.settings.get_default_setting("advanced_settings"))
        self.settings.close()
        available_themes = tuple(key for key in Themes.__dict__.keys() if not (key.startswith("__") or key.endswith("__")))
        dialog = AdvancedSettingsDialog(parent=self, current_settings=settings, default_settings=default_settings, master=self, available_themes=available_themes, export_settings_func=self.export_settings)
        dialog.exec()
        if not self.settings.is_open:
            self.settings.connect()
        if dialog.selected_settings is not None:
            self.settings.set_advanced_settings(dialog.selected_settings)
            font = QFont(self.settings.get_advanced_settings().get("themes").get("font"), self.font().pointSize())
            self.setFont(font)
            for child in self.findChildren(QWidget):
                child.setFont(font)
            self.update()
            self.repaint()

            # if settings["misc"]["num_workers"] != dialog.selected_settings["misc"]["num_workers"]:
            #     self.switch_provider(self.provider_combobox.currentText())
            if (settings["themes"]["light"] != dialog.selected_settings["themes"]["light"]
                    or settings["themes"]["dark"] != dialog.selected_settings["themes"]["dark"]):
                result = QMessageBox.question(self, "Restart Client?",
                                              "You must restart the client for the theme changes to take effect.\nDo you wish to continue?",
                                              QMessageBox.StandardButtons(QMessageBox.Yes | QMessageBox.No),
                                              QMessageBox.Yes)
                if result == QMessageBox.Yes:
                    print("Exiting ...")
                    self.save_settings()
                    sys.stdout.close()
                    self.settings.close()
                    QApplication.exit(1000)

    @staticmethod
    def fetch_all_data_as_json(db_file, return_dict: bool = False):
        # Connect to the SQLite database
        connection = sqlite3.connect(db_file)
        cursor = connection.cursor()

        try:
            # Get all table names
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()

            # Dictionary to hold data from all tables
            all_data = {}

            for table_name in tables:
                table_name = table_name[0]
                cursor.execute(f"SELECT * FROM {table_name}")

                # Fetch rows as dictionaries
                rows = cursor.fetchall()
                columns = [description[0] for description in cursor.description]
                all_data[table_name] = [dict(zip(columns, row)) for row in rows]

            if not return_dict:
                # Convert all data to JSON string
                json_data = json.dumps(all_data, indent=4)
                return json_data
            else:
                return all_data
        finally:
            # Close the cursor and connection
            cursor.close()
            connection.close()

    @classmethod
    def merge_dicts(cls, original, new):
        """ Recursively merge two dictionaries. """
        for key, value in new.items():
            if isinstance(value, dict) and value.get(key):
                cls.merge_dicts(original.get(key, {}), value)
            else:
                original[key] = value
        return original

    @classmethod
    def modify_json_file(cls, original_loc, new_data):
        """ Modify a JSON file with new data. """
        with open(original_loc, 'r+') as file:
            existing_data = json.load(file)
            updated_data = cls.merge_dicts(existing_data, new_data)
            file.seek(0)
            file.write(json.dumps(updated_data, indent=4))
            file.truncate()

    @staticmethod
    def modify_sqlite_db(db_path, updates):
        """
        Modify an SQLite database to update or insert settings.
        :param db_path: Path to the SQLite database file.
        :param updates: A dictionary containing key-value pairs to update or insert.
        """
        # Connect to the SQLite database
        connection = sqlite3.connect(db_path)
        cursor = connection.cursor()

        # Ensuring the table exists
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        """)

        # Prepare the SQL for updating or inserting settings
        for key, value in updates.items():
            cursor.execute("""
            INSERT INTO settings(key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value;
            """, (key, value))

        # Commit the changes and close the connection
        connection.commit()
        cursor.close()
        connection.close()

    def export_settings(self, sett):
        # sett = self.settings.get_advanced_settings()
        loc = sett.get("settings_file_path")
        mode = sett.get("settings_file_mode")

        if not os.path.isfile(loc) and os.path.exists(loc):
            return

        is_db_file = loc.endswith(".db")
        is_json_file = loc.endswith((".json", ".yaml", ".yml"))

        if mode == "overwrite":
            if os.path.exists(loc):
                os.remove(loc)
            if is_db_file:
                shutil.copyfile(f"{self.data_folder}/data.db", loc)
            elif is_json_file:
                with open(loc, "w") as f:
                    f.write(self.fetch_all_data_as_json(f"{self.data_folder}/data.db"))
        elif mode == "modify":
            if is_db_file:
                self.modify_sqlite_db(loc, self.fetch_all_data_as_json(f"{self.data_folder}/data.db", return_dict=True))
            elif is_json_file:
                new_data = self.fetch_all_data_as_json(f"{self.data_folder}/data.db", return_dict=True)
                self.modify_json_file(loc, new_data)
        else:
            if not os.path.exists(loc):
                if is_db_file:
                    shutil.copyfile(f"{self.data_folder}/data.db", loc)
                elif is_json_file:
                    with open(loc, "w") as f:
                        f.write(self.fetch_all_data_as_json(f"{self.data_folder}/data.db"))

    def switch_provider(self, name: str):
        provider_name = f"AutoProviderPlugin{name}"
        if provider_name not in self.provider_dict:
            provider_name = f"AutoProviderPlugin{self.settings.get_default_setting('provider')}"
        provider_cls = self.provider_dict[provider_name]

<<<<<<<< Updated upstream:nmv.py
        self.provider = provider_cls(self.settings.get_title(), self.settings.get_chapter(),
                                     self.settings.get_chapter_rate(), self.data_folder, self.cache_folder,
                                     self.settings.get_provider_type(), num_workers=self.settings.get_advanced_settings()["misc"]["num_workers"])
        self.provider.set_blacklisted_websites(self.settings.get_blacklisted_websites())
========
        if self.settings.get_current_lib_idx() != -1:
            current_library = self.settings.get_libraries()[self.settings.get_current_lib_idx()][1]
        else:
            current_library = ""
        self.provider = provider_cls(self.settings.get_title(), self.settings.get_chapter(), current_library, self.cache_folder, self.data_folder)
        # self.provider.set_blacklisted_websites(self.settings.get_blacklisted_websites())
>>>>>>>> Stashed changes:src/main.py

        if self.provider.get_search_results(None):
            self.search_widget.set_search_results_func(self.provider.get_search_results)
            self.search_widget.setEnabled(True)  # self.search_toggle_button.setEnabled(False)
        else:
            self.search_widget.setEnabled(False)  # self.search_toggle_button.setEnabled(False)

        new_pixmap = QPixmap(os.path.abspath(self.provider.get_logo_path()))
        self.transparent_image.setPixmap(new_pixmap)
        self.update_provider_logo()
        if self.provider.saver is not None:
            self.transfer_chapter_s_button.setEnabled(False)
            self.saver_combobox.setCurrentText(name)
            for i in range(0, self.saver_combobox.count()):
                item = self.saver_combobox.model().item(i)
                if i == self.saver_combobox.currentIndex():
                    item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEnabled)
                    continue
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
        else:
            self.transfer_chapter_s_button.setEnabled(True)
            for i in range(0, self.saver_combobox.count()):
                item = self.saver_combobox.model().item(i)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEnabled)
        # self.library_layout_frame.setEnabled(self.provider.needs_library_path)

    def reload_window_title(self):
        new_title = ' '.join(word[0].upper() + word[1:] if word else '' for word in self.provider.get_title().split())
        self.setWindowTitle(f'MV 166 | {new_title}, Chapter {self.provider.get_chapter()}')

    def get_content_paths(self, allowed_file_formats: tuple = None):
        if allowed_file_formats is None:
            allowed_file_formats = ('.png', ".jpg", ".jpeg", ".webp", ".http", '.mp4', '.txt')
        content_files = sorted([f for f in os.listdir(self.cache_folder) if
                                f.endswith(allowed_file_formats)])
        content_paths = [os.path.join(self.cache_folder, f) for f in content_files]
        return content_paths

    # Helper Functions
    def reload_hide_titlebar_setting(self):
        if self.hide_title_bar_checkbox.isChecked():
            self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint)
        else:
            self.setWindowFlags(
                self.windowFlags() & ~Qt.FramelessWindowHint | Qt.WindowSystemMenuHint | Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint)
        self.settings.set_hide_titlebar(self.hide_title_bar_checkbox.isChecked())
        self.show()

    def deepen_color(self, color, darken_factor=100, saturation_factor=1.3):
        # Increase saturation and darken the color
        # Convert to HSL for control over lightness and saturation
        color = color.toHsl()

        deepened_color = color.darker(darken_factor)  # 100 is original, higher values are darker

        # Optionally adjust saturation using HSV
        deepened_color = deepened_color.toHsv()
        deepened_color.setHsv(deepened_color.hue(),
                              min(255, int(deepened_color.saturation() * saturation_factor)),
                              deepened_color.value())

        return deepened_color

    def reload_hover_effect_all_setting(self, callback: bool = False):
        style_sheet = """\nQPushButton:hover,\nQListWidget:hover,\nQSpinBox:hover,\nQLabel:hover,
        QComboBox:hover,\nQLineEdit:hover,\nQCheckBox:hover,\nQScrollBar:hover"""
        if self.hover_effect_all_checkbox.isChecked():
            bg_color = self.deepen_color(self.menu_button.palette().color(self.menu_button.backgroundRole()), darken_factor=120)
            if self.acrylic_menus_checkbox.isChecked():
                bg_color.setAlpha(30)
            defbg_color = self.menu_button.palette().color(self.menu_button.backgroundRole())
            defbg_color.setAlpha(30)
            if self.theme == "light":
                style_sheet_non_transparent = style_sheet + f" {{background-color: {bg_color.name(QColor.HexArgb)};}}"
                style_sheet += f" {{background-color: {defbg_color.name(QColor.HexArgb)};}}"
            else:
                style_sheet_non_transparent = style_sheet + f" {{background-color: {bg_color.name(QColor.HexArgb)};}}"
                style_sheet += f" {{background-color: {defbg_color.name(QColor.HexArgb)};}}"
            self.menu_button.setStyleSheet(self.menu_button.styleSheet() + style_sheet_non_transparent)
            self.side_menu.setStyleSheet(self.side_menu.styleSheet() + style_sheet)
            self.search_bar_toggle_button.setStyleSheet(self.search_bar_toggle_button.styleSheet() + style_sheet_non_transparent)
            # self.search_widget.setStyleSheet(self.search_widget.styleSheet() + style_sheet_non_transparent)
            # self.search_widget.search_bar.setStyleSheet(self.search_widget.styleSheet() + style_sheet_non_transparent)
            self.buttons_widget.setStyleSheet(self.buttons_widget.styleSheet() + style_sheet_non_transparent)
        else:
            self.menu_button.setStyleSheet("")
            self.side_menu.setStyleSheet("")
            self.search_bar_toggle_button.setStyleSheet("")
            # self.search_widget.setStyleSheet("")
            # self.search_widget.search_bar.setStyleSheet("")
            self.buttons_widget.setStyleSheet("")
            # if self.theme == "light":
            #     style_sheet += " {background-color: rgba(85, 85, 85, 30%);}"
            # else:
            #     style_sheet += " {background-color: rgba(192, 192, 192, 30%);}"
            # for widget in [self.centralWidget(), self.side_menu, self.search_bar_toggle_button, self.search_widget,
            #                self.buttons_widget]:
            #     original_style_sheet = widget.styleSheet().removesuffix(style_sheet)
            #     widget.setStyleSheet(original_style_sheet)
        if not callback:
            self.reload_acrylic_menus_setting(callback=True)
        self.settings.set_hover_effect_all(self.hover_effect_all_checkbox.isChecked())

    def reload_borderless_setting(self):
        if self.borderless_checkbox.isChecked():
            # Set the central layout margins and spacing to 0
            self.window_layout.setContentsMargins(0, 0, 0, 0)
            self.window_layout.setSpacing(0)
        else:
            # Set the central layout margins and spacing to 0
            self.window_layout.setContentsMargins(9, 9, 9, 9)
            self.window_layout.setSpacing(6)
        self.settings.set_borderless(self.borderless_checkbox.isChecked())

    def reload_acrylic_menus_setting(self, callback: bool = False):
        if self.acrylic_menus_checkbox.isChecked():
            style_sheet = "\nQPushButton:hover,\nQComboBox:hover"
            bg_color = self.menu_button.palette().color(self.menu_button.backgroundRole())
            bg_color.setAlpha(30)
            deep_bg_color = self.deepen_color(bg_color)
            if self.theme == "light":
                style_sheet = (f"* {{background-color: {bg_color.name(QColor.HexArgb)};}}"
                               + style_sheet + f" {{background-color: {deep_bg_color.name(QColor.HexArgb)};}}")
            else:
                style_sheet = (f"* {{background-color: rgba( 0, 0, 0, 30% );}}"
                               + style_sheet + f" {{background-color: {deep_bg_color.name(QColor.HexArgb)};}}")
            self.centralWidget().setStyleSheet(style_sheet)
            self.side_menu.setStyleSheet(style_sheet)
            self.search_bar_toggle_button.setStyleSheet(style_sheet)
            self.search_widget.setStyleSheet(style_sheet)
            self.search_widget.search_bar.setStyleSheet(style_sheet)
            self.buttons_widget.setStyleSheet(style_sheet)
        else:
            self.centralWidget().setStyleSheet("")
            self.side_menu.setStyleSheet("")
            self.search_bar_toggle_button.setStyleSheet("")
            self.search_widget.setStyleSheet("")
            self.search_widget.search_bar.setStyleSheet("")
            self.buttons_widget.setStyleSheet("")
        if not callback:
            self.reload_hover_effect_all_setting(callback=True)
        self.settings.set_acrylic_menus(self.acrylic_menus_checkbox.isChecked())

    def reload_acrylic_background_setting(self):
        if self.acrylic_background_checkbox.isChecked():
            self.setWindowOpacity(0.8)
        else:
            self.setWindowOpacity(1.0)
        self.settings.set_acrylic_background(self.acrylic_background_checkbox.isChecked())

    def reload_hide_scrollbar_setting(self):
        if self.hide_scrollbar_checkbox.isChecked():
            self.scrollarea.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self.scrollarea.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        else:
            self.scrollarea.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            self.scrollarea.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.settings.set_hide_scrollbar(self.hide_scrollbar_checkbox.isChecked())

    def reload_stay_on_top_setting(self):
        if self.stay_on_top_checkbox.isChecked():
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(
                self.windowFlags() & ~Qt.WindowStaysOnTopHint | Qt.WindowSystemMenuHint | Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint)
        self.settings.set_stay_on_top(self.stay_on_top_checkbox.isChecked())
        self.show()

    def downscale_checkbox_toggled(self):
        self.settings.set_downscaling(self.downscale_checkbox.isChecked())
        self.downscaling = self.downscale_checkbox.isChecked()
        self.force_rescale = True

    def upscale_checkbox_toggled(self):
        self.settings.set_upscaling(self.upscale_checkbox.isChecked())
        self.upscaling = self.upscale_checkbox.isChecked()
        self.force_rescale = True

    def apply_manual_content_width(self):
        self.settings.set_manual_content_width(self.manual_width_spinbox.value())
        self.force_rescale = True

    def set_show_provider_logo(self) -> None:
        self.settings.set_show_provider_logo(self.show_provider_logo_checkbox.isChecked())
        self.update_provider_logo()

    def set_title(self):
        new_title = self.title_selector.text().strip()
        self.settings.set_title(new_title)
        self.provider.set_title(new_title)

    def set_chapter(self):
        new_chapter = float("0" + self.chapter_selector.text())
        if 0.0 <= new_chapter < 1000.0:
            self.provider.set_chapter(new_chapter)
        else:
            self.provider.set_chapter(0)
            self.gui_changing = True
            self.chapter_selector.setText("0")
            self.gui_changing = False

    def set_library_name(self, library: tuple[str, str]) -> None:
        new_name, ok = QInputDialog.getText(self, "Set Library Name", "Enter new name:", text=library[0])
        if ok and new_name:
            self.library_edit.set_lib_name(library[1], new_name)

    def set_chapter_rate(self):
        new_chapter_rate = float("0" + self.chapter_rate_selector.text())
        if 0.1 <= new_chapter_rate <= 2.0:
            self.settings.set_chapter_rate(new_chapter_rate)
<<<<<<<< Updated upstream:nmv.py
            self.provider.set_chapter_rate(new_chapter_rate)
========
            # self.provider.set_chapter_rate(new_chapter_rate)
            self.gui_changing = True
>>>>>>>> Stashed changes:src/main.py
            self.chapter_rate_selector.setText(str(new_chapter_rate))
            self.gui_changing = False
        else:
            self.settings.set_chapter_rate(0.1)
<<<<<<<< Updated upstream:nmv.py
            self.provider.set_chapter_rate(0.1)
========
            # self.provider.set_chapter_rate(0.1)
            self.gui_changing = True
>>>>>>>> Stashed changes:src/main.py
            self.chapter_rate_selector.setText("0.1")
            self.gui_changing = False

    def update_sensitivity(self, value):
        sensitivity = value / 10
        self.settings.set_scrolling_sensitivity(sensitivity)
        self.sensitivity_label.setText(f"Current Sensitivity: {sensitivity:.1f}")
        self.scrollarea.sensitivity = sensitivity

    def selected_chosen_result(self, new_title, toggle_search_bar: bool = True):
        self.title_selector.setText(new_title)
        self.title_selector.textChanged.emit(new_title)
        self.chapter_selector.setText("1")
        self.chapter_selector.textChanged.emit("1")
        self.settings.set_chapter(1)
        self.reload_chapter()
        if toggle_search_bar:
            self.toggle_search_bar()
        # self.save_last_title(self.provider.get_title())

    def selected_chosen_item(self, new_item, toggle_search_bar: bool = True):
        provider, title, chapter, *_ = new_item.split("\x00") + ["", ""]
        if not _:
            provider, title, chapter = title, provider, 0.0
        else:
            chapter = float(chapter)

        self.title_selector.setText(title)
        self.title_selector.textChanged.emit(title)
        self.chapter_selector.setText(str(chapter))
        self.chapter_selector.textChanged.emit(str(chapter))
        self.settings.set_chapter(chapter)
        if provider != "":
            # self.switch_provider(provider)
            self.provider_combobox.setCurrentText(provider)
        self.reload_chapter()
        if toggle_search_bar:
            self.toggle_search_bar()
        # self.save_last_title(self.provider.get_title())

    def save_last_title(self, last_provider: str, last_title: str, last_chapter: str) -> None:
        if self.settings.get_save_last_titles():
            sett = self.settings.get_advanced_settings()
            last_title = last_title.lower()
            last_chapter = str(last_chapter)
            new_titles = []

            for recent_title in sett["recent_titles"]:
                provider, title, chapter, *_ = recent_title.split("\x00") + ["", ""]
                if title.lower() == last_title and (provider == last_provider or chapter == last_chapter):
                    continue
                elif not _:
                    new_titles.append(f"{title}\x00{provider}\x00{0}")  # As the title is the first split
                    continue
                new_titles.append(f"{provider}\x00{title}\x00{chapter}")
            new_titles.append(f"{last_provider}\x00{last_title}\x00{last_chapter}")
            sett["recent_titles"] = new_titles
            self.settings.set_advanced_settings(sett)

<<<<<<<< Updated upstream:nmv.py
    def change_provider_type(self):
        self.settings.set_provider_type(self.provider_type_combobox.currentText().lower())
        self.provider.set_provider_type(self.settings.get_provider_type())

    def blacklist_current_url(self):
        blk_urls = self.provider.get_blacklisted_websites() + [urlparse(self.provider.get_current_url()).netloc]
        self.provider.set_blacklisted_websites(blk_urls)
        self.settings.set_blacklisted_websites(self.provider.get_blacklisted_websites())

========
>>>>>>>> Stashed changes:src/main.py
    def change_provider(self, *args, callback: bool = False):
        if not callback:
            self.previous_provider = self.provider
        self.switch_provider(self.provider_combobox.currentText())
        if not callback:
            QTimer.singleShot(50, self.change_provider_callback)

<<<<<<<< Updated upstream:nmv.py
========
    def change_saver(self, *args):
        self.saver = self.savers_dict[self.saver_combobox.currentText()]
        self.settings.set_library_manager(self.saver_combobox.currentText())
        if not self.saver.is_compatible(self.library_edit.current_library()[1]):
            if self.settings.get_current_lib_idx() != self.library_edit.currentIndex():
                self.library_edit.setCurrentIndex(self.settings.get_current_lib_idx())
            else:
                self.library_edit.setCurrentIndex(-1)

    def change_library(self, *args) -> None:
        new_library_path: str = self.library_edit.current_library()[1]
        if self.saver.is_compatible(new_library_path):
            self.saver.create_library(*self.library_edit.current_library()[::-1])
        else:
            if self.settings.get_current_lib_idx() != self.library_edit.currentIndex():
                self.library_edit.setCurrentIndex(self.settings.get_current_lib_idx())
            else:
                self.library_edit.setCurrentIndex(-1)
            new_library_path = self.library_edit.current_library()[1]
        self.settings.set_current_lib_idx(self.library_edit.currentIndex())
        self.provider.set_library_path(new_library_path)
        if hasattr(self, "previous_provider"):
            self.previous_provider.set_library_path(new_library_path)

    def advance_cache(self) -> bool:
        """Advances the cache by rotating the folders. Returns True if cache was already loaded, else False."""
        try:
            if os.path.exists(self.last_cache_folder):  # Delete last_cache
                shutil.rmtree(self.last_cache_folder)
            if os.path.exists(self.cache_folder):  # Move cache -> last_cache
                os.rename(self.cache_folder, self.last_cache_folder)
            if os.path.exists(self.next_cache_folder):  # Move next_cache -> cache
                os.rename(self.next_cache_folder, self.cache_folder)

            # Check if cache is already loaded (not empty)
            files = os.listdir(self.cache_folder) if os.path.exists(self.cache_folder) else []
            cache_was_loaded = len(files) > 0
            os.makedirs(self.next_cache_folder, exist_ok=True)  # Create a new next_cache folder
        except PermissionError:
            self.reset_caches()
            return False
        return cache_was_loaded

    def retract_cache(self) -> bool:
        """Retracts the cache by rotating the folders in the opposite direction. Returns True if cache was already loaded, else False."""
        try:
            if os.path.exists(self.next_cache_folder):  # Delete next_cache
                shutil.rmtree(self.next_cache_folder)
            if os.path.exists(self.cache_folder):  # Move cache -> next_cache
                os.rename(self.cache_folder, self.next_cache_folder)
            if os.path.exists(self.last_cache_folder):  # Move last_cache -> cache
                os.rename(self.last_cache_folder, self.cache_folder)

            # Check if cache is already loaded (not empty)
            files = os.listdir(self.cache_folder) if os.path.exists(self.cache_folder) else []
            cache_was_loaded = len(files) > 0
            os.makedirs(self.last_cache_folder, exist_ok=True)  # Create a new last_cache folder
        except PermissionError:
            self.reset_caches()
            return False
        return cache_was_loaded

    def reset_caches(self) -> None:
        """Empties all cache folders without deleting them."""
        self._clear_folder(self.cache_folder)
        self._clear_folder(self.next_cache_folder)
        self._clear_folder(self.last_cache_folder)

    def reset_cache(self) -> None:
        """Empties only the main cache folder."""
        self._clear_folder(self.cache_folder)

    def reset_next_cache(self) -> None:
        """Empties only the next_cache folder."""
        self._clear_folder(self.next_cache_folder)

    def reset_last_cache(self) -> None:
        """Empties only the last_cache folder."""
        self._clear_folder(self.last_cache_folder)

    def _clear_folder(self, folder):
        """Helper function to clear a folder's contents while keeping it intact."""
        if os.path.exists(folder):
            for f in os.listdir(folder):
                file_path = os.path.join(folder, f)
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.remove(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)

>>>>>>>> Stashed changes:src/main.py
    def change_provider_callback(self):
        self.change_provider(callback=True)
        print("PREV", self.previous_provider, "->", self.provider)
        if type(self.provider) is not type(self.previous_provider):
            self.provider.redo_prep()
            self.reload_content()

    # Dynamic movement methods
    def toggle_search_bar(self):
        is_visible = self.search_widget.y() >= 0
        if is_visible:
            end_rect = QRect(0, -self.search_widget.height(), self.search_widget.width(), self.search_widget.height())
        else:
            end_rect = QRect(0, self.search_bar_toggle_button.height() - 20, self.search_widget.width(),
                             self.search_widget.height())
        self.search_bar_animation.setStartValue(self.search_widget.geometry())
        self.search_bar_animation.setEndValue(end_rect)
        self.search_bar_animation.start()

    def search_bar_animation_value_changed(self, value):
        move_value = value.y() + self.search_widget.height()
        self.search_bar_toggle_button.move(0, move_value)
        self.update_menu_button_position(value2=move_value)

    def toggle_side_menu(self):
        width = max(200, int(self.width() / 3))
        height = self.height()

        if self.side_menu.x() >= self.width():
            start_value = QRect(self.width(), 0, width, height)
            end_value = QRect(self.width() - width, 0, width, height)
        else:
            start_value = QRect(self.width() - width, 0, width, height)
            end_value = QRect(self.width(), 0, width, height)

        self.side_menu_animation.setStartValue(start_value)
        self.side_menu_animation.setEndValue(end_value)
        self.side_menu_animation.start()

    def update_menu_button_position(self, value=None, value2=None):
        if not value:
            value = self.side_menu.x()
        else:
            value = value.x()
        if not value2: value2 = self.search_widget.y() + self.search_widget.height()
        self.menu_button.move(value - self.menu_button.width(), (20 + value2 if value2 >= 0 else 20))

    def update_search_geometry(self, value):
        self.search_bar_toggle_button.setFixedWidth(value.x())  # Adjust the width of the toggle button
        self.search_widget.setFixedWidth(value.x())  # Adjust the width of the search bar

    def side_menu_animation_value_changed(self, value):
        self.update_menu_button_position(value)
        self.update_search_geometry(value)

    # Window management methods
    def update_font_size(self):
        if self.width() <= 800:
            new_font_size = min(max(6, math.log(self.width() * 4)), 14)
        else:
            new_font_size = min(max(6, self.width() // 80), 14)
        font = QFont()
        font.setPointSize(new_font_size)
        self.setFont(font)
        # print(self.side_menu.children())
        for widget in self.side_menu.children():
            if hasattr(widget, "setFont"):
                widget.setFont(font)
                # print(type(widget).__name__) # Debug

    def update_provider_logo(self):
        # Adjust the size of the transparent image based on window width
        if not self.settings.get_show_provider_logo():
            self.transparent_image.setVisible(False)
        else:
            self.transparent_image.setVisible(True)
        pixmap = self.transparent_image.pixmap()
        if not pixmap:
            return
        if pixmap.width() > pixmap.height():
            smaller_size = "height"
            size_to_scale_to = pixmap.width()
        else:
            smaller_size = "width"
            size_to_scale_to = pixmap.height()
        wanted_size = self.width() // 5
        if size_to_scale_to != wanted_size:  # If the current image width is outside the min and max size range, resize it
            if smaller_size == "width":
                scaled_pixmap = QPixmap(os.path.abspath(self.provider.get_logo_path())).scaledToWidth(wanted_size, Qt.TransformationMode.SmoothTransformation)
            else:
                scaled_pixmap = QPixmap(os.path.abspath(self.provider.get_logo_path())).scaledToHeight(wanted_size,
                                                                                                      Qt.TransformationMode.SmoothTransformation)
            self.transparent_image.setFixedSize(scaled_pixmap.width() + 20, scaled_pixmap.height() + 20)
            self.transparent_image.setPixmap(scaled_pixmap)

    # Rest
    def reload_providers(self):
<<<<<<<< Updated upstream:nmv.py
        provider_manager = AutoProviderManager(self.extensions_folder, AutoProviderPlugin, [
                        AutoProviderPlugin, AutoProviderBaseLike, AutoProviderBaseLike2])
========
        provider_manager = AutoProviderManager(self.extensions_folder, CoreProvider, [])
>>>>>>>> Stashed changes:src/main.py
        self.provider_dict = provider_manager.get_providers()
        self.savers_dict = {}

        self.provider_combobox.clear()
<<<<<<<< Updated upstream:nmv.py

        for i, provider_name in enumerate(self.provider_dict.keys()):
            provider = self.provider_dict[provider_name]("", 1, 0.5, self.data_folder, self.cache_folder, "direct")

            icon_path = provider.get_logo_path()
            image = QImage(os.path.abspath(icon_path))
========
        self.saver_combobox.clear()
        last_working_provider = None
        saved_provider_working = False
        saved_provider = self.settings.get_provider()
        saved_saver = self.settings.get_library_manager()

        i = 0
        i2 = 0
        for provider_cls_name in self.provider_dict.keys():
            provider = self.provider_dict[provider_cls_name]("", 0, "", self.cache_folder, self.data_folder)

            if not provider.can_work():
                continue

            logo_path = provider.get_logo_path()
            icon_path = provider.get_icon_path()
            image = QImage(os.path.abspath(logo_path))
            image_width, image_height = image.width(), image.height()
>>>>>>>> Stashed changes:src/main.py

            if provider.clipping_space is not None:
                start_x, start_y, end_x, end_y = provider.clipping_space

<<<<<<<< Updated upstream:nmv.py
                print("Cropping", image.height(), "x", image.width(), "for", provider_name)
                cropped_image = image.copy(start_y if start_y != "max" else image.width(),
                                           start_x if start_x != "max" else image.height(),
                                           end_y if end_y != "max" else image.width(),
                                           end_x if end_x != "max" else image.height())
            else:
                print("Cube cropping", image.height(), "for", provider_name)
                cropped_image = image.copy(0, 0, image.height(), image.height())
            icon = QIcon(QPixmap.fromImage(cropped_image))

            # Add item to the dropdown
            self.provider_combobox.addItem(icon, provider_name.replace("AutoProviderPlugin", ""))
            if "AutoProviderPlugin" not in provider_name:
                self.provider_combobox.setItemUnselectable(i)
        self.provider_combobox.setCurrentText(self.settings.get_provider())
========
                def _resolve(value: int) -> int:
                    if value == -1:
                        return image_height
                    elif value == -2:
                        return image_width
                    return value

                start_x = _resolve(start_x)
                start_y = _resolve(start_y)
                end_x = _resolve(end_x)
                end_y = _resolve(end_y)

                print(f"Cropping {image_height} x {image_width} for {provider_cls_name}")
                cropped_image = image.copy(start_y, start_x, end_y, end_x)
            else:
                cropped_image = QImage(os.path.abspath(icon_path))

            icon = QIcon(QPixmap.fromImage(cropped_image))

            # Add item to the dropdown
            provider_name = provider_cls_name.removesuffix("Provider")
            self.provider_combobox.addItem(icon, provider_name)

            if provider.saver is not None:
                self.savers_dict[provider_name] = provider.saver
                self.saver_combobox.addItem(icon, provider_name)
                i2 += 1

            if not provider.is_working():
                item = self.provider_combobox.model().item(i)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
                if provider.saver is not None:
                    item2 = self.saver_combobox.model().item(i2-1)
                    item2.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
            else:
                if provider_name == saved_provider:
                    saved_provider_working = True
                last_working_provider = provider_name  # Track last working provider
            i += 1
        if saved_provider_working:
            print(f"Saved provider ({saved_provider}) working")
            self.provider_combobox.setCurrentText(saved_provider)
        elif last_working_provider is not None:
            print(f"Other working provider ({last_working_provider})")
            self.provider_combobox.setCurrentText(last_working_provider)  # Fallback to last working provider
        else:
            print("No working provider")
            self.provider_combobox.setCurrentIndex(-1)  # No selection if no working provider found
        self.saver_combobox.setCurrentText(saved_saver)
        self.reload_searchers()

    def reload_searchers(self) -> None:
        for provider_cls_name, provider_cls in self.provider_dict.items():
            provider_name = provider_cls_name.removesuffix("Provider")
            provider = provider_cls("", 0, "", self.cache_folder, self.data_folder)
            if not provider.get_search_results(None) or not provider.can_work() or not provider.is_working():
                continue
            try:
                # provider.get_search_results("")
                if isinstance(provider, OfflineProvider):
                    raise Exception
            except Exception:
                continue
            self.known_working_searchers.append((provider_name, provider_cls))
>>>>>>>> Stashed changes:src/main.py

    def save_settings(self):
        if hasattr(self, "settings") and self.settings.is_open:
            self.settings.set_provider(self.provider_combobox.currentText())
            self.settings.set_title(self.provider.get_title())
            self.settings.set_chapter(self.provider.get_chapter())
            self.settings.set_chapter_rate(self.provider.get_chapter_rate())
            self.settings.set_provider_type(self.provider.get_provider_type())

            self.settings.set_blacklisted_websites(self.provider.get_blacklisted_websites())

            self.settings.set_hover_effect_all(self.hover_effect_all_checkbox.isChecked())
            self.settings.set_borderless(self.borderless_checkbox.isChecked())
            self.settings.set_acrylic_menus(self.acrylic_menus_checkbox.isChecked())
            self.settings.set_acrylic_background(self.acrylic_background_checkbox.isChecked())

            self.settings.set_downscaling(self.downscale_checkbox.isChecked())
            self.settings.set_upscaling(self.upscale_checkbox.isChecked())
            self.settings.set_lazy_loading(self.lazy_loading_checkbox.isChecked())
            self.settings.set_manual_content_width(self.manual_width_spinbox.value())

            self.settings.set_hide_titlebar(self.hide_title_bar_checkbox.isChecked())
            self.settings.set_hide_scrollbar(self.hide_scrollbar_checkbox.isChecked())
            self.settings.set_stay_on_top(self.stay_on_top_checkbox.isChecked())

            self.settings.set_save_last_titles(self.save_last_titles_checkbox.isChecked())
            # self.settings.set_advanced_settings([])

            self.settings.set_geometry([self.x(), self.y(), self.width(), self.height()])
            self.settings.set_last_scroll_positions(
                [self.scrollarea.verticalScrollBar().value(), self.scrollarea.horizontalScrollBar().value()]
            )
            self.settings.set_scrolling_sensitivity(self.scroll_sensitivity_scroll_bar.value() / 10)

    def reload_gui(self, reload_geometry: bool = False, reload_position: bool = False):
<<<<<<<< Updated upstream:nmv.py
        self.provider_combobox.setCurrentText(self.settings.get_provider())
========
        # self.provider_combobox.setCurrentText(self.settings.get_provider())
        self.show_provider_logo_checkbox.setChecked(self.settings.get_show_provider_logo())
>>>>>>>> Stashed changes:src/main.py
        self.title_selector.setText(self.settings.get_title())
        self.gui_changing = True
        self.chapter_selector.setText(str(self.settings.get_chapter()))
        self.chapter_rate_selector.setText(str(self.settings.get_chapter_rate()))
<<<<<<<< Updated upstream:nmv.py
        self.provider_type_combobox.setCurrentText(self.settings.get_provider_type().title())
========
        self.gui_changing = False
        # self.provider_type_combobox.setCurrentText(self.settings.get_provider_type().title())
        lib_idx = self.settings.get_current_lib_idx()
        self.library_edit.clear()
        for (name, path) in self.settings.get_libraries():
            self.library_edit.add_library_item(name, path)
        self.library_edit.setCurrentIndex(lib_idx)
>>>>>>>> Stashed changes:src/main.py

        self.provider.set_blacklisted_websites(self.settings.get_blacklisted_websites())

        self.hover_effect_all_checkbox.setChecked(self.settings.get_hover_effect_all())
        self.borderless_checkbox.setChecked(self.settings.get_borderless())
        self.acrylic_menus_checkbox.setChecked(self.settings.get_acrylic_menus())
        self.acrylic_background_checkbox.setChecked(self.settings.get_acrylic_background())

        self.downscale_checkbox.setChecked(self.settings.get_downscaling())
        self.upscale_checkbox.setChecked(self.settings.get_upscaling())
        self.lazy_loading_checkbox.setChecked(self.settings.get_lazy_loading())
        self.manual_width_spinbox.setValue(self.settings.get_manual_content_width())

        self.hide_title_bar_checkbox.setChecked(self.settings.get_hide_titlebar())
        self.hide_scrollbar_checkbox.setChecked(self.settings.get_hide_scrollbar())
        self.stay_on_top_checkbox.setChecked(self.settings.get_stay_on_top())

        self.save_last_titles_checkbox.setChecked(self.settings.get_save_last_titles())
        self.settings.get_advanced_settings()

        self.setGeometry(*(self.geometry().getRect()[:2] if not reload_position else (100, 100)),
                         *(self.settings.get_geometry()[2:] if not reload_geometry else (800, 630)))
        self.settings.set_geometry(self.geometry().getRect()[:])
        vertical_scrollbar_position, horizontal_scrollbar_position = self.settings.get_last_scroll_positions()
        self.scrollarea.verticalScrollBar().setValue(vertical_scrollbar_position)
        self.scrollarea.horizontalScrollBar().setValue(horizontal_scrollbar_position)
        self.scroll_sensitivity_scroll_bar.setValue(self.settings.get_scrolling_sensitivity() * 10)
        self.save_last_titles_checkbox.setChecked(self.settings.get_save_last_titles())

    def reload(self):
        current_ts = time.time()
        self.save_settings()
        self.reload_window_title()
        self.provider_combobox.currentIndexChanged.disconnect()
        self.reload_providers()
        self.switch_provider(self.settings.get_provider())
        self.provider_combobox.currentIndexChanged.connect(self.change_provider)
        self.reload_gui(reload_geometry=True, reload_position=True if (current_ts - self.last_reload_ts) < 1 else False)

        self.reload_hover_effect_all_setting()
        self.reload_borderless_setting()
        self.reload_acrylic_menus_setting()
        self.reload_acrylic_background_setting()

        self.force_rescale = True

        self.reload_hide_titlebar_setting()
        self.reload_hide_scrollbar_setting()
        self.reload_stay_on_top_setting()

        self.update_sensitivity(int(self.settings.get_scrolling_sensitivity() * 10))

        self.content_paths = self.get_content_paths()
        self.reload_content()
        self.last_reload_ts = time.time()
        self.downscaling = self.downscale_checkbox.isChecked()
        self.upscaling = self.upscale_checkbox.isChecked()

    # Content management methods
    def get_wanted_width(self):
        scroll_area_width = self.scrollarea.viewport().width() + self.scrollarea.verticalScrollBar().width()
        # if len(self.content_widgets) > 0:
        #     content_width = next(iter(self.content_widgets)).pixmap().width()
        # else:
        #     content_width = 1
        standard_image_width = self.manual_width_spinbox.value()  # or content_width

        conditions = [
            scroll_area_width != self.previous_scrollarea_width,
            self.force_rescale
        ]
        if any(conditions):
            new_image_width = standard_image_width
            self.rescale_coefficient = abs(self.previous_scrollarea_width / self.scrollarea.viewport().width())
            self.previous_scrollarea_width = self.scrollarea.viewport().width()
            if self.downscaling and standard_image_width > scroll_area_width:
                new_image_width = scroll_area_width
            elif self.upscaling and standard_image_width < scroll_area_width:
                new_image_width = scroll_area_width
            self.force_rescale = False
            return new_image_width
        return None

    def update_content(self):
        wanted_image_width = self.get_wanted_width()
        if wanted_image_width is None:
            return

        for widget, path in zip(self.content_widgets, self.content_paths):
            if isinstance(widget, QLabel):
                pixmap = widget.pixmap()
                if pixmap:
                    if wanted_image_width != pixmap.width():
                        pixmap.load(path)
                        widget.setPixmap(pixmap.scaledToWidth(wanted_image_width,
                                                              Qt.TransformationMode.SmoothTransformation))
                else:
                    font = widget.font()
                    # Apply transformations here
                    widget.setFont(font)
            elif isinstance(widget, QVideoWidget) or isinstance(widget, QWebEngineView):
                widget.setFixedWidth(wanted_image_width)

        height = 0
        for widget in [self.scrollarea.content_widget.layout().itemAt(i).widget() for i in range(self.scrollarea.content_widget.layout().count())]:
            if hasattr(widget, "pixmap") and widget.pixmap():
                height += widget.pixmap().height()
            else:
                height += widget.sizeHint().height()

        rescale_size = self.scrollarea.recorded_default_size
        rescale_size.setHeight(height)
        self.scrollarea.content_widget.resize(rescale_size)
        self.scrollarea.reload_scrollbars()

    def reload_content(self):
        self.content_paths = self.get_content_paths()
        content_widgets_length = len(self.content_widgets) - 1
        i = 0

        for i, content_path in enumerate(self.content_paths):
            if content_path.endswith((".png", ".jpg", ".jpeg", ".webp")):
                if i > content_widgets_length:
                    image_label = ImageLabel()
                    self.content_widgets.append(image_label)
                    pixmap = QPixmap(content_path)
                else:
                    image_label = self.content_widgets[i]
                    pixmap = image_label.pixmap()
                    pixmap.load(content_path)
                image_label.setPixmap(pixmap)
                image_label.setAlignment(Qt.AlignCenter)
            else:
                raise Exception

            self.content_layout.addWidget(image_label)
            QApplication.processEvents()

        # Clear remaining existing content
        content_widgets_length = len(self.content_widgets) - 1
        for j, widget in enumerate(self.content_widgets.copy()[::-1]):
            j = content_widgets_length - j
            if j > i:
                self.content_widgets.pop(j)
                self.content_layout.removeWidget(widget)
                widget.deleteLater()

        self.content_layout.addWidget(self.buttons_widget)
        self.update_content()

    # Chapter methods
    def threading_wrapper(self, new_thread, blocking, func, args=(), kwargs=None):
        self.threading = True
        progress_dialog = CustomProgressDialog(
            self,
            window_title="Loading ...",
            window_icon=f"{self.data_folder}/Untitled-1-noBackground.png",
            new_thread=new_thread,
            func=func,
            args=args,
            kwargs=kwargs)
        if blocking:
            progress_dialog.exec()
        else:
            progress_dialog.show()

        self.task_successful = progress_dialog.task_successful
        self.threading = False

    def chapter_loading_wrapper(self, func, fail_info, fail_text):
        self.provider.redo_prep()
        self.threading_wrapper(True, True, func)

        if self.task_successful:
            self.reload_window_title()
            self.settings.set_chapter(self.provider.get_chapter())
            self.task_successful = False
        else:
<<<<<<<< Updated upstream:nmv.py
            self.provider.set_chapter(self.settings.get_chapter())
            self.provider.reload_chapter()
========
            # self.provider.set_chapter(self.settings.get_chapter())
            # self.provider.load_current_chapter()
            if not 1:
                new_chapter = self.provider.get_chapter()
                self.gui_changing = True
                self.chapter_selector.setText(str(self.settings.get_chapter()))
                self.gui_changing = False
                self.set_chapter()
                if abs(new_chapter - self.settings.get_chapter()) > 1:
                    self.reload_chapter()
                else:
                    [lambda: None, self.retract_cache, self.advance_cache][int((new_chapter - self.settings.get_chapter()) // self.settings.get_chapter_rate())]()
            else:
                self.reload_window_title()
                self.settings.set_chapter(self.provider.get_chapter())
>>>>>>>> Stashed changes:src/main.py
            QMessageBox.information(self, fail_info, fail_text,
                                    QMessageBox.StandardButton.Ok,
                                    QMessageBox.StandardButton.Ok)
        self.gui_changing = True
        self.chapter_selector.setText(str(self.settings.get_chapter()))
        self.gui_changing = False
        print("Reloading images ...")
        self.scrollarea.verticalScrollBar().setValue(0)
        self.scrollarea.horizontalScrollBar().setValue((self.scrollarea.width() // 2))
        self.reload_content()
<<<<<<<< Updated upstream:nmv.py
        self.force_rescale = True

    def next_chapter(self):
        self.chapter_loading_wrapper(self.provider.next_chapter, "Info | Loading of chapter has failed!",
                                     "The loading of the next chapter has failed.\nLook in the logs for more info.")

    def previous_chapter(self):
        self.chapter_loading_wrapper(self.provider.previous_chapter, "Info | Loading of chapter has failed!",
                                     "The loading of the previous chapter has failed.\nLook in the logs for more info.")

    def reload_chapter(self):
        self.chapter_loading_wrapper(self.provider.reload_chapter, "Info | Reloading of chapter has failed",
                                     "The reloading the current chapter has failed.\nLook in the logs for more info.")
========
        self.save_last_title(self.provider.__class__.__name__.removesuffix("Provider"), self.provider.get_title(), self.settings.get_chapter())
        if self.settings.get_advanced_settings().get("misc", {}).get("auto_export", False):
            if self.library_edit.current_library()[1] == "":
                QMessageBox.warning(self, "No library selected", "Please select a library to enable \nthe transfer of chapters.")
                return
            elif self.provider.saver is not None:
                return  # So we don't save the same chapter over and over, destroying it's quality
            elif self.transferring:
                return
            chapter = self.settings.get_chapter()

            args = (
                self.provider,
                chapter,
                f"Chapter {chapter}",
                self.cache_folder,
                self.settings.get_advanced_settings()["misc"]["quality_preset"]
            )
            kwargs = {}
            progress_dialog = CustomProgressDialog(
                parent=self,
                window_title="Transferring ...",
                window_icon="",
                window_label="Doing a task...",
                button_text="Cancel",
                new_thread=True,
                func=self.saver.save_chapter,
                args=args,
                kwargs=kwargs)
            progress_dialog.show()
            print("Transfer Task: ", progress_dialog.task_successful)
            if not progress_dialog.task_successful:
                QMessageBox.information(self, "Info | Transferring of the chapter has failed!", "Look in the logs for more info.",
                                        QMessageBox.StandardButton.Ok,
                                        QMessageBox.StandardButton.Ok)

    def next_chapter(self) -> None:
        self.provider.increase_chapter(self.settings.get_chapter_rate())
        is_already_loaded: bool = self.advance_cache()
        if not is_already_loaded:
            self.chapter_loading_wrapper(self.provider.load_current_chapter, "Info | Loading of the chapter has failed!",
                                         "Maybe this chapter doesn't exist?\nIf that isn't the case, look in the logs for more info.")
        else:
            self.reload_window_title()
            self.settings.set_chapter(self.provider.get_chapter())
            self.task_successful = False
            self.gui_changing = True
            self.chapter_selector.setText(str(self.settings.get_chapter()))
            self.gui_changing = False
            self.save_last_title(self.provider.__class__.__name__.removesuffix("Provider"), self.provider.get_title(), self.settings.get_chapter())
            print("Reloading images ...")
            self.scrollarea.verticalScrollBar().setValue(0)
            self.scrollarea.horizontalScrollBar().setValue((self.scrollarea.width() // 2))
            self.reload_content()

    def previous_chapter(self) -> None:
        if self.provider.get_chapter() - self.settings.get_chapter_rate() < 0:
            return
        self.provider.increase_chapter(-self.settings.get_chapter_rate())
        is_already_loaded: bool = self.retract_cache()
        if not is_already_loaded:
            self.chapter_loading_wrapper(self.provider.load_current_chapter, "Info | Loading of the chapter has failed!",
                                         "Maybe this chapter doesn't exist?\nIf that isn't the case, look in the logs for more info.")
        else:
            self.reload_window_title()
            self.settings.set_chapter(self.provider.get_chapter())
            self.task_successful = False
            self.gui_changing = True
            self.chapter_selector.setText(str(self.settings.get_chapter()))
            self.gui_changing = False
            self.save_last_title(self.provider.__class__.__name__.removesuffix("Provider"), self.provider.get_title(), self.settings.get_chapter())
            print("Reloading images ...")
            self.scrollarea.verticalScrollBar().setValue(0)
            self.scrollarea.horizontalScrollBar().setValue((self.scrollarea.width() // 2))
            self.reload_content()

    def ensure_loaded_chapter(self) -> None:
        files = os.listdir(self.cache_folder) if os.path.exists(self.cache_folder) else []
        cache_was_loaded = len(files) > 0
        if not cache_was_loaded:
            self.chapter_loading_wrapper(self.provider.load_current_chapter, "Info | Reloading of the chapter has failed",
                                         "Maybe this chapter doesn't exist?\nIf that isn't the case, look in the logs for more info.")
        else:
            self.reload_window_title()
            self.settings.set_chapter(self.provider.get_chapter())
            self.task_successful = False
            self.gui_changing = True
            self.chapter_selector.setText(str(self.settings.get_chapter()))
            self.gui_changing = False
            self.save_last_title(self.provider.__class__.__name__.removesuffix("Provider"), self.provider.get_title(), self.settings.get_chapter())
            print("Reloading images ...")
            self.scrollarea.verticalScrollBar().setValue(0)
            self.scrollarea.horizontalScrollBar().setValue((self.scrollarea.width() // 2))
            self.reload_content()

    def reload_chapter(self) -> None:
        self.reset_cache()
        self.chapter_loading_wrapper(self.provider.load_current_chapter, "Info | Reloading of chapter has failed",
                                     "Maybe this chapter doesn't exist?\nIf that isn't the case, look in the logs for more info.")
>>>>>>>> Stashed changes:src/main.py

    # Window Methods
    def resizeEvent(self, event):
        window_width = self.width()

        self.side_menu.move(window_width, 0)  # Update the position of the side menu
        self.side_menu_animation.setStartValue(QRect(window_width, 0, 0, self.height()))
        self.side_menu_animation.setEndValue(QRect(window_width - 200, 0, 200,
                                                   self.height()))  # Adjust 200 as per the desired width of the side menu
        self.menu_button.move(window_width - 40, 20)  # Update the position of the menu button

        new_width = self.width()
        self.search_bar_toggle_button.setFixedWidth(new_width)  # Adjust the width of the toggle button
        self.search_widget.setFixedWidth(new_width)  # Adjust the width of the search bar

        self.update_provider_logo()
        self.update_font_size()
        self.update_menu_button_position()

        super().resizeEvent(event)

    def closeEvent(self, event):
        can_exit = True
        if can_exit:
            print("Exiting ...")
            self.save_settings()
            sys.stdout.close()
            self.settings.close()
            event.accept()  # let the window close
        else:
            print("Couldn't exit.")
            event.ignore()

    # Theme methods
    def set_theme(self):
        theme_setting = self.settings.get_advanced_settings()["themes"][self.os_theme]

        theme = getattr(Themes, theme_setting)
        if theme.stylesheet is not None:
            self.setStyleSheet(theme.stylesheet)
        if theme.app_style is not None:
            self.app.setStyle(theme.app_style)
        icon_theme_color = theme.theme_style if theme.theme_style != "os" else self.os_theme
        font = QFont(self.settings.get_advanced_settings().get("themes").get("font"), self.font().pointSize())
        self.setFont(font)
        for child in self.findChildren(QWidget):
            child.setFont(font)
        self.update()
        self.repaint()

        if hasattr(self, "window_layout"):
            if icon_theme_color == "light":
                self.reload_chapter_button.setIcon(QIcon(f"{self.data_folder}/reload_chapter_icon_dark.png"))
                self.reload_content_button.setIcon(QIcon(f"{self.data_folder}/reload_icon_dark.png"))
            else:
                self.reload_chapter_button.setIcon(QIcon(f"{self.data_folder}/reload_chapter_icon_light.png"))
                self.reload_content_button.setIcon(QIcon(f"{self.data_folder}/reload_icon_light.png"))
        self.theme = icon_theme_color

    def set_dark_stylesheet(self):
        self.setStyleSheet(Themes.dark[0])

    def set_light_dark_stylesheet(self):
        self.setStyleSheet(Themes.light_dark[0])

    def update_theme(self, new_theme: str):
        self.os_theme = new_theme
        self.set_theme()
        if hasattr(self, "window_layout"):
            self.reload_acrylic_menus_setting()

    def timer_tick(self):
        if not self.threading:
            self.update_content()
        if random.randint(0, 20) == 0:
            os_theme = (self.system.get_windows_theme() or os.environ.get("MV_THEME")).lower()
            if os_theme != self.os_theme:
                self.update_theme(os_theme)


class App:
    def __init__(self, qgui, qapp, input_path, logging_level) -> None:
        qgui.app = qapp

    def exit(self) -> None:
        ...


if __name__ == "__main__":
<<<<<<<< Updated upstream:nmv.py
    app = QApplication(sys.argv)
    RESTART_CODE = 1000
    window = MainWindow(app=app)
    window.show()
    current_exit_code = app.exec()

    if current_exit_code == RESTART_CODE:
        os.execv(sys.executable, [sys.executable] + sys.argv)  # os.execv(sys.executable, ['python'] + sys.argv)
========
    print(f"Starting {config.PROGRAM_NAME} {str(config.VERSION) + config.VERSION_ADD} with py{'.'.join([str(x) for x in sys.version_info])} ...")
    CODES: dict[int, _a.Callable[[], None]] = {
        1000: lambda: os.execv(sys.executable, [sys.executable] + sys.argv[1:])  # RESTART_CODE (only works compiled)
    }
    qapp: QApplication | None = None
    qgui: MainWindow | None = None
    dp_app: App | None = None
    current_exit_code: int = -1

    parser = ArgumentParser(description=f"{config.PROGRAM_NAME}")
    parser.add_argument("input", nargs="?", default="", help="Path to the input file.")
    parser.add_argument("--logging-mode", choices=["DEBUG", "INFO", "WARN", "WARNING", "ERROR"], default=None,
                        help="Logging mode (default: None)")
    args = parser.parse_args()

    logging_mode: str = args.logging_mode
    logging_level: int | None = None
    if logging_mode is not None:
        logging_level = getattr(logging, logging_mode.upper(), None)
        if logging_level is None:
            logging.error(f"Invalid logging mode: {logging_mode}")

    input_path: str = ""
    if args.input != "":
        input_path = os.path.abspath(args.input)

        if not os.path.exists(input_path):
            logging.error(f"The input file ({input_path}) needs to exist")
            input_path = ""
        else:
            config.exported_logs += f"Reading {input_path}\n"

    try:
        qapp = QApplication(sys.argv)
        qgui = MainWindow(qapp)
        dp_app = App(qgui, qapp, input_path, logging_level)  # Shows gui
        current_exit_code = qapp.exec()
    except Exception as e:
        perm_error = False
        if isinstance(e.__cause__, PermissionError):
            perm_error = True
        icon: QIcon
        if perm_error:
            error_title = "Warning"
            icon = QIcon(QMessageBox.standardIcon(QMessageBox.Icon.Warning))
            error_text = (f"{config.PROGRAM_NAME} encountered a permission error. This error is unrecoverable.     \n"
                          "Make sure no other instance is running and that no internal app files are open.     ")
        else:
            error_title = "Fatal Error"
            icon = QIcon(QMessageBox.standardIcon(QMessageBox.Icon.Critical))
            error_text = (f"There was an error while running the app {config.PROGRAM_NAME}.\n"
                          "This error is unrecoverable.\n"
                          "Please submit the details to our GitHub issues page.")
        error_description = format_exc()

        custom_icon: bool = False
        if dp_app is not None and hasattr(dp_app, "abs_window_icon_path"):
            icon_path = dp_app.abs_window_icon_path
            icon = QIcon(icon_path)
            custom_icon = True

        msg_box = QQuickMessageBox(None, QMessageBox.Icon.Warning if custom_icon else None, error_title, error_text,
                                   error_description,
                                   standard_buttons=QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Retry,
                                   default_button=QMessageBox.StandardButton.Ok)
        msg_box.setWindowIcon(icon)
        pressed_button = msg_box.exec()
        if pressed_button == QMessageBox.StandardButton.Retry:
            current_exit_code = 1000

        logger: logging.Logger = logging.getLogger("ActLogger")
        if not logger.hasHandlers():
            print(error_description.strip())  # We print, in case the logger is not initialized yet
        else:
            for line in error_description.strip().split("\n"):
                logger.error(line)
    finally:
        if dp_app is not None:
            dp_app.exit()
        if qgui is not None:
            qgui.close()
        if qapp is not None:
            instance = qapp.instance()
            if instance is not None:
                instance.quit()
        results: str = diagnose_shutdown_blockers(return_result=True)
        CODES.get(current_exit_code, lambda: sys.exit(current_exit_code))()
>>>>>>>> Stashed changes:src/main.py

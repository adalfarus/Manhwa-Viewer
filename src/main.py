"""TBA"""
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from aplustools.package.timid import TimidTimer

# Copyright adalfarus 2025
import config
from modules.pipeline_plugin.shader_executor import run_opengl_pipeline_batch

config.check()
config.setup()

from playwright.sync_api import sync_playwright
playwright_instance = sync_playwright().start()

from PySide6.QtWidgets import (QApplication, QLabel, QVBoxLayout, QWidget, QMainWindow, QHBoxLayout, QScroller,
                               QSpinBox, QPushButton, QGraphicsOpacityEffect, QScrollerProperties, QFrame, QFormLayout,
                               QLineEdit, QMessageBox, QScrollBar, QGraphicsProxyWidget, QCheckBox, QToolButton,
                               QFileDialog, QInputDialog, QSizePolicy)
from PySide6.QtGui import QDesktopServices, QPixmap, QIcon, QDoubleValidator, QFont, QImage, QSurfaceFormat, QPainter, \
    QPixmapCache
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QRect, QUrl, QSize
from PySide6.QtGui import QColor

from modules.LibraryPlugin import CoreProvider, CoreSaver
from modules.Classes import Settings, AutoProviderManager, CacheManager
from modules.themes import Themes
from modules.IOManager import IOManager
from modules.pipeline_plugin.loader import PipelineEffectLoader, PipelineEffectModule

from modules.gui import (CustomComboBox, AdvancedSettingsDialog, TransferDialog, TutorialPopup, WaitingDialog,
                              LibraryEdit)
from modules.gui.tasks import CustomProgressDialog, TaskBar
from modules.gui.search_widget import SearchWidget
from modules.gui.image_area import TargetContainer, VerticalManagement

from aplustools.io.env import diagnose_shutdown_blockers
# Apt stuff ( update to newer version )
from oaplustools.data.updaters import VersionNumber
from oaplustools.io.environment import System

from argparse import ArgumentParser
from traceback import format_exc
from pathlib import Path as PLPath
import imageio.v3 as iio
import numpy as np
import requests
import logging
import sqlite3
import random
import shutil
import json
import math
import time
import sys
import cv2
import os

# Standard typing imports for aps
import collections.abc as _a
import typing as _ty

# import multiprocessing
import stdlib_list
from aplustools.io.qtquick import QQuickMessageBox

# multiprocessing.freeze_support()
hiddenimports = list(stdlib_list.stdlib_list())


class MainWindow(QMainWindow):
    def __init__(self, app: QApplication, input_path: str, logging_level: int | None = None) -> None:
        try:
            super().__init__()
            self.app = app
            self.transferring = False

            self.data_folder = os.path.abspath("data").strip("/")
            self.caches_folder = os.path.abspath("data/caches").strip("/")
            self.modules_folder = os.path.abspath(f"{config.VERSION}{config.VERSION_ADD}/core/modules").strip("/")
            self.library_extensions_folder = os.path.abspath(f"{config.VERSION}{config.VERSION_ADD}/extensions/library").strip("/")
            self.pipeline_extensions_folder = os.path.abspath(f"{config.VERSION}{config.VERSION_ADD}/extensions/pipeline_effects").strip("/")
            self.styling_extensions_folder = os.path.abspath(f"{config.VERSION}{config.VERSION_ADD}/extensions/pipeline_effects").strip("/")

            self.cache_manager: CacheManager = CacheManager(self.caches_folder)

            # Setup IOManager
            self.io_manager: IOManager = IOManager()
            self.io_manager.init(self.button_popup, f"{self.data_folder}/logs", config.INDEV)
            if logging_level:
                mode = getattr(logging, logging.getLevelName(logging_level).upper())
            else:
                mode = logging.INFO
            if mode is not None:
                self.io_manager.set_logging_level(mode)
            for exported_line in config.exported_logs.split("\n"):
                self.io_manager.debug(exported_line)  # Flush config prints
            self.system = System()

            self.setWindowTitle(f"Super Manhwa Viewer {str(config.VERSION) + config.VERSION_ADD}")
            self.abs_window_icon_path: str = f"{self.data_folder}/assets/Untitled-1-noBackground.png"
            self.setWindowIcon(QIcon(self.abs_window_icon_path))

            db_path = f"{self.data_folder}/data.db"

            if int(self.system.get_major_os_version()) <= 10:
                self.settings = Settings(db_path, {"geometry": "100, 100, 800, 630", "advanced_settings": '{"recent_titles": [], "themes": {"light": "light", "dark": "dark", "font": "Segoe UI"}, "settings_file_path": "", "settings_file_mode": "overwrite", "misc": {"auto_export": false, "num_workers": 10}}',}, self.export_settings)
            else:
                self.settings = Settings(db_path, {"geometry": "100, 100, 800, 630"}, self.export_settings)
            # self.settings.set_geometry([100, 100, 800, 630])

            self.os_theme = self.system.get_windows_theme() or os.environ.get('MV_THEME') or "light"
            self.theme = None
            x, y, height, width = self.settings.get_geometry()
            self.setGeometry(x, y + 31, height, width)  # Somehow saves it as 31 pixels less
            self.setup_gui()
            self.update_scene_renderer(self.settings.get_advanced_settings()["misc"]["use_opengl_scene_renderer"])
            if os.path.isdir(input_path):
                self.library_edit.add_library_item(os.path.basename(input_path), input_path)
            self.update_theme(self.os_theme.lower())

            # Advanced setup
            self.provider: CoreProvider | None = None
            self.provider_list: list[_ty.Type[CoreProvider]] = []
            self.saver_list: list[CoreSaver] = []
            self.provider_combobox.currentIndexChanged.disconnect()
            self.known_working_searchers = []
            self.reload_providers()
            self.switch_provider(self.settings.get_provider_id())
            self.provider_combobox.currentIndexChanged.connect(self.change_provider)

            self.reload_window_title()

            # Scaling stuff
            self.content_paths = self.get_content_paths()
            self.task_successful = False
            self.threading = False
            self.gui_changing = False  # So we don't clear caches if the gui is changing

            self.reload_gui()

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

            self.content_widgets = []
            self.reload_content()
            QTimer.singleShot(50, lambda: (
                self.scrollarea.verticalScrollBar().setValue(self.settings.get_last_scroll_positions()[0]),
                self.scrollarea.horizontalScrollBar().setValue(self.settings.get_last_scroll_positions()[1]),
                self.scrollarea._onScroll()
            ))

            self.show()
            self.check_for_update()
            self.show_tutorial()
            self.last_reload_ts = time.time()
        except Exception as e:
            self.close()
            raise Exception("Exception occurred during initialization of the Main class") from e

    def button_popup(self, title: str, text: str, description: str,
                     icon: _ty.Literal["Information", "Critical", "Question", "Warning", "NoIcon"],
                     buttons: list[str], default_button: str, checkbox: str | None = None) -> tuple[str | None, bool]:
        if checkbox is not None:
            checkbox = QCheckBox(checkbox)
        msg_box = QQuickMessageBox(self, getattr(QMessageBox.Icon, icon), title, text,
                                   checkbox=checkbox, standard_buttons=None, default_button=None)
        button_map: dict[str, QPushButton] = {}
        for button_str in buttons:
            button = QPushButton(button_str)
            button_map[button_str] = button
            msg_box.addButton(button, QMessageBox.ButtonRole.ActionRole)
        custom_button = button_map.get(default_button)
        if custom_button is not None:
            msg_box.setDefaultButton(custom_button)
        msg_box.setDetailedText(description)

        clicked_button: int = msg_box.exec()

        checkbox_checked = False
        if checkbox is not None:
            checkbox_checked = checkbox.isChecked()

        for button_text, button_obj in button_map.items():
            if msg_box.clickedButton() == button_obj:
                return button_text, checkbox_checked
        return None, checkbox_checked

    def show_tutorial(self) -> None:
        if not self.settings.get_show_tutorial():
            return
        popup = TutorialPopup(self)
        result = popup.exec()

        if popup.checkbox.isChecked():
            print("Do not show again selected")
            self.settings.set_show_tutorial(False)

    def check_for_update(self):
        try:
            response = requests.get("https://raw.githubusercontent.com/adalfarus/Manhwa-Viewer/main/update-check.json",
                                    timeout=1.0)
        except Exception as e:
            title = "Info"
            text = "There was an error when checking for updates."
            description = f"{e}"
            retval, checkbox_checked = self.button_popup(title, text, description, "Information", ["Ok"], "Ok")
            return
        try:
            update_json = response.json()
        except (requests.exceptions.RequestException, requests.exceptions.JSONDecodeError, ValueError) as e:
            print(f"An error occurred: {e}")
            return

        # Initializing all variables
        current_version = VersionNumber(str(config.VERSION) + config.VERSION_ADD)
        found_version: VersionNumber | None = None
        found_release: dict | None = None
        found_push: bool = False

        for release in update_json["versions"]:
            release_version = VersionNumber(release["versionNumber"])
            if release_version == current_version:
                found_version = release_version
                found_release = release
                found_push = False  # Doesn't need to be set again
            if release_version > current_version:
                push = release["push"].title() == "True"
                if found_version is None or (release_version > found_version and push):
                    found_version = release_version
                    found_release = release
                    found_push = push

        if found_version is None:  # Current version is bigger than all in update check and not in update check
            return

        if found_version > current_version and self.settings.get_update_info() and found_push:
            title = "There is an update available"
            text = (f"There is a newer version ({found_version}) "
                    f"available.\nDo you want to open the link to the update?")
            description = f"v{found_version}: {found_release.get('description')}"
            checkbox = "Do not show again"
            retval, checkbox_checked = self.button_popup(title, text, description, "Question", ["Yes", "No"], "Yes", checkbox)

            if checkbox_checked:
                print("Do not show again selected")
                self.settings.set_update_info(False)
            if retval == "Yes":
                if found_release.get("updateUrl", "None").title() == "None":
                    link = update_json["metadata"].get("sorryUrl", "https://example.com")
                else:
                    link = found_release.get("updateUrl")
                QDesktopServices.openUrl(QUrl(link))
        elif self.settings.get_no_update_info() and found_version <= current_version:
            title = "Info"
            text = (f"No new updates available.\nChecklist last updated "
                    f"{update_json['metadata']['lastUpdated'].replace('-', '.')}.")
            description = f"v{found_version}: {found_release.get('description')}"
            checkbox = "Do not show again"
            retval, checkbox_checked = self.button_popup(title, text, description, "Information", ["Ok"], "Ok",
                                                         checkbox)

            if checkbox_checked:
                print("Do not show again selected")
                self.settings.set_no_update_info(False)
        elif self.settings.get_not_recommended_update_info() and not found_push:
            title = "Info"
            text = (f"New version available, but not recommended {found_version}.\n"
                    f"Checklist last updated {update_json['metadata']['lastUpdated'].replace('-', '.')}.")
            description = f"v{found_version}: {found_release.get('description')}"
            checkbox = "Do not show again"
            retval, checkbox_checked = self.button_popup(title, text, description, "Information", ["Ok", "Take me there"], "Ok",
                                                         checkbox)

            if retval == "Take me there":
                if found_release.get("updateUrl", "None").title() == "None":
                    link = update_json["metadata"].get("sorryUrl", "https://example.com")
                else:
                    link = found_release.get("updateUrl")
                QDesktopServices.openUrl(QUrl(link))

            if checkbox_checked:
                print("Do not show again selected")
                self.settings.set_not_recommended_update_info(False)

    def setup_gui(self) -> None:
        # Central Widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.window_layout = QVBoxLayout(central_widget)

        # Add buttons at the end of the content, side by side
        self.buttons_widget = QWidget()
        buttons_layout = QHBoxLayout(self.buttons_widget)
        self.prev_button = QPushButton("Previous")
        buttons_layout.addWidget(self.prev_button)
        self.next_button = QPushButton("Next")
        buttons_layout.addWidget(self.next_button)

        self.buttons_proxy_widget = QGraphicsProxyWidget()
        self.buttons_proxy_widget.setWidget(self.buttons_widget)

        # Scroll Area
        self.scrollarea = TargetContainer(self.settings.get_scrolling_sensitivity(), parent=self)
        self.scrollarea.setManagement(VerticalManagement(self.buttons_proxy_widget, self.settings.get_downscaling(), self.settings.get_upscaling(),
                                                         self.settings.get_manual_content_width(), self.settings.get_lazy_loading()))
        self.scrollarea.scrollBarsBackgroundRedraw(True)
        self.scrollarea.graphics_view.setBackgroundBrush(Qt.NoBrush)
        self.scrollarea.scene.addItem(self.buttons_proxy_widget)
        # self.scrollarea.verticalScrollBar().setSingleStep(24)
        self.window_layout.addWidget(self.scrollarea)

        # Taskbar
        self.task_bar = TaskBar(self, "first")
        self.window_layout.addWidget(self.task_bar)

        # Enable kinetic scrolling
        scroller = QScroller.scroller(self.scrollarea.graphics_view.viewport())
        scroller.grabGesture(self.scrollarea.graphics_view.viewport(), QScroller.ScrollerGestureType.TouchGesture)
        scroller_properties = QScrollerProperties(scroller.scrollerProperties())
        scroller_properties.setScrollMetric(QScrollerProperties.ScrollMetric.MaximumVelocity, 0.3)
        scroller.setScrollerProperties(scroller_properties)

        # Add a transparent image on the top left
        self.transparent_image = QLabel(self)
        self.transparent_image.setObjectName("transparentImage")
        self.transparent_image.setPixmap(QPixmap(os.path.abspath(f"{self.data_folder}/assets/empty.png")))
        self.transparent_image.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        opacity = QGraphicsOpacityEffect(self.transparent_image)
        opacity.setOpacity(0.5)  # Adjust the opacity level
        self.transparent_image.setGraphicsEffect(opacity)
        self.transparent_image.setAttribute(Qt.WA_TransparentForMouseEvents, True)

        # Menu Button
        self.menu_button = QPushButton(QIcon(f"{self.data_folder}/assets/empty.png"), "", self)  # .centralWidget()
        self.menu_button.setFixedSize(40, 40)

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

        self.saver_combobox = CustomComboBox()
        saver_layout = QHBoxLayout()
        saver_layout.addWidget(QLabel("Library Manager:"))
        saver_layout.addWidget(self.saver_combobox)
        side_menu_layout.addRow(saver_layout)

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

        self.library_edit: LibraryEdit = LibraryEdit()
        library_select_button: QToolButton = QToolButton()
        library_select_button.setText("...")
        library_select_button.clicked.connect(self.select_folder)
        library_layout = QHBoxLayout()
        library_layout.setContentsMargins(0, 0, 0, 0)
        label = QLabel("Library: ")
        self.library_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        library_select_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        library_layout.addWidget(label)
        library_layout.addWidget(self.library_edit)
        library_layout.addWidget(library_select_button)

        self.library_layout_frame = QFrame()
        self.library_layout_frame.setFrameShape(QFrame.Shape.NoFrame)
        self.library_layout_frame.setLayout(library_layout)

        side_menu_layout.addRow(self.library_layout_frame)

        previous_chapter_button_side_menu = QPushButton("Previous")
        next_chapter_button_side_menu = QPushButton("Next")
        self.reload_chapter_button = QPushButton(QIcon(f"{self.data_folder}/assets/empty.png"), "")
        self.reload_content_button = QPushButton(QIcon(f"{self.data_folder}/assets/empty.png"), "")

        side_menu_buttons_layout = QHBoxLayout()
        side_menu_buttons_layout.addWidget(previous_chapter_button_side_menu)
        side_menu_buttons_layout.addWidget(next_chapter_button_side_menu)
        side_menu_buttons_layout.addWidget(self.reload_chapter_button)
        side_menu_buttons_layout.addWidget(self.reload_content_button)
        side_menu_layout.addRow(side_menu_buttons_layout)

        self.show_provider_logo_checkbox = QCheckBox("Provider Logo")
        self.search_all_button = QPushButton("Search all")
        another_layout = QHBoxLayout()
        another_layout.setContentsMargins(0, 0, 0, 0)
        another_layout.addWidget(self.show_provider_logo_checkbox)
        another_layout.addWidget(self.search_all_button)

        side_menu_layout.addRow(another_layout)

        [side_menu_layout.addRow(QWidget()) for _ in range(1)]

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

        [side_menu_layout.addRow(QWidget()) for _ in range(1)]

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
        apply_manual_width_button = QPushButton("Apply Width")
        manual_width_layout = QHBoxLayout()
        manual_width_layout.setContentsMargins(0, 0, 0, 0)
        manual_width_layout.addWidget(self.manual_width_spinbox)
        manual_width_layout.addWidget(apply_manual_width_button)

        side_menu_layout.addRow(manual_width_layout)

        [side_menu_layout.addRow(QWidget()) for _ in range(1)]

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

        [side_menu_layout.addRow(QWidget()) for _ in range(1)]

        self.scroll_sensitivity_scroll_bar = QScrollBar(Qt.Orientation.Horizontal)
        self.scroll_sensitivity_scroll_bar.setMinimum(1)  # QScrollBar uses integer values
        self.scroll_sensitivity_scroll_bar.setMaximum(80)  # We multiply by 10 to allow decimal
        self.scroll_sensitivity_scroll_bar.setValue(10)  # Default value set to 1.0 (10 in this scale)
        self.scroll_sensitivity_scroll_bar.setSingleStep(1)
        self.scroll_sensitivity_scroll_bar.setPageStep(1)

        # Label to display the current sensitivity
        self.sensitivity_label = QLabel("Current Sensitivity: 1.0")
        side_menu_layout.addRow(self.sensitivity_label, self.scroll_sensitivity_scroll_bar)

        [side_menu_layout.addRow(QWidget()) for _ in range(1)]

        self.save_last_titles_checkbox = QCheckBox("Save last titles")
        side_menu_layout.addRow(self.save_last_titles_checkbox)
        self.transfer_chapter_s_button = QPushButton("Transfer chapter(s)")  # "Export Settings"
        advanced_settings_button = QPushButton("Adv Settings")
        side_menu_layout.addRow(self.transfer_chapter_s_button, advanced_settings_button)

        self.convert_to_lossless_checkbox = QCheckBox("Lossless format (avoids pipeline artifacts)")
        side_menu_layout.addRow(self.convert_to_lossless_checkbox)

        image_processing_pipeline_button = QPushButton("Run Image processing pipeline")
        side_menu_layout.addRow(image_processing_pipeline_button)

        # Timer to regularly check for resizing needs
        timer = QTimer(self)
        timer.start(500)

        # Connect GUI components
        self.search_bar_toggle_button.clicked.connect(self.toggle_search_bar)
        # Checkboxes
        self.downscale_checkbox.toggled.connect(self.downscale_checkbox_toggled)
        self.upscale_checkbox.toggled.connect(self.upscale_checkbox_toggled)
        self.lazy_loading_checkbox.toggled.connect(self.lazy_loading_toggled)
        self.borderless_checkbox.toggled.connect(self.reload_borderless_setting)
        self.acrylic_menus_checkbox.toggled.connect(self.reload_acrylic_menus_setting)
        self.acrylic_background_checkbox.toggled.connect(self.reload_acrylic_background_setting)
        self.hide_scrollbar_checkbox.toggled.connect(self.reload_hide_scrollbar_setting)
        self.stay_on_top_checkbox.toggled.connect(self.reload_stay_on_top_setting)
        self.hide_title_bar_checkbox.toggled.connect(self.reload_hide_titlebar_setting)
        self.hover_effect_all_checkbox.toggled.connect(self.reload_hover_effect_all_setting)
        self.save_last_titles_checkbox.toggled.connect(self.toggle_save_last_titles_checkbox)
        # Selectors
        self.show_provider_logo_checkbox.checkStateChanged.connect(self.set_show_provider_logo)
        self.title_selector.editingFinished.connect(self.finish_editing_title)
        self.chapter_selector.textChanged.connect(self.set_chapter)
        self.library_edit.currentIndexChanged.connect(self.change_library)
        self.library_edit.remove_library.connect(lambda item: (
            self.settings.set_libraries(self.settings.get_libraries().remove(item[1])),
            self.settings.set_current_lib_idx(self.library_edit.currentIndex())
        ))
        self.library_edit.set_library_name.connect(self.set_library_name)
        self.chapter_rate_selector.textChanged.connect(self.set_chapter_rate)
        # Menu components
        self.menu_button.clicked.connect(self.toggle_side_menu)  # Menu
        apply_manual_width_button.clicked.connect(self.apply_manual_content_width)  # Menu
        self.prev_button.clicked.connect(self.previous_chapter)  # Menu
        self.next_button.clicked.connect(self.next_chapter)  # Menu
        self.reload_chapter_button.clicked.connect(self.reload_chapter)  # Menu
        self.reload_content_button.clicked.connect(self.reload)  # Menu
        previous_chapter_button_side_menu.clicked.connect(self.previous_chapter)
        next_chapter_button_side_menu.clicked.connect(self.next_chapter)
        advanced_settings_button.clicked.connect(self.advanced_settings)  # Menu
        self.transfer_chapter_s_button.clicked.connect(self.transfer_chapter_s)  # Menu
        image_processing_pipeline_button.clicked.connect(self.run_pipeline)
        self.convert_to_lossless_checkbox.checkStateChanged.connect(self.convert_to_lossless_toggled)
        # Rest
        self.provider_combobox.currentIndexChanged.connect(self.change_provider)  # Menu
        self.saver_combobox.currentIndexChanged.connect(self.change_saver)  # Menu
        self.side_menu_animation.valueChanged.connect(self.side_menu_animation_value_changed)  # Menu
        timer.timeout.connect(self.timer_tick)
        self.search_bar_animation.valueChanged.connect(self.search_bar_animation_value_changed)
        self.search_widget.selectedItem.connect(self.selected_chosen_result)
        self.scroll_sensitivity_scroll_bar.valueChanged.connect(self.update_sensitivity)
        self.search_all_button.clicked.connect(self.search_all)

        # Style GUI components
        self.centralWidget().setStyleSheet("background: transparent;")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.menu_button.setIcon(QIcon(f"{self.data_folder}/assets/menu_icon.png"))
        if self.theme == "light":
            self.reload_chapter_button.setIcon(QIcon(f"{self.data_folder}/assets/reload_chapter_icon_dark.png"))
            self.reload_content_button.setIcon(QIcon(f"{self.data_folder}/assets/reload_icon_dark.png"))
        else:
            self.reload_chapter_button.setIcon(QIcon(f"{self.data_folder}/assets/reload_chapter_icon_light.png"))
            self.reload_content_button.setIcon(QIcon(f"{self.data_folder}/assets/reload_icon_light.png"))

    def convert_to_lossless_toggled(self) -> None:
        self.settings.set_convert_to_lossless(self.convert_to_lossless_checkbox.isChecked())

    def handle_search_all(self, text: str) -> None:
        provider_name, rest = text.split(": ", maxsplit=1)
        title, chapter = rest.rsplit(", Ch ", maxsplit=1)
        self.selected_chosen_item(f"{provider_name}\x00{title}\x00{chapter}")

    def search_all(self) -> None:
        is_visible = self.search_widget.y() >= 0
        if not is_visible:
            end_rect = QRect(0, self.search_bar_toggle_button.height() - 20, self.search_widget.width(),
                             self.search_widget.height())
            self.search_bar_animation.setStartValue(self.search_widget.geometry())
            self.search_bar_animation.setEndValue(end_rect)
            self.search_bar_animation.start()
        old_func = self.search_widget.search_results_func

        duped_provider_search_funcs = []
        providers = []  # Never used, just so they don't go out of scope
        def _create_lambda(provider_name: str, func, wanted_chapter: str, wanted_range: tuple[int, int]):
            return lambda text: [(f"{provider_name}: {result[0]}, Ch {wanted_chapter}", result[1]) for result in func(text) if result[0] is not None][wanted_range[0]:wanted_range[1]]
        def _try_result_wrapper(func, text) -> list[tuple[str, str]]:
            try:
                ret = func(text)
            except Exception:
                return []
            return ret
        for provider_name, provider_cls in self.known_working_searchers:
            provider = provider_cls("", 0, "", f"{self.data_folder}/logos")
            duped_provider_search_funcs.append(_create_lambda(provider_name, provider.get_search_results, "1", (0, 2)))
            providers.append(provider)

        self.search_widget.search_results_func = lambda text: sum([_try_result_wrapper(func, text) for func in duped_provider_search_funcs], start=[])
        self.search_widget.search_bar.setStyleSheet("border: 2px solid gold; border-radius: 4px;")
        self.search_widget.selectedItem.disconnect()
        self.search_widget.selectedItem.connect(self.handle_search_all)
        self.search_widget.search_bar.setFocus()
        while self.search_widget.isAncestorOf(QApplication.focusWidget()):
            time.sleep(0.01)
            QApplication.processEvents()
        QTimer.singleShot(10, lambda: (
            self.search_widget.search_bar.setStyleSheet(""),
            setattr(self.search_widget, "search_results_func", old_func),
            self.search_widget.on_text_changed(),
            self.search_widget.selectedItem.disconnect(),
            self.search_widget.selectedItem.connect(self.selected_chosen_result)
        ))  # To allow for a search to happen

    def transfer_chapter_s(self) -> None:
        old_chapter = self.settings.get_chapter()
        self.transferring = True
        dialog = TransferDialog(self, self.settings.get_chapter(), self.settings.get_chapter_rate())
        dialog.exec()
        if dialog.return_to_chapter:
            self.set_chapter()
            self.chapter_selector.setText(str(old_chapter))
            self.ensure_loaded_chapter()
            self.settings.set_chapter(old_chapter)
        self.transferring = False

    def select_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            self.library_edit.add_library_item(os.path.basename(folder), folder)
            self.settings.set_libraries(self.settings.get_libraries() + [folder])
            self.settings.set_current_lib_idx(self.library_edit.currentIndex())

    def toggle_save_last_titles_checkbox(self):
        self.settings.set_save_last_titles(self.save_last_titles_checkbox.isChecked())

    def update_scene_renderer(self, opengl_enabled: bool) -> None:
        view = self.scrollarea.graphics_view
        if opengl_enabled:
            print("Switching to OpenGL Widget")
            fmt = QSurfaceFormat()
            fmt.setRenderableType(QSurfaceFormat.RenderableType.OpenGL)
            QSurfaceFormat.setDefaultFormat(fmt)

            gl_widget = QOpenGLWidget()
            view.setViewport(gl_widget)
        else:
            print("Switching to default Widget")
            view.setViewport(QWidget())

        # Required: re-layout the view
        # view.setRenderHints(
        #     QPainter.RenderHint.SmoothPixmapTransform |
        #     QPainter.RenderHint.Antialiasing
        # )
        QPixmapCache.clear()
        view.viewport().update()
        view.scene().invalidate()  # Forces full redraw
        view.scene().update()

    def advanced_settings(self, *_, blocking: bool = True):
        settings = self.settings.get_advanced_settings()
        default_settings = json.loads(self.settings.get_default_setting("advanced_settings"))
        self.settings.close()
        available_themes = tuple(key for key in Themes.__dict__.keys() if not (key.startswith("__") or key.endswith("__")))
        dialog = AdvancedSettingsDialog(parent=self, current_settings=settings, default_settings=default_settings, master=self, available_themes=available_themes, export_settings_func=self.export_settings)
        if blocking:
            dialog.exec()
        else:
            dialog.show()
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

            if (settings["themes"]["light"] != dialog.selected_settings["themes"]["light"]
                    or settings["themes"]["dark"] != dialog.selected_settings["themes"]["dark"]):
                self.save_settings()
                self.set_theme()
            if settings["misc"]["use_opengl_scene_renderer"] != dialog.selected_settings["misc"]["use_opengl_scene_renderer"]:
                if dialog.selected_settings["misc"]["use_opengl_scene_renderer"] == False:
                    result = QMessageBox.question(self, "Restart Client?",
                                                  "When switching back from the OpenGL Scene-Renderer, you'll need to restart the program for it to take effect.\nDo you wish to continue?",
                                                  QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                                  QMessageBox.StandardButton.Yes)
                    if result == QMessageBox.StandardButton.Yes:
                        print("Exiting ...")
                        self.save_settings()
                        # sys.stdout.close()
                        # self.settings.close()
                        QApplication.exit(1000)
                self.update_scene_renderer(dialog.selected_settings["misc"]["use_opengl_scene_renderer"])

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

    def switch_provider(self, id: str):
        global playwright_instance
        provider_cls: _ty.Type[CoreProvider] | None = None
        for prov_cls in self.provider_list:
            if id == prov_cls.register_provider_id:
                provider_cls = prov_cls
                break
        if provider_cls is None:
            raise Exception(f"Switching of provider to id {id} failed: id not found")

        if hasattr(provider_cls, "_playwright") and provider_cls._playwright is None:
            provider_cls._playwright = playwright_instance

        if self.settings.get_current_lib_idx() != -1:
            current_library = self.settings.get_libraries()[self.settings.get_current_lib_idx()]
        else:
            current_library = ""
        self.provider = provider_cls(self.settings.get_title(), self.settings.get_chapter(), current_library, f"{self.data_folder}/logos")

        if self.provider.get_search_results(None):
            self.search_widget.set_search_results_func(self.provider.get_search_results)
            self.search_widget.setEnabled(True)
        else:
            self.search_widget.setEnabled(False)

        new_pixmap = QPixmap(os.path.abspath(self.provider.get_logo_path()))
        self.transparent_image.setPixmap(new_pixmap)
        self.update_provider_logo()
        self.update_provider_logo()
        if self.provider.register_saver is not None:
            self.transfer_chapter_s_button.setEnabled(False)
            self.saver_combobox.setCurrentIndex(self.saver_list.index(self.provider.register_saver))
            self.change_saver()
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

    def format_title(self, title: str) -> str:
        return ' '.join(word[0].upper() + word[1:] if word else '' for word in title.lower().split())

    def reload_window_title(self):
        new_title = self.format_title(self.provider.get_title())
        self.setWindowTitle(f'SMV {str(config.VERSION) + config.VERSION_ADD} | {new_title}, Chapter {self.provider.get_chapter()}')

    def get_content_paths(self, allowed_file_formats: tuple = None):
        if allowed_file_formats is None:
            allowed_file_formats = ('.png', ".jpg", ".jpeg", ".webp", ".http", '.mp4', '.txt')
        cache_folder: str = self.cache_manager.get_cache_folder(self.provider.get_chapter())
        content_files = sorted([f for f in os.listdir(cache_folder) if
                                f.endswith(allowed_file_formats)])
        content_paths = [os.path.join(cache_folder, f) for f in content_files]
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
            self.buttons_widget.setStyleSheet(self.buttons_widget.styleSheet() + style_sheet_non_transparent)
        else:
            self.menu_button.setStyleSheet("")
            self.side_menu.setStyleSheet("")
            self.search_bar_toggle_button.setStyleSheet("")
            self.buttons_widget.setStyleSheet("")
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
        self.scrollarea.management.downscaling = self.downscale_checkbox.isChecked()
        self.scrollarea.force_rescaling = True
        self.scrollarea._rescaleImages(QSize(self.scrollarea.width(), self.scrollarea.height()))
        self.scrollarea._adjustSceneBounds()
        self.scrollarea.graphics_view.resetCachedContent()
        self.scrollarea.updateScrollBars()
        self.scrollarea._onScroll()

    def upscale_checkbox_toggled(self):
        self.settings.set_upscaling(self.upscale_checkbox.isChecked())
        self.scrollarea.management.upscaling = self.upscale_checkbox.isChecked()
        self.scrollarea.force_rescaling = True
        self.scrollarea._rescaleImages(QSize(self.scrollarea.width(), self.scrollarea.height()))
        self.scrollarea._adjustSceneBounds()
        self.scrollarea.graphics_view.resetCachedContent()
        self.scrollarea.updateScrollBars()
        self.scrollarea._onScroll()

    def lazy_loading_toggled(self) -> None:
        self.settings.set_lazy_loading(self.lazy_loading_checkbox.isChecked())
        self.scrollarea.management.lazy_loading = self.lazy_loading_checkbox.isChecked()
        self.scrollarea._onScroll()

    def apply_manual_content_width(self):
        self.settings.set_manual_content_width(self.manual_width_spinbox.value())
        self.scrollarea.management.base_width = self.manual_width_spinbox.value()
        self.scrollarea.force_rescaling = True
        self.scrollarea._rescaleImages(QSize(self.scrollarea.width(), self.scrollarea.height()))
        self.scrollarea._adjustSceneBounds()
        self.scrollarea.graphics_view.resetCachedContent()
        self.scrollarea.updateScrollBars()
        self.scrollarea._onScroll()

    def set_show_provider_logo(self) -> None:
        self.settings.set_show_provider_logo(self.show_provider_logo_checkbox.isChecked())
        self.update_provider_logo()

    def wait_for_tasks(self) -> None:
        if self.task_bar.task_count() != 0:
            wait_dialog = WaitingDialog(self)
            wait_dialog.show()
            while self.task_bar.task_count() != 0:
                QApplication.processEvents()
                time.sleep(0.1)
            wait_dialog.close()

    def finish_editing_title(self) -> None:
        new_title = self.title_selector.text().strip().lower()
        if new_title == self.provider.get_title().lower():
            return
        if not self.gui_changing:
            self.wait_for_tasks()
            self.cache_manager.clear_all_caches()
            self.reload_content()
        self.settings.set_title(new_title)
        self.provider.set_title(new_title)

    def set_chapter(self):
        new_chapter = float("0" + self.chapter_selector.text())
        if 0.0 <= new_chapter < 1000.0:
            self.provider.set_chapter(new_chapter)
        else:
            self.provider.set_chapter(0)
            # self.gui_changing = True
            self.chapter_selector.setText("0")
            # self.gui_changing = False

    def set_library_name(self, library: tuple[str, str]) -> None:
        new_name, ok = QInputDialog.getText(self, "Set Library Name", "Enter new name:", text=library[0])
        if ok and new_name:
            self.saver_list[self.saver_combobox.currentIndex()].rename_library(library[1], new_name)
            self.library_edit.set_lib_name(library[1], new_name)

    def set_chapter_rate(self):
        new_chapter_rate = float("0" + self.chapter_rate_selector.text())
        if 0.1 <= new_chapter_rate <= 2.0:
            self.settings.set_chapter_rate(new_chapter_rate)
            # self.provider.set_chapter_rate(new_chapter_rate)
            # self.gui_changing = True
            self.chapter_rate_selector.setText(str(new_chapter_rate))
            # self.gui_changing = False
        else:
            self.settings.set_chapter_rate(0.1)
            # self.provider.set_chapter_rate(0.1)
            # self.gui_changing = True
            self.chapter_rate_selector.setText("0.1")
            # self.gui_changing = False

    def update_sensitivity(self, value):
        sensitivity = value / 10
        self.settings.set_scrolling_sensitivity(sensitivity)
        self.sensitivity_label.setText(f"Current Sensitivity: {sensitivity:.1f}")
        self.scrollarea.graphics_view.sensitivity = sensitivity
        self.scrollarea.verticalScrollBar().setSingleStep(value * 10)
        self.scrollarea.verticalScrollBar().setPageStep(value * 100)
        self.scrollarea.horizontalScrollBar().setSingleStep(value * 10)
        self.scrollarea.horizontalScrollBar().setPageStep(value * 100)

    def selected_chosen_result(self, title, toggle_search_bar: bool = True):
        new_title = self.format_title(title)
        self.title_selector.setText(new_title)
        self.finish_editing_title()
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

        new_title = self.format_title(title)
        self.title_selector.setText(new_title)
        self.finish_editing_title()
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
                if title.lower() == last_title and (provider == last_provider or chapter == last_chapter):  # Was just not working
                    print(title, last_title, provider, last_provider, chapter, last_chapter)
                    print("Removing")
                    continue
                elif not _:
                    new_titles.append(f"{title}\x00{provider}\x00{0}")  # As the title is the first split
                    continue
                new_titles.append(f"{provider}\x00{title}\x00{chapter}")
            new_titles.append(f"{last_provider}\x00{last_title}\x00{last_chapter}")
            sett["recent_titles"] = new_titles
            self.settings.set_advanced_settings(sett)

    def change_provider(self, *args, callback: bool = False):
        if not callback:
            self.previous_provider = self.provider
        self.switch_provider(self.provider_list[self.provider_combobox.currentIndex()].register_provider_id)
        if not callback:
            QTimer.singleShot(50, self.change_provider_callback)

    def change_saver(self, *args):
        self.saver = self.saver_list[self.saver_combobox.currentIndex()]
        self.settings.set_library_manager_id(self.saver.register_library_id)
        if not self.saver.is_compatible(self.library_edit.current_library()[1]):
            if self.settings.get_current_lib_idx() != self.library_edit.currentIndex():
                self.library_edit.setCurrentIndex(self.settings.get_current_lib_idx())
            else:
                self.library_edit.setCurrentIndex(-1)
            self.change_library()

    def change_library(self, *args) -> None:
        new_library_path: str = self.library_edit.current_library()[1]
        if new_library_path != "":
            if self.saver.is_compatible(new_library_path):
                self.saver.create_library(*self.library_edit.current_library()[::-1])
            else:
                for i, saver in enumerate(self.saver_list):
                    if saver.is_compatible(new_library_path):
                        self.saver_combobox.setCurrentIndex(i)
                        self.change_saver()
                        break
                # if self.settings.get_current_lib_idx() != self.library_edit.currentIndex():
                #     self.library_edit.setCurrentIndex(self.settings.get_current_lib_idx())
                # else:
                #     self.library_edit.setCurrentIndex(-1)
                # new_library_path = self.library_edit.current_library()[1]
        self.settings.set_current_lib_idx(self.library_edit.currentIndex())
        self.provider.set_library_path(new_library_path)
        if hasattr(self, "previous_provider"):
            self.previous_provider.set_library_path(new_library_path)

    def change_provider_callback(self):
        self.change_provider(callback=True)
        print(f"Switching provider {self.previous_provider} -> {self.provider}")
        self.wait_for_tasks()
        if type(self.provider) is not type(self.previous_provider):
            self.cache_manager.clear_all_caches()
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
                scaled_pixmap = QPixmap(os.path.abspath(self.provider.get_logo_path())).scaledToHeight(wanted_size, Qt.TransformationMode.SmoothTransformation)
            if pixmap.width() > self.width() - 20:
                scaled_pixmap = QPixmap(os.path.abspath(self.provider.get_logo_path())).scaledToWidth(self.width() - 20, Qt.TransformationMode.SmoothTransformation)
            elif pixmap.height() > self.height() - 20:
                scaled_pixmap = QPixmap(os.path.abspath(self.provider.get_logo_path())).scaledToHeight(self.height() - 20, Qt.TransformationMode.SmoothTransformation)
            self.transparent_image.setFixedSize(scaled_pixmap.width() + 20, scaled_pixmap.height() + 20)
            self.transparent_image.setPixmap(scaled_pixmap)

    # Rest
    def reload_providers(self) -> None:
        provider_manager: AutoProviderManager = AutoProviderManager(self.library_extensions_folder, CoreProvider)
        loaded_provs = provider_manager.get_providers()
        self.provider_list.clear()
        self.saver_list.clear()

        if len(self.provider_list) > 0:
            self.provider_list[0].button_popup = self.button_popup

        self.provider_combobox.clear()
        self.saver_combobox.clear()
        # last_prov_idx: int | None = None
        saved_prov_idx: int | None = None
        saved_provider_id = self.settings.get_provider_id()
        saved_saver_idx: int = -1
        saved_saver_id = self.settings.get_library_manager_id()

        prov_i = 0
        saver_i = 0
        for provider_cls in loaded_provs:
            provider = provider_cls("", 0, "", f"{self.data_folder}/logos")

            if not provider.can_work():
                continue
            self.provider_list.append(provider_cls)
            provider_name = provider.register_provider_name

            logo_path = provider.get_logo_path()
            icon_path = provider.get_icon_path()
            image = QImage(os.path.abspath(logo_path))
            image_width, image_height = image.width(), image.height()

            if provider.clipping_space is not None:
                start_x, start_y, end_x, end_y = provider.clipping_space

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

                print(f"Cropping {image_height} x {image_width} for {provider_name}")
                cropped_image = image.copy(start_y, start_x, end_y, end_x)
            else:
                cropped_image = QImage(os.path.abspath(icon_path))

            icon = QIcon(QPixmap.fromImage(cropped_image))

            # Add item to the dropdown
            self.provider_combobox.addItem(icon, provider_name)

            if provider.register_saver is not None:
                self.saver_list.append(provider.register_saver)
                self.saver_combobox.addItem(icon, provider.register_saver.register_library_name)
                if provider.register_saver.register_library_id == saved_saver_id:
                    saved_saver_idx = saver_i
                saver_i += 1

            if not provider.is_working():
                item = self.provider_combobox.model().item(prov_i)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
                if provider.register_saver is not None:
                    item2 = self.saver_combobox.model().item(saver_i-1)
                    item2.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
            else:
                if provider.register_provider_id == saved_provider_id:
                    saved_prov_idx = prov_i
                # last_prov_idx = prov_i  # Track last working provider
            # if "Provider" not in provider_cls_name:
            #     self.provider_combobox.setItemUnselectable(prov_i)
            prov_i += 1
        if saved_prov_idx is not None:
            print(f"Saved provider ({saved_provider_id}) working")
            self.provider_combobox.setCurrentIndex(saved_prov_idx)
        # elif last_prov_idx is not None:
        #     print(f"Other working provider ({last_prov_idx})")
        #     self.provider_combobox.setCurrentIndex(last_prov_idx)  # Fallback to last working provider
        else:
            print("Saved provider not found")
            self.provider_combobox.setCurrentIndex(-1)  # No selection if no working provider found
        self.saver_combobox.setCurrentIndex(saved_saver_idx)
        self.change_saver()
        self.reload_searchers()

    def reload_searchers(self) -> None:
        for provider_cls in self.provider_list:
            provider_name = provider_cls.register_provider_name
            provider = provider_cls("", 0, "", f"{self.data_folder}/logos")
            if not provider.get_search_results(None) or not provider.can_work() or not provider.is_working():
                continue
            self.known_working_searchers.append((provider_name, provider_cls))

    def save_settings(self):
        if hasattr(self, "settings") and self.settings.is_open:
            self.settings.set_provider_id(self.provider_list[self.provider_combobox.currentIndex()].register_provider_id)
            self.settings.set_title(self.provider.get_title())
            self.settings.set_chapter(self.provider.get_chapter())
            self.settings.set_chapter_rate(float(self.chapter_rate_selector.text()))
            # self.settings.set_provider_type(self.provider.get_provider_type())

            # self.settings.set_blacklisted_websites(self.provider.get_blacklisted_websites())

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

    def get_library_name(self, lib_path: str) -> str:
        for saver in self.saver_list:
            if saver.is_compatible(lib_path):
                return saver.get_library_name(lib_path)
        return "Unknown"

    def reload_gui(self, reload_geometry: bool = False, reload_position: bool = False):
        # self.provider_combobox.setCurrentText(self.settings.get_provider())
        self.pipeline_effects_loader = PipelineEffectLoader()
        self.pipeline_effects_loader.load_from_folder(self.pipeline_extensions_folder)
        self.show_provider_logo_checkbox.setChecked(self.settings.get_show_provider_logo())
        self.gui_changing = True
        self.title_selector.setText(self.format_title(self.settings.get_title()))
        self.gui_changing = False
        self.chapter_selector.setText(str(self.settings.get_chapter()))
        self.chapter_rate_selector.setText(str(self.settings.get_chapter_rate()))
        # self.provider_type_combobox.setCurrentText(self.settings.get_provider_type().title())
        lib_idx = self.settings.get_current_lib_idx()
        self.library_edit.currentIndexChanged.disconnect(self.change_library)
        self.library_edit.clear()
        for path in self.settings.get_libraries():
            name = self.get_library_name(path)
            self.library_edit.add_library_item(name, path)
        if lib_idx != -1:
            self.library_edit.setCurrentIndex(lib_idx)
        else:
            self.library_edit.blockSignals(True)
            self.library_edit.setCurrentIndex(-1)
            self.library_edit.setEditText("")  # ← Works better than setCurrentText("")
            self.library_edit.clearEditText()  # Optional, more explicit
            self.library_edit.blockSignals(False)
        self.library_edit.currentIndexChanged.connect(self.change_library)

        # self.provider.set_blacklisted_websites(self.settings.get_blacklisted_websites())

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
        self.convert_to_lossless_checkbox.setChecked(self.settings.get_convert_to_lossless())

    def reload(self):
        current_ts = time.time()
        self.save_settings()
        self.reload_window_title()
        self.provider_combobox.currentIndexChanged.disconnect()
        self.reload_providers()
        self.switch_provider(self.settings.get_provider_id())
        self.provider_combobox.currentIndexChanged.connect(self.change_provider)
        self.reload_gui(reload_geometry=True, reload_position=True if (current_ts - self.last_reload_ts) < 1 else False)

        self.reload_hover_effect_all_setting()
        self.reload_borderless_setting()
        self.reload_acrylic_menus_setting()
        self.reload_acrylic_background_setting()

        self.reload_hide_titlebar_setting()
        self.reload_hide_scrollbar_setting()
        self.reload_stay_on_top_setting()

        self.update_sensitivity(int(self.settings.get_scrolling_sensitivity() * 10))

        self.content_paths = self.get_content_paths()
        self.reload_content()
        self.last_reload_ts = time.time()

    # Content management methods
    def reload_content(self):
        self.content_paths = self.get_content_paths()
        content_widgets_length = len(self.content_widgets) - 1
        i = 0
        self.scrollarea.verticalScrollBar().setValue(0)
        self.scrollarea.horizontalScrollBar().setValue(0)
        for item in self.scrollarea.scene.items():
            if item != self.buttons_proxy_widget:
                self.scrollarea.scene.removeItem(item)
        self.scrollarea.images.clear()

        for i, content_path in enumerate(self.content_paths):
            if content_path.endswith((".png", ".jpg", ".jpeg", ".webp")):
                self.scrollarea.addImagePath(content_path)
                # if i > content_widgets_length:
                #     image_label = ImageLabel()
                #     self.content_widgets.append(image_label)
                #     pixmap = QPixmap(content_path)
                # else:
                #     image_label = self.content_widgets[i]
                #     pixmap = image_label.pixmap()
                #     pixmap.load(content_path)
                # image_label.setPixmap(pixmap)
                # image_label.setAlignment(Qt.AlignCenter)
            else:
                raise Exception

            # self.content_layout.addWidget(image_label)
            # QApplication.processEvents()
        self.scrollarea.force_rescaling = self.scrollarea.resizing = True
        self.scrollarea._rescaleImages(QSize(self.scrollarea.width(), self.scrollarea.height()))
        self.scrollarea._onScroll()
        self.scrollarea._adjustSceneBounds()
        # Clear remaining existing content
        # content_widgets_length = len(self.content_widgets) - 1
        # for j, widget in enumerate(self.content_widgets.copy()[::-1]):
        #     j = content_widgets_length - j
        #     if j > i:
        #         self.content_widgets.pop(j)
        #         self.content_layout.removeWidget(widget)
        #         widget.deleteLater()
        #
        # self.scrollarea.scene.addItem(self.buttons_proxy_widget)
        self.scrollarea.updateScrollBars()

    # Chapter methods
    def threading_wrapper(self, new_thread, blocking, func, args=(), kwargs=None):
        self.threading = True
        progress_dialog = CustomProgressDialog(
            self,
            window_title="Loading ...",
            new_thread=self.provider.use_threading,
            func=func,
            args=args,
            kwargs=kwargs)
        if blocking:
            progress_dialog.exec()
        else:
            progress_dialog.show()

        self.task_successful = progress_dialog.task_successful
        self.threading = False

    def _resolve_pipeline_execution(self) -> list[tuple[PipelineEffectModule, dict[str, _ty.Any]]]:
        resolved_pipeline = []
        mode = self.settings.get_advanced_settings()["misc"].get("pipeline_mode", "sequential")

        incompatible_effects = []

        for step in self.settings.get_advanced_settings()["misc"]["image_processing_pipeline"]:
            print(step)
            effect_id = step.get("id")
            settings = step.get("settings", {})

            module = self.pipeline_effects_loader.verified_modules.get(effect_id)
            if not module:
                incompatible_effects.append(str(effect_id))
                continue

            if mode == "opengl" and not module.gpu_supported:
                incompatible_effects.append(module.effect_name)
                continue
            if mode in {"parallel", "sequential"} and not module.cpu_supported:
                incompatible_effects.append(module.effect_name)
                continue

            resolved_pipeline.append((module, settings))

        if incompatible_effects:
            print("Incompat", incompatible_effects)
            self.button_popup("Incompatible Effects", "Some effects do not support this pipeline mode and were skipped.", "\n".join(incompatible_effects), "Warning")
        return resolved_pipeline

    @staticmethod
    def _resize_to_pixel_count(img: np.ndarray, target_density_per_mpx: int = 1_000_000) -> np.ndarray:
        h, w = img.shape[:2]
        img_area = h * w
        reference_area = 1_000_000  # 1000x1000 region

        desired_pixels = (img_area / reference_area) * target_density_per_mpx
        scale = (desired_pixels / img_area) ** 0.5

        new_w, new_h = int(w * scale), int(h * scale)

        if scale < 1:  # Choose interpolation method
            interpolation = cv2.INTER_AREA  # Downscaling
        elif scale > 1:
            interpolation = cv2.INTER_CUBIC  # Upscaling
        else:
            return img  # No resize needed

        return cv2.resize(img, (max(1, new_w), max(1, new_h)), interpolation=interpolation)

    def apply_transform(self, img: np.ndarray, transform_id: str) -> np.ndarray:
        def gray():
            if len(img.shape) == 2:
                return img  # already grayscale
            return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        match transform_id:
            case "invert":
                if len(img.shape) == 2:
                    return cv2.bitwise_not(img)
                elif img.shape[2] == 4:  # BGRA
                    bgr = img[:, :, :3]
                    alpha = img[:, :, 3:]
                    inverted = cv2.bitwise_not(bgr)
                    return np.concatenate((inverted, alpha), axis=2)
                else:
                    return cv2.bitwise_not(img)
            case "posterize":
                levels = 4  # Change for stronger or subtler effect, but not too many
                factor = 256 // levels
                return ((img // factor) * factor).astype(np.uint8)
            case "color_quantize":
                levels = 10  # Change for stronger or subtler effect, but not too many
                factor = 256 // levels
                return ((img // factor) * factor).astype(np.uint8)


            case "clahe_lab":
                if len(img.shape) == 2 or img.shape[2] != 3:
                    img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
                lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
                l, a, b = cv2.split(lab)
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                l = clahe.apply(l)
                return cv2.cvtColor(cv2.merge((l, a, b)), cv2.COLOR_LAB2BGR)
            case "kmeans_flatten":
                if len(img.shape) == 2 or img.shape[2] != 3:
                    img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
                Z = img.reshape((-1, 3)).astype(np.float32)
                criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
                K = 8
                _, labels, centers = cv2.kmeans(Z, K, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
                centers = np.uint8(centers)
                result = centers[labels.flatten()].reshape(img.shape)
                return result
            case "flatten_fast":
                # Fast color simplification (much faster than K-Means)
                return cv2.pyrMeanShiftFiltering(img, sp=8, sr=16)
            case "bloom":
                blur = cv2.GaussianBlur(img, (0, 0), sigmaX=10, sigmaY=10)
                return cv2.addWeighted(img, 1.0, blur, 0.3, 0)
            case "sharpen":
                # Soft unsharp masking: sharp = original + (original - blur) * amount
                blur = cv2.GaussianBlur(img, (0, 0), sigmaX=1.5)
                sharpened = cv2.addWeighted(img, 1.5, blur, -0.5, 0)
                return sharpened
            case "soft_blur":
                return cv2.GaussianBlur(img, (5, 5), 1.5)
            case "saturation_boost":
                hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
                h, s, v = cv2.split(hsv)
                s = cv2.multiply(s, 1.4)
                s = np.clip(s, 0, 255).astype(np.uint8)
                return cv2.cvtColor(cv2.merge((h, s, v)), cv2.COLOR_HSV2BGR)
            # case "contrast_boost":
            #     lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
            #     l, a, b = cv2.split(lab)
            #     l = cv2.equalizeHist(l)
            #     return cv2.cvtColor(cv2.merge((l, a, b)), cv2.COLOR_LAB2BGR)
            case "toon_shader":
                # Bilateral filter for smooth edges
                smooth = cv2.bilateralFilter(img, d=9, sigmaColor=75, sigmaSpace=75)

                # Convert to grayscale and apply adaptive threshold
                gray = cv2.cvtColor(smooth, cv2.COLOR_BGR2GRAY)
                edges = cv2.adaptiveThreshold(gray, 255,
                                              cv2.ADAPTIVE_THRESH_MEAN_C,
                                              cv2.THRESH_BINARY, 9, 5)

                # Reduce colors (posterize) with median blur
                quantized = cv2.pyrMeanShiftFiltering(smooth, sp=10, sr=30)

                # Combine with edges
                edges_colored = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
                return cv2.bitwise_and(quantized, edges_colored)

            case "light_rays":
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                bright = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)[1]

                kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
                rays = cv2.dilate(bright, kernel, iterations=15)
                rays = cv2.GaussianBlur(rays, (0, 0), sigmaX=15)

                rays_colored = cv2.cvtColor(rays, cv2.COLOR_GRAY2BGR)
                return cv2.addWeighted(img, 1.0, rays_colored, 0.3, 0)
            case "sepia":
                sepia_filter = np.array([[0.272, 0.534, 0.131],
                                         [0.349, 0.686, 0.168],
                                         [0.393, 0.769, 0.189]])
                sepia = cv2.transform(img, sepia_filter)
                return np.clip(sepia, 0, 255).astype(np.uint8)
            case "gamma_correct":
                gamma = 1.4  # < 1.0 for darker, > 1.0 for brighter
                inv_gamma = 1.0 / gamma
                table = np.array([(i / 255.0) ** inv_gamma * 255 for i in range(256)]).astype("uint8")
                return cv2.LUT(img, table)
            # case "lens_distortion":
            #     h, w = img.shape[:2]
            #     K = np.array([[w, 0, w // 2], [0, w, h // 2], [0, 0, 1]], dtype=np.float32)
            #     D = np.array([-0.3, 0.1, 0, 0])  # Distortion coefficients
            #     map1, map2 = cv2.initUndistortRectifyMap(K, D, None, K, (w, h), cv2.CV_32FC1)
            #     return cv2.remap(img, map1, map2, interpolation=cv2.INTER_LINEAR)
            case "pixel_cleanup":
                # Median blur to clean block edges + light bilateral smoothing
                median = cv2.medianBlur(img, 3)
                smooth = cv2.bilateralFilter(median, d=5, sigmaColor=25, sigmaSpace=25)
                return smooth
            case "increase_resolution":
                scale_factor = 2  # You can expose this to the UI
                new_size = (img.shape[1] * scale_factor, img.shape[0] * scale_factor)
                return cv2.resize(img, new_size, interpolation=cv2.INTER_LANCZOS4)
            case "increase_resolution_dl":
                try:
                    from cv2 import dnn_superres
                    model_path = os.path.abspath(os.path.join(f"{config.VERSION}{config.VERSION_ADD}", "models", "FSRCNN_x2.pb"))
                    if not os.path.exists(model_path):
                        raise FileNotFoundError(f"Model not found: {model_path}")
                    scale = 2

                    sr = dnn_superres.DnnSuperResImpl_create()
                    sr.readModel(model_path)
                    sr.setModel("fsrcnn", scale)
                    return sr.upsample(img)
                except Exception as e:
                    print(f"[Error] DL Upscale failed: {e}")
                    return img  # Fallback: return original
            case "adaptive_line_overlay":
                # 1. Convert to grayscale for edge detection
                gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

                # 2. Detect lines (black on white)
                edges = cv2.adaptiveThreshold(gray_img, 255,
                                              cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                              cv2.THRESH_BINARY_INV, 9, 5)

                # 3. Convert to 3-channel
                edges_bgr = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)

                # 4. Draw black lines over original where edges exist
                # Wherever edge == 255 → draw black on top
                result = img.copy()
                result[edges == 255] = [0, 0, 0]

                return result
            case "canny_line_overlay":
                gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                edges = cv2.Canny(gray_img, 100, 200)  # Fast edge detection
                result = img.copy()
                result[edges == 255] = [0, 0, 0]  # Paint lines as black
                return result
            case "color_dodge_overlay":
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                inv = 255 - gray
                blur = cv2.GaussianBlur(inv, (21, 21), 0)
                dodge = cv2.divide(gray, 255 - blur, scale=256)

                # Blend result on top — brighten only light areas
                dodge = cv2.cvtColor(dodge, cv2.COLOR_GRAY2BGR)
                return cv2.addWeighted(img, 0.75, dodge, 0.25, 0)
            case "split_tone":
                if len(img.shape) == 2 or img.shape[2] != 3:
                    img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
                lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
                l, a, b = cv2.split(lab)
                a = cv2.add(a, 10)  # Warmer shadows
                b = cv2.subtract(b, 10)  # Cooler highlights
                return cv2.cvtColor(cv2.merge((l, a, b)), cv2.COLOR_LAB2BGR)
            case "poster_edge":
                # 1. Smooth image
                blur = cv2.medianBlur(img, 5)

                # 2. Grayscale for line detection
                gray = cv2.cvtColor(blur, cv2.COLOR_BGR2GRAY)

                # 3. Detect lines (black on white)
                edges = cv2.adaptiveThreshold(gray, 255,
                                              cv2.ADAPTIVE_THRESH_MEAN_C,
                                              cv2.THRESH_BINARY_INV, 9, 5)

                # 4. Dilate if you want thicker lines
                kernel = np.ones((1, 1), np.uint8)
                edges = cv2.dilate(edges, kernel, iterations=1)

                # 5. Convert to 3-channel and draw black lines on top
                result = blur.copy()
                result[edges == 255] = [0, 0, 0]  # this time for real: black lines

                return result
            case "shrink_50":
                new_size = (img.shape[1] // 2, img.shape[0] // 2)
                return cv2.resize(img, new_size, interpolation=cv2.INTER_AREA)
            case "shrink_25":
                new_size = (img.shape[1] // 4, img.shape[0] // 4)
                return cv2.resize(img, new_size, interpolation=cv2.INTER_AREA)
            case "resize_to_1mp":
                return self._resize_to_pixel_count(img, 1_000_000)
            case "resize_to_2mp":
                return self._resize_to_pixel_count(img, 2_000_000)
            case "resize_to_4mp":
                return self._resize_to_pixel_count(img, 4_000_000)
            case "resize_to_8mp":
                return self._resize_to_pixel_count(img, 8_000_000)
            case "resize_to_12mp":
                return self._resize_to_pixel_count(img, 12_000_000)
            case "resize_to_16mp":
                return self._resize_to_pixel_count(img, 16_000_000)
            case "resize_to_20mp":
                return self._resize_to_pixel_count(img, 20_000_000)
            case "resize_to_24mp":
                return self._resize_to_pixel_count(img, 24_000_000)
            case "resize_to_28mp":
                return self._resize_to_pixel_count(img, 28_000_000)
            case "resize_to_32mp":
                return self._resize_to_pixel_count(img, 32_000_000)
            case "deblock":
                # Use strong bilateral to smooth without killing edges
                return cv2.bilateralFilter(img, d=9, sigmaColor=50, sigmaSpace=75)
            case "denoise":
                return cv2.fastNlMeansDenoisingColored(img, None, h=10, hColor=10, templateWindowSize=7, searchWindowSize=21)
            case "smart_smooth":
                return cv2.edgePreservingFilter(img, flags=1, sigma_s=60, sigma_r=0.4)
        # case "hsv_boost":
            #     hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            #     h, s, v = cv2.split(hsv)
            #     v = cv2.equalizeHist(v)  # or cv2.normalize(v, None, 0, 255, cv2.NORM_MINMAX)
            #     return cv2.cvtColor(cv2.merge((h, s, v)), cv2.COLOR_HSV2BGR)
            # case "ycrcb_boost":
            #     ycrcb = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)
            #     y, cr, cb = cv2.split(ycrcb)
            #     y = cv2.equalizeHist(y)
            #     return cv2.cvtColor(cv2.merge((y, cr, cb)), cv2.COLOR_YCrCb2BGR)
            # case "hls_adjust":
            #     hls = cv2.cvtColor(img, cv2.COLOR_BGR2HLS)
            #     h, l, s = cv2.split(hls)
            #     l = cv2.equalizeHist(l)
            #     return cv2.cvtColor(cv2.merge((h, l, s)), cv2.COLOR_HLS2BGR)
            # Grayscale Variants
            case "adaptive_threshold":
               gray_img = gray()
               return cv2.adaptiveThreshold(gray_img, 255,
                                            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                            cv2.THRESH_BINARY, 11, 2)
            case "threshold_fast":
                gray_img = gray()
                _, th = cv2.threshold(gray_img, 127, 255, cv2.THRESH_BINARY)
                return th
            case "canny_edges":
                gray_img = gray()
                return cv2.Canny(gray_img, 100, 200)
            case "color_dodge":
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                inv = 255 - gray
                blur = cv2.GaussianBlur(inv, (21, 21), 0)
                dodge = cv2.divide(gray, 255 - blur, scale=256)
                return cv2.cvtColor(dodge, cv2.COLOR_GRAY2BGR)
            case "xdog":
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

                # Parameters you can tweak
                k = 4.5  # Ratio between two Gaussian sigmas
                gamma = 0.95  # Weighting factor for second Gaussian
                epsilon = -0.1  # Threshold for edge enhancement
                phi = 10  # Sharpness of tanh

                # Gaussian blurs
                g1 = cv2.GaussianBlur(gray, (0, 0), sigmaX=1)
                g2 = cv2.GaussianBlur(gray, (0, 0), sigmaX=k)

                # XDoG equation
                dog = g1 - gamma * g2
                dog = (dog - dog.min()) / (dog.max() - dog.min())  # Normalize to 0–1
                xdog = np.where(dog >= epsilon, 1.0, 1.0 + np.tanh(phi * (dog - epsilon)))

                return (xdog * 255).astype(np.uint8)
            case "gradient_laplacian":
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

                # Use Laplacian to find edge magnitude
                lap = cv2.Laplacian(gray, cv2.CV_64F, ksize=3)
                lap = cv2.convertScaleAbs(lap)

                # Threshold the laplacian to get strong edges
                _, binary = cv2.threshold(lap, 30, 255, cv2.THRESH_BINARY)

                # Optional: clean up with morphological closing
                kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
                cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

                return cleaned
            case "clahe":
                gray_img = gray()
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                return clahe.apply(gray_img)
            case "luma_contrast":
                gray_img = gray()
                return cv2.equalizeHist(gray_img)
            case "grayscale_luma":
                return gray()
            case "grayscale_average":
                return np.mean(img, axis=2).astype(np.uint8) if len(img.shape) == 3 else img
            case "kuwahara":
                def fast_kuwahara(img, radius=4):
                    if len(img.shape) == 2:
                        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
                    img = img.astype(np.float32)

                    h, w, c = img.shape
                    kernel_size = radius + 1

                    # Precompute integral images for each channel
                    means = []
                    variances = []

                    for dy, dx in [(0, 0), (0, 1), (1, 0), (1, 1)]:
                        y0 = dy * radius
                        x0 = dx * radius

                        region = img[y0:h - radius + y0, x0:w - radius + x0]
                        mean = cv2.boxFilter(region, ddepth=-1, ksize=(kernel_size, kernel_size))
                        sqmean = cv2.boxFilter(region ** 2, ddepth=-1, ksize=(kernel_size, kernel_size))
                        var = sqmean - mean ** 2

                        means.append(mean)
                        variances.append(var.sum(axis=2, keepdims=True))  # Variance across channels

                    # Stack and select region with lowest variance
                    var_stack = np.stack(variances, axis=-1)  # shape: (h', w', 1, 4)
                    mean_stack = np.stack(means, axis=-1)  # shape: (h', w', 3, 4)

                    best_indices = np.argmin(var_stack, axis=-1)[..., None]
                    result = np.take_along_axis(mean_stack, best_indices, axis=3)
                    result = result.squeeze(axis=3).astype(np.uint8)

                    return result

                return fast_kuwahara(img, radius=4)
            case "bilateral_filter_soft":
                return cv2.bilateralFilter(img, d=7, sigmaColor=45, sigmaSpace=45)
            case "bilateral_filter":
                # d: diameter of pixel neighborhood
                # sigmaColor: larger = more color smoothing
                # sigmaSpace: larger = more spatial smoothing
                return cv2.bilateralFilter(img, d=9, sigmaColor=75, sigmaSpace=75)
            case "bilateral_filter_strong":
                return cv2.bilateralFilter(img, d=9, sigmaColor=100, sigmaSpace=100)
            case "unknown_id":
                return img
            case _:
                raise ValueError(f"Unknown transform: {transform_id}")

    def _process_single_image(self, filename: str, input_folder: str, cache_folder: str,
                              pipeline_modules: list[tuple[PipelineEffectModule, dict[str, _ty.Any]]]) -> None:
        try:
            ext = PLPath(filename).suffix.lower()
            filepath = os.path.join(input_folder, filename)
            if ext in {".heic", ".heif", ".gif"}:
                img = iio.imread(filepath)
                img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            else:
                img = cv2.imread(filepath)
            if img is None:
                print(f"[Warning] Could not load: {filename}")
                return

            for module, settings in pipeline_modules:
                preprocessing_funcs = module.get_preprocessing_funcs()
                settings = {
                    k: preprocessing_funcs[k](v) for k, v in settings.items()
                }
                if module.cpu_function:
                    img = module.cpu_function(img, **settings)
                else:
                    print(f"[Warning] Effect {module.effect_id} has no CPU fallback.")

            out_path = os.path.join(cache_folder, filename)
            cv2.imwrite(out_path, img)
        except Exception as e:
            print(f"[Error] Processing {filename}: {e}")
            print(format_exc())

    def process_images(self, cache_folder: str, _: list = None) -> None:
        os.makedirs(cache_folder, exist_ok=True)
        input_folder = cache_folder

        image_files = [
            f for f in os.listdir(input_folder)
            if PLPath(f).suffix.lower() in (".png", ".webp", ".jpg", ".jpeg", ".gif", ".heif", ".heic", ".bmp")
        ]
        if not image_files:
            return

        # Determine pipeline mode and resolve usable modules
        mode = self.settings.get_advanced_settings()["misc"].get("pipeline_mode", "sequential")
        pipeline_modules = self._resolve_pipeline_execution()
        if not pipeline_modules:
            return

        def process_all_images(progress_signal=None):
            start = TimidTimer()
            total = len(image_files)
            try:
                if mode == "parallel" and getattr(self, "provider", None) and getattr(self.provider,
                                                                                      "_shared_request_pool", None):
                    futures = [
                        self.provider._shared_request_pool.pool.submit(
                            self._process_single_image,
                            filename,
                            input_folder,
                            cache_folder,
                            pipeline_modules
                        )
                        for filename in image_files
                    ]
                    for i, future in enumerate(futures):
                        future.result()
                        if progress_signal:
                            progress_signal.emit(100 * ((i + 1) / total))
                        yield
                elif mode == "opengl":
                    yield from run_opengl_pipeline_batch(
                        # self=self,
                        image_files=image_files,
                        input_folder=input_folder,
                        cache_folder=cache_folder,
                        pipeline=pipeline_modules,
                        progress_signal=progress_signal
                    )
                else:  # sequential
                    for i, filename in enumerate(image_files):
                        self._process_single_image(
                            filename,
                            input_folder,
                            cache_folder,
                            pipeline_modules
                        )
                        if progress_signal:
                            progress_signal.emit(100 * ((i + 1) / total))
                        yield
            except Exception as e:
                print(f"[Error] Pipeline failed: {e}")
                print(start.end())
                return False
            print(start.end())
            return True

        progress_dialog = CustomProgressDialog(
            self,
            window_title="Processing Images...",
            new_thread=True,
            func=process_all_images,
            args=(),
            kwargs={}
        )
        progress_dialog.exec()
        if not progress_dialog.task_successful:
            QMessageBox.information(self, "Info", "The processing of the chapter has failed.",
                                    QMessageBox.StandardButton.Ok,
                                    QMessageBox.StandardButton.Ok)

    def run_pipeline(self) -> None:
        scroll_positions = (self.scrollarea.horizontalScrollBar().value(), self.scrollarea.verticalScrollBar().value())
        self.process_images(self.cache_manager.get_cache_folder(self.provider.get_chapter()))
        self.reload_content()
        self.scrollarea.horizontalScrollBar().setValue(scroll_positions[0])
        self.scrollarea.verticalScrollBar().setValue(scroll_positions[1])

    def chapter_loading_wrapper(self, func, cache_folder, fail_info, fail_text):
        self.threading_wrapper(True, True, func, args=(cache_folder, self.settings.get_convert_to_lossless()))

        if self.task_successful:
            self.reload_window_title()
            self.settings.set_chapter(self.provider.get_chapter())
            self.task_successful = False
        else:
            # self.provider.set_chapter(self.settings.get_chapter())
            # self.provider.load_current_chapter()
            # if not 1:
            #     new_chapter = self.provider.get_chapter()
            #     self.gui_changing = True
            #     self.chapter_selector.setText(str(self.settings.get_chapter()))
            #     self.gui_changing = False
            #     self.set_chapter()
            #     if abs(new_chapter - self.settings.get_chapter()) > 1:
            #         self.reload_chapter()
            #     else:
            #         [lambda: None, self.retract_cache, self.advance_cache][int((new_chapter - self.settings.get_chapter()) // self.settings.get_chapter_rate())]()
            # else:
            self.reload_window_title()
            self.settings.set_chapter(self.provider.get_chapter())
            QMessageBox.information(self, fail_info, fail_text,
                                    QMessageBox.StandardButton.Ok,
                                    QMessageBox.StandardButton.Ok)
        # self.gui_changing = True
        self.chapter_selector.setText(str(self.settings.get_chapter()))
        # self.gui_changing = False
        print("Reloading images ...")
        self.process_images(cache_folder, self.settings.get_advanced_settings().get("misc", {}).get("image_processing_pipeline", []))
        self.scrollarea.verticalScrollBar().setValue(0)
        self.scrollarea.horizontalScrollBar().setValue((self.scrollarea.width() // 2))
        self.reload_content()
        self.save_last_title(self.provider.register_provider_name, self.provider.get_title(), self.settings.get_chapter())
        if self.settings.get_advanced_settings().get("misc", {}).get("auto_export", False):
            if self.library_edit.current_library()[1] == "":
                QMessageBox.warning(self, "No library selected", "Please select a library to enable \nthe transfer of chapters.")
                return
            elif self.provider.register_saver is not None:
                return  # So we don't save the same chapter over and over, destroying it's quality
            elif self.transferring:
                return
            chapter = self.settings.get_chapter()

            args = (
                self.provider,
                chapter,
                f"Chapter {chapter}",
                self.cache_manager.get_cache_folder(chapter),
                self.settings.get_advanced_settings()["misc"]["quality_preset"]
            )
            kwargs = {}
            task = self.task_bar.add_task(name=f"Transferring Ch {chapter}", func=self.saver.save_chapter, args=args, kwargs=kwargs)
            task.task_done.connect(lambda t: (
                print("Transfer Task: ", t.task_successful),
                QMessageBox.information(self, "Info",
                                        "Transferring of the chapter has failed!\nLook in the logs for more info.",
                                        QMessageBox.StandardButton.Ok,
                                        QMessageBox.StandardButton.Ok) if not t.task_successful else None
            ))

    def next_chapter(self) -> None:
        self.provider.increase_chapter(self.settings.get_chapter_rate())
        cache_folder: str = self.cache_manager.get_cache_folder(self.provider.get_chapter())
        if not self.cache_manager.is_cache_loaded(cache_folder):
            self.chapter_loading_wrapper(self.provider.load_current_chapter, cache_folder, "Info | Loading of the chapter has failed!",
                                         "Maybe this chapter doesn't exist?\nIf that isn't the case, look in the logs for more info.")
        else:
            self.reload_window_title()
            self.settings.set_chapter(self.provider.get_chapter())
            self.task_successful = False
            # self.gui_changing = True
            self.chapter_selector.setText(str(self.settings.get_chapter()))
            # self.gui_changing = False
            self.save_last_title(self.provider.__class__.__name__.removesuffix("Provider"), self.provider.get_title(), self.settings.get_chapter())
            print("Reloading images ...")
            self.scrollarea.verticalScrollBar().setValue(0)
            self.scrollarea.horizontalScrollBar().setValue((self.scrollarea.width() // 2))
            self.reload_content()
        self.cache_manager.ensure_less_than(self.settings.get_advanced_settings().get("misc", {}).get("max_cached_chapters", -1), self.provider.get_chapter())

    def previous_chapter(self) -> None:
        if self.provider.get_chapter() - self.settings.get_chapter_rate() < 0:
            return
        self.provider.increase_chapter(-self.settings.get_chapter_rate())
        cache_folder: str = self.cache_manager.get_cache_folder(self.provider.get_chapter())
        if not self.cache_manager.is_cache_loaded(cache_folder):
            self.chapter_loading_wrapper(self.provider.load_current_chapter, cache_folder, "Info | Loading of the chapter has failed!",
                                         "Maybe this chapter doesn't exist?\nIf that isn't the case, look in the logs for more info.")
        else:
            self.reload_window_title()
            self.settings.set_chapter(self.provider.get_chapter())
            self.task_successful = False
            # self.gui_changing = True
            self.chapter_selector.setText(str(self.settings.get_chapter()))
            # self.gui_changing = False
            self.save_last_title(self.provider.__class__.__name__.removesuffix("Provider"), self.provider.get_title(), self.settings.get_chapter())
            print("Reloading images ...")
            self.scrollarea.verticalScrollBar().setValue(0)
            self.scrollarea.horizontalScrollBar().setValue((self.scrollarea.width() // 2))
            self.reload_content()
        self.cache_manager.ensure_less_than(self.settings.get_advanced_settings().get("misc", {}).get("max_cached_chapters", -1), self.provider.get_chapter())

    def ensure_loaded_chapter(self) -> None:
        cache_folder: str = self.cache_manager.get_cache_folder(self.provider.get_chapter())
        if not self.cache_manager.is_cache_loaded(cache_folder):
            self.chapter_loading_wrapper(self.provider.load_current_chapter, cache_folder, "Info | Reloading of the chapter has failed",
                                         "Maybe this chapter doesn't exist?\nIf that isn't the case, look in the logs for more info.")
        else:
            self.reload_window_title()
            self.settings.set_chapter(self.provider.get_chapter())
            self.task_successful = False
            # self.gui_changing = True
            self.chapter_selector.setText(str(self.settings.get_chapter()))
            # self.gui_changing = False
            self.save_last_title(self.provider.__class__.__name__.removesuffix("Provider"), self.provider.get_title(), self.settings.get_chapter())
            print("Reloading images ...")
            self.scrollarea.verticalScrollBar().setValue(0)
            self.scrollarea.horizontalScrollBar().setValue((self.scrollarea.width() // 2))
            self.reload_content()
        self.cache_manager.ensure_less_than(self.settings.get_advanced_settings().get("misc", {}).get("max_cached_chapters", -1), self.provider.get_chapter())

    def reload_chapter(self) -> None:
        self.wait_for_tasks()  # Current chapter could be task, so we wait to be sure
        cache_folder = self.cache_manager.get_cache_folder(self.provider.get_chapter())
        self.cache_manager.clear_cache(cache_folder)
        os.makedirs(cache_folder)
        self.chapter_loading_wrapper(self.provider.load_current_chapter, cache_folder, "Info | Reloading of chapter has failed",
                                     "Maybe this chapter doesn't exist?\nIf that isn't the case, look in the logs for more info.")
        self.cache_manager.ensure_less_than(self.settings.get_advanced_settings().get("misc", {}).get("max_cached_chapters", -1), self.provider.get_chapter())

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
        self.scrollarea._onScroll()

    def closeEvent(self, event):
        global playwright_instance
        self.wait_for_tasks()
        self.provider.local_cleanup()
        self.provider.cleanup()  # Final cleanup
        if playwright_instance is not None:
            playwright_instance.stop()
            playwright_instance = None
        can_exit = True
        if can_exit:
            print("Exiting ...")
            self.save_settings()
            self.scrollarea.thread_pool.shutdown()
            # sys.stdout.close()
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
            self.buttons_widget.setStyleSheet(theme.stylesheet)
            self.prev_button.setStyleSheet(theme.stylesheet)
            self.next_button.setStyleSheet(theme.stylesheet)
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
                self.reload_chapter_button.setIcon(QIcon(f"{self.data_folder}/assets/reload_chapter_icon_dark.png"))
                self.reload_content_button.setIcon(QIcon(f"{self.data_folder}/assets/reload_icon_dark.png"))
            else:
                self.reload_chapter_button.setIcon(QIcon(f"{self.data_folder}/assets/reload_chapter_icon_light.png"))
                self.reload_content_button.setIcon(QIcon(f"{self.data_folder}/assets/reload_icon_light.png"))
        self.theme = icon_theme_color
        self.scrollarea.graphics_view.resetCachedContent()

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
        if random.randint(0, 20) == 0:
            os_theme = (self.system.get_windows_theme() or os.environ.get("MV_THEME")).lower()
            if os_theme != self.os_theme:
                self.update_theme(os_theme)


if __name__ == "__main__":
    print(f"Starting {config.PROGRAM_NAME} {str(config.VERSION) + config.VERSION_ADD} with py{'.'.join([str(x) for x in sys.version_info])} ...")
    CODES: dict[int, _a.Callable[[], None]] = {
        1000: lambda: os.execv(sys.executable, [sys.executable] + sys.argv[1:])  # RESTART_CODE (only works compiled)
    }
    qapp: QApplication | None = None
    # qgui: MainWindow | None = None
    dp_app: MainWindow | None = None
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
        # qgui = MainWindow(qapp)
        dp_app = MainWindow(qapp, input_path, logging_level)  # Shows gui
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
            dp_app.close()
        # if qgui is not None:
        #     qgui.close()
        if qapp is not None:
            instance = qapp.instance()
            if instance is not None:
                instance.quit()
        results: str = diagnose_shutdown_blockers(return_result=True)
        CODES.get(current_exit_code, lambda: sys.exit(current_exit_code))()

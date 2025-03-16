# Copyright adalfarus 2025
import config  # Configures python environment before anything else is done

from PySide6.QtWidgets import (QApplication, QLabel, QVBoxLayout, QWidget, QMainWindow, QCheckBox, QHBoxLayout,
                               QScroller, QSpinBox, QPushButton, QGraphicsOpacityEffect, QScrollerProperties, QFrame,
                               QComboBox, QFormLayout, QLineEdit, QMessageBox, QScrollBar, QGraphicsProxyWidget)
from PySide6.QtGui import QDesktopServices, QPixmap, QIcon, QDoubleValidator, QFont, QImage
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QRect, QUrl, QSize
# from PySide6.QtMultimediaWidgets import QVideoWidget
# from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtGui import QColor

from modules.AutoProviderPlugin import AutoProviderPlugin, AutoProviderBaseLike, AutoProviderBaseLike2
from modules.Classes import (CustomProgressDialog, ImageLabel, SearchWidget, AdvancedQMessageBox,
                             CustomComboBox, Settings, TargetContainer, VerticalManagement, AutoProviderManager,
                             AdvancedSettingsDialog)
from modules.themes import Themes

# Apt stuff ( update to newer version )
from oaplustools.io.loggers import monitor_stdout
from oaplustools.data.updaters import VersionNumber
from oaplustools.io.environment import System
from oaplustools import set_dir_to_ex

from urllib.parse import urlparse
import requests
import sqlite3
import random
import shutil
import json
import math
import time
import sys
import os

import multiprocessing
import stdlib_list
multiprocessing.freeze_support()
hiddenimports = list(stdlib_list.stdlib_list())

# old_dir = os.getcwd()
set_dir_to_ex()
os.chdir(os.path.join(os.getcwd(), './_internal'))


class MainWindow(QMainWindow):
    def __init__(self, app):
        super().__init__()
        self.app = app

        self.data_folder = os.path.abspath('./data').strip("/")
        self.cache_folder = os.path.abspath('./cache').strip("/")
        self.modules_folder = os.path.abspath('./modules').strip("/")
        self.extensions_folder = os.path.abspath('./extensions').strip("/")

        self.logger = monitor_stdout(f"{self.data_folder}/logs.txt")

        self.system = System()

        self.setWindowTitle("Super Manhwa Viewer 170")
        self.setWindowIcon(QIcon(f"{self.data_folder}/Untitled-1-noBackground.png"))

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
        self.update_theme(self.os_theme.lower())

        # Advanced setup
        self.provider_dict = self.provider = None
        self.provider_combobox.currentIndexChanged.disconnect()
        self.reload_providers()
        self.switch_provider(self.settings.get_provider())
        self.provider_combobox.currentIndexChanged.connect(self.change_provider)

        self.reload_window_title()

        # Scaling stuff
        self.content_paths = self.get_content_paths()
        self.task_successful = False
        self.threading = False

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
        else:
            print("Bug, please fix me.")

    def setup_gui(self):
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

        # Content widgets
        # content_widget = QWidget()
        # self.scrollarea.setWidget(content_widget)
        # self.content_layout = self.scrollarea.content_layout  # QVBoxLayout(content_widget)

        # Enable kinetic scrolling
        scroller = QScroller.scroller(self.scrollarea.graphics_view.viewport())
        scroller.grabGesture(self.scrollarea.graphics_view.viewport(), QScroller.ScrollerGestureType.TouchGesture)
        scroller_properties = QScrollerProperties(scroller.scrollerProperties())
        scroller_properties.setScrollMetric(QScrollerProperties.ScrollMetric.MaximumVelocity, 0.3)
        scroller.setScrollerProperties(scroller_properties)

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
        self.title_selector.textChanged.connect(self.set_title)
        self.chapter_selector.textChanged.connect(self.set_chapter)
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
        # self.content_layout.setSpacing(0)
        # self.content_layout.setContentsMargins(0, 0, 0, 0)
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

    def toggle_save_last_titles_checkbox(self):
        self.settings.set_save_last_titles(self.save_last_titles_checkbox.isChecked())

    def advanced_settings(self):
        settings = self.settings.get_advanced_settings()
        default_settings = json.loads(self.settings.get_default_setting("advanced_settings"))
        self.settings.close()
        available_themes = tuple(key for key in Themes.__dict__.keys() if not (key.startswith("__") or key.endswith("__")))
        dialog = AdvancedSettingsDialog(parent=self, current_settings=settings, default_settings=default_settings, master=self, available_themes=available_themes)
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

            if settings["misc"]["num_workers"] != dialog.selected_settings["misc"]["num_workers"]:
                self.switch_provider(self.provider_combobox.currentText())
            if (settings["themes"]["light"] != dialog.selected_settings["themes"]["light"]
                    or settings["themes"]["dark"] != dialog.selected_settings["themes"]["dark"]):
                self.save_settings()
                self.set_theme()
                # result = QMessageBox.question(self, "Restart Client?",
                #                               "You must restart the client for the theme changes to take effect.\nDo you wish to continue?",
                #                               QMessageBox.StandardButtons(QMessageBox.Yes | QMessageBox.No),
                #                               QMessageBox.Yes)
                # if result == QMessageBox.Yes:
                #     print("Exiting ...")
                #     self.save_settings()
                #     sys.stdout.close()
                #     self.settings.close()
                #     QApplication.exit(1000)

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

    def export_settings(self):
        sett = self.settings.get_advanced_settings()
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

        self.provider = provider_cls(self.settings.get_title(), self.settings.get_chapter(),
                                     self.settings.get_chapter_rate(), self.data_folder, self.cache_folder,
                                     self.settings.get_provider_type(), num_workers=self.settings.get_advanced_settings()["misc"]["num_workers"])
        self.provider.set_blacklisted_websites(self.settings.get_blacklisted_websites())

        if self.provider.get_search_results(None):
            self.search_widget.set_search_results_func(self.provider.get_search_results)
            self.search_widget.setEnabled(True)  # self.search_toggle_button.setEnabled(False)
        else:
            self.search_widget.setEnabled(False)  # self.search_toggle_button.setEnabled(False)

        new_pixmap = QPixmap(os.path.abspath(self.provider.get_logo_path()))
        self.transparent_image.setPixmap(new_pixmap)
        self.update_provider_logo()

    def reload_window_title(self):
        new_title = ' '.join(word[0].upper() + word[1:] if word else '' for word in self.provider.get_title().split())
        self.setWindowTitle(f'SMV 170 | {new_title}, Chapter {self.provider.get_chapter()}')

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
        self.scrollarea.management.downscaling = self.downscale_checkbox.isChecked()
        self.scrollarea.force_rescaling = True
        self.scrollarea._rescaleImages(QSize(self.scrollarea.width(), self.scrollarea.height()))
        self.scrollarea.graphics_view.resetCachedContent()

    def upscale_checkbox_toggled(self):
        self.settings.set_upscaling(self.upscale_checkbox.isChecked())
        self.scrollarea.management.upscaling = self.upscale_checkbox.isChecked()
        self.scrollarea.force_rescaling = True
        self.scrollarea._rescaleImages(QSize(self.scrollarea.width(), self.scrollarea.height()))
        self.scrollarea.graphics_view.resetCachedContent()

    def lazy_loading_toggled(self) -> None:
        self.settings.set_lazy_loading(self.lazy_loading_checkbox.isChecked())
        self.scrollarea.management.lazy_loading = self.lazy_loading_checkbox.isChecked()
        self.scrollarea._onScroll()

    def apply_manual_content_width(self):
        self.settings.set_manual_content_width(self.manual_width_spinbox.value())
        self.scrollarea.management.base_width = self.manual_width_spinbox.value()
        self.scrollarea.force_rescaling = True
        self.scrollarea._rescaleImages(QSize(self.scrollarea.width(), self.scrollarea.height()))
        self.scrollarea.graphics_view.resetCachedContent()

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
            self.chapter_selector.setText("0")

    def set_chapter_rate(self):
        new_chapter_rate = float("0" + self.chapter_rate_selector.text())
        if 0.1 <= new_chapter_rate <= 2.0:
            self.settings.set_chapter_rate(new_chapter_rate)
            self.provider.set_chapter_rate(new_chapter_rate)
            self.chapter_rate_selector.setText(str(new_chapter_rate))
        else:
            self.settings.set_chapter_rate(0.1)
            self.provider.set_chapter_rate(0.1)
            self.chapter_rate_selector.setText("0.1")

    def update_sensitivity(self, value):
        sensitivity = value / 10
        self.settings.set_scrolling_sensitivity(sensitivity)
        self.sensitivity_label.setText(f"Current Sensitivity: {sensitivity:.1f}")
        self.scrollarea.graphics_view.sensitivity = sensitivity

    def selected_chosen_result(self, new_title, toggle_search_bar: bool = True):
        self.title_selector.setText(new_title)
        self.title_selector.textChanged.emit(new_title)
        self.chapter_selector.setText("1")
        self.chapter_selector.textChanged.emit("1")
        self.settings.set_chapter(1)
        self.reload_chapter()
        if toggle_search_bar:
            self.toggle_search_bar()
        self.save_last_title(self.provider.get_title())

    def save_last_title(self, title):
        if self.settings.get_save_last_titles():
            sett = self.settings.get_advanced_settings()
            title = title.lower()
            print(title)
            if title in sett["recent_titles"]:
                sett["recent_titles"].remove(title)
            sett["recent_titles"].append(title)
            self.settings.set_advanced_settings(sett)

    def change_provider_type(self):
        self.settings.set_provider_type(self.provider_type_combobox.currentText().lower())
        self.provider.set_provider_type(self.settings.get_provider_type())

    def blacklist_current_url(self):
        blk_urls = self.provider.get_blacklisted_websites() + [urlparse(self.provider.get_current_url()).netloc]
        self.provider.set_blacklisted_websites(blk_urls)
        self.settings.set_blacklisted_websites(self.provider.get_blacklisted_websites())

    def change_provider(self, *args, callback: bool = False):
        if not callback:
            self.previous_provider = self.provider
        self.switch_provider(self.provider_combobox.currentText())
        if not callback:
            QTimer.singleShot(50, self.change_provider_callback)

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
        max_size = self.width() // 3
        min_size = self.width() // 10
        content_width = self.transparent_image.pixmap().width() if self.transparent_image.pixmap() else 0  # Adjust the size of the transparent image based on window width
        if not min_size <= content_width <= max_size:  # If the current image width is outside the min and max size range, resize it
            scaled_pixmap = QPixmap(os.path.abspath(self.provider.get_logo_path())).scaledToWidth(max_size, Qt.SmoothTransformation)
            self.transparent_image.setPixmap(scaled_pixmap)
        self.transparent_image.setFixedSize(max_size, max_size)

    # Rest
    def reload_providers(self):
        provider_manager = AutoProviderManager(self.extensions_folder, AutoProviderPlugin, [
                        AutoProviderPlugin, AutoProviderBaseLike, AutoProviderBaseLike2])
        self.provider_dict = provider_manager.get_providers()

        self.provider_combobox.clear()

        for i, provider_name in enumerate(self.provider_dict.keys()):
            provider = self.provider_dict[provider_name]("", 1, 0.5, self.data_folder, self.cache_folder, "direct")

            icon_path = provider.get_logo_path()
            image = QImage(os.path.abspath(icon_path))

            if provider.clipping_space is not None:
                start_x, start_y, end_x, end_y = provider.clipping_space

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
        self.provider_combobox.setCurrentText(self.settings.get_provider())
        self.title_selector.setText(self.settings.get_title())
        self.chapter_selector.setText(str(self.settings.get_chapter()))
        self.chapter_rate_selector.setText(str(self.settings.get_chapter_rate()))
        self.provider_type_combobox.setCurrentText(self.settings.get_provider_type().title())

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
    def threading_wrapper(self, new_thread, blocking, func, *args, **kwargs):
        self.threading = True
        progress_dialog = CustomProgressDialog(
            self,
            window_title="Loading ...",
            window_icon=f"{self.data_folder}/Untitled-1-noBackground.png",
            new_thread=new_thread,
            func=func,
            *args,
            **kwargs)
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
            self.save_last_title(self.provider.get_title())
        else:
            self.provider.set_chapter(self.settings.get_chapter())
            self.provider.reload_chapter()
            QMessageBox.information(self, fail_info, fail_text,
                                    QMessageBox.StandardButton.Ok,
                                    QMessageBox.StandardButton.Ok)
        self.chapter_selector.setText(str(self.settings.get_chapter()))
        print("Reloading images ...")
        self.scrollarea.verticalScrollBar().setValue(0)
        self.scrollarea.horizontalScrollBar().setValue((self.scrollarea.width() // 2))
        self.reload_content()

    def next_chapter(self):
        self.chapter_loading_wrapper(self.provider.next_chapter, "Info | Loading of chapter has failed!",
                                     "The loading of the next chapter has failed.\nLook in the logs for more info.")

    def previous_chapter(self):
        self.chapter_loading_wrapper(self.provider.previous_chapter, "Info | Loading of chapter has failed!",
                                     "The loading of the previous chapter has failed.\nLook in the logs for more info.")

    def reload_chapter(self):
        self.chapter_loading_wrapper(self.provider.reload_chapter, "Info | Reloading of chapter has failed",
                                     "The reloading the current chapter has failed.\nLook in the logs for more info.")

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
        can_exit = True
        if can_exit:
            print("Exiting ...")
            self.save_settings()
            self.scrollarea.thread_pool.shutdown()
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
                self.reload_chapter_button.setIcon(QIcon(f"{self.data_folder}/reload_chapter_icon_dark.png"))
                self.reload_content_button.setIcon(QIcon(f"{self.data_folder}/reload_icon_dark.png"))
            else:
                self.reload_chapter_button.setIcon(QIcon(f"{self.data_folder}/reload_chapter_icon_light.png"))
                self.reload_content_button.setIcon(QIcon(f"{self.data_folder}/reload_icon_light.png"))
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
    app = QApplication(sys.argv)
    # RESTART_CODE = 1000
    window = MainWindow(app=app)
    window.show()
    current_exit_code = app.exec()
    sys.exit(current_exit_code)
    # if current_exit_code == RESTART_CODE:
    #     os.chdir(old_dir)
    #     os.execv(sys.executable, [sys.executable] + sys.argv)  # os.execv(sys.executable, ['python'] + sys.argv)

"""TBA"""
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QMainWindow, QCheckBox, QMessageBox, QPushButton

# Standard typing imports for aps
import collections.abc as _a
import typing as _ty
import types as _ts

from aplustools.io.qtquick import QQuickMessageBox


class MainWindow(QMainWindow):
    some_signal = Signal()

    def __init__(self) -> None:
        super().__init__(parent=None)

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

        self.provider_combobox = QComboBox()
        provider_layout = QHBoxLayout()
        provider_layout.addWidget(QLabel("Provider:"))
        provider_layout.addWidget(self.provider_combobox)
        side_menu_layout.addRow(provider_layout)

        self.saver_combobox = QComboBox()
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

        # self.provider_type_combobox = QComboBox(self)
        # self.provider_type_combobox.addItem("Indirect", 0)
        # self.provider_type_combobox.addItem("Direct", 1)
        # self.provider_type_combobox.setCurrentText("Direct")
        # self.provider_type_combobox.setEnabled(False)
        # side_menu_layout.addRow(self.provider_type_combobox, QLabel("Provider Type"))
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
        self.reload_chapter_button = QPushButton(QIcon(f"{self.data_folder}/empty.png"), "")
        self.reload_content_button = QPushButton(QIcon(f"{self.data_folder}/empty.png"), "")

        side_menu_buttons_layout = QHBoxLayout()
        side_menu_buttons_layout.addWidget(previous_chapter_button_side_menu)
        side_menu_buttons_layout.addWidget(next_chapter_button_side_menu)
        side_menu_buttons_layout.addWidget(self.reload_chapter_button)
        side_menu_buttons_layout.addWidget(self.reload_content_button)
        side_menu_layout.addRow(side_menu_buttons_layout)

        self.show_provider_logo_checkbox = QCheckBox("Provider Logo")
        search_all_button = QPushButton("Search all")
        another_layout = QHBoxLayout()
        another_layout.setContentsMargins(0, 0, 0, 0)
        another_layout.addWidget(self.show_provider_logo_checkbox)
        another_layout.addWidget(search_all_button)

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
        # transfer_chapter_s_button.setEnabled(False)
        advanced_settings_button = QPushButton("Adv Settings")
        side_menu_layout.addRow(self.transfer_chapter_s_button, advanced_settings_button)

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
        self.show_provider_logo_checkbox.checkStateChanged.connect(self.set_show_provider_logo)
        self.title_selector.textChanged.connect(self.set_title)
        self.chapter_selector.textChanged.connect(self.set_chapter)
        # self.library_line_edit.textChanged.connect(self.set_library_path)
        self.library_edit.currentTextChanged.connect(self.change_library)
        self.library_edit.remove_library.connect(lambda item: (
            self.settings.set_libraries(self.settings.get_libraries().remove(item)),
            self.settings.set_current_lib_idx(self.library_edit.currentIndex())
        ))
        self.library_edit.set_library_name.connect(self.set_library_name)
        self.chapter_rate_selector.textChanged.connect(self.set_chapter_rate)
        self.chapter_selector.textChanged.connect(lambda: self.reset_caches() if not self.gui_changing else "")  # So we don't have faulty caches
        self.chapter_rate_selector.textChanged.connect(lambda: self.reset_caches() if not self.gui_changing else "")  # So we don't have faulty caches
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
        # Rest
        self.provider_combobox.currentIndexChanged.connect(self.change_provider)  # Menu
        self.saver_combobox.currentIndexChanged.connect(self.change_saver)  # Menu
        # self.provider_type_combobox.currentIndexChanged.connect(self.change_provider_type)
        self.side_menu_animation.valueChanged.connect(self.side_menu_animation_value_changed)  # Menu
        timer.timeout.connect(self.timer_tick)
        self.search_bar_animation.valueChanged.connect(self.search_bar_animation_value_changed)
        self.search_widget.selectedItem.connect(self.selected_chosen_result)
        self.scroll_sensitivity_scroll_bar.valueChanged.connect(self.update_sensitivity)
        search_all_button.clicked.connect(self.search_all)

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
        # search_all_button.setEnabled(False)
        # self.save_last_titles_checkbox.setEnabled(False)
        # export_settings_button.setEnabled(False)
        # advanced_settings_button.setEnabled(False)

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
        for provider_name, provider_cls in self.known_working_searchers:
            provider = provider_cls("", 0, "", self.cache_folder, self.data_folder)
            duped_provider_search_funcs.append(_create_lambda(provider_name, provider.get_search_results, "1", (0, 2)))
            providers.append(provider)

        self.search_widget.search_results_func = lambda text: sum([func(text) for func in duped_provider_search_funcs], start=[])
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
            if abs(self.settings.get_chapter() - old_chapter) > 1:
                self.chapter_selector.setText(str(old_chapter))
                # self.reset_cache()
                # self.reload_content()
                self.reload_chapter()
            else:
                self.gui_changing = True
                self.chapter_selector.setText(str(old_chapter))
                self.gui_changing = False
                [lambda: None, self.retract_cache, self.advance_cache][int((self.settings.get_chapter() - old_chapter) // self.settings.get_chapter_rate())]()
                self.reload_content()
            self.settings.set_chapter(old_chapter)
        self.transferring = False

    def select_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            self.library_edit.add_library_item(os.path.basename(folder), folder)
            self.settings.set_libraries(self.settings.get_libraries() + [(os.path.basename(folder), folder)])
            self.settings.set_current_lib_idx(self.library_edit.currentIndex())

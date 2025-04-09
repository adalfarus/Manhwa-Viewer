"""TBA"""
from PySide6.QtWidgets import (QListWidget, QDialog, QStyledItemDelegate, QComboBox, QGroupBox, QVBoxLayout,
                               QFormLayout,
                               QFontComboBox, QLabel, QLineEdit, QToolButton, QHBoxLayout, QRadioButton, QPushButton,
                               QCheckBox, QSpinBox, QDialogButtonBox, QListWidgetItem, QWidget, QFileDialog, QMenu,
                               QStyleOptionComboBox, QStyle, QDoubleSpinBox, QProgressBar, QSizePolicy, QMessageBox,
                               QTextEdit, QLayout, QLayoutItem, QScrollArea, QFrame, QSlider, QColorDialog)
from PySide6.QtCore import QPropertyAnimation, QEasingCurve, QByteArray, Qt, QTimer, Signal, QPoint, QSize, QRect
from PySide6.QtGui import QWheelEvent, QFont, QPaintEvent, QPainter, QFontMetrics, QShowEvent

from .tasks import CustomProgressDialog

import sqlite3
import shutil
import json
import os

from ..pipeline_plugin.gui import NoGui, ColorPicker, Combobox, Spinbox, Slider, Checkbox, Input, KeyboardInput, \
    VectorInput, Widget

# Standard typing imports for aps
from abc import abstractmethod, ABCMeta
import collections.abc as _a
import typing as _ty
import types as _ts

from ..pipeline_plugin.loader import PipelineEffectModule


class QFlowLayout(QLayout):  # Not by me
    """
    A custom flow layout class that arranges child widgets horizontally and wraps as needed.
    """

    def __init__(self, parent=None, margin=0, hSpacing=6, vSpacing=6):
        super().__init__(parent)
        self.setContentsMargins(margin, margin, margin, margin)
        self.hSpacing = hSpacing
        self.vSpacing = vSpacing
        self.items = []

    def addItem(self, item):
        self.items.append(item)

    def horizontalSpacing(self) -> int:
        return self.hSpacing

    def verticalSpacing(self) -> int:
        return self.vSpacing

    def count(self) -> int:
        return len(self.items)

    def itemAt(self, index) -> QLayoutItem:
        if 0 <= index < len(self.items):
            return self.items[index]
        return None

    def takeAt(self, index) -> QLayoutItem:
        if 0 <= index < len(self.items):
            return self.items.pop(index)
        return None

    def expandingDirections(self) -> Qt.Orientations:
        return Qt.Horizontal | Qt.Vertical

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        return self.doLayout(QRect(0, 0, width, 0), testOnly=True)

    def setGeometry(self, rect: QRect):
        super().setGeometry(rect)
        self.doLayout(rect, testOnly=False)

    def expandingDirections(self) -> Qt.Orientations:
        """Prevents unnecessary expansion by keeping the layout compact."""
        return Qt.Orientation(0)  # Prevents expanding horizontally/vertically

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        """Calculate the layout height based on the available width."""
        return self.doLayout(QRect(0, 0, width, 0), testOnly=True)

    def sizeHint(self) -> QSize:
        """Return the preferred size of the layout."""
        return self.calculateSize()

    def minimumSize(self) -> QSize:
        """Return the minimum size of the layout."""
        return self.calculateSize()

    def calculateSize(self) -> QSize:
        size = QSize()
        for item in self.items:
            size = size.expandedTo(item.minimumSize())
        size += QSize(2 * self.contentsMargins().top(), 2 * self.contentsMargins().top())
        return size

    def doLayout(self, rect: QRect, testOnly: bool) -> int:
        x, y, lineHeight = rect.x(), rect.y(), 0

        for item in self.items:
            wid = item.widget()
            spaceX, spaceY = self.horizontalSpacing(), self.verticalSpacing()
            nextX = x + item.sizeHint().width() + spaceX
            if nextX - spaceX > rect.right() and lineHeight > 0:
                x = rect.x()
                y += lineHeight + spaceY
                nextX = x + item.sizeHint().width() + spaceX
                lineHeight = 0

            if not testOnly:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            x = nextX
            lineHeight = max(lineHeight, item.sizeHint().height())

        return y + lineHeight - rect.y()


class PillFrame(QFrame):
    doubleClickEvent = Signal()
    def mouseDoubleClickEvent(self, event, /):
        self.doubleClickEvent.emit()
        super().mouseDoubleClickEvent(event)


class QLabelSelector(QWidget):
    pill_added_signal = Signal(tuple)  # tuple idx label
    pill_removed_signal = Signal(int)  # idx
    pill_doubleclicked = Signal(int)  # idx

    def __init__(self, parent: QWidget | None = None, position_label_bar_at_top: bool = False) -> None:
        super().__init__(parent=parent)
        self._available_labels: list[str] = []

        main_layout = QVBoxLayout(self)
        # Top: Available labels
        self.label_bar = QFlowLayout()
        label_bar_scroll = QScrollArea()
        label_bar_scroll.setWidgetResizable(True)
        label_bar_scroll.setFrameShape(QFrame.Shape.NoFrame)
        label_bar_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        label_bar_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        # label_bar_scroll.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
        label_bar_content = QWidget()
        label_bar_content.setLayout(self.label_bar)
        label_bar_scroll.setWidget(label_bar_content)
        if position_label_bar_at_top:
            main_layout.addWidget(label_bar_scroll)

        # Scrollable flow layout
        pill_scroll = QScrollArea()
        pill_scroll.setWidgetResizable(True)
        pill_scroll.setFrameShape(QFrame.Shape.NoFrame)
        pill_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        pill_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        # pill_scroll.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.MinimumExpanding)

        pill_content = QWidget()
        self.pill_layout = QFlowLayout()
        pill_content.setLayout(self.pill_layout)
        pill_scroll.setWidget(pill_content)
        main_layout.addWidget(pill_scroll)
        if not position_label_bar_at_top:
            main_layout.addWidget(label_bar_scroll)

        self._pills: list[PillFrame] = []

    def set_available_labels(self, labels: list[str]) -> None:
        self._available_labels = labels
        while self.label_bar.count():  # Clear current buttons
            item = self.label_bar.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
        for name in labels:  # Add new ones
            btn = QPushButton(name)
            btn.clicked.connect(lambda _, n=name: self._add_pill(n))
            self.label_bar.addWidget(btn)

    def _remove_pill(self, tag_frame: PillFrame) -> None:
        tag_frame.setParent(None)
        tag_frame.deleteLater()
        pill_idx: int = self._pills.index(tag_frame)
        self._pills.pop(pill_idx)
        self.pill_removed_signal.emit(pill_idx)
        # self.pill_added_signal.emit(self.get_current_pills())

    def _add_pill(self, name: str) -> None:
        tag_label = QLabel(name)
        tag_xbutton = QPushButton("✕")
        tag_layout = QHBoxLayout()
        tag_layout.setContentsMargins(3, 3, 3, 3)
        tag_layout.addWidget(tag_label)
        tag_layout.addWidget(tag_xbutton)
        tag_frame = PillFrame()
        tag_frame.setFrameShape(QFrame.Shape.StyledPanel)
        # tag_frame.setStyleSheet("background-color: #d0d0d0; border-radius: 6px;")
        tag_frame.setLayout(tag_layout)
        tag_frame.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.MinimumExpanding)

        tag_frame.doubleClickEvent.connect(lambda: self.pill_doubleclicked.emit(self._pills.index(tag_frame)))
        tag_xbutton.clicked.connect(lambda: self._remove_pill(tag_frame))
        self.pill_layout.addWidget(tag_frame)
        idx = len(self._pills)
        self._pills.append(tag_frame)
        self.pill_added_signal.emit((idx, name))  # self.get_current_pills()

    def change_pill_label(self, pill_idx: int, new_label: str) -> None:
        maybe_label = self._pills[pill_idx].findChild(QLabel)
        if maybe_label:
            maybe_label.setText(new_label)

    def get_current_pills(self) -> list[str]:
        raise NotImplementedError
        pills: list[str] = []
        for widget in self._pills:
            label = widget.findChild(QLabel)
            if label:
                pills.append(label.text())
        return pills

    def set_current_pills(self, pills: list[str]) -> None:
        valid_pills = pills  # [p for p in pills if p in self._available_labels]
        while self.pill_layout.count():  # Clear current
            item = self.pill_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
        for name in valid_pills:  # Add new ones
            self._add_pill(name)


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


class SmartSlider(QSlider):
    scaledValueChanged = Signal(object)

    def __init__(self, widget_def, value):
        super().__init__(Qt.Orientation.Horizontal)

        self._step = widget_def.step
        self._type = widget_def.type

        if self._type == float:
            # Calculate scaling factor to convert float range to int range
            self._scale = 1 / self._step

            self.setMinimum(int(widget_def.min * self._scale))
            self.setMaximum(int(widget_def.max * self._scale))
            self.setValue(int(value * self._scale))
        else:
            self._scale = 1
            self.setMinimum(int(widget_def.min))
            self.setMaximum(int(widget_def.max))
            self.setValue(int(value))

        self.setSingleStep(1)
        self.setProperty("step_size", self._step)
        self.setProperty("value_type", self._type)
        self.valueChanged.connect(self._emit_scaled)

    def _emit_scaled(self, _):
        self.scaledValueChanged.emit(self.value())

    def value(self):
        raw = super().value()
        return raw / self._scale if self._type == float else raw

    def setValue(self, val):
        if self._type == float:
            super().setValue(int(val * self._scale))
        else:
            super().setValue(int(val))


class SmartTextEdit(QTextEdit):
    """
    A smart text edit that automatically adjusts it's size
    """

    def __init__(self, max_height: int = 100, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.max_height: int = max_height
        self.textChanged.connect(self._adjustHeight)

    def _adjustHeight(self) -> None:
        """
        Adjusts the height of the text edit
        """
        doc_height: float = self.document().size().height()
        if doc_height > self.max_height:
            self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            self.setFixedHeight(self.max_height)
        else:
            self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self.setFixedHeight(int(doc_height))

    def showEvent(self, event: QShowEvent) -> None:
        """
        QTextEdit show event
        """
        super().showEvent(event)
        self._adjustHeight()

    def text(self) -> str:
        """
        Returns the plaintext of the text edit
        """
        return self.toPlainText()

    def setText(self, text: str, /) -> None:
        self.setPlainText(text)


class QVectorInput(QWidget):
    valueChanged = Signal(list)  # Emits [x, y, z, ...] when any changes

    def __init__(self, dims=3, labels=True, type_=float, min_=None, max_=None, step=0.1, parent=None):
        super().__init__(parent)
        self.dims = dims
        self.spinboxes = []
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        axis_labels = ["X", "Y", "Z", "W"]
        SpinBox = QDoubleSpinBox if type_ == float else QSpinBox

        for i in range(dims):
            if labels:
                self.layout.addWidget(QLabel(axis_labels[i]))
            sb = SpinBox()
            if min_ is not None: sb.setMinimum(min_)
            if max_ is not None: sb.setMaximum(max_)
            sb.setSingleStep(step)
            sb.valueChanged.connect(self.emit_value)
            self.spinboxes.append(sb)
            self.layout.addWidget(sb)

    def emit_value(self):
        self.valueChanged.emit([sb.value() for sb in self.spinboxes])

    def set_value(self, values):
        for i, val in enumerate(values):
            self.spinboxes[i].setValue(val)

    def get_value(self):
        return [sb.value() for sb in self.spinboxes]


class PipelineEffectSettingsDialog(QDialog):
    def __init__(self, effect_module: PipelineEffectModule, current_settings: dict[str, _ty.Any], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(effect_module.effect_name + " Settings")
        self.setModal(True)

        self.inputs = effect_module.register_gui_inputs
        self.widgets: dict[str, QWidget] = {}

        layout = QVBoxLayout()
        form_layout = QFormLayout()

        for key, input_obj in self.inputs.items():
            label = QLabel(input_obj.label)
            widget = self._build_widget(input_obj, current_settings.get(key, input_obj.default), key, label, effect_module)
            self.widgets[key] = widget
            if isinstance(widget, QWidget):
                if label.text() != "":
                    form_layout.addRow(label, widget)
                else:
                    form_layout.addRow(widget)

        effect_module.gui_update_function(self.widgets)
        layout.addLayout(form_layout)
        layout.addWidget(self._build_buttons())
        self.setLayout(layout)

    def _build_widget(self, input_obj: Input, value: _ty.Any, key: str, label: QLabel, module: PipelineEffectModule) -> QWidget | Widget | None:
        widget_def = input_obj.widget
        if isinstance(widget_def, Checkbox):
            box: QCheckBox = QCheckBox(widget_def.label)
            box.setChecked(bool(value))
            box.checkStateChanged.connect(lambda _: module.gui_update_function(self.widgets))
            return box
        elif isinstance(widget_def, Slider):
            slider = SmartSlider(widget_def, value)
            slider.setValue(value)
            slider.scaledValueChanged.connect(lambda val: label.setText(input_obj.label.format(n=val)))
            slider.scaledValueChanged.emit(slider.value())
            slider.scaledValueChanged.connect(lambda _: module.gui_update_function(self.widgets))
            return slider
        elif isinstance(widget_def, Spinbox):
            spinbox: QSpinBox | QDoubleSpinBox
            if widget_def.type == int:
                spinbox = QSpinBox()
                spinbox.setMinimum(int(widget_def.min))
                spinbox.setMaximum(int(widget_def.max))
                spinbox.setSingleStep(int(widget_def.step))
                spinbox.setValue(int(value))
                spinbox.valueChanged.connect(lambda _: module.gui_update_function(self.widgets))
                return spinbox
            else:
                spinbox = QDoubleSpinBox()
                spinbox.setMinimum(float(widget_def.min))
                spinbox.setMaximum(float(widget_def.max))
                spinbox.setSingleStep(float(widget_def.step))
                spinbox.setValue(float(value))
                spinbox.valueChanged.connect(lambda _: module.gui_update_function(self.widgets))
                return spinbox
        elif isinstance(widget_def, Combobox):
            combo = QComboBox()
            reverse = {v: k for k, v in widget_def.options.items()}
            for name, val in widget_def.options.items():
                combo.addItem(name, userData=val)
            default_text = reverse.get(value, list(widget_def.options.keys())[0])
            combo.setCurrentText(default_text)
            combo.currentIndexChanged.connect(lambda _: module.gui_update_function(self.widgets))
            return combo
        elif isinstance(widget_def, ColorPicker):
            btn = QPushButton("Pick Color")
            btn.setProperty("color_value", value)
            btn.setProperty("gui_update_func", module.gui_update_function)
            btn.setStyleSheet(f"background-color: rgb({value[0] * 255}, {value[1] * 255}, {value[2] * 255});")
            btn.clicked.connect(lambda: self._choose_color(btn, key))
            return btn
        elif isinstance(widget_def, NoGui):
            widget_def.set_value(value)
            return widget_def
        elif isinstance(widget_def, KeyboardInput):
            edit: SmartTextEdit | QLineEdit
            widget_def: KeyboardInput
            if widget_def.multiline:
                edit = SmartTextEdit()
            else:
                edit = QLineEdit()
            edit.setPlaceholderText(widget_def.placeholder)
            edit.setText(value)
            edit.textChanged.connect(lambda x: edit.setText(widget_def.validation_func(x)))
            edit.textChanged.connect(lambda _: module.gui_update_function(self.widgets))
            return edit
        elif isinstance(widget_def, VectorInput):
            widget = QVectorInput(
                dims=widget_def.dims,
                labels=widget_def.labels,
                type_=widget_def.type,
                min_=widget_def.min,
                max_=widget_def.max,
                step=widget_def.step,
            )

            if isinstance(value, (list, tuple)):
                widget.set_value(value)

            # Optional: connect valueChanged to update the label
            def update_label(vec):
                formatted = ", ".join(f"{v:.2f}" for v in vec)
                label.setText(input_obj.label.format(n=formatted))

            widget.valueChanged.connect(update_label)
            update_label(widget.get_value())
            widget.valueChanged.connect(lambda _: module.gui_update_function(self.widgets))
            return widget
        return None

    def _choose_color(self, btn: QPushButton, key: str):
        current_rgb = self.widgets[key].palette().button().color()
        color = QColorDialog.getColor(current_rgb, self, "Choose Tint Color")

        if color.isValid():
            self.widgets[key].setStyleSheet(f"background-color: {color.name()};")
            rgb = (color.redF(), color.greenF(), color.blueF())
            self.widgets[key].setProperty("color_value", rgb)
            self.widgets[key].property("gui_update_func")(self.widgets)

    def _build_buttons(self) -> QDialogButtonBox:
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        return btns

    def get_updated_settings(self) -> dict[str, _ty.Any]:
        result = {}
        for key, widget in self.widgets.items():
            if isinstance(widget, QPushButton):
                result[key] = widget.property("color_value") or (1.0, 0.0, 0.0)
            elif isinstance(widget, QSlider):
                # step = widget.property("step_size") or 1
                # typ = widget.property("value_type") or int
                result[key] = widget.value()
            elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
                result[key] = widget.value()
            elif isinstance(widget, QComboBox):
                result[key] = widget.currentData()
            elif isinstance(widget, (SmartTextEdit, QLineEdit)):
                result[key] = widget.text()
            elif isinstance(widget, QVectorInput):
                result[key] = widget.get_value()
            elif isinstance(widget, NoGui):
                result[key] = widget.get_value()
            elif isinstance(widget, QCheckBox):
                result[key] = int(widget.isChecked())
            else:
                raise RuntimeError(f"Unknown widget type {widget}")
        return result


class AdvancedSettingsDialog(QDialog):
    def __init__(self, parent: QWidget | None = None, current_settings: dict | None = None, default_settings: dict | None = None,
                 master=None, available_themes=None, export_settings_func=None) -> None:
        super().__init__(parent, Qt.WindowType.WindowCloseButtonHint | Qt.WindowType.WindowTitleHint)
        if default_settings is None:
            self.default_settings = {"recent_titles": [],
                                     "themes": {"light": "light_light", "dark": "dark", "font": "Segoe UI"},
                                     "settings_file_path": "",
                                     "settings_file_mode": "overwrite",
                                     "misc": {"auto_export": False, "quality_preset": "quality", "max_cached_chapters": -1,
                                              "pipeline_mode": "parallel", "image_processing_pipeline": [],
                                              "use_opengl_scene_renderer": False}}
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
        self.setMinimumWidth(800)

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
        # self.fileHandlingGroupBox = QGroupBox("Settings File Handling", self)
        # self.fileHandlingLayout = QVBoxLayout(self.fileHandlingGroupBox)
        # self.fileLocationLineEdit = QLineEdit(self.fileHandlingGroupBox)
        # self.fileLocationLineEdit.setPlaceholderText("File Location")
        # self.fileLocationToolButton = QToolButton(self.fileHandlingGroupBox)
        # self.fileLocationToolButton.setText("...")
        # self.fileLocationToolButton.clicked.connect(self.get_file_location)
        # self.fileLocationLayout = QHBoxLayout()
        # self.fileLocationLayout.addWidget(self.fileLocationLineEdit)
        # self.fileLocationLayout.addWidget(self.fileLocationToolButton)
        # self.overwriteRadioButton = QRadioButton("Overwrite", self.fileHandlingGroupBox)
        # self.modifyRadioButton = QRadioButton("Modify", self.fileHandlingGroupBox)
        # self.createNewRadioButton = QRadioButton("Create New", self.fileHandlingGroupBox)
        # self.overwriteRadioButton.setChecked(True)
        # self.exportSettingsPushButton = QPushButton("Export Settings-file")
        # self.exportSettingsPushButton.clicked.connect(self.export_settings)
        # # self.exportSettingsPushButton.setEnabled(False)
        # self.loadSettingsPushButton = QPushButton("Load Settings-file")
        # self.loadSettingsPushButton.clicked.connect(self.load_settings_file)
        # last_layout = QHBoxLayout()
        # last_layout.setContentsMargins(0, 0, 0, 0)
        # last_layout.addWidget(self.createNewRadioButton)
        # last_layout.addStretch()
        # last_layout.addWidget(self.exportSettingsPushButton)
        # last_layout.addWidget(self.loadSettingsPushButton)
        # self.fileHandlingLayout.addLayout(self.fileLocationLayout)
        # self.fileHandlingLayout.addWidget(self.overwriteRadioButton)
        # self.fileHandlingLayout.addWidget(self.modifyRadioButton)
        # self.fileHandlingLayout.addLayout(last_layout)
        # self.mainLayout.addWidget(self.fileHandlingGroupBox)

        # Auto-Export and Workers
        self.miscSettingsGroupBox = QGroupBox("Chapter Settings", self)
        self.miscSettingsLayout = QFormLayout(self.miscSettingsGroupBox)
        self.autoExportCheckBox = QCheckBox("Enable Auto-Transfer", self.miscSettingsGroupBox)
        # self.autoExportCheckBox.setEnabled(False)
        # self.workersSpinBox = QSpinBox(self.miscSettingsGroupBox)
        # self.workersSpinBox.setRange(1, 20)
        # self.workersSpinBox.setValue(10)
        # self.workersSpinBox.setEnabled(False)
        self.quality_combo = QComboBox(self.miscSettingsGroupBox)
        self.quality_combo.addItems([
            "Maximum Quality",
            "High Quality",
            "Quality",
            "Size",
            "Smaller Size",
            "Smallest Size",
            "Fast Read",            # Optimized for decoding speed (even if larger file)
            "Archival",             # Long-term storage with full data integrity
        ])
        quality_layout = QHBoxLayout()
        quality_layout.setContentsMargins(0, 0, 0, 0)
        quality_layout.addWidget(QLabel("Auto-Transfer Quality preset:"))
        quality_layout.addWidget(self.quality_combo)
        quality_frame = QFrame()
        quality_frame.setLayout(quality_layout)
        quality_frame.setFrameShape(QFrame.Shape.NoFrame)

        self.max_cached_chapters_spinbox = QSpinBox(self.miscSettingsGroupBox, minimum=-1, singleStep=1)
        chapters_layout = QHBoxLayout()
        chapters_layout.setContentsMargins(0, 0, 0, 0)
        chapters_layout.addWidget(QLabel("Max cached chapters:"))
        chapters_layout.addWidget(self.max_cached_chapters_spinbox)
        chapters_frame = QFrame()
        chapters_frame.setLayout(chapters_layout)
        chapters_frame.setFrameShape(QFrame.Shape.NoFrame)

        self.miscSettingsLayout.addRow(self.autoExportCheckBox)
        # self.miscSettingsLayout.addRow(QLabel("Number of Workers:"), self.workersSpinBox)
        self.miscSettingsLayout.addRow(quality_frame, chapters_frame)
        self.miscSettingsLayout.addRow(self.autoExportCheckBox)

        self.image_processing_pipeline = QLabelSelector(self.miscSettingsGroupBox)
        image_proc_layout = QVBoxLayout()
        image_proc_layout.setContentsMargins(0, 0, 0, 0)
        image_proc_layout.addWidget(QLabel("Image processing pipeline"))
        image_proc_layout.addWidget(self.image_processing_pipeline)
        self.image_processing_pipeline.pill_added_signal.connect(self.add_pipeline_effect)
        self.image_processing_pipeline.pill_removed_signal.connect(self.remove_pipeline_effect)
        self.image_processing_pipeline.pill_doubleclicked.connect(self.show_pipeline_effect_gui)

        self.miscSettingsLayout.addRow(image_proc_layout)

        self.pipeline_modes_label_to_id = {
            "Sequential (Avoids thrashing)": "sequential",
            "Parallel (if possible)": "parallel",
            "OpenGL Shaders": "opengl"
        }
        self.pipeline_modes_id_to_label = {v: k for k, v in self.pipeline_modes_label_to_id.items()}
        self.pipeline_mode_combobox = QComboBox()
        self.pipeline_mode_combobox.addItems(tuple(self.pipeline_modes_label_to_id.keys()))

        self.miscSettingsLayout.addRow(self.pipeline_mode_combobox)
        self.use_opengl_render = QCheckBox("Use OpenGL Scene-Renderer")
        self.miscSettingsLayout.addRow(self.use_opengl_render)

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

    def format_pill_label(self, settings: dict[str, _ty.Any], module) -> str:
        to_format: str = module.effect_name_format
        formats: dict[str, _ty.Any] = {}
        for name, definition in module.register_gui_inputs.items():
            widget_def = definition.widget
            if isinstance(widget_def, Combobox):
                reverse = {v: k for k, v in widget_def.options.items()}
                value = reverse[settings.get(name, None)]
            elif isinstance(widget_def, ColorPicker):
                value = tuple(round(x, 2) for x in settings.get(name, None))
            else:
                value = settings.get(name, None)
            formats[name] = value
        return to_format.format(**formats)

    def add_pipeline_effect(self, effect: tuple[int, str]) -> None:
        effect_idx, effect_name = effect
        effect_id = self.image_proc_label_to_id.get(effect_name, "unknown_id")
        if effect_id == "unknown_id":
            default_settings = {}
        else:
            module = self.verified_modules[effect_id]
            default_settings = module.get_default_settings()
            self.image_processing_pipeline.change_pill_label(effect_idx, self.format_pill_label(default_settings, module))
        self.current_image_proc_pipeline.append(
            {
                "id": effect_id,
                "settings": default_settings
            }
        )

    def add_pipeline_effect_label(self, effect: tuple[int, str]) -> None:
        effect_idx, effect_name = effect
        effect_id = self.image_proc_label_to_id.get(effect_name, "unknown_id")
        if effect_id != "unknown_id":
            module = self.verified_modules[effect_id]
            settings = self.current_image_proc_pipeline[effect_idx].get("settings")
            self.image_processing_pipeline.change_pill_label(effect_idx, self.format_pill_label(settings, module))

    def remove_pipeline_effect(self, idx: int) -> None:
        self.current_image_proc_pipeline.pop(idx)

    def show_pipeline_effect_gui(self, pipeline_effect_idx: int) -> None:
        pipeline_effect = self.current_image_proc_pipeline[pipeline_effect_idx]
        pipeline_effect_settings = pipeline_effect.get("settings", {})
        # effect_id = pipeline_effect["effect_id"]
        pipeline_effect_module = self.verified_modules.get(pipeline_effect.get("id"), None)
        if pipeline_effect_module is None:
            pipeline_effect_module = PipelineEffectModule("unknown_id",
            type("unknown_id", (), {  # type: ignore
                "effect_name": "Unknown ID",
                "effect_name_format": "Unknown ID",
                "effect_id": "unknown_id",
                "supports_cpu": False,
                "supports_opengl": False,
                "register_gui_inputs": {},
                "vertex_shader_src": "",
                "fragment_shader_src": "",
                "update_gui": lambda _: None,
                "apply_transform_cpu": None
            }), "")

        dlg = PipelineEffectSettingsDialog(
            effect_module=pipeline_effect_module,
            current_settings=pipeline_effect_settings,
            parent=self
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            updated = dlg.get_updated_settings()
            pipeline_effect["settings"] = updated
            self.image_processing_pipeline.change_pill_label(pipeline_effect_idx, self.format_pill_label(updated, pipeline_effect_module))

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
            # "settings_file_path": self.fileLocationLineEdit.text(),
            # "settings_file_mode": "overwrite" if self.overwriteRadioButton.isChecked() else "modify" if self.modifyRadioButton.isChecked() else "create_new",
            "misc": {"auto_export": self.autoExportCheckBox.isChecked(), "quality_preset": self.quality_combo.currentText().lower().replace(" ", "_"),
                     "max_cached_chapters": self.max_cached_chapters_spinbox.value(), "pipeline_mode": self.pipeline_modes_label_to_id[self.pipeline_mode_combobox.currentText()],
                     "image_processing_pipeline": self.current_image_proc_pipeline.copy(), "use_opengl_scene_renderer": self.use_opengl_render.isChecked()}})
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

        # self.fileLocationLineEdit.setText(settings.get("settings_file_path", ""))
        #
        # sett_mode = settings.get("settings_file_mode")
        # if sett_mode == "overwrite":
        #     self.overwriteRadioButton.setChecked(True)
        #     self.modifyRadioButton.setChecked(False)
        #     self.createNewRadioButton.setChecked(False)
        # elif sett_mode == "modify":
        #     self.overwriteRadioButton.setChecked(False)
        #     self.modifyRadioButton.setChecked(True)
        #     self.createNewRadioButton.setChecked(False)
        # else:
        #     self.overwriteRadioButton.setChecked(False)
        #     self.modifyRadioButton.setChecked(False)
        #     self.createNewRadioButton.setChecked(True)

        self.autoExportCheckBox.setChecked(settings.get("misc").get("auto_export") is True)
        # self.workersSpinBox.setValue(settings.get("misc").get("num_workers"))
        self.quality_combo.setCurrentText(settings.get("misc").get("quality_preset").replace("_", " ").title())


        self.image_proc_label_to_id1 = {
            # Color
            "Color: Bloom / Glow": "bloom",
            "Color: Light Rays": "light_rays",
            "Color: Split Tone": "split_tone",
            "Color: Saturation Boost": "saturation_boost",
            "Color: CLAHE + LAB (Enhanced Lightness)": "clahe_lab",
            "Color: Flatten (K-Means)": "kmeans_flatten",
            "Color: Flatten (Fast)": "flatten_fast",
            # Stylize
            "Stylize: Toon Shader": "toon_shader",
            "Stylize: Poster Edge": "poster_edge",
            "Stylize: Posterize Colors": "posterize",
            "Stylize: Kuwahara Filter": "kuwahara",
            "Stylize: Color Quantize (Flat Colors)": "color_quantize",
            "Stylize: Sepia Tone (Vintage)": "sepia",
            # Lines
            # "Lens Distortion": "lens_distortion",
            "Stylize: Adaptive Line Overlay": "adaptive_line_overlay",
            "Stylize: Line Overlay (Canny)": "canny_line_overlay",
            "Stylize: Color Dodge Line Overlay": "canny_line_overlay",
            # B/W
            "B/W: Luma": "grayscale_luma",
            "B/W: CLAHE (Local Contrast)": "clahe",
            # "B/W: Luma + Contrast Boost": "luma_contrast",
            "B/W: Average": "grayscale_average",
            "B/W: Adaptive Threshold (Line Art)": "adaptive_threshold",
            "B/W: Threshold (Fast)": "threshold_fast",
            "B/W: Edge Detection (Canny)": "canny_edges",
            "B/W: Color Dodge (Pencil Highlight)": "color_dodge",
            # Fixes
            "Fix: Increase Resolution (2x)": "increase_resolution",
            "Fix: AI-upscaling (2x)": "increase_resolution_dl",
            "Fix: Resize to 1MP": "resize_to_1mp",
            "Fix: Resize to 2MP": "resize_to_2mp",
            "Fix: Resize to 4MP": "resize_to_4mp",
            "Fix: Resize to 8MP": "resize_to_8mp",
            "Fix: Resize to 12MP": "resize_to_12mp",
            "Fix: Resize to 16MP": "resize_to_16mp",
            "Fix: Resize to 20MP": "resize_to_20mp",
            "Fix: Resize to 24MP": "resize_to_24mp",
            "Fix: Resize to 28MP": "resize_to_28mp",
            "Fix: Resize to 32MP": "resize_to_32mp",
            "Fix: Shrink 50%": "shrink_50",
            "Fix: Shrink 25%": "shrink_25",
            "Fix: Invert Colors": "invert",
            "Fix: Sharpen": "sharpen",
            "Fix: Bilateral Filter (Soft Denoise)": "bilateral_filter_soft",
            "Fix: Bilateral Filter (Denoise)": "bilateral_filter",
            "Fix: Bilateral Filter (Strong Denoise)": "bilateral_filter_strong",
            "Fix: Soft Blur": "soft_blur",
            "Fix: Pixel Cleanup (Low-Res Art)": "pixel_cleanup",
            "Fix: De-Block (Compression Repair)": "deblock",
            "Fix: Denoise (Grain Cleanup)": "denoise",
            "Fix: Smart Smooth (Contour Blur)": "smart_smooth",
            "Fix: Gamma Correction (Brighten)": "gamma_correct",

            # "LAB (Perceptual Color)": "lab",
            # "Contrast Boost": "contrast_boost",
            # "HSV": "hsv",
            # "YCrCb": "ycrcb",
            # "HLS": "hls",
            # "HSV (Boost Value)": "hsv_boost",
            # "YCrCb (Contrast Boost)": "ycrcb_boost",
            # "HLS (Tone Adjust)": "hls_adjust",
            # "B/W: Max-Min (Desat)": "grayscale_maxmin",
            # "B/W: Red": "grayscale_red",
            # "B/W: Green": "grayscale_green",
            # "B/W: Blue": "grayscale_blue",
            "Unknown ID": "unknown_id"
        }
        self.verified_modules = self.master.pipeline_effects_loader.verified_modules
        self.image_proc_label_to_id = {"Unknown ID": "unknown_id"}
        self.image_proc_label_to_id.update(**{item.effect_name: item.effect_id for item in list(self.verified_modules.values())})
        self.image_proc_id_to_label = {v: k for k, v in self.image_proc_label_to_id.items()}
        lst = list(self.image_proc_label_to_id.keys())
        lst.remove("Unknown ID")
        self.image_processing_pipeline.set_available_labels(lst)
        self.current_image_proc_pipeline = settings.get("misc").get("image_processing_pipeline")
        self.image_processing_pipeline.pill_added_signal.disconnect(self.add_pipeline_effect)
        self.image_processing_pipeline.pill_added_signal.connect(self.add_pipeline_effect_label)
        self.image_processing_pipeline.set_current_pills([self.image_proc_id_to_label.get(x.get("id"), "Unknown ID") for x in self.current_image_proc_pipeline])
        self.image_processing_pipeline.pill_added_signal.disconnect(self.add_pipeline_effect_label)
        self.image_processing_pipeline.pill_added_signal.connect(self.add_pipeline_effect)

        self.pipeline_mode_combobox.setCurrentText(self.pipeline_modes_id_to_label[settings.get("misc").get("pipeline_mode")])
        self.use_opengl_render.setChecked(settings.get("misc").get("use_opengl_scene_renderer"))
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
            # "settings_file_path": self.fileLocationLineEdit.text(),
            # "settings_file_mode": "overwrite" if self.overwriteRadioButton.isChecked() else "modify" if self.modifyRadioButton.isChecked() else "create_new",
            "misc": {"auto_export": self.autoExportCheckBox.isChecked(), "quality_preset": self.quality_combo.currentText().lower().replace(" ", "_"),
                     "max_cached_chapters": self.max_cached_chapters_spinbox.value(), "pipeline_mode": self.pipeline_modes_label_to_id[self.pipeline_mode_combobox.currentText()],
                     "image_processing_pipeline": self.current_image_proc_pipeline.copy(), "use_opengl_scene_renderer": self.use_opengl_render.isChecked()}}
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

    def setCurrentIndex(self, index, /):
        super().setCurrentIndex(index)

    def setCurrentText(self, text, /):
        super().setCurrentText(text)


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
            "Maximum Quality",
            "High Quality",
            "Quality",
            "Size",
            "Smaller Size",
            "Smallest Size",
            "Fast Read",            # Optimized for decoding speed (even if larger file)
            "Archival",             # Long-term storage with full data integrity
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

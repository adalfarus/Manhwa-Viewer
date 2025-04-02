"""TBA"""
from PySide6.QtWidgets import (QWidget, QHBoxLayout, QLabel, QVBoxLayout, QLineEdit, QPushButton, QListWidget,
                               QSizePolicy, QListWidgetItem)
from PySide6.QtCore import Signal, QSize, Qt
from PySide6.QtGui import QPixmap, QFont, QIcon

import os

# Standard typing imports for aps
from abc import abstractmethod, ABCMeta
import collections.abc as _a
import typing as _ty
import types as _ts


class SearchResultItem(QWidget):
    def __init__(self, title: str, description: str, icon_path: str) -> None:
        super().__init__()

        self.main_layout = QHBoxLayout(self)

        self.icon_label = QLabel(self)
        self.icon_label.setPixmap(QPixmap(icon_path).scaledToWidth(50, Qt.TransformationMode.SmoothTransformation))
        self.main_layout.addWidget(self.icon_label)

        self.text_layout = QVBoxLayout()
        self.title_label = QLabel(title)
        self.title_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.text_layout.addWidget(self.title_label)

        self.description_label = QLabel(description)
        self.description_label.setFont(QFont("Arial", 10))
        self.text_layout.addWidget(self.description_label)

        self.main_layout.addLayout(self.text_layout)


class SearchWidget(QWidget):
    selectedItem = Signal(str)

    def __init__(self, search_results_func: _ty.Callable[[str], list[tuple[str, str]]]):
        super().__init__()
        self.initUI()
        self.search_results_func: _ty.Callable[[str], list[tuple[str, str]]] = search_results_func

    def set_search_results_func(self, new_func: _ty.Callable[[str], list[tuple[str, str]]]) -> None:
        self.search_results_func = new_func

    def sizeHint(self) -> QSize:
        search_bar_size_hint = self.search_bar.sizeHint()
        if self.results_list.isVisible():
            results_list_size_hint = self.results_list.sizeHint()
            # Combine the heights and take the maximum width
            combined_height = search_bar_size_hint.height() + results_list_size_hint.height()
            combined_width = max(search_bar_size_hint.width(), results_list_size_hint.width())
            return QSize(combined_width, combined_height)
        else:
            return search_bar_size_hint  # Return size hint of search_bar

    def minimumSizeHint(self) -> QSize:
        return self.search_bar.minimumSizeHint()

    def initUI(self) -> None:
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

    def on_text_finished(self) -> None:
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

    def on_return_pressed(self) -> None:
        item = self.results_list.currentItem() or self.results_list.item(0)
        if item:
            self.select_item(item)

    def on_item_activated(self, item: QListWidgetItem) -> None:
        self.select_item(item)

    def select_item(self, item: QListWidgetItem) -> None:
        title = item.text()
        print(f'Selected: {title}')
        self.search_bar.setText('')
        self.results_list.hide()
        self.selectedItem.emit(title)

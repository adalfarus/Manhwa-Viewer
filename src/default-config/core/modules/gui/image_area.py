"""TBA"""
from PySide6.QtWidgets import (QWidget, QGraphicsProxyWidget, QGraphicsItem, QGraphicsPixmapItem, QSizePolicy,
                               QStyleOptionGraphicsItem, QGraphicsView, QScrollBar, QGraphicsScene)
from PySide6.QtCore import QObject, Signal, Qt, QRectF, QPropertyAnimation, QByteArray, QEasingCurve, QSize, QTimer
from PySide6.QtGui import (QPixmap, QPainter, QPen, QFont, QTextOption, QTransform, QWheelEvent, QResizeEvent,
                           QImageReader, QImage, QColor)

from PySide6.QtOpenGLWidgets import QOpenGLWidget

from aplustools.io.qtquick import QNoSpacingBoxLayout, QBoxDirection
from aplustools.io.concurrency import LazyDynamicThreadPoolExecutor

import cv2

import math
import os

# Standard typing imports for aps
from abc import abstractmethod, ABCMeta
import collections.abc as _a
import typing as _ty
import types as _ts


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
            reader = QImageReader(self._abs_pixmap_path)
            reader.setAutoTransform(True)

            max_dim = QSize(15000, 15000)
            size = reader.size()
            if size.width() > max_dim.width() or size.height() > max_dim.height():
                scaled_size = size.scaled(max_dim, Qt.AspectRatioMode.KeepAspectRatio)
                reader.setScaledSize(scaled_size)

            img = reader.read()
            self._original_pixmap = QPixmap.fromImage(img)

            if self._original_pixmap.isNull():
                img = cv2.imread(self._abs_pixmap_path)
                if img is not None:
                    h, w, ch = img.shape
                    bytes_per_line = ch * w
                    qimg = QImage(img.data, w, h, bytes_per_line, QImage.Format.Format_BGR888)
                    self._original_pixmap = QPixmap.fromImage(qimg)
                if self._original_pixmap.isNull():
                    red_image = QImage(512, 512, QImage.Format.Format_RGB32)
                    red_image.fill(QColor("red"))
                    self._original_pixmap = QPixmap.fromImage(red_image)
                    print("First load not possible")
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
        image.first_load()  # target.thread_pool.submit(image.first_load)
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

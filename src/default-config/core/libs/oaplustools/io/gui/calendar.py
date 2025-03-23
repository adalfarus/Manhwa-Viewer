import datetime

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QLabel, QFrame,
                               QPushButton, QListWidget, QScrollArea, QMessageBox, QWidgetAction, 
                               QMenu, QGraphicsDropShadowEffect, QLayout, QLayoutItem)
from PySide6.QtCore import (QPropertyAnimation, QDate, Signal, QTime, QDateTime, Qt, QRect, QSize, QPoint, QObject,
                            QTimeZone)
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QPen, QMouseEvent, QAction
from math import floor
from typing import List, Dict, Union, Tuple, Optional
import hashlib


import warnings
warnings.warn("This module is new and not usable yet. Please use oaplustools.web.webtools instead till release 1.5.0",
              UserWarning,
              stacklevel=2)


class QMoment:
    def __init__(self, date: Union[QDate, str], time: Union[QTime, str], tz: Union[QTimeZone, str, None] = None):
        self.datetime = QDateTime()

        self.set_date(date)
        self.set_time(time)
        self.set_timezone(tz if tz is not None else QTimeZone.utc())

    @staticmethod
    def from_datetime(datetime: QDateTime) -> 'QMoment':
        return QMoment(datetime.date(), datetime.time(), datetime.timeZone())

    @staticmethod
    def fromString(string: str) -> 'QMoment':
        # Assuming the string format includes timezone abbreviation at the end
        datetime = QDateTime.fromString(string[:-4], "yyyy.MM.dd HH:mm:ss")  # Exclude timezone abbreviation
        timezone = QTimeZone(string[-3:].encode())  # Get the timezone abbreviation
        datetime.setTimeZone(timezone)
        return QMoment.from_datetime(datetime)

    def toString(self) -> str:
        timezone = self.datetime.timeZone()
        timezoneAbbreviation = timezone.abbreviation(self.datetime)
        return self.datetime.toString("yyyy.MM.dd HH:mm:ss") + " " + timezoneAbbreviation

    def get_date(self) -> QDate:
        return self.datetime.date()

    def get_time(self) -> QTime:
        return self.datetime.time()

    def get_timezone(self) -> QTimeZone:
        return self.datetime.timeZone()

    def set_date(self, new_date: Union[QDate, str], refresh: bool = True):
        if isinstance(new_date, str):
            new_date = QDate.fromString(new_date, "yyyy.MM.dd")
        elif not isinstance(new_date, QDate):
            raise TypeError(f"Cannot convert {type(new_date)} to QDate.")
        if refresh:
            self.datetime.setDate(new_date)

    def set_time(self, new_time: Union[QTime, str], refresh: bool = True):
        if isinstance(new_time, str):
            new_time = QTime.fromString(new_time, "HH:mm")
        elif not isinstance(new_time, QTime):
            raise TypeError(f"Cannot convert {type(new_time)} to QTime.")
        if refresh:
            self.datetime.setTime(new_time)

    def set_timezone(self, tz: Union[QTimeZone, str], refresh: bool = True):
        if isinstance(tz, str):
            tz = QTimeZone(tz.encode())
        elif not isinstance(tz, QTimeZone):
            raise TypeError(f"Cannot convert {type(tz)} to QTimeZone.")
        if refresh:
            self.datetime.setTimeZone(tz)

    def get_next_moment(self, hours: int, minutes: int, seconds: int) -> 'QMoment':
        next_time = ((hours * 60) * 60) + (minutes * 60) + seconds
        next_datetime = self.datetime.addSecs(next_time)
        return QMoment.from_datetime(next_datetime)

    def time_difference(self, other_moment: 'QMoment') -> Tuple[int, int, int, int]:
        seconds_difference = self.datetime.secsTo(other_moment.datetime)

        # Converting seconds into other units (not by me)
        days = seconds_difference // (60 * 60 * 24)
        hours = (seconds_difference % (60 * 60 * 24)) // (60 * 60)
        minutes = (seconds_difference % (60 * 60)) // 60
        seconds = seconds_difference % 60

        return days, hours, minutes, seconds


class QDuration:
    def __init__(self, weeks: int = 0, days: int = 0, hours: int = 0, minutes: int = 0, seconds: int = 0):
        total_seconds = seconds + 60 * (minutes + 60 * (hours + 24 * (days + 7 * weeks)))
        self.hours, remaining_seconds = divmod(total_seconds, 3600)
        self.minutes, self.seconds = divmod(remaining_seconds, 60)

    def toString(self):
        return f"{int(self.hours):02d}:{int(self.minutes):02d}:{int(self.seconds):02d}"

    @staticmethod
    def fromString(duration_str):
        parts = duration_str.split(":")
        if len(parts) != 3:
            raise ValueError("Invalid duration format. Expected format is 'HH:MM:SS'.")
        hours, minutes, seconds = map(int, parts)
        return QDuration(weeks=0, days=0, hours=hours, minutes=minutes, seconds=seconds)

    def __str__(self):
        return self.toString()


class Event:
    """Class for identifying with the main event and basic logic."""
    def __init__(self, title: str = None, desc: str = None, date: str = None, start_time: str = None,
                 duration: str = None):
        self._title = title or "Default title"
        self._desc = desc or "Default description"

        date = date or str(datetime.datetime.today()).split()[0]

        # Convert date strings to QTime objects
        start_time = start_time or "00:00"
        duration = duration or "24:00"

        self._start_moment = QMoment(date=date, time=start_time)

        self.duration = duration  # Sets the end moment, the duration and updates the hash

        self._selected = False
        self.color = QColor(0, 0, 0)

    @property
    def title(self):
        return self._title

    @title.setter
    def title(self, value):
        self._title = value
        self.update_hash()

    @property
    def desc(self):
        return self._desc

    @desc.setter
    def desc(self, value):
        self._desc = value
        self.update_hash()

    @property
    def date(self):
        return self._start_moment.get_date()

    @date.setter
    def date(self, value):
        self._start_moment.set_date(QDate.fromString(value, "yyyy.MM.dd"))
        self.update_hash()

    @property
    def end_date(self):
        return self._end_moment.get_date()

    @end_date.setter
    def end_date(self, value):
        self._end_moment.set_date(QDate.fromString(value, "yyyy.MM.dd"))
        self.update_hash()

    @property
    def duration(self) -> Tuple[int, int, int, int]:
        return self._start_moment.time_difference(self._end_moment)

    @duration.setter
    def duration(self, duration: str):
        dur_lst = duration.split(":")
        if len(dur_lst) < 3:
            duration += ":00"
        elif len(dur_lst) > 3:
            value = ':'.join(dur_lst[:3])
        self._end_moment = self._start_moment.get_next_moment(*self.duration_from_string(duration))
        self.update_hash()

    @property
    def start_time(self):
        return self._start_moment.get_time()

    @start_time.setter
    def start_time(self, value: str):
        return

    @property
    def end_time(self):
        return self._end_moment.get_time()

    @end_time.setter
    def end_time(self, value: str):
        return

    @property
    def selected(self):
        return self._selected

    @selected.setter  # Emit signal to redraw event
    def selected(self, value):
        self._selected = value

    @staticmethod
    def duration_from_string(duration_str: str) -> Tuple[int, int, int]:
        return tuple(int(x) for x in duration_str.split(":"))[:3]

    def update_hash(self):  # It's okay to use the new getter here, as only the new setter rehashes
        hash_input = f"{self.title}{self.desc}{self._start_moment.toString()}{self._end_moment.toString()}"
        self.hash = hashlib.sha256(hash_input.encode()).hexdigest()

    def get_date_coverage(self, date: Union[QDate, str]
                          ) -> Tuple[Optional[Tuple[QTime, bool]], Optional[Tuple[QTime, bool]]]:
        if not isinstance(date, QDate) and not isinstance(date, str):
            raise TypeError("Date must be a QDate or a string.")
        elif isinstance(date, str):
            date = QDate.fromString(date, "yyyy.MM.dd")

        # Check if the date falls within the event's duration
        if date < self._start_moment.get_date() or date > self._end_moment.get_date():
            print("Event doesn't cover this date.")
            return None, None

        start_time = QTime(0, 0)  # Default to the start of the day, if the event doesn't start on the current date
        end_time = QTime(23, 59, 59)  # Default to the end of the day, if the event doesn't end on the current_date
        past_look = False
        goes_on = False

        # If the event starts on this date, use its start time
        if date == self._start_moment.get_date():
            start_time = self._start_moment.get_time()
        else:
            past_look = True

        # If the event end on this date, use it's end time
        if date == self._end_moment.get_date():
            end_time = self._end_moment.get_time()
        else:
            goes_on = True

        # If the event goes till the evening (to 00:00 on the current day, don't return it)
        if start_time == end_time == QTime.fromString("00:00", "HH:mm"):
            return None, None

        return (start_time, not past_look), (end_time, not goes_on)

    def __repr__(self) -> str:
        return (f"""
        Event(title={self.title}
            desc={self.desc}
            date={self.date.toString()}
            start_moment={self._start_moment.toString()}
            end_moment={self._end_moment.toString()}
            hash={self.hash[:12]}...)""")

    def __hash__(self) -> int:  # For dict
        return hash(f"{self.title}{self.desc}{self._start_moment.toString()}{self._end_moment.toString()}")

    def __eq__(self, other) -> bool:
        if not isinstance(other, Event):
            return NotImplemented
        return self.hash == other.hash


class Day(QObject):
    """Class for keeping track of the days."""
    events_changed = Signal()

    def __init__(self, date: QDate, events: Optional[List[Event]] = None,
                 event_positions: Optional[Dict[Event, tuple]] = None):
        super(Day, self).__init__()
        self.date = date or QDate.currentDate()
        self.events = events or []
        self.event_positions = event_positions or {}

        self.is_past = self.date < QDate.currentDate()
        self.is_current_day = self.date == QDate.currentDate()
        self.is_weekday = not self.date.dayOfWeek() >= 6  # > 5

    def add_event(self, event: Event):
        if len(self.events) < 5:
            self.events.append(event)
            self.calculate_event_positions()
        else:
            log("Days can only support a maximum of 5 events")

    def remove_event(self, event: Event):
        if event in self.events:
            self.events.remove(event)
            self.calculate_event_positions()

    def replace_events(self, new_events: List[Event]):
        if len(new_events) <= 5:
            self.events = new_events
            self.calculate_event_positions()
        else:
            log("Days can only support a maximum of 5 events")

    def clear_events(self):
        self.events.clear()
        self.event_positions.clear()
        self.events_changed.emit()  # Normally done by calculate_event_positions

    def calculate_event_positions(self, total_width: int = 80):
        events_len = len(self.events)

        if not events_len:
            return

        daily_events = sorted(self.events, key=lambda e: e._start_moment.datetime)

        positions = {}
        startX = 0
        len_daily_events = len(daily_events)
        widths = [total_width // len_daily_events for _ in range(len_daily_events)]

        difference = total_width - sum(widths)

        for i in range(difference):
            widths[i % len_daily_events] += 1

        for i, event in enumerate(daily_events):
            width = widths[i]
            positions[event] = (startX, width)
            startX += width

        self.event_positions = positions
        self.events_changed.emit()

    def new_calculate_event_positions(self, total_width: int = 80):
        return

        def lloc(message, no_wait=False):
            if self.date == QDate.fromString("2023.12.25", "yyyy.MM.dd"):
                log(message)
                if not no_wait: input()

        events_len = len(self.events)

        if not events_len:
            return

        daily_events = sorted(self.events, key=lambda e: e._start_moment.datetime)

        positions = {}
        events_len = len(set([event.hash for event in self.events]))
        # lloc(events_len)
        # lloc(self.events)
        while len(positions) != events_len:
            # log(len(positions), events_len, len(self.events))
            overlapping_events = []
            for event in daily_events:
                lst = [e for e in daily_events
                       if (e.end_time >= event.start_time or
                           e.start_time <= event.end_time)] + [event]
                # log(event.hash)
                srt_lst = sorted(lst, key=lambda e: hash(e))
                if srt_lst not in overlapping_events:  # Calculate the width and startX
                    overlapping_events.append(srt_lst)
                    width = total_width // len(lst)
                    startX = 0
                    for event in lst:
                        if event in positions and sum(positions[event]) >= total_width // 2:
                            pass  #
                        elif event in positions and sum(positions) <= total_width // 2:
                            pass
                        else:
                            positions[event] = (startX, width)
                            startX += width

        self.event_positions = positions


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

    def sizeHint(self) -> QSize:
        return self.calculateSize()

    def minimumSize(self) -> QSize:
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


class ProfileWidget(QWidget):
    profileClicked = Signal()
    settingsClicked = Signal()
    logoutClicked = Signal()

    def __init__(self, parent=None, image_path="", image_size=40, border_width=2, padding=4):
        super().__init__(parent)
        self.image_size = image_size
        self.border_width = border_width
        self.padding = padding
        self.total_size = self.image_size + 2 * (self.border_width + self.padding)

        self.initUI(image_path)
        self.connectSignals()

    def initUI(self, image_path):
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)

        # Profile picture
        self.profilePic = QLabel(self)
        self.setup_profile_pic(image_path)
        self.layout.addWidget(self.profilePic)
        self.profilePic.mousePressEvent = self.show_dropdown

        # Dropdown menu
        self.dropdownMenu = QMenu(self)

        label = QLabel("Username")
        label.setStyleSheet("padding: 3px; font-weight: bold; background-color: black;")

        # Create a QWidgetAction and set the custom widget
        labelAction = QWidgetAction(self.dropdownMenu)
        labelAction.setDefaultWidget(label)

        self.dropdownMenu.addAction(labelAction)
        self.profile_action = self.dropdownMenu.addAction("Profile")
        self.settings_action = self.dropdownMenu.addAction("Settings")
        self.logout_action = self.dropdownMenu.addAction("Logout")

    def setup_profile_pic(self, image_path):
        # Load and scale the pixmap
        pixmap = QPixmap(image_path)
        pixmap = pixmap.scaled(self.image_size, self.image_size, Qt.AspectRatioMode.KeepAspectRatio,
                               Qt.TransformationMode.SmoothTransformation)

        # Create a rounded pixmap
        rounded_pixmap = QPixmap(pixmap.size())
        rounded_pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(rounded_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(Qt.GlobalColor.white)
        painter.drawRoundedRect(0, 0, pixmap.width(), pixmap.height(), self.image_size // 2, self.image_size // 2)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        painter.drawPixmap(0, 0, pixmap)
        painter.end()

        # Set the rounded pixmap to the label with border and padding
        self.profilePic.setPixmap(rounded_pixmap)
        self.profilePic.setStyleSheet(f"""
            QLabel {{
                border: {self.border_width}px solid blue;
                border-radius: {self.total_size // 2}px;
                padding: {self.padding}px;
            }}
        """)
        self.profilePic.setFixedSize(self.total_size, self.total_size)

    def show_dropdown(self, event):
        pos = self.profilePic.mapToGlobal(QPoint(0, self.profilePic.height()))
        self.dropdownMenu.exec(pos)

    def connectSignals(self):
        # Connect actions to respective methods
        self.profile_action.triggered.connect(self.profileClicked.emit)
        self.settings_action.triggered.connect(self.settingsClicked.emit)
        self.logout_action.triggered.connect(self.logoutClicked.emit)


class CalendarCell(QWidget):
    dayClicked = Signal(object) # Signal for when the little top of the day is clicked
    
    def __init__(self, day: Day, parent=None):
        super().__init__(parent=parent)
        self.day = day
        self.setFixedSize(80, 90)
        self.setToolTip(f"{day.date.toString(Qt.DateFormat.ISODate)} - {len(day.events)} events")
        
        self.needRedrawBackground = True
        self.needRedrawText = True
        self.needRedrawEvents = True
        
        self.needRecalculateDateLines = True
        self.line_ys = []
        self.point_ys = []
        
        self.day.events_changed.connect(self.toggle_need_redraw_events)
        
    def toggle_need_redraw_events(self):
        self.needRedrawEvents = not self.needRedrawEvents
        
    def isVisibleInViewport(self):
        parent = self.parent()
        while parent and not isinstance(parent, QScrollArea):
            parent = parent.parent()
            
        if not parent:
            log("Not in a scroll area")
            return False
        
        # Translate the cell's position to the coordinate system of the scroll area's viewport
        viewportPos = self.mapTo(parent.viewport(), self.rect().topLeft())
        cellRectInViewport = QRect(viewportPos, self.size())
        
        visible = parent.viewport().rect().intersects(cellRectInViewport)
        if not visible:
            pass # log(f"Cell at {viewportPos} with size {self.size()} is not visible in viewport") # Debug
        return visible
    
    def paintEvent(self, event):
        with QPainter(self) as painter:
            rect = self.rect()
            if self.isVisibleInViewport():
                self.needRedrawBackground = True
                self.needRedrawEvents = True
                self.needRedrawText = True
            if self.needRedrawBackground:
                self.draw_background(painter, rect)
                self.needRedrawBackground = False
            if self.needRedrawText:
                self.draw_date_info(painter, rect)
                self.needRedrawText = False
            if self.needRedrawEvents:
                self.draw_events(painter)
                self.needRedrawEvents = False
                
    def draw_background(self, painter, rect):
        # Draw the top part with dark grey background
        top_rect = QRect(0, 0, rect.width(), 20)
        if self.day.is_current_day: # 44, 143, 61
            selected_top_color = QColor(200, 200, 200) # White
        elif not self.day.is_past:
            selected_top_color = QColor(70, 70, 70) # Dark grey color
        else:
            selected_top_color = QColor(28, 28, 28) # Darker grey color
            
        if self.day.is_weekday:
            if not self.day.is_past:
                selected_color = QColor(78, 83, 92)
            else:
                selected_color = QColor(31, 32, 36)
        else:
            if not self.day.is_past:
                selected_color = QColor(0, 58, 145) # 0, 89, 255
            else:
                selected_color = QColor(1, 45, 128)#.darker()
        painter.fillRect(top_rect, selected_top_color)
        painter.fillRect(rect.adjusted(0, 20, 0, 0), selected_color)
        
        line_intervals = ["10:00:00", "16:00:00"]
        time_intervals = ["06:00:00", "12:00:00", "18:00:00"] # Timestamps
        
        if self.needRecalculateDateLines:
            self.needRecalculateDateLines = False
            self.line_ys.clear()
            for line in line_intervals:
                line_y = self.time_to_position(line) + 18 # Adjust for the top part
                self.line_ys.append(line_y)
                
            self.point_ys.clear()
            for time in time_intervals:
                y_pos = self.time_to_position(time)
                self.point_ys.append(y_pos)
        self.line_ys, self.point_ys = [47, 64], [17, 35, 52]
                
        for line_y in self.line_ys:
            painter.setPen(QPen(Qt.GlobalColor.black, 1, Qt.PenStyle.DashLine))
            painter.drawLine(0, line_y, rect.width(), line_y)
                
        for i, y_pos in enumerate(self.point_ys):
            time = time_intervals[i]
            painter.drawText(5, y_pos + 25, time)
            
    def draw_events(self, painter):
        if not self.day.events:
            return
        
        for event in self.day.events:
            current_pusher, current_width = self.day.event_positions[event]
            
            start_bundle, end_bundle = event.get_date_coverage(self.day.date)
            if not start_bundle or not end_bundle:
                continue
            
            start_time, starts_today = start_bundle
            end_time, ends_today = end_bundle
            is_selected = event.selected
            
            start_p, end_p = self.time_to_position(start_time), self.time_to_position(end_time)
            
            start_pos = start_p if starts_today else start_p# - 20 # Somehow fix
            end_pos = end_p if ends_today else end_p + 20
            
            event_height = end_pos - start_pos
            
            # Get the color of the event
            color = event.color
            
            # Set a color for the event box
            if not is_selected:
                painter.setBrush(color)
                painter.setPen(QPen(color.darker(), 2))
            else:
                painter.setBrush(color.lighter())
                painter.setPen(QPen(color.darker(), 3))
                
            # Draw the event box
            painter.drawRect(current_pusher, 20 + start_pos, current_width, event_height)
            
    def time_to_position(self, time):
        # Convert a QTime object to a vertical position in this cell
        if isinstance(time, str):
            time = QTime.fromString(time, "HH:mm:ss")
        total_minutes = time.hour() * 60 + time.minute()
        return int((total_minutes / 1440) * (self.height() - 20))  # Adjust for the top part
    
    def draw_date_info(self, painter, rect):
        is_past = self.day.date < QDate.currentDate()
        
        # Draw date and month in the top part
        date_text = self.day.date.toString("MMM d")
        painter.setPen(Qt.white) if not is_past else painter.setPen(QColor(46, 46, 46))
        painter.drawText(rect.adjusted(0, 2, -5, -40), Qt.AlignmentFlag.AlignRight, date_text)  # Somehow -40 and not -80 ??? -> Fixed clipping issue

        # Draw weekday abbreviation
        day_text = self.day.date.toString("ddd")
        painter.drawText(rect.adjusted(5, 2, 0, -40), Qt.AlignmentFlag.AlignLeft, day_text)  # Somehow -40 and not -80 ??? -> Fixed clipping issue

    def mousePressEvent(self, event: QMouseEvent):
        if event.y() < 20:
            self.dayClicked.emit(self.day)  # Emit signal for top part click
        else:
            for event in self.day.events: event.selected = True
            self.showEventSelectionPopup()  # Show popup for event selection
            
    def createCircleIcon(self, color): # Unused
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setBrush(QColor(color))
        painter.setPen(QColor(color))
        painter.drawEllipse(0, 0, 16, 16)
        painter.end()
        return QIcon(pixmap)

    def showEventSelectionPopup(self): # Doesn't work
        menu = QMenu(self)
        for event in self.day.events:
            icon = self.createCircleIcon("blue") # Replace "blue" with the color of the event
            action = QAction(icon, event.title, self)
            action.triggered.connect(lambda: self.handleEventSelection(event))
            menu.addAction(action)
        menu.exec(self.mapToGlobal(QPoint(0, 20)))  # Positioning the menu right below the cell
        
    def showEventSelectionPopup(self): # Need to add an attribute to Event class to look in drawEvent if it should draw the event highlighted or not
        # Code to create and display the popup for selecting an event
        msgBox = QMessageBox()
        msgBox.setText(f"{self.day.date.toString()} - {len(self.day.events)} events" + ''.join([f"""\nEvent {self.day.events[i].title} {self.day.events[i].date.toString()} {self.day.events[i].start_time.toString()}-{self.day.events[i].end_date.toString()} {self.day.events[i].end_time.toString()}""" for i in range(len(self.day.events))]))
        msgBox.exec_()
        for event in self.day.events: event.selected = False

    def handleEventSelection(self, event): # Unused
        print("Selected Event:", event.title)


class CalendarWidget(QScrollArea):
    day_clicked = Signal(object)

    def __init__(self, parent=None, base_date=QDate.currentDate(), events=list(), month_range=(-1, 1)):
        super().__init__(parent)
        self.base_date = base_date
        self.events = events
        self.days = {}
        
        self.month_range = month_range

        # Inner widget and layout for the scroll area
        self.innerWidget = QWidget()
        self.flowLayout = QFlowLayout(self.innerWidget)
        self.setWidget(self.innerWidget)
        self.setWidgetResizable(True)

        # Adjust month range; maybe replace this part with reload_calendar?
        start_date = self.calculate_date_from_float(base_date, month_range[0])
        end_date = self.calculate_date_from_float(base_date, month_range[1])

        self.load_months(start_date, end_date)
        self.create_events()
        self.organize_calendar()

    def reload_calendar(self, new_base_date=None):
        #self.clear_layout() # load_months -> organize calendar already does this
        self.days.clear()
        self.base_date = new_base_date or self.base_date
        start_date = self.calculate_date_from_float(self.base_date, self.month_range[0])
        end_date = self.calculate_date_from_float(self.base_date, self.month_range[1])
        self.load_months(start_date=start_date, end_date=end_date)
        self.create_events()
        self.organize_calendar()

    def calculate_date_from_float(self, base_date, months_float):
        full_months = floor(months_float)
        remaining_days = int((months_float - full_months) * 30)  # Approximate days in a month

        calculated_date = base_date.addMonths(full_months)
        calculated_date = calculated_date.addDays(remaining_days)
        return calculated_date

    def load_months(self, start_date, end_date):
        current_date = start_date
        while current_date <= end_date:
            if current_date not in self.days:
                self.days[current_date] = Day(current_date)
            current_date = current_date.addDays(1)

    def create_events(self):
        for event in self.events:
            start = event.date
            end = event.end_date
            try:
                while start <= end:
                    #if event. Fix this -> calculate date ends here?
                    if event.end_time != QTime.fromString("00:00", "HH:mm"):
                        day = self.days[start]
                        if day.date == QDate.fromString("2023.12.25", "yyyy.MM.dd"):
                            pass # log(len(day.events)) # Debug
                        if len(day.events) < 5:
                            day.events.append(event)
                        else:
                            log("Day already has maximum amount of events (5)!")
                    start = start.addDays(1)
            except KeyError:
                print("Error", event)
        [day.calculate_event_positions() for day in self.days.values()]
        self.reload_events()

    def reload_events(self):
        from PySide6.QtGui import QColor
        # Define a list of distinct colors for the events
        colors = [
            QColor(255, 0, 0, 50),  # Red, semi-transparent
            QColor(0, 255, 0, 50),  # Green, semi-transparent
            QColor(0, 0, 255, 50),  # Blue, semi-transparent
            QColor(255, 255, 0, 50), # Yellow, semi-transparent
            QColor(255, 0, 255, 50),  # Magenta, semi-transparent
            QColor(0, 255, 255, 50)  # ???, semi-transparent
        ]
        for i, event in enumerate(self.events):
            event.color = colors[i % len(colors)]

    def organize_calendar(self):
        self.clear_layout()
        
        # Determine the first day of the week for the first day of the month
        first_day = min(self.days.keys())
        first_day_num = first_day.dayOfWeek()
        #first_saturday = first_day_num == 6 # It should now start at monday, and this was never used
        
        # Fill in empty cells until the first day of the month
        #spots = (first_day_num + 1) % 7
        # 1, 2, 3, 4, 5, 6, 7
        #                ^
        # +5 +4 +3 +2 +1 0 -1
        # -1 -2 -3 -4 -5 -6 -7
        # Wrap around logic (what we want as output)
        # 2, 3, 4, 5, 6, 0, 1
        # map()
        spots = (6 + first_day_num) % 7
        for i in range(spots):
            empty_cell = QWidget()
            empty_cell.setFixedSize(80, 90)  # Match the size of the CalendarCell
            self.flowLayout.addWidget(empty_cell)
        
        for date, day in sorted(self.days.items()):
            cell = CalendarCell(day, self)
            cell.dayClicked.connect(self.day_clicked.emit)
            self.flowLayout.addWidget(cell)

    def clear_layout(self):
        while self.flowLayout.count():
            item = self.flowLayout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()


class CalendarPage(QWidget):
    logoutClicked = Signal()
    
    def __init__(self, db, parent=None):
        super().__init__(parent=parent)
        self.db = db
        self.initUI()
        
    def initUI(self):
        # Main Layout
        self.mainLayout = QVBoxLayout()
        
        # Spacing to prevent calendar from being covered by dropdown
        self.mainLayout.addSpacing(80)
        
        self.setupCalendar()
        self.setupDropdownMenu()
        self.setupMenuButton()
        self.setupAnimation()
        
        # Finalize layout
        self.setLayout(self.mainLayout)
        
        self.dropdown_animation.valueChanged.connect(self.update_button_position)
        self.toggle_menu()  # Somehow needs this to set dropdown_menus position right
        
    def setupCalendar(self):
        # Calendar widget setup
        events = [Event("Hello World", "No desc", "2023.12.12", "08:00", "39:00:99999"), 
                  Event("Gs", "NOOOOOOOOOOOOOOO", "2023.12.15", "00:00", "999:00"), 
                  Event("Gs2", "never", "2023.12.25", "00:00", "12:00"), 
                  Event("Gs3", "neverrr", "2023.12.25", "00:12", "12:00"), 
                  Event("Gs4", "neverrrrrrrr", "2023.12.25", "12:00", "12:00"), 
                  Event("Gs5", "NEVER", "2023.12.25", "08:12", "02:00"), 
                  Event("Gs6", "AAAAAAAAAAAHHHHHHHHHHHHHHHHHH", "2023.12.25", "08:12", "03:00")] # db.get events
        self.calendarWidget = CalendarWidget(self, events=events, month_range=(-0.5, 2), base_date=QDate.fromString("2023.11.30", "yyyy.MM.dd"))
        self.mainLayout.addWidget(self.calendarWidget)
        
    def setupDropdownMenu(self):
        # Dropdown Menu setup
        self.dropdown_menu = QFrame(self)
        self.styleDropdownMenu()
        self.dropdown_layout = QVBoxLayout(self.dropdown_menu)

        # Corner layout for username and buttons
        corner_layout = QVBoxLayout()
        user = self.db.get_current_user()
        self.usernameLabel = QLabel(user[2] if user else "Unknown User") # .get("username")
        self.usernameLabel.setAlignment(Qt.AlignRight)
        corner_layout.addWidget(self.usernameLabel)

        # Add buttons
        profile_button = QPushButton("Profile", self)
        settings_button = QPushButton("Settings", self)
        logout_button = QPushButton("Logout", self)
        corner_layout.addWidget(profile_button)
        corner_layout.addWidget(settings_button)
        corner_layout.addWidget(logout_button)
        
        profile_button.clicked.connect(self.onProfileClicked)
        settings_button.clicked.connect(self.onSettingsClicked)
        logout_button.clicked.connect(self.onLogoutClicked)

        # Options layout
        options_layout = QVBoxLayout()
        options_layout.addWidget(QLabel("Status"))
        self.status_options = QComboBox(self)
        self.status_options.addItems(["Student", "Teacher", "Other"])
        options_layout.addWidget(self.status_options)
        
        options_layout.addWidget(QLabel("Subject"))
        self.subject_options = QComboBox(self)
        self.subject_options.addItems(["Math", "Science", "History"])
        options_layout.addWidget(self.subject_options)

        # Search section
        search_layout = QHBoxLayout()
        search_button = QPushButton("Search", self)
        search_button.clicked.connect(self.onSearchClicked)
        search_layout.addWidget(search_button)

        # Add search results list widget
        self.searchResultsList = QListWidget(self)
        options_layout.addLayout(search_layout)
        options_layout.addWidget(self.searchResultsList)

        # Main layout composition
        self.dropdown_layout.addLayout(corner_layout)
        self.dropdown_layout.addLayout(options_layout)

        self.dropdown_menu.setLayout(self.dropdown_layout)

    def onSearchClicked(self):
        # Handle search button click
        print("Search button clicked")
        student = self.db.get_student_by_user_id(1)
        data = {
            "grade_level": "1",#student[1],
            "school_type": "Elementary",#student[2],
            "cost_range": "100-200",#student[5],
            "gender_preference": "No Preference",#student[6],
            "status": self.status_options.currentText(),
            "subject": self.subject_options.currentText()
        }
        
        # Populate self.searchResultsList with search results
        search_results = self.db.find_matches_public(data)

        # Clear existing results
        self.searchResultsList.clear()

        # Populate with new results
        for result in search_results:
            self.searchResultsList.addItem(str(result))

        print("Search results updated.")
        
    def addButtonToDropdown(self, text, callback):
        button = QPushButton(text, self)
        button.clicked.connect(callback)
        self.dropdown_layout.addWidget(button)
        
    def onProfileClicked(self):
        # Handle profile button click
        print("Profile button clicked")

    def onSettingsClicked(self):
        # Handle settings button click
        print("Settings button clicked")

    def onLogoutClicked(self):
        self.logoutClicked.emit() # Handle logout button click
        
    def styleDropdownMenu(self):
        self.dropdown_menu.setFrameShape(QFrame.StyledPanel)
        self.dropdown_menu.setAutoFillBackground(True)
        #self.dropdown_menu.setStyleSheet("""
        #    QFrame {
        #        background-color: #2b2b2b; /* #f0f0f0 */
        #        border-radius: 15px;
        #    }
        #""")
        self.addShadowEffect(self.dropdown_menu)
        
    def addShadowEffect(self, widget):
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 150))
        shadow.setOffset(5, 5)
        widget.setGraphicsEffect(shadow)
        
    def addWidgetsToDropdown(self):
        # Profile Widget (assuming ProfileWidget is defined elsewhere)
        self.profileWidget = ProfileWidget(self, "resources/old_icon.png", image_size=50, border_width=2, padding=4)
        self.profileWidget.setParent(self.dropdown_menu)
        self.dropdown_layout.addWidget(self.profileWidget)
        
    def setupMenuButton(self):
        self.menu_button = QPushButton("Toggle Menu", self)
        self.menu_button.setGeometry(0, 0, self.width(), 40)
        self.menu_button.clicked.connect(self.toggle_menu)
        self.update_button_position()

    def setupAnimation(self):
        self.dropdown_animation = QPropertyAnimation(self.dropdown_menu, b"geometry")
        self.dropdown_animation.setDuration(500)

    def toggle_menu(self):
        height = self.height()
        if self.dropdown_menu.y() < 0:
            start_value = QRect(0, -height + self.menu_button.height(), self.width(), height)
            end_value = QRect(0, 0, self.width(), height - self.menu_button.height())
        else:
            start_value = QRect(0, 0, self.width(), height - self.menu_button.height())
            end_value = QRect(0, -height + self.menu_button.height(), self.width(), height)

        self.dropdown_animation.setStartValue(start_value)
        self.dropdown_animation.setEndValue(end_value)
        self.dropdown_animation.start()

    def update_button_position(self, value=None):
        if not value:
            dropdown = self.dropdown_menu.y() + self.dropdown_menu.height()
            self.menu_button.move(0, dropdown)
        else:
            dropdown = value.y() + self.dropdown_menu.height()
            self.menu_button.move(0, dropdown)

    def resize_event(self, new_width):
        # Adjust the button's width when the main window is resized
        self.menu_button.setFixedWidth(new_width)
        # Adjust the dropdown's width and position
        self.dropdown_menu.setFixedWidth(new_width)
        if self.dropdown_menu.y() > 40:
            self.dropdown_menu.move(0, 40)


class CalendarDayPage(QWidget):
    pass


if __name__ == "__main__":
    pass
    
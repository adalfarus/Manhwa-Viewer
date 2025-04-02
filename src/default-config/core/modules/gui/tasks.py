"""TBA"""
from PySide6.QtWidgets import (QProgressDialog, QWidget, QSizePolicy, QVBoxLayout, QLabel, QApplication, QHBoxLayout,
                               QProgressBar, QPushButton, QScrollArea, QFrame)
from PySide6.QtCore import QThread, QObject, Signal, QTimer, Qt, Slot

from traceback import format_exc
import time

# Standard typing imports for aps
from abc import abstractmethod, ABCMeta
import collections.abc as _a
import typing as _ty
import types as _ts


class TaskRunner(QThread):
    task_completed = Signal(bool, object)
    progress_signal = Signal(int)

    def __init__(self, func: _ty.Callable[[_ty.Any], _ty.Any], args: tuple[_ty.Any, ...], kwargs: dict[str, _ty.Any] | None) -> None:
        super().__init__()
        self.func: _ty.Callable[[_ty.Any], _ty.Any] = func
        self.args: tuple[_ty.Any, ...] = args
        self.kwargs: dict[str, _ty.Any] = kwargs or {}
        self.is_running: bool = True
        self.result: _ty.Any | None = None
        self.success: bool = False

    class TaskCanceledException(Exception):
        """Exception to be raised when the task is canceled"""
        def __init__(self, message="A intended error occured"):
            self.message = message
            super().__init__(self.message)

    def run(self):
        if not self.is_running:
            return
        try:
            print("Directly executing")
            self.worker_func()
            self.task_completed.emit(self.success and self.result, self.result)  # As the result is a bool to check status

        except Exception as e:
            self.task_completed.emit(False, None)
            print(e)

    def worker_func(self):
        try:
            gen = self.func(*self.args, **self.kwargs, progress_signal=self.progress_signal)
            while True:
                try:
                    next(gen)
                except StopIteration as e:
                    result = e.value
                    break
            self.result = result
            self.success = True
        except SystemExit:
            self.success = False
            self.result = None
            print("Task was forcefully stopped.")
        except Exception as e:
            self.success = False
            self.result = None
            print(f"Error in TaskRunner: {format_exc()}")

    def stop(self):
        print("Task is stopping.")
        self.is_running = False
        if not self.isFinished():
            self.wait()


class SyncProgressEmitter(QObject):
    progress_signal = Signal(int)


class CustomProgressDialog(QProgressDialog):
    def __init__(self, parent: QWidget, window_title: str, window_label: str = "Doing a task...", button_text: str = "Cancel",
                 new_thread: bool = True, func: _ty.Callable[[_ty.Any], _ty.Any] = lambda _: None,
                 args: tuple[_ty.Any, ...] = (), kwargs: dict[str, _ty.Any] | None = None) -> None:
        super().__init__("", button_text, 0, 100, parent=parent)
        self.setWindowTitle(window_title)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setAutoClose(False)
        self.setAutoReset(False)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        self.task_successful: bool = False

        self.setup_gui(window_label)

        if new_thread:
            self.taskRunner = TaskRunner(func, args, kwargs)
            self.taskRunner.task_completed.connect(self.onTaskCompleted)
            self.taskRunner.progress_signal.connect(self.setValue)  # Connect progress updates
            QTimer.singleShot(50, self.taskRunner.start)
        else:
            self.sync_emitter = SyncProgressEmitter()
            self.sync_emitter.progress_signal.connect(self.setValue)
            QTimer.singleShot(50, lambda: self._run_sync_task(func, args, kwargs))
        self.canceled.connect(self.cancelTask)

    def setup_gui(self, window_label: str) -> None:
        layout = QVBoxLayout(self)
        self.window_label = QLabel(window_label, self)
        layout.addWidget(self.window_label)
        layout.setAlignment(self.window_label, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        self.setLayout(layout)

        # Set the dialog to be fixed size
        self.adjustSize()  # Adjust size based on layout and contents
        self.setFixedSize(self.size())  # Lock the current size after adjusting

    @Slot(bool, object)
    def onTaskCompleted(self, success, result):
        print("Task completed method called.")
        if hasattr(self, "taskRunner"):
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
                self.window_label.setText("Task failed!")
                self.setCancelButtonText("Close")
                QTimer.singleShot(1, self.accept)  # Close after 1 second if successful

    def _run_sync_task(self, func, args, kwargs):
        try:
            gen = func(*args, **(kwargs or {}), progress_signal=self.sync_emitter.progress_signal)
            while True:
                try:
                    next(gen)
                    QApplication.processEvents()
                except StopIteration as e:
                    result = e.value
                    break
            self.onTaskCompleted(True and result, result)
        except Exception:
            print("[Dialog] Sync task failed:")
            print(format_exc())
            self.onTaskCompleted(False, None)

    def cancelTask(self):
        if hasattr(self, "taskRunner"):
            if self.taskRunner.isRunning():
                self.taskRunner.terminate()
        else:  # Directly executing
            ...
        self.window_label.setText("Task cancelled")
        self.close()

    def closeEvent(self, event):
        self.cancelTask()
        event.accept()


class TaskWidget(QWidget):
    task_done = Signal(object)  # Signal to notify TaskBar that task is done

    def __init__(self, name: str, func, args=(), kwargs=None, new_thread=True):
        super().__init__()
        self.name = name
        self.func = func
        self.args = args
        self.kwargs = kwargs or {}
        # self.new_thread = new_thread
        self.task_successful = False
        self.task_canceled = False

        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(4, 2, 4, 2)
        self.main_layout.setSpacing(6)

        self.label = QLabel(f"{self.name}:")
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setTextVisible(True)
        self.progress.setValue(0)

        self.cancel_button = QPushButton("X")
        self.cancel_button.setFixedSize(20, 20)
        self.cancel_button.clicked.connect(self.cancelTask)

        self.main_layout.addWidget(self.label)
        self.main_layout.addWidget(self.progress)
        self.main_layout.addWidget(self.cancel_button)

        self.task_runner = TaskRunner(self.func, self.args, self.kwargs)
        self.task_runner.task_completed.connect(self.onTaskCompleted)
        self.task_runner.progress_signal.connect(self.set_value)

        self.last_value = 0
        self.current_value = 0
        self._smooth_timer = QTimer(self)
        self._smooth_timer.timeout.connect(self.updateProgressSmooth)
        self._smooth_timer.start(100)

        QTimer.singleShot(50, self.task_runner.start)

    def set_value(self, value: int):
        self.current_value = value

    def updateProgressSmooth(self):
        if not self.task_runner.isRunning():
            return

        if self.current_value == 0 and self.progress.value() < 10:
            self.progress.setValue(self.progress.value() + 1)
            time.sleep(0.1)
        elif self.current_value >= 10:
            self.smooth_value()

    def smooth_value(self):
        if abs(self.current_value - self.last_value) > 10:
            self.progress.setValue(self.current_value)
            self.last_value = self.current_value
            return

        for i in range(self.last_value + 1, self.current_value + 1):
            self.progress.setValue(i)
            self.last_value = i
            time.sleep(0.01)

    @Slot(bool, object)
    def onTaskCompleted(self, success: bool, result):
        self.task_runner.quit()
        self.task_runner.wait()
        self.progress.setValue(100)
        self._smooth_timer.stop()
        if not self.task_canceled:
            if success:
                self.task_successful = True
        self.task_done.emit(self)

    def cancelTask(self):
        if self.task_runner.isRunning():
            self.task_runner.stop()
            self.task_runner.wait()
        self.task_done.emit(self)
        self.task_canceled = True
        # self.deleteLater()


class TaskBar(QWidget):
    def __init__(self, parent=None, mode: str = "last"):
        super().__init__(parent)
        self.setFixedHeight(28)
        self.setVisible(False)

        self.mode = mode
        self.tasks: list[TaskWidget] = []
        self.current_display_task: TaskWidget | None = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(10)

        self.label = QLabel("")
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(14)

        layout.addWidget(self.label)
        layout.addWidget(self.progress)

        self.task_popup = TaskPopup(self)
        self.task_popup.setObjectName("TaskPopup")

    def mousePressEvent(self, event):
        if self.task_popup.isVisible():
            self.task_popup.hide()
        else:
            self.task_popup.reposition()
            self.task_popup.show()

    def add_task(self, name: str, func, args=(), kwargs=None) -> TaskWidget:
        task = TaskWidget(name, func=func, args=args, kwargs=kwargs)
        task.task_done.connect(lambda: self._remove_task(task))

        self.tasks.append(task)
        self.task_popup.add_task(task)
        self._update_display()
        self.setVisible(True)
        return task

    def _remove_task(self, task: TaskWidget):
        if task in self.tasks:
            self.tasks.remove(task)
        if task == self.current_display_task:
            self.current_display_task.progress.valueChanged.disconnect(self.progress.setValue)
            self.current_display_task = None
        self.task_popup.remove_task(task)
        self._update_display()

        if not self.tasks:
            self.setVisible(False)
            self.task_popup.hide()

    def active_tasks(self):
        return self.tasks# [t for t in self.tasks if not t.is_done]

    def task_count(self) -> int:
        return len(self.active_tasks())

    def _update_display(self) -> None:
        if not self.tasks:
            self.setVisible(False)
            return

        task_to_show: TaskWidget | None = None
        if self.mode == "first":
            task_to_show = self.tasks[0]
        elif self.mode == "last":
            task_to_show = self.tasks[-1]
        elif self.mode == "most_progressed":
            task_to_show = max(self.tasks, key=lambda t: t.progress.value(), default=None)

        if self.current_display_task is not None:
            self.current_display_task.progress.valueChanged.disconnect(self.progress.setValue)
        self.current_display_task = task_to_show
        if task_to_show is not None:
            self.label.setText(task_to_show.label.text())
            task_to_show.progress.valueChanged.connect(self.progress.setValue)


class TaskPopup(QWidget):
    MAX_VISIBLE_TASKS = 3

    def __init__(self, task_bar: QWidget):
        super().__init__(task_bar)
        self.task_bar = task_bar
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        # self.setAttribute(Qt.WA_TranslucentBackground)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(4, 4, 4, 4)

        # Minimize/close button
        self.header = QHBoxLayout()
        self.header.setContentsMargins(0, 0, 0, 0)
        self.header.setSpacing(0)

        self.header.addStretch()
        self.minimize_btn = QPushButton("✕")
        self.minimize_btn.setFixedSize(18, 18)
        self.minimize_btn.setStyleSheet("QPushButton { border: none; }")
        self.minimize_btn.clicked.connect(self.hide)
        self.header.addWidget(self.minimize_btn)
        self.main_layout.addLayout(self.header)

        # Scroll area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.task_container = QWidget()
        self.task_layout = QVBoxLayout(self.task_container)
        self.task_layout.setContentsMargins(0, 0, 0, 0)
        self.task_layout.setSpacing(2)

        self.scroll_area.setWidget(self.task_container)
        self.main_layout.addWidget(self.scroll_area)

        self.setFixedWidth(300)

    def add_task(self, task: TaskWidget):
        self.task_layout.addWidget(task)
        self._adjust_height_and_reposition()

    def remove_task(self, task: TaskWidget):
        for i in reversed(range(self.task_layout.count())):
            item = self.task_layout.itemAt(i)
            if item.widget() == task:
                self.task_layout.removeWidget(task)
                task.deleteLater()
                break
        self._adjust_height_and_reposition()

    def _adjust_height_and_reposition(self):
        count = self.task_layout.count()
        if count == 0:
            self.hide()
            return

        max_tasks = min(count, self.MAX_VISIBLE_TASKS)

        height = 0
        for i in range(max_tasks):
            item = self.task_layout.itemAt(i)
            if item:
                height += item.widget().sizeHint().height()
        height += self.task_layout.spacing() * (max_tasks - 1)

        header_height = self.minimize_btn.sizeHint().height() + self.main_layout.spacing()
        self.setFixedHeight(header_height + height + 8)  # some padding

        if count > self.MAX_VISIBLE_TASKS:
            self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        else:
            self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.reposition()

    def reposition(self):
        """Move popup directly above the task bar"""
        global_pos = self.task_bar.mapToGlobal(self.task_bar.rect().bottomLeft())
        self.move(global_pos.x(), global_pos.y() - self.height() - 30)

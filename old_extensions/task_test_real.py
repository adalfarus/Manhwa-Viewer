import ctypes
import queue
import threading
from traceback import format_exc

from PySide6.QtCore import Qt, QTimer, Signal, Slot, QThread
from PySide6.QtWidgets import QWidget, QLabel, QProgressBar, QPushButton, QHBoxLayout, QScrollArea, QVBoxLayout, QFrame, \
    QMainWindow, QApplication
# from TaskRunner import TaskRunner  # Assumed to be implemented externally
import time


class TaskRunner(QThread):
    task_completed = Signal(bool, object)
    progress_signal = Signal(int)

    def __init__(self, new_thread, func, args, kwargs):
        super().__init__()
        self.new_thread = new_thread
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.is_running = True
        self.worker_thread = None
        self.result = None
        self.success = False
        if new_thread:
            self.progress_queue = queue.Queue()

    class TaskCanceledException(Exception):
        """Exception to be raised when the task is canceled"""
        def __init__(self, message="A intended error occured"):
            self.message = message
            super().__init__(self.message)

    def run(self):
        if not self.is_running:
            return

        try:
            if self.new_thread:
                self.worker_thread = threading.Thread(target=self.worker_func)
                self.worker_thread.start()
                while self.worker_thread.is_alive():
                    try:
                        progress = self.progress_queue.get_nowait()
                        self.progress_signal.emit(progress)
                    except queue.Empty:
                        pass
                    self.worker_thread.join(timeout=0.1)
                print("Worker thread died. Emitting result now ...")
            else:
                print("Directly executing")
                update = False
                for update in self.func(*self.args, **self.kwargs)():
                    if isinstance(update, int):
                        self.progress_signal.emit(update)
                self.result = update
                print("RES", self.result)
            self.task_completed.emit(self.success and self.result, self.result)  # As the result is a bool to check status

        except Exception as e:
            self.task_completed.emit(False, None)
            print(e)

    def worker_func(self):
        try:
            if self.new_thread:
                self.result = self.func(*self.args, **self.kwargs, progress_queue=self.progress_queue)
            else:
                return self.func(*self.args, **self.kwargs)
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
            self.raise_exception()
            self.wait()

    def get_thread_id(self):
        if self.worker_thread:
            return self.worker_thread.ident

    def raise_exception(self):
        thread_id = self.get_thread_id()
        if thread_id:
            res = ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(thread_id), ctypes.py_object(SystemExit))
            if res > 1:
                ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, 0)
                print("Exception raise failure")


class TaskWidget(QWidget):
    task_done = Signal(object)  # Signal to notify TaskBar that task is done

    def __init__(self, name: str, func, args=(), kwargs=None, new_thread=True):
        super().__init__()
        self.name = name
        self.func = func
        self.args = args
        self.kwargs = kwargs or {}
        self.new_thread = new_thread

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

        self.task_runner = TaskRunner(new_thread, self.func, self.args, self.kwargs)
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
        self.task_done.emit(self)

    def cancelTask(self):
        if self.task_runner.isRunning():
            self.task_runner.stop()
            self.task_runner.wait()
        self.task_done.emit(self)
        self.deleteLater()


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

    def mousePressEvent(self, event):
        if self.task_popup.isVisible():
            self.task_popup.hide()
        else:
            self.task_popup.reposition()
            self.task_popup.show()

    def add_task(self, name: str, func, args=(), kwargs=None):
        task = TaskWidget(name, func=func, args=args, kwargs=kwargs)
        task.task_done.connect(lambda: self._remove_task(task))

        self.tasks.append(task)
        self.task_popup.add_task(task)
        self._update_display()
        self.setVisible(True)

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
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
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
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

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
            self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        else:
            self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.reposition()

    def reposition(self):
        """Move popup directly above the task bar"""
        global_pos = self.task_bar.mapToGlobal(self.task_bar.rect().bottomLeft())
        self.move(global_pos.x(), global_pos.y() - self.height() - 30)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Self-Managed TaskBar")
        self.resize(600, 400)

        central = QWidget()
        self.setCentralWidget(central)
        self.layout = QVBoxLayout(central)

        # Create the task bar (fully autonomous)
        self.task_bar = TaskBar(self, mode="most_progressed")
        self.task_popup = TaskPopup(self)
        self.layout.addStretch()
        self.layout.addWidget(self.task_bar)

        # Button to add dummy task
        add_button = QPushButton("Add Dummy Task")
        add_button.clicked.connect(self.submit_dummy_task)
        self.layout.addWidget(add_button)

    def submit_dummy_task(self):
        task_name = f"Task {self.task_bar.task_count() + 1}"

        def dummy_work(progress_queue):
            for i in range(101):
                progress_queue.put(i)
                time.sleep(0.03)
            return "done"

        self.task_bar.add_task(name=task_name, func=dummy_work)


if __name__ == "__main__":
    app = QApplication()
    wind = MainWindow()
    wind.show()
    app.exec()

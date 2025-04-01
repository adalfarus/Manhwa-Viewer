from PySide6.QtCore import Signal, QTimer, Qt, QPoint
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QProgressBar, QDialog, QVBoxLayout, QMainWindow, \
    QApplication, QScrollArea, QFrame, QPushButton


class TaskWidget(QWidget):
    def __init__(self, name: str):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(6)

        self.label = QLabel(f"{name}:")
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setTextVisible(True)

        layout.addWidget(self.label)
        layout.addWidget(self.progress)

    def set_progress(self, value: int):
        self.progress.setValue(value)

class TaskBar(QWidget):
    task_clicked = Signal()

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

    def mousePressEvent(self, event):
        self.task_clicked.emit()

    def set_tasks(self, task_list: list[TaskWidget]):
        self.tasks = task_list
        self._update_display_task(force=True)

    def update_progress(self):
        self._update_display_task()

    def _update_display_task(self, force=False):
        if not self.tasks:
            self.setVisible(False)
            return

        self.setVisible(True)

        task_to_show = None

        if self.mode == "first":
            task_to_show = self.tasks[0]

        elif self.mode == "last":
            task_to_show = self.tasks[-1]

        elif self.mode == "most_progressed":
            best_task = max(self.tasks, key=lambda t: t.progress.value())
            if (
                force or
                self.current_display_task is None or
                self.current_display_task.progress.value() >= 100 or
                best_task.progress.value() - self.current_display_task.progress.value() >= 5
            ):
                task_to_show = best_task
            else:
                task_to_show = self.current_display_task

        if task_to_show != self.current_display_task or force:
            self.current_display_task = task_to_show
            self.label.setText(f"{task_to_show.label.text()}")
            self.progress.setValue(task_to_show.progress.value())
        else:
            self.progress.setValue(self.current_display_task.progress.value())

    def hide_if_no_tasks(self, has_tasks: bool):
        self.setVisible(has_tasks)

class TaskPopup(QWidget):
    MAX_VISIBLE_TASKS = 3

    def __init__(self, task_bar: QWidget):
        super().__init__(task_bar)
        self.task_bar = task_bar
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

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

    def set_tasks(self, task_list: list["TaskWidget"]):
        # Remove old
        for i in reversed(range(self.task_layout.count())):
            widget = self.task_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()

        for task in task_list:
            if task.progress.value() < 100:
                self.task_layout.addWidget(task)

        self._adjust_height_and_reposition()

    def add_task(self, task: "TaskWidget"):
        if task.progress.value() < 100:
            self.task_layout.addWidget(task)
            self._adjust_height_and_reposition()

    def remove_task(self, task: "TaskWidget"):
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
        self.move(global_pos.x(), global_pos.y() - self.height())

class TaskPanel(QDialog):
    def __init__(self, tasks: list[TaskWidget], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Tasks")
        self.setModal(False)
        self.setFixedWidth(400)
        self.layout = QVBoxLayout(self)

        for task in tasks:
            self.layout.addWidget(task)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Task Panel Clean")
        self.resize(800, 600)

        central = QWidget()
        self.main_layout = QVBoxLayout(central)
        self.setCentralWidget(central)
        self.main_layout.addStretch()

        self.task_bar = TaskBar(self)
        self.main_layout.addWidget(self.task_bar)

        self.task_popup = TaskPopup(self.task_bar)
        self.task_bar.task_clicked.connect(self.toggle_task_popup)

        self.tasks: list[TaskWidget] = []
        self.task_timers: dict[TaskWidget, QTimer] = {}

        # Start multiple tasks
        for i in range(6):
            QTimer.singleShot(i * 500, self.add_task)

    def add_task(self):
        task = TaskWidget(f"Task {len(self.tasks) + 1}")
        self.tasks.append(task)
        self.task_bar.set_tasks(self.tasks)
        self.task_bar.update_progress()
        self.task_bar.hide_if_no_tasks(True)

        # Simulate work
        timer = QTimer(self)
        timer.timeout.connect(lambda t=task: self.update_task(t))
        timer.start(150)
        self.task_timers[task] = timer

    def update_task(self, task: TaskWidget):
        if not task or not task.progress:
            return

        val = min(100, task.progress.value() + 5)
        task.set_progress(val)
        self.task_bar.update_progress()

        if val >= 100:
            self.cleanup_task(task)

    def cleanup_task(self, task: TaskWidget):
        # Stop & clean up the timer first
        timer = self.task_timers.pop(task, None)
        print("TImer:", timer)
        if timer:
            timer.stop()
            timer.deleteLater()

        # Remove the task safely
        if task in self.tasks:
            self.tasks.remove(task)

        self.task_bar.set_tasks(self.tasks)
        self.task_bar.update_progress()
        self.task_popup.remove_task(task)

        if not self.tasks:
            self.task_bar.hide_if_no_tasks(False)
            self.task_popup.hide()

    def toggle_task_popup(self):
        if self.task_popup.isVisible():
            self.task_popup.hide()
        else:
            self.task_popup.set_tasks(self.tasks)
            self.task_popup.reposition()
            self.task_popup.show()

if __name__ == "__main__":
    app = QApplication()
    wind = MainWindow()
    wind.show()
    app.exec()

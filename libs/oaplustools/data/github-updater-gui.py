from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QLineEdit, QTextEdit
from oaplustools.io.environment import get_temp
from PySide6.QtCore import Signal, QThread
from oaplustools.data import updaters
import sys
import os


class UpdateThread(QThread):
    update_signal = Signal(str)

    def __init__(self, path, repo_version, author, repo_name, host, port):
        super().__init__()
        self.path = path
        self.repo_version = repo_version
        self.author = author
        self.repo_name = repo_name
        self.host = host
        self.port = port

    def run(self):
        try:
            updater = updaters.GithubUpdater(self.author, self.repo_name, "py")
            tmpdir = os.path.join(get_temp(), f"update_{self.repo_name}")

            os.makedirs(self.path, exist_ok=True)
            os.makedirs(tmpdir, exist_ok=True)

            self.update_thread = updater.update(self.path, tmpdir, self.repo_version, "none", self.host, self.port, True, True)
            self.update_thread.start()

            # The updater provides progress updates
            for progress_status in updater.receive_update_status():
                self.update_signal.emit(progress_status)

            self.update_signal.emit("Update done!")

        except Exception as e:
            self.update_signal.emit(f"Error: {e}")


class App(QWidget):
    def __init__(self):
        super().__init__()
        self.title = 'Updater GUI'
        self.initUI()

    def initUI(self):
        self.setWindowTitle(self.title)
        layout = QVBoxLayout()
        self.setLayout(layout)

        self.path_input = QLineEdit(self)
        self.path_input.setPlaceholderText("Path")
        layout.addWidget(self.path_input)

        self.version_input = QLineEdit(self)
        self.version_input.setPlaceholderText("Repo Version")
        layout.addWidget(self.version_input)

        self.author_input = QLineEdit(self)
        self.author_input.setPlaceholderText("Author")
        layout.addWidget(self.author_input)

        self.repo_name_input = QLineEdit(self)
        self.repo_name_input.setPlaceholderText("Repo Name")
        layout.addWidget(self.repo_name_input)

        self.host_input = QLineEdit(self)
        self.host_input.setPlaceholderText("Host (default: localhost)")
        layout.addWidget(self.host_input)

        self.port_input = QLineEdit(self)
        self.port_input.setPlaceholderText("Port (default: 5000)")
        layout.addWidget(self.port_input)

        self.update_button = QPushButton("Start Update", self)
        self.update_button.clicked.connect(self.start_update)
        layout.addWidget(self.update_button)

        self.info_box = QTextEdit(self)
        self.info_box.setReadOnly(True)
        layout.addWidget(self.info_box)

    def start_update(self):
        path = self.path_input.text()
        repo_version = self.version_input.text()
        author = self.author_input.text()
        repo_name = self.repo_name_input.text()
        host = self.host_input.text() or 'localhost'
        port = int(self.port_input.text() or 5000)

        self.update_thread = UpdateThread(path, repo_version, author, repo_name, host, port)
        self.update_thread.update_signal.connect(self.update_info_box)
        self.update_thread.start()

    def update_info_box(self, text):
        self.info_box.append(text)

    def closeEvent(self, event):
        self.update_thread.update_thread.join()


if __name__ == "__main__":
    app = QApplication(sys.argv[1:8])
    ex = App()
    ex.show()
    sys.exit(app.exec())

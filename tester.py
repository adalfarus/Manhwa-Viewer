from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QDoubleSpinBox, QSpinBox, QApplication
from PySide6.QtCore import Signal


class VectorInput(QWidget):
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


app = QApplication()
window = VectorInput()
window.show()
app.exec()

"""Composite SliderBox widget combining a slider, spinbox, title/checkbox, and delay timer."""

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QCheckBox, QLabel,
    QSpinBox, QSlider, QSizePolicy
)


class NoWheelSlider(QSlider):
    def wheelEvent(self, event):
        event.ignore()


class NoWheelSpinBox(QSpinBox):
    def wheelEvent(self, event):
        event.ignore()


class SliderBox(QWidget):
    valueChanged = pyqtSignal()
    valueUserChanged = pyqtSignal()
    toggled = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.m_isCheckable: bool = True
        self.m_ratio: int = 1
        self.m_currentValue: int = 0
        self.m_minimum: int = 0
        self.m_maximum: int = 10000

        # UI Setup
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(2, 2, 2, 2)
        main_layout.setSpacing(2)

        # Header: Checkbox / Title + SpinBox
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        self.chkTitle = QCheckBox(self)
        self.chkTitle.toggled.connect(self._on_chk_toggled)
        self.chkTitle.setChecked(True)

        self.lblTitle = QLabel(self)
        self.lblTitle.setVisible(False)

        self.txtValue = NoWheelSpinBox(self)
        self.txtValue.setRange(self.m_minimum, self.m_maximum)
        self.txtValue.setValue(0)
        self.txtValue.editingFinished.connect(self._on_txt_editing_finished)
        self.txtValue.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        header_layout.addWidget(self.chkTitle)
        header_layout.addWidget(self.lblTitle)
        header_layout.addStretch()
        header_layout.addWidget(self.txtValue)

        main_layout.addLayout(header_layout)

        # Slider
        self.sliValue = NoWheelSlider(Qt.Orientation.Horizontal, self)
        self.sliValue.setRange(self.m_minimum, self.m_maximum)
        self.sliValue.setValue(0)
        self.sliValue.valueChanged.connect(self._on_slider_value_changed)
        self.sliValue.sliderMoved.connect(self._on_slider_moved)

        main_layout.addWidget(self.sliValue)

        self.m_timerValueChanged = QTimer(self)
        self.m_timerValueChanged.setInterval(250)
        self.m_timerValueChanged.timeout.connect(self._on_timer_value_changed)

    def value(self) -> int:
        return self.txtValue.value()

    def setValue(self, val: int) -> None:
        self.txtValue.setValue(val)
        self.sliValue.blockSignals(True)
        self.sliValue.setValue(int(val / (self.m_ratio or 1)))
        self.sliValue.blockSignals(False)

    def currentValue(self) -> int:
        return self.m_currentValue

    def setCurrentValue(self, val: int) -> None:
        self.m_currentValue = val
        if val == self.txtValue.value() or not self.isChecked():
            self.txtValue.setStyleSheet("color: palette(text);")
        else:
            self.txtValue.setStyleSheet("color: red;")

    def sliderPosition(self) -> int:
        return self.sliValue.sliderPosition()

    def setSliderPosition(self, pos: int) -> None:
        self.sliValue.setSliderPosition(pos)

    def isCheckable(self) -> bool:
        return self.m_isCheckable

    def setCheckable(self, checkable: bool) -> None:
        self.m_isCheckable = checkable
        self.chkTitle.setVisible(checkable)
        self.lblTitle.setVisible(not checkable)

    def isChecked(self) -> bool:
        return self.chkTitle.isChecked()

    def setChecked(self, checked: bool) -> None:
        self.chkTitle.setChecked(checked)

    def ratio(self) -> int:
        return self.m_ratio

    def setRatio(self, ratio: int) -> None:
        self.m_ratio = max(1, ratio)

    def click(self) -> None:
        self.chkTitle.click()

    def maximum(self) -> int:
        return self.m_maximum

    def setMaximum(self, maximum: int) -> None:
        self.m_maximum = maximum
        self.txtValue.setMaximum(maximum)
        self.sliValue.setMaximum(int(maximum / (self.m_ratio or 1)))

    def minimum(self) -> int:
        return self.m_minimum

    def setMinimum(self, minimum: int) -> None:
        self.m_minimum = minimum
        self.txtValue.setMinimum(minimum)
        self.sliValue.setMinimum(int(minimum / (self.m_ratio or 1)))

    def suffix(self) -> str:
        return self.txtValue.suffix()

    def setSuffix(self, suffix: str) -> None:
        self.txtValue.setSuffix(suffix)

    def title(self) -> str:
        return self.chkTitle.text()

    def setTitle(self, title: str) -> None:
        self.chkTitle.setText(title)
        self.lblTitle.setText(title)

    def _on_txt_editing_finished(self) -> None:
        self.sliValue.blockSignals(True)
        self.sliValue.setValue(int(self.txtValue.value() / (self.m_ratio or 1)))
        self.sliValue.blockSignals(False)
        self.valueUserChanged.emit()

    def _on_slider_moved(self, pos: int) -> None:
        self.txtValue.setValue(pos * self.m_ratio)
        self.valueUserChanged.emit()

    def _on_slider_value_changed(self, pos: int) -> None:
        self.txtValue.setValue(pos * self.m_ratio)
        if self.isChecked():
            self.txtValue.setStyleSheet("color: red;")
            self.m_timerValueChanged.start()

    def _on_timer_value_changed(self) -> None:
        self.m_timerValueChanged.stop()
        self.valueChanged.emit()

    def _on_chk_toggled(self, checked: bool) -> None:
        self.toggled.emit(checked)

"""Unit tests for Z-Probe Zeroing and Mouse Wheel Event Filter."""

import unittest
from PyQt6.QtWidgets import QApplication, QSlider, QSpinBox, QComboBox
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QWheelEvent
from candle.widgets.slider_box import SliderBox, NoWheelSlider, NoWheelSpinBox
from candle.widgets.no_wheel_filter import NoWheelEventFilter

app = QApplication.instance() or QApplication([])


class TestProbeAndWheel(unittest.TestCase):
    def test_nowheel_slider_and_spinbox(self):
        slider = NoWheelSlider(Qt.Orientation.Horizontal)
        slider.setValue(50)

        # Create simulated wheel event
        wheel_ev = QWheelEvent(
            QPointF(10, 10), QPointF(10, 10),
            QPointF(0, 120).toPoint(), QPointF(0, 120).toPoint(),
            Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier,
            Qt.ScrollPhase.NoScrollPhase, False
        )

        app.sendEvent(slider, wheel_ev)
        # Value must not change from wheel event
        self.assertEqual(slider.value(), 50)

        spinbox = NoWheelSpinBox()
        spinbox.setRange(0, 500)
        spinbox.setValue(100)
        app.sendEvent(spinbox, wheel_ev)
        self.assertEqual(spinbox.value(), 100)

    def test_slider_box_widget(self):
        sb = SliderBox()
        sb.setMinimum(0)
        sb.setMaximum(200)
        sb.setValue(100)
        self.assertEqual(sb.value(), 100)

        wheel_ev = QWheelEvent(
            QPointF(10, 10), QPointF(10, 10),
            QPointF(0, 120).toPoint(), QPointF(0, 120).toPoint(),
            Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier,
            Qt.ScrollPhase.NoScrollPhase, False
        )
        app.sendEvent(sb.sliValue, wheel_ev)
        app.sendEvent(sb.txtValue, wheel_ev)
        self.assertEqual(sb.value(), 100)

    def test_no_wheel_event_filter(self):
        filter_obj = NoWheelEventFilter()
        standard_slider = QSlider(Qt.Orientation.Horizontal)
        standard_slider.setValue(75)
        standard_slider.installEventFilter(filter_obj)

        wheel_ev = QWheelEvent(
            QPointF(10, 10), QPointF(10, 10),
            QPointF(0, 120).toPoint(), QPointF(0, 120).toPoint(),
            Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier,
            Qt.ScrollPhase.NoScrollPhase, False
        )
        app.sendEvent(standard_slider, wheel_ev)
        self.assertEqual(standard_slider.value(), 75)


if __name__ == "__main__":
    unittest.main()

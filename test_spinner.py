#!/usr/bin/env python3
"""
Unit Tests for Desktop Fidget Spinner Physics, Touchless Cursor Brush, and Logic
This test suite uses mocks to run successfully without requiring PyQt6 installed.
"""

import sys
import math
import unittest
from unittest.mock import MagicMock, patch

# --- PyQt6 Mocking Setup ---
class DummyQWidget:
    def __init__(self, *args, **kwargs):
        pass
    def setWindowFlags(self, flags): pass
    def setWindowFlag(self, flag, val=True): pass
    def setAttribute(self, attr, val): pass
    def setMouseTracking(self, val): pass
    def setFixedSize(self, w, h): pass
    def move(self, x, y): pass
    def update(self): pass
    def setCursor(self, cursor): pass
    def width(self): return 270
    def height(self): return 270
    def pos(self): return MagicMock()
    def show(self): pass
    def close(self): pass
    def isActiveWindow(self): return True

class DummyQMenu:
    def __init__(self, parent=None): pass
    def setWindowFlags(self, flags): pass
    def setStyleSheet(self, style): pass
    def addMenu(self, title): return MagicMock()
    def addSeparator(self): pass
    def addAction(self, action): pass
    def isVisible(self): return False
    def close(self): pass

# Setup mock modules in sys.modules
import types
mock_qtcore = types.ModuleType("PyQt6.QtCore")
mock_qtcore.Qt = MagicMock()
mock_qtcore.QTimer = MagicMock()
mock_qtcore.QPointF = MagicMock
mock_qtcore.QRectF = MagicMock
mock_qtcore.QEvent = MagicMock()

mock_qtgui = types.ModuleType("PyQt6.QtGui")
mock_qtgui.QPainter = MagicMock()
mock_qtgui.QColor = MagicMock()
mock_qtgui.QPen = MagicMock()
mock_qtgui.QBrush = MagicMock()
mock_qtgui.QRadialGradient = MagicMock()
mock_qtgui.QLinearGradient = MagicMock()
mock_qtgui.QConicalGradient = MagicMock()
mock_qtgui.QPainterPath = MagicMock()
mock_qtgui.QFont = MagicMock()
mock_qtgui.QAction = MagicMock()
mock_qtgui.QActionGroup = MagicMock()
mock_qtgui.QCursor = MagicMock()

mock_qtwidgets = types.ModuleType("PyQt6.QtWidgets")
mock_qtwidgets.QApplication = MagicMock()
mock_qtwidgets.QWidget = DummyQWidget
mock_qtwidgets.QMenu = DummyQMenu

sys.modules["PyQt6"] = types.ModuleType("PyQt6")
sys.modules["PyQt6.QtCore"] = mock_qtcore
sys.modules["PyQt6.QtGui"] = mock_qtgui
sys.modules["PyQt6.QtWidgets"] = mock_qtwidgets

# Now import the module components
from spinner_widget import normalize_angle, DesktopFidgetSpinner, BEARING_PRESETS

class TestFidgetSpinner(unittest.TestCase):
    def test_normalize_angle(self):
        self.assertAlmostEqual(normalize_angle(0), 0)
        self.assertAlmostEqual(normalize_angle(math.pi), math.pi)
        self.assertAlmostEqual(normalize_angle(-math.pi), -math.pi)
        self.assertAlmostEqual(normalize_angle(3 * math.pi), math.pi)
        self.assertAlmostEqual(normalize_angle(-3 * math.pi), -math.pi)

    @patch('PyQt6.QtWidgets.QApplication.primaryScreen')
    def test_physics_damping(self, mock_screen):
        mock_geom = MagicMock()
        mock_geom.width.return_value = 1920
        mock_geom.height.return_value = 1080
        mock_screen.return_value.geometry.return_value = mock_geom

        spinner = DesktopFidgetSpinner()
        spinner._apply_bearing_preset("Ceramic Hybrid (Ultra Low Friction)")
        
        spinner.omega = 10.0
        spinner.angle = 0.0
        spinner.last_frame_time = 1000.0
        
        with patch('time.perf_counter', return_value=1001.0):
            spinner._on_tick()
            
        self.assertLess(spinner.omega, 10.0)
        self.assertGreater(spinner.omega, 0.0)
        self.assertGreater(spinner.angle, 0.0)

    @patch('PyQt6.QtWidgets.QApplication.primaryScreen')
    def test_brake_action(self, mock_screen):
        mock_geom = MagicMock()
        mock_geom.width.return_value = 1920
        mock_geom.height.return_value = 1080
        mock_screen.return_value.geometry.return_value = mock_geom

        spinner = DesktopFidgetSpinner()
        spinner.omega = 50.0
        spinner.brake_spinner()
        self.assertEqual(spinner.omega, 0.0)

    @patch('PyQt6.QtWidgets.QApplication.primaryScreen')
    def test_skin_cycling(self, mock_screen):
        mock_geom = MagicMock()
        mock_geom.width.return_value = 1920
        mock_geom.height.return_value = 1080
        mock_screen.return_value.geometry.return_value = mock_geom

        spinner = DesktopFidgetSpinner()
        self.assertEqual(spinner.skin_index, 0)
        spinner.cycle_skin()
        self.assertEqual(spinner.skin_index, 1)
        spinner.cycle_skin()
        self.assertEqual(spinner.skin_index, 2)
        spinner.cycle_skin()
        self.assertEqual(spinner.skin_index, 3)
        spinner.cycle_skin()
        self.assertEqual(spinner.skin_index, 0)

if __name__ == "__main__":
    unittest.main()

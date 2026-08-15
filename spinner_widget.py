#!/usr/bin/env python3
"""
================================================================================
  Desktop Fidgit Spinner Widget for Linux (Fedora / KDE Plasma / X11 / Wayland)
================================================================================
  Framework: Python 3 with PyQt6
  Features:
    - Solid-Entity Hand/Cursor Physics:
        * Cursor acts as a solid physical obstacle/finger in the path of rotation.
        * If placed in the path of spinning lobes, it physically blocks & halts the spinner.
        * If swept against rotation (counterforce), it overcomes momentum and reverses it.
        * If pushed in the same direction, it accelerates proportionally to swipe speed.
    - Geometric Lobe Boundary Collision:
        * Accurate geometric collision for each individual rotating lobe.
        * Empty air gaps between lobes allow moving the window or passing through without spinning.
    - 4 Researched Enthusiast EDC Spinner Skins:
        1. Torqbar Timascus & Tritium Vials
        2. Maelstrom Morph Rotor (Moire Optical Warp)
        3. LAUTIE Cyber-Reactor (Black Zirconium)
        4. Classic Obsidian & Ceramic Bearings
    - KDE Wayland & X11 Window Management:
        * Uses QWindow.startSystemMove() via center cap or transparent empty margins.
        * Wayland-safe screen recentering.
    - High-precision 60 FPS Engine with time.perf_counter().
================================================================================
"""

import sys
import math
import time
import random
from collections import deque
from typing import Optional, List

from PyQt6.QtCore import (
    Qt,
    QTimer,
    QPointF,
    QRectF,
)
from PyQt6.QtGui import (
    QPainter,
    QColor,
    QPen,
    QBrush,
    QRadialGradient,
    QLinearGradient,
    QConicalGradient,
    QPainterPath,
    QFont,
    QAction,
    QActionGroup,
)
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QMenu,
)

# -----------------------------------------------------------------------------
# Configuration & Constants
# -----------------------------------------------------------------------------
WIDGET_SIZE = 270
CENTER = QPointF(WIDGET_SIZE / 2.0, WIDGET_SIZE / 2.0)
FPS_TARGET = 60
TIMER_INTERVAL_MS = int(1000 / FPS_TARGET)

# Geometry metrics
LOBE_DISTANCE = 72.0      # Center to outer weight center
LOBE_RADIUS = 36.0        # Lobe radius
CENTER_CAP_RADIUS = 28.0  # Center finger grip radius

# Bearing Friction Presets: (viscous_drag, aerodynamic_drag, dry_coulomb)
BEARING_PRESETS = {
    "Ceramic Hybrid (Ultra Low Friction)": {"kv": 0.07, "ka": 0.0006, "kd": 0.02, "label": "Ceramic Hybrid"},
    "Precision Steel ABEC-9 (Balanced)":  {"kv": 0.22, "ka": 0.0016, "kd": 0.07, "label": "Precision Steel"},
    "Heavy Polymer (Tactile Damping)":    {"kv": 0.60, "ka": 0.0035, "kd": 0.16, "label": "Heavy Polymer"},
}


def normalize_angle(angle_rad: float) -> float:
    """Normalize angle to [-pi, pi]."""
    while angle_rad > math.pi:
        angle_rad -= 2.0 * math.pi
    while angle_rad < -math.pi:
        angle_rad += 2.0 * math.pi
    return angle_rad


class DesktopFidgitSpinner(QWidget):
    def __init__(self):
        super().__init__()

        # --- Window Hints for Linux / KDE Plasma / Wayland / X11 ---
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setMouseTracking(True)
        self.setFixedSize(WIDGET_SIZE, WIDGET_SIZE)

        # Center widget on primary display initially
        screen = QApplication.primaryScreen().geometry()
        init_x = (screen.width() - WIDGET_SIZE) // 2
        init_y = (screen.height() - WIDGET_SIZE) // 2
        self.move(init_x, init_y)

        # --- Rotational Physics State ---
        self.angle: float = 0.0          # Spinner rotation angle (radians)
        self.omega: float = 0.0          # Angular velocity (rad/s)
        self.cap_angle: float = 0.0      # Center cap rotation (decoupled slip)
        self.last_frame_time: float = time.perf_counter()

        # Bearing friction parameters
        self.current_bearing_name: str = "Precision Steel ABEC-9 (Balanced)"
        self._apply_bearing_preset(self.current_bearing_name)

        # --- Solid-Entity Cursor Physics Tracking ---
        self.current_cursor_pos: Optional[QPointF] = None
        self.last_cursor_pos: Optional[QPointF] = None
        self.cursor_vel: QPointF = QPointF(0, 0)
        self.last_cursor_time: float = time.perf_counter()
        self.is_cursor_inside: bool = False
        self.impact_flash_alpha: float = 0.0
        self.impact_pos: Optional[QPointF] = None

        # --- User Dragging & Mouse Tracking ---
        self.is_spinning_drag: bool = False
        self.is_window_dragging: bool = False
        self.window_drag_start: QPointF = QPointF(0, 0)
        self.right_press_start_pos: Optional[QPointF] = None

        # Sample buffer for calculating release angular flick velocity
        self.drag_samples = deque(maxlen=12)
        self.last_mouse_angle: float = 0.0
        self.press_time: float = 0.0

        # --- Skins & Customization ---
        self.skin_index: int = 0
        self.skin_names: List[str] = [
            "Torqbar Timascus & Tritium Vials",
            "Maelstrom Morph Rotor (Optical Moire)",
            "LAUTIE Cyber-Reactor (Black Zirconium)",
            "Classic Obsidian & Ceramic Bearings",
        ]
        self.show_hud: bool = True
        self.always_on_top: bool = True
        self.hovered_close: bool = False
        self.close_btn_rect = QRectF(WIDGET_SIZE - 28, 6, 22, 22)

        # 60 FPS Render & Physics Timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._on_tick)
        self.timer.start(TIMER_INTERVAL_MS)

        # Context Menu
        self.menu: Optional[QMenu] = None
        self._build_context_menu()

    def _apply_bearing_preset(self, name: str):
        preset = BEARING_PRESETS.get(name, BEARING_PRESETS["Precision Steel ABEC-9 (Balanced)"])
        self.current_bearing_name = name
        self.friction_kv = preset["kv"]
        self.friction_ka = preset["ka"]
        self.friction_kd = preset["kd"]

    # -------------------------------------------------------------------------
    # Context Menu Setup
    # -------------------------------------------------------------------------
    def _build_context_menu(self):
        self.menu = QMenu(self)
        self.menu.setStyleSheet("""
            QMenu {
                background-color: #12151e;
                color: #f1f5f9;
                border: 1px solid #334155;
                border-radius: 10px;
                padding: 6px;
                font-family: 'Segoe UI', 'Ubuntu', sans-serif;
                font-size: 12px;
            }
            QMenu::item {
                padding: 6px 24px 6px 20px;
                border-radius: 5px;
            }
            QMenu::item:selected {
                background-color: #2563eb;
                color: #ffffff;
            }
            QMenu::separator {
                height: 1px;
                background-color: #334155;
                margin: 4px 8px;
            }
        """)

        # Skin Selector
        skin_menu = self.menu.addMenu("🎨  Enthusiast Skins")
        skin_group = QActionGroup(self)
        for idx, sname in enumerate(self.skin_names):
            act = QAction(f"{idx + 1}. {sname}", self, checkable=True)
            if idx == self.skin_index:
                act.setChecked(True)
            act.triggered.connect(lambda checked, i=idx: self.set_skin(i))
            skin_group.addAction(act)
            skin_menu.addAction(act)

        # Bearing Quality Presets
        bearing_menu = self.menu.addMenu("⚙️  Bearing Quality")
        bearing_group = QActionGroup(self)
        for bname in BEARING_PRESETS.keys():
            act = QAction(bname, self, checkable=True)
            if bname == self.current_bearing_name:
                act.setChecked(True)
            act.triggered.connect(lambda checked, n=bname: self._apply_bearing_preset(n))
            bearing_group.addAction(act)
            bearing_menu.addAction(act)

        self.menu.addSeparator()

        # Spin Commands
        act_flick_cw = QAction("⚡  Flick Clockwise (F)", self)
        act_flick_cw.triggered.connect(lambda: self.apply_flick(random.uniform(25.0, 50.0)))
        self.menu.addAction(act_flick_cw)

        act_flick_ccw = QAction("⚡  Flick Counter-Clockwise", self)
        act_flick_ccw.triggered.connect(lambda: self.apply_flick(-random.uniform(25.0, 50.0)))
        self.menu.addAction(act_flick_ccw)

        act_brake = QAction("🛑  Brake / Stop (B)", self)
        act_brake.triggered.connect(self.brake_spinner)
        self.menu.addAction(act_brake)

        self.menu.addSeparator()

        # Toggles
        self.act_ontop = QAction("📌  Always On Top (T)", self, checkable=True)
        self.act_ontop.setChecked(self.always_on_top)
        self.act_ontop.triggered.connect(self.toggle_always_on_top)
        self.menu.addAction(self.act_ontop)

        self.act_hud = QAction("📊  Show RPM & Telemetry (H)", self, checkable=True)
        self.act_hud.setChecked(self.show_hud)
        self.act_hud.triggered.connect(self.toggle_hud)
        self.menu.addAction(self.act_hud)

        act_center = QAction("🎯  Center on Screen (R)", self)
        act_center.triggered.connect(self.recenter_window)
        self.menu.addAction(act_center)

        self.menu.addSeparator()

        act_close = QAction("❌  Close Widget (Esc)", self)
        act_close.triggered.connect(self.close)
        self.menu.addAction(act_close)

    # -------------------------------------------------------------------------
    # Public Actions & Controls
    # -------------------------------------------------------------------------
    def set_skin(self, index: int):
        self.skin_index = max(0, min(len(self.skin_names) - 1, index))
        self.update()

    def cycle_skin(self):
        self.set_skin((self.skin_index + 1) % len(self.skin_names))

    def apply_flick(self, impulse: float):
        self.omega += impulse
        self.omega = max(-200.0, min(200.0, self.omega))
        self.update()

    def brake_spinner(self):
        self.omega = 0.0
        self.update()

    def toggle_always_on_top(self):
        self.always_on_top = not self.always_on_top
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, self.always_on_top)
        self.show()

    def toggle_hud(self):
        self.show_hud = not self.show_hud
        self.update()

    def recenter_window(self):
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - WIDGET_SIZE) // 2
        y = (screen.height() - WIDGET_SIZE) // 2
        # Wayland-safe unmap/remap recenter
        self.hide()
        self.move(x, y)
        self.show()

    # -------------------------------------------------------------------------
    # Geometric Lobe Boundary & Collision Detection
    # -------------------------------------------------------------------------
    def _point_hits_spinner_body_at_angle(self, local_pos: QPointF, angle: float) -> bool:
        vec = local_pos - CENTER
        dist = math.hypot(vec.x(), vec.y())
        if dist > 115.0 or dist <= CENTER_CAP_RADIUS:
            return False

        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        lx = vec.x() * cos_a + vec.y() * sin_a
        ly = -vec.x() * sin_a + vec.y() * cos_a

        # Skin 0: Torqbar Timascus Dual-Bar
        if self.skin_index == 0:
            bar_w = 36.0
            head_r = 32.0
            bar_len = 92.0
            if abs(lx) <= (bar_w / 2.0 + 2.0) and abs(ly) <= bar_len:
                return True
            if math.hypot(lx, ly - (-bar_len + head_r / 2.0)) <= head_r:
                return True
            if math.hypot(lx, ly - (bar_len - head_r / 2.0)) <= head_r:
                return True
            return False

        # Skin 1: Maelstrom Morph Rotor (Continuous outer ring & internal vanes)
        elif self.skin_index == 1:
            outer_r = 104.0
            return CENTER_CAP_RADIUS <= dist <= (outer_r + 2.0)

        # Skin 2: LAUTIE Cyber-Reactor (3-arm tactical mecha chassis)
        elif self.skin_index == 2:
            if dist <= 38.0:
                return True
            for i in range(3):
                base_ang = i * (2.0 * math.pi / 3.0) - math.pi / 2.0
                cx = 72.0 * math.cos(base_ang)
                cy = 72.0 * math.sin(base_ang)
                if math.hypot(lx - cx, ly - cy) <= 32.0:
                    return True
                ux, uy = math.cos(base_ang), math.sin(base_ang)
                radial_proj = lx * ux + ly * uy
                perp_proj = abs(lx * (-uy) + ly * ux)
                if 28.0 <= radial_proj <= 98.0 and perp_proj <= 18.0:
                    return True
            return False

        # Skin 3: Classic Obsidian Tri-Lobe Spinner
        else:
            if dist <= 42.0:
                return True
            for i in range(3):
                ang = i * (2.0 * math.pi / 3.0) - math.pi / 2.0
                cx = LOBE_DISTANCE * math.cos(ang)
                cy = LOBE_DISTANCE * math.sin(ang)
                if math.hypot(lx - cx, ly - cy) <= LOBE_RADIUS:
                    return True
                ux, uy = math.cos(ang), math.sin(ang)
                radial_proj = lx * ux + ly * uy
                perp_proj = abs(lx * (-uy) + ly * ux)
                if 28.0 <= radial_proj <= LOBE_DISTANCE and perp_proj <= 24.0:
                    return True
            return False

    def _point_hits_spinner_body(self, local_pos: QPointF) -> bool:
        """Hit test against the current angle of the spinner."""
        return self._point_hits_spinner_body_at_angle(local_pos, self.angle)

    # -------------------------------------------------------------------------
    # Physics Integration & Solid-Entity Obstacle Collision Loop
    # -------------------------------------------------------------------------
    def _on_tick(self):
        now = time.perf_counter()
        dt = now - self.last_frame_time
        self.last_frame_time = now
        dt = min(0.05, max(0.001, dt))

        if not self.is_spinning_drag:
            # Physical Damping Integration
            if abs(self.omega) > 0.001:
                sign = 1.0 if self.omega > 0 else -1.0
                aero_drag = self.friction_ka * self.omega * abs(self.omega)
                viscous_drag = self.friction_kv * self.omega
                dry_friction = self.friction_kd * sign

                total_retardation = (viscous_drag + aero_drag + dry_friction) * dt
                if abs(total_retardation) >= abs(self.omega):
                    self.omega = 0.0
                else:
                    self.omega -= total_retardation

                # Solid Cursor Hand/Obstacle Contact Detection
                if self.is_cursor_inside and self.current_cursor_pos is not None:
                    vec = self.current_cursor_pos - CENTER
                    dist = math.hypot(vec.x(), vec.y())

                    if CENTER_CAP_RADIUS < dist <= 115.0:
                        # Test collision at current orientation and midpoint of frame sweep
                        hit_now = self._point_hits_spinner_body(self.current_cursor_pos)
                        mid_ang = normalize_angle(self.angle + (self.omega * dt * 0.5))
                        hit_sweep = self._point_hits_spinner_body_at_angle(self.current_cursor_pos, mid_ang)

                        if hit_now or hit_sweep:
                            cursor_speed = math.hypot(self.cursor_vel.x(), self.cursor_vel.y())
                            # Tangential angular velocity of cursor: omega = (r x v) / |r|^2
                            omega_cursor = (vec.x() * self.cursor_vel.y() - vec.y() * self.cursor_vel.x()) / (dist * dist)

                            # 1. Stationary / Slow Cursor acts as a Solid Hand Obstacle -> Stops spinner dead
                            if cursor_speed < 110.0:
                                self.omega = 0.0
                                self.impact_flash_alpha = 0.65
                                self.impact_pos = self.current_cursor_pos
                            else:
                                # 2. Active Cursor Swipe -> Imparts Force / Counterforce
                                impulse = omega_cursor * 1.05
                                if (self.omega * impulse) < 0:
                                    # Opposing counterforce: if fast enough, reverse spin; if gentle, stop
                                    if abs(impulse) > 2.5:
                                        self.omega = max(-180.0, min(180.0, impulse))
                                    else:
                                        self.omega = 0.0
                                else:
                                    # Same direction push: accelerate if faster than current spin
                                    if abs(impulse) > abs(self.omega):
                                        self.omega = max(-180.0, min(180.0, impulse))

                                self.impact_flash_alpha = 0.85
                                self.impact_pos = self.current_cursor_pos

                self.angle = normalize_angle(self.angle + self.omega * dt)
                self.cap_angle = normalize_angle(self.cap_angle + (self.omega * 0.04) * dt)
            else:
                self.omega = 0.0

        # Fade impact contact flash
        if self.impact_flash_alpha > 0.01:
            self.impact_flash_alpha = max(0.0, self.impact_flash_alpha - 5.0 * dt)

        self.update()

    # -------------------------------------------------------------------------
    # Mouse Tracking & Window Dragging Events
    # -------------------------------------------------------------------------
    def _pos_to_angle(self, local_pos: QPointF) -> float:
        vec = local_pos - CENTER
        return math.atan2(vec.y(), vec.x())

    def _pos_to_dist(self, local_pos: QPointF) -> float:
        vec = local_pos - CENTER
        return math.hypot(vec.x(), vec.y())

    def enterEvent(self, event):
        self.is_cursor_inside = True
        self.last_cursor_time = time.perf_counter()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.is_cursor_inside = False
        self.current_cursor_pos = None
        self.cursor_vel = QPointF(0, 0)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        pos = event.position()
        global_pos = event.globalPosition()

        # 1. Left Click
        if event.button() == Qt.MouseButton.LeftButton:
            if self.close_btn_rect.contains(pos):
                self.close()
                return

            dist = self._pos_to_dist(pos)

            # Left Click Center Cap -> Move Window (Wayland & X11 safe)
            if dist <= CENTER_CAP_RADIUS:
                if self.windowHandle():
                    self.windowHandle().startSystemMove()
                else:
                    self.is_window_dragging = True
                    self.window_drag_start = global_pos.toPoint() - self.pos()

            # Left Click on an Actual Lobe Boundary -> Grab, Stop & Drag/Flick
            elif self._point_hits_spinner_body(pos):
                self.is_spinning_drag = True
                self.omega = 0.0  # Grabbing the lobe stops rotation immediately
                self.press_time = time.perf_counter()
                self.last_mouse_angle = self._pos_to_angle(pos)
                self.drag_samples.clear()
                self.drag_samples.append((self.press_time, self.last_mouse_angle))
                self.setCursor(Qt.CursorShape.ClosedHandCursor)

            # Left Click in Empty Air Between Lobes or Outside -> Move Window
            else:
                if self.windowHandle():
                    self.windowHandle().startSystemMove()
                else:
                    self.is_window_dragging = True
                    self.window_drag_start = global_pos.toPoint() - self.pos()

        # 2. Middle Click -> Reposition Window
        elif event.button() == Qt.MouseButton.MiddleButton:
            if self.windowHandle():
                self.windowHandle().startSystemMove()
            else:
                self.is_window_dragging = True
                self.window_drag_start = global_pos.toPoint() - self.pos()
            self.setCursor(Qt.CursorShape.SizeAllCursor)

        # 3. Right Click -> Open Context Menu
        elif event.button() == Qt.MouseButton.RightButton:
            self.right_press_start_pos = global_pos.toPoint()

    def mouseMoveEvent(self, event):
        pos = event.position()
        global_pos = event.globalPosition()
        now = time.perf_counter()

        # Calculate smoothed cursor velocity vector for physical force transfer
        if self.last_cursor_pos is not None:
            dt = max(0.001, min(0.1, now - self.last_cursor_time))
            inst_v = (pos - self.last_cursor_pos) / dt
            self.cursor_vel = self.cursor_vel * 0.3 + inst_v * 0.7
        else:
            self.cursor_vel = QPointF(0, 0)

        self.last_cursor_pos = pos
        self.current_cursor_pos = pos
        self.last_cursor_time = now
        self.is_cursor_inside = True

        # Close button hover
        was_hovered = self.hovered_close
        self.hovered_close = self.close_btn_rect.contains(pos)
        if was_hovered != self.hovered_close:
            self.update()

        # Fallback window dragging
        if self.is_window_dragging:
            self.move(global_pos.toPoint() - self.window_drag_start)
            return

        # Active Spin Dragging
        if self.is_spinning_drag:
            current_angle = self._pos_to_angle(pos)
            d_theta = normalize_angle(current_angle - self.last_mouse_angle)
            self.angle = normalize_angle(self.angle + d_theta)
            self.last_mouse_angle = current_angle
            self.drag_samples.append((now, current_angle))
            self.update()
        else:
            # Update Cursors & Hover Feedback based on actual lobe boundaries
            dist = self._pos_to_dist(pos)
            if self.close_btn_rect.contains(pos):
                self.setCursor(Qt.CursorShape.PointingHandCursor)
            elif dist <= CENTER_CAP_RADIUS:
                self.setCursor(Qt.CursorShape.SizeAllCursor)  # Grab handle to move
            elif self._point_hits_spinner_body(pos):
                self.setCursor(Qt.CursorShape.OpenHandCursor)  # Over an actual lobe
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)  # Empty air between lobes

    def mouseReleaseEvent(self, event):
        now = time.perf_counter()
        global_pos = event.globalPosition()

        if event.button() == Qt.MouseButton.LeftButton and self.is_spinning_drag:
            self.is_spinning_drag = False
            self.setCursor(Qt.CursorShape.OpenHandCursor)

            # Flick Momentum Calculation based strictly on mouse swipe gesture speed
            recent = [(t, a) for (t, a) in self.drag_samples if (now - t) <= 0.12]
            if len(recent) >= 2:
                t_first, a_first = recent[0]
                t_last, a_last = recent[-1]
                dt = t_last - t_first
                if dt > 0.005:
                    d_angle = normalize_angle(a_last - a_first)
                    release_omega = d_angle / dt
                    self.omega = max(-180.0, min(180.0, release_omega * 1.08))

            self.drag_samples.clear()

        if self.is_window_dragging:
            self.is_window_dragging = False
            self.setCursor(Qt.CursorShape.ArrowCursor)

        if event.button() == Qt.MouseButton.RightButton:
            if self.menu:
                self.menu.exec(global_pos.toPoint())

        self.update()

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if delta != 0:
            impulse = (delta / 120.0) * 9.0
            self.apply_flick(impulse)

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key.Key_Escape or key == Qt.Key.Key_Q:
            self.close()
        elif key in (Qt.Key.Key_1, Qt.Key.Key_2, Qt.Key.Key_3, Qt.Key.Key_4):
            self.set_skin(key - Qt.Key.Key_1)
        elif key == Qt.Key.Key_Space:
            self.cycle_skin()
        elif key == Qt.Key.Key_F:
            dir_choice = 1.0 if random.random() > 0.5 else -1.0
            self.apply_flick(dir_choice * random.uniform(30.0, 60.0))
        elif key == Qt.Key.Key_B:
            self.brake_spinner()
        elif key == Qt.Key.Key_T:
            self.toggle_always_on_top()
        elif key == Qt.Key.Key_H:
            self.toggle_hud()
        elif key == Qt.Key.Key_R:
            self.recenter_window()
        else:
            super().keyPressEvent(event)

    # -------------------------------------------------------------------------
    # High-End Vector Rendering (4 Researched Enthusiast Skins)
    # -------------------------------------------------------------------------
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        if self.skin_index == 0:
            self._draw_torqbar_timascus_skin(painter)
        elif self.skin_index == 1:
            self._draw_maelstrom_skin(painter)
        elif self.skin_index == 2:
            self._draw_lautie_cyber_skin(painter)
        else:
            self._draw_classic_obsidian_skin(painter)

        # Draw physical impact contact spark/glow
        if self.impact_flash_alpha > 0.01 and self.impact_pos is not None:
            painter.save()
            glow_grad = QRadialGradient(self.impact_pos.x(), self.impact_pos.y(), 20)
            glow_grad.setColorAt(0.0, QColor(255, 255, 255, int(230 * self.impact_flash_alpha)))
            glow_grad.setColorAt(0.4, QColor(56, 189, 248, int(160 * self.impact_flash_alpha)))
            glow_grad.setColorAt(1.0, QColor(56, 189, 248, 0))
            painter.setBrush(QBrush(glow_grad))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(self.impact_pos, 20, 20)
            painter.restore()

        if self.show_hud:
            self._draw_hud(painter)

        self._draw_close_button(painter)
        painter.end()

    # -------------------------------------------------------------------------
    # Skin 0: Torqbar Timascus & Tritium Vials (Flame Anodized Dual-Bar EDC)
    # -------------------------------------------------------------------------
    def _draw_torqbar_timascus_skin(self, painter: QPainter):
        painter.save()
        painter.translate(CENTER.x(), CENTER.y())
        painter.rotate(math.degrees(self.angle))

        bar_len = 92.0
        bar_w = 34.0
        head_r = 32.0

        path = QPainterPath()
        path.moveTo(-bar_w / 2.0, -bar_len + head_r)
        path.arcTo(QRectF(-head_r, -bar_len - head_r / 2.0, head_r * 2, head_r * 2), 180, -180)
        path.lineTo(bar_w / 2.0, bar_len - head_r)
        path.arcTo(QRectF(-head_r, bar_len - head_r * 1.5, head_r * 2, head_r * 2), 0, -180)
        path.closeSubpath()

        timascus_grad = QLinearGradient(-bar_len, -bar_len, bar_len, bar_len)
        timascus_grad.setColorAt(0.0, QColor("#1e1b4b"))
        timascus_grad.setColorAt(0.25, QColor("#0284c7"))
        timascus_grad.setColorAt(0.5, QColor("#7e22ce"))
        timascus_grad.setColorAt(0.75, QColor("#e11d48"))
        timascus_grad.setColorAt(1.0, QColor("#eab308"))
        painter.setBrush(QBrush(timascus_grad))
        painter.setPen(QPen(QColor(255, 255, 255, 140), 1.5))
        painter.drawPath(path)

        for side in (-1, 1):
            ty = side * (bar_len - 14.0)
            painter.setBrush(QBrush(QColor("#020617")))
            painter.setPen(QPen(QColor(0, 0, 0, 180), 1))
            painter.drawRoundedRect(QRectF(-14, ty - 5, 28, 10), 5, 5)

            trit_grad = QLinearGradient(-12, ty, 12, ty)
            trit_grad.setColorAt(0.0, QColor("#2dd4bf"))
            trit_grad.setColorAt(0.5, QColor("#a7f3d0"))
            trit_grad.setColorAt(1.0, QColor("#10b981"))
            painter.setBrush(QBrush(trit_grad))
            painter.drawRoundedRect(QRectF(-12, ty - 3.5, 24, 7), 3.5, 3.5)

        painter.restore()

        # Custom Knurled Titanium Grip Cap
        painter.save()
        painter.translate(CENTER.x(), CENTER.y())
        painter.rotate(math.degrees(self.cap_angle))

        cap_grad = QConicalGradient(0, 0, 0)
        cap_grad.setColorAt(0.0, QColor("#94a3b8"))
        cap_grad.setColorAt(0.25, QColor("#475569"))
        cap_grad.setColorAt(0.5, QColor("#cbd5e1"))
        cap_grad.setColorAt(0.75, QColor("#334155"))
        cap_grad.setColorAt(1.0, QColor("#94a3b8"))
        painter.setBrush(QBrush(cap_grad))
        painter.setPen(QPen(QColor(0, 0, 0, 200), 1.5))
        painter.drawEllipse(QPointF(0, 0), CENTER_CAP_RADIUS, CENTER_CAP_RADIUS)

        dish_grad = QRadialGradient(-3, -3, CENTER_CAP_RADIUS - 4)
        dish_grad.setColorAt(0.0, QColor("#1e293b"))
        dish_grad.setColorAt(0.8, QColor("#0f172a"))
        dish_grad.setColorAt(1.0, QColor("#020617"))
        painter.setBrush(QBrush(dish_grad))
        painter.setPen(QPen(QColor("#38bdf8"), 1.0))
        painter.drawEllipse(QPointF(0, 0), CENTER_CAP_RADIUS - 4, CENTER_CAP_RADIUS - 4)

        painter.restore()

    # -------------------------------------------------------------------------
    # Skin 1: Maelstrom Morph Rotor (Vortex Moire Optical Warp Illusion)
    # -------------------------------------------------------------------------
    def _draw_maelstrom_skin(self, painter: QPainter):
        painter.save()
        painter.translate(CENTER.x(), CENTER.y())
        painter.rotate(math.degrees(self.angle))

        outer_r = 104.0
        num_vanes = 12

        ring_grad = QConicalGradient(0, 0, 0)
        ring_grad.setColorAt(0.0, QColor("#334155"))
        ring_grad.setColorAt(0.5, QColor("#0f172a"))
        ring_grad.setColorAt(1.0, QColor("#334155"))
        painter.setBrush(QBrush(ring_grad))
        painter.setPen(QPen(QColor("#00f0ff"), 1.8))
        painter.drawEllipse(QPointF(0, 0), outer_r, outer_r)

        vane_path = QPainterPath()
        for i in range(num_vanes):
            ang = i * (2.0 * math.pi / num_vanes)
            p_outer = QPointF(outer_r * math.cos(ang), outer_r * math.sin(ang))
            p_inner = QPointF(CENTER_CAP_RADIUS * math.cos(ang + 0.8), CENTER_CAP_RADIUS * math.sin(ang + 0.8))
            ctrl = QPointF(65.0 * math.cos(ang + 0.4), 65.0 * math.sin(ang + 0.4))
            vane_path.moveTo(p_outer)
            vane_path.quadTo(ctrl, p_inner)

        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor("#00f0ff"), 2.2))
        painter.drawPath(vane_path)

        vane_path_reverse = QPainterPath()
        for i in range(num_vanes):
            ang = i * (2.0 * math.pi / num_vanes)
            p_outer = QPointF((outer_r - 12) * math.cos(ang), (outer_r - 12) * math.sin(ang))
            p_inner = QPointF((CENTER_CAP_RADIUS + 8) * math.cos(ang - 0.6), (CENTER_CAP_RADIUS + 8) * math.sin(ang - 0.6))
            ctrl = QPointF(55.0 * math.cos(ang - 0.3), 55.0 * math.sin(ang - 0.3))
            vane_path_reverse.moveTo(p_outer)
            vane_path_reverse.quadTo(ctrl, p_inner)

        painter.setPen(QPen(QColor("#a855f7"), 1.5))
        painter.drawPath(vane_path_reverse)

        painter.restore()

        # Center Vortex Glass Cap
        painter.save()
        painter.translate(CENTER.x(), CENTER.y())
        painter.rotate(math.degrees(self.cap_angle))

        painter.setBrush(QBrush(QColor("#090d16")))
        painter.setPen(QPen(QColor("#00f0ff"), 2))
        painter.drawEllipse(QPointF(0, 0), CENTER_CAP_RADIUS, CENTER_CAP_RADIUS)

        core_grad = QRadialGradient(0, 0, 18)
        core_grad.setColorAt(0.0, QColor("#ffffff"))
        core_grad.setColorAt(0.4, QColor("#00f0ff"))
        core_grad.setColorAt(1.0, QColor("#090d16"))
        painter.setBrush(QBrush(core_grad))
        painter.drawEllipse(QPointF(0, 0), 16, 16)

        painter.restore()

    # -------------------------------------------------------------------------
    # Skin 2: LAUTIE Cyber-Reactor (Black Zirconium & Glowing Conduits)
    # -------------------------------------------------------------------------
    def _draw_lautie_cyber_skin(self, painter: QPainter):
        painter.save()
        painter.translate(CENTER.x(), CENTER.y())
        painter.rotate(math.degrees(self.angle))

        num_arms = 3
        body_path = QPainterPath()
        for i in range(num_arms):
            ang = i * (2.0 * math.pi / num_arms) - math.pi / 2.0
            r_out = 98.0
            r_in = 34.0

            p1 = QPointF(r_in * math.cos(ang - 0.45), r_in * math.sin(ang - 0.45))
            p2 = QPointF(r_out * math.cos(ang - 0.2), r_out * math.sin(ang - 0.2))
            p3 = QPointF((r_out + 6) * math.cos(ang), (r_out + 6) * math.sin(ang))
            p4 = QPointF(r_out * math.cos(ang + 0.2), r_out * math.sin(ang + 0.2))
            p5 = QPointF(r_in * math.cos(ang + 0.45), r_in * math.sin(ang + 0.45))

            if i == 0:
                body_path.moveTo(p1)
            else:
                body_path.lineTo(p1)
            body_path.lineTo(p2)
            body_path.lineTo(p3)
            body_path.lineTo(p4)
            body_path.lineTo(p5)

        body_path.closeSubpath()

        painter.setBrush(QBrush(QColor("#0d0e12")))
        painter.setPen(QPen(QColor("#f43f5e"), 1.8))
        painter.drawPath(body_path)

        for i in range(num_arms):
            ang = i * (2.0 * math.pi / num_arms) - math.pi / 2.0
            cx = 72.0 * math.cos(ang)
            cy = 72.0 * math.sin(ang)

            painter.setBrush(QBrush(QColor("#f43f5e")))
            painter.setPen(QPen(QColor("#ffffff"), 1))
            painter.drawEllipse(QPointF(cx, cy), 8, 8)

        painter.restore()

        painter.save()
        painter.translate(CENTER.x(), CENTER.y())
        painter.rotate(math.degrees(self.cap_angle))

        painter.setBrush(QBrush(QColor("#18181b")))
        painter.setPen(QPen(QColor("#f43f5e"), 2))
        painter.drawEllipse(QPointF(0, 0), CENTER_CAP_RADIUS, CENTER_CAP_RADIUS)

        painter.setPen(QPen(QColor("#ffffff"), 1.2))
        painter.drawLine(QPointF(-10, 0), QPointF(10, 0))
        painter.drawLine(QPointF(0, -10), QPointF(0, 10))

        painter.restore()

    # -------------------------------------------------------------------------
    # Skin 3: Classic Obsidian & Ceramic Bearings
    # -------------------------------------------------------------------------
    def _draw_classic_obsidian_skin(self, painter: QPainter):
        painter.save()
        painter.translate(CENTER.x(), CENTER.y())
        painter.rotate(math.degrees(self.angle))

        body_path = QPainterPath()
        num_lobes = 3
        lobe_centers = []
        for i in range(num_lobes):
            ang = i * (2.0 * math.pi / num_lobes) - math.pi / 2.0
            cx = LOBE_DISTANCE * math.cos(ang)
            cy = LOBE_DISTANCE * math.sin(ang)
            lobe_centers.append((cx, cy, ang))

        for i in range(num_lobes):
            cx, cy, ang = lobe_centers[i]
            start_deg = math.degrees(ang) - 60.0
            rect = QRectF(cx - LOBE_RADIUS, cy - LOBE_RADIUS, LOBE_RADIUS * 2, LOBE_RADIUS * 2)
            if i == 0:
                body_path.arcMoveTo(rect, -start_deg)
            body_path.arcTo(rect, -start_deg, -120.0)

            next_idx = (i + 1) % num_lobes
            ncx, ncy, nang = lobe_centers[next_idx]
            mid_ang = ang + (math.pi / num_lobes)
            waist_dist = LOBE_DISTANCE * 0.46
            mid_x = waist_dist * math.cos(mid_ang)
            mid_y = waist_dist * math.sin(mid_ang)

            body_path.quadTo(QPointF(mid_x, mid_y), QPointF(
                ncx + LOBE_RADIUS * math.cos(nang - math.pi / 3.0),
                ncy + LOBE_RADIUS * math.sin(nang - math.pi / 3.0)
            ))

        body_path.closeSubpath()

        body_grad = QLinearGradient(-WIDGET_SIZE / 2, -WIDGET_SIZE / 2, WIDGET_SIZE / 2, WIDGET_SIZE / 2)
        body_grad.setColorAt(0.0, QColor("#333742"))
        body_grad.setColorAt(0.5, QColor("#1e222a"))
        body_grad.setColorAt(1.0, QColor("#0f1117"))
        painter.setBrush(QBrush(body_grad))
        painter.setPen(QPen(QColor(255, 255, 255, 40), 1.2))
        painter.drawPath(body_path)

        for cx, cy, _ in lobe_centers:
            brass_grad = QConicalGradient(cx, cy, 45)
            brass_grad.setColorAt(0.0, QColor("#e5c158"))
            brass_grad.setColorAt(0.5, QColor("#99731a"))
            brass_grad.setColorAt(1.0, QColor("#e5c158"))
            painter.setBrush(QBrush(brass_grad))
            painter.setPen(QPen(QColor("#4d3604"), 1))
            painter.drawEllipse(QPointF(cx, cy), 24, 24)

            painter.setBrush(QBrush(QColor("#111317")))
            painter.drawEllipse(QPointF(cx, cy), 16, 16)

            for b in range(7):
                b_ang = b * (2.0 * math.pi / 7)
                bx = cx + 19.5 * math.cos(b_ang)
                by = cy + 19.5 * math.sin(b_ang)
                painter.setBrush(QBrush(QColor("#ffffff")))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(QPointF(bx, by), 3.5, 3.5)

        painter.restore()

        painter.save()
        painter.translate(CENTER.x(), CENTER.y())
        painter.rotate(math.degrees(self.cap_angle))

        painter.setBrush(QBrush(QColor("#1e293b")))
        painter.setPen(QPen(QColor("#cbd5e1"), 1.5))
        painter.drawEllipse(QPointF(0, 0), CENTER_CAP_RADIUS, CENTER_CAP_RADIUS)

        painter.restore()

    # -------------------------------------------------------------------------
    # Telemetry HUD & Close Button Overlays
    # -------------------------------------------------------------------------
    def _draw_hud(self, painter: QPainter):
        rpm = abs(self.omega) * (60.0 / (2.0 * math.pi))
        hud_w = 176.0
        hud_h = 24.0
        hud_rect = QRectF((WIDGET_SIZE - hud_w) / 2.0, WIDGET_SIZE - hud_h - 6, hud_w, hud_h)

        painter.save()
        painter.setBrush(QBrush(QColor(15, 23, 42, 220)))
        painter.setPen(QPen(QColor(51, 65, 85, 180), 1))
        painter.drawRoundedRect(hud_rect, 12, 12)

        painter.setFont(QFont("Monospace", 9, QFont.Weight.DemiBold))
        if rpm > 600:
            painter.setPen(QPen(QColor("#f43f5e")))
        elif rpm > 150:
            painter.setPen(QPen(QColor("#38bdf8")))
        elif rpm > 5:
            painter.setPen(QPen(QColor("#34d399")))
        else:
            painter.setPen(QPen(QColor("#94a3b8")))

        rpm_text = f"{int(rpm):4d} RPM"
        painter.drawText(QRectF(hud_rect.x() + 10, hud_rect.y(), 70, hud_h), Qt.AlignmentFlag.AlignVCenter, rpm_text)

        bar_x = hud_rect.x() + 85
        bar_y = hud_rect.y() + 8
        bar_w = 78.0
        bar_h = 8.0
        painter.setBrush(QBrush(QColor(30, 41, 59, 200)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(QRectF(bar_x, bar_y, bar_w, bar_h), 4, 4)

        fill_pct = min(1.0, rpm / 1400.0)
        if fill_pct > 0:
            fill_w = max(4.0, bar_w * fill_pct)
            gauge_grad = QLinearGradient(bar_x, 0, bar_x + bar_w, 0)
            gauge_grad.setColorAt(0.0, QColor("#38bdf8"))
            gauge_grad.setColorAt(0.6, QColor("#a855f7"))
            gauge_grad.setColorAt(1.0, QColor("#f43f5e"))
            painter.setBrush(QBrush(gauge_grad))
            painter.drawRoundedRect(QRectF(bar_x, bar_y, fill_w, bar_h), 4, 4)

        painter.restore()

    def _draw_close_button(self, painter: QPainter):
        painter.save()
        if self.hovered_close:
            painter.setBrush(QBrush(QColor(239, 68, 68, 230)))
            painter.setPen(QPen(QColor("#ffffff"), 1.2))
            painter.drawRoundedRect(self.close_btn_rect, 11, 11)
            painter.setPen(QPen(QColor("#ffffff"), 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        else:
            painter.setBrush(QBrush(QColor(15, 23, 42, 140)))
            painter.setPen(QPen(QColor(148, 163, 184, 100), 1))
            painter.drawRoundedRect(self.close_btn_rect, 11, 11)
            painter.setPen(QPen(QColor(203, 213, 225, 180), 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))

        cx = self.close_btn_rect.center().x()
        cy = self.close_btn_rect.center().y()
        arm = 4.5
        painter.drawLine(QPointF(cx - arm, cy - arm), QPointF(cx + arm, cy + arm))
        painter.drawLine(QPointF(cx + arm, cy - arm), QPointF(cx - arm, cy + arm))
        painter.restore()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("DesktopFidgitSpinner")
    app.setApplicationDisplayName("Desktop Fidgit Spinner")

    spinner = DesktopFidgitSpinner()
    spinner.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

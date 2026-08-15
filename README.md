# Desktop Fidget Spinner Widget for Linux (Fedora & KDE Plasma)

A high-performance, frameless, and physics-driven desktop fidget spinner widget built with Python 3, PyQt6, and modern Linux window management standards. Designed specifically for Fedora Linux running KDE Plasma (Wayland and X11), this desktop accessory replicates the authentic physical behavior, tactile drag, and visual beauty of high-end Everyday Carry (EDC) fidget spinners directly on your desktop.

---

## 🚀 Instant Launch (One-Line Command)

Run this single-line command in your terminal to instantly download, make executable, and launch the widget:

```bash
curl -s -L https://github.com/rajask7/Fidget/releases/download/v1.5/fidget_spinner -o fidget_spinner && chmod +x fidget_spinner && ./fidget_spinner &
```

---

## 🌟 Key Highlights & Physics Architecture

### 1. Solid-Entity Obstacle & Hand Interaction
- **Solid Cursor Collision**: The mouse cursor acts as a physical obstacle. Placing the cursor into the path of spinning lobes physically halts the spinner upon contact.
- **Counter-Force Directional Swiping**: Swiping against the rotation arrests momentum and flings the rotor into reverse with force proportional to gesture velocity.
- **Touchless Finger Brush**: Swiping across outer lobes transfers tangential kinetic energy ($\vec{r} \times \vec{v}_{\text{cursor}}$) without requiring mouse clicks.
- **Grab-to-Stop & Drag**: Left-clicking any lobe instantly halts rotation ($\omega = 0.0\text{ rad/s}$), while continuous dragging allows manual manual positioning and flicking.

### 2. Multi-Phase Rotational Physics
Accurately models physical bearing decay across three damping phases:
$$\frac{d\omega}{dt} = - \Big(k_v \cdot \omega + k_a \cdot \omega |\omega| + k_d \cdot \operatorname{sgn}(\omega)\Big)$$
- **Viscous Bearing Drag ($k_v$)**: Internal lubricant resistance.
- **Aerodynamic Air Resistance ($k_a$)**: Quadratic velocity decay at high RPM.
- **Coulomb Dry Friction ($k_d$)**: Mechanical surface contact that brings low-speed spins to a smooth stop.

---

## 🎨 4 Researched Enthusiast EDC Skins

Rendered 100% procedurally with sub-pixel antialiased vector mathematics (`QPainterPath`):

1. **Torqbar Timascus & Tritium Vials**: Flame-anodized titanium dual-bar spinner featuring iridescent purple, cyan, and gold swirls with embedded self-luminescent green/cyan Tritium gas tubes.
2. **Maelstrom Morph Rotor**: Circular precision rotor with counter-curved turbine vanes that generate a hypnotic Moire optical warp illusion at high RPM.
3. **LAUTIE Cyber-Reactor**: Tactical blackened zirconium chassis with geometric angular mecha fins and glowing red LED conduit indicators.
4. **Classic Obsidian & Ceramic Bearings**: Deep matte graphite tri-lobe body with polished brass outer race rings and individual ceramic ball bearings.

---

## 🖥️ Modern Linux Desktop & Wayland Integration

- **Frameless Alpha Transparency**: Configured with `Qt.WindowType.FramelessWindowHint` and `WA_TranslucentBackground` for borderless rendering.
- **Non-Intrusive Tool Windowing**: Implements `Qt.WindowType.Tool` to float unobtrusively on top while automatically omitting taskbar clutter and dropping behind exclusive fullscreen games and media players.
- **Wayland-Native Dragging**: Employs `QWindow.startSystemMove()` via the center cap or transparent air gaps between lobes, bypassing Wayland coordinate manipulation restrictions.

---

## 🚀 Quick Start & Execution

### Option A: Standalone Binary (No Python setup required)
```bash
/home/rajaskelkar/Fidget/dist/fidget_spinner
```

### Option B: Python Virtual Environment
```bash
# 1. Activate environment
source .venv/bin/activate

# 2. Run the widget
python3 spinner_widget.py
```

### Keyboard Shortcuts
- `1` / `2` / `3` / `4`: Select skin directly.
- `Space`: Cycle skins.
- `F`: Power flick impulse.
- `B`: Brake / stop immediately.
- `T`: Toggle Always-on-Top.
- `H`: Toggle live RPM & speed telemetry HUD.
- `R`: Center widget on primary display.
- `Esc` / `Q`: Close widget.

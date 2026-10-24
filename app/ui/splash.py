"""
BillFlow Suite - Premium Animated Splash Screen
=================================================
Ultra-polished, corporate startup splash screen.
Features:
- Frameless glassmorphic card with layered drop shadow and top ambient gleam
- High-fidelity vector branding logo with pulsating ambient glow halo
- Living pulsating status indicator dot beside dynamic startup stage text
- Floating constellation particles drifting with subtle organic sway
- Dynamic expanding gradient divider with precision easing
- Sleek pill-shaped progress bar with radiant fill, glowing tip bead, and shimmer sweep
- Monospace/numeric percentage readout syncing seamlessly with real startup pipeline
- Full support for 'Reduce motion', minimum visible duration (1.2s), and clean cross-fade
- 100% theme-token compliant (zero hardcoded hex strings, zero setStyleSheet)
"""
import sys
import os
import math
import random
import logging
from pathlib import Path
from typing import Optional, List

from PySide6.QtCore import (
    Qt, QObject, Signal, Property, QPoint, QPointF, QRect, QRectF, QSize,
    QPropertyAnimation, QParallelAnimationGroup, QSequentialAnimationGroup,
    QPauseAnimation, QEasingCurve, QTimer, QElapsedTimer, QSettings
)
from PySide6.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, QFontMetrics, QLinearGradient,
    QRadialGradient, QPainterPath,
    QCursor, QScreen, QGuiApplication, QPixmap, QFontDatabase
)
from PySide6.QtWidgets import (
    QWidget, QApplication, QGraphicsDropShadowEffect
)
from PySide6.QtSvg import QSvgRenderer

from app.branding import (
    APP_NAME, BRAND_NAME, MAKER_NAME, TAGLINE, VERSION, CREDIT_LINE,
    get_asset_path
)
from app.ui.theme.theme_manager import theme_manager
from app.ui.theme.tokens import ThemeTokens

logger = logging.getLogger("billflow.splash")


def _ensure_fonts_loaded():
    """Ensure standard system sans-serif fonts are available across environments."""
    if QApplication.instance() is None:
        return
    try:
        if len(QFontDatabase.families()) == 0:
            for fn in ["segoeui.ttf", "segoeuib.ttf", "segoeuisl.ttf", "segoeuiz.ttf", "arial.ttf"]:
                p = Path(f"C:/Windows/Fonts/{fn}")
                if p.exists():
                    QFontDatabase.addApplicationFont(str(p))
    except Exception:
        pass


_ACTIVE_SPLASH: Optional["SplashScreen"] = None


def is_splash_enabled() -> bool:
    """Check if the splash screen is enabled in settings or flags."""
    if "--no-splash" in sys.argv:
        return False
    if os.environ.get("BILLFLOW_NO_SPLASH", "").lower() in ("1", "true", "yes"):
        return False
    settings = QSettings("BillFlow", "ThemeSystem")
    val = settings.value("show_splash", True)
    if isinstance(val, str):
        return val.lower() in ("true", "1", "yes")
    return bool(val)


def is_reduce_motion_enabled() -> bool:
    """Check if motion reduction is requested."""
    if "--reduce-motion" in sys.argv:
        return True
    if os.environ.get("BILLFLOW_REDUCE_MOTION", "").lower() in ("1", "true", "yes"):
        return True
    settings = QSettings("BillFlow", "ThemeSystem")
    val = settings.value("reduce_motion", False)
    if isinstance(val, str):
        return val.lower() in ("true", "1", "yes")
    return bool(val)


class _Particle:
    """A floating ambient micro-particle that sways and drifts upward."""
    __slots__ = ("x", "y", "radius", "speed", "opacity", "phase")

    def __init__(self, card_w: float, card_h: float):
        self.x = random.uniform(0.04, 0.96) * card_w
        self.y = random.uniform(0.15, 0.95) * card_h
        self.radius = random.uniform(1.0, 2.4)
        self.speed = random.uniform(0.12, 0.38)
        self.opacity = random.uniform(0.10, 0.35)
        self.phase = random.uniform(0.0, 6.28)

    def tick(self, card_h: float):
        self.y -= self.speed
        if self.y < -8.0:
            self.y = card_h + 4.0
            self.opacity = random.uniform(0.10, 0.35)


class SplashScreen(QWidget):
    """
    Ultra-refined animated corporate splash screen.
    Driven by real startup events with zero blocking.
    """

    def __init__(self, parent=None, reduce_motion: Optional[bool] = None):
        super().__init__(parent)
        global _ACTIVE_SPLASH
        _ACTIVE_SPLASH = self

        _ensure_fonts_loaded()

        self.setWindowFlags(
            Qt.SplashScreen | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_DeleteOnClose, False)

        # Motion preference
        self.reduce_motion = (
            reduce_motion if reduce_motion is not None else is_reduce_motion_enabled()
        )

        # State tracking
        self._start_timer = QElapsedTimer()
        self._min_visible_ms = 1200
        self._status_message = "Starting application..."
        self._progress_value = 0.0
        self._is_closing = False
        self._ready_to_close = False
        self._target_window: Optional[QWidget] = None

        # Animated properties
        self._card_scale = 1.0 if self.reduce_motion else 0.94
        self._logo_scale = 1.0 if self.reduce_motion else 0.75
        self._logo_opacity = 1.0 if self.reduce_motion else 0.0
        self._line_expand = 1.0 if self.reduce_motion else 0.0
        self._title_opacity = 1.0 if self.reduce_motion else 0.0
        self._title_offset = 0.0 if self.reduce_motion else 12.0
        self._brand_opacity = 1.0 if self.reduce_motion else 0.0
        self._brand_offset = 0.0 if self.reduce_motion else 10.0
        self._tagline_opacity = 1.0 if self.reduce_motion else 0.0
        self._tagline_offset = 0.0 if self.reduce_motion else 8.0
        self._shimmer_phase = 0.0
        self._idle_pulse = 0.0

        # Animation references
        self._anim_group: Optional[QParallelAnimationGroup] = None
        self._progress_anim: Optional[QPropertyAnimation] = None
        self._fade_anim: Optional[QPropertyAnimation] = None
        self._target_anim: Optional[QPropertyAnimation] = None

        # Load SVG logo or mark fallback
        self._svg_renderer: Optional[QSvgRenderer] = None
        self._load_branding_logo()

        # Frame jitter / smoothness measurement
        self._frame_timer = QElapsedTimer()
        self._last_frame_time = 0
        self.max_frame_gap_ms = 0

        # Ambient Particles
        self._particles: List[_Particle] = []

        # 60 FPS animation timer
        self._tick_timer = QTimer(self)
        self._tick_timer.setInterval(16)
        self._tick_timer.timeout.connect(self._on_tick)

        # Geometry setup (660 x 410 card)
        self._setup_geometry()

        # Connect to theme manager
        theme_manager.theme_changed.connect(lambda _: self.update())

    # --- Qt Properties for QPropertyAnimation ---
    def get_card_scale(self) -> float:
        return self._card_scale

    def set_card_scale(self, val: float):
        self._card_scale = val
        self.update()

    card_scale = Property(float, get_card_scale, set_card_scale)

    def get_logo_scale(self) -> float:
        return self._logo_scale

    def set_logo_scale(self, val: float):
        self._logo_scale = val
        self.update()

    logo_scale = Property(float, get_logo_scale, set_logo_scale)

    def get_logo_opacity(self) -> float:
        return self._logo_opacity

    def set_logo_opacity(self, val: float):
        self._logo_opacity = val
        self.update()

    logo_opacity = Property(float, get_logo_opacity, set_logo_opacity)

    def get_line_expand(self) -> float:
        return self._line_expand

    def set_line_expand(self, val: float):
        self._line_expand = val
        self.update()

    line_expand = Property(float, get_line_expand, set_line_expand)

    def get_title_opacity(self) -> float:
        return self._title_opacity

    def set_title_opacity(self, val: float):
        self._title_opacity = val
        self.update()

    title_opacity = Property(float, get_title_opacity, set_title_opacity)

    def get_title_offset(self) -> float:
        return self._title_offset

    def set_title_offset(self, val: float):
        self._title_offset = val
        self.update()

    title_offset = Property(float, get_title_offset, set_title_offset)

    def get_brand_opacity(self) -> float:
        return self._brand_opacity

    def set_brand_opacity(self, val: float):
        self._brand_opacity = val
        self.update()

    brand_opacity = Property(float, get_brand_opacity, set_brand_opacity)

    def get_brand_offset(self) -> float:
        return self._brand_offset

    def set_brand_offset(self, val: float):
        self._brand_offset = val
        self.update()

    brand_offset = Property(float, get_brand_offset, set_brand_offset)

    def get_tagline_opacity(self) -> float:
        return self._tagline_opacity

    def set_tagline_opacity(self, val: float):
        self._tagline_opacity = val
        self.update()

    tagline_opacity = Property(float, get_tagline_opacity, set_tagline_opacity)

    def get_tagline_offset(self) -> float:
        return self._tagline_offset

    def set_tagline_offset(self, val: float):
        self._tagline_offset = val
        self.update()

    tagline_offset = Property(float, get_tagline_offset, set_tagline_offset)

    def get_progress_value(self) -> float:
        return self._progress_value

    def set_progress_value(self, val: float):
        self._progress_value = val
        self.update()

    progress_value = Property(float, get_progress_value, set_progress_value)

    # --- Setup & Assets ---
    def _load_branding_logo(self):
        """Attempt to load logo.svg from assets/branding; falls back safely to monogram."""
        logo_path = get_asset_path("assets/branding/logo.svg")
        if logo_path.exists():
            try:
                renderer = QSvgRenderer(str(logo_path))
                if renderer.isValid():
                    self._svg_renderer = renderer
                    return
            except Exception as e:
                logger.warning("Failed to parse logo.svg, using monogram: %s", e)
        self._svg_renderer = None

    def _setup_geometry(self):
        """Center the card on the active display, scaling appropriately."""
        app = QApplication.instance()
        screen = QGuiApplication.screenAt(QCursor.pos())
        if not screen and app:
            screen = app.primaryScreen()

        dpi_scale = (screen.logicalDotsPerInch() / 96.0) if screen else 1.0
        geom = screen.availableGeometry() if screen else QRect(0, 0, 1920, 1080)

        card_w = min(int(geom.width() * 0.90), int(660 * dpi_scale))
        card_h = min(int(geom.height() * 0.90), int(410 * dpi_scale))
        self.card_size = QSize(card_w, card_h)

        total_w = card_w + 56
        total_h = card_h + 56
        self.setFixedSize(total_w, total_h)

        pos_x = geom.x() + (geom.width() - total_w) // 2
        pos_y = geom.y() + (geom.height() - total_h) // 2
        self.move(pos_x, pos_y)

        if not self.reduce_motion:
            self._particles = [_Particle(float(card_w), float(card_h)) for _ in range(16)]

    # --- Public API ---
    def show_splash(self):
        """Display the splash screen and trigger coordinated entrance sequence."""
        self._start_timer.start()
        self._frame_timer.start()
        self._last_frame_time = self._frame_timer.elapsed()

        if self.reduce_motion:
            self.setWindowOpacity(1.0)
            self._progress_value = 0.0
            self.show()
            self.raise_()
            return

        self.setWindowOpacity(0.0)
        self.show()
        self.raise_()

        self._start_entrance_animations()
        self._tick_timer.start()

    def set_progress(self, target_value: int, message: str = ""):
        """Smoothly advance progress to target_value (0..100) with message."""
        if message:
            self._status_message = message

        target_fl = max(0.0, min(100.0, float(target_value)))

        if self.reduce_motion:
            self._progress_value = target_fl
            self.update()
            return

        if self._progress_anim and self._progress_anim.state() == QPropertyAnimation.Running:
            self._progress_anim.stop()

        self._progress_anim = QPropertyAnimation(self, b"progress_value")
        self._progress_anim.setDuration(200)
        self._progress_anim.setStartValue(self._progress_value)
        self._progress_anim.setEndValue(target_fl)
        self._progress_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._progress_anim.start()

    def finish(self, target_window: Optional[QWidget] = None):
        """Enforces minimum visible duration (1.2s), then cross-fades into main app."""
        self._target_window = target_window
        self.set_progress(100, "Ready")

        elapsed = self._start_timer.elapsed()
        remaining = max(0, self._min_visible_ms - elapsed)

        if self.reduce_motion:
            self._do_close()
            return

        QTimer.singleShot(remaining, self._start_exit_transition)

    def close_on_error(self):
        """Immediately stop all animations and close splash upon startup error."""
        try:
            if self._anim_group:
                self._anim_group.stop()
            if self._progress_anim:
                self._progress_anim.stop()
            if self._fade_anim:
                self._fade_anim.stop()
            if self._tick_timer:
                self._tick_timer.stop()
            self.hide()
            self.close()
        except Exception as e:
            logger.error("Error closing splash on error: %s", e)

    # --- Internal Animation Sequences ---
    def _start_entrance_animations(self):
        """
        Master non-blocking choreography:
        - Window fade-in (0 to 300ms)
        - Card scale spring (0 to 300ms, OutBack)
        - Logo reveal & breathing glow (160 to 650ms, OutBack)
        - Accent line expansion (250 to 700ms, OutCubic)
        - Cascading typography reveals (350 to 800ms)
        """
        self._anim_group = QParallelAnimationGroup(self)

        # 1. Window Opacity
        anim_win = QPropertyAnimation(self, b"windowOpacity")
        anim_win.setDuration(300)
        anim_win.setStartValue(0.0)
        anim_win.setEndValue(1.0)
        anim_win.setEasingCurve(QEasingCurve.OutCubic)
        self._anim_group.addAnimation(anim_win)

        # 2. Card Scale
        anim_scale = QPropertyAnimation(self, b"card_scale")
        anim_scale.setDuration(300)
        anim_scale.setStartValue(0.94)
        anim_scale.setEndValue(1.0)
        anim_scale.setEasingCurve(QEasingCurve.OutBack)
        self._anim_group.addAnimation(anim_scale)

        # 3. Logo Reveal
        seq_logo = QSequentialAnimationGroup(self._anim_group)
        seq_logo.addAnimation(QPauseAnimation(160))
        par_logo = QParallelAnimationGroup(seq_logo)

        anim_l_scale = QPropertyAnimation(self, b"logo_scale")
        anim_l_scale.setDuration(480)
        anim_l_scale.setStartValue(0.75)
        anim_l_scale.setEndValue(1.0)
        anim_l_scale.setEasingCurve(QEasingCurve.OutBack)
        par_logo.addAnimation(anim_l_scale)

        anim_l_opac = QPropertyAnimation(self, b"logo_opacity")
        anim_l_opac.setDuration(480)
        anim_l_opac.setStartValue(0.0)
        anim_l_opac.setEndValue(1.0)
        par_logo.addAnimation(anim_l_opac)

        seq_logo.addAnimation(par_logo)
        self._anim_group.addAnimation(seq_logo)

        # 4. Accent Line
        seq_line = QSequentialAnimationGroup(self._anim_group)
        seq_line.addAnimation(QPauseAnimation(250))
        anim_line = QPropertyAnimation(self, b"line_expand")
        anim_line.setDuration(450)
        anim_line.setStartValue(0.0)
        anim_line.setEndValue(1.0)
        anim_line.setEasingCurve(QEasingCurve.OutCubic)
        seq_line.addAnimation(anim_line)
        self._anim_group.addAnimation(seq_line)

        # 5. Title Reveal
        seq_title = QSequentialAnimationGroup(self._anim_group)
        seq_title.addAnimation(QPauseAnimation(350))
        par_title = QParallelAnimationGroup(seq_title)

        anim_t_opac = QPropertyAnimation(self, b"title_opacity")
        anim_t_opac.setDuration(260)
        anim_t_opac.setStartValue(0.0)
        anim_t_opac.setEndValue(1.0)
        par_title.addAnimation(anim_t_opac)

        anim_t_off = QPropertyAnimation(self, b"title_offset")
        anim_t_off.setDuration(260)
        anim_t_off.setStartValue(12.0)
        anim_t_off.setEndValue(0.0)
        anim_t_off.setEasingCurve(QEasingCurve.OutCubic)
        par_title.addAnimation(anim_t_off)

        seq_title.addAnimation(par_title)
        self._anim_group.addAnimation(seq_title)

        # 6. Brand Subhead Reveal
        seq_brand = QSequentialAnimationGroup(self._anim_group)
        seq_brand.addAnimation(QPauseAnimation(450))
        par_brand = QParallelAnimationGroup(seq_brand)

        anim_b_opac = QPropertyAnimation(self, b"brand_opacity")
        anim_b_opac.setDuration(260)
        anim_b_opac.setStartValue(0.0)
        anim_b_opac.setEndValue(1.0)
        par_brand.addAnimation(anim_b_opac)

        anim_b_off = QPropertyAnimation(self, b"brand_offset")
        anim_b_off.setDuration(260)
        anim_b_off.setStartValue(10.0)
        anim_b_off.setEndValue(0.0)
        anim_b_off.setEasingCurve(QEasingCurve.OutCubic)
        par_brand.addAnimation(anim_b_off)

        seq_brand.addAnimation(par_brand)
        self._anim_group.addAnimation(seq_brand)

        # 7. Tagline Reveal
        seq_tag = QSequentialAnimationGroup(self._anim_group)
        seq_tag.addAnimation(QPauseAnimation(550))
        par_tag = QParallelAnimationGroup(seq_tag)

        anim_g_opac = QPropertyAnimation(self, b"tagline_opacity")
        anim_g_opac.setDuration(240)
        anim_g_opac.setStartValue(0.0)
        anim_g_opac.setEndValue(1.0)
        par_tag.addAnimation(anim_g_opac)

        anim_g_off = QPropertyAnimation(self, b"tagline_offset")
        anim_g_off.setDuration(240)
        anim_g_off.setStartValue(8.0)
        anim_g_off.setEndValue(0.0)
        anim_g_off.setEasingCurve(QEasingCurve.OutCubic)
        par_tag.addAnimation(anim_g_off)

        seq_tag.addAnimation(par_tag)
        self._anim_group.addAnimation(seq_tag)

        self._anim_group.start()

    def _start_exit_transition(self):
        """Cross-fade out splash over 220ms while target_window fades in."""
        if self._is_closing:
            return
        self._is_closing = True

        if self._tick_timer:
            self._tick_timer.stop()

        target = self._target_window
        if target:
            target.setWindowOpacity(0.0)
            target.show()
            target.raise_()
            target.activateWindow()

            self._target_anim = QPropertyAnimation(target, b"windowOpacity")
            self._target_anim.setDuration(220)
            self._target_anim.setStartValue(0.0)
            self._target_anim.setEndValue(1.0)
            self._target_anim.setEasingCurve(QEasingCurve.InOutQuad)
            self._target_anim.start()

        self._fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self._fade_anim.setDuration(220)
        self._fade_anim.setStartValue(self.windowOpacity())
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.setEasingCurve(QEasingCurve.InOutQuad)
        self._fade_anim.finished.connect(self._do_close)
        self._fade_anim.start()

    def _do_close(self):
        """Complete closure and transfer active focus."""
        target = self._target_window
        if target:
            target.setWindowOpacity(1.0)
            target.show()
            target.raise_()
            target.activateWindow()

        self.hide()
        self.close()

    def _on_tick(self):
        """60 FPS continuous animation updates."""
        now = self._frame_timer.elapsed()
        gap = now - self._last_frame_time
        self._last_frame_time = now

        if hasattr(self, "_first_tick_done") and self._first_tick_done:
            if gap > self.max_frame_gap_ms:
                self.max_frame_gap_ms = gap
        else:
            self._first_tick_done = True

        # Shimmer progress sweep (wraps smoothly every 1.8s)
        self._shimmer_phase = (self._shimmer_phase + 0.014) % 1.0

        # Logo glow & dot breathing pulse (sine wave)
        t = now / 1000.0
        self._idle_pulse = (math.sin(t * 2.8) + 1.0) / 2.0

        # Particle drift
        card_h = float(self.card_size.height())
        for p in self._particles:
            p.tick(card_h)

        self.update()

    # --- Pure Theme-Compliant Color Derivations ---
    def _color_alpha(self, color_str: str, alpha: int) -> QColor:
        """Create a QColor with overridden alpha."""
        c = QColor(color_str)
        c.setAlpha(max(0, min(255, alpha)))
        return c

    # --- Pure Painting (Zero CSS, Zero Hardcoded Hex) ---
    def paintEvent(self, event):
        """Render the complete luxury splash canvas."""
        tokens = theme_manager.tokens
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

        margin = 28.0
        card_w = float(self.card_size.width())
        card_h = float(self.card_size.height())
        card_rect = QRectF(margin, margin, card_w, card_h)
        card_cx = card_rect.center().x()
        card_cy = card_rect.center().y()

        # Apply Card Entrance Scale Transform
        if self._card_scale != 1.0:
            center = card_rect.center()
            painter.translate(center)
            painter.scale(self._card_scale, self._card_scale)
            painter.translate(-center)

        # -----------------------------------------------------------------
        # 1. LUXURY DROP SHADOW (6 soft concentric diffused rings)
        # -----------------------------------------------------------------
        shadow_source = tokens.bg if tokens.is_dark else tokens.sidebar_bg
        for i in range(6, 0, -1):
            alpha = int(18 * (1.0 - (i / 7.0)))
            sc = self._color_alpha(shadow_source, alpha)
            painter.setPen(QPen(sc, float(i * 2.2)))
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(card_rect.adjusted(-i, -i, i, i), 18.0, 18.0)

        # -----------------------------------------------------------------
        # 2. MAIN CARD SURFACE with subtle depth gradient
        # -----------------------------------------------------------------
        card_gradient = QLinearGradient(card_rect.topLeft(), card_rect.bottomLeft())
        if tokens.is_dark:
            card_gradient.setColorAt(0.0, QColor(tokens.surface).lighter(108))
            card_gradient.setColorAt(1.0, QColor(tokens.surface))
        else:
            card_gradient.setColorAt(0.0, QColor(tokens.surface))
            card_gradient.setColorAt(1.0, QColor(tokens.surface).darker(103))

        painter.setPen(QPen(self._color_alpha(tokens.border, 90), 1.0))
        painter.setBrush(QBrush(card_gradient))
        painter.drawRoundedRect(card_rect, 16.0, 16.0)

        # -----------------------------------------------------------------
        # 3. TOP AMBIENT GLEAM (frosted glass specular highlight)
        # -----------------------------------------------------------------
        gleam_rect = card_rect.adjusted(1.5, 1.5, -1.5, -1.5)
        gleam_grad = QLinearGradient(gleam_rect.topLeft(), gleam_rect.bottomLeft())
        gleam_color = tokens.text_on_accent if tokens.is_dark else tokens.surface_elevated
        gleam_grad.setColorAt(0.0, self._color_alpha(gleam_color, 45 if tokens.is_dark else 25))
        gleam_grad.setColorAt(0.15, self._color_alpha(gleam_color, 10))
        gleam_grad.setColorAt(1.0, self._color_alpha(gleam_color, 0))
        painter.setPen(QPen(QBrush(gleam_grad), 1.2))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(gleam_rect, 15.0, 15.0)

        # -----------------------------------------------------------------
        # 4. FLOATING CONSTELLATION PARTICLES
        # -----------------------------------------------------------------
        if not self.reduce_motion and self._particles:
            now_sec = self._frame_timer.elapsed() / 1000.0
            for p in self._particles:
                px = card_rect.left() + p.x + math.sin(now_sec * 0.9 + p.phase) * 3.5
                py = card_rect.top() + p.y
                if card_rect.contains(QPointF(px, py)):
                    dot_color = self._color_alpha(tokens.accent, int(255 * p.opacity * 0.40))
                    painter.setPen(Qt.NoPen)
                    painter.setBrush(QBrush(dot_color))
                    painter.drawEllipse(QPointF(px, py), p.radius, p.radius)

        # -----------------------------------------------------------------
        # 5. LOGO GLOW HALO & EMBLEM
        # -----------------------------------------------------------------
        logo_y = card_rect.top() + 34.0
        logo_box_size = 78.0
        logo_center = QPointF(card_cx, logo_y + (logo_box_size / 2.0))
        logo_rect = QRectF(card_cx - (logo_box_size / 2.0), logo_y, logo_box_size, logo_box_size)

        # Pulsating Radial Glow Halo
        if self._logo_opacity > 0.0 and not self.reduce_motion:
            glow_rad = logo_box_size * 1.15
            radial_glow = QRadialGradient(logo_center, glow_rad)
            peak_alpha = int(32 * self._idle_pulse + 16)
            radial_glow.setColorAt(0.0, self._color_alpha(tokens.accent, peak_alpha))
            radial_glow.setColorAt(0.55, self._color_alpha(tokens.accent, int(peak_alpha * 0.35)))
            radial_glow.setColorAt(1.0, self._color_alpha(tokens.accent, 0))
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(radial_glow))
            painter.drawEllipse(logo_center, glow_rad, glow_rad)

        if self._logo_opacity > 0.0:
            painter.save()
            painter.setOpacity(self._logo_opacity)
            if self._logo_scale != 1.0:
                painter.translate(logo_center)
                painter.scale(self._logo_scale, self._logo_scale)
                painter.translate(-logo_center)

            if self._svg_renderer and self._svg_renderer.isValid():
                self._svg_renderer.render(painter, logo_rect)
            else:
                # Monogram fallback inside stylized accent shield
                mono_grad = QLinearGradient(logo_rect.topLeft(), logo_rect.bottomRight())
                mono_grad.setColorAt(0.0, QColor(tokens.accent))
                mono_grad.setColorAt(1.0, QColor(tokens.accent).darker(125))
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(mono_grad))
                painter.drawRoundedRect(logo_rect, 22.0, 22.0)

                painter.setPen(QPen(QColor(tokens.text_on_accent)))
                font_mono = QFont("Segoe UI", 26, QFont.Bold)
                font_mono.setStyleHint(QFont.SansSerif)
                font_mono.setLetterSpacing(QFont.AbsoluteSpacing, 1.5)
                painter.setFont(font_mono)
                painter.drawText(logo_rect, Qt.AlignCenter, "BA")

            painter.restore()

        # -----------------------------------------------------------------
        # 6. APP TITLE ("BillFlow Suite")
        # -----------------------------------------------------------------
        title_y = logo_y + logo_box_size + 18.0 + self._title_offset
        if self._title_opacity > 0.0:
            painter.save()
            painter.setOpacity(self._title_opacity)
            painter.setPen(QPen(QColor(tokens.text_primary)))
            font_title = QFont("Segoe UI", 23, QFont.Bold)
            font_title.setStyleHint(QFont.SansSerif)
            font_title.setLetterSpacing(QFont.AbsoluteSpacing, 1.2)
            painter.setFont(font_title)
            title_rect = QRectF(card_rect.left(), title_y, card_w, 34.0)
            painter.drawText(title_rect, Qt.AlignCenter, APP_NAME)
            painter.restore()

        # -----------------------------------------------------------------
        # 7. ELEGANT EXPANDING ACCENT DIVIDER
        # -----------------------------------------------------------------
        line_y = title_y + 38.0
        if self._line_expand > 0.0:
            full_line_w = 170.0
            cur_line_w = full_line_w * self._line_expand
            line_x1 = card_cx - (cur_line_w / 2.0)
            line_x2 = card_cx + (cur_line_w / 2.0)

            line_gradient = QLinearGradient(line_x1, line_y, line_x2, line_y)
            line_gradient.setColorAt(0.0, self._color_alpha(tokens.accent, 20))
            line_gradient.setColorAt(0.3, QColor(tokens.accent))
            line_gradient.setColorAt(0.7, QColor(tokens.accent))
            line_gradient.setColorAt(1.0, self._color_alpha(tokens.accent, 20))
            painter.setPen(QPen(QBrush(line_gradient), 2.0, Qt.SolidLine, Qt.RoundCap))
            painter.drawLine(QPointF(line_x1, line_y), QPointF(line_x2, line_y))

        # -----------------------------------------------------------------
        # 8. ENTERPRISE BRAND ("BINAPANI AUTOMATION")
        # -----------------------------------------------------------------
        brand_y = line_y + 12.0 + self._brand_offset
        if self._brand_opacity > 0.0:
            painter.save()
            painter.setOpacity(self._brand_opacity)
            painter.setPen(QPen(QColor(tokens.accent)))
            font_brand = QFont("Segoe UI", 12, QFont.DemiBold)
            font_brand.setStyleHint(QFont.SansSerif)
            font_brand.setLetterSpacing(QFont.AbsoluteSpacing, 3.2)
            painter.setFont(font_brand)
            brand_rect = QRectF(card_rect.left(), brand_y, card_w, 20.0)
            painter.drawText(brand_rect, Qt.AlignCenter, BRAND_NAME.upper())
            painter.restore()

        # -----------------------------------------------------------------
        # 9. TAGLINE ("Offline Accounting & Billing")
        # -----------------------------------------------------------------
        tagline_y = brand_y + 24.0 + self._tagline_offset
        if self._tagline_opacity > 0.0:
            painter.save()
            painter.setOpacity(self._tagline_opacity)
            painter.setPen(QPen(QColor(tokens.text_secondary)))
            font_tag = QFont("Segoe UI", 11, QFont.Normal)
            font_tag.setStyleHint(QFont.SansSerif)
            font_tag.setLetterSpacing(QFont.AbsoluteSpacing, 0.6)
            painter.setFont(font_tag)
            tag_rect = QRectF(card_rect.left(), tagline_y, card_w, 20.0)
            painter.drawText(tag_rect, Qt.AlignCenter, TAGLINE)
            painter.restore()

        # -----------------------------------------------------------------
        # 10. REFINED PROGRESS SECTION
        # -----------------------------------------------------------------
        bar_w = card_w - 110.0
        bar_x = card_rect.left() + 55.0
        bar_y = card_rect.bottom() - 68.0
        bar_h = 5.5

        # Status Line above bar: Pulsing Activity Dot + Message + Percentage
        status_y = bar_y - 24.0
        dot_cx = bar_x + 5.0
        dot_cy = status_y + 9.0

        # Living Breathing Activity Dot
        if not self.reduce_motion and self._progress_value < 100.0:
            dot_alpha = int(140 + 115 * self._idle_pulse)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(self._color_alpha(tokens.accent, dot_alpha)))
            painter.drawEllipse(QPointF(dot_cx, dot_cy), 3.2, 3.2)
        elif self._progress_value >= 100.0:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor(tokens.success)))
            painter.drawEllipse(QPointF(dot_cx, dot_cy), 3.2, 3.2)

        # Message Text
        msg_rect = QRectF(bar_x + 16.0, status_y, bar_w - 70.0, 18.0)
        painter.setPen(QPen(QColor(tokens.text_muted)))
        font_status = QFont("Segoe UI", 10, QFont.Normal)
        font_status.setStyleHint(QFont.SansSerif)
        painter.setFont(font_status)
        painter.drawText(msg_rect, Qt.AlignLeft | Qt.AlignVCenter, self._status_message)

        # Percentage Text (Aligned Right)
        pct_rect = QRectF(bar_x + bar_w - 50.0, status_y, 50.0, 18.0)
        pct_str = f"{int(self._progress_value)}%"
        font_pct = QFont("Segoe UI", 10, QFont.DemiBold)
        font_pct.setStyleHint(QFont.SansSerif)
        painter.setFont(font_pct)
        painter.drawText(pct_rect, Qt.AlignRight | Qt.AlignVCenter, pct_str)

        # Progress Track
        track_rect = QRectF(bar_x, bar_y, bar_w, bar_h)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(self._color_alpha(tokens.input_bg, 160)))
        painter.drawRoundedRect(track_rect, bar_h / 2.0, bar_h / 2.0)

        # Progress Fill
        fill_w = max(0.0, min(bar_w, bar_w * (self._progress_value / 100.0)))
        if fill_w > 0.0:
            fill_rect = QRectF(bar_x, bar_y, fill_w, bar_h)
            fill_grad = QLinearGradient(fill_rect.left(), bar_y, fill_rect.right(), bar_y)
            fill_grad.setColorAt(0.0, QColor(tokens.accent))
            fill_grad.setColorAt(1.0, QColor(tokens.accent).lighter(122))
            painter.setBrush(QBrush(fill_grad))
            painter.drawRoundedRect(fill_rect, bar_h / 2.0, bar_h / 2.0)

            # Shimmer highlight sweep
            if self._progress_value < 100.0 and not self.reduce_motion and fill_w > 16.0:
                shimmer_x = bar_x + (fill_w * self._shimmer_phase)
                shim_grad = QLinearGradient(shimmer_x - 35.0, bar_y, shimmer_x + 35.0, bar_y)
                shim_col = tokens.text_on_accent if tokens.is_dark else tokens.surface
                shim_grad.setColorAt(0.0, self._color_alpha(shim_col, 0))
                shim_grad.setColorAt(0.5, self._color_alpha(shim_col, 110))
                shim_grad.setColorAt(1.0, self._color_alpha(shim_col, 0))
                painter.setBrush(QBrush(shim_grad))
                painter.drawRoundedRect(fill_rect, bar_h / 2.0, bar_h / 2.0)

            # Leading Edge Glowing Bead
            if not self.reduce_motion and fill_w > 6.0 and self._progress_value < 100.0:
                bead_x = bar_x + fill_w
                bead_y = bar_y + (bar_h / 2.0)
                bead_rad = QRadialGradient(QPointF(bead_x, bead_y), 7.0)
                bead_rad.setColorAt(0.0, self._color_alpha(tokens.accent, 95))
                bead_rad.setColorAt(0.6, self._color_alpha(tokens.accent, 35))
                bead_rad.setColorAt(1.0, self._color_alpha(tokens.accent, 0))
                painter.setBrush(QBrush(bead_rad))
                painter.drawEllipse(QPointF(bead_x, bead_y), 7.0, 7.0)

        # -----------------------------------------------------------------
        # 11. FOOTER: Credit Line & Version
        # -----------------------------------------------------------------
        footer_y = card_rect.bottom() - 28.0
        footer_rect = QRectF(bar_x, footer_y, bar_w, 18.0)
        painter.setPen(QPen(self._color_alpha(tokens.text_muted, 150)))
        font_foot = QFont("Segoe UI", 9, QFont.Normal)
        font_foot.setStyleHint(QFont.SansSerif)
        painter.setFont(font_foot)

        # Left: "Made by Surjyakamal Saha"
        painter.drawText(footer_rect, Qt.AlignLeft | Qt.AlignVCenter, CREDIT_LINE)

        # Right: Version "v1.0.0"
        painter.drawText(footer_rect, Qt.AlignRight | Qt.AlignVCenter, f"v{VERSION}")

        # Subtle centered separator dot
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(self._color_alpha(tokens.text_muted, 70)))
        painter.drawEllipse(QPointF(card_cx, footer_y + 9.0), 1.6, 1.6)

        painter.end()

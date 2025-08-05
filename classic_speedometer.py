from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QRectF, QPointF, QTimer
from PyQt5.QtGui import QPainter, QPen, QColor, QFont, QConicalGradient, QPainterPath, QRadialGradient
import math

class ClassicSpeedometer(QWidget):
    def __init__(self, max_speed=100, parent=None):
        super().__init__(parent)
        self.max_speed = max_speed
        self.current_speed = 0
        self.target_speed = 0
        self.hovered = False
        self.is_dark_mode = True  # Kendi sisteminden alınmalı

        self.setMinimumSize(320, 320)
        self.setMaximumSize(600, 600)
        self.setMouseTracking(True)

        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self._animate_speed)
        self.animation_timer.start(16)  # 60 FPS

    def set_speed(self, speed):
        self.target_speed = max(0, min(speed, self.max_speed))

    def _animate_speed(self):
        if abs(self.current_speed - self.target_speed) < 0.5:
            self.current_speed = self.target_speed
        else:
            self.current_speed += (self.target_speed - self.current_speed) * 0.1
        self.update()

    def enterEvent(self, event):
        self.hovered = True
        self.update()

    def leaveEvent(self, event):
        self.hovered = False
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect()
        center = rect.center()
        radius = min(rect.width(), rect.height()) / 2 * 0.85

        # === RENKLER ===
        background_color = QColor("#121212") if self.is_dark_mode else QColor("#F4F4F4")
        foreground_color = QColor("#FFFFFF") if self.is_dark_mode else QColor("#000000")
        accent_color = QColor("#3DDC97")
        needle_color = QColor("#FFFFFF") if self.is_dark_mode else QColor("#000000")

        # === Arka Plan ===
        painter.setBrush(background_color)
        painter.setPen(Qt.NoPen)
        painter.drawRect(rect)

        # === Hover Glow ===
        glow_gradient = QRadialGradient(center, radius * 1.2)
        if self.hovered:
            glow_gradient.setColorAt(0, QColor(60, 220, 150, 120))
        else:
            glow_gradient.setColorAt(0, QColor(0, 0, 0, 0))
        glow_gradient.setColorAt(1, QColor(0, 0, 0, 0))
        painter.setBrush(glow_gradient)
        painter.drawEllipse(center, radius * 1.1, radius * 1.1)

        # === Dial background ===
        dial_gradient = QRadialGradient(center, radius)
        dial_gradient.setColorAt(0, QColor("#1E1E1E") if self.is_dark_mode else QColor("#FFFFFF"))
        dial_gradient.setColorAt(1, background_color)
        painter.setBrush(dial_gradient)
        painter.drawEllipse(center, radius, radius)

        # === Arc ===
        arc_rect = QRectF(center.x() - radius, center.y() - radius, 2 * radius, 2 * radius)
        start_angle = 210
        span_angle = -240
        gradient = QConicalGradient(center, start_angle - 90)
        gradient.setColorAt(0.0, QColor(61, 220, 151, 200))
        gradient.setColorAt(0.5, QColor(255, 159, 28, 200))
        gradient.setColorAt(1.0, QColor(255, 94, 91, 200))
        pen = QPen(gradient, radius * 0.08, Qt.SolidLine, Qt.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawArc(arc_rect, start_angle * 16, span_angle * 16)

        # === Needle ===
        angle_deg = start_angle - (self.current_speed / self.max_speed) * abs(span_angle)
        angle_rad = math.radians(angle_deg)
        needle_length = radius * 0.75
        needle_width = radius * 0.04

        base_left = QPointF(
            center.x() + math.cos(angle_rad + math.pi / 2) * needle_width,
            center.y() - math.sin(angle_rad + math.pi / 2) * needle_width
        )
        base_right = QPointF(
            center.x() + math.cos(angle_rad - math.pi / 2) * needle_width,
            center.y() - math.sin(angle_rad - math.pi / 2) * needle_width
        )
        tip = QPointF(
            center.x() + math.cos(angle_rad) * needle_length,
            center.y() - math.sin(angle_rad) * needle_length
        )
        needle_path = QPainterPath()
        needle_path.moveTo(base_left)
        needle_path.lineTo(tip)
        needle_path.lineTo(base_right)
        needle_path.closeSubpath()
        painter.setBrush(needle_color)
        painter.setPen(Qt.NoPen)
        painter.drawPath(needle_path)

        # === Center circle ===
        painter.setBrush(accent_color)
        painter.drawEllipse(center, radius * 0.06, radius * 0.06)

        # === Speed Text ===
        painter.setPen(foreground_color)
        font_speed = QFont("Segoe UI", int(radius * 0.18), QFont.Bold)
        painter.setFont(font_speed)
        speed_text = f"{self.current_speed:.1f}"
        speed_rect = QRectF(center.x() - radius / 2, center.y() + radius * 0.05, radius, radius / 2)
        painter.drawText(speed_rect, Qt.AlignCenter, speed_text)

        # === Mbps label ===
        font_label = QFont("Segoe UI", int(radius * 0.1))
        painter.setFont(font_label)
        mbps_rect = QRectF(center.x() - radius / 2, center.y() + radius * 0.45, radius, radius / 3)
        painter.drawText(mbps_rect, Qt.AlignCenter, "Mbps")

        # === Tick marks ===
        tick_pen = QPen(foreground_color)
        tick_pen.setWidthF(2)
        painter.setPen(tick_pen)
        for i in range(11):
            tick_angle = start_angle - i * (abs(span_angle) / 10)
            tick_rad = math.radians(tick_angle)
            x1 = center.x() + math.cos(tick_rad) * radius * 0.85
            y1 = center.y() - math.sin(tick_rad) * radius * 0.85
            x2 = center.x() + math.cos(tick_rad) * radius * 0.95
            y2 = center.y() - math.sin(tick_rad) * radius * 0.95
            painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))



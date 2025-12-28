# src/ui/radar.py
# 2025年终极增强雷达窗（透视ESP + 距离 + 血条 + 骨骼线）

from PyQt5.QtWidgets import QDialog, QVBoxLayout
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont

from src.core.yolo_ai import visual_core
from src.core.screenshot import game_capture
from src.config.config import load_config

import math

class RadarWindow(QDialog):
    """
    增强雷达窗（同时作为透视ESP叠加窗）
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("安静AI - 增强雷达（透视ESP）")
        self.setFixedSize(500, 500)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        self.radar_widget = EnhancedRadarWidget(self)
        layout.addWidget(self.radar_widget)
        self.setLayout(layout)

        # 实时更新
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.radar_widget.update_scene)
        self.timer.start(30)  # ~33FPS，流畅不卡

class EnhancedRadarWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.targets = []
        self.config = load_config()

    def update_scene(self):
        img = game_capture.capture()
        if img is not None:
            self.targets = visual_core.infer(img, conf=0.35, classes=[0])
        self.update()

    def paintEvent(self, event):
        qp = QPainter(self)
        qp.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        cx, cy = w // 2, h // 2
        radius = min(cx, cy) - 30

        # 背景半透明圆
        qp.setBrush(QBrush(QColor(20, 30, 50, 200)))
        qp.setPen(QPen(QColor(100, 200, 255, 180), 3))
        qp.drawEllipse(cx - radius, cy - radius, radius * 2, radius * 2)

        # 网格
        qp.setPen(QPen(QColor(60, 120, 180, 100), 1, Qt.DashLine))
        for i in range(1, 5):
            r = radius * i // 5
            qp.drawEllipse(cx - r, cy - r, r * 2, r * 2)

        # 自己（中心）
        qp.setBrush(QBrush(QColor(0, 255, 100)))
        qp.setPen(QPen(QColor(0, 200, 80), 3))
        qp.drawEllipse(cx - 15, cy - 15, 30, 30)

        # 朝向箭头（模拟玩家视角）
        qp.setBrush(QBrush(QColor(0, 180, 255)))
        qp.setPen(QPen(QColor(0, 140, 255), 4))
        qp.drawLine(cx, cy, cx, cy - radius + 20)

        if not self.targets:
            qp.setPen(QColor(200, 200, 200))
            qp.setFont(QFont("Microsoft YaHei", 12))
            qp.drawText(self.rect(), Qt.AlignCenter, "无目标")
            return

        # ESP颜色（从配置读取）
        esp_color = QColor(self.config.get("game_params", {}).get("CF", {}).get("esp_color", "#FF6464"))

        for target in self.targets:
            if "keypoints" not in target or "box" not in target:
                continue

            box = target["box"]
            kps = target["keypoints"]

            # 计算敌人中心相对位置（用于雷达点）
            box_center_x = (box[0] + box[2]) / 2
            box_center_y = (box[1] + box[3]) / 2
            rel_x = (box_center_x - w / 2) / radius
            rel_y = (box_center_y - h / 2) / radius
            distance = math.hypot(rel_x, rel_y) * 100  # 模拟距离

            ex = cx + rel_x * radius * 0.9
            ey = cy + rel_y * radius * 0.9

            # 雷达点
            qp.setBrush(QBrush(QColor(255, 60, 60)))
            qp.setPen(QPen(QColor(255, 0, 0), 2))
            qp.drawEllipse(int(ex - 10), int(ey - 10), 20, 20)

            # 名字 + 距离
            name = target.get("name", "敌人")
            qp.setPen(QColor(255, 255, 255))
            qp.setFont(QFont("Microsoft YaHei", 9))
            qp.drawText(int(ex + 15), int(ey), f"{name} {int(distance)}m")

            # 模拟血条
            hp = random.randint(30, 100)  # 模拟血量
            bar_width = 60
            bar_height = 8
            qp.setBrush(QBrush(QColor(100, 100, 100)))
            qp.drawRect(int(ex - bar_width//2), int(ey - 25), bar_width, bar_height)
            qp.setBrush(QBrush(QColor(0, 255, 0) if hp > 50 else QColor(255, 200, 0) if hp > 30 else QColor(255, 0, 0)))
            qp.drawRect(int(ex - bar_width//2), int(ey - 25), int(bar_width * hp / 100), bar_height)

            # 骨骼线（COCO标准关键连接）
            connections = [
                (0, 1), (1, 2), (0, 3), (3, 4),  # 头
                (5, 6), (5, 7), (7, 9), (6, 8), (8, 10),  # 上身手臂
                (5, 11), (6, 12), (11, 13), (12, 14)  # 下身腿
            ]
            qp.setPen(QPen(esp_color, 3))
            for a, b in connections:
                if a < len(kps) and b < len(kps):
                    ax, ay = kps[a]
                    bx, by = kps[b]
                    if ax > 0 and ay > 0 and bx > 0 and by > 0:
                        # 投影到雷达相对位置（简化）
                        proj_ax = cx + (ax - w/2) / radius * radius * 0.8
                        proj_ay = cy + (ay - h/2) / radius * radius * 0.8
                        proj_bx = cx + (bx - w/2) / radius * radius * 0.8
                        proj_by = cy + (by - h/2) / radius * radius * 0.8
                        qp.drawLine(int(proj_ax), int(proj_ay), int(proj_bx), int(proj_by))

        qp.end()
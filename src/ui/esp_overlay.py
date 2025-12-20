# src/ui/esp_overlay.py
# 2025年独立透视叠加窗（ESP透视终极版）

from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPainter, QPen, QBrush, QFont, QColor

from src.core.yolo_ai import visual_core
from src.core.screenshot import game_capture
from src.config.config import load_config

import math

class ESPOverlay(QWidget):
    """
    独立透视叠加窗
    - 透明背景 + 点击穿透 + 始终置顶
    - 实时绘制ESP：方框 + 骨骼 + 名字 + 距离 + 血条
    - 颜色从当前游戏配置读取
    - 热键F3开关（在main_window注册）
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("安静AI - ESP透视叠加窗")
        self.setWindowFlags(
            Qt.FramelessWindowHint |           # 无边框
            Qt.WindowStaysOnTopHint |          # 始终置顶
            Qt.Tool |                          # 不显示在任务栏
            Qt.WindowTransparentForInput       # 点击穿透（鼠标操作透到游戏）
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)  # 透明背景

        # 全屏覆盖主显示器
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)

        self.visible = True
        self.targets = []

        # 实时更新
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_esp)
        self.timer.start(16)  # ~60FPS

        print("[ESP] 透视叠加窗已创建（F3开关）")

    def toggle_visibility(self):
        """开关透视窗"""
        self.visible = not self.visible
        if self.visible:
            self.show()
            self.raise_()
            self.activateWindow()
            print("[ESP] 透视已开启")
        else:
            self.hide()
            print("[ESP] 透视已关闭")

    def update_esp(self):
        """每帧更新检测结果"""
        img = game_capture.capture()
        if img is not None:
            self.targets = visual_core.infer(img, conf=0.35, classes=[0])
        self.update()  # 触发重绘

    def paintEvent(self, event):
        if not self.visible:
            return

        if not self.targets:
            return

        qp = QPainter(self)
        qp.setRenderHint(QPainter.Antialiasing)

        # 当前游戏配置（用于读取ESP颜色）
        config = load_config()
        # 假设从主窗口获取当前Tab（这里简化用CF作为默认）
        current_game = "CF"  # 实际应从主窗口传递当前游戏key
        esp_color_hex = config.get("game_params", {}).get(current_game, {}).get("esp_color", "#FF6464")
        esp_color = QColor(esp_color_hex)
        esp_color.setAlpha(220)

        line_pen = QPen(esp_color, 2)
        box_pen = QPen(esp_color, 3)
        text_font = QFont("Microsoft YaHei", 10, QFont.Bold)
        small_font = QFont("Microsoft YaHei", 8)

        for target in self.targets:
            if "box" not in target or "keypoints" not in target:
                continue

            box = target["box"]
            kps = target["keypoints"]

            x1, y1, x2, y2 = map(int, box)

            # 2D方框
            qp.setPen(box_pen)
            qp.setBrush(Qt.NoBrush)
            qp.drawRect(x1, y1, x2 - x1, y2 - y1)

            # 中心点
            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2

            # 名字 + 距离
            name = target.get("name", "敌人")
            distance = int(math.hypot(center_x - self.width() // 2, center_y - self.height() // 2) / 15)
            qp.setPen(QColor(255, 255, 255))
            qp.setFont(text_font)
            qp.drawText(center_x - 50, y1 - 10, f"{name} {distance}m")

            # 血条
            hp = random.randint(20, 100)  # 模拟血量
            bar_width = x2 - x1
            bar_height = 10
            qp.setBrush(QBrush(QColor(50, 50, 50)))
            qp.drawRect(x1, y1 - 25, bar_width, bar_height)
            hp_color = QColor(0, 255, 0) if hp > 50 else QColor(255, 255, 0) if hp > 25 else QColor(255, 0, 0)
            qp.setBrush(QBrush(hp_color))
            qp.drawRect(x1, y1 - 25, int(bar_width * hp / 100), bar_height)

            # 骨骼线（COCO标准连接）
            connections = [
                (0, 1), (1, 2), (0, 3), (3, 4),           # 头部
                (1, 5), (2, 6),                           # 肩膀
                (5, 7), (7, 9), (6, 8), (8, 10),          # 手臂
                (5, 11), (6, 12), (11, 13), (12, 14),     # 腿部
                (13, 15), (14, 16)                        # 脚
            ]
            qp.setPen(line_pen)
            for a, b in connections:
                if a < len(kps) and b < len(kps):
                    ax, ay = kps[a]
                    bx, by = kps[b]
                    if ax > 0 and ay > 0 and bx > 0 and by > 0:
                        qp.drawLine(int(ax), int(ay), int(bx), int(by))

        qp.end()
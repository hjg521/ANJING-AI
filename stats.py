# ================== src/ui/stats.py ==================
from PyQt5.QtWidgets import QWidget, QDialog, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPainter, QColor, QPen, QFont
import random
import math

class StatsWindow(QDialog):
    """
    今日击杀/KD/最远狙距等曲线图统计小窗
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("今日战绩统计")
        self.setFixedSize(380, 340)
        layout = QVBoxLayout()
        layout.addWidget(QLabel("今日击杀/爆头/最远狙击等曲线（仅Demo）"))
        self.stats_view = StatsCurveWidget(self)
        layout.addWidget(self.stats_view)
        self.setLayout(layout)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.stats_view.update_data)
        self._timer.start(2000)  # 每2秒模拟数据刷新

class StatsCurveWidget(QWidget):
    """
    曲线图及数据模拟
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data = {
            "kill": [random.randint(0, 10) for _ in range(12)],
            "kd": [round(random.uniform(0.5, 3.0), 2) for _ in range(12)],
            "snipe": [random.randint(20, 300) for _ in range(12)]
        }
        self.ptr = 12

    def update_data(self):
        # 模拟新一轮成绩
        if len(self.data["kill"]) >= 30:
            for k in self.data: self.data[k] = self.data[k][1:]
        self.data["kill"].append(random.randint(0, 18))
        self.data["kd"].append(round(random.uniform(0.7, 4.3), 2))
        self.data["snipe"].append(random.randint(33, 366))
        self.ptr += 1
        self.update()

    def paintEvent(self, event):
        qp = QPainter(self)
        qp.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        margin = 40
        rect_w = w - margin * 2
        rect_h = h - margin * 2
        # 坐标轴
        qp.setPen(QPen(QColor(120, 120, 120), 2))
        qp.drawLine(margin, margin, margin, h-margin)
        qp.drawLine(margin, h-margin, w-margin, h-margin)
        # 绘制每条曲线
        self._draw_curve(qp, self.data["kill"], margin, h, rect_w, rect_h,
                         QColor(255,100,100), "击杀数/局")
        self._draw_curve(qp, self.data["kd"], margin, h, rect_w, rect_h,
                         QColor(80,180,255), "K/D")
        self._draw_curve(qp, [x/20.0 for x in self.data["snipe"]], margin, h, rect_w, rect_h,
                         QColor(220,100,255), "最远狙击/20m")
        # 标记左上角
        qp.setFont(QFont("微软雅黑", 9))
        qp.setPen(QColor(90, 90, 90))
        qp.drawText(margin+8, margin-10, f"局数:{len(self.data['kill'])}")

    def _draw_curve(self, qp, datalist, margin, h, rect_w, rect_h, color, label):
        N = len(datalist)
        if N < 2: return
        step_x = rect_w // (N-1) if N>1 else rect_w
        points = []
        maxy = max(max(datalist), 1)
        miny = min(min(datalist), 0)
        scale = rect_h / (maxy - miny + 1e-2)
        # 画曲线
        for i, v in enumerate(datalist):
            x = margin + i * step_x
            y = h - margin - (v - miny) * scale
            points.append((x, y))
        qp.setPen(QPen(color, 2))
        for i in range(N-1):
            qp.drawLine(int(points[i][0]), int(points[i][1]), int(points[i+1][0]), int(points[i+1][1]))
        # 最右下角标记
        qp.setPen(color)
        qp.setFont(QFont("微软雅黑", 10, QFont.Bold))
        qp.drawText(int(points[-1][0]-36), int(points[-1][1]-13), label)

# ================== src/ui/stats.py 完，下一个推荐模块入口 src/config/config.py（配置存取与加密） ==================

# 拼接说明：战绩统计窗代码实现完毕。
# 下一步在 src/config/ 目录下新建 config.py，等待配置读写模块。
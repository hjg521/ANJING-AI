# ================== src/ui/dialogs.py ==================
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit, QTableWidget, 
    QTableWidgetItem, QHeaderView, QAbstractItemView, QMessageBox, QComboBox, 
    QProgressBar, QSpacerItem, QSizePolicy
)
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QRect
from PyQt5.QtGui import QIcon, QColor, QBrush, QPixmap, QPainter, QPen
import random
import datetime

class SettingsDialog(QDialog):
    """
    通用设置窗口，可扩展各类偏好/高级参数配置
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("系统设置")
        self.setFixedSize(420, 320)
        layout = QVBoxLayout()
        # 演示：可添加多个设置项
        layout.addWidget(QLabel("功能设置区，更多参数请在src/ui/dialogs.py完善..."))
        self.setLayout(layout)


class KamiDialog(QDialog):
    """
    卡密后台系统：生成、冻结、删除、卡密列表、批量美化、粒子庆祝
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("卡密后台（生成/冻结/仿真）")
        self.setFixedSize(640, 480)
        self._setup_ui()
        self._init_data()
        self._refresh_table()

    def _setup_ui(self):
        layout = QVBoxLayout()
        hl = QHBoxLayout()
        hl.addWidget(QLabel("生成数量："))
        self.num_box = QComboBox()
        self.num_box.addItems(["1","10","50","100"])
        hl.addWidget(self.num_box)
        self.btn_gen = QPushButton("生成")
        self.btn_gen.clicked.connect(self._on_generate)
        hl.addWidget(self.btn_gen)
        # 进度条
        self.progress = QProgressBar()
        self.progress.hide()
        hl.addWidget(self.progress)
        hl.addStretch()
        layout.addLayout(hl)
        # 表格展示
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels([
            "卡密", "类型", "备注", "IP", "HWID", "到期", "状态"
        ])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._on_context_menu)
        layout.addWidget(self.table)
        # 粉色粒子动画区域
        self.anim_widget = ParticleWidget(self)
        layout.addWidget(self.anim_widget)
        layout.addSpacing(10)
        self.setLayout(layout)

    def _init_data(self):
        # 假设用内存结构保存（实际可接API/数据库）
        self.kami_list = []   # [dict(kami, type, ...)]
        self._load_data()

    def _load_data(self):
        # 可以加载数据库/磁盘/云API
        # 这里仅模拟生成部分假数据
        for i in range(10):
            self.kami_list.append({
                "kami": f"KAMI2025A00{i}",
                "type": random.choice(["1天", "7天", "1月", "永久"]),
                "note": f"备注{i}",
                "ip": "8.8.8.8",
                "hwid": "ABCD-1234-5678-999{}".format(i),
                "exp": (datetime.datetime.now() + datetime.timedelta(days=30)).strftime('%Y-%m-%d'),
                "state": "已使用" if i % 2 == 0 else "未激活"
            })

    def _refresh_table(self):
        self.table.setRowCount(len(self.kami_list))
        for row, k in enumerate(self.kami_list):
            for col, key in enumerate(["kami", "type", "note", "ip", "hwid", "exp", "state"]):
                item = QTableWidgetItem(str(k.get(key, "")))
                self.table.setItem(row, col, item)

    def _on_generate(self):
        # 批量生成带进度条和粒子动画
        try:
            count = int(self.num_box.currentText())
        except:
            count = 10
        self.progress.setMaximum(count)
        self.progress.setValue(0)
        self.progress.show()
        self.btn_gen.setEnabled(False)
        self.anim_widget.hide()
        self._gen_count = count
        self._now_gen = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._gen_tick)
        self._timer.start(50)

    def _gen_tick(self):
        if self._now_gen >= self._gen_count:
            self._timer.stop()
            self.progress.hide()
            self.btn_gen.setEnabled(True)
            self.anim_widget.start_particles()
            self._refresh_table()
            return
        # 随机生成假卡密
        idx = len(self.kami_list) + 1
        kami = f"KAMI{random.randint(100000,999999)}"
        self.kami_list.append({
            "kami": kami,
            "type": random.choice(["1小时", "12小时", "1天", "7天", "1月", "1季度", "1年"]),
            "note": "批量生成",
            "ip": "未激活",
            "hwid": "",
            "exp": (datetime.datetime.now() + datetime.timedelta(days=365)).strftime('%Y-%m-%d'),
            "state": "未激活"
        })
        self._now_gen += 1
        self.progress.setValue(self._now_gen)

    def _on_context_menu(self, pos):
        row = self.table.currentRow()
        if row >= 0:
            menu = QMenu(self)
            act_freeze = menu.addAction("冻结")
            act_delete = menu.addAction("删除")
            act_export = menu.addAction("导出")
            act_freeze.triggered.connect(lambda: self._do_freeze(row))
            act_delete.triggered.connect(lambda: self._do_delete(row))
            act_export.triggered.connect(lambda: self._do_export(row))
            menu.exec_(self.table.viewport().mapToGlobal(pos))

    def _do_freeze(self, row):
        # 冻结卡密
        self.kami_list[row]["state"] = "冻结"
        self._refresh_table()
        QMessageBox.information(self, "冻结卡密", "冻结成功！")

    def _do_delete(self, row):
        self.kami_list.pop(row)
        self._refresh_table()
        QMessageBox.information(self, "删除卡密", "删除成功！")

    def _do_export(self, row):
        # 导出卡密信息（可写本地、或复制到剪贴板）
        info = self.kami_list[row]
        info_str = "\n".join([f"{k}: {v}" for k,v in info.items()])
        dlg = QDialog(self)
        dlg.setWindowTitle("卡密导出")
        vbox = QVBoxLayout()
        ed = QLineEdit(info_str)
        vbox.addWidget(ed)
        btn = QPushButton("复制")
        btn.clicked.connect(lambda: QApplication.clipboard().setText(info_str))
        vbox.addWidget(btn)
        dlg.setLayout(vbox)
        dlg.exec_()


class ParticleWidget(QWidget):
    """
    粉色粒子庆祝动画Widget（生成卡密时触发）
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.seeds = []
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_particles)
        self.hide()
        self.setFixedHeight(48)

    def start_particles(self):
        # 大量生成粒子
        self.seeds = []
        w = self.width() if self.width() > 0 else 400
        for _ in range(38):
            x = random.randint(0, w)
            v = random.randint(-5, 5)
            c = QColor(255, 160 + random.randint(0, 80), 255, random.randint(100, 230))
            scale = random.uniform(0.8, 1.5)
            self.seeds.append([x, 0, v, c, scale])
        self.show()
        self.timer.start(30)

    def update_particles(self):
        for p in self.seeds:
            p[1] += random.randint(3, 7)
            p[0] += p[2]
        if self.seeds and max(x[1] for x in self.seeds) > self.height():
            self.seeds = []
            self.hide()
            self.timer.stop()
        self.update()

    def paintEvent(self, event):
        qp = QPainter(self)
        for x, y, v, c, scale in self.seeds:
            qp.setPen(Qt.NoPen)
            qp.setBrush(QBrush(c))
            qp.drawEllipse(x, y, int(21*scale), int(18*scale))


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("关于 安静AI视觉辅助平台")
        self.setFixedSize(360, 220)
        layout = QVBoxLayout()
        txt = QLabel("安静专属顶级AI视觉技术\n版本 1.0\n\n为PC端九大主流射击网游全系打造\n融合最新YOLO视觉AI、多外设、极致安全防检测、七大皮肤主题\n项目开源/私用均可，商用请授权！\n\n感谢您的信任与体验！")
        txt.setAlignment(Qt.AlignCenter)
        txt.setStyleSheet("font-size:15px;")
        layout.addWidget(txt)
        self.setLayout(layout)

# ================== src/ui/dialogs.py 完，下一步 src/ui/radar.py（独立雷达窗口）开始 ==================

# 拼接说明：弹窗/卡密/设置/粒子动画均已实现。
# 下一步请在 src/ui/ 新建 radar.py，等待下一个模块。
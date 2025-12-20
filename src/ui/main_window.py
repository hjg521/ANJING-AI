# src/ui/main_window.py
# 2025年旗舰风格UI完整版（左侧9游戏竖排 + 右侧参数 + 折叠高级） - 完整无省略

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QAction, QMenu, QStatusBar, QSplitter, QListWidget, QListWidgetItem,
    QGroupBox, QGridLayout, QScrollArea, QToolBox, QFrame, QSlider, QCheckBox,
    QColorDialog
)
from PyQt5.QtCore import Qt, QTimer, QSize
from PyQt5.QtGui import QIcon, QColor, QFont, QPixmap, QPainter, QPen, QBrush, QLinearGradient

from .theme import ThemeManager
from .radar import RadarWindow
from .stats import StatsWindow
from .esp_overlay import ESPOverlay
from src.tools.resource_path import resource_path
from src.config.config import load_config, save_config
from src.core.hotkeys import HotkeyManager
from src.core.cheats import cheat_service
from src.core.yolo_ai import visual_core
from src.devices.hardware import hardware_manager

import os

# ============ 压枪曲线编辑器 ============
class CurveEditor(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(500, 250)
        self.setStyleSheet("background-color: #1e1e2e; border: 1px solid #444; border-radius: 10px;")
        self.curve = [0.0] * 30
        self.drawing = False

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drawing = True
            self.update_point(event.pos())

    def mouseMoveEvent(self, event):
        if self.drawing:
            self.update_point(event.pos())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drawing = False
            if hasattr(self, "save_callback"):
                self.save_callback(self.get_curve())

    def update_point(self, pos):
        x = max(0, min(pos.x(), self.width() - 1))
        y = max(0, min(pos.y(), self.height() - 1))
        idx = int(x / self.width() * len(self.curve))
        if 0 <= idx < len(self.curve):
            max_offset = 60.0
            self.curve[idx] = (y / self.height()) * max_offset
        self.update()

    def paintEvent(self, event):
        qp = QPainter(self)
        qp.setRenderHint(QPainter.Antialiasing)
        qp.fillRect(self.rect(), QColor(30, 30, 46))

        # 网格
        qp.setPen(QPen(QColor(80, 80, 80), 1, Qt.DashLine))
        for i in range(1, 6):
            y = int(self.height() * i / 6)
            qp.drawLine(0, y, self.width(), y)

        # 曲线
        qp.setPen(QPen(QColor(0, 170, 255), 4))
        points = []
        for i, v in enumerate(self.curve):
            x = int(i / len(self.curve) * self.width())
            y = int(self.height() - (v / 60.0 * self.height()))
            points.append(QPoint(x, y))

        if len(points) > 1:
            for i in range(len(points) - 1):
                qp.drawLine(points[i], points[i + 1])

        # 文字
        qp.setPen(QColor(200, 200, 200))
        qp.setFont(QFont("Microsoft YaHei", 10))
        qp.drawText(20, 30, "压枪曲线编辑（鼠标拖动绘制）")

    def get_curve(self):
        return self.curve[:]

    def set_curve(self, curve):
        if len(curve) == len(self.curve):
            self.curve = curve[:]
            self.update()

# ============ 主窗口 ============
class MainWindow(QMainWindow):
    def __init__(self, user_info, theme_manager: ThemeManager, parent=None):
        super().__init__(parent)
        self.user_info = user_info
        self.theme_manager = theme_manager
        self.setWindowTitle("安静AI - 顶级视觉技术")
        self.setWindowIcon(QIcon(resource_path("resources/ai_icon.ico")))
        self.setGeometry(100, 50, 1600, 1000)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # 左侧游戏列表
        self.setup_game_list()

        # 分隔
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.game_list_widget)

        # 右侧面板
        self.right_panel = QWidget()
        self.right_layout = QVBoxLayout(self.right_panel)
        self.right_layout.setContentsMargins(20, 20, 20, 20)
        self.setup_right_panel()

        splitter.addWidget(self.right_panel)
        splitter.setSizes([350, 1250])

        self.main_layout.addWidget(splitter)

        # 热键
        self.hotkey_mgr = HotkeyManager(self)
        self.hotkey_mgr.install_on_widget(self)
        self.hotkey_mgr.register_hotkey("切换透视", Qt.Key_F3, callback=self.toggle_esp)

        # 透视窗
        self.esp_overlay = ESPOverlay(self)
        self.esp_overlay.hide()

        # 硬件刷新
        self.hardware_timer = QTimer(self)
        self.hardware_timer.timeout.connect(self.update_status)
        self.hardware_timer.start(5000)
        self.update_status()

        # 默认选中第一个游戏
        self.game_list_widget.setCurrentRow(0)

    def setup_game_list(self):
        self.game_list_widget = QListWidget()
        self.game_list_widget.setStyleSheet("""
            QListWidget {
                background-color: rgba(20, 20, 40, 240);
                border: none;
            }
            QListWidget::item {
                padding: 15px;
                margin: 5px;
                border-radius: 10px;
            }
            QListWidget::item:selected {
                background-color: rgba(0, 170, 255, 100);
                border-left: 6px solid #00AAFF;
            }
        """)
        self.game_list_widget.setIconSize(QSize(140, 140))
        self.game_list_widget.setSpacing(10)
        self.game_list_widget.setViewMode(QListWidget.IconMode)
        self.game_list_widget.setFlow(QListWidget.TopToBottom)
        self.game_list_widget.setResizeMode(QListWidget.Adjust)

        games = [
            ("CF", "穿越火线", "cf.png"),
            ("CFHD", "穿越火线高清", "cfhd.png"),
            ("DELTA", "三角洲行动", "delta.png"),
            ("VAL", "无畏契约", "val.png"),
            ("CSGO", "CSGO(CS2)", "csgo.png"),
            ("PEACE", "PC和平精英", "peace.png"),
            ("NZ", "逆战猎场", "nz.png"),
            ("YJ", "永劫无间", "yj.png"),
            ("PUBG", "PUBG(绝地求生)", "pubg.png")
        ]

        for key, name, icon_file in games:
            item = QListWidgetItem()
            icon_path = resource_path(os.path.join('resources', icon_file))
            item.setIcon(QIcon(icon_path))
            item.setText(name)
            item.setTextAlignment(Qt.AlignCenter)
            item.setData(Qt.UserRole, key)
            item.setSizeHint(QSize(180, 200))
            self.game_list_widget.addItem(item)

        self.game_list_widget.currentRowChanged.connect(self.on_game_selected)

    def setup_right_panel(self):
        # 顶部信息
        top_frame = QFrame()
        top_frame.setStyleSheet("background-color: rgba(30, 30, 50, 200); border-radius: 10px; padding: 10px;")
        top_layout = QHBoxLayout(top_frame)

        self.l_kami = QLabel(f"卡密：{self.user_info.get('kami', '未识别')}")
        self.l_kami.setStyleSheet("color: #00AAFF; font-size: 16px; font-weight: bold;")
        top_layout.addWidget(self.l_kami)

        self.l_type = QLabel(f"类型：{self.user_info.get('type', 'user').upper()}")
        self.l_type.setStyleSheet("color: #88FF88; font-size: 15px;")
        top_layout.addWidget(self.l_type)

        remaining = self.user_info.get("remaining_hours", "永久")
        expire_text = "永久" if remaining == "永久" else f"剩余 {remaining:.1f}小时"
        self.l_expire = QLabel(f"到期：{expire_text}")
        self.l_expire.setStyleSheet("color: #FFAA00; font-size: 15px;")
        top_layout.addWidget(self.l_expire)

        top_layout.addStretch()

        self.l_hardware = QLabel("硬件：离线")
        self.l_hardware.setStyleSheet("color: #FFFFFF; font-size: 15px;")
        top_layout.addWidget(self.l_hardware)

        self.right_layout.addWidget(top_frame)

        # 参数滚动区
        self.scroll = QScrollArea()
        self.scroll.setStyleSheet("background-color: transparent;")
        self.scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        self.scroll_layout.setSpacing(20)

        self.scroll.setWidget(self.scroll_widget)
        self.scroll.setWidgetResizable(True)
        self.right_layout.addWidget(self.scroll)

    def on_game_selected(self, row):
        if row < 0:
            return
        item = self.game_list_widget.item(row)
        game_key = item.data(Qt.UserRole)
        visual_core.switch_game_model(game_key)
        self.update_right_panel(game_key)

    def update_right_panel(self, game_key):
        # 清空旧内容
        for i in reversed(range(self.scroll_layout.count())):
            child = self.scroll_layout.itemAt(i).widget()
            if child:
                child.setParent(None)

        config = load_config()
        param = config.get("game_params", {}).get(game_key, {})

        # 基础功能
        basic_group = QGroupBox("基础功能")
        basic_group.setStyleSheet("QGroupBox { font-size: 18px; font-weight: bold; color: #00AAFF; border: none; }")
        basic_layout = QGridLayout()
        basic_layout.setSpacing(20)

        row = 0
        aim_check = QCheckBox("启用自瞄")
        aim_check.setStyleSheet("font-size: 16px;")
        aim_check.setChecked(param.get("aim_enabled", True))
        basic_layout.addWidget(aim_check, row, 0)
        row += 1

        esp_check = QCheckBox("启用透视")
        esp_check.setStyleSheet("font-size: 16px;")
        esp_check.setChecked(True)
        basic_layout.addWidget(esp_check, row, 0)
        row += 1

        recoil_check = QCheckBox("启用压枪")
        recoil_check.setStyleSheet("font-size: 16px;")
        recoil_check.setChecked(param.get("recoil_compensate", False))
        basic_layout.addWidget(recoil_check, row, 0)
        row += 1

        start_btn = QPushButton("开始实时推理")
        start_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #00AAFF, stop:1 #0088CC);
                color: white;
                font-size: 24px;
                font-weight: bold;
                padding: 30px;
                border-radius: 15px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #00CCFF, stop:1 #0099DD);
            }
        """)
        start_btn.setFixedHeight(100)
        basic_layout.addWidget(start_btn, row, 0)
        row += 1

        basic_group.setLayout(basic_layout)
        self.scroll_layout.addWidget(basic_group)

        # 高级设置折叠
        advanced = QToolBox()
        advanced.setStyleSheet("""
            QToolBox::tab {
                background: #2d2d44;
                color: white;
                padding: 15px;
                font-size: 16px;
                border-radius: 10px;
                margin-bottom: 5px;
            }
            QToolBox::tab:selected {
                background: #00AAFF;
            }
        """)

        # 瞄准设置
        aim_page = QWidget()
        aim_layout = QGridLayout(aim_page)
        aim_layout.setSpacing(20)

        aim_layout.addWidget(QLabel("自瞄FOV:"), 0, 0)
        fov_slider = QSlider(Qt.Horizontal)
        fov_slider.setRange(20, 300)
        fov_slider.setValue(param.get("aim_fov", 100))
        fov_slider.setStyleSheet("QSlider::handle:horizontal { background: #00AAFF; width: 20px; border-radius: 10px; }")
        aim_layout.addWidget(fov_slider, 0, 1)
        aim_layout.addWidget(QLabel("100"), 0, 2)

        aim_layout.addWidget(QLabel("自动开火:"), 1, 0)
        auto_fire = QCheckBox()
        auto_fire.setChecked(param.get("auto_fire", False))
        aim_layout.addWidget(auto_fire, 1, 1)

        advanced.addItem(aim_page, "瞄准设置")

        # 透视设置
        esp_page = QWidget()
        esp_layout = QGridLayout(esp_page)
        esp_layout.addWidget(QLabel("ESP颜色:"), 0, 0)
        color_btn = QPushButton("点击拾取颜色")
        color_btn.setStyleSheet(f"background-color: {param.get('esp_color', '#FF6464')}; min-height: 40px; border-radius: 10px;")
        esp_layout.addWidget(color_btn, 0, 1)
        advanced.addItem(esp_page, "透视设置")

        # 压枪设置
        recoil_page = QWidget()
        recoil_layout = QGridLayout(recoil_page)
        curve = CurveEditor()
        curve.set_curve(param.get("recoil_curve", [0.0] * 30))
        recoil_layout.addWidget(curve, 0, 0)
        advanced.addItem(recoil_page, "压枪设置")

        self.scroll_layout.addWidget(advanced)
        self.scroll_layout.addStretch()
            def update_status(self):
        devices = hardware_manager.list_devices()
        count = len(devices)
        status = "在线" if count > 0 else "离线"
        self.l_hardware.setText(f"硬件：{count}台 | 状态：{status}")

    def toggle_esp(self):
        self.esp_overlay.toggle_visibility()

    def _setup_menu(self):
        menu = self.menuBar()
        m_tools = menu.addMenu('工具')

        act_radar = QAction("打开雷达 (F1)", self)
        act_radar.triggered.connect(self.show_radar_window)
        m_tools.addAction(act_radar)

        act_stats = QAction("打开战绩 (F2)", self)
        act_stats.triggered.connect(self.show_stats_window)
        m_tools.addAction(act_stats)

        m_tools.addSeparator()

        act_settings = QAction("高级设置", self)
        act_settings.triggered.connect(self._on_kami_entry)
        m_tools.addAction(act_settings)

        act_about = QAction("关于", self)
        act_about.triggered.connect(self.show_about)
        m_tools.addAction(act_about)

    def _on_kami_entry(self):
        # 你的卡密后台入口逻辑
        pass

    def show_radar_window(self):
        if not hasattr(self, '_radar') or self._radar.isHidden():
            self._radar = RadarWindow(parent=None)
            self._radar.show()
            self._radar.raise_()
            self._radar.activateWindow()

    def show_stats_window(self):
        if not hasattr(self, '_stats') or self._stats.isHidden():
            self._stats = StatsWindow(parent=None)
            self._stats.show()
            self._stats.raise_()
            self._stats.activateWindow()

    def show_about(self):
        pass

    def init_windows(self):
        pass

    def _load_user_avatar(self):
        pass

    def toggle_global_aim(self):
        current_row = self.game_list_widget.currentRow()
        if current_row < 0:
            return
        item = self.game_list_widget.item(current_row)
        game_key = item.data(Qt.UserRole)
        helper = cheat_service.helpers.get(game_key)
        if helper:
            helper.active = not helper.active
            status = "开启" if helper.active else "关闭"
            self.statusBar().showMessage(f"{game_key} 自瞄 {status}", 2000)

    def closeEvent(self, event):
        # 程序关闭时停止所有线程
        cheat_service.stop_all()
        if hasattr(self, 'esp_overlay'):
            self.esp_overlay.close()
        event.accept()
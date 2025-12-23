# src/ui/main_window.py
# 2025年旗舰风格UI完整版（左侧9游戏竖排 + 右侧参数 + 折叠高级 + 截图切换 + 配置热重载）

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QAction, QMenu, QStatusBar, QSplitter, QListWidget, QListWidgetItem,
    QGroupBox, QGridLayout, QScrollArea, QToolBox, QFrame, QSlider, QCheckBox,
    QColorDialog, QComboBox
)
from PyQt5.QtCore import Qt, QTimer, QSize
from PyQt5.QtGui import QIcon, QColor, QFont, QPixmap, QPainter, QPen, QBrush, QLinearGradient

from .theme import ThemeManager
from .stats import StatsWindow
from .esp_overlay import ESPOverlay
from src.tools.resource_path import resource_path
from src.config.config import load_config, load_all_configs
from src.core.hotkeys import HotkeyManager
from src.core.cheats import cheat_service
from src.core.yolo_ai import visual_core
from src.devices.hardware import hardware_manager
from src.core.screenshot import ScreenshotManager, game_capture  # 全局game_capture

import os
import time

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
            points.append((x, y))

        if len(points) > 1:
            for i in range(len(points) - 1):
                qp.drawLine(points[i][0], points[i][1], points[i+1][0], points[i+1][1])

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
        self.hotkey_mgr.register_hotkey("热重载配置", Qt.Key_R, Qt.ControlModifier | Qt.AltModifier, callback=self.reload_config)

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

    # ==============================================
    # 右侧面板布局
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

        # ============ 截图模式选择 ============
        capture_group = QGroupBox("截图模式")
        capture_group.setStyleSheet("QGroupBox { font-size: 16px; font-weight: bold; color: #00FFAA; }")
        capture_layout = QHBoxLayout()

        self.capture_combo = QComboBox()
        self.capture_combo.addItems([
            "DXGI 多线程 (全屏推荐, 默认)",
            "DXGI 单线程",
            "句柄截图 (窗口化推荐)",
            "MSS (兼容最广)"
        ])
        self.capture_combo.setCurrentIndex(0)
        self.capture_combo.currentIndexChanged.connect(self.change_capture_mode)
        capture_layout.addWidget(QLabel("模式:"))
        capture_layout.addWidget(self.capture_combo)
        capture_layout.addStretch()

        capture_group.setLayout(capture_layout)
        self.right_layout.addWidget(capture_group)

        # ============ 一键刷新配置按钮 ============
        refresh_group = QGroupBox("配置管理")
        refresh_group.setStyleSheet("QGroupBox { font-size: 16px; font-weight: bold; color: #FFAA00; }")
        refresh_layout = QHBoxLayout()

        self.refresh_btn = QPushButton("🔄 刷新配置")
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #FFAA00, stop:1 #CC8800);
                color: white;
                font-size: 16px;
                font-weight: bold;
                padding: 10px;
                border-radius: 8px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #FFCC00, stop:1 #DD9900);
            }
        """)
        self.refresh_btn.clicked.connect(self.reload_config)
        refresh_layout.addWidget(self.refresh_btn)
        refresh_layout.addStretch()

        refresh_group.setLayout(refresh_layout)
        self.right_layout.addWidget(refresh_group)

        # 参数滚动区
        self.scroll = QScrollArea()
        self.scroll.setStyleSheet("background-color: transparent;")
        self.scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        self.scroll_layout.setSpacing(20)

        self.scroll.setWidget(self.scroll_widget)
        self.scroll.setWidgetResizable(True)
        self.right_layout.addWidget(self.scroll)

    # ==============================================
    # 类方法

    def change_capture_mode(self, index):
        """截图模式切换逻辑"""
        global game_capture

        modes = ["dxgi_thread", "dxgi", "handle", "mss"]
        new_mode = modes[index]

        print(f"[截图] 正在切换到模式: {new_mode.upper()}")

        # 停止旧线程
        try:
            if hasattr(game_capture, 'stop'):
                game_capture.stop()
                time.sleep(0.1)
        except:
            pass
# 创建新实例
        game_capture = ScreenshotManager(mode=new_mode)

        # 多线程模式启动后台截图
        if new_mode == "dxgi_thread":
            game_capture.start_continuous(self.on_new_frame)

        self.statusBar().showMessage(f"截图模式切换为: {self.capture_combo.currentText()}", 3000)

    def on_new_frame(self, frame):
        """多线程模式下收到新帧的回调"""
        if frame is None:
            return

        targets = visual_core.infer(frame)

        if hasattr(self, 'esp_overlay') and self.esp_overlay.isVisible():
            self.esp_overlay.targets = targets
            self.esp_overlay.update()

    def reload_config(self):
        """热重载配置（按钮或热键触发）"""
        from src.config.config import load_all_configs

        load_all_configs()

        self.statusBar().showMessage("✅ 配置已刷新！", 5000)

        if hasattr(self, 'refresh_btn'):
            original_style = self.refresh_btn.styleSheet()
            self.refresh_btn.setText("✔ 已刷新")
            self.refresh_btn.setStyleSheet("""
                QPushButton {
                    background: #00AA00;
                    color: white;
                    font-size: 16px;
                    font-weight: bold;
                    padding: 10px;
                    border-radius: 8px;
                }
            """)
            self.refresh_btn.setEnabled(False)

            QTimer.singleShot(2000, lambda: (
                self.refresh_btn.setText("🔄 刷新配置"),
                self.refresh_btn.setStyleSheet(original_style),
                self.refresh_btn.setEnabled(True)
            ))

        current_row = self.game_list_widget.currentRow()
        if current_row >= 0:
            self.on_game_selected(current_row)

        print("[Config] 配置热重载完成")

    def update_status(self):
        devices = hardware_manager.list_devices()
        count = len(devices)
        status = "在线" if count > 0 else "离线"
        self.l_hardware.setText(f"硬件：{count}台 | 状态：{status}")

    def toggle_esp(self):
        self.esp_overlay.toggle_visibility()

    # ... 你的其他方法（如 on_game_selected, update_right_panel, setup_game_list 等保持不变） ...

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
        param = config.get("game_params", {}).get(game_key, GameParam(). __dict__)  # 使用默认值

        # 基础功能
        basic_group = QGroupBox("基础功能")
        basic_group.setStyleSheet("QGroupBox { font-size: 18px; font-weight: bold; color: #00AAFF; border: none; }")
        basic_layout = QGridLayout()
        basic_layout.setSpacing(20)

        row = 0
        aim_check = QCheckBox("启用自瞄")
        aim_check.setStyleSheet("font-size: 16px;")
        aim_check.setChecked(param.get("aim_enabled", True))
        aim_check.stateChanged.connect(lambda state: self.set_param(game_key, "aim_enabled", state == Qt.Checked))
        basic_layout.addWidget(aim_check, row, 0)
        row += 1

        esp_check = QCheckBox("启用透视")
        esp_check.setStyleSheet("font-size: 16px;")
        esp_check.setChecked(param.get("esp_enabled", True))
        esp_check.stateChanged.connect(lambda state: self.set_param(game_key, "esp_enabled", state == Qt.Checked))
        basic_layout.addWidget(esp_check, row, 0)
        row += 1

        recoil_check = QCheckBox("启用压枪")
        recoil_check.setStyleSheet("font-size: 16px;")
        recoil_check.setChecked(param.get("recoil_compensate", False))
        recoil_check.stateChanged.connect(lambda state: self.set_param(game_key, "recoil_compensate", state == Qt.Checked))
        basic_layout.addWidget(recoil_check, row, 0)
        row += 1

        auto_fire_check = QCheckBox("自动开火")
        auto_fire_check.setStyleSheet("font-size: 16px;")
        auto_fire_check.setChecked(param.get("auto_fire_enabled", False))
        auto_fire_check.stateChanged.connect(lambda state: self.set_param(game_key, "auto_fire_enabled", state == Qt.Checked))
        basic_layout.addWidget(auto_fire_check, row, 0)
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
        start_btn.clicked.connect(lambda: cheat_service.start_cheat(game_key, param))
        basic_layout.addWidget(start_btn, row, 0)

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
        fov_slider.valueChanged.connect(lambda v: self.set_param(game_key, "aim_fov", v))
        aim_layout.addWidget(fov_slider, 0, 1)
        aim_layout.addWidget(QLabel("100"), 0, 2)

        aim_layout.addWidget(QLabel("miss率:"), 1, 0)
        miss_slider = QSlider(Qt.Horizontal)
        miss_slider.setRange(0, 50)
        miss_slider.setValue(int(param.get("miss_rate", 0.12) * 100))
        miss_slider.valueChanged.connect(lambda v: self.set_param(game_key, "miss_rate", v / 100))
        aim_layout.addWidget(miss_slider, 1, 1)

        advanced.addItem(aim_page, "瞄准设置")

        # 透视设置
        esp_page = QWidget()
        esp_layout = QGridLayout(esp_page)
        esp_layout.addWidget(QLabel("ESP颜色:"), 0, 0)
        color_btn = QPushButton("点击拾取颜色")
        color_btn.setStyleSheet(f"background-color: {param.get('esp_color', '#FF6464')}; min-height: 40px; border-radius: 10px;")
        color_btn.clicked.connect(lambda: self.choose_esp_color(game_key, color_btn))
        esp_layout.addWidget(color_btn, 0, 1)
        advanced.addItem(esp_page, "透视设置")

        # 压枪设置
        recoil_page = QWidget()
        recoil_layout = QGridLayout(recoil_page)
        curve_editor = CurveEditor()
        curve_editor.set_curve(param.get("recoil_curve", [0.0] * 30))
        curve_editor.save_callback = lambda curve: self.set_param(game_key, "recoil_curve", curve)
        recoil_layout.addWidget(curve_editor, 0, 0)
        advanced.addItem(recoil_page, "压枪设置")

        self.scroll_layout.addWidget(advanced)
        self.scroll_layout.addStretch()

    def choose_esp_color(self, game_key, btn):
        color = QColorDialog.getColor(QColor(param.get("esp_color", "#FF6464")))
        if color.isValid():
            hex_color = color.name()
            self.set_param(game_key, "esp_color", hex_color)
            btn.setStyleSheet(f"background-color: {hex_color}; min-height: 40px; border-radius: 10px;")

    def set_param(self, game_key, key, value):
        """实时保存参数到配置"""
        cfg = load_config()
        if "game_params" not in cfg:
            cfg["game_params"] = {}
        if game_key not in cfg["game_params"]:
            cfg["game_params"][game_key] = {}
        cfg["game_params"][game_key][key] = value
        save_config(cfg)

    def closeEvent(self, event):
        cheat_service.stop_all()
        if hasattr(self, 'esp_overlay'):
            self.esp_overlay.close()
        super().closeEvent(event)

# 文件结束
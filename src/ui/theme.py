# src/ui/theme.py
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QHBoxLayout, QComboBox, QPushButton, QLineEdit, QMessageBox, QSpacerItem, QSizePolicy
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPalette, QColor
import json
import os
from src.tools.resource_path import resource_path
from appdirs import user_config_dir

class ThemeManager:
    """
    全局主题管理，支持多皮肤、实时应用、用户目录持久化
    """
    _builtin_themes = {
        "default": {
            "name": "极简白",
            "palette": {
                "base": "#F9FAFC",
                "window": "#FFFFFF",
                "text": "#222",
                "button": "#F3F5F7",
                "highlight": "#4488FF",
                "highlightedText": "#fff"
            }
        },
        "dark": {
            "name": "暗色科技",
            "palette": {
                "base": "#23283C",
                "window": "#181B2C",
                "text": "#F2F2F2",
                "button": "#22264B",
                "highlight": "#37D1F2",
                "highlightedText": "#181B2C"
            }
        },
        "transparent_blue": {
            "name": "蓝光透明",
            "palette": {
                "base": "#1e293bCC",
                "window": "#151b29CC",
                "text": "#DEE6FC",
                "button": "#223059A0",
                "highlight": "#54CFFD",
                "highlightedText": "#222"
            }
        },
        "gray": {
            "name": "极简亮灰",
            "palette": {
                "base": "#F2F2F8",
                "window": "#FAFAFA",
                "text": "#121212",
                "button": "#EEE",
                "highlight": "#7090DA",
                "highlightedText": "#FFF"
            }
        },
        "night": {
            "name": "深邃星空",
            "palette": {
                "base": "#181A25",
                "window": "#171825",
                "text": "#F0EFFF",
                "button": "#23254D",
                "highlight": "#B356E8",
                "highlightedText": "#fff"
            }
        },
        "neon": {
            "name": "荧光绿黑",
            "palette": {
                "base": "#131F15",
                "window": "#151E13",
                "text": "#ABFF93",
                "button": "#192923",
                "highlight": "#45FFB7",
                "highlightedText": "#151E13"
            }
        },
        "purple": {
            "name": "炫光紫黑",
            "palette": {
                "base": "#221B4A",
                "window": "#171627",
                "text": "#F3EFFF",
                "button": "#2D2257",
                "highlight": "#D15EDB",
                "highlightedText": "#fff"
            }
        }
    }

    # 使用用户目录持久化
    CONFIG_DIR = user_config_dir("AnjingAI")
    CONFIG_FILE = os.path.join(CONFIG_DIR, "theme_config.json")

    def __init__(self):
        self.current_theme = "default"
        self.user_custom = {}
        os.makedirs(self.CONFIG_DIR, exist_ok=True)
        self._load_config()

    def get_theme_list(self):
        base = list(self._builtin_themes.keys())
        if self.user_custom:
            base.extend([f"user_{k}" for k in self.user_custom.keys()])
        return base

    def get_theme_meta(self, theme_key):
        if theme_key.startswith("user_"):
            name = theme_key[5:]
            return self.user_custom.get(name, self._builtin_themes["default"])
        return self._builtin_themes.get(theme_key, self._builtin_themes["default"])

    def get_stylesheet(self, theme_key=None):
        key = theme_key or self.current_theme
        palette = self.get_theme_meta(key)["palette"]
        base = palette["base"]
        window = palette["window"]
        text = palette["text"]
        button = palette["button"]
        highlight = palette["highlight"]
        highlighted_text = palette["highlightedText"]

        return f"""
        QWidget {{
            background: {window};
            color: {text};
        }}
        QPushButton, QComboBox, QLineEdit, QTextEdit, QCheckBox {{
            background: {button};
            border: 1px solid {highlight}70;
            color: {text};
            border-radius: 4px;
            padding: 5px;
        }}
        QPushButton:hover {{
            background: {highlight}33;
        }}
        QTabWidget::pane {{
            border: 1px solid {highlight};
            border-radius: 8px;
        }}
        QTabBar::tab:selected {{
            background: {highlight};
            color: {highlighted_text};
        }}
        QStatusBar {{
            background: {window};
            color: {text};
        }}
        QToolTip {{
            background: {highlight}DD;
            color: {highlighted_text};
            border-radius: 4px;
            padding: 6px;
        }}
        """

    def apply_theme(self, app):
        """全局应用主题"""
        app.setStyleSheet(self.get_stylesheet())

    def set_theme(self, theme_key: str, app=None):
        self.current_theme = theme_key
        if app:
            self.apply_theme(app)
        self._save_config()

    def _load_config(self):
        if os.path.exists(self.CONFIG_FILE):
            try:
                with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.current_theme = data.get("theme", "default")
                    self.user_custom = data.get("user_custom", {})
            except Exception:
                self.current_theme = "default"

    def _save_config(self):
        try:
            data = {
                "theme": self.current_theme,
                "user_custom": self.user_custom
            }
            with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print("主题保存失败:", e)


class ThemeSwitcherDialog(QDialog):
    """
    主题切换对话框 + 管理员密码入口（三层隐藏）
    """
    def __init__(self, theme_manager: ThemeManager, parent=None):
        super().__init__(parent)
        self.theme_manager = theme_manager
        self.admin_password = ""
        self.setWindowTitle("主题切换")
        self.setFixedSize(420, 340)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self._setup_ui()
        self._preview_current()

    def _setup_ui(self):
        layout = QVBoxLayout()

        label = QLabel("请选择UI主题（实时预览）")
        label.setStyleSheet("font-weight:bold;margin:12px;")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

        self.cb = QComboBox()
        self.theme_keys = self.theme_manager.get_theme_list()
        theme_names = [self.theme_manager.get_theme_meta(t)["name"] for t in self.theme_keys]
        self.cb.addItems(theme_names)

        # 当前主题定位
        try:
            idx = self.theme_keys.index(self.theme_manager.current_theme)
            self.cb.setCurrentIndex(idx)
        except ValueError:
            self.cb.setCurrentIndex(0)

        self.cb.currentIndexChanged.connect(self._on_theme_changed)
        layout.addWidget(self.cb)

        layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # 隐藏的管理员密码输入
        pwd_layout = QHBoxLayout()
        pwd_label = QLabel("访问码（高级功能）：")
        pwd_label.setStyleSheet("color:#888;font-size:12px;")
        pwd_layout.addWidget(pwd_label)

        self.pw_edit = QLineEdit()
        self.pw_edit.setEchoMode(QLineEdit.Password)
        self.pw_edit.setPlaceholderText("可选，普通换肤无需输入")
        pwd_layout.addWidget(self.pw_edit)
        layout.addLayout(pwd_layout)

        # 按钮
        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("应用主题")
        btn_cancel = QPushButton("取消")
        btn_ok.clicked.connect(self._apply_and_accept)
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)

        tip = QLabel("输对访问码可解锁高级模块，常用不需输入，只管切主题即可。")
        tip.setStyleSheet("color:#777;font-size:12px;")
        tip.setAlignment(Qt.AlignCenter)
        layout.addWidget(tip)

        self.setLayout(layout)

    def _on_theme_changed(self, idx):
        if 0 <= idx < len(self.theme_keys):
            key = self.theme_keys[idx]
            # 实时预览全局
            if self.parent() and hasattr(self.parent(), 'parent') and self.parent().parent():
                app = self.parent().parent()  # MainWindow -> SafeApp
                self.theme_manager.set_theme(key, app)

    def _preview_current(self):
        self._on_theme_changed(self.cb.currentIndex())

    def _apply_and_accept(self):
        idx = self.cb.currentIndex()
        if 0 <= idx < len(self.theme_keys):
            key = self.theme_keys[idx]
            self.theme_manager.set_theme(key)
            self.admin_password = self.pw_edit.text().strip()
            self.accept()

    def get_admin_password(self):
        return self.admin_password
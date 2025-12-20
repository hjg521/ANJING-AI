# src/app.py
import sys
import traceback
import platform
import datetime
import subprocess
import os

from PyQt5.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon, QMenu, QAction
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt

from src.tools.resource_path import resource_path  # 资源路径打包兼容
from appdirs import user_config_dir  # 用户目录

class SafeApp(QApplication):
    """
    全局安全应用类：异常拦截、托盘管理、统一通知、日志写入用户目录
    """
    _instance = None

    # 日志路径改为用户目录（打包后可写）
    LOG_DIR = user_config_dir("AnjingAI")
    LOG_FILE = os.path.join(LOG_DIR, "application.log")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        SafeApp._instance = self
        self.tray_icon = None
        self.is_tray_shown = False

        os.makedirs(SafeApp.LOG_DIR, exist_ok=True)  # 确保日志目录存在

        self._setup_excepthook()
        self._setup_tray()

    def _setup_excepthook(self):
        """捕获所有未处理异常，写入日志并弹窗"""
        def handle_exception(exc_type, exc_value, exc_traceback):
            if issubclass(exc_type, KeyboardInterrupt):
                sys.__excepthook__(exc_type, exc_value, exc_traceback)
                return

            err_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
            self.log_error(err_msg)

            QMessageBox.critical(
                None,
                "程序异常终止",
                f"软件运行时出现未捕获异常！\n\n错误已记录到日志文件。\n\n{exc_value}"
            )
            self.quit()

        sys.excepthook = handle_exception

    def _setup_tray(self):
        """系统托盘：最小化、恢复、退出"""
        icon_path = resource_path("resources/tray.png")
        tray_icon = QIcon(icon_path) if os.path.exists(icon_path) else QIcon()

        self.tray_icon = QSystemTrayIcon(tray_icon, self)
        menu = QMenu()

        act_restore = QAction("恢复主窗口", self)
        act_hide = QAction("最小化到托盘", self)
        act_exit = QAction("彻底退出", self)

        act_restore.triggered.connect(self.restore_all_windows)
        act_hide.triggered.connect(self.hide_all_windows)
        act_exit.triggered.connect(self.quit)

        menu.addAction(act_restore)
        menu.addAction(act_hide)
        menu.addSeparator()
        menu.addAction(act_exit)

        self.tray_icon.setContextMenu(menu)
        self.tray_icon.setToolTip("安静AI视觉辅助平台")
        self.tray_icon.show()
        self.is_tray_shown = True

    def notify(self, title, msg, icon=QSystemTrayIcon.Information, timeout=5000):
        """托盘气泡通知"""
        if self.tray_icon:
            self.tray_icon.showMessage(title, msg, icon, timeout)

    def restore_all_windows(self):
        """恢复所有窗口（主窗、雷达、战绩等）"""
        for w in self.topLevelWidgets():
            if w.isHidden():
                w.show()
            w.raise_()
            w.activateWindow()

    def hide_all_windows(self):
        """隐藏所有窗口到托盘（辅助后台运行）"""
        for w in self.topLevelWidgets():
            w.hide()

    @staticmethod
    def log_error(errmsg):
        """写入日志到用户目录"""
        try:
            with open(SafeApp.LOG_FILE, "a", encoding="utf-8") as f:
                now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                plat = platform.platform()
                f.write(f"\n[{now}][{plat}] CRITICAL ERROR\n{errmsg}\n{'-'*60}\n")
        except Exception as e:
            print("日志写入失败:", e)

    @staticmethod
    def instance():
        """获取全局单例"""
        return SafeApp._instance

    def restart_app(self):
        """安全重启程序"""
        self.quit()
        subprocess.Popen([sys.executable] + sys.argv)
# main.py
# 程序入口（完整优化版）
import sys
import os
import socket

# ============ 路径自动修正（支持PyInstaller打包） ============
if getattr(sys, 'frozen', False):
    # 打包后运行
    os.chdir(os.path.dirname(sys.executable))
else:
    # 开发时运行
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

# 添加 src 到路径
sys.path.append(os.path.join(os.getcwd(), 'src'))

# ============ 必要依赖检测（新手友好） ============
try:
    from PyQt5.QtWidgets import QApplication
except ImportError:
    print("未检测到 PyQt5！请运行以下命令安装依赖：")
    print("pip install -r requirements.txt")
    sys.exit(1)

# ============ 单实例锁定（防止重复运行） ============
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
try:
    sock.bind(('127.0.0.1', 54329))
except OSError:
    print("本辅助软件已启动，无需重复运行。")
    sys.exit(0)

# ============ 导入核心模块 ============
from src.app import SafeApp
from src.ui.login import LoginDialog
from src.ui.main_window import MainWindow
from src.ui.theme import ThemeManager
from src.config.config import init_config, load_all_configs, save_all_configs
from src.core.hotkeys import HotkeyManager
from PyQt5.QtCore import Qt

def main():
    # 启动全局Qt应用（安全版）
    app = SafeApp(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # 全局主题管理
    theme = ThemeManager()
    theme.load_default()  # 加载持久化主题
    theme.apply_theme(app)  # 立即应用

    # 初始化配置（目录、密钥、默认值）
    init_config()
    load_all_configs()

    # 登录流程
    login = LoginDialog(theme_manager=theme)
    if login.exec_() != login.Accepted:
        sys.exit(0)

    user_info = login.get_user_info()

    # 主窗口启动
    mw = MainWindow(user_info=user_info, theme_manager=theme)
    mw.show()

    # ============ 安装全局热键管理 ============
    hotkey_mgr = HotkeyManager(mw)
    hotkey_mgr.install_on_widget(mw)

    # 示例热键（已集成到MainWindow，这里可额外全局注册）
    # hotkey_mgr.register_hotkey("退出程序", Qt.Key_Escape, Qt.ControlModifier | Qt.ShiftModifier, callback=app.quit)

    # ============ 运行事件循环 ============
    exit_code = app.exec_()

    # 退出前保存所有配置
    save_all_configs()

    sys.exit(exit_code)

if __name__ == '__main__':
    main()
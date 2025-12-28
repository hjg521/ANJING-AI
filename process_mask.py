# src/tools/process_mask.py
# 2025终极中外融合动态随机伪装（系统进程 + 中国本土软件 + 杀毒 + 托盘图标，150+ 方案）

import sys
import os
import ctypes
import platform
import threading
import time
import random
from PyQt5.QtGui import QIcon

from src.tools.resource_path import resource_path

if platform.system() == "Windows":
    import win32gui
    import win32con

class ProcessMasking:
    """终极融合伪装：系统进程 + 中国本土软件 + 杀毒 + 随机托盘图标"""

    FAKE_PROFILES = {
        # 1. 经典系统进程（最安全、最常见伪装）
        "windows_system": {
            "processes": [
                "svchost.exe", "dwm.exe", "csrss.exe", "winlogon.exe", "explorer.exe",
                "taskhostw.exe", "ctfmon.exe", "sihost.exe", "RuntimeBroker.exe",
                "ShellExperienceHost.exe", "SearchIndexer.exe", "smss.exe", "wininit.exe",
                "services.exe", "lsass.exe", "fontdrvhost.exe", "conhost.exe",
                "SecurityHealthSystray.exe", "MoUsoCoreWorker.exe", "TiWorker.exe",
                "TrustedInstaller.exe", "msmpeng.exe", "nisSrv.exe", "sihost.exe"
            ],
            "titles": [
                "Desktop Window Manager", "Windows Shell Experience Host", "Program Manager",
                "Security and Maintenance", "System", "Search", "Settings", "Task Host",
                "Runtime Broker", "Font Driver Host", "Console Window Host",
                "Microsoft Windows Operating System", "Windows Security Health",
                "Windows Update", "Microsoft Defender Antivirus Service"
            ],
            "icons": ["system", "dwm", "explorer", "security", "update", "defender"]  # 可放通用Windows图标
        },

        # 2. 即时通讯/社交
        "im_social": {
            "processes": ["WeChat.exe", "QQ.exe", "TIM.exe", "DingTalk.exe", "Feishu.exe", "EnterpriseWeChat.exe"],
            "titles": ["微信", "QQ", "TIM", "钉钉", "飞书", "企业微信", "微信 - 正在同步消息", "QQ - 消息提醒"],
            "icons": ["wechat", "qq", "tim", "dingtalk", "feishu", "enterprisewc"]
        },

        # 3. 短视频/直播
        "video_short": {
            "processes": ["Douyin.exe", "Kuaishou.exe", "XiguaVideo.exe", "Bilibili.exe", "Youku.exe", "iQIYI.exe"],
            "titles": ["抖音", "快手", "西瓜视频", "哔哩哔哩", "优酷", "爱奇艺", "抖音 - 推荐", "B站 - 首页"],
            "icons": ["douyin", "kuaishou", "xigua", "bilibili", "youku", "iqiyi"]
        },

        # 4. 电商/外卖
        "shopping": {
            "processes": ["Taobao.exe", "JDLive.exe", "Pinduoduo.exe", "Meituan.exe", "Eleme.exe"],
            "titles": ["淘宝", "京东", "拼多多", "美团", "饿了么", "淘宝 - 首页", "京东 - 购物车"],
            "icons": ["taobao", "jd", "pinduoduo", "meituan", "eleme"]
        },

        # 5. 杀毒/安全软件（重点）
        "antivirus": {
            "processes": [
                "360safe.exe", "360tray.exe", "ZhuDongFangYu.exe", "KSafeTray.exe",
                "Huorong.exe", "HipsTray.exe", "KvMon.exe", "TxGuard.exe", "QQPCMgr.exe"
            ],
            "titles": ["360安全卫士", "360安全卫士 - 主面板", "火绒安全", "金山毒霸", "腾讯电脑管家", "360实时保护"],
            "icons": ["360safe", "360tray", "huorong", "kv", "txcomputer", "qqpcmgr"]
        },

        # 6. 浏览器
        "browser": {
            "processes": ["chrome.exe", "msedge.exe", "360chrome.exe", "QQBrowser.exe"],
            "titles": ["Chrome", "Microsoft Edge", "360安全浏览器", "QQ浏览器", "新标签页", "百度一下，你就知道"],
            "icons": ["chrome", "msedge", "360chrome", "qqbrowser"]
        },

        # 7. 系统/媒体/游戏平台
        "media_game": {
            "processes": [
                "Steam.exe", "WeGame.exe", "EpicGamesLauncher.exe",
                "PotPlayerMini64.exe", "vlc.exe", "Thunder.exe", "BaiduNetdisk.exe"
            ],
            "titles": ["Steam", "WeGame", "Epic Games", "PotPlayer", "VLC", "迅雷", "百度网盘"],
            "icons": ["steam", "wegame", "epic", "potplayer", "vlc", "thunder", "baidunetdisk"]
        }
    }

    @staticmethod
    def get_random_fake_profile():
        category = random.choice(list(ProcessMasking.FAKE_PROFILES.keys()))
        profile = ProcessMasking.FAKE_PROFILES[category]
        fake_process = random.choice(profile["processes"])
        fake_title = random.choice(profile["titles"])
        icon_base = random.choice(profile["icons"])
        return fake_process, fake_title, icon_base, category

    @staticmethod
    def mask_process_name(fake_name: str):
        if platform.system() == "Windows":
            try:
                ctypes.windll.kernel32.SetConsoleTitleW(fake_name)
                print(f"[Mask] 进程控制台标题伪装为: {fake_name}")
            except Exception as e:
                print(f"[Mask] 进程名伪装失败: {e}")

    @staticmethod
    def mask_window_title(window, fake_title: str):
        try:
            window.setWindowTitle(fake_title)
            print(f"[Mask] 主窗口标题伪装为: {fake_title}")
        except Exception as e:
            print(f"[Mask] 窗口标题伪装失败: {e}")

    @staticmethod
    def mask_tray_icon(app, icon_base_name: str):
        try:
            candidates = [
                resource_path(os.path.join("fake_icons", f"{icon_base_name}.ico")),
                resource_path(os.path.join("fake_icons", f"{icon_base_name}.png")),
                resource_path(os.path.join("fake_icons", icon_base_name)),
            ]
            for path in candidates:
                if os.path.exists(path):
                    app.tray_icon.setIcon(QIcon(path))
                    print(f"[Mask] 托盘图标伪装为: {os.path.basename(path)}")
                    return
            print("[Mask] 未找到对应图标，使用默认托盘图标")
        except Exception as e:
            print(f"[Mask] 托盘图标伪装失败: {e}")

    @staticmethod
    def hide_from_taskbar(window):
        if platform.system() != "Windows":
            return
        try:
            hwnd = int(window.winId())
            style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            style |= win32con.WS_EX_TOOLWINDOW
            style &= ~win32con.WS_EX_APPWINDOW
            win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, style)
            print("[Mask] 主窗口已隐藏任务栏图标和Alt+Tab")
        except Exception as e:
            print(f"[Mask] 隐藏任务栏失败: {e}")

    @staticmethod
    def apply_full_mask(main_window, app):
        threading.Thread(
            target=ProcessMasking._delayed_full_mask,
            args=(main_window, app),
            daemon=True
        ).start()

    @staticmethod
    def _delayed_full_mask(main_window, app):
        time.sleep(2.0)

        fake_process, fake_title, icon_base, category = ProcessMasking.get_random_fake_profile()
        print(f"[Mask] 本次融合伪装方案 [{category}]: 进程={fake_process} | 标题={fake_title} | 图标={icon_base}")

        ProcessMasking.mask_process_name(fake_process)
        ProcessMasking.mask_window_title(main_window, fake_title)
        ProcessMasking.mask_tray_icon(app, icon_base)
        ProcessMasking.hide_from_taskbar(main_window)

# 使用方式不变：
# ProcessMasking.apply_full_mask(self, SafeApp.instance())
# src/ui/login.py
# 纯本地终极卡密验证（带剩余时间 + 解绑扣2小时）

from PyQt5.QtWidgets import (
    QDialog, QLabel, QLineEdit, QVBoxLayout, QHBoxLayout, QPushButton,
    QMessageBox, QCheckBox, QWidget, QSpacerItem, QSizePolicy
)
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt
import uuid
import hashlib
import subprocess
import datetime
import os
import json

from src.config.config import _get_fernet
from appdirs import user_config_dir

# 反调试
import ctypes
if ctypes.windll.kernel32.IsDebuggerPresent():
    import sys
    sys.exit(0)

class LoginDialog(QDialog):
    def __init__(self, theme_manager, parent=None):
        super().__init__(parent)
        self.theme_manager = theme_manager
        self.setWindowTitle("登录 - 安静AI视觉技术")
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setFixedSize(420, 340)

        self.bind_file = os.path.join(user_config_dir("AnjingAI"), "bind.dat")

        main_layout = QVBoxLayout()
        l_title = QLabel("账号登录")
        l_title.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
        l_title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(l_title)

        h_kami = QHBoxLayout()
        self.le_kami = QLineEdit()
        self.le_kami.setPlaceholderText("请输入卡密...")
        h_kami.addWidget(self.le_kami, 5)

        btn_unbind = QPushButton("解绑换机")
        btn_unbind.setToolTip("解绑本机，扣除2小时剩余时间")
        btn_unbind.clicked.connect(self.unbind_hwid)
        h_kami.addWidget(btn_unbind, 3)
        main_layout.addLayout(h_kami)

        self.cb_autologin = QCheckBox("下次自动登录")
        self.cb_autologin.setChecked(True)
        main_layout.addWidget(self.cb_autologin)

        btn_layout = QHBoxLayout()
        btn_login = QPushButton("登录验证")
        btn_login.clicked.connect(self._do_login)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_login)
        btn_layout.addStretch()
        main_layout.addLayout(btn_layout)

        self.le_hwid = QLineEdit(self.get_hwid()[:16] + "...")
        self.le_hwid.setReadOnly(True)
        self.le_hwid.setToolTip("当前设备识别码（已加强）")
        main_layout.addWidget(self.le_hwid)

        tip = QLabel("首次使用需输入卡密绑定本机，换机点击解绑（扣2小时）。")
        tip.setStyleSheet("color:gray;font-size:12px;")
        tip.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(tip)

        self.setLayout(main_layout)
        self.user_info = None

        self.try_auto_login()

    def get_hwid(self):
        hwid_parts = []
        try:
            result = subprocess.check_output("wmic diskdrive get serialnumber", shell=True, encoding='utf-8')
            hwid_parts.append(result.strip())
        except:
            pass
        try:
            result = subprocess.check_output("wmic cpu get processorid", shell=True, encoding='utf-8')
            hwid_parts.append(result.strip())
        except:
            pass
        try:
            result = subprocess.check_output("wmic csproduct get uuid", shell=True, encoding='utf-8')
            hwid_parts.append(result.strip())
        except:
            pass
        hwid_parts.append(str(uuid.getnode()))
        raw = "".join(hwid_parts).encode('utf-8', errors='ignore')
        return hashlib.sha256(raw).hexdigest().upper()

    def try_auto_login(self):
        if not self.cb_autologin.isChecked() or not os.path.exists(self.bind_file):
            return

        try:
            f = _get_fernet()
            with open(self.bind_file, "rb") as fh:
                enc = fh.read()
                data = json.loads(f.decrypt(enc).decode('utf-8'))

            current_hwid = self.get_hwid()
            if data["hwid"] == current_hwid:
                # 计算剩余时间
                remaining = self.calculate_remaining(data)
                if remaining <= 0 and data["total_hours"] != "permanent":
                    QMessageBox.critical(self, "卡密过期", "卡密已过期，请联系作者续费。")
                    os.remove(self.bind_file)
                    return

                self.user_info = {
                    "kami": data["kami"],
                    "hwid": current_hwid,
                    "type": data.get("type", "user"),
                    "expire_time": data.get("expire_time", "永久"),
                    "remaining_hours": remaining if data["total_hours"] != "permanent" else "永久"
                }
                self.accept()
        except Exception:
            pass

    def calculate_remaining(self, data):
        if data["total_hours"] == "permanent":
            return "永久"

        total = data["total_hours"]
        used = data.get("used_hours", 0.0)
        last_login = datetime.datetime.fromisoformat(data.get("last_login", datetime.datetime.now().isoformat()))
        now = datetime.datetime.now()
        session_hours = (now - last_login).total_seconds() / 3600
        used += session_hours

        remaining = total - used
        return max(0, remaining)

    def unbind_hwid(self):
        if not os.path.exists(self.bind_file):
            QMessageBox.information(self, "无绑定", "当前设备未绑定卡密。")
            return

        reply = QMessageBox.question(self, "解绑确认", 
                                     "解绑将扣除2小时剩余时间，确定吗？",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                f = _get_fernet()
                with open(self.bind_file, "rb") as fh:
                    enc = fh.read()
                    data = json.loads(f.decrypt(enc).decode('utf-8'))

                if data["total_hours"] != "permanent":
                    data["used_hours"] = data.get("used_hours", 0) + 2
                    enc = f.encrypt(json.dumps(data).encode('utf-8'))
                    with open(self.bind_file, "wb") as fh:
                        fh.write(enc)
                    QMessageBox.information(self, "解绑成功", "已扣除2小时，绑定已清除。")
                os.remove(self.bind_file)
            except Exception as e:
                QMessageBox.critical(self, "解绑失败", str(e))

    def _do_login(self):
        kami = self.le_kami.text().strip()
        if not kami:
            QMessageBox.warning(self, "缺少卡密", "请输入您的卡密。")
            return

        hwid = self.get_hwid()

        # 卡密哈希表（添加你的卡密哈希）
        valid_kami = {
            "EXAMPLE_HASH1": {"total_hours": "permanent", "type": "vip"},
            "EXAMPLE_HASH2": {"total_hours": 100.0, "type": "user"},
            # 用 hashlib.sha256("你的卡密".encode()).hexdigest().upper() 生成哈希填这里
        }

        kami_hash = hashlib.sha256(kami.encode('utf-8')).hexdigest().upper()
        if kami_hash not in valid_kami:
            QMessageBox.critical(self, "卡密错误", "卡密无效！")
            return

        card_info = valid_kami[kami_hash]

        if os.path.exists(self.bind_file):
            try:
                f = _get_fernet()
                with open(self.bind_file, "rb") as fh:
                    enc = fh.read()
                    data = json.loads(f.decrypt(enc).decode('utf-8'))
                if data["hwid"] != hwid:
                    QMessageBox.critical(self, "绑定失败", "此卡密已绑定其他设备！")
                    return
            except:
                QMessageBox.critical(self, "验证失败", "绑定文件损坏")
                return
        else:
            # 首次绑定
            bind_data = {
                "kami": kami,
                "hwid": hwid,
                "total_hours": card_info["total_hours"],
                "used_hours": 0.0,
                "last_login": datetime.datetime.now().isoformat(),
                "type": card_info["type"]
            }
            try:
                f = _get_fernet()
                enc = f.encrypt(json.dumps(bind_data).encode('utf-8'))
                os.makedirs(os.path.dirname(self.bind_file), exist_ok=True)
                with open(self.bind_file, "wb") as fh:
                    fh.write(enc)
            except Exception as e:
                QMessageBox.critical(self, "绑定失败", str(e))
                return

        # 计算剩余时间
        remaining = card_info["total_hours"] if card_info["total_hours"] == "permanent" else card_info["total_hours"]

        self.user_info = {
            "kami": kami,
            "hwid": hwid,
            "type": card_info["type"],
            "expire_time": "永久" if card_info["total_hours"] == "permanent" else f"剩余 {remaining} 小时",
            "remaining_hours": remaining
        }
        self.accept()

    def get_user_info(self):
        return self.user_info or {}
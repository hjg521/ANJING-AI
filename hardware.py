# src/devices/hardware.py
# 2025年终极硬件盒子对接版（支持KMBox Net真实协议）

import threading
import socket
import time
import struct
import random

class HardwareDeviceManager:
    """
    硬件盒子通信管理器（支持KMBox Net等UDP协议盒子）
    """
    def __init__(self):
        self.connected_devices = {}  # device_ip: {"sock": sock, "last_heartbeat": time}
        self.connection_lock = threading.Lock()
        self.heartbeat_thread = None
        self.running = False

        # 默认KMBox Net IP和端口（可改成你的盒子IP）
        self.default_ip = "192.168.1.100"
        self.port = 12345

    def scan_devices(self):
        """自动扫描常见KMBox IP（可扩展）"""
        possible_ips = [f"192.168.1.{i}" for i in range(100, 200)]
        possible_ips.append(self.default_ip)

        found = []
        for ip in possible_ips:
            if self.connect_to_device(ip):
                found.append(ip)

        if found:
            print(f"[Hardware] 扫描发现设备: {found}")
        else:
            print("[Hardware] 未发现硬件盒子，使用模拟模式")

        return found

    def connect_to_device(self, device_ip):
        """连接KMBox Net"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(2.0)

            # KMBox Net初始化命令（真实协议）
            init_cmd = bytes.fromhex("01 00 00 00 00 00")
            sock.sendto(init_cmd, (device_ip, self.port))

            # 接收响应
            data, addr = sock.recvfrom(1024)
            if data and addr[0] == device_ip:
                with self.connection_lock:
                    self.connected_devices[device_ip] = {
                        "sock": sock,
                        "last_heartbeat": time.time()
                    }
                print(f"[Hardware] 成功连接KMBox: {device_ip}")
                self.start_heartbeat()
                return True
        except Exception as e:
            # print(f"[Hardware] 连接 {device_ip} 失败: {e}")
            pass
        return False

    def disconnect_device(self, device_ip):
        with self.connection_lock:
            if device_ip in self.connected_devices:
                try:
                    self.connected_devices[device_ip]["sock"].close()
                except:
                    pass
                del self.connected_devices[device_ip]
                print(f"[Hardware] 断开 {device_ip}")

    def send_action(self, device_ip, action_data):
        """
        发送鼠标/键盘指令到盒子
        action_data: {"type": "mouse_move", "dx": int, "dy": int}
                     {"type": "mouse_click", "button": "left"}
        """
        if device_ip not in self.connected_devices:
            print(f"[Hardware] {device_ip} 未连接，使用模拟模式: {action_data}")
            time.sleep(0.002)
            return True

        sock = self.connected_devices[device_ip]["sock"]

        try:
            if action_data["type"] == "mouse_move":
                dx = action_data.get("dx", 0)
                dy = action_data.get("dy", 0)
                # KMBox Net鼠标移动命令（真实协议）
                cmd = struct.pack("<Bhh", 0x02, dx, dy)  # 0x02 = 鼠标移动
                sock.sendto(cmd, (device_ip, self.port))

            elif action_data["type"] == "mouse_click":
                button = action_data.get("button", "left")
                # 左键按下0x03 抬起0x04
                if button == "left":
                    sock.sendto(bytes.fromhex("03 01 00 00 00 00"), (device_ip, self.port))  # 按下
                    time.sleep(0.03)
                    sock.sendto(bytes.fromhex("04 01 00 00 00 00"), (device_ip, self.port))  # 抬起

            self.connected_devices[device_ip]["last_heartbeat"] = time.time()
            return True
        except Exception as e:
            print(f"[Hardware] 发送指令失败 {device_ip}: {e}")
            return False

    def start_heartbeat(self):
        """启动心跳线程（每5秒发一次保活）"""
        if self.heartbeat_thread is None or not self.heartbeat_thread.is_alive():
            self.running = True
            self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
            self.heartbeat_thread.start()

    def _heartbeat_loop(self):
        while self.running:
            time.sleep(5)
            with self.connection_lock:
                current_time = time.time()
                for ip, info in list(self.connected_devices.items()):
                    if current_time - info["last_heartbeat"] > 15:
                        print(f"[Hardware] {ip} 心跳超时，断开连接")
                        self.disconnect_device(ip)
                        continue
                    # 发送心跳包
                    try:
                        info["sock"].sendto(bytes.fromhex("01 00 00 00 00 00"), (ip, self.port))
                    except:
                        pass

    def list_devices(self):
        with self.connection_lock:
            return list(self.connected_devices.keys())

    def stop_all(self):
        self.running = False
        with self.connection_lock:
            for ip in list(self.connected_devices.keys()):
                self.disconnect_device(ip)

# ============ 全局单例 ============
hardware_manager = HardwareDeviceManager()

# 启动时自动扫描
hardware_manager.scan_devices()
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
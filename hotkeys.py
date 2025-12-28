# src/core/hotkeys.py
from PyQt5.QtCore import QObject, pyqtSignal, Qt
from PyQt5.QtWidgets import QApplication

class HotkeyManager(QObject):
    """
    支持组合键的窗口内热键管理
    """
    hotkeyPressed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._hotkeys = {}  # (key, modifiers): (name, callback)

    def register_hotkey(self, name, qtkey, modifiers=Qt.NoModifier, callback=None):
        combo = (qtkey, modifiers)
        self._hotkeys[combo] = (name, callback)

    def process_key_event(self, event):
        key = event.key()
        modifiers = event.modifiers()

        # 优先精确匹配（带修饰键）
        combo = (key, modifiers)
        if combo in self._hotkeys:
            name, callback = self._hotkeys[combo]
            if callback:
                callback()
            self.hotkeyPressed.emit(name)
            return True

        # fallback 单键匹配
        combo_no_mod = (key, Qt.NoModifier)
        if combo_no_mod in self._hotkeys:
            name, callback = self._hotkeys[combo_no_mod]
            if callback:
                callback()
            self.hotkeyPressed.emit(name)
            return True

        return False

    def install_on_widget(self, widget):
        widget.installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == event.KeyPress:
            if self.process_key_event(event):
                return True
        return super().eventFilter(obj, event)
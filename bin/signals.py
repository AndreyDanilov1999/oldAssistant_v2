from PyQt5.QtCore import QObject, pyqtSignal


class ColorChangeSignal(QObject):
    color_changed = pyqtSignal()

color_signal = ColorChangeSignal()

class GuiSignals(QObject):
    open_widget_signal = pyqtSignal()
    close_widget_signal = pyqtSignal()

gui_signals = GuiSignals()

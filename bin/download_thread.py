from PyQt5.QtCore import QThread, pyqtSignal, QPropertyAnimation
from PyQt5.QtWidgets import QProgressBar

from bin.check_update import download_update


class DownloadThread(QThread):
    download_complete = pyqtSignal(str, bool, bool, str)  # file_path, success, skipped, error
    progress_signal = pyqtSignal(str)

    def __init__(self, type_version, version=None, parent=None):
        super().__init__(parent)
        self.type_version = type_version
        self.version = version

    def run(self):
        download_update(type_version=self.type_version, on_complete=self._handle_complete, version=self.version)
        self.progress_signal.emit("Начинаем загрузку...")

    def _handle_complete(self, file_path, success=True, skipped=False, error=None):
        self.download_complete.emit(file_path, success, skipped, error)


class SliderProgressBar(QProgressBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setRange(0, 100)
        self.setValue(0)
        self.setTextVisible(False)  # Скрываем текст

        # Инициализация анимации
        self.animation = QPropertyAnimation(self, b"value")
        self.animation.setDuration(2000)  # Продолжительность одного цикла
        self.animation.setStartValue(0)
        self.animation.setEndValue(100)
        self.animation.setLoopCount(-1)  # Бесконечное повторение

    def startAnimation(self):
        """Запуск анимации ползунка"""
        self.animation.start()

    def stopAnimation(self):
        """Остановка анимации"""
        self.animation.stop()
        self.setValue(0)  # Сброс в начальное положение
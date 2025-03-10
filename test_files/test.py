from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtWidgets import QLabel, QWidget, QVBoxLayout, QApplication
from PyQt5.QtGui import QDesktopServices

class ClickableLabel(QLabel):
    def __init__(self, text, url, parent=None):
        super().__init__(parent)
        self.url = url
        self.setText(text)
        self.setCursor(Qt.PointingHandCursor)  # Меняем курсор на "руку"

    def mousePressEvent(self, event):
        QDesktopServices.openUrl(QUrl(self.url))  # Открываем URL

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Создаем кликабельный лейбл
        url = "https://disk.yandex.ru/d/YG4jcxkh8wjJCA"  # Ваш URL
        url_label = ClickableLabel("Все версии тут", url)
        layout.addWidget(url_label)

        self.setLayout(layout)
        self.setWindowTitle("Пример текста с ссылкой")

if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec_()
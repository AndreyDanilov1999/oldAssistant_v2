from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout
import sys

class MyWindow(QWidget):
    def __init__(self):
        super().__init__()

        # Создаем кнопку
        self.button = QPushButton("Блестящая кнопка", self)

        # Применяем стиль к кнопке
        self.button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50; /* Основной цвет кнопки */
                border: 1px solid #3E8E41; /* Цвет рамки */
                border-radius: 10px; /* Закругление углов */
                color: white; /* Цвет текста */
                padding: 10px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #45a049; /* Цвет кнопки при наведении */
            }
            QPushButton:pressed {
                background-color: #3E8E41; /* Цвет кнопки при нажатии */
                padding-left: 12px; /* Эффект нажатия */
                padding-top: 12px; /* Эффект нажатия */
            }
        """)

        # Устанавливаем макет
        layout = QVBoxLayout()
        layout.addWidget(self.button)
        self.setLayout(layout)

        # Настройки окна
        self.setWindowTitle("Пример блестящей кнопки")
        self.setGeometry(300, 300, 300, 200)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MyWindow()
    window.show()
    sys.exit(app.exec_())
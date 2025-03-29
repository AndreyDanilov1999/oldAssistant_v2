import csv
from datetime import timedelta, datetime
from pathlib import Path
import pandas as pd
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QMessageBox, QLabel, QStackedWidget, QFrame, QHBoxLayout, \
    QDialog
from logging_config import logger
from path_builder import get_path



class OtherOptionsWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.assistant = parent
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Прочие опции")
        self.setFixedSize(400, 450)

        # Основной layout
        main_layout = QHBoxLayout(self)

        # Левая колонка с кнопками
        left_column = QVBoxLayout()
        left_column.setAlignment(Qt.AlignTop)  # Выравниваем кнопки по верху
        main_layout.addLayout(left_column, 1)

        # Добавляем линию-разделитель
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)  # Вертикальная линия
        separator.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(separator)

        # Правая колонка с содержимым
        self.right_column = QStackedWidget()
        main_layout.addWidget(self.right_column, 2)

        # Добавляем кнопки и их содержимое
        self.add_tab("Счетчик цензуры", CensorCounterWidget(self))
        self.add_tab("Обновления", CheckUpdateWidget(self.assistant))

    def add_tab(self, button_name, content_widget):
        # Создаем кнопку
        button = QPushButton(button_name, self)
        button.clicked.connect(lambda _, w=content_widget: self.right_column.setCurrentWidget(w))

        # Добавляем кнопку в левую колонку
        self.layout().itemAt(0).layout().addWidget(button)

        # Добавляем содержимое в правую колонку
        self.right_column.addWidget(content_widget)


class CensorCounterWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.load_data()

    def init_ui(self):
        # Основной layout
        layout = QVBoxLayout(self)

        # Метки для отображения данных
        self.day_label = QLabel("За день: 0", self)
        self.week_label = QLabel("За последние 7 дней: 0", self)
        self.month_label = QLabel("За последние 30 дней: 0", self)
        self.total_label = QLabel("Всего: 0", self)

        # Добавляем метки в layout
        layout.addWidget(self.day_label)
        layout.addWidget(self.week_label)
        layout.addWidget(self.month_label)
        layout.addWidget(self.total_label)

        self.reset_button = QPushButton("Сбросить счетчик")
        self.reset_button.clicked.connect(self.reset_censor_counter)
        layout.addWidget(self.reset_button)

        layout.addStretch()

    def load_data(self):
        # Загружаем данные из CSV-файла
        file_path = get_path("user_settings", "censor_counter.csv")
        try:
            self.data = pd.read_csv(file_path, parse_dates=["date"])
            self.calculate_scores()
        except Exception as e:
            logger.error(f"Ошибка при загрузке censor_counter.csv: {e}")

    def calculate_scores(self):
        # Текущая дата
        today = datetime.now().date()

        # Данные за день
        day_data = self.data[self.data["date"].dt.date == today]
        day_score = int(day_data["score"].sum())

        # Данные за неделю (последние 7 дней, включая сегодня)
        week_start = today - timedelta(days=6)
        week_data = self.data[self.data["date"].dt.date >= week_start]
        week_score = int(week_data["score"].sum())

        # Данные за месяц (последние 30 дней, включая сегодня)
        month_start = today - timedelta(days=29)
        month_data = self.data[self.data["date"].dt.date >= month_start]
        month_score = int(month_data["score"].sum())

        # Общий счет
        total_score = int(self.data["score"].sum())

        # Обновляем метки
        self.day_label.setText(f"За день: {day_score}")
        self.week_label.setText(f"За последние 7 дней: {week_score}")
        self.month_label.setText(f"За последние 30 дней: {month_score}")
        self.total_label.setText(f"Всего: {total_score}")

    def reset_censor_counter(self):
        """
        Сбрасывает счетчик, обнуляя таблицу censor_counter.csv.
        Оставляет только заголовки.
        """

        # Диалоговое окно с подтверждением
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle('Сброс счетчика')
        msg_box.setText("Точно сбросить значения?")
        yes_button = msg_box.addButton("Да", QMessageBox.YesRole)
        no_button = msg_box.addButton("Нет", QMessageBox.NoRole)
        yes_button.setStyleSheet("padding: 1px 10px;")
        no_button.setStyleSheet("padding: 1px 10px;")
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.exec_()

        # Если пользователь нажал "Нет", выходим из метода
        if msg_box.clickedButton() == no_button:
            logger.info("Сброс счетчика отменен.")
            return

        # Путь к CSV-файлу
        CSV_FILE = get_path('user_settings', 'censor_counter.csv')

        # Проверяем, существует ли файл
        if not Path(CSV_FILE).exists():
            logger.error("Файл censor_counter.csv не существует. Невозможно сбросить счетчик.")
            return

        # Открываем файл для записи и оставляем только заголовки
        with open(CSV_FILE, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['date', 'score', 'total_score'])  # Записываем заголовки

        logger.info("Счетчик успешно сброшен.")

        # Обновляем лейблы после сброса
        self.update_labels()

    def update_labels(self):
        """
        Обновляет лейблы после сброса счетчика.
        """
        try:
            # Обновляем значения в лейблах
            self.day_label.setText("За день: 0")
            self.week_label.setText("За последние 7 дней: 0")
            self.month_label.setText("За последние 30 дней: 0")
            self.total_label.setText("Всего: 0")
        except Exception as e:
            logger.error(f"Ошибка при обновлении лейблов: {e}")


class CheckUpdateWidget(QWidget):
    def __init__(self, assistant, parent=None):
        super().__init__(parent)
        self.assistant = assistant
        self.init_ui()

    def init_ui(self):
        # Основной layout
        layout = QVBoxLayout(self)

        self.check_button = QPushButton("Проверить обновления")
        self.check_button.clicked.connect(self.assistant.check_for_updates_app)
        layout.addWidget(self.check_button)

        layout.addStretch()
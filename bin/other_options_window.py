import csv
import os
from pathlib import Path
import simpleaudio as sa
import numpy as np
import pandas as pd
from PyQt5.QtCore import Qt, QTimer, QPoint, QPropertyAnimation, QEasingCurve
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QMessageBox, QLabel, QStackedWidget, QFrame, QHBoxLayout, \
    QDialog, QLineEdit, QSlider, QCheckBox
from logging_config import logger, debug_logger
from path_builder import get_path



# class OtherOptionsWindow(QDialog):
#     def __init__(self, parent=None):
#         super().__init__(parent)
#         self.assistant = parent
#         self.init_ui()
#
#     def init_ui(self):
#         self.setWindowTitle("Прочие опции")
#         self.setFixedSize(500, 450)
#
#         # Основной layout
#         main_layout = QHBoxLayout(self)
#
#         # Левая колонка с кнопками
#         left_column = QVBoxLayout()
#         left_column.setAlignment(Qt.AlignTop)  # Выравниваем кнопки по верху
#         main_layout.addLayout(left_column, 1)
#
#         # Добавляем линию-разделитель
#         separator = QFrame()
#         separator.setFrameShape(QFrame.VLine)  # Вертикальная линия
#         separator.setFrameShadow(QFrame.Sunken)
#         main_layout.addWidget(separator)
#
#         # Правая колонка с содержимым
#         self.right_column = QStackedWidget()
#         main_layout.addWidget(self.right_column, 2)
#
#         # Добавляем кнопки и их содержимое
#         self.add_tab("Счетчик цензуры", CensorCounterWidget(self))
#         self.add_tab("Обновления", CheckUpdateWidget(self.assistant))
#         self.add_tab("Подробные логи", DebugLoggerWidget(self))
#         self.add_tab("Релакс?", RelaxWidget(self))
#
#     def add_tab(self, button_name, content_widget):
#         # Создаем кнопку
#         button = QPushButton(button_name, self)
#         button.clicked.connect(lambda _, w=content_widget: self.right_column.setCurrentWidget(w))
#
#         # Добавляем кнопку в левую колонку
#         self.layout().itemAt(0).layout().addWidget(button)
#
#         # Добавляем содержимое в правую колонку
#         self.right_column.addWidget(content_widget)
class OtherOptionsWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.assistant = parent
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setWindowModality(Qt.WindowModal)
        self.setFixedSize(450, self.assistant.height())

        # Анимация движения
        self.pos_animation = QPropertyAnimation(self, b"pos")
        self.pos_animation.setDuration(300)
        self.pos_animation.setEasingCurve(QEasingCurve.OutCubic)

        # Анимация прозрачности
        self.opacity_animation = QPropertyAnimation(self, b"windowOpacity")
        self.opacity_animation.setDuration(300)

        self.init_ui()
        self.setup_animation()

    def setup_animation(self):
        # Начальная позиция - слева за границей основного окна
        self.move(self.assistant.x() - self.width(),
                  self.assistant.y())

        # Конечная позиция - прижата к левому краю родителя
        self.final_position = QPoint(
            self.assistant.x() - self.width(),
            self.assistant.y()
        )

    def init_ui(self):
        # Главный контейнер
        self.container = QWidget(self)
        self.container.setObjectName("SettingsContainer")
        self.container.setGeometry(0, 0, self.width(), self.height())

        # Кастомный заголовок
        self.title_bar = QWidget(self.container)
        self.title_bar.setObjectName("TitleBar")
        self.title_bar.setGeometry(0, 0, self.width(), 40)

        self.title_label = QLabel("Прочие опции", self.title_bar)
        self.title_label.setGeometry(15, 5, 200, 30)

        self.close_btn = QPushButton("✕", self.title_bar)
        self.close_btn.setGeometry(self.width() - 40, 5, 30, 30)
        self.close_btn.setObjectName("CloseButton")
        self.close_btn.clicked.connect(self.hide_with_animation)

        # Основной layout под заголовком
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 40, 0, 0)  # Отступ под заголовком
        self.container.setLayout(main_layout)

        # Левая панель с кнопками
        self.tabs_container = QWidget()
        self.tabs_container.setFixedWidth(150)
        self.tabs_container.setObjectName("TabsContainer")

        self.tabs_layout = QVBoxLayout(self.tabs_container)
        self.tabs_layout.setContentsMargins(5, 15, 5, 10)
        self.tabs_layout.setSpacing(5)
        self.tabs_layout.setAlignment(Qt.AlignTop)

        # Правая панель с контентом
        self.content_stack = QStackedWidget()
        self.content_stack.setObjectName("ContentStack")

        # Разделитель
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setFrameShadow(QFrame.Sunken)

        # Компоновка
        main_layout.addWidget(self.tabs_container)
        main_layout.addWidget(separator)
        main_layout.addWidget(self.content_stack)

        # Добавляем вкладки
        self.add_tab("Счетчик цензуры", CensorCounterWidget(self))
        self.add_tab("Обновления", CheckUpdateWidget(self.assistant))
        self.add_tab("Подробные логи", DebugLoggerWidget(self))
        self.add_tab("Релакс?", RelaxWidget(self))

    def add_tab(self, name, widget):
        """Добавляет вкладку с кнопкой"""
        btn = QPushButton(name)
        btn.setCheckable(True)
        btn.setObjectName("TabButton")
        btn.clicked.connect(lambda: self.switch_tab(widget, btn))

        if self.content_stack.count() == 0:
            btn.setChecked(True)

        self.tabs_layout.addWidget(btn)
        self.content_stack.addWidget(widget)

    def switch_tab(self, widget, button):
        """Переключает вкладку"""
        for btn in self.tabs_container.findChildren(QPushButton):
            btn.setChecked(False)
        button.setChecked(True)
        self.content_stack.setCurrentWidget(widget)

    def hide_with_animation(self):
        """Плавное исчезание: движение + прозрачность"""
        # 1. Поднимаем основное окно на передний план
        self.assistant.raise_()

        # 2. Настраиваем обратную анимацию прозрачности
        self.opacity_animation.stop()
        self.opacity_animation.setStartValue(1.0)  # От непрозрачного
        self.opacity_animation.setEndValue(0.0)  # К прозрачному
        self.opacity_animation.finished.connect(self.hide)

        # 3. Настраиваем обратное движение
        self.pos_animation.stop()
        self.pos_animation.setStartValue(self.pos())
        self.pos_animation.setEndValue(QPoint(
            self.assistant.x(),
            self.assistant.y()
        ))

        # 4. Запускаем анимации
        self.pos_animation.start()
        self.opacity_animation.start()

    def hideEvent(self, event):
        """Сброс состояния при скрытии"""
        self.move(self.assistant.x(),
                  self.assistant.y())
        self.setWindowOpacity(0.0)  # Сбрасываем к прозрачному
        self.opacity_animation.finished.disconnect(self.hide)
        super().hideEvent(event)

    def showEvent(self, event):
        """Плавное появление: движение + прозрачность"""
        self.setWindowOpacity(0.0)
        self.opacity_animation.stop()
        self.opacity_animation.setStartValue(0.0)  # Начинаем с прозрачного
        self.opacity_animation.setEndValue(1.0)  # Заканчиваем непрозрачным
        self.pos_animation.stop()
        self.pos_animation.setStartValue(QPoint(
            self.assistant.x(),
            self.assistant.y()
        ))
        self.pos_animation.setEndValue(self.final_position)
        self.pos_animation.start()
        self.opacity_animation.start()
        super().showEvent(event)


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
        """Загружает данные из CSV-файла, проверяет и подготавливает данные."""
        file_path = get_path("user_settings", "censor_counter.csv")

        try:
            # Чтение данных с явным указанием формата и обработкой ошибок
            self.data = pd.read_csv(
                file_path,
                parse_dates=["date"],
                date_format="%Y-%m-%d",  # явный формат вместо dayfirst
                dtype={"score": "Int64", "total_score": "Int64"},  # явное указание типов
                on_bad_lines="warn"  # обработка битых строк
            )

            # Проверка и преобразование даты
            if not pd.api.types.is_datetime64_any_dtype(self.data["date"]):
                self.data["date"] = pd.to_datetime(
                    self.data["date"],
                    format="%Y-%m-%d",
                    errors="coerce"
                )

            # Проверка обязательных колонок
            required_columns = ["date", "score", "total_score"]
            if not all(col in self.data.columns for col in required_columns):
                missing = [col for col in required_columns if col not in self.data.columns]
                raise ValueError(f"Отсутствуют обязательные колонки: {missing}")

            # Обработка пустого DataFrame
            if self.data.empty:
                self.data = pd.DataFrame(columns=required_columns)
                self.data["date"] = pd.to_datetime(self.data["date"])
                self.data["score"] = self.data["score"].astype("Int64")
                self.data["total_score"] = self.data["total_score"].astype("Int64")

            # Удаление строк с некорректными датами
            self.data = self.data.dropna(subset=["date"]).copy()

            # Заполнение пропущенных значений
            self.data["score"] = self.data["score"].fillna(0).astype(int)
            self.data["total_score"] = self.data["total_score"].fillna(0).astype(int)

            logger.info("Данные счетчика цензуры успешно загружены")
            debug_logger.debug("Данные счетчика цензуры успешно загружены")

            self.calculate_scores()

        except FileNotFoundError:
            debug_logger.warning("Файл censor_counter.csv не найден, создаем новый")
            self.data = pd.DataFrame(columns=["date", "score", "total_score"])
            self.data["date"] = pd.to_datetime(self.data["date"])
            self.update_labels()
        except Exception as e:
            logger.error("Ошибка загрузки данных: %s", str(e), exc_info=True)
            debug_logger.error("Ошибка загрузки данных: %s", str(e), exc_info=True)
            self.data = pd.DataFrame(columns=["date", "score", "total_score"])
            self.data["date"] = pd.to_datetime(self.data["date"])
            self.update_labels()

    def calculate_scores(self):
        try:
            # Проверка, что данные загружены
            if not hasattr(self, "data") or self.data.empty:
                self.update_labels()
                return

            # Преобразуем 'date' в datetime (если ещё не)
            if not pd.api.types.is_datetime64_any_dtype(self.data["date"]):
                self.data["date"] = pd.to_datetime(
                    self.data["date"],
                    format="%Y-%m-%d",  # явно указываем формат
                    errors="coerce"  # некорректные -> NaT
                )

            # Удаляем строки с NaT (если есть)
            clean_data = self.data.dropna(subset=["date"]).copy()

            # Если после очистки данных нет — обнуляем
            if clean_data.empty:
                self.update_labels()
                return

            # Текущая дата как pd.Timestamp (без времени)
            today = pd.Timestamp.now().normalize()  # или .floor('D')

            # Для отладки: выводим даты из данных
            debug_logger.info(f"Даты в данных: {clean_data['date'].dt.strftime('%Y-%m-%d').tolist()}")
            debug_logger.info(f"Текущая дата: {today.strftime('%Y-%m-%d')}")

            # Маски для фильтрации
            day_mask = (clean_data["date"].dt.normalize() == today)
            week_mask = (clean_data["date"].dt.normalize() >= (today - pd.Timedelta(days=6)))
            month_mask = (clean_data["date"].dt.normalize() >= (today - pd.Timedelta(days=29)))

            # Проверка масок (для отладки)
            debug_logger.info(f"Строки за день: {clean_data[day_mask]}")
            debug_logger.info(f"Строки за неделю: {clean_data[week_mask]}")
            debug_logger.info(f"Строки за месяц: {clean_data[month_mask]}")

            # Считаем суммы
            day_score = int(clean_data.loc[day_mask, "score"].sum())
            week_score = int(clean_data.loc[week_mask, "score"].sum())
            month_score = int(clean_data.loc[month_mask, "score"].sum())
            total_score = int(clean_data["score"].sum())

            # Обновляем UI
            self.day_label.setText(f"За день: {day_score}")
            self.week_label.setText(f"За последние 7 дней: {week_score}")
            self.month_label.setText(f"За последние 30 дней: {month_score}")
            self.total_label.setText(f"Всего: {total_score}")

        except Exception as e:
            logger.error(f"Ошибка в calculate_scores: {e}", exc_info=True)
            debug_logger.error(f"Ошибка в calculate_scores: {e}", exc_info=True)
            self.update_labels()

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
            debug_logger.info("Сброс счетчика отменен.")
            return

        # Путь к CSV-файлу
        CSV_FILE = get_path('user_settings', 'censor_counter.csv')

        # Проверяем, существует ли файл
        if not Path(CSV_FILE).exists():
            logger.error("Файл censor_counter.csv не существует. Невозможно сбросить счетчик.")
            debug_logger.error("Файл censor_counter.csv не существует. Невозможно сбросить счетчик.")
            return

        # Открываем файл для записи и оставляем только заголовки
        with open(CSV_FILE, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['date', 'score', 'total_score'])  # Записываем заголовки

        logger.info("Счетчик успешно сброшен.")
        debug_logger.info("Счетчик успешно сброшен.")

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
            debug_logger.error(f"Ошибка при обновлении лейблов: {e}")


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

        self.update_check = QCheckBox("Уведомлять о бета-версиях", self)
        self.update_check.setChecked(self.assistant.beta_version)  # Устанавливаем текущее значение
        self.update_check.stateChanged.connect(self.toggle_beta_version)  # Подключаем обработчик
        layout.addWidget(self.update_check)

        layout.addStretch()

    def toggle_beta_version(self, state):
        """Включает/отключает проверку экспериментальных версий"""
        self.assistant.beta_version = state == Qt.Checked


class DebugLoggerWidget(QWidget):
    """Виджет для открытия папки с подробными логами"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.check_button = None
        self.init_ui()

    def init_ui(self):
        # Основной layout
        layout = QVBoxLayout(self)

        self.check_button = QPushButton("Файл логов")
        self.check_button.clicked.connect(self.open_folder)
        layout.addWidget(self.check_button)

        layout.addStretch()

    def open_folder(self):
        path = get_path("log")

        os.startfile(path)


class RelaxWidget(QWidget):
    """Виджет управления звуковыми эффектами(не знаю, прикол)"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.duration = 30
        self.rate = 60
        self.volume_factor = 0.5
        self.is_playing = False  # Переменная состояния
        self.play_obj = None  # Для хранения ссылки на объект воспроизведения
        self.timer = QTimer(self)  # Создаем таймер

        self.timer.timeout.connect(self.timer_finished)  # Подключаем сигнал таймера к методу

        self.init_ui()

    def init_ui(self):
        # Поля для настройки выходного звука
        self.duration_title = QLabel('Укажите длительность в секундах')
        self.duration_field = QLineEdit('30')

        self.rate_title = QLabel('Укажите частоту (не рекомендую выше 450)')
        self.rate_field = QLineEdit('60')

        self.apply_button = QPushButton('Запустить')
        self.apply_button.clicked.connect(self.toggle_play)

        # Создание QLabel для отображения значения
        self.label = QLabel('Значение: 0.50', self)

        # Создание горизонтального ползунка
        self.slider = QSlider(Qt.Horizontal, self)
        self.slider.setMinimum(0)  # Минимальное значение
        self.slider.setMaximum(100)  # Максимальное значение
        self.slider.setValue(50)  # Начальное значение
        self.slider.setTickInterval(10)  # Интервал для отметок
        self.slider.setSingleStep(1)  # Шаг при перемещении ползунка

        # Подключение сигнала изменения значения ползунка к слоту
        self.slider.valueChanged.connect(self.update_volume)

        # Создание вертикального layout
        layout = QVBoxLayout()
        layout.addWidget(self.duration_title)
        layout.addWidget(self.duration_field)
        layout.addWidget(self.rate_title)
        layout.addWidget(self.rate_field)
        layout.addWidget(self.label)
        layout.addWidget(self.slider)
        layout.addStretch()
        layout.addWidget(self.apply_button)

        # Установка layout для виджета
        self.setLayout(layout)

    def update_volume(self, value):
        # Обновление текста в QLabel
        normalized_value = value / 100.0  # Нормализация значения от 0 до 1
        self.volume_factor = normalized_value
        self.label.setText(f'Значение: {normalized_value:.2f}')

    def toggle_play(self):
        # Считываем значения длительности и частоты
        try:
            self.duration = int(self.duration_field.text())
            self.label.setText(f'Длительность: {self.duration} секунд')
        except ValueError:
            self.label.setText('Введите корректное значение для длительности')
            return  # Выход, если значение некорректно

        try:
            self.rate = int(self.rate_field.text())
            self.label.setText(f'Частота: {self.rate} Гц')
        except ValueError:
            self.label.setText('Введите корректное значение для частоты')
            return  # Выход, если значение некорректно

        if self.is_playing:
            self.stop_sound()
        else:
            self.generate_sound()
            self.apply_button.setText('Стоп')
            self.timer.start(self.duration * 1000)  # Запускаем таймер на длительность в миллисекундах
            self.is_playing = True  # Устанавливаем состояние воспроизведения

    def stop_sound(self):
        if self.play_obj is not None:
            self.play_obj.stop()  # Остановка воспроизведения
        self.apply_button.setText('Запустить')
        self.timer.stop()  # Останавливаем таймер
        self.is_playing = False  # Устанавливаем состояние не воспроизведения

    def timer_finished(self):
        self.stop_sound()  # Останавливаем звук, когда таймер истекает

    def generate_sound(self):
        sample_rate = 48000
        new_frequency = self.rate
        volume_factor = self.volume_factor

        # Создаем временной массив
        t = np.linspace(0, self.duration, int(sample_rate * self.duration), endpoint=False)
        audio_data = np.sin(2 * np.pi * new_frequency * t)
        audio_data = (audio_data * volume_factor * 32767).astype(np.int16)

        # Воспроизведение аудио
        self.play_obj = sa.play_buffer(audio_data, 1, 2, sample_rate)
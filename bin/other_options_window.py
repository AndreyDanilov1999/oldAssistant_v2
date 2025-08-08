import csv
import os
from itertools import chain
from pathlib import Path
import simpleaudio as sa
import numpy as np
import pandas as pd
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QMessageBox, QLabel, QHBoxLayout, QDialog,
                             QLineEdit, QSlider, QCheckBox, QTextEdit, QDesktopWidget, QListWidget, QListWidgetItem)
from packaging import version
from bin.apply_color_methods import ApplyColor
from bin.check_update import check_all_versions
from bin.download_thread import DownloadThread, SliderProgressBar
from bin.signals import progress_signal
from logging_config import logger, debug_logger
from path_builder import get_path


class CensorCounterWidget(QWidget):
    """
    Виджет счетчика матерных слов
    """

    def __init__(self, assistant, parent=None):
        super().__init__(parent)
        self.assistant = assistant
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

        self.day_label.setStyleSheet("background: transparent;")
        self.week_label.setStyleSheet("background: transparent;")
        self.month_label.setStyleSheet("background: transparent;")
        self.total_label.setStyleSheet("background: transparent;")

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
            # debug_logger.info(f"Даты в данных: {clean_data['date'].dt.strftime('%Y-%m-%d').tolist()}")
            # debug_logger.info(f"Текущая дата: {today.strftime('%Y-%m-%d')}")

            # Маски для фильтрации
            day_mask = (clean_data["date"].dt.normalize() == today)
            week_mask = (clean_data["date"].dt.normalize() >= (today - pd.Timedelta(days=6)))
            month_mask = (clean_data["date"].dt.normalize() >= (today - pd.Timedelta(days=29)))

            # Проверка масок (для отладки)
            # debug_logger.info(f"Строки за день: {clean_data[day_mask]}")
            # debug_logger.info(f"Строки за неделю: {clean_data[week_mask]}")
            # debug_logger.info(f"Строки за месяц: {clean_data[month_mask]}")

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
        # Используем кастомное диалоговое окно для подтверждения
        result = self.assistant.show_message(
            text="Точно сбросить значения?",
            title="Сброс счетчика",
            message_type="warning",
            buttons=QMessageBox.Yes | QMessageBox.No
        )
        # Если пользователь нажал "Нет" или закрыл окно, выходим из метода
        if result == QMessageBox.No:
            logger.info("Сброс счетчика отменен.")
            debug_logger.info("Сброс счетчика отменен.")
            return

        if result == QMessageBox.Yes:
            # Путь к CSV-файлу
            CSV_FILE = get_path('user_settings', 'censor_counter.csv')

            # Проверяем, существует ли файл
            if not Path(CSV_FILE).exists():
                error_msg = "Файл censor_counter.csv не существует. Невозможно сбросить счетчик."
                logger.error(error_msg)
                debug_logger.error(error_msg)
                self.assistant.show_message(error_msg, "Ошибка", "error")
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
    """
    Виджет для ручной проверки обновлений, выбора определенной версии из списка доступных
    """

    def __init__(self, assistant, parent=None):
        super().__init__(parent)
        self.assistant = assistant
        progress_signal.start_progress.connect(self.animation_start_load)
        progress_signal.stop_progress.connect(self.animation_stop_load)
        self.init_ui()
        self.style_manager = ApplyColor(self)
        self.color_path = self.style_manager.color_path
        self.styles = self.style_manager.load_styles()
        self.style_manager.apply_progressbar(key="QPushButton", widget=self.progress, style="parts")
        self.style_manager.apply_progressbar(key="QPushButton", widget=self.progress_any, style="parts")
        self.style_manager.apply_progressbar(key="QPushButton", widget=self.progress_load_duplicate, style="parts")

    def init_ui(self):
        # Основной layout
        layout = QVBoxLayout(self)

        self.check_button = QPushButton("Проверить обновления")
        self.check_button.clicked.connect(self.assistant.check_update_app)
        layout.addWidget(self.check_button)

        self.update_check = QCheckBox("Уведомлять о бета-версиях", self)
        self.update_check.setStyleSheet("background: transparent;")
        self.update_check.setChecked(self.assistant.beta_version)  # Устанавливаем текущее значение
        self.update_check.stateChanged.connect(self.toggle_beta_version)  # Подключаем обработчик
        layout.addWidget(self.update_check)

        self.rollback = QPushButton("Откатиться до стабильной версии")
        self.rollback.clicked.connect(self.wait_and_rollback)
        layout.addWidget(self.rollback)

        self.progress = SliderProgressBar(self)
        self.progress.hide()
        layout.addWidget(self.progress)

        self.load_any_version = QPushButton("Выбрать из доступных версий")
        self.load_any_version.clicked.connect(self.open_list)
        layout.addWidget(self.load_any_version)

        self.list_versions = QListWidget()
        self.list_versions.setStyleSheet("background: transparent;")
        self.list_versions.setFixedHeight(200)
        self.list_versions.hide()
        layout.addWidget(self.list_versions)

        self.done_button = QPushButton("Установить выбранную версию")
        self.done_button.clicked.connect(self.on_button_click)
        self.done_button.hide()
        layout.addWidget(self.done_button)

        self.progress_any = SliderProgressBar(self)
        self.progress_any.hide()
        layout.addWidget(self.progress_any)

        self.list_versions.itemClicked.connect(self.on_version_click)

        layout.addStretch()

        self.progress_load_duplicate = SliderProgressBar(self)  # Дубликат прогрессбара из основного окна
        self.progress_load_duplicate.hide()
        layout.addWidget(self.progress_load_duplicate)

    def animation_start_load(self):
        self.progress_load_duplicate.show()
        self.progress_load_duplicate.startAnimation()

    def animation_stop_load(self):
        self.progress_load_duplicate.hide()
        self.progress_load_duplicate.stopAnimation()

    def toggle_beta_version(self, state):
        """Включает/отключает проверку экспериментальных версий"""
        self.assistant.beta_version = state == Qt.Checked

    def wait_and_rollback(self):
        # Показываем диалог и получаем результат
        result = self.assistant.show_message(
            "Уверены в своих действиях?",
            "Запрос на откат версии",
            "question",
            buttons=QMessageBox.Ok
        )

        # Обрабатываем результат
        if result == QMessageBox.Ok:
            self.rollback_stable_version()
        else:
            pass

    def rollback_stable_version(self):
        try:
            self.start_load()
            self.download_thread = DownloadThread(type_version="stable")
            self.download_thread.download_complete.connect(
                lambda: self.assistant.update_app(type_version="stable"))
            self.download_thread.finished.connect(self.finish_load)
            self.download_thread.start()
        except Exception as e:
            debug_logger.error(f"Ошибка в методе rollback_stable_version: {e}")

    def start_load(self):
        self.progress.show()
        self.rollback.hide()
        self.progress.startAnimation()

    def finish_load(self):
        self.progress.hide()
        self.rollback.setText("Ожидайте")
        self.progress.stopAnimation()

    def open_list(self):
        self.load_any_version.hide()
        self.load_versions()
        self.list_versions.show()

    def load_versions(self):
        data = check_all_versions()
        all_versions = list(chain.from_iterable(data))
        sorted_versions = sorted(all_versions, key=lambda v: version.parse(v), reverse=True)

        self.list_versions.clear()

        for ver in sorted_versions:
            item = QListWidgetItem(ver)
            if "alpha" in ver or "beta" in ver or "rc" in ver:
                item.setForeground(QColor("orange"))  # Нестабильные
            else:
                item.setForeground(QColor("green"))  # Стабильные
            self.list_versions.addItem(item)

    def on_version_click(self, item):
        """Обработчик клика по версии"""
        selected_version = item.text()
        self.done_button.setText(f"Версия {selected_version}. Установить?")
        self.done_button.show()  # Показываем кнопку

    def on_button_click(self):
        try:
            selected_item = self.list_versions.currentItem()
            if selected_item:
                selected_version = selected_item.text()
                self.list_versions.hide()
                self.done_button.setText(f"Скачивание...")
                self.progress_any.show()
                self.progress_any.startAnimation()
                if any(ver in selected_version for ver in ("alpha", "beta", "rc")):
                    self.download_thread = DownloadThread(type_version="exp", version=selected_version)
                    self.download_thread.download_complete.connect(
                        lambda: self.assistant.update_app(type_version="exp"))
                else:
                    self.download_thread = DownloadThread(type_version="stable", version=selected_version)
                    self.download_thread.download_complete.connect(
                        lambda: self.assistant.update_app(type_version="stable"))

                self.download_thread.finished.connect(self.finish_load_any_version)
                self.download_thread.start()

            else:
                self.assistant.show_notification_message("Версия не выбрана!")
                debug_logger.error("Версия не выбрана!")
        except Exception as e:
            self.done_button.setText(f"Произошла ошибка")
            self.progress_any.hide()
            self.progress_any.stopAnimation()
            logger.error(f"Ошибка в методе one_button_click: {e}")
            debug_logger.error(f"Ошибка в методе one_button_click: {e}")

    def finish_load_any_version(self):
        self.done_button.setText(f"Почти готово...")
        self.progress_any.hide()
        self.progress_any.stopAnimation()


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

        self.open_button = QPushButton("Открыть лог-файл")
        self.open_button.clicked.connect(self.load_window)
        layout.addWidget(self.open_button)

        layout.addStretch()

    def open_folder(self):
        path = get_path("log")
        os.startfile(path)

    def load_window(self):
        try:
            debuglog = DebuglogWindow(self)
            debuglog.show()
        except Exception as e:
            logger.error(f"Ошибка при открытии/закрытии окна дебаг-файла: {e}")
            debug_logger.error(f"Ошибка при открытии/закрытии окна дебаг-файла: {e}")


class DebuglogWindow(QDialog):
    """
    Окно с логами
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setFixedSize(1000, 900)
        screen_geometry = QDesktopWidget().screenGeometry()
        x = (screen_geometry.width() - self.width()) // 2
        y = (screen_geometry.height() - self.height()) // 2
        self.move(x, y)

        # Основной контейнер с рамкой
        container = QWidget(self)
        container.setObjectName("WindowContainer")
        container.setGeometry(0, 0, self.width(), self.height())

        # Заголовок с крестиком
        title_bar = QWidget(container)
        title_bar.setObjectName("TitleBar")
        title_bar.setGeometry(1, 1, self.width() - 2, 35)

        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(10, 5, 10, 5)
        title_layout.setSpacing(5)

        title_label = QLabel("Подробный лог-файл")
        title_label.setStyleSheet("background: transparent;")
        title_label.setObjectName("TitleLabel")
        title_label.setFixedSize(150, 20)
        title_layout.addWidget(title_label)
        title_layout.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setObjectName("CloseButton")
        close_btn.setFixedSize(25, 25)
        close_btn.clicked.connect(self.close)
        title_layout.addWidget(close_btn)

        # Основное содержимое
        content_widget = QWidget(container)
        content_widget.setGeometry(1, 36, self.width() - 2, self.height() - 37)

        # Вертикальный layout
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(10, 10, 10, 10)

        self.log_area = QTextEdit()
        self.log_area.setStyleSheet("background: transparent;")
        self.log_area.setReadOnly(True)
        self.log_area.setFont(QFont("Consolas"))
        self.log_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.load_debuglog()

        layout.addWidget(self.log_area)

        # Кнопка закрытия
        close_button = QPushButton("Закрыть")
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button)

    def load_debuglog(self):
        path = get_path("log", "debug_assist.log")
        try:
            if not os.path.exists(path):
                self.logger.info("Файл логов не найден. Создаем новый.")
                with open(path, "w", encoding="utf-8"):
                    pass  # Создаем пустой файл

            with open(path, "r", encoding="utf-8-sig", errors="replace") as file:
                existing_logs = file.read()
                self.log_area.append(existing_logs)
                self.last_position = file.tell()  # Сохраняем позицию последнего прочитанного байта
        except Exception as e:
            self.logger.error(f"Ошибка при чтении файла логов: {e}")
            self.log_area.append(f"Ошибка при чтении файла логов: {e}")


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
        self.duration_title.setStyleSheet("background: transparent;")
        self.duration_field = QLineEdit('30')

        self.rate_title = QLabel('Укажите частоту (не рекомендую выше 450)')
        self.rate_title.setStyleSheet("background: transparent;")
        self.rate_field = QLineEdit('60')

        self.apply_button = QPushButton('Запустить')
        self.apply_button.clicked.connect(self.toggle_play)

        # Создание QLabel для отображения значения
        self.label = QLabel('Значение: 0.50', self)
        self.label.setStyleSheet("background: transparent;")

        # Создание горизонтального ползунка
        self.slider = QSlider(Qt.Horizontal, self)
        self.slider.setStyleSheet("background: transparent;")
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
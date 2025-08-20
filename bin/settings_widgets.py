import json
import os
import sounddevice as sd
from sounddevice import default

from bin.signals import color_signal
from bin.speak_functions import thread_react
from bin.choose_color_window import ColorSettingsWindow
from path_builder import get_path
from logging_config import logger, debug_logger
from PyQt5.QtCore import pyqtSignal, Qt, QPoint, QPropertyAnimation, QEasingCurve
from PyQt5.QtWidgets import QFileDialog, QPushButton, QCheckBox, QLineEdit, QLabel, QSlider, QComboBox, \
    QVBoxLayout, QWidget, QDialog, QFrame, QStackedWidget, QHBoxLayout, QApplication

speakers = dict(Персик="persik", Джарвис="jarvis", Пласид='placide', Бестия='rogue',
                Джонни='johnny', СанСаныч='sanych', Санбой='sanboy', Woman='tigress', Стейтем='stathem')


class InterfaceWidget(QWidget):
    """Виджет настроек оформления интерфейса"""

    def __init__(self, assistant, parent=None):
        super().__init__(parent)
        self.assistant = assistant
        self.init_ui()

    style_applied = pyqtSignal(dict)  # Сигнал для передачи стиля

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(20)

        # Заголовок
        title = QLabel("Выбор стиля интерфейса")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("background: transparent; font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        # Контейнер для двух колонок
        cols = QHBoxLayout()
        left_col = QVBoxLayout()
        right_col = QVBoxLayout()

        # Левая колонка
        btn_dark_orange = QPushButton("Оранжевый неон")
        btn_dark_orange.clicked.connect(lambda: self.apply_style_file("orange_neon.json"))
        left_col.addWidget(btn_dark_orange)

        btn_dark_blue = QPushButton("Синий неон")
        btn_dark_blue.clicked.connect(lambda: self.apply_style_file("blue_neon.json"))
        left_col.addWidget(btn_dark_blue)

        btn_dark_green = QPushButton("Зеленый неон")
        btn_dark_green.clicked.connect(lambda: self.apply_style_file("green_neon.json"))
        left_col.addWidget(btn_dark_green)

        btn_dark_purple = QPushButton("Розовый неон")
        btn_dark_purple.clicked.connect(lambda: self.apply_style_file("pink_neon.json"))
        left_col.addWidget(btn_dark_purple)

        btn_dark_red = QPushButton("Красный неон")
        btn_dark_red.clicked.connect(lambda: self.apply_style_file("red_neon.json"))
        left_col.addWidget(btn_dark_red)

        btn_dark_blue = QPushButton("Голубой неон")
        btn_dark_blue.clicked.connect(lambda: self.apply_style_file("dark_blue.json"))
        left_col.addWidget(btn_dark_blue)

        btn_purple_neon = QPushButton("Фиолетовый неон")
        btn_purple_neon.clicked.connect(lambda: self.apply_style_file("purple_neon.json"))
        left_col.addWidget(btn_purple_neon)

        # Правая колонка
        btn_dark = QPushButton("Dark")
        btn_dark.clicked.connect(lambda: self.apply_style_file("dark.json"))
        right_col.addWidget(btn_dark)

        btn_legacy = QPushButton("Legacy")
        btn_legacy.clicked.connect(lambda: self.apply_style_file("legacy.json"))
        right_col.addWidget(btn_legacy)

        btn_white = QPushButton("White")
        btn_white.clicked.connect(lambda: self.apply_style_file("white.json"))
        right_col.addWidget(btn_white)

        btn_white_orange = QPushButton("Blue-Orange")
        btn_white_orange.clicked.connect(lambda: self.apply_style_file("blue_orange.json"))
        right_col.addWidget(btn_white_orange)

        btn_purple = QPushButton("MoonLight")
        btn_purple.clicked.connect(lambda: self.apply_style_file("moonlight.json"))
        right_col.addWidget(btn_purple)

        btn_pink_blue = QPushButton("Pink-Blue")
        btn_pink_blue.clicked.connect(lambda: self.apply_style_file("pink_blue.json"))
        right_col.addWidget(btn_pink_blue)

        btn_orange_purple = QPushButton("Закат")
        btn_orange_purple.clicked.connect(lambda: self.apply_style_file("sunset.json"))
        right_col.addWidget(btn_orange_purple)

        cols.addLayout(left_col)
        cols.addLayout(right_col)
        layout.addLayout(cols)

        # Выпадающий список для кастомных стилей
        self.custom_presets_combo = QComboBox()
        self.custom_presets_combo.addItem("Выберите пользовательский стиль...")
        self.load_custom_presets()
        self.custom_presets_combo.currentIndexChanged.connect(self.apply_custom_style)
        self.label_styles = QLabel("Пользовательские стили:")
        self.label_styles.setStyleSheet("background: transparent;")
        layout.addWidget(self.label_styles)

        layout.addWidget(self.custom_presets_combo)

        layout.addStretch()

        btn_default = QPushButton("Default")
        btn_default.clicked.connect(lambda: self.apply_style_file("default.json"))
        layout.addWidget(btn_default)

        # Кнопка создания своего стиля
        create_btn = QPushButton("Создать свой стиль")
        create_btn.clicked.connect(self.open_color_settings)
        layout.addWidget(create_btn)

    def apply_style_file(self, filename):
        """Применяет стиль из указанного файла, проверяя обе директории."""
        base_presets = get_path('bin', 'color_presets')
        custom_presets = get_path('user_settings', 'presets')

        # Проверяем, в какой папке есть файл (приоритет у custom_presets)
        preset_path = None
        custom_path = os.path.join(custom_presets, filename)
        base_path = os.path.join(base_presets, filename)

        if os.path.exists(custom_path):
            preset_path = custom_path
        elif os.path.exists(base_path):
            preset_path = base_path
        else:
            logger.error(f"Пресет '{filename}' не найден ни в одной из папок.")
            debug_logger.error(f"Пресет '{filename}' не найден ни в одной из папок.")
            return

        try:
            with open(preset_path, 'r', encoding='utf-8') as json_file:
                styles = json.load(json_file)

                # Сохраняем стили в основной файл настроек
                with open(self.assistant.color_path, 'w') as f:
                    json.dump(styles, f, indent=4)

                # Применяем стили
                self.assistant.styles = styles
                self.assistant.apply_styles()
                self.assistant.check_start_win()
                color_signal.color_changed.emit()
                self.assistant.show_notification_message(message=f"Стиль успешно применен!")
                debug_logger.info(f"Применён стиль из файла: {filename}")

        except json.JSONDecodeError:
            logger.error(f"Ошибка: файл пресета повреждён ({preset_path}).")
            debug_logger.error(f"Ошибка: файл пресета повреждён ({preset_path}).")
        except Exception as e:
            logger.error(f"Ошибка загрузки пресета: {e}")
            debug_logger.error(f"Ошибка загрузки пресета: {e}")
            self.assistant.show_message(f"Ошибка загрузки пресета: {e}", "Ошибка", "error")

    def load_custom_presets(self):
        """Загружает список пользовательских пресетов в выпадающий список"""
        self.custom_presets_combo.clear()
        self.custom_presets_combo.addItem("Тут Ваши созданные стили...")

        custom_presets_dir = get_path('user_settings', 'presets')

        if os.path.exists(custom_presets_dir):
            for filename in sorted(os.listdir(custom_presets_dir)):
                if filename.endswith('.json'):
                    preset_name = filename[:-5]  # Убираем расширение .json
                    self.custom_presets_combo.addItem(preset_name)

    def apply_custom_style(self, index):
        """Применяет выбранный пользовательский стиль"""
        if index == 0:  # Первый элемент - заглушка
            return

        preset_name = self.custom_presets_combo.currentText()
        if preset_name:
            # Добавляем расширение .json, если его нет
            if not preset_name.endswith('.json'):
                preset_name += '.json'
            self.apply_style_file(preset_name)

    def open_color_settings(self):
        """Открывает диалоговое окно для настройки цветов."""
        try:
            color_dialog = ColorSettingsWindow(assistant=self.assistant, parent=self)
            color_dialog.colorChanged.connect(self.assistant.apply_styles)
            color_dialog.exec_()
        except Exception as e:
            logger.error(f"Ошибка при открытии окна настроек цветов: {e}")
            debug_logger.error(f"Ошибка при открытии окна настроек цветов: {e}")
            self.assistant.show_message(f"Не удалось открыть настройки цветов: {e}", "Ошибка", "error")


class SettingsWidget(QWidget):
    """
    Виджет общих настроек
    """
    voice_changed = pyqtSignal(str)

    def __init__(self, assistant, parent=None):
        super().__init__(parent)
        self.assistant = assistant
        self.current_voice = None
        self.current_name = None
        self.current_name2 = None
        self.current_name3 = None
        self.current_steam_path = None
        self.current_volume = None
        self.name_1 = None
        self.load_current_settings()
        self.init_ui()

    def load_current_settings(self):
        self.current_voice = self.assistant.speaker
        self.current_name = self.assistant.assistant_name
        self.current_name2 = self.assistant.assist_name2
        self.current_name3 = self.assistant.assist_name3
        self.current_steam_path = self.assistant.steam_path
        self.current_volume = self.assistant.volume_assist

    def hide_method(self):
        """Закрывает панель настроек через главный класс"""
        if hasattr(self.assistant, 'hide_widget'):
            self.assistant.hide_widget()
        else:
            debug_logger.error("Метод close_settings не найден в assistant")

    def init_ui(self):
        # Создаем виджет-контейнер для содержимого
        content_widget = QWidget()
        self.setLayout(QVBoxLayout())
        self.layout().addWidget(content_widget)

        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Поле для ввода имени ассистента
        name_label = QLabel("Основное имя ассистента:", self)
        name_label.setStyleSheet("background: transparent;")
        layout.addWidget(name_label, alignment=Qt.AlignLeft)

        self.name_input = QLineEdit(self)
        self.name_input.setText(self.assistant.assistant_name)
        layout.addWidget(self.name_input)

        # Поле для ввода имени №2
        name2_label = QLabel("Дополнительно:", self)
        name2_label.setAttribute(Qt.WA_StyledBackground, True)
        name2_label.setStyleSheet("background: transparent;")
        layout.addWidget(name2_label, alignment=Qt.AlignLeft)

        self.name2_input = QLineEdit(self)
        self.name2_input.setText(self.assistant.assist_name2)
        layout.addWidget(self.name2_input)

        # Поле для ввода имени №3
        self.name3_input = QLineEdit(self)
        self.name3_input.setText(self.assistant.assist_name3)
        layout.addWidget(self.name3_input)

        # Выбор голоса
        voice_label = QLabel("Выберите голос:", self)
        voice_label.setStyleSheet("background: transparent;")
        layout.addWidget(voice_label, alignment=Qt.AlignLeft)

        self.voice_combo = QComboBox(self)
        self.voice_combo.addItems(list(speakers.keys()))
        current_key = next(key for key, value in speakers.items() if value == self.assistant.speaker)
        self.voice_combo.setCurrentText(current_key)
        self.voice_combo.currentIndexChanged.connect(self.on_voice_change)
        layout.addWidget(self.voice_combo)

        # Громкость
        volume_label = QLabel("Громкость ассистента", self)
        volume_label.setStyleSheet("background: transparent;")
        layout.addWidget(volume_label, alignment=Qt.AlignLeft)

        self.volume_slider = QSlider(Qt.Horizontal, self)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(int(self.assistant.volume_assist * 100))
        self.volume_slider.valueChanged.connect(self.update_volume)
        layout.addWidget(self.volume_slider)

        self.check_voice = QPushButton("Тест голоса", self)
        self.check_voice.clicked.connect(self.check_new_voice)
        layout.addWidget(self.check_voice)

        # Путь к Steam
        steam_label = QLabel("Укажите полный путь к файлу steam.exe", self)
        steam_label.setStyleSheet("background: transparent;")
        layout.addWidget(steam_label, alignment=Qt.AlignLeft)

        self.steam_path_input = QLineEdit(self)
        self.steam_path_input.setText(self.assistant.steam_path)
        layout.addWidget(self.steam_path_input)

        select_steam_button = QPushButton("Выбрать папку", self)
        select_steam_button.setStyleSheet("padding-left: 5px; padding-right: 5px;")
        select_steam_button.clicked.connect(self.select_steam_folder)
        layout.addWidget(select_steam_button, alignment=Qt.AlignRight)

        layout.addStretch()

        self.default_btn = QPushButton("По умолчанию")
        self.default_btn.setStyleSheet("padding-left: 5px; padding-right: 5px;")
        self.default_btn.clicked.connect(self.set_default_settings)
        layout.addWidget(self.default_btn, alignment=Qt.AlignLeft)

        # Кнопка применения
        apply_button = QPushButton("Применить", self)
        apply_button.clicked.connect(self.apply_settings)
        layout.addWidget(apply_button, alignment=Qt.AlignBottom)

    def update_volume(self, value):
        self.assistant.volume_assist = value / 100.0
        self.assistant.save_settings()

    def select_steam_folder(self):
        folder_path = QFileDialog.getExistingDirectory(
            self, "Выберите папку с steam.exe")

        if folder_path:
            # Проверяем наличие steam.exe в выбранной папке
            steam_exe_path = os.path.normpath(os.path.join(folder_path, "steam.exe"))
            if os.path.exists(steam_exe_path):
                self.steam_path_input.setText(steam_exe_path)
            else:
                self.assistant.show_message("Файл steam.exe не найден в выбранной папке!", "Предупреждение", "warning")

    def on_voice_change(self):
        new_voice_key = self.voice_combo.currentText()
        if new_voice_key in speakers:
            self.voice_changed.emit(speakers[new_voice_key])
            self.assistant.save_settings()

    def check_new_voice(self):
        """
        Метод для озвучивания выбранного голоса (в качестве проверки)
        """
        try:
            path = self.assistant.audio_paths
            get_path = path.get("echo_folder")
            thread_react(get_path)
        except Exception as e:
            logger.error(f"При тесте голоса произошла ошибка:{e}")
            debug_logger.error(f"При тесте голоса произошла ошибка:{e}")

    def update_ui(self):
        """Обновляет UI виджета текущими настройками"""
        self.name_input.setText(self.assistant.assistant_name)
        self.name2_input.setText(self.assistant.assist_name2)
        self.name3_input.setText(self.assistant.assist_name3)
        self.steam_path_input.setText(self.assistant.steam_path)
        self.volume_slider.setValue(int(self.assistant.volume_assist * 100))

        # Установка текущего голоса в комбобокс
        current_key = next((key for key, value in speakers.items() if value == self.assistant.speaker), None)
        if current_key:
            self.voice_combo.setCurrentText(current_key)

    def set_default_settings(self):
        default_settings = {
            "voice": "johnny",
            "assistant_name": "джо",
            "assist_name2": "джо",
            "assist_name3": "джо",
            "steam_path": "D:/Steam/steam.exe",
            "is_censored": True,
            "volume_assist": 0.2,
            "run_updater": True,
            "minimize_to_tray": False,
            "start_win": True,
            "is_widget": True,
            "input_device_id": None,
            "input_device_name": None
        }

        if os.path.exists(self.assistant.settings_file_path):
            with open(self.assistant.settings_file_path, "r", encoding="utf-8") as file:
                try:
                    settings = json.load(file)
                except json.JSONDecodeError:
                    settings = {}
        else:
            settings = {}

        for key, value in default_settings.items():
            settings[key] = value

        with open(self.assistant.settings_file_path, "w", encoding="utf-8") as file:
            json.dump(settings, file, ensure_ascii=False, indent=4)
            self.assistant.show_notification_message("Установлены настройки по умолчанию!")

        # Загружаем настройки в ассистента
        self.assistant.install_settings()
        # Обновляем текущие настройки в виджете
        self.load_current_settings()
        # Обновляем UI
        self.update_ui()

    def apply_settings(self):
        new_name = self.name_input.text().strip().lower()
        if not new_name:
            self.assistant.show_message(f"Имя ассистента не может быть пустым", "Предупреждение", "warning")
            return

        new_name2 = self.name2_input.text().strip().lower()
        new_name3 = self.name3_input.text().strip().lower()
        new_steam_path = self.steam_path_input.text().strip()

        if not os.path.isfile(new_steam_path):
            self.assistant.show_message(f"Укажите правильный путь к steam.exe", "Предупреждение", "warning")
            return

        # Обновляем параметры в родительском окне
        self.assistant.assistant_name = new_name
        self.assistant.assist_name2 = new_name2 if new_name2 else new_name
        self.assistant.assist_name3 = new_name3 if new_name3 else new_name
        self.assistant.steam_path = new_steam_path
        self.assistant.speaker = speakers[self.voice_combo.currentText()]

        self.assistant.save_settings()
        self.hide_method()
        self.assistant.show_notification_message(message="Настройки применены!")


class OtherSettingsWidget(QWidget):
    """ Виджет с дополнительными настройками (перенёс сюда чекбоксы) """

    def __init__(self, assistant, parent=None):
        super().__init__(parent)
        self.assistant = assistant
        self.init_ui()
        self.get_devices()

    def init_ui(self):
        content_widget = QWidget()
        self.setLayout(QVBoxLayout())
        self.layout().addWidget(content_widget)

        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Чекбоксы
        self.censor_check = QCheckBox("Реагировать на мат", self)
        self.censor_check.setStyleSheet("background: transparent;")
        self.censor_check.setChecked(self.assistant.is_censored)
        self.censor_check.stateChanged.connect(self.toggle_censor)
        layout.addWidget(self.censor_check)

        self.update_check = QCheckBox("Запуск утилиты обновления перед стартом", self)
        self.update_check.setStyleSheet("background: transparent;")
        self.update_check.setChecked(self.assistant.run_updater)
        self.update_check.stateChanged.connect(self.toggle_update)
        layout.addWidget(self.update_check)

        self.start_win_check = QCheckBox("Запуск с Windows", self)
        self.start_win_check.setStyleSheet("background: transparent;")
        self.start_win_check.setChecked(self.assistant.toggle_start)
        self.start_win_check.stateChanged.connect(self.assistant.toggle_start_win)
        layout.addWidget(self.start_win_check)

        # Чекбокс для сворачивания в трей
        self.minimize_check = QCheckBox("Сворачивать в трей при запуске", self)
        self.minimize_check.setStyleSheet("background: transparent;")
        self.minimize_check.setChecked(self.assistant.is_min_tray)
        self.minimize_check.stateChanged.connect(self.toggle_minimize)
        layout.addWidget(self.minimize_check)

        self.widget_check = QCheckBox("Запускать виджет", self)
        self.widget_check.setStyleSheet("background: transparent;")
        self.widget_check.setToolTip("Открытие виджета при запуске программы")
        self.widget_check.setChecked(self.assistant.is_widget)
        self.widget_check.stateChanged.connect(self.toggle_widget)
        layout.addWidget(self.widget_check)

        self.get_widget_btn = QPushButton("Открыть виджет", self)
        self.get_widget_btn.clicked.connect(self.get_widget)
        layout.addWidget(self.get_widget_btn)

        self.label_input = QLabel("Устройство ввода")
        self.label_input.setStyleSheet("background: transparent;")
        self.device_list = QComboBox()
        layout.addWidget(self.label_input)
        layout.addWidget(self.device_list)

        layout.addStretch()

        self.device_list.activated.connect(self.on_microphone_selected)

    def toggle_censor(self):
        self.assistant.is_censored = self.censor_check.isChecked()
        self.assistant.save_settings()

    def toggle_update(self):
        self.assistant.run_updater = self.update_check.isChecked()
        self.assistant.save_settings()

    def toggle_minimize(self):
        """Обработка чекбокса 'Сворачивать в трей'"""
        self.assistant.is_min_tray = self.minimize_check.isChecked()
        self.assistant.save_settings()

    def toggle_widget(self):
        """Обработка чекбокса 'Запускать виджет'"""
        self.assistant.is_widget = self.widget_check.isChecked()
        self.assistant.save_settings()

    def get_widget(self):
        self.assistant.open_widget()

    def get_devices(self):
        self.device_list.clear()

        try:
            devices = self.get_input_devices()

            if not devices:
                self.device_list.addItem("Нет активных микрофонов")
                return

            for name, index in devices:
                self.device_list.addItem(name, index)

        except Exception as e:
            self.device_list.addItem("Нет активных микрофонов")
            self.assistant.show_notification_message(f"Ошибка при получении данных аудиоустройств: {str(e)}")
            debug_logger.error(f"Ошибка при получении данных аудиоустройств: {str(e)}")

    def get_input_devices(self):
        devices = sd.query_devices()
        active_mics = []
        seen_names = set()  # Для борьбы с дублями
        try:
            for device in devices:
                try:
                    if device.get('max_input_channels', 0) == 0:
                        continue  # Только вход

                    name = device.get('name', '').strip()
                    idx = device['index']

                    # --- Фильтр: исключаем системные/виртуальные ---
                    if any(keyword in name.lower() for keyword in [
                        'mapper', 'primary', 'wave', 'звуковой маршрутизатор',
                        'драйвер записи', 'default', 'аналоговый'
                    ]):
                        continue

                    # Получаем тип API
                    host_api_name = sd.query_hostapis(device['hostapi'])['name']
                    if host_api_name.lower() in ['mm', 'mme', 'directsound']:
                        # Пропускаем MME и DirectSound, если есть WASAPI аналог
                        # Но можно временно добавить для теста с пометкой
                        continue  # ← лучше использовать только WASAPI

                    # Упрощаем имя для сравнения (убираем цифры в скобках и т.п.)
                    clean_name = name.split('(')[0].strip()

                    # Избегаем дублей по базовому имени
                    if clean_name in seen_names:
                        continue
                    seen_names.add(clean_name)

                    # Проверяем, можно ли открыть поток
                    try:
                        with sd.InputStream(
                                device=idx,
                                channels=1,
                                samplerate=44100,
                                blocksize=1024
                        ):
                            active_mics.append((name, idx))
                    except Exception:
                        continue  # Не удалось открыть

                except Exception:
                    continue

            return active_mics
        except Exception as e:
            debug_logger.error(f"Ошибка в проверке активных микрофонов: {str(e)}")

    def on_microphone_selected(self):
        device_id = self.device_list.currentData()  # int или None
        if device_id is not None:
            # Получаем имя устройства по ID
            device_info = sd.query_devices(device_id)
            device_name = device_info['name']

            # Сохраняем и ID, и имя
            self.assistant.input_device_id = device_id
            self.assistant.input_device_name = device_name

            # Сохраняем в файл настроек
            self.assistant.save_settings()
            self.assistant.save_settings_signal.emit()

            debug_logger.info(f"Выбрано устройство: '{device_name}' (ID={device_id})")

    def hide_method(self):
        """Закрывает панель настроек через главный класс"""
        if hasattr(self.assistant, 'hide_widget'):
            self.assistant.hide_widget()
        else:
            debug_logger.error("Метод close_settings не найден в assistant")

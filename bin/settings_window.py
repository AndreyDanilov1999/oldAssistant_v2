import json
import os
import sounddevice as sd
from bin.signals import color_signal
from bin.speak_functions import thread_react
from bin.choose_color_window import ColorSettingsWindow
from path_builder import get_path
from logging_config import logger, debug_logger
from PyQt5.QtCore import pyqtSignal, Qt, QPoint, QPropertyAnimation, QEasingCurve
from PyQt5.QtWidgets import QFileDialog, QPushButton, QCheckBox, QLineEdit, QLabel, QSlider, QComboBox, \
    QVBoxLayout, QWidget, QDialog, QFrame, QStackedWidget, QHBoxLayout, QApplication

speakers = dict(Персик="persik", Джарвис="jarvis", Пласид='placide', Бестия='rogue',
                Джонни='johnny', СанСаныч='sanych', Санбой='sanboy', Тигрица='tigress', Стейтем='stathem')


# class MainSettingsWindow(QDialog):
#     """Окно настроек с анимацией и кнопками вкладок"""
#
#     def __init__(self, parent=None):
#         super().__init__(parent)
#         self.assistant = parent
#         self.settings_widget = SettingsWidget(self.assistant, self)
#         self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
#         self.setFixedSize(450, self.assistant.height())
#
#         # Подключаем сигнал родителя к слоту закрытия
#         if parent and hasattr(parent, "close_child_windows"):
#             parent.close_child_windows.connect(self.hide_with_animation)
#
#         # Анимация движения
#         self.pos_animation = QPropertyAnimation(self, b"pos")
#         self.pos_animation.setDuration(300)
#         self.pos_animation.setEasingCurve(QEasingCurve.OutCubic)
#
#         # Анимация прозрачности
#         self.opacity_animation = QPropertyAnimation(self, b"windowOpacity")
#         self.opacity_animation.setDuration(300)
#         self.opacity_animation.setKeyValueAt(0.0, 0.0)
#         self.opacity_animation.setKeyValueAt(0.5, 0.1)
#         self.opacity_animation.setKeyValueAt(0.8, 0.8)
#         self.opacity_animation.setKeyValueAt(1.0, 1.0)
#
#         self.init_ui()
#         self.setup_animation()
#
#     def init_ui(self):
#         self.setAttribute(Qt.WA_TranslucentBackground)
#         self.container = QWidget(self)
#         self.container.setObjectName("SettingsContainer")
#         self.container.setGeometry(0, 0, self.width(), self.height())
#
#         # Кастомный заголовок
#         self.title_bar = QWidget(self.container)
#         self.title_bar.setObjectName("TitleBar")
#         self.title_bar.setGeometry(0, 0, self.width(), 35)
#         self.title_layout = QHBoxLayout(self.title_bar)
#         self.title_layout.setContentsMargins(10, 5, 10, 5)
#         self.title_layout.setSpacing(5)
#
#         self.title_label = QLabel("Настройки", self.title_bar)
#         self.title_label.setStyleSheet("background: transparent;")
#         self.title_label.setGeometry(15, 5, 200, 30)
#         self.title_layout.addWidget(self.title_label)
#         self.close_btn = QPushButton("✕", self.title_bar)
#         self.close_btn.setFixedSize(25, 25)
#         self.close_btn.setObjectName("CloseButton")
#         self.close_btn.clicked.connect(self.hide_with_animation)
#         self.title_layout.addWidget(self.close_btn)
#
#         # Контейнер для кнопок вкладок
#         self.tabs_container = QWidget(self.container)
#         self.tabs_container.setGeometry(0, 40, 120, self.height() - 40)
#         self.tabs_container.setObjectName("TabsContainer")
#
#         # Вертикальный layout с выравниванием по верхнему краю
#         self.tabs_layout = QVBoxLayout(self.tabs_container)
#         self.tabs_layout.setContentsMargins(5, 15, 5, 10)
#         self.tabs_layout.setSpacing(5)
#         self.tabs_layout.setAlignment(Qt.AlignTop)
#
#         # Контейнер для содержимого
#         self.content_stack = QStackedWidget(self.container)
#         self.content_stack.setGeometry(120, 40, self.width() - 120, self.height() - 40)
#         self.content_stack.setObjectName("ContentStack")
#
#         # Разделитель
#         self.separator = QFrame(self.container)
#         self.separator.setGeometry(120, 40, 1, self.height() - 40)
#         self.separator.setFrameShape(QFrame.VLine)
#
#         # Добавляем вкладки
#         self.add_tab("Основные", SettingsWidget(self.assistant, self))
#         self.add_tab("Дополнительно", OtherSettingsWidget(self.assistant, self))
#         self.add_tab("Интерфейс", InterfaceWidget(self.assistant))
#
#     def keyPressEvent(self, event):
#         """
#         Сворачивает с анимацией
#         :param event:
#         """
#         if event.key() == Qt.Key_Escape:
#             if self.opacity_animation.state() != QPropertyAnimation.Running:
#                 self.hide_with_animation()
#             event.accept()
#         else:
#             super().keyPressEvent(event)
#
#     def add_tab(self, name, widget):
#         """Добавляет вкладку с кнопкой"""
#         btn = QPushButton(name)
#         btn.setCheckable(True)
#         btn.setObjectName("TabButton")
#         btn.clicked.connect(lambda: self.switch_tab(widget, btn))
#
#         if self.content_stack.count() == 0:
#             btn.setChecked(True)
#
#         self.tabs_layout.addWidget(btn)  # Кнопки будут прижаты к верху
#         self.content_stack.addWidget(widget)
#
#     def switch_tab(self, widget, button):
#         """Переключает вкладку"""
#         for btn in self.tabs_container.findChildren(QPushButton):
#             btn.setChecked(False)
#         button.setChecked(True)
#         self.content_stack.setCurrentWidget(widget)
#
#     def setup_animation(self):
#         # Начальная позиция - слева за границей основного окна
#         self.move(self.assistant.x() - self.width(),
#                   self.assistant.y())
#
#         # Конечная позиция - прижата к левому краю родителя
#         self.final_position = QPoint(
#             self.assistant.x() - self.width(),
#             self.assistant.y()
#         )
#
#     def hide_with_animation(self):
#         """Плавное исчезание: движение + прозрачность"""
#         # 1. Поднимаем основное окно на передний план
#         self.assistant.raise_()
#
#         # 2. Настраиваем обратную анимацию прозрачности
#         self.opacity_animation.stop()
#         self.opacity_animation = QPropertyAnimation(self, b"windowOpacity")
#         self.opacity_animation.setDuration(300)
#         self.opacity_animation.setKeyValueAt(0.0, 1.0)  # От непрозрачного
#         self.opacity_animation.setKeyValueAt(0.1, 0.8)
#         self.opacity_animation.setKeyValueAt(0.2, 0.6)
#         self.opacity_animation.setKeyValueAt(0.3, 0.3)
#         self.opacity_animation.setKeyValueAt(1.0, 0.0)
#         # self.opacity_animation.setStartValue(1.0)
#         # self.opacity_animation.setEndValue(0.0)
#         self.opacity_animation.finished.connect(self.hide)
#
#         # 3. Настраиваем обратное движение
#         self.pos_animation.stop()
#         self.pos_animation.setStartValue(self.pos())
#         self.pos_animation.setEndValue(QPoint(
#             self.assistant.x(),
#             self.assistant.y()
#         ))
#
#         # 4. Запускаем анимации
#         self.pos_animation.start()
#         self.opacity_animation.start()
#
#     def hideEvent(self, event):
#         """Сброс состояния при скрытии"""
#         self.move(self.assistant.x(),
#                   self.assistant.y())
#         self.setWindowOpacity(0.0)  # Сбрасываем к прозрачному
#         self.opacity_animation.finished.disconnect(self.hide)
#         super().hideEvent(event)
#
#     def showEvent(self, event):
#         """Плавное появление: движение + прозрачность"""
#         # 1. Устанавливаем начальную прозрачность
#         self.setWindowOpacity(0.0)
#
#         # 2. Настраиваем анимацию прозрачности
#         self.opacity_animation.stop()
#         self.opacity_animation.setStartValue(0.0)  # Начинаем с прозрачного
#         self.opacity_animation.setEndValue(1.0)  # Заканчиваем непрозрачным
#
#         # 3. Настраиваем анимацию движения
#         self.pos_animation.stop()
#         self.pos_animation.setStartValue(QPoint(
#             self.assistant.x(),
#             self.assistant.y()
#         ))
#         self.pos_animation.setEndValue(self.final_position)
#
#         # 4. Запускаем обе анимации
#         self.pos_animation.start()
#         self.opacity_animation.start()
#
#         super().showEvent(event)
#
#     def get_settings_widget(self):
#         for i in range(self.content_stack.count()):
#             widget = self.content_stack.widget(i)
#             if isinstance(widget, SettingsWidget):
#                 return widget
#         return None


class InterfaceWidget(QWidget):
    """
    Виджет настроек оформления интерфейса
    """

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

        # Левая колонка (5 кнопок)
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

        # Правая колонка (5 кнопок)
        btn_dark = QPushButton("Dark")
        btn_dark.clicked.connect(lambda: self.apply_style_file("dark.json"))
        right_col.addWidget(btn_dark)

        btn_legacy = QPushButton("Legacy")
        btn_legacy.clicked.connect(lambda: self.apply_style_file("legacy.json"))
        right_col.addWidget(btn_legacy)

        btn_white = QPushButton("White")
        btn_white.clicked.connect(lambda: self.apply_style_file("white.json"))
        right_col.addWidget(btn_white)

        btn_white_orange = QPushButton("Светло-оранжевый")
        btn_white_orange.clicked.connect(lambda: self.apply_style_file("white_orange.json"))
        right_col.addWidget(btn_white_orange)

        btn_purple = QPushButton("Светло-фиолетовый")
        btn_purple.clicked.connect(lambda: self.apply_style_file("white_purple.json"))
        right_col.addWidget(btn_purple)

        btn_white_blue = QPushButton("Светло-голубой")
        btn_white_blue.clicked.connect(lambda: self.apply_style_file("white_blue.json"))
        right_col.addWidget(btn_white_blue)

        btn_orange_purple = QPushButton("Закат")
        btn_orange_purple.clicked.connect(lambda: self.apply_style_file("sunset.json"))
        right_col.addWidget(btn_orange_purple)

        cols.addLayout(left_col)
        cols.addLayout(right_col)
        layout.addLayout(cols)

        # Выпадающий список для кастомных стилей
        self.custom_presets_combo = QComboBox()
        self.custom_presets_combo.addItem("Выберите пользовательский стиль...")
        self.load_custom_presets()  # Загружаем пользовательские пресеты
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
        self.current_voice = self.assistant.speaker
        self.current_name = self.assistant.assistant_name
        self.current_name2 = self.assistant.assist_name2
        self.current_name3 = self.assistant.assist_name3
        self.current_steam_path = self.assistant.steam_path
        self.current_volume = self.assistant.volume_assist
        # self.main_settings_window = parent
        self.init_ui()

    def hide_method(self):
        """Закрывает панель настроек через главный класс"""
        if hasattr(self.assistant, 'hide_widget'):
            self.assistant.hide_widget()
        else:
            debug_logger.error("Метод close_settings не найден в assistant")

    # def hide_method(self):
    #     if self.main_settings_window:
    #         self.main_settings_window.hide_with_animation()

    def init_ui(self):
        # # Создаем главный контейнер с прокруткой
        # scroll_area = QScrollArea()
        # scroll_area.setWidgetResizable(True)
        # scroll_area.setFrameShape(QFrame.NoFrame)

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
        select_steam_button.setStyleSheet("padding: 5px;")
        select_steam_button.clicked.connect(self.select_steam_folder)
        layout.addWidget(select_steam_button, alignment=Qt.AlignRight)

        layout.addStretch()

        # Кнопка применения
        apply_button = QPushButton("Применить", self)
        apply_button.clicked.connect(self.apply_settings)
        layout.addWidget(apply_button, alignment=Qt.AlignBottom)

        # # Устанавливаем контент в scroll area
        # scroll_area.setWidget(content_widget)
        #
        # # Настройки скролла
        # scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        # scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

    def update_volume(self, value):
        self.assistant.volume_assist = value / 100.0

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
        # self.main_settings_window = parent
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

        self.update_check = QCheckBox("Уведомлять о новой версии", self)
        self.update_check.setStyleSheet("background: transparent;")
        self.update_check.setChecked(self.assistant.show_upd_msg)
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
        self.assistant.show_upd_msg = self.update_check.isChecked()
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

    # def hide_method(self):
    #     if self.main_settings_window:
    #         self.main_settings_window.hide_with_animation()
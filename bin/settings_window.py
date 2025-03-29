import json
import os
from path_builder import get_path
from logging_config import logger
from PyQt5.QtCore import QSettings, pyqtSignal, Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QPushButton, QCheckBox, QLineEdit, QLabel, QSlider, QComboBox, \
    QVBoxLayout, QWidget, QDialog, QColorDialog, QFrame, QStackedWidget, QHBoxLayout

speakers = dict(Пласид='placide', Бестия='rogue', Джонни='johnny', СанСаныч='sanych',
                Санбой='sanboy', Тигрица='tigress', Стейтем='stathem')



class CustomInputDialog(QDialog):
    def __init__(self, title, label, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedSize(300, 100)

        # Поле для ввода текста
        self.input_field = QLineEdit(self)
        self.input_field.setPlaceholderText(label)

        # Кнопки "ОК" и "Отмена"
        self.ok_button = QPushButton('Сохранить', self)
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton('Закрыть', self)
        self.cancel_button.clicked.connect(self.reject)  # Закрываем диалог

        # Размещение элементов
        layout = QVBoxLayout()
        layout.addWidget(self.input_field)
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)
        self.setLayout(layout)

    def get_text(self):
        return self.input_field.text()


class MainSettingsWindow(QDialog):
    """
    Основное окно настроек
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.assistant = parent
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Настройки")
        self.setFixedSize(550, 600)

        # Основной layout
        main_layout = QHBoxLayout(self)

        # Левая колонка с кнопками
        left_column = QVBoxLayout()
        left_column.setAlignment(Qt.AlignTop)
        main_layout.addLayout(left_column, 1)

        # Разделитель
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(separator)

        # Правая колонка с содержимым
        self.right_column = QStackedWidget()
        main_layout.addWidget(self.right_column, 2)

        # Добавляем вкладки, передавая параметры
        self.add_tab("Общие", SettingsWidget(self.assistant))
        self.add_tab("Интерфейс", InterfaceWidget(self.assistant))

    def add_tab(self, button_name, content_widget):
        # Создаем кнопку
        button = QPushButton(button_name, self)

        # Подключаем кнопку к переключению на соответствующий виджет
        button.clicked.connect(lambda _, w=content_widget: self.right_column.setCurrentWidget(w))

        # Добавляем кнопку в левую колонку
        self.layout().itemAt(0).layout().addWidget(button)

        # Добавляем содержимое в правую колонку
        self.right_column.addWidget(content_widget)

    def get_settings_widget(self):
        """Возвращает виджет настроек из стека"""
        for i in range(self.right_column.count()):
            widget = self.right_column.widget(i)
            if isinstance(widget, SettingsWidget):
                return widget
        return None

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
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        # Контейнер для двух колонок
        cols = QHBoxLayout()
        left_col = QVBoxLayout()
        right_col = QVBoxLayout()

        # Левая колонка (5 кнопок)
        btn_dark = QPushButton("Оранжевый неон")
        btn_dark.clicked.connect(lambda: self.apply_style_file("orange_neon.json"))
        left_col.addWidget(btn_dark)

        btn_blue = QPushButton("Синий неон")
        btn_blue.clicked.connect(lambda: self.apply_style_file("blue_neon.json"))
        left_col.addWidget(btn_blue)

        btn_green = QPushButton("Зеленый неон")
        btn_green.clicked.connect(lambda: self.apply_style_file("green_neon.json"))
        left_col.addWidget(btn_green)

        btn_purple = QPushButton("Розовый неон")
        btn_purple.clicked.connect(lambda: self.apply_style_file("pink_neon.json"))
        left_col.addWidget(btn_purple)

        btn_red = QPushButton("Красный неон")
        btn_red.clicked.connect(lambda: self.apply_style_file("red_neon.json"))
        left_col.addWidget(btn_red)

        # Правая колонка (5 кнопок)
        btn_light = QPushButton("Dark")
        btn_light.clicked.connect(lambda: self.apply_style_file("dark.json"))
        right_col.addWidget(btn_light)

        btn_material = QPushButton("Legacy")
        btn_material.clicked.connect(lambda: self.apply_style_file("legacy.json"))
        right_col.addWidget(btn_material)

        btn_console = QPushButton("White")
        btn_console.clicked.connect(lambda: self.apply_style_file("white.json"))
        right_col.addWidget(btn_console)

        btn_monochrome = QPushButton("Светло-оранжевый")
        btn_monochrome.clicked.connect(lambda: self.apply_style_file("white_orange.json"))
        right_col.addWidget(btn_monochrome)

        btn_high_contrast = QPushButton("Светло-фиолетовый")
        btn_high_contrast.clicked.connect(lambda: self.apply_style_file("white_purple.json"))
        right_col.addWidget(btn_high_contrast)

        cols.addLayout(left_col)
        cols.addLayout(right_col)
        layout.addLayout(cols)

        # Выпадающий список для кастомных стилей
        self.custom_presets_combo = QComboBox()
        self.custom_presets_combo.addItem("Выберите пользовательский стиль...")
        self.load_custom_presets()  # Загружаем пользовательские пресеты
        self.custom_presets_combo.currentIndexChanged.connect(self.apply_custom_style)
        layout.addWidget(QLabel("Пользовательские стили:"))
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
            return

        try:
            with open(preset_path, 'r', encoding='utf-8') as json_file:
                styles = json.load(json_file)

                # Сохраняем стили в основной файл настроек
                with open(self.assistant.color_settings_path, 'w') as f:
                    json.dump(styles, f, indent=4)

                # Применяем стили
                self.assistant.styles = styles
                self.assistant.load_and_apply_styles()

                logger.info(f"Применён стиль из файла: {filename}")

        except json.JSONDecodeError:
            logger.error(f"Ошибка: файл пресета повреждён ({preset_path}).")
        except Exception as e:
            logger.error(f"Ошибка загрузки пресета: {e}")
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
            color_dialog.colorChanged.connect(self.assistant.load_and_apply_styles)
            color_dialog.exec_()
        except Exception as e:
            logger.error(f"Ошибка при открытии окна настроек цветов: {e}")
            self.assistant.show_message(f"Не удалось открыть настройки цветов: {e}", "Ошибка", "error")


class ColorSettingsWindow(QDialog):
    """
    Класс обрабатывающий окно изменения оформления интерфейса
    (изменение цветовой палитры, сохранение и выбор пресетов)
    """
    colorChanged = pyqtSignal()  # Определяем сигнал

    def __init__(self, assistant, parent=None):
        super().__init__(parent)
        self.assistant = assistant
        self.styles = self.assistant.styles  # Передаем текущие стили
        self.color_settings_path = self.assistant.color_settings_path
        self.base_presets = get_path('bin', 'color_presets')
        self.custom_presets = get_path('user_settings', 'presets')
        os.makedirs(self.custom_presets, exist_ok=True)
        self.init_ui()
        # Инициализация переменных для цветов
        self.bg_color = ""
        self.btn_color = ""
        self.text_color = ""
        self.text_edit_color = ""
        self.border_color = ""
        self.load_color_settings()  # Загружаем текущие цвета

    def init_ui(self):
        self.setWindowTitle('Редактор стилей')
        self.setFixedSize(300, 400)

        # Кнопки для выбора цветов
        self.bg_button = QPushButton('Фон')
        self.bg_button.clicked.connect(self.choose_background_color)

        self.btn_button = QPushButton('Цвет кнопок')
        self.btn_button.clicked.connect(self.choose_button_color)

        self.border_button = QPushButton('Обводка кнопок')
        self.border_button.clicked.connect(self.choose_border_color)

        self.text_button = QPushButton('Цвет текста')
        self.text_button.clicked.connect(self.choose_text_color)

        self.text_edit_button = QPushButton('Цвет текста в логах и сносках')
        self.text_edit_button.clicked.connect(self.choose_text_edit_color)

        # Кнопка для применения изменений
        self.apply_button = QPushButton('Применить')
        self.apply_button.clicked.connect(self.apply_changes)

        # Кнопка для сохранения пресета
        self.save_preset_button = QPushButton('Сохранить стиль')
        self.save_preset_button.clicked.connect(self.save_preset)

        # Выпадающий список для выбора существующих пресетов
        self.preset_combo_box = QComboBox()
        self.load_presets()  # Загружаем существующие пресеты
        self.preset_combo_box.setCurrentIndex(0)
        self.preset_combo_box.currentIndexChanged.connect(self.load_preset)

        # Размещение элементов
        layout = QVBoxLayout()
        layout.addWidget(self.bg_button)
        layout.addWidget(self.btn_button)
        layout.addWidget(self.border_button)
        layout.addWidget(self.text_button)
        layout.addWidget(self.text_edit_button)
        layout.addWidget(self.save_preset_button)
        layout.addWidget(QLabel('Стили:'))
        layout.addWidget(self.preset_combo_box)
        layout.addStretch()
        layout.addWidget(self.apply_button)

        self.setLayout(layout)

    def load_color_settings(self):
        """Загружает текущие цвета из файла настроек."""
        self.bg_color = self.styles.get("QWidget", {}).get("background-color", "#1d2028")
        self.btn_color = self.styles.get("QPushButton", {}).get("background-color", "#293f85")
        self.text_color = self.styles.get("QPushButton", {}).get("color", "#8eaee5")
        self.text_edit_color = self.styles.get("QTextEdit", {}).get("color", "#ffffff")
        # Разбираем строку border, чтобы извлечь цвет
        border_style = self.styles.get("QPushButton", {}).get("border", "1px solid #293f85")
        border_parts = border_style.split()
        self.border_color = border_parts[-1] if len(border_parts) > 2 else "#293f85"

    def choose_background_color(self):
        try:
            initial_color = QColor(self.bg_color) if hasattr(self, 'bg_color') else Qt.white
            color = QColorDialog.getColor(initial_color, self)
            if color.isValid():
                self.bg_color = color.name()
        except Exception as e:
            logger.error(e)

    def choose_button_color(self):
        try:
            initial_color = QColor(self.btn_color) if hasattr(self, 'btn_color') else Qt.white
            color = QColorDialog.getColor(initial_color, self)
            if color.isValid():
                self.btn_color = color.name()
        except Exception as e:
            logger.error(e)

    def choose_border_color(self):
        try:
            initial_color = QColor(self.border_color) if hasattr(self, 'border_color') else Qt.white
            color = QColorDialog.getColor(initial_color, self)
            if color.isValid():
                self.border_color = color.name()
        except Exception as e:
            logger.error(e)

    def choose_text_color(self):
        try:
            initial_color = QColor(self.text_color) if hasattr(self, 'text_color') else Qt.white
            color = QColorDialog.getColor(initial_color, self)
            if color.isValid():
                self.text_color = color.name()
        except Exception as e:
            logger.error(e)

    def choose_text_edit_color(self):
        try:
            initial_color = QColor(self.text_edit_color) if hasattr(self, 'text_edit_color') else Qt.white
            color = QColorDialog.getColor(initial_color, self)
            if color.isValid():
                self.text_edit_color = color.name()
        except Exception as e:
            logger.error(e)

    def show_error_message(self, text, parent_dialog=None):
        """Показывает сообщение об ошибке, не закрывая родительский диалог."""
        msg = QMessageBox(parent_dialog if parent_dialog else self)
        msg.setIcon(QMessageBox.Warning)
        msg.setText(text)
        msg.setWindowTitle("Ошибка")
        ok_btn = msg.addButton("OK", QMessageBox.AcceptRole)
        ok_btn.setStyleSheet("padding: 1px 10px;")
        msg.exec_()

    def apply_changes(self):
        try:
            new_styles = {
                "QWidget": {
                    "background-color": self.bg_color,
                    "color": self.text_color,
                    "font-size": "13px"
                },
                "QPushButton": {
                    "background-color": self.btn_color,
                    "color": self.text_color,
                    "height": "30px",
                    "border": f"1px solid {self.border_color}",
                    "border-radius": "3px",
                    "font-size": "13px"
                },
                "QPushButton:hover": {
                    "background-color": self.darken_color(self.btn_color, 10),
                    "color": self.text_color,
                    "font-size": "13px"
                },
                "QPushButton:pressed": {
                    "background-color": self.darken_color(self.btn_color, 30),
                    "padding-left": "3px",
                    "padding-top": "3px",
                },
                "QTextEdit": {
                    "background-color": self.bg_color,
                    "color": self.text_edit_color,
                    "border": "1px solid",
                    "border-radius": "4px",
                    "font-size": "12px"
                },
                "label_version": {
                    "color": self.text_edit_color,
                    "font-size": "10px"
                },
                "label_message": {
                    "color": self.text_color,
                    "font-size": "13px"
                },
                "update_label": {
                    "color": self.text_edit_color,
                    "font-size": "12px"
                }
            }
            self.save_color_settings(new_styles)
            self.colorChanged.emit()
        except Exception as e:
            logger.info(f"Ошибка при применении изменений: {e}")
            self.assistant.show_message(f"Не удалось применить изменения: {e}", "Ошибка", "error")

    def save_color_settings(self, new_styles):
        """Сохраняет новые стили в color_settings.json."""
        with open(self.color_settings_path, 'w') as json_file:
            json.dump(new_styles, json_file, indent=4)

    def save_preset(self):
        """Сохраняет текущие стили как новый пресет с валидацией имени."""
        while True:  # Цикл для повторного ввода при ошибках
            dialog = CustomInputDialog('Сохранить пресет', 'Введите имя пресета:', self)
            result = dialog.exec_()

            if result != QDialog.Accepted:  # Если отмена/закрытие
                logger.info("Сохранение пресета отменено")
                return

            preset_name = dialog.get_text().strip()

            # Валидация имени
            if not preset_name:
                self.assistant.show_message("Имя пресета не может быть пустым!", "Предупреждение", "warning")
                continue  # Повторяем ввод

            # Проверка существующих пресетов
            conflict_paths = [
                os.path.join(self.base_presets, f"{preset_name}.json"),
                os.path.join(self.custom_presets, f"{preset_name}.json")
            ]

            if any(os.path.exists(path) for path in conflict_paths):
                self.assistant.show_message(f"Пресет '{preset_name}' уже существует!\n"
                                            "Пожалуйста, выберите другое имя.", "Предупреждение", "warning")
                # self.show_error_message(
                #     f"Пресет '{preset_name}' уже существует!\n"
                #     "Пожалуйста, выберите другое имя.",
                #     dialog
                # )
                continue

            try:
                os.makedirs(self.custom_presets, exist_ok=True)
                preset_path = conflict_paths[1]  # custom_presets путь

                with open(preset_path, 'w', encoding='utf-8') as f:
                    json.dump({
                        "QWidget": {
                            "background-color": self.bg_color,
                            "color": self.text_color,
                            "font-size": "13px"
                        },
                        "QPushButton": {
                            "background-color": self.btn_color,
                            "color": self.text_color,
                            "height": "30px",
                            "border": f"1px solid {self.border_color}",
                            "border-radius": "3px",
                            "font-size": "13px"
                        },
                        "QPushButton:hover": {
                            "background-color": self.darken_color(self.btn_color, 10),
                            "color": self.text_color,
                            "font-size": "13px"
                        },
                        "QPushButton:pressed": {
                            "background-color": self.darken_color(self.btn_color, 30),
                            "padding-left": "3px",
                            "padding-top": "3px",
                        },
                        "QTextEdit": {
                            "background-color": self.bg_color,
                            "color": self.text_edit_color,
                            "border": "1px solid",
                            "border-radius": "4px",
                            "font-size": "12px"
                        },
                        "label_version": {
                            "color": self.text_edit_color,
                            "font-size": "10px"
                        },
                        "label_message": {
                            "color": self.text_color,
                            "font-size": "13px"
                        },
                        "update_label": {
                            "color": self.text_edit_color,
                            "font-size": "12px"
                        }
                    }, f, indent=4, ensure_ascii=False)

                self.load_presets()
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle('Успех')
                msg_box.setText(f"Пресет сохранен!")
                ok_button = msg_box.addButton("ОК", QMessageBox.AcceptRole)
                ok_button.setStyleSheet("padding: 1px 10px;")
                msg_box.exec_()
                break  # Выход из цикла после успешного сохранения

            except Exception as e:
                self.show_error_message(
                    f"Ошибка сохранения:\n{str(e)}",
                    dialog
                )

    def load_presets(self):
        """Загружает существующие пресеты в выпадающий список."""
        self.preset_combo_box.clear()
        self.preset_combo_box.addItem("Выбрать пресет")

        # Проверяем, существует ли директория, если нет - создаем
        if not os.path.exists(self.base_presets):
            os.makedirs(self.base_presets)

        # Загружаем все файлы .json из директории пресетов
        for filename in os.listdir(self.base_presets):
            if filename.endswith('.json'):
                self.preset_combo_box.addItem(filename[:-5])  # Добавляем имя файла без .json

        for filename in os.listdir(self.custom_presets):
            if filename.endswith('.json'):
                self.preset_combo_box.addItem(filename[:-5])  # Добавляем имя файла без .json

    def load_preset(self):
        """Загружает выбранный пресет из файла, проверяя обе директории."""
        selected_preset = self.preset_combo_box.currentText()
        if not selected_preset or selected_preset == "Выбрать пресет":
            return  # Пресет не выбран

        # Формируем пути к файлам в обеих папках
        base_preset_path = os.path.join(self.base_presets, f"{selected_preset}.json")
        custom_preset_path = os.path.join(self.custom_presets, f"{selected_preset}.json")

        # Проверяем, в какой папке есть файл (приоритет у custom_presets)
        preset_path = None
        if os.path.exists(custom_preset_path):
            preset_path = custom_preset_path
        elif os.path.exists(base_preset_path):
            preset_path = base_preset_path
        else:
            logger.error(f"Пресет '{selected_preset}' не найден ни в одной из папок.")
            self.assistant.show_message(f"Пресет '{selected_preset}' не найден ни в одной из папок.", "Ошибка", "error")
            return

        try:
            with open(preset_path, 'r', encoding='utf-8') as json_file:
                styles = json.load(json_file)

                # Загружаем цвета
                self.bg_color = styles.get("QWidget", {}).get("background-color", "#1d2028")
                self.btn_color = styles.get("QPushButton", {}).get("background-color", "#293f85")
                self.text_color = styles.get("QWidget", {}).get("color", "#8eaee5")
                self.text_edit_color = styles.get("QTextEdit", {}).get("color", "#ffffff")
                self.border_color = styles.get("QPushButton", {}).get("border", "1px solid #293f85").split()[-1]

                logger.info(f"Пресет загружен: {preset_path}")

        except json.JSONDecodeError:
            logger.error(f"Ошибка: файл пресета повреждён ({preset_path}).")
        except Exception as e:
            logger.error(f"Ошибка загрузки пресета: {e}")

    def darken_color(self, color_str, amount):
        """Уменьшает яркость цвета на заданное количество (в формате hex)."""
        color = QColor(color_str)
        color.setRed(max(0, color.red() - amount))
        color.setGreen(max(0, color.green() - amount))
        color.setBlue(max(0, color.blue() - amount))
        return color.name()

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
        self.settings = QSettings("Настройки", "Общие")
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Поле для ввода имени ассистента
        name_label = QLabel("Основное имя ассистента:", self)
        layout.addWidget(name_label, alignment=Qt.AlignLeft)

        self.name_input = QLineEdit(self)
        self.name_input.setText(self.assistant.assistant_name)
        layout.addWidget(self.name_input)

        # Поле для ввода имени №2
        name2_label = QLabel("Дополнительно:", self)
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
        layout.addWidget(voice_label, alignment=Qt.AlignLeft)

        self.voice_combo = QComboBox(self)
        self.voice_combo.addItems(list(speakers.keys()))
        current_key = next(key for key, value in speakers.items() if value == self.assistant.speaker)
        self.voice_combo.setCurrentText(current_key)
        self.voice_combo.currentIndexChanged.connect(self.on_voice_change)
        layout.addWidget(self.voice_combo)

        # Громкость
        volume_label = QLabel("Громкость ассистента", self)
        layout.addWidget(volume_label, alignment=Qt.AlignLeft)

        self.volume_slider = QSlider(Qt.Horizontal, self)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(int(self.assistant.volume_assist * 100))
        self.volume_slider.valueChanged.connect(self.update_volume)
        layout.addWidget(self.volume_slider)

        # Путь к Steam
        steam_label = QLabel("Укажите полный путь к файлу steam.exe", self)
        layout.addWidget(steam_label, alignment=Qt.AlignLeft)

        self.steam_path_input = QLineEdit(self)
        self.steam_path_input.setText(self.assistant.steam_path)
        layout.addWidget(self.steam_path_input)

        select_steam_button = QPushButton("Выбрать файл", self)
        select_steam_button.clicked.connect(self.select_steam_file)
        layout.addWidget(select_steam_button)

        # Чекбоксы
        self.censor_check = QCheckBox("Реагировать на мат", self)
        self.censor_check.setChecked(self.assistant.is_censored)
        self.censor_check.stateChanged.connect(self.toggle_censor)
        layout.addWidget(self.censor_check)

        self.update_check = QCheckBox("Уведомлять о новой версии", self)
        self.update_check.setChecked(self.assistant.show_upd_msg)
        self.update_check.stateChanged.connect(self.toggle_update)
        layout.addWidget(self.update_check)

        # Чекбокс для сворачивания в трей
        self.minimize_check = QCheckBox("Сворачивать в трей при запуске", self)
        self.minimize_check.setChecked(self.assistant.is_min_tray)
        self.minimize_check.stateChanged.connect(self.toggle_minimize)
        layout.addWidget(self.minimize_check)

        layout.addStretch()

        # Кнопка применения
        apply_button = QPushButton("Применить", self)
        apply_button.clicked.connect(self.apply_settings)
        layout.addWidget(apply_button, alignment=Qt.AlignBottom)

    def update_volume(self, value):
        self.assistant.volume_assist = value / 100.0

    def toggle_censor(self):
        self.assistant.is_censored = self.censor_check.isChecked()

    def toggle_update(self):
        self.assistant.show_upd_msg = self.update_check.isChecked()

    def toggle_minimize(self):
        """Обработка чекбокса 'Сворачивать в трей'"""
        self.assistant.is_min_tray = self.minimize_check.isChecked()

    def select_steam_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите steam.exe", "", "Executable Files (*.exe);;All Files (*)")
        if file_path:
            self.steam_path_input.setText(file_path)

    def on_voice_change(self, index):
        new_voice_key = self.voice_combo.currentText()
        if new_voice_key in speakers:
            self.voice_changed.emit(speakers[new_voice_key])

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
        self.assistant.show_message(f"Настройки применены!")

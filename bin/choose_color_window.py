import json
import math
import os
import re


from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QColor, QPainter, QLinearGradient
from PyQt5.QtWidgets import QLabel, QVBoxLayout, QPushButton, QSpinBox, QSlider, QDialog, QWidget, QTabWidget, \
    QColorDialog, QCheckBox, QHBoxLayout, QComboBox, QApplication, QLineEdit

from logging_config import debug_logger
from path_builder import get_path


class ColorSettingsWindow(QDialog):
    """Окно изменения оформления интерфейса с поддержкой градиентов"""

    colorChanged = pyqtSignal()  # Сигнал изменения цвета

    def __init__(self, assistant, parent=None):
        super().__init__(parent)
        self.assistant = assistant
        self.styles = self.assistant.styles
        self.color_settings_path = self.assistant.color_path
        self.base_presets = get_path("bin", 'color_presets')
        self.custom_presets = get_path('user_settings', 'presets')
        os.makedirs(self.custom_presets, exist_ok=True)

        # Настройка окна без рамки
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setFixedSize(500, 600)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # Инициализация переменных для цветов
        self.bg_color = ""
        self.btn_color = ""
        self.text_color = ""
        self.text_edit_color = ""
        self.border_color = ""

        # Настройки градиентов
        self.gradient_settings = {
            'background': {
                'enabled': False,
                'solid_color': "#000000",
                'color1': "",
                'color2': "",
                'angle': 0,
                'widgets': {}  # Будет заполнено в init_ui
            },
            'buttons': {
                'enabled': False,
                'color1': "",
                'color2': "",
                'angle': 0,
                'widgets': {}
            },
            'borders': {
                'enabled': False,
                'color1': "",
                'color2': "",
                'angle': 0,
                'widgets': {}
            }
        }

        self.init_ui()
        self.load_color_settings()

    def init_ui(self):
        # Основной контейнер
        self.container = QWidget(self)
        self.container.setObjectName("MessageContainer")
        self.container.setGeometry(0, 0, self.width(), self.height())

        # Кастомный заголовок
        self.title_bar = QWidget(self.container)
        self.title_bar.setObjectName("TitleBar")
        self.title_bar.setGeometry(1, 1, self.width() - 2, 35)
        self.title_layout = QHBoxLayout(self.title_bar)
        self.title_layout.setContentsMargins(10, 5, 10, 5)
        self.title_layout.setSpacing(5)

        self.title_label = QLabel("Редактор стилей", self.title_bar)
        self.title_layout.addWidget(self.title_label)

        self.close_btn = QPushButton("✕", self.title_bar)
        self.close_btn.setFixedSize(25, 25)
        self.close_btn.setObjectName("CloseButton")
        self.close_btn.clicked.connect(self.close)
        self.title_layout.addWidget(self.close_btn)

        # Основной контент
        self.content_widget = QWidget(self.container)
        self.content_widget.setGeometry(1, 36, self.width() - 2, self.height() - 37)
        self.content_widget.setObjectName("ContentWidget")

        # Создаем вкладки для разных элементов
        self.tab_widget = QTabWidget(self.content_widget)
        self.tab_widget.setStyleSheet("""
                QTabWidget::pane {
                    border: 1px solid palette(shadow);
                    background: palette(base);
                }
                QTabBar::tab {
                    background: palette(button);
                    color: palette(text);
                    padding: 5px;
                    border: 1px solid palette(shadow);
                    border-bottom: none;
                    border-top-left-radius: 4px;
                    border-top-right-radius: 4px;
                }
                QTabBar::tab:selected {
                    background: palette(base);
                    border-bottom: 1px solid palette(base);
                }
            """)

        # Вкладка для фона
        self.bg_tab = QWidget()
        self.init_gradient_tab(self.bg_tab, 'background', 'Фон')

        self.text_tab = QWidget()
        # Добавляем раздел для текста
        self.add_text_color_section(self.text_tab)

        # Вкладка для кнопок
        self.btn_tab = QWidget()
        self.init_gradient_tab(self.btn_tab, 'buttons', 'Кнопки')

        # Вкладка для обводок
        self.border_tab = QWidget()
        self.init_gradient_tab(self.border_tab, 'borders', 'Обводки')

        self.tab_widget.addTab(self.bg_tab, "Фон")
        self.tab_widget.addTab(self.text_tab, "Текст")
        self.tab_widget.addTab(self.btn_tab, "Кнопки")
        self.tab_widget.addTab(self.border_tab, "Обводки")

        # Кнопка для сохранения пресета
        self.save_preset_button = QPushButton('Сохранить стиль')
        self.save_preset_button.clicked.connect(self.save_preset)

        # Выпадающий список для пресетов
        self.preset_combo_box = QComboBox()
        self.load_presets()
        self.preset_combo_box.setCurrentIndex(0)
        self.preset_combo_box.currentIndexChanged.connect(self.load_preset)

        self.warning_label = QLabel("Внимание!\nПри выборе градиента для 'Обводки', "
                                    "первый цвет будет браться за основу окрашивания значков и svg-элементов")
        self.warning_label.setWordWrap(True)

        # Кнопка для применения изменений
        self.apply_button = QPushButton('Применить')
        self.apply_button.clicked.connect(lambda: self.apply_changes(preview=False))

        # Размещение элементов
        layout = QVBoxLayout(self.content_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        layout.addWidget(self.tab_widget)
        layout.addWidget(self.save_preset_button)
        layout.addWidget(QLabel('Стили:'))
        layout.addWidget(self.preset_combo_box)
        layout.addWidget(self.warning_label)
        layout.addStretch()
        layout.addWidget(self.apply_button)

    def init_gradient_tab(self, tab, element_type, title):
        """Инициализирует вкладку для настройки градиента конкретного элемента"""
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(8)

        # Чекбокс для включения градиента
        checkbox = QCheckBox(f'Использовать градиент для {title.lower()}')
        checkbox.stateChanged.connect(lambda state: self.toggle_gradient(element_type, state))
        layout.addWidget(checkbox)

        # Основной цвет (показывается всегда)
        solid_color_btn = QPushButton('Выбрать цвет')
        solid_color_btn.clicked.connect(lambda: self.choose_solid_color(element_type))
        layout.addWidget(solid_color_btn)

        # Контейнер для элементов градиента (скрывается при отключении)
        gradient_group = QWidget()
        gradient_layout = QVBoxLayout(gradient_group)
        gradient_layout.setContentsMargins(0, 0, 0, 0)

        # Кнопки выбора цветов
        color_layout = QHBoxLayout()
        color1_btn = QPushButton('Цвет 1')
        color1_btn.clicked.connect(lambda: self.choose_gradient_color(element_type, 1))
        color_layout.addWidget(color1_btn)
        color2_btn = QPushButton('Цвет 2')
        color2_btn.clicked.connect(lambda: self.choose_gradient_color(element_type, 2))
        color_layout.addWidget(color2_btn)
        gradient_layout.addLayout(color_layout)

        # Управление углом
        angle_label = QLabel(f'Угол градиента (0-360°):')
        gradient_layout.addWidget(angle_label)
        angle_slider = QSlider(Qt.Horizontal)
        angle_slider.setRange(0, 360)
        angle_slider.setTickInterval(45)
        angle_slider.setTickPosition(QSlider.TicksBelow)
        angle_slider.valueChanged.connect(lambda angle: self.update_gradient_angle(element_type, angle))
        gradient_layout.addWidget(angle_slider)
        angle_spin = QSpinBox()
        angle_spin.setRange(0, 360)
        angle_spin.setSuffix('°')
        angle_spin.valueChanged.connect(lambda angle: self.update_gradient_angle(element_type, angle))
        gradient_layout.addWidget(angle_spin)

        # Связываем слайдер и спинбокс
        angle_slider.valueChanged.connect(angle_spin.setValue)
        angle_spin.valueChanged.connect(angle_slider.setValue)

        layout.addWidget(gradient_group)  # Добавляем группу в основной layout

        # Превью градиента
        preview = GradientPreview()
        layout.addWidget(preview)
        layout.addStretch()

        # Сохраняем ссылки на элементы для обновления
        self.gradient_settings[element_type]['widgets'] = {
            'checkbox': checkbox,
            'solid_color_btn': solid_color_btn,
            'gradient_group': gradient_group,
            'color1_btn': color1_btn,
            'color2_btn': color2_btn,
            'slider': angle_slider,
            'spinbox': angle_spin,
            'preview': preview
        }

        # Инициализируем состояние
        self.toggle_gradient(element_type, checkbox.isChecked())

    def add_text_color_section(self, tab):
        """Добавляет секцию настроек текста"""
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(8)

        # Заголовок
        text_label = QLabel("Цвет текста")
        text_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(text_label)

        # Основной текст
        self.text_color_btn = QPushButton('Цвет текста (общий, на кнопках)')
        self.text_color_btn.clicked.connect(self.choose_text_color)
        layout.addWidget(self.text_color_btn)

        # Текст в QTextEdit
        self.text_edit_color_btn = QPushButton('Цвет текста в логах')
        self.text_edit_color_btn.clicked.connect(self.choose_text_edit_color)
        layout.addWidget(self.text_edit_color_btn)

        # Превью текста
        self.text_preview = QLabel("Пример текста")
        self.text_preview.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.text_preview)

        # Превью текста
        self.text_edit_preview = QLabel("Пример текста в логах")
        self.text_edit_preview.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.text_edit_preview)

    def choose_text_color(self):
        color = QColorDialog.getColor(QColor(self.text_color), self, "Выберите цвет текста")
        if color.isValid():
            self.text_color = color.name()
            self.update_text_preview()

    def choose_text_edit_color(self):
        color = QColorDialog.getColor(QColor(self.text_edit_color), self, "Выберите цвет текста в логах")
        if color.isValid():
            self.text_edit_color = color.name()
            self.update_text_preview()

    def choose_solid_color(self, element_type):
        """Выбор сплошного цвета (когда градиент выключен)"""
        current_color = self.gradient_settings[element_type].get('solid_color', "#000000")
        color = QColorDialog.getColor(QColor(current_color), self, "Выберите цвет")
        if color.isValid():
            self.gradient_settings[element_type]['solid_color'] = color.name()
            if element_type == 'background':
                self.bg_color = color.name()
            elif element_type == 'buttons':
                self.btn_color = color.name()
            elif element_type == 'borders':
                self.border_color = color.name()
            self.update_gradient_preview(element_type)
            self.apply_changes(preview=True)

    def update_text_preview(self):
        """Обновляет превью текста"""
        self.text_preview.setStyleSheet(f"""
            color: {self.text_color};
            background-color: {'#FFFFFF' if QColor(self.text_color).lightness() < 128 else '#000000'};
            padding: 5px;
        """)
        self.text_edit_preview.setStyleSheet(f"""
            color: {self.text_edit_color};
            background-color: {'#FFFFFF' if QColor(self.text_color).lightness() < 128 else '#000000'};
            padding: 5px;
        """)

    def toggle_gradient(self, element_type, state):
        """Включает/выключает градиент для конкретного элемента"""
        enabled = state == Qt.Checked
        self.gradient_settings[element_type]['enabled'] = enabled

        widgets = self.gradient_settings[element_type]['widgets']
        # --- ЭТИ СТРОКИ УПРАВЛЯЮТ ДОСТУПНОСТЬЮ ---
        widgets['color1_btn'].setEnabled(enabled)
        widgets['color2_btn'].setEnabled(enabled)
        widgets['slider'].setEnabled(enabled)
        widgets['spinbox'].setEnabled(enabled)
        # ------------------------------------------

        if enabled and self.gradient_settings[element_type]['color1'] and self.gradient_settings[element_type][
            'color2']:
            self.update_gradient_preview(element_type)

        self.apply_changes(preview=True)

    def choose_gradient_color(self, element_type, color_num):
        """Выбор цвета градиента для конкретного элемента"""
        current_color = self.gradient_settings[element_type][f'color{color_num}']
        initial_color = QColor(current_color) if current_color else QColor("#000000")

        color = QColorDialog.getColor(initial_color, self, f"Выберите цвет {color_num} для градиента")
        if color.isValid():
            self.gradient_settings[element_type][f'color{color_num}'] = color.name()
            self.update_gradient_preview(element_type)
            self.apply_changes(preview=True)

    def update_gradient_angle(self, element_type, angle):
        """Обновляет угол градиента для конкретного элемента"""
        self.gradient_settings[element_type]['angle'] = angle
        self.update_gradient_preview(element_type)
        self.apply_changes(preview=True)

    def update_gradient_preview(self, element_type):
        """Обновляет превью в зависимости от режима"""
        settings = self.gradient_settings[element_type]
        preview = settings['widgets']['preview']

        if settings['enabled']:
            # Режим градиента
            if settings.get('color1') and settings.get('color2'):
                preview.set_gradient(settings['color1'], settings['color2'], settings.get('angle', 0))
        else:
            # Режим сплошного цвета
            color = settings.get('solid_color', "#000000")
            preview.set_gradient(color, color, 0)  # Одинаковый цвет для обоих стопов

    def load_color_settings(self):
        """Загружает текущие цвета из файла настроек."""
        # Основные цвета
        self.text_color = self.styles.get("QPushButton", {}).get("color", "#8eaee5")
        self.text_edit_color = self.styles.get("QTextEdit", {}).get("color", "#ffffff")

        # Загружаем настройки для каждого элемента
        self.load_element_settings(
            'background',
            self.styles.get("QWidget", {}).get("background-color", "#1d2028")
        )
        self.load_element_settings(
            'buttons',
            self.styles.get("QPushButton", {}).get("background-color", "#293f85")
        )

        border_value = self.styles.get("QPushButton", {}).get("border", "1px solid #293f85")
        self.load_element_settings('borders', border_value)

        # Синхронизируем устаревшие переменные с текущими значениями
        self.bg_color = self.gradient_settings['background']['solid_color']
        self.btn_color = self.gradient_settings['buttons']['solid_color']
        # Для border_color нужно извлечь часть из полной CSS строки, как это делается в load_element_settings
        border_full_value = self.styles.get("QPushButton", {}).get("border", "1px solid #293f85")
        if border_full_value.startswith("1px solid "):
            self.border_color = border_full_value[len("1px solid "):]
        else:
            # Если формат неожиданный, попробуем взять из gradient_settings
            self.border_color = self.gradient_settings['borders']['solid_color']

    def load_element_settings(self, element_type, css_value):
        """Загружает настройки элемента (градиент или сплошной цвет)"""
        settings = self.gradient_settings[element_type]
        widgets = settings.get('widgets', {})

        # Сброс настроек
        settings.update({
            'enabled': False,
            'solid_color': "#000000",
            'color1': "#000000",
            'color2': "#000000",
            'angle': 0
        })

        # Для border нужно сначала извлечь цвет/градиент из строки
        if element_type == 'borders':
            # Извлекаем цвет или градиент из "1px solid ..."
            parts = css_value.split()
            if len(parts) >= 3:
                color_part = ' '.join(parts[2:])  # Берем всё после "1px solid"
                # Убираем возможные скобки в конце
                color_part = color_part.rstrip(');,')
            else:
                color_part = "#000000"
        else:
            color_part = css_value

        if color_part.startswith("qlineargradient"):
            # Режим градиента
            settings['enabled'] = True

            try:
                # Парсим координаты
                coord_pattern = r"([xy][12]):([\d.]+)"
                coords = dict(re.findall(coord_pattern, color_part))

                if len(coords) == 4:
                    x1, y1, x2, y2 = map(float, [coords['x1'], coords['y1'], coords['x2'], coords['y2']])
                    dx, dy = x2 - x1, y2 - y1
                    settings['angle'] = int(math.degrees(math.atan2(dy, dx)) % 360)

                # Парсим цвета
                color_pattern = r"stop:\d+\s+(#[0-9a-fA-F]{6}|#[0-9a-fA-F]{3})"
                colors = re.findall(color_pattern, color_part)

                if len(colors) >= 2:
                    settings['color1'], settings['color2'] = colors[0], colors[1]

            except Exception as e:
                debug_logger.error(f"Ошибка парсинга градиента для {element_type}: {e}")
                settings['enabled'] = False
        else:
            # Режим сплошного цвета
            settings['solid_color'] = color_part if color_part.startswith('#') else "#000000"
            settings['enabled'] = False
            if element_type == 'background':
                self.bg_color = settings['solid_color']
            elif element_type == 'buttons':
                self.btn_color = settings['solid_color']
            elif element_type == 'borders':
                self.border_color = settings['solid_color']

        # Обновляем UI если виджеты уже созданы
        if widgets:
            widgets['checkbox'].setChecked(settings['enabled'])
            # --- ЯВНО ВЫЗЫВАЕМ toggle_gradient ПОСЛЕ setChecked ---
            # Это необходимо, чтобы обновить видимость gradient_group и доступность других элементов
            # в соответствии с загруженным значением settings['enabled']
            self.toggle_gradient(element_type, Qt.Checked if settings['enabled'] else Qt.Unchecked)
            # ----------------------------------------------------
            # Следующие строки могут быть избыточны, так как toggle_gradient уже делает это,
            # но оставим их для ясности, если вы хотите разделить логику.
            # if 'gradient_group' in widgets:
            #     widgets['gradient_group'].setVisible(settings['enabled']) # Уже сделано в toggle_gradient
            if 'solid_color_btn' in widgets:
                widgets['solid_color_btn'].setText('Выбрать градиент' if settings['enabled'] else 'Выбрать цвет')

            if settings['enabled']:
                widgets['slider'].setValue(settings['angle'])
                widgets['spinbox'].setValue(settings['angle'])

            self.update_gradient_preview(element_type)

        QApplication.processEvents() # Обработать все события в очереди
        self.container.repaint()
        self.update_text_preview()  # для обновления цвета текста на превью во вкладке "Текст"
        self.apply_changes(preview=True)

    def apply_changes(self, preview=False):
        try:
            new_styles = {
                "QWidget": {
                    "background-color": self.get_gradient_css('background') if self.gradient_settings['background'][
                        'enabled'] else self.bg_color,
                    "color": self.text_color,
                    "font-size": "13px"
                },
                "QPushButton": {
                    "background-color": self.get_gradient_css('buttons') if self.gradient_settings['buttons'][
                        'enabled'] else self.btn_color,
                    "color": self.text_color,
                    "height": "30px",
                    "border": f"1px solid {self.get_gradient_css('borders')}" if self.gradient_settings['borders'][
                        'enabled'] else f"1px solid {self.border_color}",
                    "border-radius": "3px",
                    "font-size": "13px"
                },
                "QPushButton:hover": {
                    "background-color": self.get_hover_gradient_css('buttons'),
                    "color": self.text_color,
                    "font-size": "13px"
                },
                "QPushButton:pressed": {
                    "background-color": self.get_pressed_gradient_css('buttons', 30),
                    "padding-left": "3px",
                    "padding-top": "3px",
                },
                "QTextEdit": {
                    "background": "transparent",
                    "color": self.text_edit_color,
                    "border": "none",
                    "font-size": "15px"
                },
                "label_version": {
                    "background": "transparent",
                    "color": self.text_edit_color,
                    "font-size": "10px"
                },
                "label_message": {
                    "color": self.text_color,
                    "font-size": "13px"
                },
                "update_label": {
                    "background": "transparent",
                    "color": self.text_edit_color,
                    "font-size": "12px"
                },
                "TitleBar": {
                    "border-bottom": f"1px solid {self.get_gradient_css('borders')}" if
                    self.gradient_settings['borders']['enabled'] else f"1px solid {self.border_color}"
                },
                "TrayButton": {
                    "background-color": self.get_gradient_css('buttons') if self.gradient_settings['buttons'][
                        'enabled'] else self.btn_color,
                    "color": self.text_color,
                    "height": "30px",
                    "border": f"1px solid {self.get_gradient_css('borders')}" if self.gradient_settings['borders'][
                        'enabled'] else f"1px solid {self.border_color}",
                    "border-radius": "3px",
                    "font-size": "13px"
                },
                "TrayButton:hover": {
                    "color": "#ffffff",
                    "background-color": "#0790EC",
                    "border": "1px solid #0790EC"
                },
                "CloseButton": {
                    "background-color": self.get_gradient_css('buttons') if self.gradient_settings['buttons'][
                        'enabled'] else self.btn_color,
                    "color": self.text_color,
                    "height": "30px",
                    "border": f"1px solid {self.get_gradient_css('borders')}" if self.gradient_settings['borders'][
                        'enabled'] else f"1px solid {self.border_color}",
                    "border-radius": "3px",
                    "font-size": "13px"
                },
                "CloseButton:hover": {
                    "color": "#ffffff",
                    "background-color": "#E04F4F",
                    "border": "1px solid #E04F4F"
                },
                "MessageContainer": {
                    "border": f"1px solid {self.get_gradient_css('borders')}" if self.gradient_settings['borders'][
                        'enabled'] else f"1px solid {self.border_color}",
                    "border-radius": "25px"
                }
            }

            if not preview:
                self.save_color_settings(new_styles)
                self.colorChanged.emit()
                self.assistant.check_start_win()
            else:
                # Применяем стили только для предпросмотра
                self.container.setStyleSheet(self.generate_stylesheet(new_styles))

        except Exception as e:
            self.assistant.show_notification_message(f"Ошибка при применении изменений в превью-окне: {e}")
            debug_logger.error(f"Ошибка при применении изменений в превью-окне: {e}")

    def get_gradient_css(self, element_type):
        """Генерирует CSS для градиента конкретного элемента"""
        settings = self.gradient_settings[element_type]
        if not settings['color1'] or not settings['color2']:
            return ""

        rad = math.radians(settings['angle'])
        x1 = 0.5 - 0.5 * math.cos(rad)
        y1 = 0.5 - 0.5 * math.sin(rad)
        x2 = 0.5 + 0.5 * math.cos(rad)
        y2 = 0.5 + 0.5 * math.sin(rad)

        return (
            f"qlineargradient("
            f"x1:{x1:.2f}, y1:{y1:.2f}, "
            f"x2:{x2:.2f}, y2:{y2:.2f}, "
            f"stop:0 {settings['color1']}, "
            f"stop:1 {settings['color2']})"
        )

    def generate_stylesheet(self, styles):
        """Генерирует строку CSS из словаря стилей"""
        stylesheet = ""
        for selector, properties in styles.items():
            stylesheet += f"{selector} {{\n"
            for prop, value in properties.items():
                stylesheet += f"    {prop}: {value};\n"
            stylesheet += "}\n"
        return stylesheet

    def save_color_settings(self, new_styles):
        """Сохраняет новые стили в color_settings.json."""
        with open(self.color_settings_path, 'w') as json_file:
            json.dump(new_styles, json_file, indent=4)

    def get_hover_gradient_css(self, element_type):
        """
        Генерирует CSS для градиента в состоянии :hover.
        Меняет местами color1 и color2.
        Если градиент отключен, возвращает сплошной цвет.
        """
        settings = self.gradient_settings[element_type]
        if not settings['enabled']:
            # Если градиент выключен, используем сплошной цвет и затемняем его
            solid_color = settings.get('solid_color', "#000000")
            # Используем существующий метод для затемнения
            return self._darken_single_color(solid_color, 10)

        color1 = settings.get('color1', "#000000")
        color2 = settings.get('color2', "#ffffff")
        angle = settings.get('angle', 0)

        # Меняем местами цвета
        return self._generate_qlineargradient(color2, color1, angle)

    def get_pressed_gradient_css(self, element_type, darken_amount=30):
        """
        Генерирует CSS для градиента в состоянии :pressed.
        Затемняет оба цвета на заданное количество.
        Если градиент отключен, затемняет сплошной цвет.
        """
        settings = self.gradient_settings[element_type]
        if not settings['enabled']:
            # Если градиент выключен, используем сплошной цвет и затемняем его
            solid_color = settings.get('solid_color', "#000000")
            return self._darken_single_color(solid_color, darken_amount)

        color1 = settings.get('color1', "#000000")
        color2 = settings.get('color2', "#ffffff")
        angle = settings.get('angle', 0)

        # Затемняем оба цвета
        dark_color1 = self._darken_single_color(color1, darken_amount)
        dark_color2 = self._darken_single_color(color2, darken_amount)

        return self._generate_qlineargradient(dark_color1, dark_color2, angle)

    def _generate_qlineargradient(self, color1, color2, angle):
        """Вспомогательный метод для генерации строки qlineargradient."""
        rad = math.radians(angle)
        x1 = 0.5 - 0.5 * math.cos(rad)
        y1 = 0.5 - 0.5 * math.sin(rad)
        x2 = 0.5 + 0.5 * math.cos(rad)
        y2 = 0.5 + 0.5 * math.sin(rad)
        return f"qlineargradient(x1:{x1:.2f}, y1:{y1:.2f}, x2:{x2:.2f}, y2:{y2:.2f}, stop:0 {color1}, stop:1 {color2})"

    def _darken_single_color(self, color_str, amount):
        """Вспомогательный метод для затемнения одного цвета."""
        if not color_str or not color_str.startswith('#'):
            return "#000000"
        color = QColor(color_str)
        color.setRed(max(0, color.red() - amount))
        color.setGreen(max(0, color.green() - amount))
        color.setBlue(max(0, color.blue() - amount))
        return color.name()

    def save_preset(self):
        """Сохраняет текущие стили как новый пресет."""
        dialog = CustomInputDialog('Сохранить пресет', 'Введите имя пресета:', self)
        if dialog.exec_() != QDialog.Accepted:
            return

        preset_name = dialog.get_text().strip()
        if not preset_name:
            self.assistant.show_notification_message("Имя пресета не может быть пустым!")
            return

        # Проверяем существующие пресеты
        conflict_paths = [
            os.path.join(self.base_presets, f"{preset_name}.json"),
            os.path.join(self.custom_presets, f"{preset_name}.json")
        ]

        if any(os.path.exists(path) for path in conflict_paths):
            self.assistant.show_notification_message(f"Пресет '{preset_name}' уже существует!\nПожалуйста, выберите другое имя.")
            return

        try:
            os.makedirs(self.custom_presets, exist_ok=True)
            preset_path = conflict_paths[1]  # custom_presets путь

            with open(preset_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "QWidget": {
                        "background-color": self.get_gradient_css('background') if self.gradient_settings['background'][
                            'enabled'] else self.bg_color,
                        "color": self.text_color,
                        "font-size": "13px"
                    },
                    "QPushButton": {
                        "background-color": self.get_gradient_css('buttons') if self.gradient_settings['buttons'][
                            'enabled'] else self.btn_color,
                        "color": self.text_color,
                        "height": "30px",
                        "border": f"1px solid {self.get_gradient_css('borders')}" if self.gradient_settings['borders'][
                            'enabled'] else f"1px solid {self.border_color}",
                        "border-radius": "3px",
                        "font-size": "13px"
                    },
                    "QPushButton:hover": {
                        "background-color": self.get_hover_gradient_css('buttons'),
                        "color": self.text_color,
                        "font-size": "13px"
                    },
                    "QPushButton:pressed": {
                        "background-color": self.get_pressed_gradient_css('buttons', 30),
                        "padding-left": "3px",
                        "padding-top": "3px",
                    },
                    "QTextEdit": {
                        "background": "transparent",
                        "color": self.text_edit_color,
                        "border": "1px solid",
                        "border-radius": "4px",
                        "font-size": "15px"
                    },
                    "label_version": {
                        "background": "transparent",
                        "color": self.text_edit_color,
                        "font-size": "10px"
                    },
                    "label_message": {
                        "color": self.text_color,
                        "font-size": "13px"
                    },
                    "update_label": {
                        "background": "transparent",
                        "color": self.text_edit_color,
                        "font-size": "12px"
                    },
                    "TitleBar": {
                        "border-bottom": f"1px solid {self.get_gradient_css('borders')}" if
                        self.gradient_settings['borders']['enabled'] else f"1px solid {self.border_color}"
                    },
                    "TrayButton": {
                        "background-color": self.get_gradient_css('buttons') if self.gradient_settings['buttons'][
                            'enabled'] else self.btn_color,
                        "color": self.text_color,
                        "height": "30px",
                        "border": f"1px solid {self.get_gradient_css('borders')}" if self.gradient_settings['borders'][
                            'enabled'] else f"1px solid {self.border_color}",
                        "border-radius": "3px",
                        "font-size": "13px"
                    },
                    "TrayButton:hover": {
                        "color": "#ffffff",
                        "background-color": "#0790EC",
                        "border": "1px solid #0790EC"
                    },
                    "CloseButton": {
                        "background-color": self.get_gradient_css('buttons') if self.gradient_settings['buttons'][
                            'enabled'] else self.btn_color,
                        "color": self.text_color,
                        "height": "30px",
                        "border": f"1px solid {self.get_gradient_css('borders')}" if self.gradient_settings['borders'][
                            'enabled'] else f"1px solid {self.border_color}",
                        "border-radius": "3px",
                        "font-size": "13px"
                    },
                    "CloseButton:hover": {
                        "color": "#ffffff",
                        "background-color": "#E04F4F",
                        "border": "1px solid #E04F4F"
                    },
                    "MessageContainer": {
                        "border": f"1px solid {self.get_gradient_css('borders')}" if self.gradient_settings['borders'][
                            'enabled'] else f"1px solid {self.border_color}",
                        "border-radius": "25px"
                    }
                }, f, indent=4, ensure_ascii=False)

            self.load_presets()
            self.assistant.show_notification_message("Пресет сохранен!")

        except Exception as e:
            self.assistant.show_notification_message(f"Ошибка сохранения:\n{str(e)}")

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
            self.assistant.show_notification_message(f"Пресет '{selected_preset}' не найден ни в одной из папок.")
            return

        try:
            with open(preset_path, 'r', encoding='utf-8') as json_file:
                styles = json.load(json_file)

            # Загружаем основные цвета текста (они не зависят от градиентов)
            self.text_color = styles.get("QWidget", {}).get("color",
                                                            "#8eaee5")  # Используется для текста кнопок и виджетов
            self.text_edit_color = styles.get("QTextEdit", {}).get("color", "#ffffff")

            # Загружаем настройки для каждого элемента, полагаясь на load_element_settings
            # для правильного парсинга и обновления внутренних структур и устаревших переменных
            self.load_element_settings(
                'background',
                styles.get("QWidget", {}).get("background-color", "#1d2028")
            )
            self.load_element_settings(
                'buttons',
                styles.get("QPushButton", {}).get("background-color", "#293f85")
            )

            # Для бордера нужно извлечь часть цвета/градиента из полной CSS строки
            border_full_css = styles.get("QPushButton", {}).get("border", "1px solid #293f85")
            self.load_element_settings('borders', border_full_css)  # <-- Исправлено

            # --- ДОБАВИТЬ ---
            # Принудительная перерисовка после загрузки пресета, аналогично load_color_settings
            # Это может помочь отобразить сложные стили, такие как градиентные бордера
            QApplication.processEvents()  # Обработать все события в очереди
            self.container.repaint()  # Принудительно перерисовать контейнер
            # --- КОНЕЦ ДОБАВЛЕНИЯ ---

        except Exception as e:
            self.assistant.show_notification_message(f"Ошибка загрузки пресета: {e}")


class GradientPreview(QLabel):
    """Виджет для предпросмотра градиента"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(150, 30)
        self.color1 = QColor("#000000")
        self.color2 = QColor("#ffffff")
        self.angle = 0

    def set_gradient(self, color1, color2, angle):
        self.color1 = QColor(color1) if color1 else QColor("#000000")
        self.color2 = QColor(color2) if color2 else QColor("#ffffff")
        self.angle = angle
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        gradient = QLinearGradient(0, 0, self.width(), self.height())

        rad = math.radians(self.angle)
        x1 = 0.5 - 0.5 * math.cos(rad)
        y1 = 0.5 - 0.5 * math.sin(rad)
        x2 = 0.5 + 0.5 * math.cos(rad)
        y2 = 0.5 + 0.5 * math.sin(rad)

        gradient.setColorAt(0, self.color1)
        gradient.setColorAt(1, self.color2)
        gradient.setStart(self.width() * x1, self.height() * y1)
        gradient.setFinalStop(self.width() * x2, self.height() * y2)

        painter.fillRect(self.rect(), gradient)
        painter.end()

class CustomInputDialog(QDialog):
    """Кастомное диалоговое окно ввода с собственной рамкой"""

    def __init__(self, title, label, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setFixedSize(300, 150)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.init_ui(title, label)

    def init_ui(self, title, label):
        # Основной контейнер
        self.container = QWidget(self)
        self.container.setObjectName("MessageContainer")
        self.container.setGeometry(0, 0, self.width(), self.height())

        # Кастомный заголовок
        self.title_bar = QWidget(self.container)
        self.title_bar.setObjectName("TitleBar")
        self.title_bar.setGeometry(1, 1, self.width() - 2, 35)
        self.title_layout = QHBoxLayout(self.title_bar)
        self.title_layout.setContentsMargins(10, 5, 10, 5)
        self.title_layout.setSpacing(5)

        self.title_label = QLabel(title, self.title_bar)
        self.title_label.setGeometry(10, 5, 200, 20)
        self.title_layout.addWidget(self.title_label)

        self.close_btn = QPushButton("✕", self.title_bar)
        self.close_btn.setFixedSize(25, 25)
        self.close_btn.setObjectName("CloseButton")
        self.close_btn.clicked.connect(self.reject)
        self.title_layout.addWidget(self.close_btn)

        # Основное содержимое
        self.content_widget = QWidget(self.container)
        self.content_widget.setGeometry(1, 36, self.width() - 2, self.height() - 37)
        self.content_widget.setObjectName("ContentWidget")

        # Поле ввода
        self.input_field = QLineEdit(self.content_widget)
        self.input_field.setPlaceholderText(label)

        # Кнопки
        self.ok_button = QPushButton('Сохранить', self.content_widget)
        self.ok_button.setStyleSheet("padding: 1px 10px;")
        self.ok_button.setObjectName("AcceptButton")
        self.ok_button.clicked.connect(self.accept)

        self.cancel_button = QPushButton('Закрыть', self.content_widget)
        self.cancel_button.setStyleSheet("padding: 1px 10px;")
        self.cancel_button.setObjectName("RejectButton")
        self.cancel_button.clicked.connect(self.reject)

        # Размещение элементов
        main_layout = QVBoxLayout(self.content_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        main_layout.addWidget(self.input_field)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        main_layout.addLayout(button_layout)

        # Установка стратегии позиционирования
        self.set_position_strategy()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()  # Закрываем только это окно
        else:
            super().keyPressEvent(event)

    def set_position_strategy(self):
        """Выбирает стратегию позиционирования окна"""
        self.position_strategy = self.center_to_parent()

    def ensure_on_screen(self):
        screen_geometry = QApplication.desktop().availableGeometry()
        if not screen_geometry.contains(self.geometry()):
            self.move(
                min(screen_geometry.right() - self.width(), max(screen_geometry.left(), self.x())),
                min(screen_geometry.bottom() - self.height(), max(screen_geometry.top(), self.y())))

    def center_to_parent(self):
        """Центрирует по горизонтали и позиционирует чуть ниже заголовка родителя"""
        if not self.parent():
            return

        parent_rect = self.parent().geometry()
        title_bar_height = 20  # Высота заголовка родительского окна (может потребоваться подстройка)

        # Центрируем по горизонтали и позиционируем вертикально чуть ниже заголовка
        new_x = parent_rect.x() + (parent_rect.width() - self.width()) // 2
        new_y = parent_rect.y() + title_bar_height + 15

        self.move(new_x, new_y)

        # Проверяем, чтобы окно не выходило за пределы экрана
        self.ensure_on_screen()

    def get_text(self):
        """Возвращает введенный текст"""
        return self.input_field.text()

    def mousePressEvent(self, event):
        """Перетаскивание окна за заголовок"""
        if event.button() == Qt.LeftButton and event.y() < 30:
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        """Перетаскивание окна за заголовок"""
        if hasattr(self, 'drag_position') and event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.drag_position)
            event.accept()
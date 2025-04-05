import json
import os
from path_builder import get_path
from logging_config import logger, debug_logger
from PyQt5.QtCore import QSettings, pyqtSignal, Qt, QPoint, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QPushButton, QCheckBox, QLineEdit, QLabel, QSlider, QComboBox, \
    QVBoxLayout, QWidget, QDialog, QColorDialog, QFrame, QStackedWidget, QHBoxLayout, QGraphicsDropShadowEffect, \
    QDialogButtonBox, QButtonGroup, QApplication

speakers = dict(Пласид='placide', Бестия='rogue', Джонни='johnny', СанСаныч='sanych',
                Санбой='sanboy', Тигрица='tigress', Стейтем='stathem')


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
        new_y = parent_rect.y() + title_bar_height + 15  # +10 для небольшого отступа

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


class MainSettingsWindow(QDialog):
    """Окно настроек с анимацией и кнопками вкладок"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.assistant = parent
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setFixedSize(450, self.assistant.height())  # Шире для кнопок

        # Анимация движения
        self.pos_animation = QPropertyAnimation(self, b"pos")
        self.pos_animation.setDuration(300)
        self.pos_animation.setEasingCurve(QEasingCurve.OutCubic)

        # Анимация прозрачности
        self.opacity_animation = QPropertyAnimation(self, b"windowOpacity")
        self.opacity_animation.setDuration(300)

        self.init_ui()
        self.setup_animation()

    def init_ui(self):
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.container = QWidget(self)
        self.container.setObjectName("SettingsContainer")
        self.container.setGeometry(0, 0, self.width(), self.height())

        # Кастомный заголовок
        self.title_bar = QWidget(self.container)
        self.title_bar.setObjectName("TitleBar")
        self.title_bar.setGeometry(0, 0, self.width(), 35)
        self.title_layout = QHBoxLayout(self.title_bar)
        self.title_layout.setContentsMargins(10, 5, 10, 5)
        self.title_layout.setSpacing(5)

        self.title_label = QLabel("Настройки", self.title_bar)
        self.title_label.setGeometry(15, 5, 200, 30)
        self.title_layout.addWidget(self.title_label)
        self.close_btn = QPushButton("✕", self.title_bar)
        self.close_btn.setFixedSize(25, 25)
        self.close_btn.setObjectName("CloseButton")
        self.close_btn.clicked.connect(self.hide_with_animation)
        self.title_layout.addWidget(self.close_btn)

        # Контейнер для кнопок вкладок
        self.tabs_container = QWidget(self.container)
        self.tabs_container.setGeometry(0, 40, 120, self.height() - 40)
        self.tabs_container.setObjectName("TabsContainer")

        # Вертикальный layout с выравниванием по верхнему краю
        self.tabs_layout = QVBoxLayout(self.tabs_container)
        self.tabs_layout.setContentsMargins(5, 15, 5, 10)
        self.tabs_layout.setSpacing(5)
        self.tabs_layout.setAlignment(Qt.AlignTop)

        # Контейнер для содержимого
        self.content_stack = QStackedWidget(self.container)
        self.content_stack.setGeometry(120, 40, self.width() - 120, self.height() - 40)
        self.content_stack.setObjectName("ContentStack")

        # Разделитель
        self.separator = QFrame(self.container)
        self.separator.setGeometry(120, 40, 1, self.height() - 40)
        self.separator.setFrameShape(QFrame.VLine)

        # Добавляем вкладки
        self.add_tab("Основные", SettingsWidget(self.assistant))
        self.add_tab("Интерфейс", InterfaceWidget(self.assistant))

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            if self.opacity_animation.state() != QPropertyAnimation.Running:
                self.hide_with_animation()
            event.accept()
        else:
            super().keyPressEvent(event)

    def add_tab(self, name, widget):
        """Добавляет вкладку с кнопкой"""
        btn = QPushButton(name)
        btn.setCheckable(True)
        btn.setObjectName("TabButton")
        btn.clicked.connect(lambda: self.switch_tab(widget, btn))

        if self.content_stack.count() == 0:
            btn.setChecked(True)

        self.tabs_layout.addWidget(btn)  # Кнопки будут прижаты к верху
        self.content_stack.addWidget(widget)

    def switch_tab(self, widget, button):
        """Переключает вкладку"""
        for btn in self.tabs_container.findChildren(QPushButton):
            btn.setChecked(False)
        button.setChecked(True)
        self.content_stack.setCurrentWidget(widget)

    def setup_animation(self):
        # Начальная позиция - слева за границей основного окна
        self.move(self.assistant.x() - self.width(),
                  self.assistant.y())

        # Конечная позиция - прижата к левому краю родителя
        self.final_position = QPoint(
            self.assistant.x() - self.width(),
            self.assistant.y()
        )

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
        # 1. Устанавливаем начальную прозрачность
        self.setWindowOpacity(0.0)

        # 2. Настраиваем анимацию прозрачности
        self.opacity_animation.stop()
        self.opacity_animation.setStartValue(0.0)  # Начинаем с прозрачного
        self.opacity_animation.setEndValue(1.0)  # Заканчиваем непрозрачным

        # 3. Настраиваем анимацию движения
        self.pos_animation.stop()
        self.pos_animation.setStartValue(QPoint(
            self.assistant.x(),
            self.assistant.y()
        ))
        self.pos_animation.setEndValue(self.final_position)

        # 4. Запускаем обе анимации
        self.pos_animation.start()
        self.opacity_animation.start()

        super().showEvent(event)

    def get_settings_widget(self):
        for i in range(self.content_stack.count()):
            widget = self.content_stack.widget(i)
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
            debug_logger.error(f"Пресет '{filename}' не найден ни в одной из папок.")
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
            color_dialog.colorChanged.connect(self.assistant.load_and_apply_styles)
            color_dialog.exec_()
        except Exception as e:
            logger.error(f"Ошибка при открытии окна настроек цветов: {e}")
            debug_logger.error(f"Ошибка при открытии окна настроек цветов: {e}")
            self.assistant.show_message(f"Не удалось открыть настройки цветов: {e}", "Ошибка", "error")


class ColorSettingsWindow(QDialog):
    """Окно изменения оформления интерфейса (цветовая палитра, пресеты)"""

    colorChanged = pyqtSignal()  # Сигнал изменения цвета

    def __init__(self, assistant, parent=None):
        super().__init__(parent)
        self.assistant = assistant
        self.styles = self.assistant.styles
        self.color_settings_path = self.assistant.color_settings_path
        self.base_presets = get_path('bin', 'color_presets')
        self.custom_presets = get_path('user_settings', 'presets')
        os.makedirs(self.custom_presets, exist_ok=True)

        # Настройка окна без рамки
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setFixedSize(300, 400)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # Инициализация переменных для цветов
        self.bg_color = ""
        self.btn_color = ""
        self.text_color = ""
        self.text_edit_color = ""
        self.border_color = ""

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
        self.title_label.setGeometry(10, 5, 200, 20)
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

        # Кнопки для выбора цветов
        self.bg_button = QPushButton('Фон', self.content_widget)
        self.bg_button.clicked.connect(self.choose_background_color)

        self.btn_button = QPushButton('Цвет кнопок', self.content_widget)
        self.btn_button.clicked.connect(self.choose_button_color)

        self.border_button = QPushButton('Обводка кнопок', self.content_widget)
        self.border_button.clicked.connect(self.choose_border_color)

        self.text_button = QPushButton('Цвет текста', self.content_widget)
        self.text_button.clicked.connect(self.choose_text_color)

        self.text_edit_button = QPushButton('Цвет текста в логах', self.content_widget)
        self.text_edit_button.clicked.connect(self.choose_text_edit_color)

        # Кнопка для применения изменений
        self.apply_button = QPushButton('Применить', self.content_widget)
        self.apply_button.clicked.connect(self.apply_changes)

        # Кнопка для сохранения пресета
        self.save_preset_button = QPushButton('Сохранить стиль', self.content_widget)
        self.save_preset_button.clicked.connect(self.save_preset)

        # Выпадающий список для пресетов
        self.preset_combo_box = QComboBox(self.content_widget)
        self.load_presets()
        self.preset_combo_box.setCurrentIndex(0)
        self.preset_combo_box.currentIndexChanged.connect(self.load_preset)

        # Размещение элементов
        layout = QVBoxLayout(self.content_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
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

    # def choose_background_color(self):
    #     try:
    #         initial_color = QColor(self.bg_color) if hasattr(self, 'bg_color') else Qt.white
    #         color = QColorDialog.getColor(initial_color, self)
    #         if color.isValid():
    #             self.bg_color = color.name()
    #     except Exception as e:
    #         logger.error(e)
    #         debug_logger.error(f"Метод choose_background_color: {e}")

    def choose_background_color(self):
        try:
            # Создаем кастомное окно
            dialog = QDialog(self)
            dialog.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
            dialog.setFixedSize(520, 500)
            dialog.setAttribute(Qt.WA_TranslucentBackground)

            # Основной контейнер с рамкой 1px
            container = QWidget(dialog)
            container.setObjectName("MessageContainer")
            container.setGeometry(0, 0, dialog.width(), dialog.height())

            # Заголовок (35px высота)
            title_bar = QWidget(container)
            title_bar.setObjectName("TitleBar")
            title_bar.setGeometry(1, 1, dialog.width() - 2, 35)

            # Layout заголовка
            title_layout = QHBoxLayout(title_bar)
            title_layout.setContentsMargins(10, 5, 10, 5)
            title_layout.setSpacing(5)

            # Надпись заголовка
            title_label = QLabel("Выбор цвета фона")
            title_layout.addWidget(title_label)
            title_layout.addStretch()

            # Кнопка закрытия 25x25
            close_btn = QPushButton("✕")
            close_btn.setFixedSize(25, 25)
            close_btn.setObjectName("CloseButton")
            close_btn.clicked.connect(dialog.reject)
            title_layout.addWidget(close_btn)

            # Встраиваем стандартный QColorDialog
            color_widget = QColorDialog()
            color_widget.setOptions(QColorDialog.NoButtons | QColorDialog.DontUseNativeDialog)

            # Начальный цвет
            if hasattr(self, 'bg_color'):
                color_widget.setCurrentColor(QColor(self.bg_color))

            # Layout содержимого
            content_widget = QWidget(container)
            content_widget.setGeometry(1, 36, dialog.width() - 2, dialog.height() - 37)

            layout = QVBoxLayout(content_widget)
            layout.setContentsMargins(5, 5, 5, 5)
            layout.addWidget(color_widget)

            # Кнопки
            self.ok_button = QPushButton('Применить', self.content_widget)
            self.ok_button.setStyleSheet("padding: 1px 10px;")
            self.ok_button.setObjectName("AcceptButton")
            self.ok_button.clicked.connect(dialog.accept)

            self.cancel_button = QPushButton('Закрыть', self.content_widget)
            self.cancel_button.setStyleSheet("padding: 1px 10px;")
            self.cancel_button.setObjectName("RejectButton")
            self.cancel_button.clicked.connect(dialog.reject)
            button_layout = QHBoxLayout()
            button_layout.addStretch()
            button_layout.addWidget(self.ok_button)
            button_layout.addWidget(self.cancel_button)
            layout.addLayout(button_layout)

            if dialog.exec_() == QDialog.Accepted:
                self.bg_color = color_widget.currentColor().name()
                self.apply_changes()

        except Exception as e:
            logger.error(f"Ошибка в choose_background_color: {e}")
            debug_logger.exception(e)

    # def choose_button_color(self):
    #     try:
    #         initial_color = QColor(self.btn_color) if hasattr(self, 'btn_color') else Qt.white
    #         color = QColorDialog.getColor(initial_color, self)
    #         if color.isValid():
    #             self.btn_color = color.name()
    #     except Exception as e:
    #         logger.error(e)
    #         debug_logger.error(f"Метод choose_button_color: {e}")

    def choose_button_color(self):
        try:
            # Создаем кастомное окно
            dialog = QDialog(self)
            dialog.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
            dialog.setFixedSize(520, 500)
            dialog.setAttribute(Qt.WA_TranslucentBackground)

            # Основной контейнер с рамкой 1px
            container = QWidget(dialog)
            container.setObjectName("MessageContainer")
            container.setGeometry(0, 0, dialog.width(), dialog.height())

            # Заголовок (35px высота)
            title_bar = QWidget(container)
            title_bar.setObjectName("TitleBar")
            title_bar.setGeometry(1, 1, dialog.width() - 2, 35)

            # Layout заголовка
            title_layout = QHBoxLayout(title_bar)
            title_layout.setContentsMargins(10, 5, 10, 5)
            title_layout.setSpacing(5)

            # Надпись заголовка
            title_label = QLabel("Выбор цвета")
            title_layout.addWidget(title_label)
            title_layout.addStretch()

            # Кнопка закрытия 25x25
            close_btn = QPushButton("✕")
            close_btn.setFixedSize(25, 25)
            close_btn.setObjectName("CloseButton")
            close_btn.clicked.connect(dialog.reject)
            title_layout.addWidget(close_btn)

            # Встраиваем стандартный QColorDialog
            color_widget = QColorDialog()
            color_widget.setOptions(QColorDialog.NoButtons | QColorDialog.DontUseNativeDialog)

            # Начальный цвет
            if hasattr(self, 'btn_color'):
                color_widget.setCurrentColor(QColor(self.btn_color))

            # Layout содержимого
            content_widget = QWidget(container)
            content_widget.setGeometry(1, 36, dialog.width() - 2, dialog.height() - 37)

            layout = QVBoxLayout(content_widget)
            layout.setContentsMargins(5, 5, 5, 5)
            layout.addWidget(color_widget)

            # Кнопки
            self.ok_button = QPushButton('Применить', self.content_widget)
            self.ok_button.setStyleSheet("padding: 1px 10px;")
            self.ok_button.setObjectName("AcceptButton")
            self.ok_button.clicked.connect(dialog.accept)

            self.cancel_button = QPushButton('Закрыть', self.content_widget)
            self.cancel_button.setStyleSheet("padding: 1px 10px;")
            self.cancel_button.setObjectName("RejectButton")
            self.cancel_button.clicked.connect(dialog.reject)
            button_layout = QHBoxLayout()
            button_layout.addStretch()
            button_layout.addWidget(self.ok_button)
            button_layout.addWidget(self.cancel_button)
            layout.addLayout(button_layout)

            if dialog.exec_() == QDialog.Accepted:
                self.btn_color = color_widget.currentColor().name()
                self.apply_changes()

        except Exception as e:
            logger.error(f"Ошибка в choose_background_color: {e}")
            debug_logger.exception(e)

    # def choose_border_color(self):
    #     try:
    #         initial_color = QColor(self.border_color) if hasattr(self, 'border_color') else Qt.white
    #         color = QColorDialog.getColor(initial_color, self)
    #         if color.isValid():
    #             self.border_color = color.name()
    #     except Exception as e:
    #         logger.error(e)
    #         debug_logger.error(f"Метод choose_border_color: {e}")

    def choose_border_color(self):
        try:
            # Создаем кастомное окно
            dialog = QDialog(self)
            dialog.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
            dialog.setFixedSize(520, 500)
            dialog.setAttribute(Qt.WA_TranslucentBackground)

            # Основной контейнер с рамкой 1px
            container = QWidget(dialog)
            container.setObjectName("MessageContainer")
            container.setGeometry(0, 0, dialog.width(), dialog.height())

            # Заголовок (35px высота)
            title_bar = QWidget(container)
            title_bar.setObjectName("TitleBar")
            title_bar.setGeometry(1, 1, dialog.width() - 2, 35)

            # Layout заголовка
            title_layout = QHBoxLayout(title_bar)
            title_layout.setContentsMargins(10, 5, 10, 5)
            title_layout.setSpacing(5)

            # Надпись заголовка
            title_label = QLabel("Выбор цвета")
            title_layout.addWidget(title_label)
            title_layout.addStretch()

            # Кнопка закрытия 25x25
            close_btn = QPushButton("✕")
            close_btn.setFixedSize(25, 25)
            close_btn.setObjectName("CloseButton")
            close_btn.clicked.connect(dialog.reject)
            title_layout.addWidget(close_btn)

            # Встраиваем стандартный QColorDialog
            color_widget = QColorDialog()
            color_widget.setOptions(QColorDialog.NoButtons | QColorDialog.DontUseNativeDialog)

            # Начальный цвет
            if hasattr(self, 'border_color'):
                color_widget.setCurrentColor(QColor(self.border_color))

            # Layout содержимого
            content_widget = QWidget(container)
            content_widget.setGeometry(1, 36, dialog.width() - 2, dialog.height() - 37)

            layout = QVBoxLayout(content_widget)
            layout.setContentsMargins(5, 5, 5, 5)
            layout.addWidget(color_widget)

            # Кнопки
            self.ok_button = QPushButton('Применить', self.content_widget)
            self.ok_button.setStyleSheet("padding: 1px 10px;")
            self.ok_button.setObjectName("AcceptButton")
            self.ok_button.clicked.connect(dialog.accept)

            self.cancel_button = QPushButton('Закрыть', self.content_widget)
            self.cancel_button.setStyleSheet("padding: 1px 10px;")
            self.cancel_button.setObjectName("RejectButton")
            self.cancel_button.clicked.connect(dialog.reject)
            button_layout = QHBoxLayout()
            button_layout.addStretch()
            button_layout.addWidget(self.ok_button)
            button_layout.addWidget(self.cancel_button)
            layout.addLayout(button_layout)

            if dialog.exec_() == QDialog.Accepted:
                self.border_color = color_widget.currentColor().name()
                self.apply_changes()

        except Exception as e:
            logger.error(f"Ошибка в choose_background_color: {e}")
            debug_logger.exception(e)

    # def choose_text_color(self):
    #     try:
    #         initial_color = QColor(self.text_color) if hasattr(self, 'text_color') else Qt.white
    #         color = QColorDialog.getColor(initial_color, self)
    #         if color.isValid():
    #             self.text_color = color.name()
    #     except Exception as e:
    #         logger.error(e)
    #         debug_logger.error(f"Метод choose_text_color: {e}")

    def choose_text_color(self):
        try:
            # Создаем кастомное окно
            dialog = QDialog(self)
            dialog.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
            dialog.setFixedSize(520, 500)
            dialog.setAttribute(Qt.WA_TranslucentBackground)

            # Основной контейнер с рамкой 1px
            container = QWidget(dialog)
            container.setObjectName("MessageContainer")
            container.setGeometry(0, 0, dialog.width(), dialog.height())

            # Заголовок (35px высота)
            title_bar = QWidget(container)
            title_bar.setObjectName("TitleBar")
            title_bar.setGeometry(1, 1, dialog.width() - 2, 35)

            # Layout заголовка
            title_layout = QHBoxLayout(title_bar)
            title_layout.setContentsMargins(10, 5, 10, 5)
            title_layout.setSpacing(5)

            # Надпись заголовка
            title_label = QLabel("Выбор цвета")
            title_layout.addWidget(title_label)
            title_layout.addStretch()

            # Кнопка закрытия 25x25
            close_btn = QPushButton("✕")
            close_btn.setFixedSize(25, 25)
            close_btn.setObjectName("CloseButton")
            close_btn.clicked.connect(dialog.reject)
            title_layout.addWidget(close_btn)

            # Встраиваем стандартный QColorDialog
            color_widget = QColorDialog()
            color_widget.setOptions(QColorDialog.NoButtons | QColorDialog.DontUseNativeDialog)

            # Начальный цвет
            if hasattr(self, 'text_color'):
                color_widget.setCurrentColor(QColor(self.text_color))

            # Layout содержимого
            content_widget = QWidget(container)
            content_widget.setGeometry(1, 36, dialog.width() - 2, dialog.height() - 37)

            layout = QVBoxLayout(content_widget)
            layout.setContentsMargins(5, 5, 5, 5)
            layout.addWidget(color_widget)

            # Кнопки
            self.ok_button = QPushButton('Применить', self.content_widget)
            self.ok_button.setStyleSheet("padding: 1px 10px;")
            self.ok_button.setObjectName("AcceptButton")
            self.ok_button.clicked.connect(dialog.accept)

            self.cancel_button = QPushButton('Закрыть', self.content_widget)
            self.cancel_button.setStyleSheet("padding: 1px 10px;")
            self.cancel_button.setObjectName("RejectButton")
            self.cancel_button.clicked.connect(dialog.reject)
            button_layout = QHBoxLayout()
            button_layout.addStretch()
            button_layout.addWidget(self.ok_button)
            button_layout.addWidget(self.cancel_button)
            layout.addLayout(button_layout)

            if dialog.exec_() == QDialog.Accepted:
                self.text_color = color_widget.currentColor().name()
                self.apply_changes()

        except Exception as e:
            logger.error(f"Ошибка в choose_background_color: {e}")
            debug_logger.exception(e)

    # def choose_text_edit_color(self):
    #     try:
    #         initial_color = QColor(self.text_edit_color) if hasattr(self, 'text_edit_color') else Qt.white
    #         color = QColorDialog.getColor(initial_color, self)
    #         if color.isValid():
    #             self.text_edit_color = color.name()
    #     except Exception as e:
    #         logger.error(e)
    #         debug_logger.error(f"Метод choose_text_edit_color: {e}")

    def choose_text_edit_color(self):
        try:
            # Создаем кастомное окно
            dialog = QDialog(self)
            dialog.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
            dialog.setFixedSize(520, 500)
            dialog.setAttribute(Qt.WA_TranslucentBackground)

            # Основной контейнер с рамкой 1px
            container = QWidget(dialog)
            container.setObjectName("MessageContainer")
            container.setGeometry(0, 0, dialog.width(), dialog.height())

            # Заголовок (35px высота)
            title_bar = QWidget(container)
            title_bar.setObjectName("TitleBar")
            title_bar.setGeometry(1, 1, dialog.width() - 2, 35)

            # Layout заголовка
            title_layout = QHBoxLayout(title_bar)
            title_layout.setContentsMargins(10, 5, 10, 5)
            title_layout.setSpacing(5)

            # Надпись заголовка
            title_label = QLabel("Выбор цвета")
            title_layout.addWidget(title_label)
            title_layout.addStretch()

            # Кнопка закрытия 25x25
            close_btn = QPushButton("✕")
            close_btn.setFixedSize(25, 25)
            close_btn.setObjectName("CloseButton")
            close_btn.clicked.connect(dialog.reject)
            title_layout.addWidget(close_btn)

            # Встраиваем стандартный QColorDialog
            color_widget = QColorDialog()
            color_widget.setOptions(QColorDialog.NoButtons | QColorDialog.DontUseNativeDialog)

            # Начальный цвет
            if hasattr(self, 'text_edit_color'):
                color_widget.setCurrentColor(QColor(self.text_edit_color))

            # Layout содержимого
            content_widget = QWidget(container)
            content_widget.setGeometry(1, 36, dialog.width() - 2, dialog.height() - 37)

            layout = QVBoxLayout(content_widget)
            layout.setContentsMargins(5, 5, 5, 5)
            layout.addWidget(color_widget)

            # Кнопки
            self.ok_button = QPushButton('Применить', self.content_widget)
            self.ok_button.setStyleSheet("padding: 1px 10px;")
            self.ok_button.setObjectName("AcceptButton")
            self.ok_button.clicked.connect(dialog.accept)

            self.cancel_button = QPushButton('Закрыть', self.content_widget)
            self.cancel_button.setStyleSheet("padding: 1px 10px;")
            self.cancel_button.setObjectName("RejectButton")
            self.cancel_button.clicked.connect(dialog.reject)
            button_layout = QHBoxLayout()
            button_layout.addStretch()
            button_layout.addWidget(self.ok_button)
            button_layout.addWidget(self.cancel_button)
            layout.addLayout(button_layout)

            if dialog.exec_() == QDialog.Accepted:
                self.text_edit_color = color_widget.currentColor().name()
                self.apply_changes()

        except Exception as e:
            logger.error(f"Ошибка в choose_background_color: {e}")
            debug_logger.exception(e)

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
                    "font-size": "15px"
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
                },
                "TitleBar": {
                    "border-bottom": f"1px solid {self.border_color}"
                },
                "TrayButton": {
                    "background-color": self.btn_color,
                    "color": self.text_color,
                    "height": "30px",
                    "border": f"1px solid {self.border_color}",
                    "border-radius": "3px",
                    "font-size": "13px"
                },
                "TrayButton:hover": {
                    "color": "#ffffff",
                    "background-color": "#0790EC",
                    "border": "1px solid #0790EC"
                },
                "CloseButton": {
                    "background-color": self.btn_color,
                    "color": self.text_color,
                    "height": "30px",
                    "border": f"1px solid {self.border_color}",
                    "border-radius": "3px",
                    "font-size": "13px"
                },
                "CloseButton:hover": {
                    "color": "#ffffff",
                    "background-color": "#E04F4F",
                    "border": "1px solid #E04F4F"
                },
                "MessageContainer": {
                    "border": f"1px solid {self.border_color}"
                }
            }
            self.save_color_settings(new_styles)
            self.colorChanged.emit()
        except Exception as e:
            logger.info(f"Ошибка при применении изменений: {e}")
            debug_logger.info(f"Ошибка при применении изменений: {e}")
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
                debug_logger.info("Сохранение пресета отменено")
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
                            "font-size": "15px"
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
                        },
                        "TitleBar": {
                            "border-bottom": f"1px solid {self.border_color}"
                        },
                        "TrayButton": {
                            "background-color": self.btn_color,
                            "color": self.text_color,
                            "height": "30px",
                            "border": f"1px solid {self.border_color}",
                            "border-radius": "3px",
                            "font-size": "13px"
                        },
                        "TrayButton:hover": {
                            "color": "#ffffff",
                            "background-color": "#0790EC",
                            "border": "1px solid #0790EC"
                        },
                        "CloseButton": {
                            "background-color": self.btn_color,
                            "color": self.text_color,
                            "height": "30px",
                            "border": f"1px solid {self.border_color}",
                            "border-radius": "3px",
                            "font-size": "13px"
                        },
                        "CloseButton:hover": {
                            "color": "#ffffff",
                            "background-color": "#E04F4F",
                            "border": "1px solid #E04F4F"
                        },
                        "MessageContainer": {
                            "border": f"1px solid {self.border_color}"
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
            debug_logger.error(f"Пресет '{selected_preset}' не найден ни в одной из папок.")
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
                debug_logger.info(f"Пресет загружен: {preset_path}")

        except json.JSONDecodeError:
            logger.error(f"Ошибка: файл пресета повреждён ({preset_path}).")
            debug_logger.error(f"Ошибка: файл пресета повреждён ({preset_path}).")
        except Exception as e:
            logger.error(f"Ошибка загрузки пресета: {e}")
            debug_logger.error(f"Ошибка загрузки пресета: {e}")

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

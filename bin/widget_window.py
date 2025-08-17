import json
import os
import subprocess
from urllib.parse import parse_qsl

import wmi
from PyQt5.QtGui import QFont, QFontDatabase, QRegion
from PyQt5.QtSvg import QSvgWidget
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QHBoxLayout, \
    QDialog, QLabel, QGridLayout, QStackedWidget, QSizePolicy, QTextEdit
from PyQt5.QtCore import Qt, QPoint, QSize, QPropertyAnimation, QRect, QTimer, QTime, QEasingCurve

from bin.apply_color_methods import ApplyColor
from bin.audio_control import controller
from bin.function_list_main import shutdown_windows
from bin.signals import color_signal
from logging_config import debug_logger
from path_builder import get_path


class WindowStateManager:
    def __init__(self, config_path=get_path("user_settings", "widget_state.json")):
        self.config_path = config_path
        self.default_state = {
            "window_position": {"x": 100, "y": 100},
            "window_size": {"width": 240, "height": 300},
            "is_compact": False,
            "is_pinned": False,
            "is_locked": False
        }

        # Создаем файл при инициализации, если его нет
        if not os.path.exists(self.config_path):
            self.save_state(self.default_state)

    def load_state(self):
        """Загружает состояние окна из JSON файла"""
        try:
            with open(self.config_path, 'r') as f:
                state = json.load(f)
                # Объединяем с default_state для обратной совместимости
                return {**self.default_state, **state}
        except (json.JSONDecodeError, IOError) as e:
            debug_logger.error(f"Ошибка загрузки состояния: {e}, используются значения по умолчанию")
            return self.default_state.copy()

    def save_state(self, state):
        """Сохраняет состояние окна в JSON файл"""
        try:
            # Создаем папку, если ее нет
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)

            with open(self.config_path, 'w') as f:
                json.dump(state, f, indent=4)
        except IOError as e:
            debug_logger.error(f"Ошибка сохранения состояния: {e}")

    def save_window_state(self, window):
        """Специальный метод для сохранения состояния QWidget"""
        state = {
            "window_position": {
                "x": window.pos().x(),
                "y": window.pos().y()
            },
            "window_size": {
                "width": window.width(),
                "height": window.height()
            },
            "is_compact": getattr(window, 'is_compact', False),
            "is_pinned": getattr(window, 'is_pinned', False),
            "is_locked": getattr(window, 'is_locked', False)
        }
        self.save_state(state)

    def apply_state(self, window):
        """Применяет сохраненное состояние к окну"""
        state = self.load_state()

        window.move(QPoint(state["window_position"]["x"],
                           state["window_position"]["y"]))
        window.resize(QSize(state["window_size"]["width"],
                            state["window_size"]["height"]))

        # Устанавливаем дополнительные состояния
        window.is_compact = state["is_compact"]
        window.is_pinned = state["is_pinned"]
        window.is_locked = state["is_locked"]

        return state


class SmartWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.assistant = parent
        self.buttons_data = {}
        self.player_buttons = {}
        self.is_paused = False
        color_signal.color_changed.connect(self.update_colors)
        self.notes_file = get_path("user_settings", "notes.txt")

        # Пути к иконкам
        self.camera_path = get_path("bin", "icons", "camera.svg")
        self.power_path = get_path("bin", "icons", "power.svg")
        self.open_main_path = get_path("bin", "icons", "open_main.svg")
        self.settings_path = get_path("bin", "icons", "settings.svg")
        self.shortcut_path = get_path("bin", "icons", "shortcut.svg")
        self.next_track = get_path("bin", "icons", "next.svg")
        self.prev_track = get_path("bin", "icons", "prev.svg")
        self.pause_track = get_path("bin", "icons", "pause.svg")
        self.play_track = get_path("bin", "icons", "play.svg")
        self.pin_path = get_path("bin", "icons", "pin.svg")
        self.active_pin_path = get_path("bin", "icons", "active_pin.svg")
        self.lock_path = get_path("bin", "icons", "lock.svg")
        self.unlock_path = get_path("bin", "icons", "unlock.svg")
        self.close_path = get_path("bin", "icons", "cancel.svg")
        self.resize_path = get_path("bin", "icons", "resize.svg")
        self.ohm_path = self.assistant.ohm_path
        self.ohm_namespace = "root\\OpenHardwareMonitor"

        # Шрифт
        self.font_id = QFontDatabase.addApplicationFont(
            get_path("bin", "fonts", "Digital Numbers", "DigitalNumbers-Regular.ttf"))
        self.font_family = QFontDatabase.applicationFontFamilies(self.font_id)[0]

        # Стили
        self.style_manager = ApplyColor(self)
        self.color_path = self.style_manager.color_path
        self.styles = self.style_manager.load_styles()

        # Таймер времени
        self.timer_clock = QTimer(self)
        self.timer_clock.timeout.connect(self.update_time)
        self.timer_clock.start(1000)

        # Менеджер состояния
        self.state_manager = WindowStateManager()
        saved_state = self.state_manager.apply_state(self)
        self.is_compact = saved_state["is_compact"]
        self.is_pinned = saved_state["is_pinned"]
        self.is_locked = False

        self.init_ui()

        # Флаги окна
        base_flags = Qt.FramelessWindowHint | Qt.Tool
        if self.is_pinned:
            base_flags |= Qt.WindowStaysOnTopHint
            self.pin_svg.load(self.active_pin_path)
            self.style_manager.apply_color_svg(self.pin_svg, strength=0.95)
        self.setWindowFlags(base_flags)

        # Для перетаскивания
        self.old_pos = None
        self.is_dragging = False
        self.current_position = {"x": 0, "y": 0}

        # Таймеры
        self.sensor_timer = QTimer()
        self.sensor_timer.timeout.connect(self.update_sensors)

        # Загрузка заметок
        self.load_notes()

        # Анимация
        self.animation = None

        # Обновляем время
        self.update_time()
        self.update_ui_for_mode()

    def init_ui(self):
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("background-color: transparent")

        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)

        # Основной контент
        self.main_container = QWidget()
        self.main_container.setObjectName("MainContainer")
        self.main_container.setStyleSheet("""
                    #MainContainer {
                        background: rgba(30, 30, 30, 180);
                        border-radius: 10px;
                    }
                """)
        self.content_layout = QVBoxLayout(self.main_container)
        self.content_layout.setContentsMargins(5, 5, 5, 5)
        self.content_layout.setSpacing(5)

        self.title_bar = self.create_title_bar()
        self.content_layout.addWidget(self.title_bar)

        # Часы
        self.clock_mini = QLabel()
        self.clock_mini.setAlignment(Qt.AlignCenter)
        self.clock_font = QFont(self.font_family, 30)
        self.clock_mini.setFont(self.clock_font)
        self.clock_mini.setStyleSheet("""
                QLabel {
                    color: white;
                    background: transparent;
                    font-size: 15px;
                }
            """)
        self.content_layout.addWidget(self.clock_mini)

        # Аудио
        self.audio_widget = self.create_audio_controls()
        self.content_layout.addWidget(self.audio_widget, alignment=Qt.AlignCenter)

        # Кнопки
        self.buttons_widget = self.create_main_buttons()
        self.content_layout.addWidget(self.buttons_widget, alignment=Qt.AlignCenter)

        # Вкладки (по умолчанию скрыты в компактном режиме)
        self.tab_widget = self.create_tabs_widget()
        self.content_layout.addWidget(self.tab_widget)

        self.layout().addWidget(self.main_container)

        if not self.is_compact:
            self.switch_tab(1)

    def create_title_bar(self):
        title_bar = QWidget()
        title_bar.setObjectName("TitleBar")
        title_bar.setFixedHeight(25)
        title_bar.setStyleSheet("""
            #TitleBar {
                background: transparent;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
                border-bottom: 1px solid rgba(70, 70, 70, 100);
            }
        """)
        layout = QHBoxLayout(title_bar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.clock_widget = QWidget()
        self.clock_widget.setStyleSheet("background: transparent;")
        clock_layout = QHBoxLayout(self.clock_widget)
        clock_layout.setContentsMargins(0, 0, 0, 0)

        self.clock_title = QLabel()
        self.clock_title.setAlignment(Qt.AlignCenter)
        self.clock_title.setStyleSheet("""
                QLabel {
                    color: white;
                    background: transparent;
                    font-size: 13px;
                    padding: 0 5px;
                }
            """)

        # Устанавливаем шрифт
        self.clock_font = QFont(self.font_family, 12)
        self.clock_title.setFont(self.clock_font)

        clock_layout.addWidget(self.clock_title)
        layout.addWidget(self.clock_widget)

        # Кнопки
        self.pin_btn = QPushButton()
        self.pin_btn.setFixedSize(20, 20)
        self.pin_btn.setToolTip("Поверх других окон")
        self.pin_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
            }
            QPushButton:hover {
                background: rgba(40, 110, 230, 80%);
            }
        """)
        self.pin_svg = QSvgWidget(self.pin_path, self.pin_btn)
        self.pin_svg.setFixedSize(13, 13)
        self.pin_svg.move(3, 3)
        self.pin_svg.setStyleSheet("background: transparent; border: none;")
        self.pin_btn.clicked.connect(self.pin_widget)
        self.pin_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        self.lock_btn = QPushButton()
        self.lock_btn.setFixedSize(20, 20)
        self.lock_btn.setToolTip("Запретить перетаскивание")
        self.lock_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
            }
            QPushButton:hover {
                background: rgba(40, 110, 230, 80%);
            }
        """)
        self.lock_svg = QSvgWidget(self.lock_path, self.lock_btn)
        self.lock_svg.setFixedSize(13, 13)
        self.lock_svg.move(3, 3)
        self.lock_svg.setStyleSheet("background: transparent; border: none;")
        self.lock_btn.clicked.connect(self.lock_state)
        self.lock_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        self.resize_btn = QPushButton()
        self.resize_btn.setFixedSize(20, 20)
        self.resize_btn.setToolTip("Компактный режим")
        self.resize_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
            }
            QPushButton:hover {
                background: rgba(40, 110, 230, 80%);
            }
        """)
        self.resize_svg = QSvgWidget(self.resize_path, self.resize_btn)
        self.resize_svg.setFixedSize(13, 13)
        self.resize_svg.move(3, 3)
        self.resize_svg.setStyleSheet("background: transparent; border: none;")
        self.resize_btn.clicked.connect(self.resize_widget)

        self.close_btn = QPushButton()
        self.close_btn.setFixedSize(20, 20)
        self.close_btn.setToolTip("Закрыть")
        self.close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
            }
            QPushButton:hover {
                background: rgba(230, 37, 37, 80%);
            }
        """)
        self.close_svg = QSvgWidget(self.close_path, self.close_btn)
        self.close_svg.setFixedSize(13, 13)
        self.close_svg.move(3, 3)
        self.close_svg.setStyleSheet("background: transparent; border: none;")
        self.close_btn.clicked.connect(self.close)

        # Применяем цвет
        for svg in [self.pin_svg, self.lock_svg, self.resize_svg, self.close_svg]:
            self.style_manager.apply_color_svg(svg, strength=0.90)

        # Добавляем в layout
        layout.addStretch()
        for btn in [self.pin_btn, self.lock_btn, self.resize_btn, self.close_btn]:
            layout.addWidget(btn)

        return title_bar

    def create_main_buttons(self, vertical=False):
        widget = QWidget()
        widget.setStyleSheet("background: transparent;")
        layout_class = QVBoxLayout if vertical else QHBoxLayout
        buttons_layout = layout_class(widget)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(0)

        buttons_config = {
            'power_btn': {'icon': self.power_path, 'tooltip': 'Выключить Компьютер', 'action': self.shutdown_system},
            'settings_btn': {'icon': self.settings_path, 'tooltip': 'Открыть настройки', 'action': self.open_settings},
            'scrn_folder_btn': {'icon': self.camera_path, 'tooltip': 'Открыть папку скриншотов',
                                'action': self.assistant.open_folder_screenshots},
            'link_btn': {'icon': self.shortcut_path, 'tooltip': 'Открыть папку с ярлыками',
                         'action': self.assistant.open_folder_shortcuts},
            'open_main_btn': {'icon': self.open_main_path, 'tooltip': 'Развернуть основное окно',
                              'action': self.open_main_window}
        }

        for btn_name, config in buttons_config.items():
            btn = QPushButton()
            btn.setFixedSize(40, 40)
            btn.setToolTip(config['tooltip'])
            btn.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    border: none;
                }
                QPushButton:hover {
                    background: rgba(60, 60, 60, 150);
                    border-radius: 5px;
                }
            """)
            svg = QSvgWidget(config['icon'], btn)
            svg.setFixedSize(30, 30)
            svg.move(5, 5)
            self.buttons_data[btn_name] = {'button': btn, 'svg': svg}
            self.style_manager.apply_color_svg(svg, strength=0.90)
            btn.clicked.connect(config['action'])
            setattr(self, btn_name, btn)
            buttons_layout.addWidget(btn)

        if vertical:
            buttons_layout.addStretch()

        return widget

    def create_audio_controls(self):
        widget = QWidget()
        widget.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 5, 0, 0)
        layout.setSpacing(0)

        player_config = {
            'prev_btn': {'icon': self.prev_track, 'tooltip': 'Предыдущий трек', 'action': self.prev_track_action},
            'pause_btn': {'icon': self.pause_track, 'tooltip': 'Пауза', 'action': self.pause_track_action},
            'next_btn': {'icon': self.next_track, 'tooltip': 'Следующий трек', 'action': self.next_track_action}
        }

        layout.addStretch()
        for btn_name, config in player_config.items():
            btn = QPushButton()
            btn.setFixedSize(20, 20)
            btn.setToolTip(config['tooltip'])
            btn.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    border: none;
                }
                QPushButton:hover {
                    background: rgba(60, 60, 60, 150);
                }
            """)
            svg = QSvgWidget(config['icon'], btn)
            svg.setFixedSize(18, 18)
            svg.move(1, 1)
            self.player_buttons[btn_name] = {'button': btn, 'svg': svg}
            self.style_manager.apply_color_svg(svg, strength=0.90)
            btn.clicked.connect(config['action'])
            setattr(self, btn_name, btn)
            layout.addWidget(btn, alignment=Qt.AlignCenter)

        return widget

    def create_sensors_tab(self):
        """Создаёт вкладку с датчиками (CPU, GPU, RAM)"""
        widget = QWidget()
        widget.setObjectName("SensorsTab")
        widget.setStyleSheet("background: transparent; color: white;")

        layout = QGridLayout(widget)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # Заголовки
        cpu_label = QLabel("CPU")
        gpu_label = QLabel("GPU")
        ram_label = QLabel("RAM")

        for label in [cpu_label, gpu_label, ram_label]:
            label.setStyleSheet("font-weight: bold; color: #ddd;")
            label.setAlignment(Qt.AlignCenter)

        layout.addWidget(cpu_label, 0, 0, Qt.AlignCenter)
        layout.addWidget(gpu_label, 0, 1, Qt.AlignCenter)
        layout.addWidget(ram_label, 0, 2, Qt.AlignCenter)

        # CPU датчики
        self.cpu_temp_label = QLabel("🌡--°C")
        self.cpu_core_label = QLabel("📈--%")
        self.cpu_watt_label = QLabel("⚡--W")
        self.cpu_clock_label = QLabel("⚙--МГц")

        layout.addWidget(self.cpu_temp_label, 1, 0, Qt.AlignCenter)
        layout.addWidget(self.cpu_core_label, 2, 0, Qt.AlignCenter)
        layout.addWidget(self.cpu_watt_label, 3, 0, Qt.AlignCenter)
        layout.addWidget(self.cpu_clock_label, 4, 0, Qt.AlignCenter)

        # GPU датчики
        self.gpu_temp_label = QLabel("🌡--°C")
        self.gpu_core_label = QLabel("📈--%")
        self.gpu_watt_label = QLabel("⚡--W")
        self.gpu_clock_label = QLabel("⚙--МГц")

        layout.addWidget(self.gpu_temp_label, 1, 1, Qt.AlignCenter)
        layout.addWidget(self.gpu_core_label, 2, 1, Qt.AlignCenter)
        layout.addWidget(self.gpu_watt_label, 3, 1, Qt.AlignCenter)
        layout.addWidget(self.gpu_clock_label, 4, 1, Qt.AlignCenter)

        # RAM датчики
        self.ram_usage_label = QLabel("💾--Гб")
        self.ram_over_label = QLabel("💾--Гб")

        layout.addWidget(self.ram_usage_label, 1, 2, Qt.AlignCenter)
        layout.addWidget(self.ram_over_label, 2, 2, Qt.AlignCenter)

        # Пустые ячейки для выравнивания
        empty = QLabel("")
        layout.addWidget(empty, 3, 2)
        layout.addWidget(QLabel(""), 4, 2)

        return widget

    def create_tabs_widget(self):
        widget = QWidget()
        widget.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Кнопки вкладок
        tab_buttons = QWidget()
        tab_buttons_layout = QHBoxLayout(tab_buttons)
        tab_buttons_layout.setContentsMargins(5, 0, 5, 0)
        tab_buttons_layout.setSpacing(5)

        self.btn_sensors = QPushButton("Датчики")
        self.btn_notes = QPushButton("Заметки")

        tab_style = """
            QPushButton {
                background: rgba(50, 50, 50, 150);
                color: white;
                border: none;
                border-radius: 5px;
                padding: 5px;
                font-size: 12px;
            }
            QPushButton:hover {
                background: rgba(70, 70, 70, 200);
            }
            QPushButton:pressed {
                background: rgba(40, 110, 230, 200);
            }
        """
        for btn in [self.btn_sensors, self.btn_notes]:
            btn.setStyleSheet(tab_style)
            btn.setCheckable(True)
            btn.setFixedHeight(25)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        tab_buttons_layout.addWidget(self.btn_sensors)
        tab_buttons_layout.addWidget(self.btn_notes)

        # Контент вкладок
        self.tab_content = QStackedWidget()
        self.tab_content.setStyleSheet("background: transparent;")

        # Вкладка датчиков
        self.sensors_tab = self.create_sensors_tab()
        self.tab_content.addWidget(self.sensors_tab)

        # Вкладка заметок
        self.notes_tab = QTextEdit("Тут можно писать заметки")
        self.notes_tab.setAlignment(Qt.AlignLeft)
        self.notes_tab.setStyleSheet("""
            QTextEdit {
                border: none;
                font-size: 12px;
                color: white;
            }
        """)
        self.tab_content.addWidget(self.notes_tab)

        # Таймер автосохранения
        self.notes_save_timer = QTimer(self)
        self.notes_save_timer.setSingleShot(True)
        self.notes_save_timer.timeout.connect(self.save_notes)
        self.notes_tab.textChanged.connect(self.start_notes_save_timer)

        # Собираем
        layout.addWidget(tab_buttons)
        layout.addWidget(self.tab_content)

        # Подключаем переключение
        self.btn_sensors.clicked.connect(lambda: self.switch_tab(0))
        self.btn_notes.clicked.connect(lambda: self.switch_tab(1))

        return widget

    def relayout_buttons(self, vertical=False):
        """Перестраивает layout кнопок между горизонтальным и вертикальным расположением"""
        try:
            content_layout = self.content_layout
            index = content_layout.indexOf(self.buttons_widget)

            if index != -1:
                item = content_layout.takeAt(index)
                if item:
                    old_widget = item.widget()
                    if old_widget:
                        old_widget.deleteLater()
            self.buttons_widget = self.create_main_buttons(vertical=vertical)

            audio_index = content_layout.indexOf(self.audio_widget)
            if audio_index != -1:
                # Вставляем после audio_widget
                content_layout.insertWidget(audio_index + 1, self.buttons_widget, alignment=Qt.AlignCenter)
            else:
                content_layout.addWidget(self.buttons_widget, alignment=Qt.AlignCenter)
        except Exception as e:
            debug_logger.error(f"Ошибка в relayout_buttons: {e}")

    # Методы для перемещения окна
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and not getattr(self, 'is_locked', False):
            self.old_pos = event.globalPos()
            self.is_dragging = False  # Флаг для отслеживания начала перемещения

    def mouseMoveEvent(self, event):
        if hasattr(self, 'old_pos') and self.old_pos and not getattr(self, 'is_locked', False):
            delta = event.globalPos() - self.old_pos
            new_pos = self.pos() + delta
            self.move(new_pos)
            self.old_pos = event.globalPos()

            # Сохраняем текущие координаты в переменные (но не в файл)
            self.current_position = {"x": new_pos.x(), "y": new_pos.y()}
            self.is_dragging = True

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.is_dragging:
            # Сохраняем окончательные координаты в файл
            state = self.state_manager.load_state()
            state["window_position"] = self.current_position
            self.state_manager.save_state(state)
            self.is_dragging = False

    def load_window_state(self):
        """Загружает состояние окна из JSON"""
        state = self.state_manager.load_state()
        pos = state["window_position"]
        size = state["window_size"]
        self.move(QPoint(pos["x"], pos["y"]))
        self.resize(QSize(size["width"], size["height"]))

    def pin_widget(self):
        try:
            self.is_pinned = not self.is_pinned

            # Получаем текущие флаги (без изменения)
            flags = self.windowFlags()

            # Обновляем флаг поверх окон
            if self.is_pinned:
                flags |= Qt.WindowStaysOnTopHint
                self.pin_svg.load(self.active_pin_path)
                self.style_manager.apply_color_svg(self.pin_svg, strength=0.95)
            else:
                flags &= ~Qt.WindowStaysOnTopHint
                self.pin_svg.load(self.pin_path)

            # Применяем флаги и обновляем окно
            self.setWindowFlags(flags)
            self.show()  # Обязательно после изменения флагов!

            self.state_manager.save_window_state(self)
        except Exception as e:
            debug_logger.error(f"Ошибка {e}")

    def update_ui_for_mode(self):
        """Обновляет UI в зависимости от режима"""
        if self.is_compact:
            self.tab_widget.hide()
            self.relayout_buttons(vertical=True)
            # self.buttons_widget.setFixedWidth(80)
            self.audio_widget.show()
            self.clock_mini.show()
            self.clock_widget.hide()

        else:
            self.tab_widget.show()
            self.relayout_buttons(vertical=False)

            self.audio_widget.hide()
            self.clock_mini.hide()
            self.clock_widget.show()

    def resize_widget(self):
        """Переключает между компактным и нормальным режимом"""
        try:
            self.save_notes()
            if hasattr(self, 'current_tab') and self.current_tab == 0:
                self.close_sensors()
            if self.animation and self.animation.state() == QPropertyAnimation.Running:
                self.animation.stop()

            old_geometry = self.geometry()
            new_width = 90 if not self.is_compact else 240
            new_height = 300

            # Сохраняем правый край
            right_edge = old_geometry.x() + old_geometry.width()
            new_x = right_edge - new_width
            # Переключаем состояние
            self.is_compact = not self.is_compact

            # Обновляем UI
            self.update_ui_for_mode()

            # Анимация
            self.animation = QPropertyAnimation(self, b"geometry")
            self.animation.setDuration(200)
            self.animation.setStartValue(old_geometry)
            self.animation.setEndValue(QRect(new_x, old_geometry.y(), new_width, new_height))
            self.animation.setEasingCurve(QEasingCurve.OutBack)

            def on_animation_finished():
                self.save_state()
                if not self.is_compact:
                    self.switch_tab(1)

            self.animation.finished.connect(on_animation_finished)
            self.animation.start()

        except Exception as e:
            debug_logger.error(f"Ошибка в resize_widget: {e}")

    def shutdown_system(self):
        """Выключает компьютер после подтверждения"""
        try:
            # Создаем кастомное окно вместо QMessageBox
            confirm_dialog = QDialog(self)
            confirm_dialog.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
            confirm_dialog.setFixedSize(110, 80)

            # Основной контейнер
            main_layout = QVBoxLayout(confirm_dialog)
            main_layout.setContentsMargins(5, 5, 5, 5)
            main_layout.setSpacing(5)

            # Текст (с автоматическим переносом слов)
            label = QLabel("Выключить комп?")  # Укороченный текст для маленького окна
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("""
                QLabel {
                    color: white;
                    font-size: 12px;
                    padding: 0;
                }
            """)
            main_layout.addWidget(label)

            # Контейнер для кнопок
            btn_container = QWidget()
            btn_layout = QHBoxLayout(btn_container)
            btn_layout.setContentsMargins(0, 0, 0, 0)
            btn_layout.setSpacing(5)

            # Кнопки
            yes_btn = QPushButton("Да")
            no_btn = QPushButton("Нет")

            # Стилизация кнопок
            btn_style = """
                QPushButton {
                    background: rgba(70, 70, 70, 160);
                    color: white;
                    border: 1px solid #555;
                    border-radius: 3px;
                    padding: 3px;
                    width: 20px;
                    height: 20px;
                    font-size: 12px;
                }
            """
            yes_btn.setStyleSheet(btn_style)
            no_btn.setStyleSheet(btn_style)

            btn_layout.addStretch()
            btn_layout.addWidget(yes_btn)
            btn_layout.addWidget(no_btn)
            btn_layout.addStretch()

            main_layout.addWidget(btn_container)

            # Обработчики кнопок
            yes_btn.clicked.connect(lambda: confirm_dialog.accept())
            no_btn.clicked.connect(lambda: confirm_dialog.reject())

            # Показываем и ждем результат
            if confirm_dialog.exec_() == QDialog.Accepted:
                try:
                    shutdown_windows()
                except Exception as e:
                    debug_logger.error(f"Ошибка выключения: {e}")

        except Exception as e:
            debug_logger.error(f"Ошибка диалога: {e}")

    def open_settings(self):
        """Переключатель для основного окна и настроек"""
        try:
            if self.assistant.isVisible():
                if not (hasattr(self.assistant, 'mutable_panel') and self.assistant.mutable_panel.isVisible()):
                    self.assistant.open_main_settings()
                else:
                    self.assistant.hide_widget()
                    self.assistant.custom_hide()
            else:
                # Если основное окно скрыто - показываем его
                self.assistant.show()

                # Открываем настройки, только если они еще не открыты
                if not (hasattr(self.assistant, 'mutable_panel') and self.assistant.mutable_panel.isVisible()):
                    self.assistant.open_main_settings()
        except Exception as e:
            debug_logger.error(f"Ошибка при переключении окна настроек: {e}")

    def open_main_window(self):
        try:
            if self.assistant.isVisible():
                self.assistant.custom_hide()
            else:
                self.assistant.show()
        except Exception as e:
            debug_logger.error(f"Ошибка при открытии основного окна через виджет {e}")

    def lock_state(self):
        """Переключает возможность перетаскивания виджета"""
        try:
            if not hasattr(self, 'lock_btn') or not hasattr(self, 'lock_svg'):
                return
            self.is_locked = not getattr(self, 'is_locked', False)

            # Меняем иконку в зависимости от состояния
            if hasattr(self, 'lock_svg'):
                if self.is_locked:
                    # Меняем на иконку "разблокировки"
                    self.lock_svg.load(self.unlock_path)
                    self.lock_btn.setToolTip("Включить перемещение")
                    self.lock_title_widget(state=False)
                    if hasattr(self, "audio_widget") and hasattr(self, "buttons_widget"):
                        self.audio_widget.setEnabled(False)
                        self.buttons_widget.setEnabled(False)
                    if hasattr(self, "tab_widget"):
                        self.tab_widget.setEnabled(False)
                else:
                    # Возвращаем стандартную иконку
                    self.lock_svg.load(self.lock_path)
                    self.lock_btn.setToolTip("Отключить перемещение")
                    self.lock_title_widget()
                    if hasattr(self, "audio_widget") and hasattr(self, "buttons_widget"):
                        self.audio_widget.setEnabled(True)
                        self.buttons_widget.setEnabled(True)
                    if hasattr(self, "tab_widget"):
                        self.tab_widget.setEnabled(True)

                # Применяем цвет к SVG
                self.style_manager.apply_color_svg(self.lock_svg, strength=0.95)

            # Сохраняем состояние блокировки
            self.save_state()
        except Exception as e:
            debug_logger.error(f"Ошибка в методе lock_state: {e}")

    def save_state(self):
        self.state_manager.save_window_state(self)

    def lock_title_widget(self, state=True):
        if hasattr(self, "title_bar"):
            # Пропускаем только lock_btn
            if state:
                for btn in self.title_bar.findChildren(QPushButton):
                    if btn != self.lock_btn:
                        btn.setEnabled(True)
            else:
                for btn in self.title_bar.findChildren(QPushButton):
                    if btn != self.lock_btn:
                        btn.setEnabled(False)

    def prev_track_action(self):
        try:
            controller.previous_track()
        except Exception as e:
            debug_logger.error(f"Ошибка при переключении трека: {e}")

    def pause_track_action(self):
        try:
            self.is_paused = not self.is_paused
            svg = self.player_buttons['pause_btn']['svg']
            btn = self.player_buttons['pause_btn']['button']
            # Меняем иконку в зависимости от состояния
            if self.is_paused:
                svg.load(self.play_track)
                btn.setToolTip("Продолжить")
                self.is_paused = True
            else:
                # Возвращаем стандартную иконку
                svg.load(self.pause_track)
                btn.setToolTip("Пауза")
                self.is_paused = False

            # Применяем цвет к SVG
            self.style_manager.apply_color_svg(svg, strength=0.95)
            controller.play_pause()
        except Exception as e:
            debug_logger.error(f"Ошибка при попытке поставить паузу: {e}")

    def next_track_action(self):
        try:
            controller.next_track()
        except Exception as e:
            debug_logger.error(f"Ошибка при переключении трека: {e}")

    def closeEvent(self, event):
        # Сохраняем состояние виджета
        self.save_state()
        self.save_notes()

        if hasattr(self, 'wmi_conn'):
            self.close_ohm()
        # Проверяем состояние главного окна
        if self.assistant:
            if self.assistant.isVisible() and not self.assistant.isMinimized():
                # Если главное окно видимо и не свернуто - просто закрываем виджет
                pass
            else:
                # В противном случае вызываем специальный метод
                self.assistant.restore_and_hide()

        super().closeEvent(event)

    def apply_styles(self):
        try:
            self.styles = self.style_manager.load_styles()

            # Применяем стили к текущему окну
            style_sheet = ""
            for widget, styles in self.styles.items():
                if widget.startswith("Q"):  # Для стандартных виджетов (например, QMainWindow, QPushButton)
                    selector = widget
                else:  # Для виджетов с objectName (например, TitleBar, CentralWidget)
                    selector = f"#{widget}"

                style_sheet += f"{selector} {{\n"
                for prop, value in styles.items():
                    style_sheet += f"    {prop}: {value};\n"
                style_sheet += "}\n"

            # Устанавливаем стиль для текущего окна
            self.setStyleSheet(style_sheet)
        except Exception as e:
            debug_logger.error(f"Ошибка в методе apply_styles: {e}")

    def update_colors(self):
        self.styles = self.style_manager.load_styles()
        for name, data in self.player_buttons.items():
            self.style_manager.apply_color_svg(data['svg'], strength=0.90)
        for name, data in self.buttons_data.items():
            self.style_manager.apply_color_svg(data['svg'], strength=0.90)

        self.style_manager.apply_color_svg(self.pin_svg, strength=0.95)
        self.style_manager.apply_color_svg(self.lock_svg, strength=0.95)

    def set_default_sensor_values(self):
        """Устанавливает значения по умолчанию для всех датчиков"""
        self.cpu_temp_label.setText("🌡--°C")
        self.cpu_core_label.setText("📈--%")
        self.cpu_watt_label.setText("⚡--W")
        self.cpu_clock_label.setText("⚙️--МГц")
        self.gpu_temp_label.setText("🌡--°C")
        self.gpu_core_label.setText("📈--%")
        self.gpu_watt_label.setText("⚡--W")
        self.gpu_clock_label.setText("⚙️--МГц")
        self.ram_usage_label.setText("💾--Гб")
        self.ram_over_label.setText("💾--Гб")

    # def switch_tab(self, index):
    #     if not hasattr(self, 'tab_content'):
    #         return
    #     self.tab_content.setCurrentIndex(index)
    #     self.current_tab = index
    #
    #     # Сброс стилей
    #     for btn in [self.btn_sensors, self.btn_notes]:
    #         btn.setStyleSheet("""
    #             QPushButton {
    #                 background: rgba(50, 50, 50, 150);
    #                 color: white;
    #                 border: none;
    #                 border-radius: 5px;
    #                 padding: 5px;
    #                 font-size: 12px;
    #             }
    #             QPushButton:hover {
    #                 background: rgba(70, 70, 70, 200);
    #             }
    #         """)
    #     # Активный
    #     active_btn = [self.btn_sensors, self.btn_notes][index]
    #     active_btn.setStyleSheet("""
    #         QPushButton {
    #             background: rgba(40, 110, 230, 200);
    #             color: white;
    #             border: none;
    #             border-radius: 5px;
    #             padding: 5px;
    #             font-size: 12px;
    #         }
    #     """)
    #
    #     if index == 0:
    #         self.open_sensors()
    #     else:
    #         self.close_sensors()

    def switch_tab(self, index):
        """Переключает вкладки и подсвечивает активную кнопку"""
        if not hasattr(self, 'tab_content'):
            return

        if hasattr(self, 'current_tab') and self.current_tab == 0:
            self.close_sensors()

            # Переключаем вкладку
        self.tab_content.setCurrentIndex(index)
        self.tab_content.show()
        self.current_tab = index  # Запоминаем текущую вкладку

        if index == 0:
            self.set_default_sensor_values()
            self.tab_content.setCurrentIndex(index)
            self.tab_content.show()
            self.open_sensors()  # Затем запускаем обновление
        else:
            self.tab_content.setCurrentIndex(index)
            self.tab_content.show()

        # Сбрасываем стиль всех кнопок
        for btn in [self.btn_sensors, self.btn_notes]:
            btn.setStyleSheet("""
                QPushButton {
                    background: rgba(50, 50, 50, 150);
                    color: white;
                    border: none;
                    border-radius: 5px;
                    padding: 5px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background: rgba(70, 70, 70, 200);
                }
            """)

        # Подсвечиваем активную кнопку
        active_btn = [self.btn_sensors, self.btn_notes][index]
        active_btn.setStyleSheet("""
            QPushButton {
                background: rgba(40, 110, 230, 200);
                color: white;
                border: none;
                border-radius: 5px;
                padding: 5px;
                font-size: 12px;
            }
        """)

    def update_time(self):
        current_time = QTime.currentTime()
        if self.is_compact:
            time_str = current_time.toString("hh:mm")
            self.clock_mini.setText(time_str)
        else:
            time_str = current_time.toString("hh:mm:ss")
            self.clock_title.setText(time_str)

    def open_sensors(self):
        try:
            self.sensors_tab.show()
            self.init_ohm()
            self.sensor_timer.start(1000)
        except Exception as e:
            debug_logger.error(f"Ошибка в open_sensors: {e}")

    def close_sensors(self):
        try:
            self.sensor_timer.stop()
            self.close_ohm()
        except Exception as e:
            debug_logger.error(f"Ошибка в close_sensors: {e}")

    def init_ohm(self):
        """Запускает OpenHardwareMonitor и подключается к WMI"""
        try:
            self.set_default_sensor_values()
            self.assistant.load_settings()
            self.ohm_path = self.assistant.ohm_path
            # 1. Проверка существования файла OHM
            if not os.path.exists(self.ohm_path):
                error_msg = (f"Файл OpenHardwareMonitor не найден\n"
                             f"Укажите корректный путь к файлу в настройках")
                self.assistant.show_notification_message(error_msg)
                debug_logger.error(error_msg)
                return  # Прекращаем выполнение если файла нет

            # 2. Проверка уже запущенного процесса
            tasks = subprocess.check_output('tasklist', shell=True).decode('cp866', errors='ignore')
            if "OpenHardwareMonitor.exe" in tasks:
                debug_logger.debug("OpenHardwareMonitor уже запущен")
                return

            # 3. Запуск с повышенными правами через PowerShell
            debug_logger.debug(f"Попытка запуска OHM: {self.ohm_path}")
            result = subprocess.run([
                "powershell",
                "-Command",
                f'Start-Process "{self.ohm_path}" -WindowStyle Hidden -Verb runAs'

            ],
                shell=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)

            # 4. Проверка результата запуска
            if result.returncode != 0:
                error_msg = f"Ошибка запуска OHM (код {result.returncode}): {result.stderr.decode('cp866')}"
                debug_logger.error(error_msg)
                return

            # 5. Подключение к WMI (с задержкой для инициализации OHM)
            try:
                self.wmi_conn = wmi.WMI(namespace=self.ohm_namespace)
                debug_logger.debug("Успешное подключение к WMI")
                self.update_sensors()
            except wmi.x_wmi as wmi_error:
                debug_logger.error(f"Ошибка подключения к WMI: {str(wmi_error)}")

        except subprocess.CalledProcessError as proc_error:
            debug_logger.error(f"Ошибка при проверке процессов: {str(proc_error)}")
        except Exception as e:
            debug_logger.error(f"Неожиданная ошибка в init_ohm: {str(e)}", exc_info=True)

    def close_ohm(self):
        """Завершает OHM"""
        try:
            result = subprocess.run(
                ['taskkill', '/IM', "OpenHardwareMonitor.exe", '/F'],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW,
                text=True,
                encoding='cp866'
            )
            debug_logger.info(f"Вывод subprocess:{result.stdout.strip()}. Ошибки:{result.stderr.strip()}")
            debug_logger.info(f"Процесс успешно завершен.")
        except subprocess.CalledProcessError:
            debug_logger.error(f"Не удалось завершить процесс.")
        except Exception as e:
            debug_logger.error(f"Ошибка: {e}")

    def update_sensors(self):
        """Обновляет данные датчиков"""
        if not hasattr(self, 'wmi_conn'):
            self.set_default_sensor_values()
            return

        try:
            sensors = self.wmi_conn.Sensor()

            # CPU данные
            cpu_temp = next(
                (round(float(s.Value)) for s in sensors
                 if s.SensorType == 'Temperature' and (
                         'CPU Core' in s.Name or 'CPU Package' in s.Name or 'Core #' in s.Name)),
                '--'
            )

            cpu_core = next(
                (round(float(s.Value)) for s in sensors
                 if s.SensorType == 'Load' and 'CPU Total' in s.Name),
                '--'
            )

            cpu_watt = next(
                (round(float(s.Value)) for s in sensors
                 if s.SensorType == 'Power' and 'CPU Package' in s.Name),
                '--'
            )

            cpu_clock = next(
                (round(float(s.Value)) for s in sensors
                 if s.SensorType == 'Clock' and 'CPU Core #1' in s.Name),
                '--'
            )

            # GPU данные
            gpu_temp = next(
                (round(float(s.Value)) for s in sensors
                 if s.SensorType == 'Temperature' and 'GPU Core' in s.Name),
                '--'
            )

            gpu_core = next(
                (round(float(s.Value)) for s in sensors
                 if s.SensorType == 'Load' and 'GPU Core' in s.Name),
                '--'
            )

            gpu_watt = next(
                (round(float(s.Value)) for s in sensors
                 if s.SensorType == 'Power' and 'GPU' in s.Name),
                '--'
            )

            gpu_clock = next(
                (round(float(s.Value)) for s in sensors
                 if s.SensorType == 'Clock' and 'GPU Core' in s.Name),
                '--'
            )

            # RAM данные
            ram_usage = next(
                (round(float(s.Value), 2) for s in sensors
                 if s.SensorType == 'Data' and 'Used Memory' in s.Name),
                '--'
            )

            ram_free = next(
                (round(float(s.Value), 2) for s in sensors
                 if s.SensorType == 'Data' and 'Available Memory' in s.Name),
                '--'
            )

            ram_total = round(float(ram_usage + ram_free))

            # Обновляем UI
            self.cpu_temp_label.setText(f"🌡{cpu_temp}°C")
            self.cpu_core_label.setText(f"📈{cpu_core}%")
            self.cpu_watt_label.setText(f"⚡{cpu_watt}W")
            self.cpu_clock_label.setText(f"⚙️{cpu_clock}МГц")

            self.gpu_temp_label.setText(f"🌡{gpu_temp}°C")
            self.gpu_core_label.setText(f"📈{gpu_core}%")
            self.gpu_watt_label.setText(f"⚡{gpu_watt}W")
            self.gpu_clock_label.setText(f"⚙️{gpu_clock}МГц")

            self.ram_usage_label.setText(f"💾{ram_usage}Гб")
            self.ram_over_label.setText(f"💾{ram_total}Гб")

        except Exception as e:
            debug_logger.error(f"Sensor update failed: {e}")

    def start_notes_save_timer(self):
        """Запускает таймер автосохранения при изменении текста"""
        self.notes_save_timer.start(5000)  # 5 секунд

    def save_notes(self):
        """Сохраняет заметки в файл"""
        try:
            notes_text = self.notes_tab.toPlainText()
            os.makedirs(os.path.dirname(self.notes_file), exist_ok=True)
            with open(self.notes_file, 'w', encoding='utf-8') as f:
                f.write(notes_text)
        except Exception as e:
            debug_logger.error(f"Ошибка сохранения заметок: {e}")

    def load_notes(self):
        """Загружает заметки из файла"""
        try:
            if os.path.exists(self.notes_file):
                with open(self.notes_file, 'r', encoding='utf-8') as f:
                    notes_text = f.read()
                    self.notes_tab.setPlainText(notes_text)
        except Exception as e:
            debug_logger.error(f"Ошибка загрузки заметок: {e}")
            self.notes_tab.setPlainText("Тут можно писать заметки")

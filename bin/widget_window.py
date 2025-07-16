import json
import os
import subprocess

import wmi
from PyQt5.QtGui import QFont, QFontDatabase
from PyQt5.QtSvg import QSvgWidget
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QHBoxLayout, \
    QDialog, QLabel, QGridLayout, QStackedWidget, QSizePolicy, QTextEdit
from PyQt5.QtCore import Qt, QPoint, QSize, QPropertyAnimation, QRect, QTimer, QTime

from bin.apply_color_methods import ApplyColor
from bin.function_list_main import shutdown_windows
from bin.signals import color_signal
from logging_config import debug_logger
from path_builder import get_path


class WindowStateManager:
    def __init__(self, config_path=get_path("user_settings", "widget_state.json")):
        self.config_path = config_path
        self.default_state = {
            "window_position": {"x": 100, "y": 100},
            "window_size": {"width": 220, "height": 300},
            "is_compact": False,
            "is_pinned": False
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

        return state


class SmartWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.assistant = parent
        self.buttons_data = {}
        color_signal.color_changed.connect(self.update_colors)
        self.notes_file = get_path("user_settings", "notes.txt")
        self.camera_path = get_path("bin", "icons", "camera.svg")
        self.power_path = get_path("bin", "icons", "power.svg")
        self.open_main_path = get_path("bin", "icons", "open_main.svg")
        self.settings_path = get_path("bin", "icons", "settings.svg")
        self.shortcut_path = get_path("bin", "icons", "shortcut.svg")
        self.style_manager = ApplyColor(self)
        self.color_path = self.style_manager.color_path
        self.styles = self.style_manager.load_styles()

        self.pin_path = get_path("bin", "icons", "push_pin.svg")
        self.lock_path = get_path("bin", "icons", "lock.svg")
        self.close_path = get_path("bin", "icons", "cancel.svg")
        self.resize_path = get_path("bin", "icons", "resize.svg")
        self.ohm_path = self.assistant.ohm_path
        self.ohm_namespace = "root\\OpenHardwareMonitor"
        self.font_id = QFontDatabase.addApplicationFont(
            get_path("bin", "fonts", "Digital Numbers", "DigitalNumbers-Regular.ttf"))
        self.font_family = QFontDatabase.applicationFontFamilies(self.font_id)[0]
        self.timer_clock = QTimer(self)
        self.timer_clock.timeout.connect(self.update_time)
        # Менеджер состояния окна
        self.state_manager = WindowStateManager()
        self.apply_styles()
        # self.load_and_apply_styles()

        saved_state = self.state_manager.apply_state(self)

        base_flags = Qt.FramelessWindowHint | Qt.Tool
        if self.is_compact:
            self.compact_ui()
        else:
            self.init_ui()
            self.switch_tab(1)
        if self.is_pinned:
            base_flags |= Qt.WindowStaysOnTopHint

        self.setWindowFlags(base_flags)
        # Для перемещения окна
        self.old_pos = None

        self.sensor_timer = QTimer()
        self.sensor_timer.timeout.connect(self.update_sensors)

        self.current_tab = 1

    def init_ui(self):
        # Настройки окна
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("""
            QWidget {
                background: rgba(30, 30, 30, 180);
                border-radius: 10px;
            }
        """)
        self.setFixedSize(240, 300)

        # Главный layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Создаем контейнер для всего содержимого (включая заголовок)
        container = QWidget()
        container.setObjectName("MainContainer")
        container.setStyleSheet("""
            #MainContainer {
                background: rgba(30, 30, 30, 180);
                border-radius: 10px;
            }
        """)

        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        # Панель заголовка (теперь часть основного окна)
        title_bar = QWidget()
        title_bar.setObjectName("TitleBar")
        title_bar.setFixedHeight(30)
        title_bar.setStyleSheet("""
            #TitleBar {
                background: transparent;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
                border-bottom: 1px solid rgba(70, 70, 70, 100);
            }
        """)

        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(2, 0, 2, 0)
        title_layout.setSpacing(2)

        self.clock_widget = QWidget()
        self.clock_widget.setStyleSheet("background: transparent;")
        clock_layout = QHBoxLayout(self.clock_widget)
        clock_layout.setContentsMargins(5, 0, 5, 0)

        self.time_clock_tab = QLabel()
        self.time_clock_tab.setAlignment(Qt.AlignCenter)
        self.time_clock_tab.setStyleSheet("""
                QLabel {
                    color: white;
                    background: transparent;
                    font-size: 12px;
                    padding: 0 5px;
                }
            """)

        # Устанавливаем шрифт
        self.clock_font = QFont(self.font_family, 12)  # Уменьшаем размер шрифта для заголовка
        self.time_clock_tab.setFont(self.clock_font)

        clock_layout.addWidget(self.time_clock_tab)
        title_layout.addWidget(self.clock_widget)

        self.timer_clock.start(1000)
        self.update_time()

        # Добавляем кнопки в заголовок
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
        self.pin_btn.clicked.connect(self.pin_widget)

        self.pin_svg = QSvgWidget(self.pin_path, self.pin_btn)
        self.pin_svg.setFixedSize(13, 13)
        self.pin_svg.move(3, 3)
        self.pin_svg.setStyleSheet("background: transparent; border: none;")

        self.lock_btn = QPushButton()
        self.lock_btn.setFixedSize(20, 20)
        self.lock_btn.setToolTip("Запомнить положение виджета")
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
        self.lock_btn.clicked.connect(self.save_state)

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
        self.resize_btn.clicked.connect(self.resize_widget)
        self.resize_svg = QSvgWidget(self.resize_path, self.resize_btn)
        self.resize_svg.setFixedSize(13, 13)
        self.resize_svg.move(3, 3)
        self.resize_svg.setStyleSheet("background: transparent; border: none;")

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
        self.close_btn.clicked.connect(self.close)
        self.close_svg = QSvgWidget(self.close_path, self.close_btn)
        self.close_svg.setFixedSize(13, 13)
        self.close_svg.move(3, 3)
        self.close_svg.setStyleSheet("background: transparent; border: none;")

        # Добавляем элементы в заголовок
        title_layout.addStretch()
        title_layout.addWidget(self.pin_btn)
        title_layout.addWidget(self.lock_btn)
        title_layout.addWidget(self.resize_btn)
        title_layout.addWidget(self.close_btn)

        # Основная область с кнопками
        content_widget = QWidget()
        content_widget.setObjectName("ContentWidget")
        content_widget.setStyleSheet("""
            #ContentWidget {
                background: transparent;
                border-bottom-left-radius: 10px;
                border-bottom-right-radius: 10px;
            }
        """)

        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(10, 10, 10, 10)
        content_layout.setSpacing(5)

        # Кнопки с иконками
        buttons_widget = QWidget()
        buttons_widget.setStyleSheet("background: transparent;")
        buttons_layout = QHBoxLayout(buttons_widget)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(5)

        # Настройки кнопок
        buttons_config = {
            'power_btn': {
                'icon': self.power_path,
                'tooltip': 'Выключить Компьютер',
                'action': self.shutdown_system
            },
            'settings_btn': {
                'icon': self.settings_path,
                'tooltip': 'Открыть настройки',
                'action': self.open_settings
            },
            'scrn_folder_btn': {
                'icon': self.camera_path,
                'tooltip': 'Открыть папку скриншотов',
                'action': self.assistant.open_folder_screenshots
            },
            'link_btn': {
                'icon': self.shortcut_path,
                'tooltip': 'Открыть папку с ярлыками',
                'action': self.assistant.open_folder_shortcuts
            },
            'open_main_btn': {
                'icon': self.open_main_path,
                'tooltip': 'Развернуть основное окно',
                'action': self.open_main_window
            }
        }

        # Создаем кнопки
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
                    background: rgba(60, 60, 60, 100);
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

        buttons_layout.addStretch()

        # Собираем все вместе
        content_layout.addWidget(buttons_widget)

        container_layout.addWidget(title_bar)
        container_layout.addWidget(content_widget)

        main_layout.addWidget(container)

        # ===== Создаем виджет с вкладками =====
        self.tab_widget = QWidget()
        self.tab_widget.setStyleSheet("background: transparent;")
        self.tab_layout = QVBoxLayout(self.tab_widget)
        self.tab_layout.setContentsMargins(0, 0, 0, 0)
        self.tab_layout.setSpacing(0)

        # --- Верхняя строка с кнопками-вкладками ---
        self.tab_buttons = QWidget()
        self.tab_buttons.setStyleSheet("background: transparent;")
        self.tab_buttons_layout = QHBoxLayout(self.tab_buttons)
        self.tab_buttons_layout.setContentsMargins(5, 0, 5, 0)
        self.tab_buttons_layout.setSpacing(5)

        # Кнопки вкладок
        self.btn_sensors = QPushButton("Датчики")
        self.btn_notes = QPushButton("Заметки")

        # Настройка стилей кнопок
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

        # Добавляем кнопки в layout
        self.tab_buttons_layout.addWidget(self.btn_sensors)
        self.tab_buttons_layout.addWidget(self.btn_notes)

        # --- Контейнер для содержимого вкладок ---
        self.tab_content = QStackedWidget()
        self.tab_content.setStyleSheet("background: transparent;")

        # ===== 1. Вкладка "Датчики" (CPU/GPU/RAM) =====
        self.sensors_tab = QWidget()
        self.sensors_tab.setStyleSheet("background: transparent; color: white;")
        self.sensors_layout = QGridLayout(self.sensors_tab)
        self.sensors_layout.setContentsMargins(5, 5, 5, 5)
        self.sensors_layout.setSpacing(5)

        # Добавляем заголовки
        self.sensors_layout.addWidget(QLabel("CPU"), 0, 0, Qt.AlignCenter)
        self.sensors_layout.addWidget(QLabel("GPU"), 0, 1, Qt.AlignCenter)
        self.sensors_layout.addWidget(QLabel("RAM"), 0, 2, Qt.AlignCenter)

        # Добавляем датчики
        self.cpu_temp_label = QLabel("🌡--°C")
        self.cpu_core_label = QLabel("📈--%")
        self.cpu_watt_label = QLabel("⚡--W")
        self.cpu_clock_label = QLabel("⚙--МГц")
        self.gpu_temp_label = QLabel("🌡--°C")
        self.gpu_core_label = QLabel("📈--%")
        self.gpu_watt_label = QLabel("⚡--W")
        self.gpu_clock_label = QLabel("⚙--МГц")
        self.ram_usage_label = QLabel("💾--Гб")
        self.ram_over_label = QLabel("💾--Гб")

        self.sensors_layout.addWidget(self.cpu_temp_label, 1, 0, Qt.AlignCenter)
        self.sensors_layout.addWidget(self.cpu_core_label, 2, 0, Qt.AlignCenter)
        self.sensors_layout.addWidget(self.cpu_watt_label, 3, 0, Qt.AlignCenter)
        self.sensors_layout.addWidget(self.cpu_clock_label, 4, 0, Qt.AlignCenter)
        self.sensors_layout.addWidget(self.gpu_temp_label, 1, 1, Qt.AlignCenter)
        self.sensors_layout.addWidget(self.gpu_core_label, 2, 1, Qt.AlignCenter)
        self.sensors_layout.addWidget(self.gpu_watt_label, 3, 1, Qt.AlignCenter)
        self.sensors_layout.addWidget(self.gpu_clock_label, 4, 1, Qt.AlignCenter)
        self.sensors_layout.addWidget(self.ram_usage_label, 1, 2, Qt.AlignCenter)
        self.sensors_layout.addWidget(self.ram_over_label, 2, 2, Qt.AlignCenter)

        # ===== 2. Вкладка "Заметки" =====
        self.notes_tab = QTextEdit("Тут можно писать заметки")
        self.notes_tab.setAlignment(Qt.AlignLeft)
        self.notes_tab.setStyleSheet("""
            QTextEdit {
                border: none;
                font-size: 12px;
                color: white;
            }
        """)
        self.load_notes()  # Загружаем сохраненные заметки

        # Таймер для автосохранения (каждые 5 секунд при изменениях)
        self.notes_save_timer = QTimer(self)
        self.notes_save_timer.setSingleShot(True)
        self.notes_save_timer.timeout.connect(self.save_notes)
        self.notes_tab.textChanged.connect(self.start_notes_save_timer)

        # Добавляем вкладки в StackedWidget
        self.tab_content.addWidget(self.sensors_tab)
        self.tab_content.addWidget(self.notes_tab)

        # Собираем всё в tab_layout
        self.tab_layout.addWidget(self.tab_buttons)
        self.tab_layout.addWidget(self.tab_content)
        self.tab_content.hide()

        # Добавляем вкладки в основной layout
        content_layout.addWidget(self.tab_buttons)  # Кнопки вкладок
        content_layout.addWidget(self.tab_content)  # Контент
        content_layout.addStretch()

        # ===== Подключаем кнопки =====
        self.btn_sensors.clicked.connect(lambda: self.switch_tab(0))
        self.btn_notes.clicked.connect(lambda: self.switch_tab(1))

        container_layout.addStretch()

        # Для перетаскивания окна
        title_bar.mousePressEvent = self.mousePressEvent
        title_bar.mouseMoveEvent = self.mouseMoveEvent

    def compact_ui(self):
        # Настройки окна
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("""
                    QWidget {
                        background: rgba(30, 30, 30, 180);
                        border-radius: 10px;
                    }
                """)
        self.setFixedSize(80, 250)

        # Главный layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Создаем контейнер для всего содержимого (включая заголовок)
        container = QWidget()
        container.setObjectName("MainContainer")
        container.setStyleSheet("""
                    #MainContainer {
                        background: rgba(30, 30, 30, 180);
                        border-radius: 10px;
                    }
                """)

        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        # Панель заголовка (теперь часть основного окна)
        title_bar = QWidget()
        title_bar.setObjectName("TitleBar")
        title_bar.setFixedHeight(30)
        title_bar.setStyleSheet("""
                    #TitleBar {
                        background: transparent;
                        border-top-left-radius: 10px;
                        border-top-right-radius: 10px;
                        border-bottom: 1px solid rgba(70, 70, 70, 100);
                    }
                """)

        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(2, 0, 2, 0)
        title_layout.setSpacing(2)

        # Добавляем кнопки в заголовок
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
        self.pin_btn.clicked.connect(self.pin_widget)

        self.pin_svg = QSvgWidget(self.pin_path, self.pin_btn)
        self.pin_svg.setFixedSize(13, 13)
        self.pin_svg.move(3, 3)
        self.pin_svg.setStyleSheet("background: transparent; border: none;")

        self.lock_btn = QPushButton()
        self.lock_btn.setFixedSize(20, 20)
        self.lock_btn.setToolTip("Запомнить положение виджета")
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
        self.lock_btn.clicked.connect(self.save_state)

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
        self.resize_btn.clicked.connect(self.resize_widget)
        self.resize_svg = QSvgWidget(self.resize_path, self.resize_btn)
        self.resize_svg.setFixedSize(13, 13)
        self.resize_svg.move(3, 3)
        self.resize_svg.setStyleSheet("background: transparent; border: none;")

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
        self.close_btn.clicked.connect(self.close)
        self.close_svg = QSvgWidget(self.close_path, self.close_btn)
        self.close_svg.setFixedSize(13, 13)
        self.close_svg.move(3, 3)
        self.close_svg.setStyleSheet("background: transparent; border: none;")

        # Добавляем элементы в заголовок
        title_layout.addWidget(self.pin_btn)
        title_layout.addWidget(self.lock_btn)
        title_layout.addWidget(self.resize_btn)
        title_layout.addWidget(self.close_btn)

        # Основная область с кнопками
        content_widget = QWidget()
        content_widget.setObjectName("ContentWidget")
        content_widget.setStyleSheet("""
                    #ContentWidget {
                        background: transparent;
                        border-bottom-left-radius: 10px;
                        border-bottom-right-radius: 10px;
                    }
                """)

        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(10, 10, 10, 10)
        content_layout.setSpacing(5)

        self.time_clock_tab = QLabel()
        self.time_clock_tab.setAlignment(Qt.AlignCenter)
        self.time_clock_tab.setStyleSheet("background: transparent; font-size: 14px; color: white;")

        self.clock_font = QFont(self.font_family, 30)
        self.time_clock_tab.setFont(self.clock_font)
        self.timer_clock.start(1000)
        self.update_time()

        content_layout.addWidget(self.time_clock_tab)

        # Кнопки с иконками
        buttons_widget = QWidget()
        buttons_widget.setStyleSheet("background: transparent;")
        buttons_layout = QVBoxLayout(buttons_widget)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(5)

        # Настройки кнопок
        buttons_config = {
            'power_btn': {
                'icon': self.power_path,
                'tooltip': 'Выключить Компьютер',
                'action': self.shutdown_system
            },
            'settings_btn': {
                'icon': self.settings_path,
                'tooltip': 'Открыть настройки',
                'action': self.open_settings
            },
            'scrn_folder_btn': {
                'icon': self.camera_path,
                'tooltip': 'Открыть папку скриншотов',
                'action': self.assistant.open_folder_screenshots
            },
            'link_btn': {
                'icon': self.shortcut_path,
                'tooltip': 'Открыть папку с ярлыками',
                'action': self.assistant.open_folder_shortcuts
            },
            'open_main_btn': {
                'icon': self.open_main_path,
                'tooltip': 'Развернуть основное окно',
                'action': self.open_main_window
            }
        }

        # Создаем кнопки
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
                            background: rgba(60, 60, 60, 100);
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
            buttons_layout.addWidget(btn, alignment=Qt.AlignCenter)

        buttons_layout.addStretch()

        # Собираем все вместе
        content_layout.addWidget(buttons_widget)
        content_layout.addStretch()

        container_layout.addWidget(title_bar)
        container_layout.addWidget(content_widget)

        main_layout.addWidget(container)

        # Для перетаскивания окна
        title_bar.mousePressEvent = self.mousePressEvent
        title_bar.mouseMoveEvent = self.mouseMoveEvent

    # Методы для перемещения окна
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.old_pos = event.globalPos()

    def mouseMoveEvent(self, event):
        if self.old_pos:
            delta = event.globalPos() - self.old_pos
            self.move(self.pos() + delta)
            self.old_pos = event.globalPos()

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
            else:
                flags &= ~Qt.WindowStaysOnTopHint

            # Применяем флаги и обновляем окно
            self.setWindowFlags(flags)
            self.show()  # Обязательно после изменения флагов!

            self.state_manager.save_window_state(self)
        except Exception as e:
            debug_logger.error(f"Ошибка {e}")

    def resize_widget(self):
        try:
            self.save_notes()
            # Останавливаем анимацию, если она активна
            if hasattr(self, 'animation') and self.animation.state() == QPropertyAnimation.Running:
                self.animation.stop()
            # Сохраняем текущую геометрию
            old_geometry = self.geometry()

            if hasattr(self, 'wmi_conn'):
                self.close_ohm()

            # Переключаем состояние
            self.is_compact = not getattr(self, 'is_compact', False)

            # Сохраняем текущее состояние pinned перед очисткой UI
            current_pinned_state = getattr(self, 'is_pinned', False)

            # Определяем новые размеры
            if self.is_compact:
                new_width, new_height = 80, 250  # Compact размер
            else:
                new_width, new_height = 240, 300  # Normal размер

            # Вычисляем новую позицию (сохраняем правый край)
            new_x = old_geometry.right() - new_width
            new_y = old_geometry.top()

            # Полностью очищаем текущий UI
            self.clear_ui()

            # Создаем новый UI в зависимости от состояния
            if self.is_compact:
                self.compact_ui()
            else:
                self.init_ui()

            # Восстанавливаем состояние pinned
            self.is_pinned = current_pinned_state
            if self.is_pinned:
                flags = self.windowFlags() | Qt.WindowStaysOnTopHint
                self.setWindowFlags(flags)
                self.show()

            # Создаем анимацию
            self.animation = QPropertyAnimation(self, b"geometry")
            self.animation.setDuration(50)
            self.animation.setStartValue(old_geometry)
            self.animation.setEndValue(QRect(new_x, new_y, new_width, new_height))

            # Запускаем анимацию
            self.animation.start()
        except Exception as e:
            debug_logger.error(f"Ошибка в методе resize_widget: {e}")

    def clear_ui(self):
        if hasattr(self, 'sensor_timer') and self.sensor_timer.isActive():
            self.sensor_timer.stop()

        if hasattr(self, 'timer_clock') and self.timer_clock.isActive():
            self.timer_clock.stop()

        # Закрываем WMI-соединение
        if hasattr(self, 'wmi_conn'):
            self.close_ohm()
        # Удаляем все дочерние виджеты и очищаем ссылки
        for child in self.findChildren(QWidget):
            if child != self:
                child.deleteLater()

        # Очищаем ссылки на основные элементы
        for attr in ['pin_btn', 'lock_btn', 'resize_btn', 'close_btn',
                     'pin_svg', 'lock_svg', 'resize_svg', 'close_svg',
                     'tab_widget', 'tab_content']:
            if hasattr(self, attr):
                delattr(self, attr)

        # Удаляем текущий layout
        if self.layout():
            QWidget().setLayout(self.layout())

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
        try:
            self.assistant.show()
            self.assistant.open_main_settings()
        except Exception as e:
            debug_logger.error(f"Ошибка при открытии окна настроек через виджет {e}")

    def open_main_window(self):
        try:
            self.assistant.show()
        except Exception as e:
            debug_logger.error(f"Ошибка при открытии основного окна через виджет {e}")

    def save_state(self):
        self.state_manager.save_window_state(self)

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
        for name, data in self.buttons_data.items():
            self.style_manager.apply_color_svg(data['svg'], strength=0.90)

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
            self.time_clock_tab.setText(time_str)
        else:
            time_str = current_time.toString("hh:mm:ss")
            self.time_clock_tab.setText(time_str)

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

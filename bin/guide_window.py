import os
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve, QUrl, QPoint
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import QDialog, QWidget, QVBoxLayout, QPushButton, QLabel, QHBoxLayout, QFrame, QSizePolicy
from path_builder import get_path
from logging_config import debug_logger


class GuideWindow(QDialog):
    """
    Класс отрисовки окна с кнопками, которые открывают гайды
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.assistant = parent
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setFixedSize(450, self.assistant.height())

        # Анимации
        self.pos_animation = QPropertyAnimation(self, b"pos")
        self.pos_animation.setDuration(300)
        self.pos_animation.setEasingCurve(QEasingCurve.OutCubic)

        self.opacity_animation = QPropertyAnimation(self, b"windowOpacity")
        self.opacity_animation.setDuration(300)

        # Список видео
        path_guides = get_path("bin", "guides")
        self.video_files = {
            "Создание команд": f"{path_guides}/new_commands.mp4",
            "Настройки и опции": f"{path_guides}/settings.mp4",
            "Скачивание и установка обновления": f"{path_guides}/update.mp4"
        }

        self.init_ui()
        self.setup_animation()

        # Подключаем сигнал родителя к слоту закрытия
        if parent and hasattr(parent, "close_child_windows"):
            parent.close_child_windows.connect(self.hide_with_animation)

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
        # Основной контейнер
        self.container = QWidget(self)
        self.container.setObjectName("GuideContainer")
        self.container.setGeometry(0, 0, self.width(), self.height())

        # Кастомный заголовок
        self.title_bar = QWidget(self.container)
        self.title_bar.setObjectName("TitleBar")
        self.title_bar.setGeometry(0, 0, self.container.width(), 35)

        title_bar_layout = QHBoxLayout(self.title_bar)
        title_bar_layout.setContentsMargins(10, 5, 10, 5)

        self.title_label = QLabel("Обучение")
        title_bar_layout.addWidget(self.title_label)
        title_bar_layout.addStretch()

        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(25, 25)
        self.close_btn.setObjectName("CloseButton")
        self.close_btn.clicked.connect(self.hide_with_animation)
        title_bar_layout.addWidget(self.close_btn)

        # Основной layout под заголовком
        main_layout = QVBoxLayout(self.container)
        main_layout.setContentsMargins(0, 40, 0, 0)  # Отступ под заголовком
        main_layout.setSpacing(20)

        # Контейнер для кнопок
        buttons_frame = QFrame()
        buttons_frame.setObjectName("ButtonsFrame")  # (если нужно стилизовать через CSS)

        # Горизонтальный layout
        buttons_layout = QVBoxLayout(buttons_frame)
        buttons_layout.setSpacing(10)
        buttons_layout.setContentsMargins(10, 10, 10, 10)  # Отступы от краёв

        # Добавляем кнопки
        for btn_text, video_path in self.video_files.items():
            btn = QPushButton(btn_text)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            btn.clicked.connect(lambda _, path=video_path: self.open_video_in_default_player(path))
            buttons_layout.addWidget(btn)
        main_layout.addWidget(buttons_frame)
        main_layout.addStretch()

    def open_video_in_default_player(self, video_path):
        """Открывает видео во внешнем плеере"""
        full_path = get_path(video_path)

        if os.path.exists(full_path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(full_path))
        else:
            debug_logger.error(f"Файл не найден: {full_path}")
            self.parent().show_message("Видео не найдено", "Ошибка", "error")

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

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            if self.opacity_animation.state() != QPropertyAnimation.Running:
                self.hide_with_animation()
            event.accept()
        else:
            super().keyPressEvent(event)

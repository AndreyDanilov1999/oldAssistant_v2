import os

from PyQt5.QtGui import QPainter
from PyQt5.QtWidgets import (QApplication, QStyleOptionSlider, QStyle, QGraphicsView, QGraphicsScene)
from PyQt5.QtCore import Qt, QPropertyAnimation, QUrl, QTimer, QSizeF
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QPushButton, QHBoxLayout,
                             QWidget, QLabel, QFrame, QSlider, QSizePolicy)
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QGraphicsVideoItem
from logging_config import debug_logger
from path_builder import get_path


class ClickableGraphicsView(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setMouseTracking(True)  # Включаем отслеживание мыши

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if hasattr(self.parent_window, 'toggle_play_pause'):
                self.parent_window.toggle_play_pause()
                # Показываем overlay с иконкой паузы/воспроизведения
                if self.parent_window.video_player.state() == QMediaPlayer.PlayingState:
                    self.parent_window.show_overlay("⏸")
                else:
                    self.parent_window.show_overlay("▶")
        super().mousePressEvent(event)


class SeekableSlider(QSlider):
    def __init__(self, parent=None):
        super().__init__(parent)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if not self.width():
                return super().mousePressEvent(event)

            opt = QStyleOptionSlider()
            self.initStyleOption(opt)
            sr = self.style().subControlRect(
                QStyle.CC_Slider, opt, QStyle.SC_SliderHandle, self
            )

            if not sr.contains(event.pos()):
                new_value = self.minimum() + ((event.x() / self.width()) * (self.maximum() - self.minimum()))
                self.setValue(int(new_value))
            super().mousePressEvent(event)
        else:
            super().mousePressEvent(event)


class GuideWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.muted = False
        self.previous_volume = 100
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)

        screen_geometry = QApplication.desktop().screenGeometry()
        self.setFixedSize(screen_geometry.width() - 100, screen_geometry.height() - 100)

        # Анимации
        self.opacity_animation = QPropertyAnimation(self, b"windowOpacity")
        self.opacity_animation.setDuration(300)

        # Видеоресурсы
        path_guides = get_path("bin", "guides")
        self.video_files = {
            "Создание команд": f"{path_guides}/new_commands.mp4",
            "Настройки и прочие опции": f"{path_guides}/settings.mp4",
        }

        self.init_ui()
        self.setup_animation()
        self.preload_first_video()

    def setup_animation(self):
        parent_center = self.parent().geometry().center()
        self.move(parent_center.x() - self.width() // 2,
                  parent_center.y() - self.height() // 2)

    def init_ui(self):
        self.container = QWidget(self)
        self.container.setObjectName("GuideContainer")
        self.container.setGeometry(0, 0, self.width(), self.height())

        # Заголовок
        self.title_bar = QWidget(self.container)
        self.title_bar.setObjectName("TitleBar")
        self.title_bar.setGeometry(0, 0, self.container.width(), 40)
        title_bar_layout = QHBoxLayout(self.title_bar)
        title_bar_layout.setContentsMargins(10, 5, 10, 5)

        self.title_label = QLabel("Видео-гайды")
        title_bar_layout.addWidget(self.title_label)
        title_bar_layout.addStretch()

        self.close_btn = QPushButton("✕", self.title_bar)
        self.close_btn.setFixedSize(30, 30)
        self.close_btn.setObjectName("CloseButton")
        self.close_btn.clicked.connect(self.close)
        title_bar_layout.addWidget(self.close_btn)

        main_layout = QVBoxLayout(self.container)
        main_layout.setContentsMargins(0, 45, 0, 10)
        main_layout.setSpacing(10)

        # Кнопки выбора видео
        buttons_frame = QFrame()
        buttons_layout = QHBoxLayout(buttons_frame)
        buttons_layout.setSpacing(20)
        for btn_text, video_path in self.video_files.items():
            btn = QPushButton(btn_text, self)
            btn.setObjectName("GuideButton")
            btn.setFixedHeight(50)
            btn.setMinimumWidth(200)
            btn.clicked.connect(lambda _, path=video_path: self.play_video(path))
            buttons_layout.addWidget(btn)
        main_layout.addWidget(buttons_frame, alignment=Qt.AlignCenter)

        # Видеоплеер через QGraphicsView
        self.video_scene = QGraphicsScene(self)
        self.video_view = ClickableGraphicsView(self.container)
        self.video_view.setScene(self.video_scene)
        self.video_view.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.video_view.viewport().setAttribute(Qt.WA_TransparentForMouseEvents, False)
        # self.video_view.setMouseTracking(True)  # Включаем отслеживание мыши
        self.video_view.setFocusPolicy(Qt.StrongFocus)
        self.video_view.setStyleSheet("background: black;")
        self.video_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.video_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.video_view.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)

        self.video_item = QGraphicsVideoItem()
        self.video_scene.addItem(self.video_item)

        self.video_player = QMediaPlayer(self)
        self.video_player.setVideoOutput(self.video_item)

        # Overlay: значок воспроизведения/паузы по центру видео
        self.overlay_label = QLabel("▶", self.video_view)
        self.overlay_label.setAlignment(Qt.AlignCenter)
        self.overlay_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.overlay_label.setStyleSheet("""
            font-size: 60px;
            color: rgba(255, 255, 255, 200);
            background: rgba(0, 0, 0, 100);
            border-radius: 50px;
            padding: 20px;
        """)
        self.overlay_label.hide()

        # Элементы управления видео
        self.controls_frame = QFrame()
        controls_layout = QHBoxLayout(self.controls_frame)

        self.play_pause_btn = QPushButton("⏸")
        self.play_pause_btn.setFixedSize(40, 30)
        self.play_pause_btn.clicked.connect(self.toggle_play_pause)

        self.mute_btn = QPushButton("🔊")
        self.mute_btn.setFixedSize(40, 30)
        self.mute_btn.clicked.connect(self.toggle_mute)

        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(100)
        self.volume_slider.setFixedWidth(120)
        self.volume_slider.valueChanged.connect(self.set_volume)

        self.position_slider = SeekableSlider(Qt.Horizontal)
        self.position_slider.setRange(0, 0)
        self.position_slider.sliderMoved.connect(self.set_video_position)

        controls_layout.addWidget(self.play_pause_btn)
        controls_layout.addWidget(self.position_slider)
        controls_layout.addWidget(self.mute_btn)
        controls_layout.addWidget(self.volume_slider)

        self.close_video_btn = QPushButton("Закрыть видео")
        self.close_video_btn.setObjectName("CloseVideoButton")
        self.close_video_btn.setFixedHeight(50)
        self.close_video_btn.setMinimumWidth(200)
        self.close_video_btn.clicked.connect(self.hide_video)

        main_layout.addWidget(self.video_view)
        main_layout.addWidget(self.controls_frame)
        main_layout.addWidget(self.close_video_btn, alignment=Qt.AlignCenter)

        # Таймер для обновления позиции
        self.timer = QTimer(self)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.update_position)

        # Подписываемся на события медиаплеера
        self.video_player.stateChanged.connect(self.media_state_changed)
        self.video_player.positionChanged.connect(self.position_changed)
        self.video_player.durationChanged.connect(self.duration_changed)

        # Изначально скрываем видео-элементы
        self.hide_video()

    def preload_first_video(self):
        if self.video_files:
            first_video = next(iter(self.video_files.values()))
            self.video_player.setMedia(QMediaContent(QUrl.fromLocalFile(get_path(first_video))))

    def show_overlay(self, icon="⏸"):
        """Показывает overlay с нужной иконкой по центру видео"""
        self.overlay_label.setText(icon)
        self.overlay_label.adjustSize()

        # Центрируем текст по центру video_view
        x = (self.video_view.width() - self.overlay_label.width()) // 2
        y = (self.video_view.height() - self.overlay_label.height()) // 2
        self.overlay_label.move(x, y)
        self.overlay_label.show()

    def play_video(self, video_path):
        try:
            full_path = get_path(video_path)
            if os.path.exists(full_path):
                self.video_view.show()
                self.controls_frame.show()
                self.close_video_btn.show()

                self.video_player.setMedia(QMediaContent(QUrl.fromLocalFile(full_path)))
                self.video_item.setSize(QSizeF(self.video_view.size()))  # Размер под окно
                self.video_player.play()
                self.timer.start()
            else:
                self.parent().show_message(f"Видеофайл не найден: {video_path}", "Ошибка", "error")
        except Exception as e:
            debug_logger.error(f"Ошибка воспроизведения видео: {e}")
            self.parent().show_message(f"Ошибка воспроизведения видео: {e}", "Ошибка", "error")

    def hide_video(self):
        self.video_player.pause()
        self.video_view.hide()
        self.controls_frame.hide()
        self.close_video_btn.hide()
        self.timer.stop()

    def toggle_play_pause(self):
        if self.video_player.state() == QMediaPlayer.PlayingState:
            self.video_player.pause()
            self.play_pause_btn.setText("⏸")
            self.show_overlay("⏸")
        else:
            self.video_player.play()
            self.play_pause_btn.setText("⏸")
            self.overlay_label.hide()

    def set_video_position(self, position):
        self.video_player.setPosition(position)

    def update_position(self):
        self.position_slider.setValue(self.video_player.position())

    def media_state_changed(self, state):
        if state == QMediaPlayer.PlayingState:
            self.play_pause_btn.setText("⏸")
        else:
            self.play_pause_btn.setText("▶")

    def position_changed(self, position):
        self.position_slider.setValue(position)

    def duration_changed(self, duration):
        self.position_slider.setRange(0, duration)

    def set_volume(self, volume):
        if not self.muted:
            self.video_player.setVolume(volume)

    def toggle_mute(self):
        self.muted = not self.muted
        if self.muted:
            self.previous_volume = self.volume_slider.value()
            self.video_player.setVolume(0)
            self.volume_slider.setValue(0)
            self.mute_btn.setText("🔇")
        else:
            self.video_player.setVolume(self.previous_volume)
            self.volume_slider.setValue(self.previous_volume)
            self.mute_btn.setText("🔊")

    def showEvent(self, event):
        self.setWindowOpacity(0.0)
        self.raise_()
        self.opacity_animation.stop()
        self.opacity_animation.setStartValue(0.0)
        self.opacity_animation.setEndValue(1.0)
        self.opacity_animation.start()
        super().showEvent(event)

    def closeEvent(self, event):
        self.video_player.stop()
        self.timer.stop()
        event.ignore()
        self.hide_with_animation()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
        elif event.key() == Qt.Key_Space:
            self.toggle_play_pause()
        else:
            super().keyPressEvent(event)

    def hide_with_animation(self):
        self.opacity_animation.stop()
        self.opacity_animation.setStartValue(1.0)
        self.opacity_animation.setEndValue(0.0)
        try:
            self.opacity_animation.finished.disconnect()
        except TypeError:
            pass
        self.opacity_animation.finished.connect(self.do_hide)
        self.opacity_animation.start()

    def do_hide(self):
        self.hide()

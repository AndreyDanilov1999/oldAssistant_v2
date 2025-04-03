import keyboard

from logging_config import debug_logger


class AudioControl:
    """Класс для управления медиа через голосовые команды путем имитации нажатий на клавиатуру"""

    def play_pause(self):
        """Эмулировать нажатие клавиши воспроизведения/паузы"""
        keyboard.send('play/pause media')
        debug_logger.info("AudioControl - play/pause media")

    def next_track(self):
        """Эмулировать нажатие клавиши следующего трека"""
        keyboard.send('next track')
        debug_logger.info("AudioControl - next track media")

    def previous_track(self):
        """Эмулировать нажатие клавиши предыдущего трека"""
        keyboard.send('previous track')
        debug_logger.info("AudioControl - previous track media")

controller = AudioControl()


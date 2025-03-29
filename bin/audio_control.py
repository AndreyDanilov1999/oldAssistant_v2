import keyboard

class AudioControl:
    """Класс для управления медиа через голосовые команды путем имитации нажатий на клавиатуру"""

    def play_pause(self):
        """Эмулировать нажатие клавиши воспроизведения/паузы"""
        keyboard.send('play/pause media')

    def next_track(self):
        """Эмулировать нажатие клавиши следующего трека"""
        keyboard.send('next track')

    def previous_track(self):
        """Эмулировать нажатие клавиши предыдущего трека"""
        keyboard.send('previous track')

controller = AudioControl()


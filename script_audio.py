from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume


class AudioControl:
    def __init__(self):
        self.devices = AudioUtilities.GetSpeakers()
        self.interface = self.devices.Activate(
            IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        self.volume = cast(self.interface, POINTER(IAudioEndpointVolume))

    def set_volume(self, volume_level):
        """Установить уровень громкости (0.0 - 1.0)"""
        self.volume.SetMasterVolumeLevelScalar(volume_level, None)

    def mute(self):
        """Выключить звук"""
        self.volume.SetMute(1, None)

    def unmute(self):
        """Включить звук"""
        self.volume.SetMute(0, None)

    def play_pause(self):
        """Эмулировать нажатие клавиши воспроизведения/паузы"""
        from pynput.keyboard import Key, Controller
        keyboard = Controller()
        keyboard.press(Key.media_play_pause)
        keyboard.release(Key.media_play_pause)

    def next_track(self):
        """Эмулировать нажатие клавиши следующего трека"""
        from pynput.keyboard import Key, Controller
        keyboard = Controller()
        keyboard.press(Key.media_next)
        keyboard.release(Key.media_next)

    def previous_track(self):
        """Эмулировать нажатие клавиши предыдущего трека"""
        from pynput.keyboard import Key, Controller
        keyboard = Controller()
        keyboard.press(Key.media_previous)
        keyboard.release(Key.media_previous)


controller = AudioControl()


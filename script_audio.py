import pyautogui


class BrowserMusicControl:
    def __init__(self):
        pass

    def play_pause(self):
        pyautogui.press('playpause')

    def next_track(self):
        pyautogui.press('nexttrack')

    def previous_track(self):
        pyautogui.press('prevtrack')

# Инициализация контроллера воспроизведения музыки в браузере
controller = BrowserMusicControl()
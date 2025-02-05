import time
import keyboard

# help(keyboard)

# keyboard.send('next track')
# time.sleep(3)
# keyboard.send('play/pause media')
# time.sleep(3)
# keyboard.send('previous track')


def test(callback):
    """Функция для захвата нажатых клавиш и вывода их названия"""
    print(callback.name)

keyboard.hook(test)
keyboard.wait()
import simpleaudio as sa
import numpy as np

# Создание простого сигнала
sample_rate = 48000  # Частота дискретизации
duration = 30  # Длительность в секундах
t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
audio_data = np.sin(2 * np.pi * 65 * t)
audio_data = (audio_data * 32767).astype(np.int16)  # Преобразование в int16

# Воспроизведение аудио
play_obj = sa.play_buffer(audio_data, 1, 2, sample_rate)
play_obj.wait_done()
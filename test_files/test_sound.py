import simpleaudio as sa
import numpy as np

# Создание простого сигнала
sample_rate = 48000  # Частота дискретизации
duration = 30  # Длительность в секундах
new_frequency = 75  # Новая частота в Гц
volume_factor = 1  # Уменьшение громкости на 50%
t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
audio_data = np.sin(2 * np.pi * new_frequency * t)
audio_data = (audio_data * volume_factor * 32767).astype(np.int16)

# Воспроизведение аудио
play_obj = sa.play_buffer(audio_data, 1, 2, sample_rate)
play_obj.wait_done()
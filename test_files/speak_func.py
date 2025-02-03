# import torch
# import simpleaudio as sa
# import numpy as np
# from collections import OrderedDict
# from concurrent.futures import ThreadPoolExecutor
# import atexit

# Путь к скачанной модели
# model_path_ru = "G:\PycharmProjects\OldAssistant\model_ru"
# model_path_en = "G:\PycharmProjects\OldAssistant\model_en"

# # Загрузка модели Silero TTS
# model, example_text = torch.hub.load(repo_or_dir='snakers4/silero-models',
#                                      model='silero_tts',
#                                      language='ru',  # Язык модели
#                                      speaker='v4_ru')  # Голос
# model.to('cpu')  # Используем CPU
#
# # Инициализация пула потоков
# executor = ThreadPoolExecutor(max_workers=2)
#
# # Кэширование аудиоданных
# MAX_CACHE_SIZE = 50
# tts_cache = OrderedDict()
#
#
# def speaking(text):
#     if text in tts_cache:
#         audio_data = tts_cache[text]
#     else:
#         audio = model.apply_tts(text=text,
#                                 sample_rate=48000,
#                                 speaker='xenia',
#                                 put_accent=True,
#                                 put_yo=True)
#         audio_data = audio.numpy()
#         if audio_data.dtype != np.int16:
#             audio_data = (audio_data * 32767).astype(np.int16)
#
#         # Добавляем в кэш и удаляем старые записи, если кэш переполнен
#         tts_cache[text] = audio_data
#         if len(tts_cache) > MAX_CACHE_SIZE:
#             tts_cache.popitem(last=False)  # Удаляем самый старый элемент
#
#     play_obj = sa.play_buffer(audio_data, 1, 2, 48000)
#     play_obj.wait_done()
#
#
# def speak(text):
#     executor.submit(speaking, text)
#
# atexit.register(tts_cache.clear)
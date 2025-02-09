import sounddevice as sd
import numpy as np
import torch
import speech_recognition as sr
import random

# Загрузка модели Silero
model, example_text = torch.hub.load(repo_or_dir='snakers4/silero-models',
                                     model='silero_tts',
                                     language='ru',
                                     speaker='v3_1_ru')
model.to(torch.device('cpu'))  # Используйте 'cuda' вместо 'cpu', если у вас есть GPU

# Генерация аудио
def generate_audio(text):
    audio = model.apply_tts(text=text,
                            speaker='xenia',
                            sample_rate=48000)
    return audio

# Распознавание голосовых команд
def recognize_speech_from_mic():
    recognizer = sr.Recognizer()
    microphone = sr.Microphone()

    with microphone as source:
        print("Listening...")
        recognizer.adjust_for_ambient_noise(source)
        audio = recognizer.listen(source)

    try:
        print("Recognizing...")
        command = recognizer.recognize_google(audio, language="ru-RU")
        print(f"You said: {command}")
        return command
    except sr.UnknownValueError:
        print("Google Speech Recognition could not understand audio")
        return None
    except sr.RequestError as e:
        print(f"Could not request results from Google Speech Recognition service; {e}")
        return None

# Запись и воспроизведение аудио
def play_and_record(audio, sample_rate):
    audio_length = len(audio)
    audio_index = 0

    def callback(indata, outdata, frames, time, status):
        nonlocal audio_index
        if status:
            print(status)
        current_audio = audio[audio_index:audio_index + frames]
        if len(current_audio) < len(indata):
            current_audio = np.resize(current_audio, indata.shape)
        outdata[:] = indata + current_audio
        audio_index = (audio_index + frames) % audio_length

    with sd.Stream(samplerate=sample_rate, channels=1, callback=callback):
        print("Playing and recording... Press Ctrl+C to stop.")
        while True:
            pass

# Основной цикл
def main():
    while True:
        command = recognize_speech_from_mic()
        if command and "число" in command.lower():
            random_number = random.randint(1, 10)
            text = f"мне очень многое хочется рассказать тебе но... {random_number}"
            audio = generate_audio(text)
            audio = np.array(audio, dtype=np.float32).reshape(-1, 1)
            play_and_record(audio, 48000)

if __name__ == "__main__":
    main()


    def get_audio(self):
        """Преобразование речи с микрофона в текст."""
        model_path_ru = os.path.join(get_base_directory(), "model_ru")  # Используем правильный путь к модели
        model_path_en = os.path.join(get_base_directory(), "model_en")
        logger.info(f"Используются модели:  ru - {model_path_ru}; en - {model_path_en}")  # Логируем путь к модели

        try:
            # Преобразуем путь в UTF-8
            model_path_ru_utf8 = model_path_ru.encode("utf-8").decode("utf-8")
            model_path_en_utf8 = model_path_en.encode("utf-8").decode("utf-8")

            # Пытаемся загрузить модель
            model_ru = Model(model_path_ru_utf8)
            model_en = Model(model_path_en_utf8)
            logger.info("Модели успешно загружены.")  # Логируем успешную загрузку модели
        except Exception as e:
            # Логируем полный стек вызовов при ошибке
            logger.error(f"Ошибка при загрузке модели: {e}. Возможно путь содержит кириллицу.")
            return
        rec_ru = KaldiRecognizer(model_ru, 16000)
        rec_en = KaldiRecognizer(model_en, 16000)
        p = pyaudio.PyAudio()
        try:
            stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=512)
            stream.start_stream()
            # Переменная для объединенного результата
            combined_result = ""
            result_ru = ""
            result_en = ""

            while self.is_assistant_running:
                try:
                    # Чтение данных из аудиопотока
                    data = stream.read(256, exception_on_overflow=False)
                    if len(data) == 0:
                        break

                    # Распознавание с использованием русской модели
                    if rec_ru.AcceptWaveform(data):
                        result_ru = rec_ru.Result()
                        result_ru = result_ru[14:-3]  # Обрезаем результат для получения только текста
                        if result_ru:
                            # logger.info(f"Русский: {result_ru}")  # Логируем распознанный текст
                            combined_result += result_ru + " "  # Добавляем результат в общую переменную

                    # Распознавание с использованием английской модели
                    if rec_en.AcceptWaveform(data):
                        result_en = rec_en.Result()
                        result_en = result_en[14:-3]  # Обрезаем результат для получения только текста
                        if result_en:
                            # logger.info(f"Английский: {result_en}")  # Логируем распознанный текст
                            combined_result += result_en + " "  # Добавляем результат в общую переменную

                    if result_en:
                        logger.info(combined_result)

                    yield combined_result.strip().lower()
                    combined_result = ""
                    result_ru = ""
                    result_en = ""
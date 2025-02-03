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
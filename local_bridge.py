import asyncio
import tempfile
import os
import requests
import playsound
import speech_recognition as sr
from pydub import AudioSegment
from pydub.playback import play
import numpy as np
from io import BytesIO

class LocalAudioBridge:
    """Локальный мост для работы с микрофоном и динамиком (упрощенная версия)"""
    
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone(sample_rate=16000)
        
    async def receive_audio(self):
        """Записывает аудио с микрофона и возвращает AudioSegment"""
        print("🎤 Говори...")
        
        # Используем ваш рабочий код для записи
        def record_audio():
            with self.microphone as source:
                # Настраиваем микрофон
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                # Записываем с лимитом времени
                audio = self.recognizer.listen(source, phrase_time_limit=5)
                return audio
        
        # Запускаем запись в отдельном потоке
        loop = asyncio.get_event_loop()
        audio = await loop.run_in_executor(None, record_audio)
        
        if audio is None:
            return None
            
        # Преобразуем в AudioSegment
        wav_data = audio.get_wav_data()
        audio_segment = AudioSegment(
            data=wav_data,
            sample_width=2,  # 16-bit
            frame_rate=16000,
            channels=1
        )
        
        print("✅ Аудио записано")
        return audio_segment
    
    async def send_audio(self, audio_segment):
        """Воспроизводит аудио через динамик"""
        if audio_segment is None:
            return
            
        print("🔊 Воспроизвожу ответ...")
        
        # Используем ваш рабочий код для воспроизведения
        def play_audio():
            # Сохраняем во временный файл
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
                audio_segment.export(tmp.name, format="mp3")
                playsound.playsound(tmp.name)
                os.remove(tmp.name)
        
        # Запускаем воспроизведение в отдельном потоке
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, play_audio)
        print("✅ Воспроизведение завершено")

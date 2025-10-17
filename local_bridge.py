import asyncio
import pyaudio
import wave
import tempfile
import os
from pydub import AudioSegment
from pydub.playback import play
import numpy as np
from io import BytesIO

class LocalAudioBridge:
    """Локальный мост для работы с микрофоном и динамиком"""
    
    def __init__(self, sample_rate=16000, chunk_size=1024):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.audio = pyaudio.PyAudio()
        self.is_recording = False
        
    def __del__(self):
        if hasattr(self, 'audio'):
            self.audio.terminate()
    
    async def receive_audio(self):
        """Записывает аудио с микрофона и возвращает AudioSegment"""
        print("🎤 Говори...")
        
        # Настройки для записи
        stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.sample_rate,
            input=True,
            frames_per_buffer=self.chunk_size
        )
        
        frames = []
        self.is_recording = True
        
        # Записываем 3 секунды или до тишины
        silence_threshold = 500
        silence_duration = 0
        max_silence = 1.0  # секунды
        max_duration = 10.0  # максимальная длительность
        start_time = asyncio.get_event_loop().time()
        
        while self.is_recording:
            data = stream.read(self.chunk_size, exception_on_overflow=False)
            frames.append(data)
            
            # Проверяем уровень звука
            audio_data = np.frombuffer(data, dtype=np.int16)
            volume = np.sqrt(np.mean(audio_data**2))
            
            current_time = asyncio.get_event_loop().time()
            elapsed = current_time - start_time
            
            if volume < silence_threshold:
                silence_duration += self.chunk_size / self.sample_rate
                if silence_duration > max_silence and elapsed > 1.0:  # Минимум 1 секунда записи
                    break
            else:
                silence_duration = 0
                
            if elapsed > max_duration:
                break
                
            # Небольшая задержка для снижения нагрузки на CPU
            await asyncio.sleep(0.01)
        
        stream.stop_stream()
        stream.close()
        
        if not frames:
            return None
            
        # Преобразуем в AudioSegment
        audio_data = b''.join(frames)
        audio_segment = AudioSegment(
            data=audio_data,
            sample_width=2,  # 16-bit
            frame_rate=self.sample_rate,
            channels=1
        )
        
        print("✅ Аудио записано")
        return audio_segment
    
    async def send_audio(self, audio_segment):
        """Воспроизводит аудио через динамик"""
        if audio_segment is None:
            return
            
        print("🔊 Воспроизвожу ответ...")
        
        # Преобразуем AudioSegment в numpy array для воспроизведения
        def play_audio():
            play(audio_segment)
        
        # Запускаем воспроизведение в отдельном потоке
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, play_audio)
        print("✅ Воспроизведение завершено")
    
    def stop_recording(self):
        """Останавливает запись"""
        self.is_recording = False

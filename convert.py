import base64
import numpy as np
import asyncio
from pydub import AudioSegment
from io import BytesIO


async def mp3_to_wav(base64_mp3: str) -> np.ndarray:
    """Декодирует base64 mp3 и возвращает WAV в виде np.ndarray"""
    loop = asyncio.get_event_loop()
    
    # Декодируем base64 в байты
    mp3_bytes = base64.b64decode(base64_mp3)

    # Загружаем MP3 из BytesIO с помощью pydub
    def load_audio():
        audio = AudioSegment.from_file(BytesIO(mp3_bytes), format="mp3")
        audio = audio.set_channels(1).set_frame_rate(16000)  # downsample (если нужно)
        samples = np.array(audio.get_array_of_samples()).astype(np.float32)
        samples /= np.iinfo(audio.array_type).max  # нормализация от -1.0 до 1.0
        return samples

    wav_np = await loop.run_in_executor(None, load_audio)
    return wav_np


async def wav_to_mp3(wav_np: np.ndarray, sample_rate: int = 16000) -> BytesIO:
    """Кодирует WAV np.ndarray в MP3 и возвращает BytesIO, пригодный для FormData"""
    loop = asyncio.get_event_loop()

    # Преобразуем numpy обратно в AudioSegment
    def encode_audio():
        # Преобразуем -1.0..1.0 в int16
        int_samples = (wav_np * 32767).astype(np.int16)
        audio_segment = AudioSegment(
            int_samples.tobytes(),
            frame_rate=sample_rate,
            sample_width=2,  # 16 bit
            channels=1
        )
        buffer = BytesIO()
        audio_segment.export(buffer, format="mp3", bitrate="192k")
        buffer.seek(0)
        return buffer

    mp3_buffer = await loop.run_in_executor(None, encode_audio)
    return mp3_buffer


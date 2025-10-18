import asyncio
import speech_recognition as sr
from pydub import AudioSegment
from io import BytesIO
import tempfile
import playsound

class MessengerBridge:
    def __init__(self, sample_rate=16000):
        self.sample_rate = sample_rate
        self.recognizer = sr.Recognizer()
        self.mic = sr.Microphone(sample_rate=self.sample_rate)

    async def receive_audio(self):
        loop = asyncio.get_event_loop()
        print("🎤 Говорите...")
        audio = await loop.run_in_executor(None, self._listen)
        return AudioSegment(
            data=audio.get_wav_data(),
            sample_width=2,
            frame_rate=self.sample_rate,
            channels=1
        )

    def _listen(self):
        with self.mic as source:
            print("🎙️ Слушаю...")
            audio = self.recognizer.listen(source, phrase_time_limit=5)
        return audio

    async def send_audio(self, wav_audio):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            wav_audio.export(tmp.name, format="wav")
            tmp_path = tmp.name
        print("🔊 Проигрываю ответ...")
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, playsound.playsound, tmp_path)
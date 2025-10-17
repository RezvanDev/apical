import asyncio
from pydub import AudioSegment
from collections import deque

class SpeechSegmenter:
    def __init__(self, aggressiveness=3, sample_rate=16000, frame_duration=30, max_silence_ms=800):
        self.sample_rate = sample_rate
        self.frame_duration = frame_duration  # ms
        self.frame_size = int(sample_rate * frame_duration / 1000) * 2  # 16-bit audio
        self.max_silence_ms = max_silence_ms
        self.silence_duration = 0
        self.speech_buffer = deque()
        self.in_speech = False

        # Уровень энергии для определения речи (чем выше aggressiveness, тем выше порог)
        self.energy_threshold = {0: -45, 1: -40, 2: -35, 3: -30}.get(aggressiveness, -30)

    def is_speech(self, frame: bytes) -> bool:
        segment = AudioSegment(
            data=frame,
            sample_width=2,
            frame_rate=self.sample_rate,
            channels=1
        )
        # Измерим громкость
        return segment.dBFS > self.energy_threshold

    def reset(self):
        self.silence_duration = 0
        self.in_speech = False
        self.speech_buffer.clear()

    async def run(self, input_queue: asyncio.Queue, output_queue: asyncio.Queue):
        while True:
            audio_chunk = await input_queue.get()

            # Convert to raw audio (PCM 16-bit mono 16kHz)
            if isinstance(audio_chunk, AudioSegment):
                raw_audio = audio_chunk.set_frame_rate(self.sample_rate).set_channels(1).set_sample_width(2).raw_data
            else:
                raise ValueError("Expected AudioSegment")

            for i in range(0, len(raw_audio), self.frame_size):
                frame = raw_audio[i:i + self.frame_size]
                if len(frame) < self.frame_size:
                    continue

                is_speech = self.is_speech(frame)

                if is_speech:
                    self.silence_duration = 0
                    self.speech_buffer.append(frame)
                    self.in_speech = True
                else:
                    if self.in_speech:
                        self.silence_duration += self.frame_duration
                        if self.silence_duration < self.max_silence_ms:
                            self.speech_buffer.append(frame)
                        else:
                            # Речь закончилась
                            speech_bytes = b''.join(self.speech_buffer)
                            segment = AudioSegment(
                                data=speech_bytes,
                                sample_width=2,
                                frame_rate=self.sample_rate,
                                channels=1
                            )
                            await output_queue.put(segment)
                            self.reset()


import asyncio
import numpy as np
from typing import Dict
from io import BytesIO
from segmenter import SpeechSegmenter
from api import TTS_stream, STT
from convert import mp3_to_wav, wav_to_mp3
from agent import Agent
import importlib.util
import sys

segmenter=SpeechSegmenter()

# Импортируем локальный мост вместо мессенджер моста
try:
    from local_bridge import LocalAudioBridge
    bridge = LocalAudioBridge()
    print("✅ Используется локальный мост (микрофон + динамик)")
except ImportError:
    # Fallback на мессенджер мост если локальный недоступен
    module_name = "messenger_bridge"
    module_path = "/opt/audio_bridge_server/messenger_bridge.py"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    messenger_bridge = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = messenger_bridge
    spec.loader.exec_module(messenger_bridge)
    bridge = messenger_bridge.MessengerBridge()
    print("✅ Используется мессенджер мост")

async def receive_audio_stream(received_audio_wav_queue):
    while True:
        received_audio_wav = await bridge.receive_audio()
        print('wav received')
        await received_audio_wav_queue.put(received_audio_wav)

async def STT_stream(received_segments_wav_queue,client_messages_queue):
    while True:
        audio_segment_wav = await received_segments_wav_queue.get()
        audio_segment_mp3 = await wav_to_mp3(audio_segment_wav)

        client_message_text = await api.STT(audio_segment_mp3)
        await client_messages_queue.put(client_message_text)

async def llm_stream(client_messages_queue, agent_answer_chunks_queue, agent):
    while True:
        client_message = await client_messages_queue.get()
        await agent.generate_answer(client_message, agent_answer_chunks_queue)

async def update_text_chunks(agent_answer_chunks_queue, updated_text_chunks):
    while True:
        chunk = await agent_answer_chunks_queue.get()
        buf = ''
        spaces = 0
        if chunk == '':
           if buf != '': await updated_text_chunks.put(buf+'')
           await updated_text_chunks.put('')
        for word in chunk:
            buf += word
            if word == ' ': spaces = spaces + 1
            if spaces == 10:
                spaces = 0
                await updated_text_chunks.put(buf)
                buf = ''

async def send_audio_stream(generated_mp3_queue):
    while True:
        mp3_audio = await generated_mp3_queue.get()
        wav_audio = await mp3_to_wav(mp3_audio)
        await bridge.send_audio(wav_audio)
        
async def start_call(phone, service, state): 
    agent = Agent(state)
    received_audio_wav_queue = asyncio.Queue()
    received_segments_wav_queue = asyncio.Queue()
    client_messages_queue = asyncio.Queue()
    agent_answer_chunks_queue = asyncio.Queue
    updated_text_chunks = asyncio.Queue
    generated_mp3_queue = asyncio.Queue
    
    voice_id = 'yM93hbw8Qtvdma2wCnJG'
    print('start_call')
    await asyncio.gather(
        receive_audio_stream(received_audio_wav_queue),
        segmenter.run(received_audio_wav_queue,received_segments_wav_queue),
        STT_stream(received_segments_wav_queue,client_messages_queue),
        llm_stream(client_messages_queue, agent_answer_chunks_queue, agent),
        update_text_chunks(agent_answer_chunks_queue, updated_text_chunks),
        TTS_stream(voice_id, updated_text_chunks, generated_mp3_queue),
        send_audio_stream(generated_mp3_queue)
    )
    


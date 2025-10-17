import os
from aiohttp import ClientSession
from aiohttp_socks import ProxyConnector
import aiohttp
import websockets
import json
from dotenv import load_dotenv
from pathlib import Path

env_path = Path("../.env")
load_dotenv(dotenv_path=env_path)


OPENAI_PROXY          = os.getenv("OPENAI_PROXY")
OPENAI_API_URL        = "https://api.openai.com/v1/chat/completions"
OPENAI_API_KEY        = os.getenv("OPENAI_API_KEY")
ELEVEN_PROXY          = os.getenv("ELEVEN_PROXY")
ELEVEN_APIKEY         = os.getenv("ELEVEN_APIKEY")

async def STT(audio):
    connector = ProxyConnector.from_url(ELEVEN_PROXY)
    headers = {
        'xi-api-key':ELEVEN_APIKEY
    }
    form = FormData()
    form.add_field(
        name='file',
        value=audio,
        filename="audio.mp3",
        content_type='application/octet-stream'
    )
    form.add_field(
        name='model_id',
        value='scribe_v1'
    )
    url='https://api.elevenlabs.io/v1/speech-to-text'
    async with ClientSession(connector=connector, headers=headers) as session:
        async with session.post(url, data=form, ssl=True) as response:
            
            resp_data = await response.json()
            return resp_data['text']
    

async def TTS_stream(voice_id, chunk_queue, audio_queue):
    uri = f"wss://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream-input?enable_ssml_parsing=true&model_id=eleven_flash_v2_5&enable_logging=false" 
    
    connector = ProxyConnector.from_url(ELEVEN_PROXY)

    async with aiohttp.ClientSession(connector=connector) as session:
        async with session.ws_connect(uri) as websocket:
            params_string = json.dumps({
                "text": " ",
                "voice_settings": {
                    "speed": 1,
                    "stability": 0.5,
                    "similarity_boost": 0.8
                },
                "xi_api_key": ELEVEN_APIKEY
            }) 
            await websocket.send_str(params_string)

            while True: 
                    chunk = await chunk_queue.get()
                    request_string = json.dumps({"text": chunk}, ensure_ascii=False)
                    await websocket.send_str(request_string)
                    if chunk: continue
                 
                    while True:
                        msg = await websocket.receive()
            
                        
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            try:
                                data = json.loads(msg.data)
                                
                                audio = data.get("audio")
                                if not audio: return

                                await audio_queue.put(audio)
                            except json.JSONDecodeError:
                                print("Невалидный JSON:", msg.data)

                        elif msg.type == aiohttp.WSMsgType.ERROR:
                            print("Ошибка WebSocket:", msg)
                            await audio_queue.put(None)
                            return

async def openai_stream(messages, chunk_queue):
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }

    connector = ProxyConnector.from_url(OPENAI_PROXY)

    async with aiohttp.ClientSession(connector=connector) as session:
            payload = {
                "model": "gpt-4o",
                "messages": messages,
                "temperature": 0.7,
                "stream": True,
            }

            try:
                async with session.post(
                    OPENAI_API_URL,
                    headers=headers,
                    json=payload,
                    timeout=None
                ) as resp:
                    async for line in resp.content:                        
                        line = line.decode('utf-8').strip()

                        if line.startswith("data: "):
                            data = line.removeprefix("data: ").strip()
                            
                            if data == "[DONE]":                                
                                await chunk_queue.put('')
                                break
                            try:
                                parsed = json.loads(data)
                                delta = parsed["choices"][0]["delta"]
                                content = delta.get("content")
                                if content: await chunk_queue.put(content)
                                        
                            except Exception as e:
                                print(f"\n[ERROR] {e}")
            except Exception as e:
                print(f"[REQUEST ERROR] {e}")


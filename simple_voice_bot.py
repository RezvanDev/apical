import asyncio
import tempfile
import os
import requests
import playsound
import speech_recognition as sr
from api import openai_stream
from agent import Agent

# Ваш промпт для финансового агента
FINANCIAL_AGENT_PROMPT = {
    "messages": [{
        "role": "system",
        "content": (
            "Ты — голосовой финансовый агент по имени Максим. Не задавай вопрос чем я могу вам помоч, работай по скрипту ниже не задавай как ваш день и тд "
            "Твоя задача — вести естественный, доброжелательный разговор с клиентом, "
            "следуя сценарию ниже. Говори короткими фразами, с интонацией уверенности и участия. "
            "Главное — вызвать доверие, разговорить человека и получить согласие на отправку информации в WhatsApp. "
            "Не зачитывай сценарий дословно, а действуй по смыслу, как живой человек.\n\n"
            
            "=== СЦЕНАРИЙ ДИАЛОГА ГОЛОСОВОГО АГЕНТА ===\n"
            "Тематика: Финансы / Инвестиции / Помощь клиенту\n"
            "Цель: Разговорить клиента, вызвать доверие, выявить интерес, получить согласие на отправку информации\n\n"
            
            "1. Приветствие и установление контакта:\n"
            " - Агент: «Здравствуйте! Меня зовут Максим, я специалист технической поддержки. "
            "Подскажите, пожалуйста, как я могу к вам обращаться?»\n"
            " - Если клиент отвечает именем: «Очень приятно, рад знакомству.»\n"
            " - Если клиент спрашивает «кто вы?» или «зачем звоните?» — «Мы помогаем клиентам решать любые вопросы, "
            "связанные с финансами, платежами и личными инвестициями.»\n"
            " - Если клиент говорит «неудобно / не звоните / перезвоните» — «Не хотел вас отвлекать, "
            "но боюсь, что вы можете упустить кое-что важное.»\n\n"
            
            "2. Определение профиля клиента:\n"
            " - Агент: «Скажите, пожалуйста, вы сейчас работаете по найму, ведёте свой бизнес "
            "или рассматриваете варианты удалённого дохода?»\n"
            " - Если клиент работает → «Отлично. Многие сейчас задумываются, как сделать доход стабильнее "
            "и не зависеть от одной зарплаты.»\n"
            " - Если бизнес → «Замечательно! Часто обращаются клиенты вроде вас, обычно мы быстро находим общий язык.»\n"
            " - Если не работает / ищет доход → «Понимаю, иногда именно в такие периоды появляется возможность "
            "попробовать что-то новое — например, рассмотреть инструменты удалённого дохода без стартового капитала.»\n\n"
            
            "3. Выявление интереса:\n"
            " - Агент: «А вообще, вы когда-нибудь интересовались инвестициями или удалённым заработком? "
            "Например, криптовалютой, торговыми платформами или накопительными программами?»\n"
            " - Если клиент интересовался → «Отлично, значит, вы уже немного знакомы с темой. "
            "Я могу просто помочь вам разобраться, какие варианты реально работают.»\n"
            " - Если нет → «Всё в порядке. Я объясняю простыми словами, без сложных терминов, "
            "чтобы каждый понял, как управлять своими финансами.»\n"
            " - Если клиент не верит / пробовал / не получилось → «Мы проводим поэтапное обучение и доводим "
            "до результата каждого клиента.»\n\n"
            
            "4. Помощь и вовлечение:\n"
            " - Агент: «Моя задача — помочь вам сориентироваться, какие инструменты подойдут именно вам. "
            "Всё бесплатно и без обязательств: просто расскажу, какие сейчас работают решения для дополнительного дохода.»\n"
            " - Если клиент заинтересован → «Отлично. Мы сотрудничаем с лицензированными платформами, "
            "которые позволяют работать с инвестициями под контролем клиента — вы сами видите движение средств и можете "
            "остановить или вывести в любой момент.»\n"
            " - Если спрашивают «зачем звоните?» → «Чтобы объяснить, как можно оптимизировать личные финансы "
            "и получить консультацию по текущим возможностям без подписок или обязательств.»\n"
            " - Если клиент сомневается → «Понимаю, но тема финансов всегда актуальна, я просто делюсь полезной информацией.»\n\n"
            
            "5. Завершение разговора:\n"
            " - Агент: «Спасибо, что нашли минуту. Я могу отправить вам короткое сообщение на WhatsApp — "
            "там будет ссылка на материалы и рекомендации по личным финансам. Посмотрите в удобное время, договорились?»\n"
            " - Если клиент согласен → «Отлично, отправлю сразу после разговора. Если возникнут вопросы — просто напишите.»\n"
            " - Если клиент отказывается → «Хорошо, не проблема. Всего вам доброго, буду рад помочь позже.»\n\n"
            
            "=== ДОПОЛНИТЕЛЬНЫЕ ПОДСКАЗКИ ===\n"
            " - Говори спокойно, дружелюбно, с лёгкой улыбкой.\n"
            " - Не используй сложные финансовые термины.\n"
            " - Если клиент проявляет интерес — развивай диалог вопросами.\n"
            " - Если сомневается — мягко успокой и предложи просто ознакомиться с информацией."
        )
    }]
}

class SimpleVoiceBot:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone(sample_rate=16000)
        self.agent = Agent(FINANCIAL_AGENT_PROMPT)
        
    async def listen_and_transcribe(self):
        """Слушает микрофон и возвращает текст"""
        print("🎤 Говори...")
        
        def record_audio():
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = self.recognizer.listen(source, phrase_time_limit=5)
                return audio
        
        # Записываем аудио
        loop = asyncio.get_event_loop()
        audio = await loop.run_in_executor(None, record_audio)
        
        print("🕓 Распознаю...")
        
        # Распознаем речь через OpenAI Whisper
        def transcribe():
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                tmp.write(audio.get_wav_data())
                tmp_path = tmp.name
            
            url = "https://api.openai.com/v1/audio/transcriptions"
            headers = {"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}"}
            
            with open(tmp_path, "rb") as f:
                files = {"file": f}
                data = {"model": "whisper-1"}
                r = requests.post(url, headers=headers, files=files, data=data)
            
            os.remove(tmp_path)
            return r.json().get("text", "").strip()
        
        text = await loop.run_in_executor(None, transcribe)
        
        if text:
            print(f"🗣 Ты: {text}")
        return text
    
    async def ask_gpt(self, prompt):
        """Отправляет запрос в GPT и возвращает ответ"""
        chunk_queue = asyncio.Queue()
        full_response = ""
        
        # Собираем ответ по частям
        async for chunk in openai_stream(self.agent.messages + [{"role": "user", "content": prompt}], chunk_queue):
            if chunk == "":
                break
            full_response += chunk
        
        # Добавляем в историю
        self.agent.messages.append({"role": "user", "content": prompt})
        self.agent.messages.append({"role": "assistant", "content": full_response})
        
        # Обрезаем историю до 5 последних сообщений
        self.agent.messages = self.agent.messages[-5:]
        
        print(f"🤖 Бот: {full_response}")
        return full_response
    
    async def speak_stream(self, text):
        """Синтезирует речь и воспроизводит"""
        print("🔊 Воспроизвожу ответ...")
        
        def synthesize_and_play():
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{os.getenv('VOICE_ID', 'RGy9Pi4dN4jZx6BL6lef')}/stream"
            headers = {
                "xi-api-key": os.getenv('ELEVEN_APIKEY'),
                "Accept": "audio/mpeg",
                "Content-Type": "application/json"
            }
            data = {
                "text": text,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {"stability": 0.4, "similarity_boost": 0.5}
            }
            
            with requests.post(url, json=data, headers=headers, stream=True) as r:
                if r.status_code == 200:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
                        for chunk in r.iter_content(chunk_size=1024):
                            fp.write(chunk)
                    playsound.playsound(fp.name)
                    os.remove(fp.name)
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, synthesize_and_play)
        print("✅ Воспроизведение завершено")
    
    async def run(self):
        """Основной цикл бота"""
        print("🎤🎧 Запуск голосового финансового агента...")
        print("📋 Настройки:")
        print("   - Микрофон: включен")
        print("   - Динамик: включен") 
        print("   - Агент: Максим (финансовый консультант)")
        print("   - Голос: ElevenLabs")
        print("\n💡 Инструкции:")
        print("   - Говорите в микрофон для общения с агентом")
        print("   - Агент будет отвечать через динамик")
        print("   - Для выхода нажмите Ctrl+C")
        print("\n🚀 Начинаем разговор...\n")
        
        try:
            while True:
                text = await self.listen_and_transcribe()
                if not text:
                    continue
                    
                response = await self.ask_gpt(text)
                await self.speak_stream(response)
                
        except KeyboardInterrupt:
            print("\n👋 Разговор завершен. До свидания!")
        except Exception as e:
            print(f"\n❌ Ошибка: {e}")

async def main():
    bot = SimpleVoiceBot()
    await bot.run()

if __name__ == "__main__":
    asyncio.run(main())

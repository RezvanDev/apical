from typing import Dict, List, Any
from api import openai_stream


class Agent:
    def __init__(self, context: Dict[str, Any]):
        """
        Принимает словарь с ключом 'messages', содержащим историю сообщений
        в формате OpenAI API: [{"role": ..., "content": ...}]
        """
        self.messages: List[dict] = context.get("messages", [])

    async def generate_answer(self, user_message: str, chunk_queue):
        """
        Добавляет сообщение пользователя в историю,
        обрезает до 5 последних сообщений,
        вызывает openai_stream и передаёт чанки в очередь.
        По завершении — добавляет полный ответ ассистента в историю.
        """
        # Добавить сообщение пользователя
        self.messages.append({"role": "user", "content": user_message})

        # Обрезать историю до последних 5 сообщений
        self.messages = self.messages[-5:]

        # Сбор ответа ассистента
        full_response = ""

        # Вызов openai_stream и сбор чанков
        async for chunk in openai_stream(self.messages, chunk_queue):
            if chunk == "":
                break
            await chunk_queue.put(chunk)
            full_response += chunk

        # Добавить ответ ассистента в историю
        self.messages.append({"role": "assistant", "content": full_response})


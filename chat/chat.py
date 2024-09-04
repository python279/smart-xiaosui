import logging
import json
import threading
import os
from typing import Optional, Any, Union
from openai import OpenAI

logger = logging.getLogger(__name__)


class Chat:
    def __init__(self, url: str, model: str, api_key: str):
        self.url = url
        self.model = model
        self.api_key = api_key
        self.client = OpenAI(api_key=self.api_key, base_url=self.url)

    def __call__(self, system_prompt: str, user_prompt: str) -> str:
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ],
            temperature=0.1,
            max_tokens=500 + len(user_prompt) + len(system_prompt)
        )
        return completion.choices[0].message.content


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    load_dotenv()

    chat = Chat(url=os.getenv("openai_url"), model=os.getenv("openai_model"), api_key=os.getenv("openai_api_key"))
    system_prompt = '你现在作为一个可以实时语音对话的智能助手，名字是“小燧”，你可以和用户聊天、回答问题、讲笑话、讲故事、唱歌、讲解知识等等。当碰到你不懂的问题时，你可以说“我不懂”，然后再次尝试回答。'
    response = chat(system_prompt, "你是谁，你可以做什么？")
    logger.info(f"Response: {response}")

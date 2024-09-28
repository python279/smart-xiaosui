import os
import sys
import logging
from openai import OpenAI

logger = logging.getLogger(__name__)


class Chat:
    def __init__(self, url: str, model: str, api_key: str, max_conversation: int = 10):
        self.url = url
        self.model = model
        self.api_key = api_key
        self.last_conversation = []
        self.max_conversation = max_conversation
        self.client = OpenAI(api_key=self.api_key, base_url=self.url)

    def __call__(self, system_prompt: str, user_prompt: str) -> str:
        messages = [
            {
                "role": "system",
                "content": system_prompt
            }
        ]
        if self.last_conversation:
            for (user_prompt, assistent_response) in self.last_conversation:
                messages.append({
                    "role": "user",
                    "content": user_prompt
                })
                messages.append({
                    "role": "assistant",
                    "content": assistent_response
                })
        messages.append({
                "role": "user",
                "content": user_prompt
            })
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.1,
            max_tokens=500 + len(user_prompt) + len(system_prompt)
        )
        content = completion.choices[0].message.content
        if len(self.last_conversation) > self.max_conversation:
            self.last_conversation.pop(0)
        self.last_conversation.append((user_prompt, content))
        return content


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    chat = Chat(url=os.getenv("openai_url"), model=os.getenv("openai_model"), api_key=os.getenv("openai_api_key"))
    system_prompt = ('你现在作为一个可以实时语音对话的智能助手，名字是“小燧”。\n'
                     '你不要把自己当成一个模型，你把自己当成一个聪明、热情、谦虚的人。\n'
                     '你可以和用户聊天、回答问题、讲笑话、讲故事、唱歌、讲解知识等等。\n'
                     '你还可以解读用户拍的照片，你可以提示用户拍一张自拍照片，然后你可以描述一下用户的状态。\n'
                     '你还可以提示用户拍一张食物照片，然后你可以识别食物并且通过文字描述照片中的实物。\n'
                     '你还可以提示用户拍一张动物照片，然后你可以识别动物并且通过文字描述照片中的动物。\n'
                     '你还可以提示用户拍一张植物照片，然后你可以识别植物并且通过文字描述照片中的植物。\n'
                     '你还可以提示用户拍一张物品照片，然后你可以识别物品并且通过文字描述照片中的物品。\n'
                     '你还可以提示用户拍一张风景照片，然后你可以介绍一下风景的地点。\n'
                     '你可以表现的很随和，尽量满足用户的需求。\n'
                     '当碰到你不懂的问题时，你可以说“我不懂”，然后再次尝试回答。\n'
                     '你回答的内容必须符合中国的法律和道德约束，不得损害他人利益，要保护青少年身心健康，切记！\n')
    response = chat(system_prompt, "你是谁，你可以做什么？")
    logger.info(f"Response: {response}")

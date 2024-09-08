import os
import sys
import logging
import threading
import time
from signal import pause
from dotenv import load_dotenv
from typing import Callable
from asr.xf_iat import ASRClient
from tts.xf_tts import TTSClient
from chat.chat import Chat
from audio import AudioPlayer, AudioRecorder

logger = logging.getLogger()
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


if __name__ == "__main__":
    load_dotenv()

    if os.getenv("button_source") == "keyboard":
        import keyboard
    else:
        from gpiozero import Button

    chat = Chat(url=os.getenv("openai_url"), model=os.getenv("openai_model"), api_key=os.getenv("openai_api_key"))
    system_prompt = ('你现在作为一个可以实时语音对话的智能助手，名字是“小燧”。\n'
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

    # 初始化音频播放器
    audio_player = AudioPlayer(channels=1, rate=16000)

    # 初始化音频录制器
    audio_recorder = AudioRecorder(channels=1, rate=16000)

    # 触发录音
    def _start_recording(audio_recorder: AudioRecorder, callback: Callable = None) -> None:
        if not audio_recorder.is_recording:
            threading.Thread(target=audio_recorder.start_recording, args=(callback,)).start()

    # 停止录音
    def _stop_recording(audio_recorder: AudioRecorder) -> None:
        if audio_recorder.is_recording:
            time.sleep(1)
            audio_recorder.stop_recording()

    # 录音回调函数，核心部分
    def _audio_callback(audio_bytes: bytes) -> None:
        # 语音转文字
        asr = ASRClient(os.getenv("asr_ws_connect_timeout"),
                        os.getenv("asr_app_id"),
                        os.getenv("asr_api_key"),
                        os.getenv("asr_api_secret"))
        user_prompt = asr(audio_bytes, rate=16000, timeout=int(os.getenv("asr_request_timeout")))
        if user_prompt == "":
            return

        # 文字对话
        assistent_response = chat(system_prompt, user_prompt)

        # 文字转语音并播放
        tts = TTSClient(os.getenv("tts_ws_connect_timeout"),
                        os.getenv("tts_app_id"),
                        os.getenv("tts_api_key"),
                        os.getenv("tts_api_secret"))
        tts(assistent_response, audio_player.play, rate=16000)

    if os.getenv("button_source") == "keyboard":
        # 监听键盘事件，触发或者停止录音
        keyboard.on_press_key('space', lambda _: _start_recording(audio_recorder, _audio_callback))
        keyboard.on_release_key('space', lambda _: _stop_recording(audio_recorder))
        print("准备好录音，按‘空格’键开始录音，释放’空格‘键停止录音。")
    else:
        # 监听按钮事件，触发或者停止录音
        button = Button(int(os.getenv("button_gpio_pin")))
        button.when_pressed = lambda: _start_recording(audio_recorder, _audio_callback)
        button.when_released = lambda: _stop_recording(audio_recorder)
        print("准备好录音，按‘对话’键开始录音，释放’对话‘键停止录音。")

    try:
        pause()
        while True:
            time.sleep(5)
    finally:
        pass

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
from screen.screen import Screen
from audio import AudioPlayer, AudioRecorder, AudioVolumeControl
from PIL import Image
from threading import Thread
from queue import Queue
from enum import Enum

logger = logging.getLogger()
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('%(asctime)s - %(threadName)s - %(filename)s - %(lineno)d - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


class KeyEvent(Enum):
    ENTER_PRESSED = 1
    ENTER_RELEASED = 2
    UP_PRESSED = 3
    UP_RELEASED = 4
    DOWN_PRESSED = 5
    DOWN_RELEASED = 6
    LEFT_PRESSED = 7
    LEFT_RELEASED = 8
    RIGHT_PRESSED = 9
    RIGHT_RELEASED = 10

key_gpio = {
    "ENTER": 13,
    "UP": 26,
    "DOWN": 5,
    "LEFT": 16,
    "RIGHT": 6
}

key_keyboard = {
    "ENTER": "enter",
    "UP": "up",
    "DOWN": "down",
    "LEFT": "left",
    "RIGHT": "right"
}


class UIState(Enum):
    CHAT = 1
    SETUP = 2


if __name__ == "__main__":
    load_dotenv()

    # 初始化屏幕
    screen = Screen(simulate=(os.getenv("simulate_screen") == 'true'))

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
                     '你回答的内容必须符合中国的法律和道德约束，不得损害他人利益，要保护青少年身心健康，切记！\n'
                     '你回答的内容不要包含暴力、色情、赌博、恐怖等内容，要保持中立、客观、公正。\n'
                     '你回答的内容要符合事实真相，不得散布谣言，不得违反国家政策法规。\n'
                     '你回答的内容要尊重用户隐私，不得泄露用户个人信息。\n'
                     '你回答的内容要尊重用户权益，不得误导用户，不得欺诈用户。\n'
                     '你回答的内容要尊重用户感情，不得侮辱、辱骂、挑衅用户。\n'
                     '你回答的内容要尊重用户智商，不得恶搞、恶意调侃用户。\n'
                     '你回答的内容要符合社会主意核心价值观，不得违背社会公序良俗。')

    #  初始化音量控制
    volume_control = AudioVolumeControl()

    # 初始化音频播放器
    audio_player = AudioPlayer(channels=1, rate=16000)

    # 初始化音频录制器
    audio_recorder = AudioRecorder(channels=1, rate=16000)

    # asr
    asr = None

    # tts
    tts = None

    # network connection state
    is_connected = False

    # battery state
    battery_level = 100

    # 触发录音
    def _start_recording(audio_recorder: AudioRecorder, callback: Callable = None) -> None:
        if not audio_recorder.is_recording:
            global asr
            global tts
            asr = ASRClient(os.getenv("asr_ws_connect_timeout"),
                            os.getenv("asr_app_id"),
                            os.getenv("asr_api_key"),
                            os.getenv("asr_api_secret"))
            t = threading.Thread(target=audio_recorder.start_recording, args=(callback,))
            t.start()

    # 停止录音
    def _stop_recording(audio_recorder: AudioRecorder) -> None:
        if audio_recorder.is_recording:
            time.sleep(1)
            audio_recorder.stop_recording()

    # 录音回调函数，核心部分
    def _audio_callback(audio_bytes: bytes) -> None:
        global asr
        global tts

        # 语音转文字
        user_prompt = asr(audio_bytes, rate=16000, timeout=int(os.getenv("asr_request_timeout")))
        if user_prompt == "":
            return

        tts = TTSClient(os.getenv("tts_ws_connect_timeout"),
                        os.getenv("tts_app_id"),
                        os.getenv("tts_api_key"),
                        os.getenv("tts_api_secret"))

        # 文字对话
        assistent_response = chat(system_prompt, user_prompt)
        logger.info(f"assistent_response={assistent_response}")

        # 文字转语音并播放
        tts(assistent_response, audio_player.play, rate=16000)

    def network_check_daemon(period: int = 10) -> None:
        while True:
            global is_connected
            # 通过socket判断网络是否连接
            is_connected = (os.system("ping -c 2 114.114.114.114 2>&1 > /dev/null") == 0)
            time.sleep(period)

    def show_image_with_banner(image: str, banner_height: int = 40, banner_width: int = screen.width - 10) -> None:
        global screen
        global is_connected
        global battery_level
        image = Image.open(image)
        banner = Image.new("RGBA", (banner_height, banner_width), (255, 255, 255, 0))
        wifi_state_image = "screen/image/wifi-connected.png" if is_connected else "screen/image/wifi-disconnected.png"
        if battery_level > 50:
            battery_state_image = f"screen/image/battery-100.png"
        elif battery_level > 0 and battery_level <= 50:
            battery_state_image = f"screen/image/battery-50.png"
        else:
            battery_state_image = f"screen/image/battery-0.png"
        wifi_state_image = Image.open(wifi_state_image).convert("RGBA")
        banner.paste(wifi_state_image,
                     ((banner_height - wifi_state_image.width)//2,
                      (banner_height - wifi_state_image.height)//2),
                     wifi_state_image)
        battery_state_image = Image.open(battery_state_image).convert("RGBA")
        banner.paste(battery_state_image,
                     ((banner_height - battery_state_image.width)//2,
                      (banner_height - wifi_state_image.height)//2 + banner_height),
                     battery_state_image)
        image.paste(banner,
                    (screen.width - banner_height, (screen.height - banner_width) // 2),
                    banner)
        screen.show_image(image)

    def app():
        global is_connected
        global audio_recorder
        global audio_player
        global screen

        key_event_queue = Queue()

        button_hooks = []
        if os.getenv("button_source") == "keyboard":
            for key, value in key_keyboard.items():
                keyboard.add_hotkey(value, lambda: key_event_queue.put(KeyEvent[key + "_PRESSED"]))
                keyboard.add_hotkey(value, lambda: key_event_queue.put(KeyEvent[key + "_RELEASED"]), trigger_on_release=True)
        else:
            button_enter = Button(key_gpio["ENTER"])
            button_enter.when_pressed = lambda: key_event_queue.put(KeyEvent["ENTER_PRESSED"])
            button_enter.when_released = lambda: key_event_queue.put(KeyEvent["ENTER_RELEASED"])
            button_hooks.append(button_enter)

            button_up = Button(key_gpio["UP"])
            button_up.when_pressed = lambda: key_event_queue.put(KeyEvent["UP_PRESSED"])
            button_up.when_released = lambda: key_event_queue.put(KeyEvent["UP_RELEASED"])
            button_hooks.append(button_up)

            button_down = Button(key_gpio["DOWN"])
            button_down.when_pressed = lambda: key_event_queue.put(KeyEvent["DOWN_PRESSED"])
            button_down.when_released = lambda: key_event_queue.put(KeyEvent["DOWN_RELEASED"])
            button_hooks.append(button_down)

            button_left = Button(key_gpio["LEFT"])
            button_left.when_pressed = lambda: key_event_queue.put(KeyEvent["LEFT_PRESSED"])
            button_left.when_released = lambda: key_event_queue.put(KeyEvent["LEFT_RELEASED"])
            button_hooks.append(button_left)

            button_right = Button(key_gpio["RIGHT"])
            button_right.when_pressed = lambda: key_event_queue.put(KeyEvent["RIGHT_PRESSED"])
            button_right.when_released = lambda: key_event_queue.put(KeyEvent["RIGHT_RELEASED"])
            button_hooks.append(button_right)
            logger.info(f"button_hooks={button_hooks}")

        # 显示初始画面
        ui_state = UIState.CHAT
        ui_level = 0
        show_image_with_banner("screen/image/topicon-chat.png")

        while True:
            key_event = key_event_queue.get()
            logger.info(f"key_event={key_event}")

            if ui_level == 0 and ui_state == UIState.CHAT:
                if key_event == KeyEvent.ENTER_PRESSED:
                    _start_recording(audio_recorder, _audio_callback)
                elif key_event == KeyEvent.ENTER_RELEASED:
                    _stop_recording(audio_recorder)
                elif key_event == KeyEvent.UP_PRESSED:
                    vol = volume_control.up()
                    show_image_with_banner(f"screen/image/volume-{vol}.png")
                    time.sleep(0.2)
                    show_image_with_banner("screen/image/topicon-chat.png")
                elif key_event == KeyEvent.DOWN_PRESSED:
                    vol = volume_control.down()
                    show_image_with_banner(f"screen/image/volume-{vol}.png")
                    time.sleep(0.2)
                    show_image_with_banner("screen/image/topicon-chat.png")
                elif key_event == KeyEvent.LEFT_PRESSED or key_event == KeyEvent.RIGHT_PRESSED:
                    ui_state = UIState.SETUP
                    show_image_with_banner(f"screen/image/topicon-setup.png")
            elif ui_level == 0 and ui_state == UIState.SETUP:
                if key_event == KeyEvent.LEFT_PRESSED or key_event == KeyEvent.RIGHT_PRESSED:
                    ui_state = UIState.CHAT
                    show_image_with_banner(f"screen/image/topicon-chat.png")

    network_check_thread = Thread(target=network_check_daemon)
    network_check_thread.start()
    app_thread = Thread(target=app)
    app_thread.start()

    try:
        screen.main_loop()
    finally:
        pass

import os
import queue
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
from PIL import Image, ImageDraw, ImageFont
from threading import Thread
from queue import Queue
from enum import Enum
import nmcli

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
    "LEFT": 6,
    "RIGHT": 16
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
    SETUP_WIFI_LIST = 3
    SETUP_WIFI_PASSWORD = 4


sw_keyboard = (
    ('A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L'),
    ('M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X'),
    ('Y', 'Z', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9'),
    ('a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l'),
    ('m', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x'),
    ('y', 'z', '!', '@', '#', '$', '%', '^', '&', '*', '(', ')'),
    ('_', '-', '+', '=', '{', '}', '[', ']', '|', '\\', '=', '\b'),
    (':', ';', '"', '\'', '<', ',', '>', '.', '?', '/', ' ', '\r')
)


class App:
    def __init__(self):
        self.wifi_list = []
        self.wifi_index = 0
        self.wifi_name = ""
        self.wifi_passwd = ""
        self.ui_state = UIState.CHAT
        self.ui_level = 0
        self.sw_keyboard_index = [0, 0]
        self.sw_keyboard_dim = (len(sw_keyboard), len(sw_keyboard[0]))
        self.sw_keyboard_start_px_x = 0
        self.sw_keyboard_start_px_y = 64
        self.sw_keyboard_height = 22
        self.sw_keyboard_width = 20

        # 初始化屏幕
        self.screen = Screen(simulate=(os.getenv("simulate_screen") == 'true'))

        self.chat = Chat(url=os.getenv("openai_url"), model=os.getenv("openai_model"), api_key=os.getenv("openai_api_key"))
        self.system_prompt = ('你现在作为一个可以实时语音对话的智能助手，名字是“小燧”。\n'
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
        self.volume_control = AudioVolumeControl()

        # 初始化音频播放器
        self.audio_player = AudioPlayer(channels=1, rate=16000)

        # 初始化音频录制器
        self.audio_recorder = AudioRecorder(channels=1, rate=16000)

        # asr
        self.asr = None

        # tts
        self.tts = None

        # network connection state
        self.is_connected = False

        # battery state
        self.battery_level = 100

    # 触发录音
    def _start_recording(self) -> None:
        if not self.audio_recorder.is_recording:
            self.asr = ASRClient(os.getenv("asr_ws_connect_timeout"),
                            os.getenv("asr_app_id"),
                            os.getenv("asr_api_key"),
                            os.getenv("asr_api_secret"))
            t = threading.Thread(target=self.audio_recorder.start_recording, args=(self._audio_callback,))
            t.start()

    # 停止录音
    def _stop_recording(self) -> None:
        if self.audio_recorder.is_recording:
            time.sleep(1)
            self.audio_recorder.stop_recording()

    # 录音回调函数，核心部分
    def _audio_callback(self, audio_bytes: bytes) -> None:
        # 语音转文字
        user_prompt = self.asr(audio_bytes, rate=16000, timeout=int(os.getenv("asr_request_timeout")))
        if user_prompt == "":
            return

        self.tts = TTSClient(os.getenv("tts_ws_connect_timeout"),
                        os.getenv("tts_app_id"),
                        os.getenv("tts_api_key"),
                        os.getenv("tts_api_secret"))

        # 文字对话
        assistent_response = self.chat(self.system_prompt, user_prompt)
        logger.info(f"assistent_response={assistent_response}")

        # 文字转语音并播放
        self.tts(assistent_response, self.audio_player.play, rate=16000)

    def network_check_daemon(self, period: int = 10) -> None:
        while True:
            # 通过socket判断网络是否连接
            self.is_connected = (os.system("ping -c 2 114.114.114.114 2>&1 > /dev/null") == 0)
            time.sleep(period)

    def get_banner_image(self, banner_height: int, banner_width: int) -> Image:
        banner = Image.new("RGBA", (banner_height, banner_width), (255, 255, 255, 0))
        wifi_state_image = "screen/image/wifi-connected.png" if self.is_connected else "screen/image/wifi-disconnected.png"
        if self.battery_level > 50:
            battery_state_image = f"screen/image/battery-100.png"
        elif self.battery_level > 0 and self.battery_level <= 50:
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
        return banner

    def show_image_with_banner(self, image: str) -> None:
        banner_height = 40
        banner_width = self.screen.width - 10
        image = Image.open(image)
        banner = self.get_banner_image(banner_height, banner_width)
        image.paste(banner,
                    (self.screen.width - banner_height, (self.screen.height - banner_width) // 2),
                    banner)
        self.screen.show_image(image)

    def show_wifi_list_with_banner(
            self,
            up: int = 0,
            down: int = 0
    ) -> None:
        banner_height = 40
        banner_width = self.screen.width - 10
        if up == 0 and down == 0:
            self.wifi_list = nmcli.device.wifi()
            self.wifi_index = 0
            logger.info(f"wifi_list={self.wifi_list}")
        else:
            if up:
                self.wifi_index = (self.wifi_index - 1 + len(self.wifi_list)) % len(self.wifi_list)
            elif down:
                self.wifi_index = (self.wifi_index + 1) % len(self.wifi_list)

        logger.info(f"select wifi: {self.get_selected_wifi_name()}")
        image = Image.open("screen/image/wifi-list.png")
        banner = self.get_banner_image(banner_height, banner_width)
        image.paste(banner,
                    (self.screen.width - banner_height, (self.screen.height - banner_width) // 2),
                    banner)
        image = image.rotate(90)
        draw = ImageDraw.Draw(image)
        font = ImageFont.truetype("screen/Font/Font00.ttf", 20)
        draw.text((0, self.sw_keyboard_start_px_y - self.sw_keyboard_height - 10), "选择WIFI：",
                  fill="BLACK", font=font, align="left")
        wifi_name = self.get_selected_wifi_name()
        if len(wifi_name) > 13:
            wifi_name = wifi_name[:13] + ".."
        draw.text((20, self.screen.width // 2 - 15), wifi_name, fill="BLACK", font=font, align="center")
        image = image.rotate(-90)
        self.screen.show_image(image)

    def get_selected_wifi_name(self) -> str:
        return self.wifi_list[self.wifi_index].ssid

    def show_wifi_password_with_banner(
            self,
            up: int = 0,
            down: int = 0,
            left: int = 0,
            right: int = 0,
    ) -> None:
        banner_height = 40
        banner_width = self.screen.width - 10
        image = Image.open("screen/image/wifi-passwd-sw-kb.png")
        banner = self.get_banner_image(banner_height, banner_width)
        image.paste(banner,
                    (self.screen.width - banner_height, (self.screen.height - banner_width) // 2),
                    banner)

        if up:
            self.sw_keyboard_index[0] = (self.sw_keyboard_index[0] - 1 + self.sw_keyboard_dim[0]) % self.sw_keyboard_dim[0]
        elif down:
            self.sw_keyboard_index[0] = (self.sw_keyboard_index[0] + 1) % self.sw_keyboard_dim[0]
        elif left:
            self.sw_keyboard_index[1] = (self.sw_keyboard_index[1] - 1 + self.sw_keyboard_dim[1]) % self.sw_keyboard_dim[1]
        elif right:
            self.sw_keyboard_index[1] = (self.sw_keyboard_index[1] + 1) % self.sw_keyboard_dim[1]

        logger.info(f"sw_keyboard_index={self.sw_keyboard_index}")
        logger.info(f"wifi_passwd={self.wifi_passwd}")

        image = image.rotate(90)
        draw = ImageDraw.Draw(image)
        font = ImageFont.truetype("screen/Font/Font00.ttf", 20)

        if len(self.wifi_passwd) > 8:
            wifi_passwd = self.wifi_passwd[len(self.wifi_passwd) - 8:]
        else:
            wifi_passwd = self.wifi_passwd
        draw.text((0, self.sw_keyboard_start_px_y - self.sw_keyboard_height - 10),
                  f"WIFI密码：{wifi_passwd}",
                  fill="BLACK", font=font, align="left")
        left_top = (self.sw_keyboard_start_px_x + self.sw_keyboard_width * self.sw_keyboard_index[1],
                    self.sw_keyboard_start_px_y + self.sw_keyboard_height * self.sw_keyboard_index[0])
        right_bottom = (left_top[0] + self.sw_keyboard_width, left_top[1] + self.sw_keyboard_height)
        border_color = (255, 0, 0, 255)
        draw.rectangle([left_top, right_bottom], outline=border_color, width=2)
        image = image.rotate(-90)
        self.screen.show_image(image)

    def get_sw_keyboard_input_char(self) -> str:
        return sw_keyboard[self.sw_keyboard_index[0]][self.sw_keyboard_index[1]]

    def connect_wifi(self, wifi_name: str, wifi_passwd: str) -> None:
        def _connect_wifi():
            nmcli.device.wifi_connect(wifi_name, wifi_passwd)
        threading.Thread(target=_connect_wifi).start()
        time.sleep(2)

    def core(self):
        key_event_queue = Queue()

        if os.getenv("button_source") == "keyboard":
            keyboard.add_hotkey(key_keyboard["ENTER"], lambda: key_event_queue.put("ENTER_PRESSED"))
            keyboard.add_hotkey(key_keyboard["ENTER"], lambda: key_event_queue.put("ENTER_RELEASED"),
                                trigger_on_release=True)
            keyboard.add_hotkey(key_keyboard["UP"], lambda: key_event_queue.put("UP_PRESSED"))
            keyboard.add_hotkey(key_keyboard["UP"], lambda: key_event_queue.put("UP_RELEASED"),
                                trigger_on_release=True)
            keyboard.add_hotkey(key_keyboard["DOWN"], lambda: key_event_queue.put("DOWN_PRESSED"))
            keyboard.add_hotkey(key_keyboard["DOWN"], lambda: key_event_queue.put("DOWN_RELEASED"),
                                trigger_on_release=True)
            keyboard.add_hotkey(key_keyboard["LEFT"], lambda: key_event_queue.put("LEFT_PRESSED"))
            keyboard.add_hotkey(key_keyboard["LEFT"], lambda: key_event_queue.put("LEFT_RELEASED"),
                                trigger_on_release=True)
            keyboard.add_hotkey(key_keyboard["RIGHT"], lambda: key_event_queue.put("RIGHT_PRESSED"))
            keyboard.add_hotkey(key_keyboard["RIGHT"], lambda: key_event_queue.put("RIGHT_RELEASED"),
                                trigger_on_release=True)
        else:
            button_enter = Button(key_gpio["ENTER"])
            button_enter.when_pressed = lambda: key_event_queue.put(KeyEvent["ENTER_PRESSED"])
            button_enter.when_released = lambda: key_event_queue.put(KeyEvent["ENTER_RELEASED"])

            button_up = Button(key_gpio["UP"])
            button_up.when_pressed = lambda: key_event_queue.put(KeyEvent["UP_PRESSED"])
            button_up.when_released = lambda: key_event_queue.put(KeyEvent["UP_RELEASED"])

            button_down = Button(key_gpio["DOWN"])
            button_down.when_pressed = lambda: key_event_queue.put(KeyEvent["DOWN_PRESSED"])
            button_down.when_released = lambda: key_event_queue.put(KeyEvent["DOWN_RELEASED"])

            button_left = Button(key_gpio["LEFT"])
            button_left.when_pressed = lambda: key_event_queue.put(KeyEvent["LEFT_PRESSED"])
            button_left.when_released = lambda: key_event_queue.put(KeyEvent["LEFT_RELEASED"])

            button_right = Button(key_gpio["RIGHT"])
            button_right.when_pressed = lambda: key_event_queue.put(KeyEvent["RIGHT_PRESSED"])
            button_right.when_released = lambda: key_event_queue.put(KeyEvent["RIGHT_RELEASED"])

        # 显示初始画面
        self.show_image_with_banner("screen/image/topicon-chat.png")
        while True:
            try:
                key_event = key_event_queue.get(timeout=10)
            except queue.Empty:
                key_event = None
            logger.info(f"key_event={key_event}")
            logger.info(f"ui_state={self.ui_state}, ui_level={self.ui_level}")
            if key_event is None:
                # 自动回到对话界面，刷新网络和电池状态
                self.ui_state = UIState.CHAT
                self.ui_level = 0
                self.show_image_with_banner("screen/image/topicon-chat.png")
                continue

            if self.ui_level == 0 and self.ui_state == UIState.CHAT:
                if key_event == KeyEvent.ENTER_PRESSED:
                    self._start_recording()
                elif key_event == KeyEvent.ENTER_RELEASED:
                    self._stop_recording()
                elif key_event == KeyEvent.UP_PRESSED:
                    vol = self.volume_control.up()
                    self.show_image_with_banner(f"screen/image/volume-{vol}.png")
                    time.sleep(0.2)
                    self.show_image_with_banner("screen/image/topicon-chat.png")
                elif key_event == KeyEvent.DOWN_PRESSED:
                    vol = self.volume_control.down()
                    self.show_image_with_banner(f"screen/image/volume-{vol}.png")
                    time.sleep(0.2)
                    self.show_image_with_banner("screen/image/topicon-chat.png")
                elif key_event == KeyEvent.LEFT_PRESSED or key_event == KeyEvent.RIGHT_PRESSED:
                    self.ui_state = UIState.SETUP
                    self.show_image_with_banner(f"screen/image/topicon-setup.png")
            elif self.ui_level == 0 and self.ui_state == UIState.SETUP:
                if key_event == KeyEvent.LEFT_PRESSED or key_event == KeyEvent.RIGHT_PRESSED:
                    self.ui_state = UIState.CHAT
                    self.show_image_with_banner(f"screen/image/topicon-chat.png")
                elif key_event == KeyEvent.ENTER_PRESSED:
                    self.ui_level = 1
                    self.ui_state = UIState.SETUP_WIFI_LIST
                    self.show_wifi_list_with_banner()
            elif self.ui_level == 1 and self.ui_state == UIState.SETUP_WIFI_LIST:
                if key_event == KeyEvent.UP_PRESSED:
                    self.show_wifi_list_with_banner(up=1)
                elif key_event == KeyEvent.DOWN_PRESSED:
                    self.show_wifi_list_with_banner(down=1)
                elif key_event == KeyEvent.ENTER_PRESSED:
                    self.wifi_name = self.get_selected_wifi_name()
                    self.ui_state = UIState.SETUP_WIFI_PASSWORD
                    self.wifi_name = ""
                    self.wifi_passwd = ""
                    self.sw_keyboard_index = [0, 0]
                    self.show_wifi_password_with_banner()
            elif self.ui_level == 1 and self.ui_state == UIState.SETUP_WIFI_PASSWORD:
                if key_event == KeyEvent.UP_PRESSED:
                    self.show_wifi_password_with_banner(up=1)
                elif key_event == KeyEvent.DOWN_PRESSED:
                    self.show_wifi_password_with_banner(down=1)
                elif key_event == KeyEvent.LEFT_PRESSED:
                    self.show_wifi_password_with_banner(left=1)
                elif key_event == KeyEvent.RIGHT_PRESSED:
                    self.show_wifi_password_with_banner(right=1)
                elif key_event == KeyEvent.ENTER_PRESSED:
                    char = self.get_sw_keyboard_input_char()
                    if char == "\r":
                        self.connect_wifi(self.wifi_name, self.wifi_passwd)
                        self.ui_level = 0
                        self.ui_state = UIState.SETUP
                        self.show_image_with_banner(f"screen/image/topicon-setup.png")
                    else:
                        if char == "\b":
                            self.wifi_passwd = self.wifi_passwd[:-1]
                        else:
                            self.wifi_passwd += char
                        self.show_wifi_password_with_banner()

    def run_forever(self) -> None:
        network_check_thread = Thread(target=self.network_check_daemon)
        network_check_thread.start()
        app_thread = Thread(target=self.core)
        app_thread.start()

        try:
            self.screen.main_loop()
        finally:
            pass


if __name__ == "__main__":
    load_dotenv()
    if os.getenv("button_source") == "keyboard":
        import keyboard
    else:
        from gpiozero import Button

    app = App()
    app.run_forever()

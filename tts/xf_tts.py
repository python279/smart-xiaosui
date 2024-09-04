import os
import sys
import logging
import websocket
import datetime
import hashlib
import base64
import hmac
import json
from urllib.parse import urlencode
import time
import ssl
from wsgiref.handlers import format_date_time
from datetime import datetime
from time import mktime
import threading
import os
import pyaudio
from typing import Optional, Any, Union, Callable

logger = logging.getLogger()


class TTSClient:
    def __init__(self, app_id: str, api_key: str, api_secret: str):
        self.app_id = app_id
        self.api_key = api_key
        self.api_secret = api_secret
        self.thread_loop = None
        self.is_connected: bool = False
        self.callback: Optional[Callable] = None
        self.start_daemon()

    def __del__(self):
        if self.ws:
            self.ws.close()

    def start_daemon(self):
        if not self.thread_loop:
            self.thread_loop = threading.Thread(target=self.connect, daemon=True)
            self.thread_loop.start()

    def create_url(self) -> str:
        url = 'wss://tts-api.xfyun.cn/v2/tts'
        now = datetime.now()
        date = format_date_time(mktime(now.timetuple()))

        signature_origin = f"host: ws-api.xfyun.cn\n" \
                           f"date: {date}\n" \
                           f"GET /v2/tts HTTP/1.1"
        signature_sha = hmac.new(self.api_secret.encode('utf-8'), signature_origin.encode('utf-8'),
                                 digestmod=hashlib.sha256).digest()
        signature_sha = base64.b64encode(signature_sha).decode(encoding='utf-8')

        authorization_origin = f'api_key="{self.api_key}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature_sha}"'
        authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode(encoding='utf-8')

        v = {
            "authorization": authorization,
            "date": date,
            "host": "ws-api.xfyun.cn"
        }
        return url + '?' + urlencode(v)

    def on_message(self, ws: websocket.WebSocketApp, message: str) -> None:
        try:
            message = json.loads(message)
            code = message["code"]
            sid = message["sid"]
            audio = message["data"].get("audio", "")
            audio = base64.b64decode(audio)
            status = message["data"]["status"]

            if status == 2:
                logger.info("ws is closed")
                ws.close()

            if code != 0:
                err_msg = message["message"]
                logger.error(f"sid:{sid} call error:{err_msg} code is:{code}")
            else:
                if self.callback:
                    self.callback(audio)
        except Exception as e:
            logger.error(f"receive msg, but parse exception: {e}")

    def on_error(self, ws: websocket.WebSocketApp, error: Exception) -> None:
        logger.error(f"### error ###\n{error}")

    def on_close(self, ws: websocket.WebSocketApp, a: Any, b: Any) -> None:
        logger.info(f"### closed ###\na={a}\nb={b}")
        self.is_connected = False
        self.thread_loop = None
        self.ws = None

    def on_open(self, ws: websocket.WebSocketApp) -> None:
        logger.info(f"### connected ###")
        self.is_connected = True
        self.ws = ws

    def connect(self) -> None:
        websocket.enableTrace(True)
        ws = websocket.WebSocketApp(self.create_url(),
                                    on_message=self.on_message,
                                    on_error=self.on_error,
                                    on_close=self.on_close,
                                    on_open=self.on_open)
        ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})

    def send_text(self, text: str) -> None:
        if not self.thread_loop:
            self.start_daemon()

        for i in range(10):
            if not self.is_connected:
                logger.info("WebSocket is not connected, waiting...")
                time.sleep(0.2)
            else:
                break

        if not self.is_connected:
            raise Exception("WebSocket is not connected")

        data = {
            "common": {"app_id": self.app_id},
            "business": {"aue": "raw", "auf": "audio/L16;rate=16000", "vcn": "aisjinger", "tte": "utf8", "speed": 80},
            "data": {
                "status": 2,
                "text": str(base64.b64encode(text.encode('utf-8')), "UTF8")
            }
        }
        self.ws.send(json.dumps(data))

    def __call__(self, text: str, callback: Callable) -> None:
        self.callback = callback
        self.send_text(text)


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    load_dotenv()

    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    p = pyaudio.PyAudio()
    audio_stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, output=True)

    def audio_play(audio_data: bytes) -> None:
        audio_stream.write(audio_data)

    texts = ["基于统一建模的星火多语种语音识别大模型，能将短音频(≤60秒)精准识别成文字，识别准确率极高。\
              除中文普通话和英文外，支持37个语种自动判别，说话过程中可以无缝切换语种，并实时返回对应语种的文字结果。\
              可提供公有云接口及私有化部署方案。",
             "依托讯飞超脑2030，面向物理世界、数字世界和元宇宙，帮助开发者构建虚实结合、多模态交互、\
              智能运动、模型训练、软硬一体、大小脑协同的实体机器人与虚拟数字人。"]
    for text in texts:
        tts = TTSClient(os.getenv("tts_app_id"),
                        os.getenv("tts_api_key"),
                        os.getenv("tts_api_secret"))
        tts(text, audio_play)
        time.sleep(30)

    audio_stream.stop_stream()
    audio_stream.close()
    p.terminate()

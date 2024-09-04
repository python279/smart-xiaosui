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
from typing import Union, Any, Optional
import threading

STATUS_FIRST_FRAME = 0  # 第一帧的标识
STATUS_CONTINUE_FRAME = 1  # 中间帧标识
STATUS_LAST_FRAME = 2  # 最后一帧的标识


logger = logging.getLogger()


class ASRClient:
    def __init__(self, app_id: str, api_key: str, api_secret: str):
        self.app_id: str = app_id
        self.api_key: str = api_key
        self.api_secret: str = api_secret
        self.common_args: dict[str, Any] = {"app_id": self.app_id}
        self.business_args: dict[str, Any] = {
            "domain": "iat",
            "language": "zh_cn",
            "accent": "mandarin",
            "vinfo": 1,
            "vad_eos": 10000
        }
        self.ws: Optional[websocket.WebSocketApp] = None
        self.thread_loop = None
        self.is_connected: bool = False
        self.result: str = ""
        self.once_done = False

        # 启动守护线程
        self.start_daemon()

    def __del__(self):
        if self.ws:
            self.ws.close()

    def start_daemon(self):
        if not self.thread_loop:
            self.thread_loop = threading.Thread(target=self.connect, daemon=True)
            self.thread_loop.start()

    def create_url(self) -> str:
        url: str = 'wss://ws-api.xfyun.cn/v2/iat'
        now: datetime = datetime.now()
        date: str = format_date_time(mktime(now.timetuple()))
        signature_origin: str = f"host: ws-api.xfyun.cn\n" \
                                f"date: {date}\n" \
                                f"GET /v2/iat HTTP/1.1"
        signature_sha: bytes = hmac.new(self.api_secret.encode('utf-8'), signature_origin.encode('utf-8'),
                                        digestmod=hashlib.sha256).digest()
        signature_sha: str = base64.b64encode(signature_sha).decode(encoding='utf-8')
        authorization_origin: str = f'api_key="{self.api_key}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature_sha}"'
        authorization: str = base64.b64encode(authorization_origin.encode('utf-8')).decode(encoding='utf-8')

        v: dict[str, str] = {
            "authorization": authorization,
            "date": date,
            "host": "ws-api.xfyun.cn"
        }
        return url + '?' + urlencode(v)

    def on_message(self, ws: websocket.WebSocketApp, message: str) -> None:
        try:
            if message == '':
                return
            response: dict = json.loads(message)
            code: int = response.get("code")
            sid: str = response.get("sid")

            if code != 0:
                err_msg: str = response.get("message")
                logger.error(f"sid:{sid} call error:{err_msg} code is:{code}")
            else:
                data: list = response["data"]["result"]["ws"]
                logger.info(f"sid:{sid} call success!, data is: {json.dumps(data, ensure_ascii=False)}")

                self.result += "".join(w["w"] for i in data for w in i["cw"])
                self.once_done = True
        except Exception as e:
            logger.error("receive msg, but parse exception:", e)

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

    def send_audio(self, audio_data: bytes, rate=16000) -> None:
        self.start_daemon()
        for i in range(10):
            if not self.is_connected:
                logger.info("WebSocket is not connected, waiting...")
                time.sleep(0.2)
            else:
                break

        if not self.is_connected:
            raise Exception("WebSocket is not connected")

        frame_size: int = 1280  # 每一帧的音频大小
        intervel = 0.08  # 发送音频间隔(单位:s)
        status: int = STATUS_FIRST_FRAME  # 音频的状态信息

        total_bytes: int = len(audio_data)
        offset: int = 0

        while offset < total_bytes:
            buf: bytes = audio_data[offset:offset + frame_size]
            offset += frame_size

            if not buf:
                status = STATUS_LAST_FRAME

            if status == STATUS_FIRST_FRAME:
                d: dict = {
                    "common": self.common_args,
                    "business": self.business_args,
                    "data": {
                        "status": 0,
                        "format": f"audio/L16;rate={rate}",
                        "audio": str(base64.b64encode(buf), 'utf-8'),
                        "encoding": "raw"
                    }
                }
                self.ws.send(json.dumps(d))
                status = STATUS_CONTINUE_FRAME
            elif status == STATUS_CONTINUE_FRAME:
                d: dict = {
                    "data": {
                        "status": 1,
                        "format": f"audio/L16;rate={rate}",
                        "audio": str(base64.b64encode(buf), 'utf-8'),
                        "encoding": "raw"
                    }
                }
                self.ws.send(json.dumps(d))
            elif status == STATUS_LAST_FRAME:
                d: dict = {
                    "data": {
                        "status": 2,
                        "format": "audio/L16;rate=16000",
                        "audio": str(base64.b64encode(buf), 'utf-8'),
                        "encoding": "raw"
                    }
                }
                self.ws.send(json.dumps(d))
                #time.sleep(1)
                break

            # 模拟音频采样间隔
            time.sleep(intervel)

    def __call__(self, audio_data: Union[bytes, Any], rate=16000, timeout=20) -> str:
        if isinstance(audio_data, bytes):
            self.result = ""
            self.once_done = False
            self.send_audio(audio_data, rate)

            # 等待 ASR 完成
            for i in range(int(timeout)):
                if not self.once_done:
                    time.sleep(1)
                else:
                    break
            logger.info(f"return: {self.result}")
            return self.result
        elif hasattr(audio_data, 'read'):
            # 如果是文件类对象，读取其内容
            audio_data_bytes: bytes = audio_data.read()
            return self.__call__(audio_data_bytes, rate)


if __name__ == '__main__':
    from dotenv import load_dotenv
    load_dotenv()

    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    for i in range(5):
        asr = ASRClient(os.getenv("asr_app_id"),
                        os.getenv("asr_api_key"),
                        os.getenv("asr_api_secret"))

        with open("samples/iat_pcm_16k.pcm", "rb") as f:
            result = asr(f, rate=16000)
            print(result)
        time.sleep(1)

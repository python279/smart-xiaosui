import logging
from typing import List, Tuple, Callable
try:
    import alsaaudio
    alsaaudio_available = True
except ImportError:
    import pyaudio
    alsaaudio_available = False

if alsaaudio_available:
    import pyaudio
    pyaudio_alsaaudio_foramt_mapping = {
        pyaudio.paInt16: alsaaudio.PCM_FORMAT_S16_LE,
        pyaudio.paInt24: alsaaudio.PCM_FORMAT_S24_LE,
        pyaudio.paInt32: alsaaudio.PCM_FORMAT_S32_LE,
    }

logger = logging.getLogger()


class AudioPlayer:
    def __init__(self, format=pyaudio.paInt16, channels=1, rate=16000):
        if alsaaudio_available:
            self.stream = alsaaudio.PCM(alsaaudio.PCM_PLAYBACK, channels=channels,
                                        rate=rate, format=pyaudio_alsaaudio_foramt_mapping[format],
                                        periodsize=128, device='default')
        else:
            self.pa = pyaudio.PyAudio()
            self.stream = self.pa.open(format=format,
                                       channels=channels,
                                       rate=rate,
                                       output=True,
                                       start=True)

    def __del__(self):
        self.stream.close()
        if not alsaaudio_available:
            self.pa.terminate()

    def play(self, audio_data: bytes) -> None:
        offset = 0
        chunk = 128
        while True:
            data = audio_data[offset:offset + chunk]
            offset += chunk
            if not data:
                break
            self.stream.write(data)


class AudioRecorder:
    def __init__(self, format=pyaudio.paInt16, channels=1, rate=8000, chunk=1024):
        # 设置音频参数
        self.format = format
        self.channels = channels
        self.rate = rate
        self.chunk = chunk
        if alsaaudio_available:
            pass
        else:
            self.pa = pyaudio.PyAudio()
        self.is_recording = False

    def __del__(self):
        if not alsaaudio_available:
            self.pa.terminate()

    def start_recording(self, callback: Callable = None):
        if self.is_recording:
            return

        logger.info("录音开始...")
        self.is_recording = True

        try:
            frames = []

            # 打开音频流
            if alsaaudio_available:
                stream = alsaaudio.PCM(alsaaudio.PCM_CAPTURE, alsaaudio.PCM_NONBLOCK,
                                       channels=self.channels, rate=self.rate,
                                       format=pyaudio_alsaaudio_foramt_mapping[self.format],
                                       periodsize=128, periods=8, device='default')
            else:
                stream = self.pa.open(format=self.format,
                                      channels=self.channels,
                                      rate=self.rate,
                                      input=True,
                                      start=True)

            # 循环读取音频流
            while self.is_recording:
                if alsaaudio_available:
                    l, data = stream.read()
                    if l > 0:
                        frames.append(data)
                else:
                    data = stream.read(self.chunk)
                    frames.append(data)

            # 回调音频数据后处理函数
            if callback:
               callback(b''.join(frames))

            # 停止和关闭流
            stream.close()
        except Exception as e:
            logger.error(f"录音异常: {e}")

    def stop_recording(self):
        if self.is_recording:
            self.is_recording = False
            logger.info("录音结束...")


if __name__ == '__main__':
    import os
    import sys
    import time
    from threading import Thread

    audio_player = AudioPlayer(channels=1, rate=16000)
    audio_recorder = AudioRecorder(channels=1, rate=16000)

    def play_audio(audio_data: bytes):
        audio_player.play(audio_data)

    Thread(target=audio_recorder.start_recording, args=(play_audio,)).start()
    time.sleep(10)
    audio_recorder.stop_recording()

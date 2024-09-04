import logging
import pyaudio

logger = logging.getLogger()


class AudioPlayer:
    def __init__(self, format=pyaudio.paInt16, channels=1, rate=16000):
        self.pa = pyaudio.PyAudio()
        self.stream = self.pa.open(format=format, channels=channels, rate=rate, output=True)

    def __del__(self):
        self.stream.stop_stream()
        self.stream.close()
        self.pa.terminate()

    def play(self, audio_data: bytes) -> None:
        logger.info(f'播放音频数据，大小: {len(audio_data)}')
        self.stream.write(audio_data)


class AudioRecorder:
    def __init__(self, format=pyaudio.paInt16, channels=1, rate=16000, chunk=1280):
        # 设置音频参数
        self.format = format
        self.channels = channels
        self.rate = rate
        self.chunk = chunk
        self.pa = pyaudio.PyAudio()
        self.is_recording = False

    def __del__(self):
        self.pa.terminate()

    def start_recording(self, callback=None):
        if self.is_recording:
            return

        logger.info("录音开始...")
        self.is_recording = True

        try:
            frames = []

            # 打开音频流
            stream = self.pa.open(format=self.format,
                                  channels=self.channels,
                                  rate=self.rate,
                                  input=True,
                                  frames_per_buffer=self.chunk)

            # 循环读取音频流
            while self.is_recording:
                data = stream.read(self.chunk)
                frames.append(data)

            # 停止和关闭流
            stream.stop_stream()
            stream.close()

            # 合并音频数据
            audio_data = b''.join(frames)

            # 回调音频数据后处理函数
            if callback:
               callback(audio_data)
        except Exception as e:
            logger.error(f"录音异常: {e}")

    def stop_recording(self):
        if self.is_recording:
            self.is_recording = False
            logger.info("录音结束...")

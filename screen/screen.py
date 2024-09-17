import os
import logging
import time
from PIL import Image, ImageDraw, ImageFont
from typing import List, Union
from dotenv import load_dotenv

logger = logging.getLogger()


class Screen(object):
    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, '_instance'):
            cls._instance = super(Screen, cls).__new__(cls)
        return cls._instance

    def __init__(self, simulate=False):
        self.simulate = simulate

        if hasattr(self, 'disp'):
            return

        if self.simulate:
            from .simulate import SimulatedST7789
            self.disp = SimulatedST7789()
            self.disp.init()
            return
        else:
            from .ST7789 import ST7789
            self.disp = ST7789()
            self.disp.init()
            self.disp.clear()
            self.disp.bl_DutyCycle(50)

    def show_image(self, image: Union[Image.Image, str]):
        if isinstance(image, str):
            image = Image.open(image)
        self.disp.show_image(image)

    def show_gif(self, gif_path: str):
        try:
            gif = Image.open(gif_path)
            gif_frames = []
            frame_index = 0
            while True:
                frame = gif.copy()
                gif_frames.append(frame)
                try:
                    gif.seek(gif.tell() + 1)
                except EOFError:
                    break
            self.update_animation(gif_frames, frame_index)
        except Exception as e:
            logger.error(f"Failed to show gif: {e}")

    def update_animation(self, gif_frames: List[Image], frame_index: int = 0):
        if gif_frames:
            frame = gif_frames[frame_index]
            frame_width, frame_height = frame.size
            x = (self.width - frame_width) // 2
            y = (self.height - frame_height) // 2
            bg = Image.new("RGB", (self.width, self.height), "WHITE")
            bg.paste(frame, (x, y))
            frame_index += 1
            self.show_image(bg)
            time.sleep(0.01)
            if frame_index >= len(gif_frames):
                return
            self.update_animation(gif_frames, frame_index)

    def clear(self):
        self.disp.clear()

    @property
    def height(self):
        return self.disp.height

    @property
    def width(self):
        return self.disp.width

    def main_loop(self):
        self.disp.main_loop()


if __name__ == '__main__':
    from threading import Thread
    load_dotenv()

    screen = Screen(simulate=(os.getenv("simulate_screen") == 'true'))

    def test(screen: Screen):
        time.sleep(1)

        screen.clear()
        time.sleep(1)

        image1 = Image.new("RGB", (screen.width, screen.height), "WHITE")
        draw = ImageDraw.Draw(image1)
        draw.rectangle((5, 10, 6, 11), fill="BLACK")
        draw.rectangle((5, 25, 7, 27), fill="BLACK")
        draw.rectangle((5, 40, 8, 43), fill="BLACK")
        draw.rectangle((5, 55, 9, 59), fill="BLACK")
        logging.info("draw line")
        draw.line([(20, 10), (70, 60)], fill="RED", width=1)
        draw.line([(70, 10), (20, 60)], fill="RED", width=1)
        draw.line([(170, 15), (170, 55)], fill="RED", width=1)
        draw.line([(150, 35), (190, 35)], fill="RED", width=1)
        logging.info("draw rectangle")
        draw.rectangle([(20, 10), (70, 60)], fill="WHITE", outline="BLUE")
        draw.rectangle([(85, 10), (130, 60)], fill="BLUE")
        logging.info("draw circle")
        draw.arc((150, 15, 190, 55), 0, 360, fill=(0, 255, 0))
        draw.ellipse((150, 65, 190, 105), fill=(0, 255, 0))
        logging.info("draw text")
        Font1 = ImageFont.truetype("Font/Font01.ttf", 25)
        Font2 = ImageFont.truetype("Font/Font01.ttf", 35)
        Font3 = ImageFont.truetype("Font/Font02.ttf", 32)
        draw.rectangle([(0, 65), (140, 100)], fill="WHITE")
        draw.text((5, 68), 'Hello world', fill="BLACK", font=Font1)
        draw.rectangle([(0, 115), (190, 160)], fill="RED")
        draw.text((5, 118), 'WaveShare', fill="WHITE", font=Font2)
        draw.text((5, 160), '1234567890', fill="GREEN", font=Font3)
        text = u"微雪电子"
        draw.text((5, 200), text, fill="BLUE", font=Font3)
        im_r = image1.rotate(270)
        screen.show_image(im_r)
        time.sleep(1)

        logging.info("show image")
        image = Image.open('image/pic.jpg')
        im_r = image.rotate(270)
        screen.show_image(im_r)
        time.sleep(1)

        for i in range(10):
            screen.show_gif("image/connecting.gif")

    Thread(target=test, args=(screen,)).start()
    screen.main_loop()

import logging
from PIL import Image, ImageDraw, ImageTk
import tkinter as tk

logger = logging.getLogger()


class SimulatedST7789:
    width = 240
    height = 240

    def __init__(self):
        self.image = Image.new('RGB', (self.width, self.height), 'WHITE')
        self.root = tk.Tk()
        self.root.title("Simulated Display")
        self.canvas = tk.Canvas(self.root, width=self.width, height=self.height)
        self.canvas.pack()
        self.tk_image = ImageTk.PhotoImage(self.image)
        self.gif_frames = []
        self.frame_index = 0

    def command(self, cmd):
        logger.debug(f"Command sent: {cmd}")

    def data(self, val):
        logger.debug(f"Data sent: {val}")

    def reset(self):
        logger.debug("Display reset")

    def init(self):
        logger.debug("Initializing display")

    def show_image(self, Image: Image.Image):
        if Image.size != (self.width, self.height):
            raise ValueError(f'Image must be same dimensions as display ({self.width}x{self.height}).')
        self.image = Image
        self.tk_image = ImageTk.PhotoImage(self.image)  # 更新Tkinter图像
        self.canvas.create_image(0, 0, image=self.tk_image, anchor=tk.NW)
        self.root.update()

    def clear(self):
        self.image = Image.new('RGB', (self.width, self.height), 'WHITE')
        self.tk_image = ImageTk.PhotoImage(self.image)  # 更新Tkinter图像
        self.canvas.create_image(0, 0, image=self.tk_image, anchor=tk.NW)
        self.root.update()

    def bl_DutyCycle(self, duty: int):
        logger.debug(f"Setting backlight duty cycle to {duty}")

    def main_loop(self):
        self.root.mainloop()


if __name__ == "__main__":
    display = SimulatedST7789()
    display.init()
    display.clear()
    display.main_loop()

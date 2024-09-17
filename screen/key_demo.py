# -*- coding:utf-8 -*-
from PIL import Image, ImageDraw

import ST7789

disp = ST7789.ST7789()
disp.init()
disp.clear()
disp.bl_DutyCycle(50)

# Create blank image for drawing.
# Make sure to create image with mode '1' for 1-bit color.
image1 = Image.new("RGB", (disp.width, disp.height), "WHITE")

# Get drawing object to draw on image.
draw = ImageDraw.Draw(image1)

# Draw a black filled box to clear the image.
draw.rectangle((0, 0, disp.width, disp.height), outline=0, fill=0)
disp.show_image(image1)

try:
    while True:
        # with canvas(device) as draw:
        if disp.digital_read(disp.GPIO_KEY_UP_PIN) == 0:
            # button is released
            # Up
            draw.polygon([(20, 20), (30, 2), (40, 20)], outline=255, fill=0xff00)
        else:
            # button is pressed:
            # Up filled
            draw.polygon([(20, 20), (30, 2), (40, 20)], outline=255, fill=0)
            print("Up")

        if disp.digital_read(disp.GPIO_KEY_LEFT_PIN) == 0:
            # button is released
            # left
            draw.polygon([(0, 30), (18, 21), (18, 41)], outline=255, fill=0xff00)
        else:
            # button is pressed:
            # left filled
            draw.polygon([(0, 30), (18, 21), (18, 41)], outline=255, fill=0)
            print("left")

        if disp.digital_read(disp.GPIO_KEY_RIGHT_PIN) == 0:
            # button is released
            # right
            draw.polygon([(60, 30), (42, 21), (42, 41)], outline=255, fill=0xff00)
        else:
            # button is pressed:
            # right filled
            draw.polygon([(60, 30), (42, 21), (42, 41)], outline=255, fill=0)
            print("right")

        if disp.digital_read(disp.GPIO_KEY_DOWN_PIN) == 0:
            # button is released
            # down
            draw.polygon([(30, 60), (40, 42), (20, 42)], outline=255, fill=0xff00)
        else:
            # button is pressed:
            # down filled
            draw.polygon([(30, 60), (40, 42), (20, 42)], outline=255, fill=0)
            print("down")

        if disp.digital_read(disp.GPIO_KEY_PRESS_PIN) == 0:
            # button is released
            # center
            draw.rectangle((20, 22, 40, 40), outline=255, fill=0xff00)
        else:
            # button is pressed:
            # center filled
            draw.rectangle((20, 22, 40, 40), outline=255, fill=0)
            print("center")

        disp.show_image(image1)
except Exception as e:
    print(f"{e}")

disp.module_exit()

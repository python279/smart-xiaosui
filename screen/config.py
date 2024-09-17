import logging
import time

import numpy as np
import spidev
from gpiozero import *

# GPIO define
KEY_UP_PIN = 6
KEY_DOWN_PIN = 16
KEY_LEFT_PIN = 5
KEY_RIGHT_PIN = 26
KEY_PRESS_PIN = 13


class RaspberryPi:
    def __init__(self, spi=spidev.SpiDev(0, 0), spi_freq=40000000, rst=27, dc=25, bl=24, bl_freq=1000, i2c=None,
                 i2c_freq=100000):
        self.np = np
        self.INPUT = False
        self.OUTPUT = True

        self.SPEED = spi_freq
        self.BL_freq = bl_freq

        self.GPIO_RST_PIN = self.gpio_mode(rst, self.OUTPUT)
        self.GPIO_DC_PIN = self.gpio_mode(dc, self.OUTPUT)
        self.GPIO_BL_PIN = self.gpio_pwm(bl)
        self.bl_DutyCycle(0)

        # init GPIO
        # self.GPIO_KEY_UP_PIN = self.gpio_mode(KEY_UP_PIN, self.INPUT, True, None)
        # self.GPIO_KEY_DOWN_PIN = self.gpio_mode(KEY_DOWN_PIN, self.INPUT, True, None)
        # self.GPIO_KEY_LEFT_PIN = self.gpio_mode(KEY_LEFT_PIN, self.INPUT, True, None)
        # self.GPIO_KEY_RIGHT_PIN = self.gpio_mode(KEY_RIGHT_PIN, self.INPUT, True, None)
        # self.GPIO_KEY_PRESS_PIN = self.gpio_mode(KEY_PRESS_PIN, self.INPUT, True, None)

        # Initialize SPI
        self.SPI = spi
        if self.SPI != None:
            self.SPI.max_speed_hz = spi_freq
            self.SPI.mode = 0b00

    def gpio_mode(self, Pin, Mode, pull_up=None, active_state=True):
        if Mode:
            return DigitalOutputDevice(Pin, active_high=True, initial_value=False)
        else:
            return DigitalInputDevice(Pin, pull_up=pull_up, active_state=active_state)

    def digital_write(self, Pin, value):
        if value:
            Pin.on()
        else:
            Pin.off()

    def digital_read(self, Pin):
        return Pin.value

    def delay_ms(self, delaytime):
        time.sleep(delaytime / 1000.0)

    def gpio_pwm(self, Pin):
        return PWMOutputDevice(Pin, frequency=self.BL_freq)

    def spi_writebyte(self, data):
        if self.SPI is not None:
            self.SPI.writebytes(data)

    def bl_DutyCycle(self, duty):
        self.GPIO_BL_PIN.value = duty / 100

    def bl_Frequency(self, freq):  # Hz
        self.GPIO_BL_PIN.frequency = freq

    def module_init(self):
        if self.SPI is not None:
            self.SPI.max_speed_hz = self.SPEED
            self.SPI.mode = 0b00
        return 0

    def module_exit(self):
        logging.debug("spi end")
        if self.SPI is not None:
            self.SPI.close()

        logging.debug("gpio cleanup...")
        self.digital_write(self.GPIO_RST_PIN, 1)
        self.digital_write(self.GPIO_DC_PIN, 0)
        self.GPIO_BL_PIN.close()
        time.sleep(0.001)

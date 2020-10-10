#!/usr/bin/python

from threading import Thread
from enum import Enum

import RPi.GPIO as GPIO
import time



# Operating modes for the PWM Cycler
# ============================================================================
#   OFF             Keep the pin value to GPIO.LOW until further notice
#   NORMAL          Send pulses with the given duty cycle
#   FULL_THROTTLE   Keep the pin value to GPIO.HIGH until further notice
class PwmCyclerOperatingMode(Enum):
    OFF = 1
    NORMAL = 2
    FULL_THROTTLE = 3

# Simple PWM cycler
# ============================================================================
# Maintains a separate thread which sends pulses using GPIO.OUT at an interval
# between 5ms and 10ms, depending on the set duty cycle
# 
class PwmCycler:
    CYCLE_LENGTH_SECS = 1.0
    FULL_THROTLE_THRESHOLD_PERCENT = 0.95
    FULL_TROTTLE_SLEEP_SECS = 1

    def __init__(self, pin):
        self.pin = pin
        self.started = False
        self.sleepSecs = self.CYCLE_LENGTH_SECS
        self.pulseLengthSecs = 0.0
        self.operatingMode = PwmCyclerOperatingMode.NORMAL
        self.isGpioHigh = False
        self.isGpioLow = False


    def setCycleLengthMS(self, ms):
        self.CYCLE_LENGTH_SECS = float(ms) / float(1000)

    def validateConfig(self):
        if self.CYCLE_LENGTH_SECS <= 0:
            raise Exception("CYCLE_LENGTH_SECS must be greater than 0")

    def start(self):
        self.started = True
        self.pwmThread = Thread(name='pwm', target = self.cycle)
        self.pwmThread.setDaemon(True)
        self.pwmThread.start()

    def stop(self):
        self.validateConfig()
        self.started = False
        GPIO.output(self.pin, GPIO.LOW)

    def setDutyCycle(self, dutyCyclePercent):
        if dutyCyclePercent > self.FULL_THROTLE_THRESHOLD_PERCENT:
            self.operatingMode = PwmCyclerOperatingMode.FULL_THROTTLE
        elif dutyCyclePercent == 0:
            self.operatingMode = PwmCyclerOperatingMode.OFF
        else:
            self.operatingMode = PwmCyclerOperatingMode.NORMAL
            self.pulseLengthSecs = float(self.CYCLE_LENGTH_SECS) * float(dutyCyclePercent)
            self.sleepSecs = float(self.CYCLE_LENGTH_SECS) - self.pulseLengthSecs

    def cycle(self):
        while self.started:
            if self.operatingMode == PwmCyclerOperatingMode.OFF:
                self.keepPinOff()
            elif self.operatingMode == PwmCyclerOperatingMode.NORMAL:
                self.pwmCycle()
            elif self.operatingMode == PwmCyclerOperatingMode.FULL_THROTTLE:
                self.fullThrottleCycle()

    def fullThrottleCycle(self):
        if not self.isGpioHigh:
            GPIO.output(self.pin, GPIO.HIGH)
        time.sleep(self.FULL_TROTTLE_SLEEP_SECS)

    def pwmCycle(self):
        GPIO.output(self.pin, GPIO.HIGH)
        time.sleep(self.pulseLengthSecs)
        GPIO.output(self.pin, GPIO.LOW)
        time.sleep(self.sleepSecs)

    def keepPinOff(self):
        if not self.isGpioLow:
            GPIO.output(self.pin, GPIO.LOW)
        time.sleep(self.FULL_TROTTLE_SLEEP_SECS)

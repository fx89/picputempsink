#!/usr/bin/python

from threading import Thread
from enum import Enum
import time

import pwm as PWM
import shell



# CPU threshold definition
# ============================================================================
# Configuration item for the CpuTempSink class. One ore more thresholds can be
# added to the CpuTempSink.  It will set the duty cycle to the specified value
# when the CPU temperature is over the specified value.
class CpuTempSinkThreshold:
    def __init__(self, tempC, dutyCyclePercent):
        self.tempC = tempC
        self.dutyCyclePercent = dutyCyclePercent

    def __str__(self):
        return "[temp(C): {0}, cycle(%): {1}]".format(self.tempC, self.dutyCyclePercent);

# And a sort key function to help sorting arrays of CpuTempSinkThreshold's
def thresholdsHighTempSortKey(threshold):
    return threshold.tempC



# Operating mode options for the CpuTempSink
# ============================================================================
# The CPU temperature sink executor may operate in the following modes:
#                      -------------------------------------------------------
#   SINE             : The CPU fan speed rises gradually, as temperature goes
#                      up, and decreases gradually, as temperature goes down.
#                      -------------------------------------------------------
#   SAWTOOTH         : The CPU fan speed rises gradually, as the temperature
#                      goes up. Upon reaching maximum speed the CPU fan keeps
#                      spinning at that speed until the temperature falls back
#                      below the lowest value configured across all thresholds.
#                      -------------------------------------------------------
#   INVERSE_SAWTOOTH : The CPU fan is stopped until the temperature has risen
#                      to the greatest configured value across all thresholds.
#                      After that, the CPU fan starts spinning at the maximum
#                      configured speed and gradually spins down as temperature
#                      decreases.
#                      -------------------------------------------------------
#
#   ======================
#   !!! IMPORTANT NOTE !!!
#   ======================
#   Operating modes are relevant only when the CpuTempSink is configured with
#   several temperature thresholds.
#
class OperatingMode(Enum):
    BAD_OPERATING_MODE = 0
    SINE = 1
    SAWTOOTH = 2
    INVERSE_SAWTOOTH = 3

    def __str__(self):
        if self == OperatingMode.SINE:
            return "SINE"
        elif self == OperatingMode.SAWTOOTH:
            return "SAWTOOTH"
        elif self == OperatingMode.INVERSE_SAWTOOTH:
            return "INVERSE_SAWTOOTH"
        else:
            return "BAD OPERATING MODE"

def operatingMode(strOperatingMode):
    if strOperatingMode == "SINE":
        return OperatingMode.SINE
    elif strOperatingMode == "SAWTOOTH":
        return OperatingMode.SAWTOOTH
    elif strOperatingMode == "INVERSE_SAWTOOTH":
        return OperatingMode.INVERSE_SAWTOOTH
    else:
        return OperatingMode.BAD_OPERATING_MODE



# Direction in witch temperature is going
class TempDirection(Enum):
    FALLING = 0
    STEADY = 1
    RISING = 2

    def __str__(self):
        if self == TempDirection.FALLING:
            return "FALLING"
        elif self == TempDirection.STEADY:
            return "STEADY"
        elif self == TempDirection.RISING:
            return "RISING"
        else:
            return "BAD DIRECTION"



# CPU temperature sink executor
# ============================================================================
# Monitors the CPU temperature and applies the PWM duty cycle as specified by
# the given configuration
class CpuTempSink:
    CYCLE_INTERVAL_SECS = 5
    NO_THRESHOLD_INDEX = 000

    def __init__(self, pwmCycler):
        self.pwmCycler = pwmCycler
        self.thresholds = []
        self.nThresholds = 0
        self.isRunning = False
        self.currentThrtesholdIndex = self.NO_THRESHOLD_INDEX
        self.tempDirection = TempDirection.RISING
        self.prevCpuTempC = -100
        self.prevPrevCpuTempC = -100
        self.cpuTempC = shell.getCpuTempC()
        self.operatingMode = OperatingMode.SAWTOOTH
        self.currentDutyCycle = 0.0

    def setCycleIntervalSecs(self, cycleIntervalSecs):
        self.CYCLE_INTERVAL_SECS = cycleIntervalSecs
        return self

    def addThreshold(self, threshold):
        self.thresholds.append(threshold)
        self.thresholds.sort(key=thresholdsHighTempSortKey, reverse=True)
        self.nThresholds = self.nThresholds + 1
        return self

    def setOperatingMode(self, operatingMode):
        self.operatingMode = operatingMode

    def validateConfig(self):
        if self.nThresholds <= 0:
            raise Exception("No thresholds defined. At least one threshold must be defined.")
        if self.CYCLE_INTERVAL_SECS < 1:
            raise Exception("The configured cycle interval must be at least 1 second.")

    def start(self):
        self.validateConfig()
        self.isRunning = True
        self.pwmCycler.start()
        self.tempSinkThread = Thread(name='tempSink', target = self.cycle)
        self.tempSinkThread.setDaemon(True)
        self.tempSinkThread.start()

    def stop(self):
        self.isRunning = False
        self.pwmCycler.stop()

    def cycle(self):
        while self.isRunning:
            self.cpuMonitoring()
            self.lockOnThreshold()
            self.cpuThrottling()
            time.sleep(self.CYCLE_INTERVAL_SECS)

    def cpuMonitoring(self):
        self.cpuTempC = shell.getCpuTempC()

        if self.cpuTempC > self.prevCpuTempC and self.cpuTempC > self.prevPrevCpuTempC:
            self.tempDirection = TempDirection.RISING
        elif self.cpuTempC < self.prevCpuTempC and self.cpuTempC < self.prevPrevCpuTempC:
            self.tempDirection = TempDirection.FALLING
        else:
            self.tempDirection = TempDirection.STEADY

        self.prevPrevCpuTempC = self.prevCpuTempC
        self.prevCpuTempC = self.cpuTempC

    def lockOnThreshold(self):
        for t in range(self.nThresholds):
            if self.cpuTempC > self.thresholds[t].tempC:
                self.currentThrtesholdIndex = t
                return

    def cpuThrottling(self):
        if self.operatingMode == OperatingMode.SINE:
            self.cpuThrottlingSine()
        elif self.operatingMode == OperatingMode.SAWTOOTH:
            self.cpuThrottlingSawtooth()
        elif self.operatingMode == OperatingMode.INVERSE_SAWTOOTH:
            self.cpuThrottlingInverseSawtooth()

    def cpuThrottlingSine(self):
        self.setDutyCycleForCurrentThreshold()

    def cpuThrottlingSawtooth(self):
        if self.tempDirection == TempDirection.RISING:
            self.setDutyCycleForCurrentThreshold()
            return

    def cpuThrottlingInverseSawtooth(self):
        if self.tempDirection == TempDirection.RISING:
            if self.currentThrtesholdIndex == 0:
                self.setDutyCycleForCurrentThreshold()
        elif self.tempDirection == TempDirection.FALLING:
            self.setDutyCycleForCurrentThreshold()

    def setDutyCycleForCurrentThreshold(self):
        self.currentDutyCycle = self.thresholds[self.currentThrtesholdIndex].dutyCyclePercent
        self.pwmCycler.setDutyCycle(self.currentDutyCycle)

    def printStatus(self):
        print "=================================================="
        print self.getStatusString()
        print "=================================================="

    def getStatusString(self):
        ret  = "Operating mode     : {0}".format(self.operatingMode) + "\r\n"
        ret += "Temp               : {0}C, {1}".format(self.cpuTempC, self.tempDirection) + "\r\n"
        ret += "Duty cycle         : {0}".format(self.currentDutyCycle) + "\r\n"
        ret += "Operating threshold: " + self.getThresholdString()
        return ret

    def getThresholdString(self):
        if (self.currentThrtesholdIndex == self.NO_THRESHOLD_INDEX):
            return "Threshold not yet detected"
        else:
            return str(self.thresholds[self.currentThrtesholdIndex])
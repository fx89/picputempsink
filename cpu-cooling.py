#!/usr/bin/python

import time
import RPi.GPIO as GPIO
import UTILS.cputempsink as TEMPSINK
import UTILS.shell as SHELL
import UTILS.pwm as PWM
import UTILS.os as OS
import configparser
import json



# Get INI and LOG file references
INI_FILE_PATHNAME = OS.getParamFromCmdEnvDefault(1, "CPU_COOLING_INI_FILE_PATHNAME", "cpu-cooling.ini")
LOG_FILE_PATHNAME = OS.getParamFromCmdEnvDefault(2, "CPU_COOLING_LOG_FILE_PATHNAME", "cpu-cooling.log")



# Read runtime parameters from config
# -----------------------------------------------------------------------------------------
# Parse the INI file
config = configparser.ConfigParser()
config.read(INI_FILE_PATHNAME)

# Get the service parameters
FAN_PIN                           = int(config['Service']['FAN_PIN'])
MAIN_THREAD_POLLING_INTERVAL_SECS = int(config['Service']['MAIN_THREAD_POLLING_INTERVAL_SECS'])

# Get the TempSink parameters
TEMPSINK_OPERATING_MODE           = TEMPSINK.operatingMode(config['TempSink']['TEMPSINK_OPERATING_MODE'])
TEMPSINK_CYCLE_INTERVAL_SECS      = int(config['TempSink']['CYCLE_INTERVAL_SECS'])

# Get the PWM parameters
PWM_CYCLE_LENGTH_MS    = float(config['PWM']['CYCLE_LENGTH_MS'])

# Get the thresholds for the TempSink
thresholds = []
nThresholds = 0
isLoadingThresholds = True
#
while isLoadingThresholds:
    try:
        thresholds.append(json.loads(config['Thresholds']["threshold{0}".format(nThresholds)]))
        nThresholds = nThresholds + 1
    except:
        isLoadingThresholds = False
# -----------------------------------------------------------------------------------------
        
        

# Init GPIO
GPIO.setwarnings(False)
GPIO.cleanup(FAN_PIN)
GPIO.setmode(GPIO.BOARD)
GPIO.setup(FAN_PIN, GPIO.OUT)

#Init PWM
pwm = PWM.PwmCycler(FAN_PIN)
pwm.setCycleLengthMS(PWM_CYCLE_LENGTH_MS)

# Init TEMPSINK
tempSink = TEMPSINK.CpuTempSink(pwm)
tempSink.setOperatingMode(TEMPSINK_OPERATING_MODE)
tempSink.setCycleIntervalSecs(TEMPSINK_CYCLE_INTERVAL_SECS)

# Add thresholds
for threshold in thresholds:
    tempC = int(threshold["tempC"])
    dutyCyclePercent = float(threshold["dutyCyclePercent"])
    tempSink.addThreshold(TEMPSINK.CpuTempSinkThreshold(tempC, dutyCyclePercent))



# -----------------------------------------------------------------------------------------



# Run
tempSink.start()

# Monitoring thread
while True:
    time.sleep(MAIN_THREAD_POLLING_INTERVAL_SECS)
    with open(LOG_FILE_PATHNAME, 'w') as file_object:
        file_object.write(tempSink.getStatusString())


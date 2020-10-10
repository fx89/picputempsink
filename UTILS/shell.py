#!/usr/bin/python

from subprocess import Popen, PIPE
import os

# Returns the CPU temperature in C as a rounded down integer
def getCpuTempC():
    output = Popen(["cat", "/sys/class/thermal/thermal_zone0/temp"],stdout=PIPE)
    response = output.communicate()
    strCpuTemp = "{0}".format(response)[2:7]
    return int(strCpuTemp) / 1000

# Function to clear the console
clear = lambda: os.system('clear')
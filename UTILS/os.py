#!/usr/bin/python

import sys
import os

# Get parameter value from the command line or environment variables
# Return the default if a value is not provided by either means
def getParamFromCmdEnvDefault(cmdLinePos, envVarName, defaultValue):
    ret = None
    #
    if len(sys.argv) > cmdLinePos:
        ret = sys.argv[cmdLinePos]
    #
    if ret is None or len(ret) == 0:
        try:
            ret = os.environ[envVarName]
        except:
            ret = None
    #
    if ret is None or len(ret) == 0:
        ret = defaultValue
    #
    return ret

"""
@author : Aymen Brahim Djelloul
date : 29.07.2024
version : 1.0.1
License : MIT

    // BatteryPy is a lightweight and pure python library for Windows
    that allow you to retrieve battery information from your device

    BatteryPy can guess :

    - Battery manufacturer
    - Battery chemistry
    - Battery Voltage
    - Battery percentage
    - tells is battery plugged
    - Battery health
    - Battery estimated duration
    - current power mode on the system
    - tells is fast charged

    How Its Work ?
        BatteryPy uses integrated tools on the operating system it self to gather
        battery and power management information and parse it


"""

# IMPORTS
from exceptions import NotSupportedPlatform
import platform
import sys

# DEFINE THE PLATFORM
_platform: str = platform.system()

# DEFINE GLOBAL VARIABLES
AUTHOR = "Aymen Brahim Djelloul"
VERSION = "1.0.1"

supported_platforms = ("Windows", "Linux")


if _platform == "Windows":
    from __windows_batterypy import *
elif _platform == "linux":
    from __linux_batterypy import *
else:
    raise NotSupportedPlatform("Battery Py support only Windows and Linux-debian systems")

if __name__ == "__main__":
    sys.exit()
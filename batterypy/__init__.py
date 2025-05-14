"""
This code or file is part of 'BatteryPy' project
copyright (c) 2023, Aymen Brahim Djelloul, All rights reserved.
use of this source code is governed by MIT License that can be found on the project folder.

@author : Aymen Brahim Djelloul
version : 1.1
date    : 14.05.2025
License : MIT

"""

# IMPORTS
import sys
from platform import system as system_name


__CURRENT_PLATFORM: str = system_name()

# Initialize BatteryPy
if __CURRENT_PLATFORM == "Windows":
    from ._win_battery import *
elif __CURRENT_PLATFORM == "Linux":
    from ._linux_battery import *
else:
    sys.exit("Unsupported platform")

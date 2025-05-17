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
from platform import system

# CONSTANTS
VERSION: str = "1.1"
CURRENT_PLATFORM: str = system()

# Initialize BatteryPy
if CURRENT_PLATFORM == "Windows":
    from ._win_battery import *
elif CURRENT_PLATFORM == "Linux":
    from ._linux_battery import *
else:
    sys.exit("Unsupported platform")

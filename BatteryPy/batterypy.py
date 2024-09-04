"""
This code or file is part of 'BatteryPy' project
copyright (c) 2023, Aymen Brahim Djelloul, All rights reserved.
use of this source code is governed by MIT License that can be found on the project folder.

@author : Aymen Brahim Djelloul
version : 1.1
date : 03.09.2024
Licens : MIT


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
        BatteryPy use built-in tools with drivers in the operating system and parse it
        to gather battery information including all specs and capacity and charge percent etc .

"""

# IMPORTS
import sys
from exceptions import *

# DECLARE BASIC VARIABLES
AUTHOR: str = "Aymen Brahim Djelloul"
VERSION: float = 1.1
SUPPORTED_PLATFORMS: tuple = ("Windows", "Linux")


class BatteryPy:

    def get_all_info(self) -> dict:
        """ This method will return a dictionary of all battery informations"""

    def get_csv_report(self, path: str) -> None:
        """ This method will save the battery info in csv"""

    def _get_file_content(self, file_path: str) -> str:
        """ This method will read the given file path and return its content"""
        return open(file_path, 'r', buffering=1).read()



if sys.platform == "win32":

    class Battery(BatteryPy):
        pass


elif sys.platform == "linux":

    class Battery(BatteryPy):
        
        def __init__(self) -> None:
            super(Battery, self).__init__()

            # Check for battery info paths
            if not self._is_battery():
                raise BatteryNotFound()

        def manufacturer(self) -> str:
            """ This method will get the battery manufacturer name string"""

        def chemistry(self) -> str:
            """ This method will get the battery chemistry type string"""

        def battery_voltage(self) -> float:
            """ This method will get the battery designed voltage"""

        def battery_percentage(self) -> int:
            """ This method will get the current battery percentage"""

        def battery_health(self) -> int:
            """ This method will get the current battery health or capacity"""

        def is_plugged(self) -> bool:
            """ This method will check if the battery is plugged to electricity"""

        def power_manegement_mode(self) -> str:
            """ This method will get the current power mode"""

        def is_fast_charge(self) -> bool:
            """ This method will check if the battery is charging fast or not (above 20 Watts)"""

        def _is_battery(self) -> bool:
            """ This method will check is there is battery or not"""



else:
    raise NotSupportedPlatform(sys.platform)

if __name__ == "__main__":
    sys.exit()

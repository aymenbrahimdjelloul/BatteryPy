"""
This code or file is part of 'BatteryPy' project
copyright (c) 2023, Aymen Brahim Djelloul, All rights reserved.
use of this source code is governed by MIT License that can be found on the project folder.

@author : Aymen Brahim Djelloul
version : 1.0.0
date : 30.07.2024
License : MIT

        // This is the BatteryPy implementation for Linux system //

"""

# IMPORTS
import subprocess
import sys


class Battery:
    
    @property
    def manufacturer(self):
        """ This method will get the manufacturer of battery"""

    @property
    def chemistry(self):
        """ This method will return the chemistry type of battery"""

    @property
    def type(self):
        """ This method will return the device battery type"""

    @property
    def get_current_voltage(self):
        """ This method will return the battery design voltage"""
    
    @property
    def battery_percentage(self):
        """ This method will return the current battery percentage"""

    @property
    def battery_health(self):
        """ This method will get the battery health or capacity"""

    @property
    def is_plugged(self):
        """ This method will get if the battery is currently charging"""

    def is_fast_charging(self):
        """ This method will get if the battery is charging fast or not"""

    def power_management_mode(self):
        """ This method will get the current OS power mode"""


if __name__ == "__main__":
    sys.exit()

"""
This code or file is part of 'BatteryPy' project
copyright (c) 2023-2025 , Aymen Brahim Djelloul, All rights reserved.
use of this source code is governed by MIT License that can be found on the project folder.


@author : Aymen Brahim Djelloul
version : 1.2
date    : 17.05.2025
License : MIT

"""

# IMPORTS
import sys


class _NotSupportedPlatform(BaseException):

    def __init__(self, current_platform: str) -> None:
        self.current_platform = current_platform

    def __str__(self) -> str:
        return f"BatteryPy is doesn't support '{self.current_platform}' Operating system."


class _NotSupportedDriver(BaseException):

    def __init__(self, driver: str) -> None:
        self.driver_name = driver

    def __str__(self) -> str:
        return f"BatteryPy can't reach '{self.driver_name}' driver which is necessary\nTry to update your system."


class _BatteryNotDetected(Exception):
    def __str__(self):
        return "Battery not detected on this system."


if __name__ == "__main__":
    sys.exit()

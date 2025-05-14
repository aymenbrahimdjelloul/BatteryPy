"""
@author: Aymen Brahim Djelloul
date : 29.07.2023
License: MIT

"""

# IMPORTS
import sys


class NotSupportedPlatform(BaseException):

    def __init__(self, current_platform: str):
        self.current_platform = current_platform

    def __str__(self) -> str:
        return f"BatteryPy is doesn't support '{self.current_platform}' Operating system."


class NotSupportedDriver(BaseException):

    def __init__(self, driver: str):
        self.driver_name = driver

    def __str__(self) -> str:
        return f"BatteryPy can't reach '{self.driver_name}' driver which is necessary\nTry to update your system."


class NotSupportedDeviceType(BaseException):

    def __str__(self):
        return f"Your Device Doesn't have Battery or it can't be reached"


if __name__ == "__main__":
    sys.exit()

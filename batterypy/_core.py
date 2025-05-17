"""
This code or file is part of 'BatteryPy' project
copyright (c) 2023, Aymen Brahim Djelloul, All rights reserved.
use of this source code is governed by MIT License that can be found on the project folder.

@author: Aymen Brahim Djelloul
version: 1.1
date: 14.05.2025
License: MIT

"""

# IMPORTS
import os
import sys
import ctypes
import subprocess
from batterypy import CURRENT_PLATFORM


class _Const:

    # DECLARE GLOBAL VARIABLES
    SUPPORTED_PLATFORMS: tuple = ("Windows", "Linux")

    # Set the fast charge rate at 30 Watts
    FAST_CHARGE_RATE: int = 30000


def _milliwatts_to_watts(value: int) -> int:
    """ This method will convert milliwatts to watts"""
    return int(value / 1000)


def _milliwatts_hour_to_milliampere_hour(self, value: int) -> int:
    """ This method will convert milliwatts-hour to milliampere-hour"""
    return int(value / int(self.get_current_voltage(False)))


def _is_battery(system_name: str) -> bool:
    """
    Detects if the system is running on battery power.
    Returns:
        bool: True if on battery, False if plugged in.
              Exits on undetectable.
    """

    try:
        if CURRENT_PLATFORM == system_name:
            # Using SYSTEM_POWER_STATUS struct from Windows API
            class SYSTEM_POWER_STATUS(ctypes.Structure):
                _fields_ = [
                    ('ACLineStatus', ctypes.c_byte),
                    ('BatteryFlag', ctypes.c_byte),
                    ('BatteryLifePercent', ctypes.c_byte),
                    ('Reserved1', ctypes.c_byte),
                    ('BatteryLifeTime', ctypes.c_ulong),
                    ('BatteryFullLifeTime', ctypes.c_ulong)
                ]

            status = SYSTEM_POWER_STATUS()
            if not ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(status)):
                sys.exit("[ERROR] Unable to get power status from Windows API")

            if status.ACLineStatus == 0:
                return True  # On battery
            elif status.ACLineStatus == 1:
                return False  # On AC
            else:
                sys.exit("[ERROR] Battery status undetectable (Windows)")

        elif CURRENT_PLATFORM == system_name:
            # Check common AC adapter sysfs files
            ac_paths = [
                "/sys/class/power_supply/AC/online",
                "/sys/class/power_supply/AC0/online",
                "/sys/class/power_supply/ACAD/online",
                "/sys/class/power_supply/Mains/online"
            ]

            for path in ac_paths:
                if os.path.exists(path):
                    with open(path, "r") as f:
                        status = f.read().strip()
                        return status != "1"  # True if not online (battery)

            sys.exit("[ERROR] AC adapter status undetectable (Linux)")

        elif CURRENT_PLATFORM == system_name:  # macOS
            output = subprocess.check_output(["pmset", "-g", "batt"], universal_newlines=True)
            output = output.lower()
            if "discharging" in output:
                return True
            elif "charging" in output or "charged" in output:
                return False

            sys.exit("[ERROR] Battery status undetectable (macOS)")

        else:
            sys.exit(f"[ERROR] Unsupported OS: {CURRENT_PLATFORM}")

    except Exception as e:
        sys.exit(f"[ERROR] Failed to detect battery status: {e}")



if __name__ == "__main__":
    sys.exit()

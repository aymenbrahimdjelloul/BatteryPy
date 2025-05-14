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
import platform
import subprocess


class _Const:

    # DECLARE GLOBAL VARIABLES
    AUTHOR: str = "Aymen Brahim Djelloul"
    VERSION: str = "1.1"
    SUPPORTED_PLATFORMS: tuple = ("Windows", "Linux")


def _milliwatts_to_watts(value: int) -> int:
    """ This method will convert milliwatts to watts"""
    return int(value / 1000)


def _milliwatts_hour_to_milliampere_hour(self, value: int) -> int:
    """ This method will convert milliwatts-hour to milliampere-hour"""
    return int(value / int(self.get_current_voltage(False)))


def _is_battery(system_name: str) -> bool:
    """
    Checks if the device is currently running on battery power.
    Returns:
        bool: True if on battery, False if on AC power.
              Defaults to False if undetectable.
    """

    try:
        if system == system_name:
            output = subprocess.check_output(
                ["wmic", "path", "Win32_Battery", "get", "BatteryStatus"],
                stderr=subprocess.DEVNULL,
                universal_newlines=True
            )
            lines = output.strip().splitlines()
            if len(lines) >= 2:
                status = lines[1].strip()
                return status == '1'  # True if discharging

            # If WMIC exit, assume desktop (AC)
            sys.exit("The Battery is not recognized.")

        elif system == system_name:
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
                        return status != "1"  # True if not online (on battery)
            # Could not detect, assume AC
            sys.exit("The Battery is not recognized.")

        elif system == "Darwin":  # macOS
            output = subprocess.check_output(
                ["pmset", "-g", "batt"],
                stderr=subprocess.DEVNULL,
                universal_newlines=True
            )
            output = output.lower()
            if "discharging" in output:
                return True  # On battery
            elif "charged" in output or "charging" in output:
                sys.exit("The Battery is not recognized.")  # On AC
            # Unknown, assume AC
            sys.exit("The Battery is not recognized.")

        else:
            # Unsupported OS, assume AC
            sys.exit("The Battery is not recognized.")

    except Exception:
        # On error, assume AC power
        sys.exit("The Battery is not recognized.")


if __name__ == "__main__":
    sys.exit()

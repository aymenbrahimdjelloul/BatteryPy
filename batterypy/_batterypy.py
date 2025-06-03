"""
This code or file is part of 'BatteryPy' project
copyright (c) 2023-2025 , Aymen Brahim Djelloul, All rights reserved.
use of this source code is governed by MIT License that can be found on the project folder.

@author : Aymen Brahim Djelloul
version : 1.3
date    : 03.06.2025
License : MIT

"""

# IMPORTS
import os
import re
import sys
import ctypes
import subprocess
from platform import system
from typing import Dict, Optional, Union
from ctypes import wintypes, Structure, byref
from datetime import datetime
from ._exceptions import _BatteryNotDetected


class _Const:

    # Declare software constants
    author: str = "Aymen Brahim Djelloul"
    version: str = "1.3"
    app_caption: str = f"BatteryPy - v{version}"
    app_website: str = "https://github.com/aymenbrahimdjelloulBatteryPy"

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
        if __CURRENT_PLATFORM == system_name:

            # Using _SYSTEM_POWER_STATUS struct from Windows API
            class _SYSTEM_POWER_STATUS(ctypes.Structure):
                _fields_ = [
                    ('ACLineStatus', ctypes.c_byte),
                    ('BatteryFlag', ctypes.c_byte),
                    ('BatteryLifePercent', ctypes.c_byte),
                    ('Reserved1', ctypes.c_byte),
                    ('BatteryLifeTime', ctypes.c_ulong),
                    ('BatteryFullLifeTime', ctypes.c_ulong)
                ]

            status = _SYSTEM_POWER_STATUS()
            if not ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(status)):
                raise _BatteryNotDetected("[ERROR] Unable to get power status from Windows API")

            if status.ACLineStatus == 0:
                return True  # On battery
            elif status.ACLineStatus == 1:
                return False

            else:
                raise _BatteryNotDetected("[ERROR] Battery status undetectable (Windows)")

        elif __CURRENT_PLATFORM == system_name:
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

            raise _BatteryNotDetected("[ERROR] AC adapter status undetectable (Linux)")

        elif __CURRENT_PLATFORM == system_name:  # macOS
            output = subprocess.check_output(["pmset", "-g", "batt"], universal_newlines=True)
            output = output.lower()
            if "discharging" in output:
                return True
            elif "charging" in output or "charged" in output:
                return False

            raise _BatteryNotDetected("[ERROR] Battery status undetectable (macOS)")

        else:
            raise _BatteryNotDetected(f"[ERROR] Unsupported OS: {__CURRENT_PLATFORM}")

    except Exception as e:
        raise _BatteryNotDetected(e)


class _SYSTEM_BATTERY_STATE(Structure):
    """Windows API structure for battery information"""

    _fields_ = [
        ("AcOnLine", wintypes.BOOLEAN),
        ("BatteryPresent", wintypes.BOOLEAN),
        ("Charging", wintypes.BOOLEAN),
        ("Discharging", wintypes.BOOLEAN),
        ("Spare1", wintypes.BOOLEAN * 4),
        ("MaxCapacity", wintypes.DWORD),
        ("RemainingCapacity", wintypes.DWORD),
        ("Rate", wintypes.DWORD),
        ("EstimatedTime", wintypes.DWORD),
        ("DefaultAlert1", wintypes.DWORD),
        ("DefaultAlert2", wintypes.DWORD),
    ]


class _WinBattery:
    """
    Public API class to access battery information on Windows systems.

    This class wraps the internal _BatteryHtmlReport and provides clean methods to access
    key battery health and status information.

    Features:
        - Pure python no C or C++
        - No need for external dependencies
        - Always returns clean values (never None).
        - return accurate inforamtion

    """

    def __init__(self, dev_mode: bool = False) -> None:

        """Initialize the Battery class

        Args:
            report_path: Optional custom path to store battery report
        """

        # Define constant
        self.dev_mode = dev_mode

        # Check for Battery presence
        if not _is_battery("Windows"):
            raise _BatteryNotDetected()

        # Initialize battery report
        self._battery_report = _BatteryHtmlReport()

        # Load necessary Windows DLLs
        self._kernel32 = ctypes.windll.kernel32
        self._power_prof = ctypes.windll.powrprof

    def _get_battery_state(self) -> _SYSTEM_BATTERY_STATE:
        """Get battery state directly from Windows API

        Returns:
            SYSTEM_BATTERY_STATE object with battery information

        Raises:
            OSError: If the Windows API call fails
        """
        state = _SYSTEM_BATTERY_STATE()
        result = self._power_prof.CallNtPowerInformation(
            5, None, 0, byref(state), ctypes.sizeof(state)
        )
        if result != 0:
            raise OSError(f"Failed to get battery information (Error code: {result})")
        return state

    @property
    def manufacturer(self) -> str:
        """ This method will return the battery manufacturer string"""
        return self._battery_report.battery_manufacturer()

    @property
    def chemistry(self) -> str:
        """ This method will returns the battery chemistry string"""
        return self._battery_report.battery_chemistry()

    @property
    def cycle_count(self) -> str:
        """ This method will returns the battery cycle count string"""
        return self._battery_report.battery_cycle_count()

    @property
    def design_capacity(self) -> int:
        """ This method will return the battery design capacity"""
        return self._battery_report.battery_design_capacity()

    def battery_percentage(self) -> Optional[int]:
        """Get current battery percentage

        Returns:
            Integer percentage (0-100) or None if unavailable
        """
        try:
            state = self._get_battery_state()
            if not state.BatteryPresent or state.MaxCapacity == 0:
                return None
            percent = int((state.RemainingCapacity / state.MaxCapacity) * 100)
            return min(percent, 100)
        except OSError:
            return None

    def is_plugged(self) -> Optional[bool]:
        """Check if the device is plugged into AC power

        Returns:
            True if plugged in, False if on battery, None on error

        """
        try:
            state = self._get_battery_state()
            return bool(state.AcOnLine)
        except OSError:
            return False

    def remaining_capacity(self) -> Optional[int]:
        """Get remaining battery capacity in mWh

        Returns:
            Integer capacity in mWh or None on error
        """
        try:
            state = self._get_battery_state()
            return state.RemainingCapacity if state.BatteryPresent else None

        except OSError:
            return 0

    def charge_rate(self) -> Optional[int]:
        """Get current charge/discharge rate in mW

        Returns:
            Integer rate in mW (positive when charging, negative when discharging)
            or None on error
        """
        try:
            state = self._get_battery_state()
            if not state.BatteryPresent:
                return None
            # The Rate field might need conversion based on charging/discharging status
            rate: int = state.Rate
            # Some systems report positive rate when discharging and negative when charging
            if state.Discharging and rate > 0:
                rate = 0
            elif state.Charging and rate < 0:
                rate = abs(rate)
            return rate

        except OSError:
            return 0

    def is_fast_charge(self) -> bool:
        """ This method will return if the battery is getting fast charging """
        return True if self.charge_rate() > _Const.FAST_CHARGE_RATE else False

    def battery_health(self) -> int:
        """Calculate battery health percentage compared to design capacity.

        Returns:
            Integer percentage (0-100), returns 0 if unavailable or invalid.
        """
        design_capacity = self._battery_report.battery_design_capacity()
        full_capacity = self._battery_report.battery_full_capacity()

        if design_capacity > 0 and full_capacity > 0:
            health = (full_capacity / design_capacity) * 100
            return min(int(health), 100)  # Ensure max 100%

        return 0

    @staticmethod
    def get_datetime() -> str:
        """Get current datetime formatted as string

        Returns:
            Formatted datetime string
        """
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    def get_result(self, cleanup_report: bool = True) -> Dict[str, Union[str, bool, None]]:
        """Collect all battery information into a single dictionary

        Args:
            cleanup_report: Whether to delete the report file after parsing

        Returns:
            Dictionary with all available battery information
        """

        # Build the result dictionary
        data = {
            'Battery Percentage': f"{self.battery_percentage()}%" if self.battery_percentage() is not None else "Unknown",
            'Power Status': 'Plugged In' if self.is_plugged() else 'On Battery' if self.is_plugged() is not None else "Unknown",
            'Remaining Capacity': f"{self.remaining_capacity()} mWh" if self.remaining_capacity() is not None else "Unknown",
            'Charge Rate': f"{self.charge_rate()} mW" if self.charge_rate() is not None else "Unknown",
            'Fast Charging': self.is_fast_charge(),
            'Manufacturer': self.manufacturer,
            'Chemistry': self.chemistry,
            'Cycle Count': self.cycle_count,
            'Battery Health': f"{self.battery_health()}%" if self.battery_health() is not None else 'Unknown',
            'Report Generated': self.get_datetime(),
        }

        # Check if report file still exists (if cleanup wasn't requested)
        if not cleanup_report and os.path.exists(self._report_path):
            data['Report Path'] = self._report_path

        return data


class _BatteryHtmlReport:
    """
    Internal helper class to generate, parse, and cache Windows battery reports using 'powercfg'.

    This class uses the Windows 'powercfg /batteryreport' command to generate a detailed battery
    health and status report in HTML format. The report is automatically cached to avoid redundant
    command executions and file reads. It provides methods to extract key information such as
    manufacturer, chemistry, design capacity, full charge capacity, and cycle count.

    Features:
        - Automatically generates a fresh report if no cache exists.
        - Parses the battery report HTML to extract specific data points.
        - Caches the report to a predefined path for efficient reuse.
        - Cleans up temporary files after report generation.
        - Provides clean data extraction methods with error handling and fallbacks.

    Methods:
        - battery_manufacturer(): Returns the battery manufacturer as a string.
        - battery_chemistry(): Returns the battery chemistry type as a string.
        - battery_design_capacity(): Returns the design capacity in mWh as integer.
        - battery_full_capacity(): Returns the full charge capacity in mWh as integer.
        - battery_cycle_count(): Returns the battery cycle count as integer.

    Notes:
        - This class is designed for internal use and should not be used directly by external modules.
        - It is OS-specific and works only on Windows systems where 'powercfg' is available.
        - Handles exceptions gracefully and returns 'Unknown' or 0 where data is missing.

    Example:
        report = _BatteryHtmlReport()
        manufacturer = report.battery_manufacturer()
        chemistry = report.battery_chemistry()
    """

    # Define relative cache directory inside user profile or script dir fallback
    _CACHE_FILENAME: str = f".cache_report"
    _CACHE_REPORT_PATH: str = os.path.join("batterypy", _CACHE_FILENAME)

    _REPORT_COMMAND: list = ["powercfg", "/batteryreport"]

    _SEARCH_PATTERNS: dict = {
        "manufacturer": r'MANUFACTURER<\/span>\s*<\/td>\s*<td[^>]*>(.*?)<\/td>',
        'chemistry': r'CHEMISTRY<\/span>\s*<\/td>\s*<td[^>]*>(.*?)<\/td>',
        'design_capacity': r'DESIGN CAPACITY<\/span>\s*<\/td>\s*<td[^>]*>(.*?)<\/td>',
        'full_capacity': r'FULL CHARGE CAPACITY<\/span>\s*<\/td>\s*<td[^>]*>(.*?)<\/td>',
        'cycle_count': r'CYCLE COUNT<\/span>\s*<\/td>\s*<td[^>]*>(.*?)<\/td>'
    }

    def __init__(self, force_refresh: bool = False):
        self._report_data: Optional[str] = None
        try:
            if not force_refresh and os.path.exists(self._CACHE_REPORT_PATH):
                self._report_data = self._load_cache()
            else:
                self._report_data = self._generate_battery_report()

                # print(self._report_data)
                if self._report_data:
                    self._save_cache(self._report_data)

        except Exception as e:
            print(f"[BatteryHtmlReport] Error initializing: {e}")
            self._report_data = None

    def _load_cache(self) -> str:
        """ This method will read and return html report cached file"""

        try:
            with open(self._CACHE_REPORT_PATH, "rb", encoding="utf-8") as f:
                data = f.read()
            if data:
                return data
        except Exception as e:
            print(f"[BatteryHtmlReport] Error loading cache: {e}")
        return ""

    def _generate_battery_report(self) -> Optional[str]:
        """Generates the battery report using 'powercfg',
        returns its HTML content as a string, and cleans up the report file.
        """
        try:
            # Run powercfg /batteryreport
            result = subprocess.run(
                self._REPORT_COMMAND,
                capture_output=True,
                text=True,
                check=True
            )

            output_text = result.stdout

            # Extract the report file path
            match = re.search(r'saved to\s+file path\s+(.+)', output_text, re.IGNORECASE)
            if not match:
                print("[BatteryHtmlReport] ❗ Report path not found in output.")
                return None

            report_path = match.group(1).strip().strip('"')

            if not os.path.isfile(report_path):
                print(f"[BatteryHtmlReport] ❗ Report file not found at: {report_path}")
                return None

            try:
                with open(report_path, "r", encoding="utf-8") as f:
                    html_data = f.read()
            except (OSError, IOError) as file_err:
                print(f"[BatteryHtmlReport] ❗ Error reading report: {file_err}")
                return None
            finally:
                try:
                    os.remove(report_path)
                except Exception as cleanup_err:
                    print(f"[BatteryHtmlReport] ⚠️ Failed to delete report file: {cleanup_err}")

            return html_data

        except subprocess.CalledProcessError as e:
            print(f"[BatteryHtmlReport] ❗ Failed to generate report: {e}")
        except Exception as e:
            print(f"[BatteryHtmlReport] ❗ Unexpected error: {e}")

        return None

    def _parse_html(self, query: str, as_int: bool = False) -> str | int:
        """ This method will parse the html """

        if not self._report_data:
            return "Unknown" if not as_int else -1

        pattern = self._SEARCH_PATTERNS.get(query)
        if not pattern:
            return "Unknown" if not as_int else -1

        match = re.search(pattern, self._report_data, re.IGNORECASE | re.DOTALL)
        if match:
            raw_text = match.group(1)
            cleaned_text = self._normalized_text(raw_text)

            if as_int:
                # Remove commas, spaces, non-digits, and mWh
                digits = re.sub(r'[^\d]', '', cleaned_text)
                return int(digits) if digits.isdigit() else -1
            else:
                return cleaned_text

        return "Unknown" if not as_int else -1

    @staticmethod
    def _normalized_text(html_text: str) -> str:
        """ This method will clean the text and remove html tags"""

        text = re.sub(r'<[^>]*>', '', html_text)
        text = text.replace('&nbsp;', ' ')
        return text.strip()

    # Public APIs
    def battery_manufacturer(self) -> str:
        """ This method get the battery manufacturer string"""
        return self._parse_html("manufacturer")

    def battery_chemistry(self) -> str:
        """ This method get the battery chmistry string"""
        return self._parse_html("chemistry")

    def battery_design_capacity(self) -> str | int:
        """ This method get the battery design capacity"""
        return self._parse_html("design_capacity", as_int=True)

    def battery_full_capacity(self) -> str | int:
        """ This method get the battery full capacity"""
        return self._parse_html("full_capacity", as_int=True)

    def battery_cycle_count(self) -> str | int:
        """ This method get the battery cycle count string"""
        return 0 if self._parse_html("cycle_count") == "-" else self._parse_html("cycle_count")


class _LinuxBattery:


    def __init__(self, dev_mode: bool = False) -> None:

        # Define constant
        self.dev_mode = dev_mode

    def manufacurer(self) -> str:
        """ Tjis """

# Define current system
__CURRENT_PLATFORM: str = system()

# Initialize BatteryPy
if __CURRENT_PLATFORM == "Windows":
    Battery = _WinBattery

elif __CURRENT_PLATFORM == "Linux":
    Battery = _LinuxBattery

else:
    sys.exit("Unsupported platform")


if __name__ == "__main__":
    sys.exit(0)
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
import html
import time
import ctypes
import winreg
import subprocess
from platform import system
from pathlib import Path
from functools import lru_cache
from typing import Dict, Optional, Union, Any
from ctypes import byref, Structure, c_ulong, c_ubyte, c_bool
from datetime import datetime
from abc import ABC, abstractmethod



# Declare software constants
author: str = "Aymen Brahim Djelloul"
version: str = "1.3"
caption: str = f"BatteryPy - v{version}"
website: str = "https://aymenbrahimdjelloul.github.io/BatteryPy"

# Declare supported platforms
_SUPPORTED_PLATFORMS: tuple = ("Windows", "Linux")

# Define current system
platform: str = system()

# Set the fast charge rate at 30 Watts
_fast_charge_rate: int = 30000


class BatteryPyException(BaseException):
    """ This class contain the BatteryPy exception"""

    def __init__(self, exception: str) -> None:
        self.e = exception

    def __str__(self) -> str:
        """ This method will return the BatteryPy exception error"""
        return f"ERROR : {self.e}"


def _mw_to_w(value: int) -> int:
    """
    Convert power from milli-watts to watts, rounded to the nearest integer.

    Parameters:
        value (float): Power in milli-watts.

    Returns:
        int: Power in watts, rounded.
    """
    return round(value / 1000)


# def _mwh_to_mah(self, mwh: float) -> float:
#     """
#     Parameters:
#         mwh (float): Energy in milli-watt-hours.
#
#     Returns:
#         float: Energy in milli-ampere-hours, or 0.0 if voltage is invalid.
#     """
#     return int(mwh / int(self.get_current_voltage(False)))



def _get_datetime() -> str:
    """Get current datetime formatted as string

    Returns:
        Formatted datetime string
    """
    return datetime.now().strftime('%Y-%m-%d')


def _is_battery(system_name: str) -> bool:
    """
    Detects if the system is running on battery power.
    Returns:
        bool: True if on battery, False if plugged in.
              Exits on undetectable.
    """

    try:
        if platform == system_name:

            # Using _SYSTEM_POWER_STATUS struct from Windows API
            class _SYSTEM_POWER_STATUS(ctypes.Structure):
                _fields_: list = [
                    ('ACLineStatus', ctypes.c_byte),
                    ('BatteryFlag', ctypes.c_byte),
                    ('BatteryLifePercent', ctypes.c_byte),
                    ('Reserved1', ctypes.c_byte),
                    ('BatteryLifeTime', ctypes.c_ulong),
                    ('BatteryFullLifeTime', ctypes.c_ulong)
                ]

            status = _SYSTEM_POWER_STATUS()
            if not ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(status)):
                raise BatteryPyException("[ERROR] Unable to get power status from Windows API")

            if status.ACLineStatus == 0:
                return True  # On battery
            elif status.ACLineStatus == 1:
                return False

            else:
                raise BatteryPyException("[ERROR] Battery status undetectable (Windows)")

        elif platform == system_name:
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

            raise BatteryPyException("[ERROR] AC adapter status undetectable (Linux)")

        elif platform == system_name:  # macOS
            output = subprocess.check_output(["pmset", "-g", "batt"], universal_newlines=True)
            output = output.lower()
            if "discharging" in output:
                return True
            elif "charging" in output or "charged" in output:
                return False

            raise BatteryPyException("[ERROR] Battery status undetectable (macOS)")

        else:
            raise BatteryPyException(f"[ERROR] Unsupported OS: {platform}")

    except Exception as e:
        raise BatteryPyException(e)


class _SYSTEM_BATTERY_STATE(Structure):
    """Windows SYSTEM_BATTERY_STATE structure for battery information."""
    _fields_ = [
        ("AcOnLine", c_bool),
        ("BatteryPresent", c_bool),
        ("Charging", c_bool),
        ("Discharging", c_bool),
        ("Spare1", c_ubyte * 3),
        ("Tag", c_ubyte),
        ("MaxCapacity", c_ulong),
        ("RemainingCapacity", c_ulong),
        ("Rate", c_ulong),
        ("EstimatedTime", c_ulong),
        ("DefaultAlert1", c_ulong),
        ("DefaultAlert2", c_ulong),
    ]


class _BatteryPy(ABC):
    """
    Abstract base class for battery information retrieval across different platforms.

    This class defines the interface that all platform-specific battery classes must implement.
    It provides a standardized way to access battery information regardless of the underlying
    operating system or implementation details.
    """

    def __init__(self):
        """Initialize the base battery class."""
        self._report_path: Optional[str] = None

    # Abstract methods that must be implemented by subclasses
    @abstractmethod
    def battery_percent(self) -> int:
        """Get current battery charge percentage (0-100)."""
        pass

    @abstractmethod
    def is_plugged(self) -> bool:
        """Check if device is connected to AC power."""
        pass

    @abstractmethod
    def remaining_capacity(self) -> int:
        """Get remaining battery capacity in mWh."""
        pass

    @abstractmethod
    def charge_rate(self) -> int:
        """Get current charge/discharge rate in mW."""
        pass

    @abstractmethod
    def is_fast_charge(self) -> bool:
        """Check if battery is fast charging."""
        pass

    @property
    @abstractmethod
    def manufacturer(self) -> str:
        """Get battery manufacturer name."""
        pass

    @property
    @abstractmethod
    def battery_technology(self) -> str:
        """Get battery chemistry/technology type."""
        pass

    @property
    @abstractmethod
    def cycle_count(self) -> int:
        """Get battery cycle count."""
        pass

    @abstractmethod
    def battery_health(self) -> float:
        """Get battery health percentage."""
        pass

    @abstractmethod
    def battery_voltage(self) -> Optional[float]:
        """Get battery voltage in volts."""
        pass

    @abstractmethod
    def battery_temperature(self) -> Optional[float]:
        """Get battery temperature in Celsius."""
        pass

    def get_result(self, include_raw_data: bool = False) -> Dict[str, Any]:
        """Collect all battery information into a comprehensive dictionary.

        Args:
            include_raw_data: Whether to include raw numerical values alongside formatted strings

        Returns:
            Dictionary with all available battery information
        """
        # Get raw values
        percentage = self.battery_percent()
        is_plugged = self.is_plugged()
        remaining_cap = self.remaining_capacity()
        charge_rate_val = self.charge_rate()
        health = self.battery_health()
        voltage = self.battery_voltage()
        temperature = self.battery_temperature()

        # Build the formatted result dictionary
        data: dict = {
            'battery_percentage': self._format_percentage(percentage),
            'power_status': self._format_power_status(is_plugged),
            'remaining_capacity': self._format_capacity(remaining_cap),
            'charge_rate': self._format_charge_rate(charge_rate_val),
            'is_fast_charging': self.is_fast_charge(),
            'manufacturer': self.manufacturer or "Unknown",
            'technology': self.battery_technology or "Unknown",
            'cycle_count': self.cycle_count or 0,
            'battery_health': self._format_health(health),
            'battery_voltage': self._format_voltage(voltage),
            'battery_temperature': self._format_temperature(temperature),
            'report_generated': _get_datetime(),
        }

        # Include raw numerical data if requested
        if include_raw_data:
            data['raw_data']: dict = {
                'percentage_value': percentage,
                'is_plugged_value': is_plugged,
                'remaining_capacity_mwh': remaining_cap,
                'charge_rate_mw': charge_rate_val,
                'health_percentage': health,
                'voltage_v': voltage,
                'temperature_c': temperature,
                'cycle_count_value': self.cycle_count
            }

        return data

    # def get_summary(self) -> Dict[str, str]:
    #     """Get a concise summary of key battery information.
    #
    #     Returns:
    #         Dictionary with essential battery metrics
    #     """
    #     return {
    #         'charge': f"{self.battery_percent()}%",
    #         'health': f"{self.battery_health():.1f}%",
    #         'status': 'Plugged In' if self.is_plugged() else 'On Battery',
    #         'manufacturer': self.manufacturer or "Unknown",
    #         'technology': self.battery_technology or "Unknown"
    #     }

    # def get_health_report(self) -> Dict[str, Any]:
    #     """Get detailed battery health information.
    #
    #     Returns:
    #         Dictionary with health-related metrics
    #     """
    #     health_percent = self.battery_health()
    #     cycle_count = self.cycle_count
    #
    #     # Determine health status
    #     if health_percent >= 80:
    #         health_status = "Excellent"
    #     elif health_percent >= 60:
    #         health_status = "Good"
    #     elif health_percent >= 40:
    #         health_status = "Fair"
    #     else:
    #         health_status = "Poor"
    #
    #     return {
    #         'health_percentage': health_percent,
    #         'health_status': health_status,
    #         'cycle_count': cycle_count,
    #         'manufacturer': self.manufacturer or "Unknown",
    #         'chemistry': self.battery_technology or "Unknown",
    #         'estimated_degradation': round(100 - health_percent, 1)
    #     }

    # def get_power_info(self) -> Dict[str, Any]:
    #     """Get current power and charging information.
    #
    #     Returns:
    #         Dictionary with power-related metrics
    #     """
    #     charge_rate_val = self.charge_rate()
    #     is_charging = charge_rate_val > 0 if charge_rate_val != 0 else False
    #
    #     return {
    #         'battery_percentage': self.battery_percent(),
    #         'is_plugged': self.is_plugged(),
    #         'is_charging': is_charging,
    #         'is_discharging': charge_rate_val < 0,
    #         'charge_rate_mw': abs(charge_rate_val),
    #         'charge_direction': 'Charging' if is_charging else 'Discharging' if charge_rate_val < 0 else 'Idle',
    #         'is_fast_charging': self.is_fast_charge(),
    #         'remaining_capacity_mwh': self.remaining_capacity()
    #     }

    @staticmethod
    def _format_percentage(percentage: int) -> str:
        """Format battery percentage with appropriate handling."""
        return f"{percentage}%" if percentage is not None else "Unknown"

    @staticmethod
    def _format_power_status(is_plugged: bool) -> str:
        """Format power connection status."""
        if is_plugged is None:
            return "Unknown"
        return 'Plugged In' if is_plugged else 'On Battery'

    @staticmethod
    def _format_capacity(capacity: int) -> str:
        """Format battery capacity with units."""
        return f"{capacity:,} mWh" if capacity is not None and capacity > 0 else "Unknown"

    @staticmethod
    def _format_charge_rate(rate: int) -> str:
        """Format charge rate with direction indicator."""
        if rate is None or rate == 0:
            return "Unknown"

        direction = "Charging" if rate > 0 else "Discharging"
        return f"{abs(rate):,} mW ({direction})"

    @staticmethod
    def _format_health(health: float) -> str:
        """Format battery health percentage."""
        return f"{health:.1f}%" if health is not None and health >= 0 else "Unknown"

    @staticmethod
    def _format_voltage(voltage: Optional[float]) -> str:
        """Format battery voltage with units."""
        return f"{voltage:.2f} V" if voltage is not None else "Unknown"

    @staticmethod
    def _format_temperature(temperature: Optional[float]) -> str:
        """Format battery temperature with units."""
        if temperature is not None:
            return f"{temperature:.1f}°C"
        return "Unknown"

    def is_battery_critical(self, threshold: int = 10) -> bool:
        """Check if battery level is critically low.

        Args:
            threshold: Percentage threshold for critical battery level

        Returns:
            True if battery is below threshold and not plugged in
        """
        percentage = self.battery_percent()
        return (percentage is not None and
                percentage <= threshold and
                not self.is_plugged())

    def get_battery_status_icon(self) -> str:
        """Get a Unicode icon representing current battery status.

        Returns:
            Unicode character representing battery state
        """
        percentage = self.battery_percent()
        is_plugged = self.is_plugged()

        if is_plugged:
            return "🔌"  # Plugged in
        elif percentage is None:
            return "❓"  # Unknown
        elif percentage <= 10:
            return "🪫"  # Critical
        elif percentage <= 25:
            return "🔋"  # Low
        elif percentage <= 50:
            return "🔋"  # Medium
        elif percentage <= 75:
            return "🔋"  # Good
        else:
            return "🔋"  # Full

    def __str__(self) -> str:
        """Human-readable string representation."""
        percentage = self.battery_percent()
        health = self.battery_health()
        status = "Plugged In" if self.is_plugged() else "On Battery"

        return (f"Battery: {percentage}% ({status}) | "
                f"Health: {health:.1f}% | "
                f"Manufacturer: {self.manufacturer}")

    def __repr__(self) -> str:
        """Developer-friendly string representation."""
        return (f"{self.__class__.__name__}("
                f"percentage={self.battery_percent()}, "
                f"health={self.battery_health():.1f}, "
                f"plugged={self.is_plugged()})")

    # Backward compatibility methods
    def get_formatted_result(self) -> Dict[str, str]:
        """Get formatted result for backward compatibility.

        Returns:
            Dictionary with formatted string values (deprecated, use get_result)
        """
        return {k: v for k, v in self.get_result().items()
                if not isinstance(v, dict)}  # Exclude raw_data if present

# Initialize BatteryPy
if platform == "Windows":

    class Battery(_BatteryPy):
        """
        Public API class to access battery information on Windows systems.

        This class wraps the internal _BatteryHtmlReport and provides clean methods to access
        key battery health and status information using Windows APIs for real-time data
        and powercfg reports for static battery specifications.

        Features:
            - Pure Python implementation with no external dependencies
            - Combines Windows API calls with HTML report parsing
            - Always returns clean values with proper error handling
            - Cached operations for performance optimization
            - Comprehensive battery information including health metrics

        Methods:
            - manufacturer: Battery manufacturer name
            - battery_technology: Battery chemistry type
            - cycle_count: Battery charge cycle count
            - design_capacity: Original battery design capacity
            - battery_percentage(): Current charge percentage
            - is_plugged(): AC power connection status
            - remaining_capacity(): Current battery capacity
            - charge_rate(): Current charge/discharge rate
            - battery_health(): Battery health percentage
            - is_fast_charge(): Fast charging detection
            - get_battery_info(): Complete battery information dictionary
        """

        # Class constants
        _FAST_CHARGE_THRESHOLD_MW = 15000  # 15W threshold for fast charging
        _CACHE_DURATION_SECONDS = 2  # Cache API calls for 2 seconds
        _POWER_INFO_BATTERY_STATE = 5  # Windows API constant

        # Define commands constants
        powershell_cmd_battery: list = [
            'powershell.exe', '-NoProfile', '-Command',
            "(Get-WmiObject Win32_Battery).DesignVoltage"
        ]

        def __init__(self, dev_mode: bool = False) -> None:
            """Initialize the Battery class with Windows API access.

            Args:
                dev_mode: Enable development mode for additional logging
            """
            super().__init__()

            self.dev_mode = dev_mode
            self._last_api_call = 0
            self._cached_state = None

            # Initialize battery report (static information)
            self._battery_report = _BatteryHtmlReport()

            # Load Windows DLLs with error handling
            try:
                self._kernel32 = ctypes.windll.kernel32
                self._power_prof = ctypes.windll.powrprof
            except AttributeError as e:
                if self.dev_mode:
                    print(f"[WinBattery] Warning: Failed to load Windows DLLs: {e}")
                self._kernel32 = None
                self._power_prof = None

        def _get_battery_state(self, use_cache: bool = True) -> Optional[_SYSTEM_BATTERY_STATE]:
            """Get battery state from Windows API with caching.

            Args:
                use_cache: Whether to use cached results for performance

            Returns:
                SYSTEM_BATTERY_STATE object or None if API call fails
            """
            if not self._power_prof:
                return None

            current_time = time.time()

            # Return cached state if recent and caching enabled
            if (use_cache and self._cached_state and
                    current_time - self._last_api_call < self._CACHE_DURATION_SECONDS):
                return self._cached_state

            try:
                state = _SYSTEM_BATTERY_STATE()
                result = self._power_prof.CallNtPowerInformation(
                    self._POWER_INFO_BATTERY_STATE,
                    None, 0,
                    byref(state),
                    ctypes.sizeof(state)
                )

                if result == 0:  # Success
                    self._cached_state = state
                    self._last_api_call = current_time
                    return state
                else:
                    if self.dev_mode:
                        print(f"[WinBattery] API call failed with error code: {result}")
                    return None

            except Exception as e:
                if self.dev_mode:
                    print(f"[WinBattery] Exception in _get_battery_state: {e}")
                return None

        @property
        def manufacturer(self) -> str:
            """Get battery manufacturer name."""
            return self._battery_report.battery_manufacturer()

        @property
        def battery_technology(self) -> str:
            """Get battery chemistry/technology type."""
            tech: str = self._battery_report.battery_chemistry()
            return "Lithium-ion" if tech == "LIon" else tech

        @property
        def cycle_count(self) -> int:
            """Get battery cycle count."""
            return self._battery_report.battery_cycle_count()

        @property
        def design_capacity(self) -> int:
            """Get battery design capacity in mWh."""
            return self._battery_report.battery_design_capacity()

        @property
        def full_capacity(self) -> int:
            """Get battery full charge capacity in mWh."""
            return self._battery_report.battery_full_capacity()

        def battery_percent(self) -> int:
            """Get current battery charge percentage.

            Returns:
                Integer percentage (0-100), returns 0 if unavailable
            """
            state = self._get_battery_state()
            if not state or not state.BatteryPresent or state.MaxCapacity == 0:
                return 0

            try:
                percentage = int((state.RemainingCapacity / state.MaxCapacity) * 100)
                return min(max(percentage, 0), 100)  # Clamp between 0-100
            except (ZeroDivisionError, ValueError):
                return 0

        def is_plugged(self) -> bool:
            """Check if device is connected to AC power.

            Returns:
                True if plugged in, False if on battery power
            """
            state = self._get_battery_state()
            return bool(state.AcOnLine) if state else False

        def remaining_capacity(self) -> int:
            """Get remaining battery capacity in mWh.

            Returns:
                Integer capacity in mWh, returns 0 if unavailable
            """
            state = self._get_battery_state()
            if not state or not state.BatteryPresent:
                return 0
            return state.RemainingCapacity

        def charge_rate(self) -> int:
            """Get current charge/discharge rate in mW.

            Returns:
                Integer rate in mW (positive when charging, negative when discharging)
                Returns 0 if unavailable
            """
            state = self._get_battery_state()
            if not state or not state.BatteryPresent:
                return 0

            try:
                rate = int(state.Rate)

                # Normalize rate based on charging/discharging status
                if state.Discharging and rate > 0:
                    return -rate  # Negative for discharging
                elif state.Charging and rate < 0:
                    return abs(rate)  # Positive for charging
                elif state.Charging:
                    return rate  # Already positive
                else:
                    return -abs(rate) if rate != 0 else 0  # Negative for discharging

            except (ValueError, OverflowError):
                return 0

        def is_charging(self) -> bool:
            """Check if battery is currently charging.

            Returns:
                True if charging, False otherwise
            """
            state = self._get_battery_state()
            return bool(state.Charging) if state and state.BatteryPresent else False

        def is_discharging(self) -> bool:
            """Check if battery is currently discharging.

            Returns:
                True if discharging, False otherwise
            """
            state = self._get_battery_state()
            return bool(state.Discharging) if state and state.BatteryPresent else False

        def is_fast_charge(self) -> bool:
            """Check if battery is fast charging.

            Returns:
                True if charging rate exceeds fast charge threshold
            """
            if not self.is_charging():
                return False
            return abs(self.charge_rate()) > self._FAST_CHARGE_THRESHOLD_MW

        def battery_health(self) -> float:
            """Calculate battery health percentage.

            Returns:
                Float percentage (0.0-100.0) comparing full capacity to design capacity
            """
            return self._battery_report.get_battery_health_percentage()

        def estimated_time_remaining(self) -> int:
            """Get estimated time remaining in minutes.

            Returns:
                Integer minutes remaining, returns 0 if unavailable or charging
            """
            state = self._get_battery_state()
            if not state or not state.BatteryPresent or state.Charging:
                return 0

            # EstimatedTime is in seconds, convert to minutes
            try:
                return int(state.EstimatedTime / 60) if state.EstimatedTime > 0 else 0
            except (ValueError, OverflowError):
                return 0

        def get_battery_info(self) -> Dict[str, Any]:
            """Get comprehensive battery information.

            Returns:
                Dictionary containing all available battery information
            """
            return {
                'manufacturer': self.manufacturer,
                'technology': self.battery_technology,
                'design_capacity_mwh': self.design_capacity,
                'full_capacity_mwh': self.full_capacity,
                'remaining_capacity_mwh': self.remaining_capacity(),
                'cycle_count': self.cycle_count,
                'battery_percentage': self.battery_percent(),
                'battery_health_percent': self.battery_health(),
                'is_plugged': self.is_plugged(),
                'is_charging': self.is_charging(),
                'is_discharging': self.is_discharging(),
                'charge_rate_mw': self.charge_rate(),
                'is_fast_charging': self.is_fast_charge(),
                'estimated_time_remaining_minutes': self.estimated_time_remaining(),
                'report_available': self._battery_report.is_report_available()
            }

        @lru_cache(maxsize=1)
        def get_static_battery_info(self) -> Dict[str, Any]:
            """Get static battery information (cached).

            Returns:
                Dictionary containing static battery specifications
            """
            return {
                'manufacturer': self.manufacturer,
                'technology': self.battery_technology,
                'design_capacity_mwh': self.design_capacity,
                'full_capacity_mwh': self.full_capacity,
                'cycle_count': self.cycle_count,
                'battery_health_percent': self.battery_health()
            }

        def battery_voltage(self, use_simulation: bool = True) -> Optional[float]:
            """Get battery voltage using only Windows built-in APIs and standard library.

            Attempts multiple methods without external dependencies:
            1. PowerShell WMI query (fastest)
            2. Windows Registry battery information
            3. WMI COM interface via ctypes
            4. Estimate based on system info

            Returns:
                float: Battery voltage in volts, or None if unavailable
            """

            # Method 1: PowerShell WMI (fastest, no external deps)
            try:

                result: Optional = subprocess.run(self.powershell_cmd_battery, capture_output=True, text=True, timeout=3,
                                        creationflags=subprocess.CREATE_NO_WINDOW)

                if result.returncode == 0 and result.stdout.strip():
                    voltage_mv = int(result.stdout.strip())
                    voltage = voltage_mv / 1000.0
                    if self.dev_mode:
                        print(f"[WinBattery] PowerShell voltage: {voltage:.2f}V")
                    return voltage
            except Exception as e:
                if self.dev_mode:
                    print(f"[WinBattery] PowerShell method failed: {e}")

            # Method 2: Windows Registry approach
            try:
                voltage = self._get_voltage_from_registry()
                if voltage:
                    return voltage
            except Exception as e:
                if self.dev_mode:
                    print(f"[WinBattery] Registry method failed: {e}")

            # Method 3: Direct COM/WMI via ctypes
            try:
                voltage = self._get_voltage_via_com()
                if voltage:
                    return voltage
            except Exception as e:
                if self.dev_mode:
                    print(f"[WinBattery] COM method failed: {e}")

            # Method 4: PowerShell alternative query
            try:
                powershell_cmd_battery = [
                    'powershell.exe', '-NoProfile', '-Command',
                    "Get-WmiObject Win32_PortableBattery | Select-Object -ExpandProperty DesignVoltage"
                ]
                result = subprocess.run(powershell_cmd_battery, capture_output=True, text=True, timeout=3,
                                        creationflags=subprocess.CREATE_NO_WINDOW)

                if result.returncode == 0 and result.stdout.strip():
                    voltage_mv = int(result.stdout.strip())
                    voltage = voltage_mv / 1000.0
                    if self.dev_mode:
                        print(f"[WinBattery] PortableBattery voltage: {voltage:.2f}V")
                    return voltage
            except Exception as e:
                if self.dev_mode:
                    print(f"[WinBattery] PortableBattery method failed: {e}")

            # Method 5: Estimate based on battery chemistry
            try:
                voltage = self._estimate_voltage_from_chemistry()
                if voltage:
                    return voltage
            except Exception as e:
                if self.dev_mode:
                    print(f"[WinBattery] Chemistry estimation failed: {e}")

            if self.dev_mode:
                print("[WinBattery] All voltage detection methods failed")
            return None

        def _get_voltage_from_registry(self) -> Optional[float]:
            """Extract battery voltage from Windows Registry."""
            try:
                # Common registry paths for battery info
                paths = [
                    r"SYSTEM\CurrentControlSet\Enum\ACPI",
                    r"SYSTEM\CurrentControlSet\Services\CmBatt\Parameters"
                ]

                for base_path in paths:
                    try:
                        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, base_path) as key:
                            # Enumerate subkeys looking for battery entries
                            i = 0
                            while True:
                                try:
                                    subkey_name = winreg.EnumKey(key, i)
                                    if "BAT" in subkey_name.upper() or "ACPI" in subkey_name.upper():
                                        voltage = self._read_battery_subkey(base_path, subkey_name)
                                        if voltage:
                                            if self.dev_mode:
                                                print(f"[WinBattery] Registry voltage: {voltage:.2f}V")
                                            return voltage
                                    i += 1
                                except OSError:
                                    break
                    except FileNotFoundError:
                        continue

            except Exception as e:
                if self.dev_mode:
                    print(f"[WinBattery] Registry error: {e}")

            return None

        def _read_battery_subkey(self, base_path: str, subkey_name: str) -> Optional[float]:
            """Read battery information from a specific registry subkey."""
            try:
                full_path = f"{base_path}\\{subkey_name}"
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, full_path) as subkey:
                    # Look for voltage-related values
                    voltage_keys = ["DesignVoltage", "Voltage", "NominalVoltage"]

                    i = 0
                    while True:
                        try:
                            value_name, value_data, value_type = winreg.EnumValue(subkey, i)

                            if any(v_key.lower() in value_name.lower() for v_key in voltage_keys):
                                if isinstance(value_data, int) and value_data > 1000:
                                    return value_data / 1000.0  # Convert mV to V
                                elif isinstance(value_data, int) and 1 <= value_data <= 50:
                                    return float(value_data)  # Already in volts

                            i += 1
                        except OSError:
                            break

            except Exception as e:

                # Print exception in dev mode
                if self.dev_mode:
                    print(f"[read battery subkey] ERROR : {e}")

            return None

        def _get_voltage_via_com(self) -> Optional[float]:
            """Get voltage using COM interface to WMI (ctypes only)."""
            try:
                # Initialize COM
                ole32 = ctypes.windll.ole32
                ole32.CoInitialize(None)

                try:
                    # This is a simplified approach - full COM implementation is complex
                    # Fall back to command line WMI
                    cmd = ['wmic', 'path', 'Win32_Battery', 'get', 'DesignVoltage', '/value']
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=5,
                                            creationflags=subprocess.CREATE_NO_WINDOW)

                    if result.returncode == 0:
                        match = re.search(r'DesignVoltage=(\d+)', result.stdout)
                        if match:
                            voltage_mv = int(match.group(1))
                            voltage = voltage_mv / 1000.0
                            if self.dev_mode:
                                print(f"[WinBattery] WMIC voltage: {voltage:.2f}V")
                            return voltage

                finally:
                    ole32.CoUninitialize()

            except Exception as e:
                if self.dev_mode:
                    print(f"[WinBattery] COM/WMIC error: {e}")

            return None

        def _estimate_voltage_from_chemistry(self) -> Optional[float]:
            """Estimate voltage based on battery chemistry from PowerShell."""
            try:
                cmd = [
                    'powershell.exe', '-NoProfile', '-Command',
                    "(Get-WmiObject Win32_Battery).Chemistry"
                ]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=3,
                                        creationflags=subprocess.CREATE_NO_WINDOW)

                if result.returncode == 0 and result.stdout.strip():
                    chemistry = int(result.stdout.strip())

                    # Battery chemistry voltage mapping
                    voltage_map = {
                        1: 3.7,  # Other
                        2: 3.7,  # Unknown
                        3: 12.0,  # Lead Acid
                        4: 3.6,  # Nickel Cadmium
                        5: 3.6,  # Nickel Metal Hydride
                        6: 3.7,  # lithium-ion (most common in laptops)
                        7: 1.4,  # Zinc Air
                        8: 3.7  # Lithium Polymer
                    }

                    voltage = voltage_map.get(chemistry, 11.1)  # Default to common laptop voltage

                    # Multiply by typical cell count for laptops
                    if chemistry in [6, 8]:  # Li-ion/Li-Po
                        voltage = voltage * 3  # Most laptops use 3-cell config (11.1V)

                    if self.dev_mode:
                        print(f"[WinBattery] Estimated voltage (chemistry {chemistry}): {voltage:.1f}V")
                    return voltage

            except Exception as e:
                if self.dev_mode:
                    print(f"[WinBattery] Chemistry estimation error: {e}")

            return None

        def battery_temperature(self) -> Optional[float]:
            """Get battery temperature using only Windows built-in APIs and standard library.

            Attempts multiple methods without external dependencies:
            1. PowerShell WMI thermal queries
            2. Windows Registry thermal information
            3. WMI temperature sensors
            4. ACPI thermal zone queries
            5. Hardware monitoring via Windows APIs

            Returns:
                float: Battery temperature in Celsius, or None if unavailable
            """

            # Method 1: PowerShell WMI Battery Temperature (direct)
            try:
                cmd = [
                    'powershell.exe', '-NoProfile', '-Command',
                    "(Get-WmiObject Win32_Battery | Where-Object {$_.Temperature -ne $null}).Temperature"
                ]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=3,
                                        creationflags=subprocess.CREATE_NO_WINDOW)

                if result.returncode == 0 and result.stdout.strip():
                    # Temperature in WMI is typically in tenths of Kelvin
                    temp_raw = float(result.stdout.strip())
                    if temp_raw > 1000:  # Likely in tenths of Kelvin
                        temp_celsius = (temp_raw / 10.0) - 273.15
                    else:  # Already in Celsius or other format
                        temp_celsius = temp_raw

                    if -40 <= temp_celsius <= 100:  # Reasonable battery temperature range
                        if self.dev_mode:
                            print(f"[WinBattery] Battery temperature: {temp_celsius:.1f}°C")
                        return temp_celsius
            except Exception as e:
                if self.dev_mode:
                    print(f"[WinBattery] PowerShell battery temp failed: {e}")

            # Method 2: Thermal Zone queries (system temperature)
            try:
                temp = self._get_thermal_zone_temperature()
                if temp:
                    return temp
            except Exception as e:
                if self.dev_mode:
                    print(f"[WinBattery] Thermal zone method failed: {e}")

            # Method 3: WMI Temperature Sensors
            try:
                temp = self._get_wmi_temperature_sensors()
                if temp:
                    return temp
            except Exception as e:
                if self.dev_mode:
                    print(f"[WinBattery] WMI sensors method failed: {e}")

            # Method 4: Registry-based temperature detection
            try:
                temp = self._get_temperature_from_registry()
                if temp:
                    return temp
            except Exception as e:
                if self.dev_mode:
                    print(f"[WinBattery] Registry method failed: {e}")

            # Method 5: ACPI thermal information
            try:
                temp = self._get_acpi_temperature()
                if temp:
                    return temp
            except Exception as e:
                if self.dev_mode:
                    print(f"[WinBattery] ACPI method failed: {e}")

            # Method 6: Hardware monitoring via Windows Performance Counters
            try:
                temp = self._get_performance_counter_temperature()
                if temp:
                    return temp
            except Exception as e:
                if self.dev_mode:
                    print(f"[WinBattery] Performance counter method failed: {e}")

            if self.dev_mode:
                print("[WinBattery] All temperature detection methods failed")
            return None

        def _get_thermal_zone_temperature(self) -> Optional[float]:
            """Get temperature from Windows thermal zones."""
            try:
                # Query thermal zones
                cmd = [
                    'powershell.exe', '-NoProfile', '-Command',
                    "Get-WmiObject -Namespace 'root/WMI' -Class MSAcpi_ThermalZoneTemperature | Select-Object -ExpandProperty CurrentTemperature"
                ]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=5,
                                        creationflags=subprocess.CREATE_NO_WINDOW)

                if result.returncode == 0 and result.stdout.strip():
                    lines = result.stdout.strip().split('\n')
                    for line in lines:
                        if line.strip():
                            try:
                                # Temperature is in tenths of Kelvin
                                temp_raw = float(line.strip())
                                temp_celsius = (temp_raw / 10.0) - 273.15

                                # Look for reasonable battery temperature (usually 20-50°C)
                                if 15 <= temp_celsius <= 80:
                                    if self.dev_mode:
                                        print(f"[WinBattery] Thermal zone temp: {temp_celsius:.1f}°C")
                                    return temp_celsius
                            except ValueError:
                                continue

            except Exception as e:
                if self.dev_mode:
                    print(f"[WinBattery] Thermal zone error: {e}")

            return None

        def _get_wmi_temperature_sensors(self) -> Optional[float]:
            """Get temperature from various WMI temperature sensors."""
            try:
                # Try different WMI temperature classes
                queries = [
                    "Get-WmiObject -Namespace 'root/OpenHardwareMonitor' -Class Sensor | Where-Object {$_.SensorType -eq 'Temperature' -and $_.Name -like '*battery*'}",
                    "Get-WmiObject -Namespace 'root/LibreHardwareMonitor' -Class Sensor | Where-Object {$_.SensorType -eq 'Temperature' -and $_.Name -like '*battery*'}",
                    "Get-WmiObject -Class Win32_TemperatureProbe",
                    "Get-WmiObject -Namespace 'root/WMI' -Class MSAcpi_BatteryTemperature"
                ]

                for query in queries:
                    try:
                        cmd = ['powershell.exe', '-NoProfile', '-Command', query]
                        result = subprocess.run(cmd, capture_output=True, text=True, timeout=4,
                                                creationflags=subprocess.CREATE_NO_WINDOW)

                        if result.returncode == 0 and result.stdout.strip():
                            # Parse temperature values from output
                            temps = re.findall(r'(\d+\.?\d*)', result.stdout)
                            for temp_str in temps:
                                try:
                                    temp = float(temp_str)
                                    # Check if it's a reasonable temperature
                                    if 15 <= temp <= 100:  # Celsius range
                                        if self.dev_mode:
                                            print(f"[WinBattery] WMI sensor temp: {temp:.1f}°C")
                                        return temp
                                    elif 288 <= temp <= 373:  # Kelvin range
                                        temp_celsius = temp - 273.15
                                        if self.dev_mode:
                                            print(f"[WinBattery] WMI sensor temp (K->C): {temp_celsius:.1f}°C")
                                        return temp_celsius
                                except ValueError:
                                    continue

                    except Exception:
                        continue

            except Exception as e:
                if self.dev_mode:
                    print(f"[WinBattery] WMI sensors error: {e}")

            return None

        def _get_temperature_from_registry(self) -> Optional[float]:
            """Extract battery temperature from Windows Registry."""
            try:
                # Registry paths that might contain thermal information
                paths = [
                    r"SYSTEM\CurrentControlSet\Enum\ACPI",
                    r"SYSTEM\CurrentControlSet\Services\Thermal",
                    r"SYSTEM\CurrentControlSet\Control\Power",
                    r"HARDWARE\DESCRIPTION\System\MultifunctionAdapter"
                ]

                for base_path in paths:
                    try:
                        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, base_path) as key:
                            temp = self._search_registry_for_temperature(key, base_path)
                            if temp:
                                if self.dev_mode:
                                    print(f"[WinBattery] Registry temp: {temp:.1f}°C")
                                return temp
                    except FileNotFoundError:
                        continue

            except Exception as e:
                if self.dev_mode:
                    print(f"[WinBattery] Registry error: {e}")

            return None

        def _search_registry_for_temperature(self, key, path: str, depth: int = 0) -> Optional[float]:
            """Recursively search registry for temperature values."""
            if depth > 3:  # Limit recursion depth
                return None

            try:
                # Check values in current key
                i = 0
                while True:
                    try:
                        value_name, value_data, value_type = winreg.EnumValue(key, i)

                        # Look for temperature-related values
                        if any(term in value_name.lower() for term in ['temp', 'thermal', 'heat']):
                            if isinstance(value_data, int):
                                # Convert various temperature formats
                                if 15 <= value_data <= 100:  # Already Celsius
                                    return float(value_data)
                                elif 288 <= value_data <= 373:  # Kelvin
                                    return value_data - 273.15
                                elif 1500 <= value_data <= 10000:  # Tenths of Kelvin
                                    return (value_data / 10.0) - 273.15

                        i += 1
                    except OSError:
                        break

                # Check sub-keys
                i = 0
                while True:
                    try:
                        subkey_name = winreg.EnumKey(key, i)
                        if any(term in subkey_name.lower() for term in ['thermal', 'temp', 'battery', 'power']):

                            try:
                                with winreg.OpenKey(key, subkey_name) as subkey:
                                    temp = self._search_registry_for_temperature(subkey, f"{path}\\{subkey_name}", depth + 1)
                                    if temp:
                                        return temp
                            except Exception:
                                pass
                        i += 1
                    except OSError:
                        break

            except Exception:
                pass

            return None

        def _get_acpi_temperature(self) -> Optional[float]:
            """Get temperature from ACPI thermal management."""
            try:
                # WMIC ACPI thermal zone query
                cmd = ['wmic', '/namespace:\\\\root\\wmi', 'path', 'MSAcpi_ThermalZoneTemperature', 'get',
                       'CurrentTemperature', '/value']
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=5,
                                        creationflags=subprocess.CREATE_NO_WINDOW)

                if result.returncode == 0:
                    matches = re.findall(r'CurrentTemperature=(\d+)', result.stdout)
                    for match in matches:
                        temp_raw = int(match)
                        # ACPI temperature is in tenths of Kelvin
                        temp_celsius = (temp_raw / 10.0) - 273.15

                        if 10 <= temp_celsius <= 90:  # Reasonable range
                            if self.dev_mode:
                                print(f"[WinBattery] ACPI temp: {temp_celsius:.1f}°C")
                            return temp_celsius

            except Exception as e:
                if self.dev_mode:
                    print(f"[WinBattery] ACPI error: {e}")

            return None

        def _get_performance_counter_temperature(self) -> Optional[float]:
            """Get temperature from Windows Performance Counters."""

            try:
                # TypePerf to get thermal performance counters
                cmd = [
                    'typeperf', '-sc', '1',
                    '\\Thermal Zone Information(*)\\Temperature'
                ]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10,
                                        creationflags=subprocess.CREATE_NO_WINDOW)

                if result.returncode == 0:
                    # Parse temperature values from typeperf output
                    lines = result.stdout.split('\n')
                    for line in lines:
                        if 'Temperature' in line and '"' in line:
                            # Extract temperature value
                            parts = line.split('"')
                            if len(parts) >= 3:
                                try:
                                    temp_str = parts[-2].strip()
                                    temp = float(temp_str)

                                    # Convert from Kelvin if necessary
                                    if temp > 200:  # Likely Kelvin
                                        temp_celsius = temp - 273.15
                                    else:
                                        temp_celsius = temp

                                    if 10 <= temp_celsius <= 90:
                                        if self.dev_mode:
                                            print(f"[WinBattery] PerfCounter temp: {temp_celsius:.1f}°C")
                                        return temp_celsius
                                except ValueError:
                                    continue

            except Exception as e:
                if self.dev_mode:
                    print(f"[WinBattery] Performance counter error: {e}")

            return None


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

        # Class constants
        _CACHE_FILENAME: str = ".cache_report"
        _CACHE_REPORT_PATH: str = Path(".cache") / _CACHE_FILENAME
        _REPORT_COMMAND: str = ["powercfg", "/batteryreport"]
        _COMMAND_TIMEOUT: int = 10

        # Compiled regex patterns for better performance
        _SEARCH_PATTERNS: dict = {
            "manufacturer": re.compile(r'MANUFACTURER</span>\s*</td>\s*<td[^>]*>(.*?)</td>', re.IGNORECASE | re.DOTALL),
            'chemistry': re.compile(r'CHEMISTRY</span>\s*</td>\s*<td[^>]*>(.*?)</td>', re.IGNORECASE | re.DOTALL),
            'design_capacity': re.compile(r'DESIGN CAPACITY</span>\s*</td>\s*<td[^>]*>(.*?)</td>',
                                          re.IGNORECASE | re.DOTALL),
            'full_capacity': re.compile(r'FULL CHARGE CAPACITY</span>\s*</td>\s*<td[^>]*>(.*?)</td>',
                                        re.IGNORECASE | re.DOTALL),
            'cycle_count': re.compile(r'CYCLE COUNT</span>\s*</td>\s*<td[^>]*>(.*?)</td>', re.IGNORECASE | re.DOTALL)
        }

        def __init__(self, force_refresh: bool = False):
            """Initialize the battery report with optional cache refresh."""
            self._report_data: Optional[str] = None
            self._initialize_report(force_refresh)

        def _initialize_report(self, force_refresh: bool) -> None:
            """Initialize the report data with error handling."""
            try:
                if not force_refresh and self._cache_exists():
                    self._report_data = self._load_cache()

                # Generate new report if no cache or cache load failed
                if not self._report_data:
                    self._report_data = self._generate_battery_report()
                    if self._report_data:
                        self._save_cache(self._report_data)

            except Exception as e:
                print(f"[BatteryHtmlReport] Error initializing: {e}")
                self._report_data = None

        def _cache_exists(self) -> bool:
            """Check if cache file exists and is readable."""
            return self._CACHE_REPORT_PATH.exists() and self._CACHE_REPORT_PATH.is_file()

        def _load_cache(self) -> Optional[str]:
            """Load and return cached HTML report data."""
            try:
                return self._CACHE_REPORT_PATH.read_text(encoding="utf-8")
            except Exception as e:
                print(f"[BatteryHtmlReport] Error loading cache: {e}")
                return None

        def _save_cache(self, data: str) -> None:
            """Save HTML report data to cache file."""
            try:
                # Ensure cache directory exists
                self._CACHE_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
                self._CACHE_REPORT_PATH.write_text(data, encoding="utf-8")
            except Exception as e:
                print(f"[BatteryHtmlReport] Error saving cache: {e}")

        def _generate_battery_report(self) -> Optional[str]:
            """Generate battery report using powercfg and return HTML content."""
            try:
                # Run powercfg command with timeout
                result = subprocess.run(
                    self._REPORT_COMMAND,
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=self._COMMAND_TIMEOUT
                )

                # Extract report file path
                if match := re.search(r'saved to\s+file path\s+(.+)', result.stdout, re.IGNORECASE):
                    report_path = Path(match.group(1).strip().strip('"'))
                else:
                    print("[BatteryHtmlReport] ❗ Report path not found in output.")
                    return None

                # Validate file exists
                if not report_path.is_file():
                    print(f"[BatteryHtmlReport] ❗ Report file not found at: {report_path}")
                    return None

                # Read and clean up file
                try:
                    return report_path.read_text(encoding="utf-8")
                except (OSError, IOError) as file_err:
                    print(f"[BatteryHtmlReport] ❗ Error reading report: {file_err}")
                    return None
                finally:
                    # Clean up temporary report file
                    try:
                        report_path.unlink(missing_ok=True)
                    except Exception as cleanup_err:
                        print(f"[BatteryHtmlReport] ⚠️ Failed to delete report file: {cleanup_err}")

            except subprocess.TimeoutExpired:
                print("[BatteryHtmlReport] ❗ Command timed out")

            except subprocess.CalledProcessError as e:
                print(f"[BatteryHtmlReport] ❗ Failed to generate report: {e}")

            except Exception as e:
                print(f"[BatteryHtmlReport] ❗ Unexpected error: {e}")

            return None

        def _parse_html(self, query: str, as_int: bool = False) -> Union[str, int]:
            """Parse HTML report data for specific battery information."""
            if not self._report_data:
                return 0 if as_int else "Unknown"

            pattern = self._SEARCH_PATTERNS.get(query)
            if not pattern:
                return 0 if as_int else "Unknown"

            if match := pattern.search(self._report_data):
                raw_text = match.group(1)
                cleaned_text = self._normalize_text(raw_text)

                if as_int:
                    return self._extract_numeric_value(cleaned_text)
                return cleaned_text

            return 0 if as_int else "Unknown"

        @staticmethod
        @lru_cache(maxsize=128)
        def _normalize_text(html_text: str) -> str:
            """Clean HTML text by removing tags and normalizing whitespace."""
            # Remove HTML tags
            text = re.sub(r'<[^>]*>', '', html_text)
            # Decode HTML entities
            text = html.unescape(text)
            # Normalize whitespace
            return ' '.join(text.split())

        @staticmethod
        def _extract_numeric_value(text: str) -> int:
            """Extract numeric value from text, handling various formats."""
            # Remove non-digit characters except commas and periods
            digits_only = re.sub(r'[^\d,.]', '', text)
            # Remove commas (thousand separators)
            digits_only = digits_only.replace(',', '')
            # Handle decimal points by taking integer part
            if '.' in digits_only:
                digits_only = digits_only.split('.')[0]

            try:
                return int(digits_only) if digits_only else 0
            except ValueError:
                return 0

        # Public interface methods
        def battery_manufacturer(self) -> str:
            """Get battery manufacturer."""
            return self._parse_html("manufacturer")

        def battery_chemistry(self) -> str:
            """Get battery chemistry type."""
            return self._parse_html("chemistry")

        def battery_design_capacity(self) -> int:
            """Get battery design capacity in mWh."""
            return self._parse_html("design_capacity", as_int=True)

        def battery_full_capacity(self) -> int:
            """Get battery full charge capacity in mWh."""
            return self._parse_html("full_capacity", as_int=True)

        def battery_cycle_count(self) -> int:
            """Get battery cycle count."""
            return self._parse_html("cycle_count", as_int=True)

        def is_report_available(self) -> bool:
            """Check if battery report data is available."""
            return self._report_data is not None

        def get_battery_health_percentage(self) -> float:
            """Calculate battery health as percentage of design vs full capacity."""
            design = self.battery_design_capacity()
            full = self.battery_full_capacity()

            if design > 0 and full > 0:
                return round((full / design) * 100, 2)
            return 0.0

        def battery_technology(self) -> str:
            """ This method get the battery chemistry string"""
            return self._parse_html("chemistry")


elif platform == "Linux":

    class Battery(_BatteryPy):

        def __init__(self, dev_mode: bool = False) -> None:
            super().__init__()

            # Define constant
            self.dev_mode = dev_mode

        @property
        def manufacturer(self) -> str:
            """ This method will get the manufacturer name string"""

        @property
        def battery_technology(self) -> str:
            """ This method will get the battery technology string name"""

        def cycle_count(self) -> str:
            """ This method will get the battery cycle count"""

        def design_capacity(self) -> int:
            """ This method will get the battery design capacity"""

        def battery_percent(self) -> Optional[int]:
            """ This method will get the battery charging percentage

            Returns:
                Integer percentage (0-100) or None if unavailable
            """

        def is_plugged(self) -> Optional[bool]:
            """ This method will check if the device is plugged into AC power

            Returns:
                True if plugged in , False if on battery, None on error
            """

        def remaining_capacity(self) -> Optional[int]:
            """ This method will get remaining battery capacity in mWh"""

        def charge_rate(self) -> Optional[int]:
            """ This method will get the current charge/discharge rate in mW

            Returns:
                Integer rate in mW (positive when charging, negative when discharging)
                or None on error
            """

        def is_fast_charge(self) -> Optional[bool]:
            """ This method will check if the battery is Fast charging

            Return:
                True if charge fast , False if charge slow, None if the device not charging or error

            """

        def battery_voltage(self) -> Optional[float]:
            """ This method will get the battery voltage"""

        def battery_temperature(self) -> Optional[float]:
            """ This method will get the battery sensor thermal reads"""


else:
    sys.exit("Unsupported platform")


if __name__ == "__main__":
    sys.exit(0)

"""
This code or file is part of 'BatteryPy' project
copyright (c) 2023-2025 , Aymen Brahim Djelloul, All rights reserved.
use of this source code is governed by MIT License that can be found on the project folder.

@author : Aymen Brahim Djelloul
version : 1.4
date    : 03.06.2025
License : MIT

"""

# IMPORTS
import os
import sys
import time
import ctypes
from platform import system
from pathlib import Path
from functools import lru_cache
from typing import Dict, Optional, Union, Any
from datetime import datetime
from abc import ABC, abstractmethod


# Declare software constants
author: str = "Aymen Brahim Djelloul"
version: str = "1.4"
caption: str = f"BatteryPy - v{version}"
website: str = "https://aymenbrahimdjelloul.github.io/BatteryPy"

# Declare supported platforms
_SUPPORTED_PLATFORMS: tuple[str, str] = ("Windows", "Linux")

# Define current system
platform: str = system()

# Set the fast charge rate at 20 Watts
_fast_charge_threshold: int = 20


class BatteryPyException(BaseException):
    """ This class contain the BatteryPy exception"""

    def __init__(self, exception: str) -> None:
        self.e: str = exception

    def __str__(self) -> str:
        """ This method will return the BatteryPy exception error"""
        return f"ERROR : {self.e}"


def _get_datetime() -> str:
    """Get current datetime formatted as string

    Returns:
        Formatted datetime string
    """
    return datetime.now().strftime('%Y-%m-%d')


def _has_battery() -> bool:
    """
    Checks if the device has a battery.

    Returns:
        bool: True if a battery is present, False otherwise.
    """
    try:
        _platform: str = sys.platform

        # --- Windows ---
        if _platform == "win32":

            class SYSTEM_POWER_STATUS(ctypes.Structure):
                _fields_: list[tuple] = [
                    ('ACLineStatus', ctypes.c_byte),
                    ('BatteryFlag', ctypes.c_byte),
                    ('BatteryLifePercent', ctypes.c_byte),
                    ('Reserved1', ctypes.c_byte),
                    ('BatteryLifeTime', ctypes.c_ulong),
                    ('BatteryFullLifeTime', ctypes.c_ulong),
                ]

            status = SYSTEM_POWER_STATUS()
            if not ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(status)):
                return False

            # BatteryFlag bit 128 means no battery
            if status.BatteryFlag & 128:
                return False
            return True

        # --- Linux ---
        elif _platform.startswith("linux"):
            # Check for battery presence in power_supply directory
            battery_paths: list[str] = [
                "/sys/class/power_supply/BAT0",
                "/sys/class/power_supply/BAT1",
                "/sys/class/power_supply/battery",
            ]
            for path in battery_paths:
                if os.path.exists(path):
                    # Also check if 'present' file exists and says '1'
                    present_path: str = os.path.join(path, "present")

                    if os.path.exists(present_path):
                        try:
                            with open(present_path) as f:
                                return f.read(1) == "1"
                        except OSError:
                            return True  # If we can't read, assume present

                    else:
                        return True  # No 'present' file, but battery dir exists

            return False

        # --- macOS ---
        elif _platform == "darwin":
            try:
                output: str = subprocess.check_output(
                    ["pmset", "-g", "batt"],
                    timeout=3,
                    text=True
                ).lower()

                # If pmset returns battery info, battery exists
                if "no battery" in output:
                    return False
                if "battery" in output:
                    return True

            except Exception:
                return False
            return False

        else:
            return False

    except Exception:
        return False


class _BatteryPy(ABC):
    """
    Abstract base class for battery information retrieval across different platforms.

    This class defines the interface that all platform-specific battery classes must implement.
    It provides a standardized way to access battery information regardless of the underlying
    operating system or implementation details.
    """

    def __init__(self) -> None:
        """Initialize the base battery class."""
        self._report_path: Optional[str] = None

    # Abstract methods that subclasses must implement
    @abstractmethod
    def battery_percent(self) -> int:
        """Get current battery charge percentage (0-100)."""
        pass

    @abstractmethod
    def is_plugged(self) -> bool:
        """Check if the device is connected to AC power."""
        pass

    @abstractmethod
    def remaining_capacity(self) -> int:
        """Get remaining battery capacity in mWh."""
        pass

    @abstractmethod
    def design_capacity(self) -> int:
        """
        Get the battery design capacity in mWh or mAh

        Returns:
            Design capacity or None if unavailable
        """
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

    def get_result(self) -> Dict[str, Any]:
        """Collect all battery information into a comprehensive dictionary.

        Returns:
            Dictionary with all available battery information
        """


        # Build the formatted result dictionary
        data: dict[str, Any] = {
            'battery_percent': self._format_percentage(self.battery_percent),
            'power_status': self._format_power_status(self.is_plugged()),
            'design_capacity': self._format_capacity(self.design_capacity),
            'charge_rate': self.charge_rate(),
            'fast_charge': self.is_fast_charge() or "n/a",
            'manufacturer': self.manufacturer or "n/a",
            'technology': self.battery_technology or "n/a",
            'cycle_count': self.cycle_count or 0,
            'battery_health': self._format_health(self.battery_health),
            'battery_voltage': self._format_voltage(self.battery_voltage()),
            'battery_temperature': self._format_temperature(self.battery_temperature()),
            'report_generated': _get_datetime(),
        }

        return data

    def _estimate_battery_voltage(self) -> Optional[float]:
        """Estimate voltage based on battery chemistry from PowerShell."""

        try:
            cmd: list[str] = [
                'powershell.exe', '-NoProfile', '-Command',
                "(Get-WmiObject Win32_Battery).Chemistry"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=3,
                                    creationflags=subprocess.CREATE_NO_WINDOW)

            if result.returncode == 0 and result.stdout.strip():
                chemistry: int = int(result.stdout.strip())

                # Battery chemistry voltage mapping
                voltage_map: dict[int, float] = {
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
                    voltage = voltage * 3  # Most laptops use 3-cell config (11.1 V)

                if self.dev_mode:
                    print(f"[WinBattery] Estimated voltage (chemistry {chemistry}): {voltage:.1f}V")
                return voltage

        except Exception as e:
            if self.dev_mode:
                print(f"[WinBattery] Chemistry estimation error: {e}")

        return None


    @staticmethod
    def _format_percentage(percentage: Optional[int]) -> str:
        """Format battery percentage as a string with a percent symbol."""
        return f"{percentage}%" if percentage is not None and percentage >= 0 else "n/a"

    @staticmethod
    def _format_power_status(is_plugged: Optional[bool]) -> str:
        """Format power connection status as 'Plugged In' or 'On Battery'."""
        if is_plugged is None:
            return "n/a"
        return "Plugged In" if is_plugged else "On Battery"

    @staticmethod
    def _format_capacity(capacity: Optional[int]) -> str:
        """Format battery capacity in mWh, using thousands separator."""
        return f"{capacity:,} mWh" if capacity is not None and capacity > 0 else "n/a"

    @staticmethod
    def _format_charge_rate(rate: Optional[int]) -> str:
        """Format charge/discharge rate in mW with charging direction."""
        if rate is None or rate == 0:
            return "n/a"
        direction: str = "Charging" if rate > 0 else "Discharging"
        return f"{abs(rate)} Watts ({direction})"

    @staticmethod
    def _format_health(health: Optional[float]) -> str:
        """Format battery health as a percentage with one decimal place."""
        return f"{health:.1f}%" if health is not None and health >= 0 else "n/a"

    @staticmethod
    def _format_voltage(voltage: Optional[float]) -> str:
        """Format battery voltage in volts with two decimal places."""
        return f"{voltage:.2f} V" if voltage is not None and voltage >= 0 else "n/a"

    @staticmethod
    def _format_temperature(temperature: Optional[float]) -> str:
        """Format battery temperature in Celsius with one decimal place."""
        return f"{temperature:.1f}° C"



# Initialize BatteryPy
if platform == "Windows":

    # WINDOWS IMPORTS
    import re
    import winreg
    import ctypes
    import subprocess
    import html
    from ctypes import byref, Structure, c_ulong, c_ubyte, c_bool

    class _SYSTEM_BATTERY_STATE(Structure):
        """Windows SYSTEM_BATTERY_STATE structure for battery information."""

        _fields_: list = [
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
        _CACHE_DURATION_SECONDS = 2  # Cache API calls for 2 seconds
        _POWER_INFO_BATTERY_STATE = 5  # Windows API constant

        # Define commands constants
        powershell_cmd_battery: list[str] = [
            'powershell.exe', '-NoProfile', '-Command',
            "(Get-WmiObject Win32_Battery).DesignVoltage"
        ]

        def __init__(self, dev_mode: bool = False) -> None:
            """Initialize the Battery class with Windows API access.

            Args:
                dev_mode: Enable development mode for additional logging
            """
            super().__init__()

            # Check if Battery exists
            if not _has_battery():
                raise BatteryPyException("BatteryPy cannot detect any battery")

            self.dev_mode = dev_mode
            self._last_api_call: int = 0
            self._cached_state: bool = None

            # Initialize battery report (static information)
            self._battery_report = _BatteryHtmlReport(dev_mode=self.dev_mode)

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

            current_time: float = time.time()

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

        @property
        def battery_percent(self) -> Optional[int]:
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
            """Check if the device is connected to AC power.

            Returns:
                True if plugged in, False if on battery power
            """
            state = self._get_battery_state()
            return bool(state.AcOnLine) if state else False

        def remaining_capacity(self) -> int:
            """Get the remaining battery capacity in mWh.

            Returns:
                Integer capacity in mWh, returns 0 if unavailable
            """
            state = self._get_battery_state()
            if not state or not state.BatteryPresent:
                return 0
            return state.RemainingCapacity

        def charge_rate(self, as_int: bool = False) -> str | int:
            """
            Get the current charge/discharge rate in Watts.

            Args:
                as_int (bool): If True, return raw integer rate in Watts.
                                      If False, return formatted string.

            Returns:
                Charge/discharge rate in Watts:
                    - Positive when charging
                    - Negative when discharging
                    - 0 if unavailable
                    Returned as string or int depending on `as_int`.
            """
            state = self._get_battery_state()
            if not state or not state.BatteryPresent:
                return 0 if as_int else self._format_charge_rate(0)

            try:
                rate_mw = int(state.Rate)
                rate_w = round(rate_mw / 1000)  # Convert to Watts

                if state.Discharging and rate_w > 0:
                    rate_w = -abs(rate_w)
                elif state.Charging and rate_w < 0:
                    rate_w = abs(rate_w)
                elif state.Charging:
                    rate_w = abs(rate_w)
                else:
                    rate_w = -abs(rate_w) if rate_w != 0 else 0

                return rate_w if as_int else self._format_charge_rate(rate_w)

            except (ValueError, OverflowError):
                return 0 if as_int else self._format_charge_rate(0)

        def is_fast_charge(self) -> Optional[bool]:
            """Check if battery is fast charging.

            Returns:
                True if the charging rate exceeds the fast charge threshold
            """
            if not self.is_plugged():
                return None

            return abs(self.charge_rate(as_int=True)) > _fast_charge_threshold

        @property
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

            if self.dev_mode:
                print("[WinBattery] All voltage detection methods failed")

            # Fallback
            return self._estimate_battery_voltage()

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

        def battery_temperature(self) -> Optional[float]:
            """Get battery temperature using only Windows built-in APIs and standard library.

            Returns:
                float: Battery temperature in Celsius, or None if unavailable
            """

            # Method 1: PowerShell WMI Battery Temperature (direct)
            # try:
            #     cmd = [
            #         'powershell.exe', '-NoProfile', '-Command',
            #         "(Get-WmiObject Win32_Battery | Where-Object {$_.Temperature -ne $null}).Temperature"
            #     ]
            #     result = subprocess.run(cmd, capture_output=True, text=True, timeout=3,
            #                             creationflags=subprocess.CREATE_NO_WINDOW)
            #
            #     if result.returncode == 0 and result.stdout.strip():
            #         # The Temperature in WMI is typically in tenths of Kelvin
            #         temp_raw = float(result.stdout.strip())
            #         if temp_raw > 1000:  # Likely in tenths of Kelvin
            #             temp_celsius = (temp_raw / 10.0) - 273.15
            #         else:  # Already in Celsius or other format
            #             temp_celsius = temp_raw
            #
            #         if -40 <= temp_celsius <= 100:  # Reasonable battery temperature range
            #             if self.dev_mode:
            #                 print(f"[WinBattery] Battery temperature: {temp_celsius:.1f}°C")
            #             return temp_celsius
            # except Exception as e:
            #     if self.dev_mode:
            #         print(f"[WinBattery] PowerShell battery temp failed: {e}")


            # Method 2: Thermal Zone queries (system temperature)
            try:
                temp = self._get_thermal_zone_temperature()
                if temp:
                    return temp
            except Exception as e:
                if self.dev_mode:
                    print(f"[WinBattery] Thermal zone method failed: {e}")

            # Method 5: ACPI thermal information
            try:
                temp = self._get_acpi_temperature()
                if temp:
                    return temp
            except Exception as e:
                if self.dev_mode:
                    print(f"[WinBattery] ACPI method failed: {e}")

            if self.dev_mode:
                print("[WinBattery] All temperature detection methods failed")

            return None

        def _get_thermal_zone_temperature(self) -> Optional[float]:
            """Get temperature from Windows thermal zones."""
            try:
                # Query thermal zones
                cmd: list[str] = [
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
                                # The Temperature is in tenths of Kelvin
                                temp_raw = float(line.strip())
                                temp_celsius = (temp_raw / 10.0) - 273.15

                                # Look for a reasonable battery temperature (usually 20-50°C)
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
                # Check values in the current key
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
        command executions and the file reads. It provides methods to extract key information such as
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
        _CREATE_NO_WINDOW = 0x08000000

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

        def __init__(self, force_refresh: bool = False, dev_mode: bool = False) -> None:
            """Initialize the battery report with optional cache refresh."""

            # Declare class constants
            self.dev_mode = dev_mode
            self._report_data: Optional[str] = None
            self._initialize_report(force_refresh)

        def _initialize_report(self, force_refresh: bool) -> None:
            """Initialize the report data with error handling."""
            try:
                if not force_refresh and self._cache_exists():
                    self._report_data = self._load_cache()

                # Generate the new report if no cache or cache load failed
                if not self._report_data:
                    self._report_data = self._generate_battery_report()
                    if self._report_data:
                        self._save_cache(self._report_data)

            except Exception as e:

                # Print exception in dev mode
                if self.dev_mode:
                    print(f"[BatteryHtmlReport] Error initializing: {e}")

                self._report_data = None

        def _cache_exists(self) -> bool:
            """Check if the cache file exists and is readable."""
            return self._CACHE_REPORT_PATH.exists() and self._CACHE_REPORT_PATH.is_file()

        def _load_cache(self) -> Optional[str]:
            """Load and return cached HTML report data."""

            try:
                return self._CACHE_REPORT_PATH.read_text(encoding="utf-8")

            except Exception as e:

                # Print exception in dev mode
                if self.dev_mode:
                    print(f"[BatteryHtmlReport] Error loading cache: {e}")

                return None

        def _save_cache(self, data: str) -> None:
            """Save HTML report data to a cache file."""
            try:
                # Ensure cache directory exists
                self._CACHE_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
                self._CACHE_REPORT_PATH.write_text(data, encoding="utf-8")
            except Exception as e:
                print(f"[BatteryHtmlReport] Error saving cache: {e}")

        def _generate_battery_report(self) -> Optional[str]:
            """Generate a battery report using powercfg and return HTML content."""
            try:
                # Run powercfg command with timeout
                result = subprocess.run(
                    self._REPORT_COMMAND,
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=self._COMMAND_TIMEOUT,
                    creationflags=self._CREATE_NO_WINDOW,
                )

                # Extract the report file path
                if match := re.search(r'saved to\s+file path\s+(.+)', result.stdout, re.IGNORECASE):
                    report_path = Path(match.group(1).strip().strip('"'))
                else:
                    # Print exception in dev mode
                    if self.dev_mode:
                        print("[BatteryHtmlReport] ❗ Report path not found in output.")

                    return None

                # Validate file exists
                if not report_path.is_file():

                    # Print exception in dev mode
                    if self.dev_mode:
                        print(f"[BatteryHtmlReport] ❗ Report file not found at: {report_path}")

                    return None

                # Read and clean up file
                try:
                    return report_path.read_text(encoding="utf-8")
                except (OSError, IOError) as file_err:

                    # Print exception in dev mode
                    if self.dev_mode:
                        print(f"[BatteryHtmlReport] ❗ Error reading report: {file_err}")

                    return None
                finally:
                    # Cleanup temporary report file
                    try:
                        report_path.unlink(missing_ok=True)
                    except Exception as cleanup_err:
                        print(f"[BatteryHtmlReport] ⚠️ Failed to delete report file: {cleanup_err}")

            except (subprocess.TimeoutExpired, subprocess.CalledProcessError, Exception) as err:

                # Print exception in dev mode
                if self.dev_mode:
                    print(f"[BatteryHtmlReport] ERROR : {err}")

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
            # Remove commas (a thousand separators)
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
            """Get the battery manufacturer."""
            return self._parse_html("manufacturer")

        def battery_chemistry(self) -> str:
            """Get the battery chemistry type."""
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
            """Calculate battery health as percentage of design vs. full capacity."""
            design = self.battery_design_capacity()
            full = self.battery_full_capacity()

            if design > 0 and full > 0:
                return round((full / design) * 100, 2)
            return 0.0

        def battery_technology(self) -> str:
            """ This method gets the battery chemistry string"""
            return self._parse_html("chemistry")


elif platform == "Linux":

    class Battery(_BatteryPy):
        """
        Linux-specific battery information class that reads from /sys/class/power_supply/
        """

        # Linux battery sysfs paths
        POWER_SUPPLY_PATH: str = "/sys/class/power_supply"

        # Battery property mappings
        BATTERY_PROPERTIES: dict[str, str] = {
            "manufacturer": "manufacturer",
            "technology": "technology",
            "cycle_count": "cycle_count",
            "capacity": "capacity",
            "capacity_level": "capacity_level",
            "status": "status",
            "present": "present",
            "voltage_now": "voltage_now",
            "voltage_min_design": "voltage_min_design",
            "current_now": "current_now",
            "power_now": "power_now",
            "energy_now": "energy_now",
            "energy_full": "energy_full",
            "energy_full_design": "energy_full_design",
            "charge_now": "charge_now",
            "charge_full": "charge_full",
            "charge_full_design": "charge_full_design",
            "temp": "temp"
        }

        def __init__(self, dev_mode: bool = False) -> None:
            super().__init__()

            # Declare constants
            self.dev_mode = dev_mode
            self._battery_path = None
            self._ac_adapter_paths: list = []

            # Check if Battery exists
            if not _has_battery():
                raise BatteryPyException("BatteryPy cannot detect any battery")

            # Initialize battery and AC adapter paths
            self._discover_power_supplies()

            if not self._battery_path and not dev_mode:
                raise RuntimeError("No battery found in /sys/class/power_supply/")

        def _discover_power_supplies(self) -> None:
            """
            Discover available batteries and AC adapters in the system
            """
            if not os.path.exists(self.POWER_SUPPLY_PATH):
                return

            power_supplies: list = os.listdir(self.POWER_SUPPLY_PATH)
            batteries: list = []

            for supply in power_supplies:
                supply_path = os.path.join(self.POWER_SUPPLY_PATH, supply)
                type_file = os.path.join(supply_path, "type")

                if os.path.exists(type_file):
                    supply_type = self._read_file(type_file)

                    if supply_type == "Battery":
                        batteries.append(supply_path)
                    elif supply_type == "Mains":
                        self._ac_adapter_paths.append(supply_path)

            # Select battery
            # if preferred_battery:
            #     preferred_path = os.path.join(self.POWER_SUPPLY_PATH, preferred_battery)
            #     if preferred_path in batteries:
            #         self._battery_path = preferred_path
            #     else:
            #         raise ValueError(f"Battery '{preferred_battery}' not found")
            # elif batteries:
                # Use first available battery
            self._battery_path = batteries[0]

        @staticmethod
        def _read_file(file_path: str) -> Optional[str]:
            """
            Reads the contents of the specified file and returns it as a string.

            Args:
                file_path: Path to the file to read

            Returns:
                The file content as a string (stripped), or None if error/empty
            """
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    return content if content else None
            except (FileNotFoundError, PermissionError, OSError):
                return None

        def _read_battery_property(self, property_name: str) -> Optional[str]:
            """
            Read a specific battery property from sysfs

            Args:
                property_name: Name of the property file to read

            Returns:
                Property value as string or None if not available
            """
            if not self._battery_path:
                if self.dev_mode:
                    print(f"[DEV] _read_battery_property({property_name}): No battery path available")
                return None

            property_path = os.path.join(self._battery_path, property_name)
            value = self._read_file(property_path)

            if self.dev_mode:
                if value is not None:
                    print(f"[DEV] _read_battery_property({property_name}): Read '{value}' from {property_path}")
                else:
                    print(f"[DEV] _read_battery_property({property_name}): Failed to read from {property_path}")

            return value

        def _read_battery_int(self, property_name: str) -> Optional[int]:
            """
            Read a battery property as integer
            """
            value = self._read_battery_property(property_name)
            if value is None:
                return None
            try:
                return int(value)
            except ValueError:
                return None

        def _read_battery_float(self, property_name: str) -> Optional[float]:
            """
            Read a battery property as float
            """
            value = self._read_battery_property(property_name)
            if value is None:
                return None
            try:
                return float(value)
            except ValueError:
                return None

        @property
        def manufacturer(self) -> Optional[str]:
            """Get the battery manufacturer name"""
            return self._read_battery_property("manufacturer")

        @property
        def battery_technology(self) -> str:
            """Get the battery technology (Li-ion, Li-poly, etc.)"""
            technology: str = "Lithium-Ion" if self._read_battery_property("technology") != "Unkown" else \
                    self._read_battery_property("technology")

            if technology is not None:
                if self.dev_mode:
                    print(f"[DEV] battery_technology: Using original value '{technology}'")
                return technology

            else:
                if self.dev_mode:
                    print("[DEV] battery_technology: Using fallback value 'Lithium-ion'")
                return "Lithium-ion"

        @property
        def cycle_count(self) -> Optional[int]:
            """Get the battery cycle count"""
            return self._read_battery_int("cycle_count")

        def design_capacity(self) -> Optional[int]:
            """
            Get the battery design capacity in mWh or mAh

            Returns:
                Design capacity or None if unavailable
            """
            # Try energy first (mWh), then charge (mAh)
            capacity = self._read_battery_int("energy_full_design")
            if capacity is not None:
                result = capacity // 1000  # Convert µWh to mWh
                if self.dev_mode:
                    print(f"[DEV] design_capacity: Using energy_full_design ({capacity} µWh -> {result} mWh)")
                return result

            capacity = self._read_battery_int("charge_full_design")
            if capacity is not None:
                result = capacity // 1000  # Convert µAh to mAh
                if self.dev_mode:
                    print(f"[DEV] design_capacity: Using charge_full_design fallback ({capacity} µAh -> {result} mAh)")
                return result

            if self.dev_mode:
                print("[DEV] design_capacity: No capacity information available")
            return None

        @property
        def battery_health(self) -> Optional[float]:
            """
            Calculate battery health as percentage (current_full/design_full * 100)

            Returns:
                Battery health percentage (0-100) or None if unavailable
            """
            # Try energy values first
            current_full = self._read_battery_int("energy_full")
            design_full = self._read_battery_int("energy_full_design")

            if current_full is not None and design_full is not None and design_full > 0:
                health = round((current_full / design_full) * 100, 2)
                if self.dev_mode:
                    print(f"[DEV] battery_health: Using energy values ({current_full}/{design_full} = {health}%)")
                return health

            # Fallback to charge values
            current_full = self._read_battery_int("charge_full")
            design_full = self._read_battery_int("charge_full_design")

            if current_full is not None and design_full is not None and design_full > 0:
                health = round((current_full / design_full) * 100, 2)
                if self.dev_mode:
                    print(
                        f"[DEV] battery_health: Using charge values fallback ({current_full}/{design_full} = {health}%)")
                return health

            if self.dev_mode:
                print("[DEV] battery_health: No health information available")
            return 0

        @property
        def battery_percent(self) -> Optional[int]:
            """
            Get the battery charging percentage

            Returns:
                Integer percentage (0-100) or None if unavailable
            """
            return self._read_battery_int("capacity")

        def is_plugged(self) -> Optional[bool]:
            """
            Check if the device is plugged into AC power

            Returns:
                True if plugged in, False if on battery, None on error
            """
            # Check AC adapter status
            for i, ac_path in enumerate(self._ac_adapter_paths):
                online_file = os.path.join(ac_path, "online")
                online_status = self._read_file(online_file)
                if online_status == "1":
                    if self.dev_mode:
                        print(f"[DEV] is_plugged: AC adapter {i} online - using original method")
                    return True

            # Fallback: check battery status
            status = self._read_battery_property("status")
            if status:
                is_plugged = status.lower() in ["charging", "full"]
                if self.dev_mode:
                    print(f"[DEV] is_plugged: Using battery status fallback (status='{status}', plugged={is_plugged})")
                return is_plugged

            if self.dev_mode:
                print("[DEV] is_plugged: No power information available")
            return None

        def remaining_capacity(self) -> Optional[int]:
            """
            Get remaining battery capacity in mWh or mAh

            Returns:
                Remaining capacity or None if unavailable
            """
            # Try energy first (mWh)
            capacity = self._read_battery_int("energy_now")
            if capacity is not None:
                result = capacity // 1000  # Convert µWh to mWh
                if self.dev_mode:
                    print(f"[DEV] remaining_capacity: Using energy_now ({capacity} µWh -> {result} mWh)")
                return result

            # Fallback to charge (mAh)
            capacity = self._read_battery_int("charge_now")
            if capacity is not None:
                result = capacity // 1000  # Convert µAh to mAh
                if self.dev_mode:
                    print(f"[DEV] remaining_capacity: Using charge_now fallback ({capacity} µAh -> {result} mAh)")
                return result

            if self.dev_mode:
                print("[DEV] remaining_capacity: No capacity information available")
            return None

        def charge_rate(self) -> Optional[int]:
            """
            Get the current battery charge or discharge rate in milliwatts (mW).

            Returns:
                int: Charge rate in mW (positive for charging, negative for discharging),
                     or None if unavailable.
            """

            def signed_power(value_uw: int, status: Optional[str]) -> int:
                """Convert µW to mW and apply sign based on charging status."""
                mw = abs(value_uw) // 1000
                if status and status.lower() == "discharging":
                    return -mw
                return mw

            status = self._read_battery_property("status")

            # Primary method: power_now (in µW)
            power_uw = self._read_battery_int("power_now")
            if power_uw is not None:
                result = signed_power(power_uw, status)
                if self.dev_mode:
                    print(f"[DEV] charge_rate: Using power_now ({power_uw} µW -> {result} mW, status='{status}')")
                return result

            # Fallback method: current_now (µA) * voltage_now (µV)
            current_ua = self._read_battery_int("current_now")
            voltage_uv = self._read_battery_int("voltage_now")

            if current_ua is not None and voltage_uv is not None:
                power_uw = abs(current_ua) * voltage_uv  # Still in µW
                result = signed_power(power_uw, status) // 1000  # Convert to mW
                if self.dev_mode:
                    print(f"[DEV] charge_rate: Fallback using current * voltage "
                          f"({current_ua} µA * {voltage_uv} µV = {power_uw} µW -> {result} mW, status='{status}')")
                return result

            if self.dev_mode:
                print("[DEV] charge_rate: No power data available")
            return None

        def is_fast_charge(self) -> Optional[bool] | str:
            """
            Check if the battery is fast charging

            Returns:
                True if fast charging, False if slow charging,
                None if not charging or error
            """
            if not self.is_plugged():
                return None

            status = self._read_battery_property("status")
            if not status or status.lower() != "charging":
                return False

            charge_rate = self.charge_rate()
            if charge_rate is None or charge_rate <= 0:
                return False

            # Consider fast charging if rate > 20W (arbitrary threshold)
            # You may want to adjust this based on your device specifications
            return charge_rate > _fast_charge_threshold

        def battery_voltage(self) -> Optional[float]:
            """
            Get the current battery voltage in Volts

            Returns:
                Voltage in Volts or None if unavailable
            """
            voltage_uv = self._read_battery_int("voltage_now")
            if voltage_uv is not None:
                return voltage_uv / 1000000.0  # Convert µV to V

            # Fallback estimate the voltage
            return self._estimate_battery_voltage()

        def battery_temperature(self) -> Optional[float]:
            """
            Get the battery temperature in Celsius

            Returns:
                Temperature in Celsius or None if unavailable
            """
            temp = self._read_battery_int("temp")
            if temp is not None:
                return temp / 10.0  # Convert from tenths of degrees

            # Fallback
            return None

        # @property
        # def battery_status(self) -> Optional[str]:
        #     """
        #     Get the current battery status
        #
        #     Returns:
        #         Status string (Charging, Discharging, Full, etc.) or None
        #     """
        #     return self._read_battery_property("status")


else:
    sys.exit("Unsupported platform")


if __name__ == "__main__":
    sys.exit(0)

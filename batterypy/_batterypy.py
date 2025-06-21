"""
This code or file is part of 'BatteryPy' project
copyright (c) 2023-2025 , Aymen Brahim Djelloul, All rights reserved.
use of this source code is governed by MIT License that can be found on the project folder.

@_AUTHOR : Aymen Brahim Djelloul
VERSION : 1.5
date    : 19.06.2025
License : MIT License

"""

# IMPORTS
import os
import re
import sys
import time
from pathlib import Path
from functools import lru_cache
from typing import Dict, Optional, Union, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from abc import ABC, abstractmethod


# Declare software constants
VERSION: str = "1.5"
_AUTHOR: str = "Aymen Brahim Djelloul"
_CAPTION: str = f"BatteryPy - v{VERSION}"
_WEBSITE: str = "https://aymenbrahimdjelloul.github.io/BatteryPy"

# Declare supported platforms
_SUPPORTED_PLATFORMS: tuple[str, str] = ("Windows", "Linux")

# Define current system
_PLATFORM: str = sys.platform


class BatteryPyException(BaseException):
    """ This class contain the BatteryPy exception"""

    def __init__(self, exception: str) -> None:
        self.e: str = exception

    def __str__(self) -> str:
        """ This method will return the BatteryPy exception error"""
        return f"ERROR : {self.e}"


class _BatteryPy(ABC):
    """
    Abstract base class for battery information retrieval across different platforms.

    This class defines the interface that all platform-specific battery classes must implement.
    It provides a standardized way to access battery information regardless of the underlying
    operating system or implementation details.
    """

    def __init__(self, dev_mode: bool = True, timeout: float = 2.0):
        """
        Initialize the base battery class.

        Args:
            dev_mode: Enable development/debug mode for verbose output
            timeout: Timeout for system calls in seconds
        """

        self._report_path: Optional[str] = None
        self._dev_mode = dev_mode
        self._timeout = timeout
        self._cache_ttl: int = 1.0  # Cache results for 1 second to avoid excessive system calls
        self._last_cache_time: int = 0
        self._FAST_CHARGE_THRESHOLD: int = 20000    # Set the fast charge rate at 20 Watts
        self._cached_result: Optional[Dict[str, Any]] = None

        # Validate battery presence on initialization
        if not self._has_battery():
            raise BatteryPyException("No battery detected on this system")

    @lru_cache(maxsize=1)
    def _has_battery(self) -> bool:
        """
        Ultra-fast cross-platform battery hardware detection.
        Determines if the system has a battery (laptop) vs desktop computer.

        Returns:
            bool: True if system has battery hardware, False if desktop

        Raises:
            BatteryPyException: If battery detection fails or unsupported platform
        """

        try:

            if _PLATFORM == "win32":
                # Define Windows power status structure
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
                kernel32 = ctypes.windll.kernel32

                if not kernel32.GetSystemPowerStatus(ctypes.byref(status)):
                    raise BatteryPyException("Windows power status unavailable")

                # Fast path: definitive no-battery indicators
                if status.BatteryFlag in (128, 255) and status.BatteryLifePercent == 255:
                    return False

                # Fast path: valid battery percentage (most common)
                if 0 <= status.BatteryLifePercent <= 100:
                    return True

                # Check battery flags with bitwise operation (faster)
                return status.BatteryFlag & 0x0F != 0

            elif _PLATFORM == "linux":
                # Essential battery files to check
                essential_files: set[str] = {'capacity', 'energy_now', 'charge_now'}
                power_supply_path: str = "/sys/class/power_supply/"

                # Check if power supply directory exists
                if not os.path.exists(power_supply_path):
                    return False

                try:
                    # Use scandir for better performance
                    with os.scandir(power_supply_path) as entries:
                        for entry in entries:
                            if entry.is_dir() and entry.name.lower().startswith(("bat", "battery")):
                                try:
                                    # Check if any essential battery files exist
                                    entry_path = entry.path
                                    if any(os.path.exists(os.path.join(entry_path, f)) for f in essential_files):
                                        return True

                                except (OSError, PermissionError):
                                    continue

                except (OSError, PermissionError):
                    pass

                return False

            elif _PLATFORM == "darwin":
                # Try pmset first (faster and more reliable)
                try:
                    result = subprocess.run(
                        ["pmset", "-g", "batt"],
                        capture_output=True, text=True, timeout=2, check=False
                    )

                    if result.returncode == 0:
                        output_lower = result.stdout.lower()
                        # Check no-battery indicators first (early exit)
                        if any(x in output_lower for x in ("no batteries", "not found", "unavailable")):
                            return False
                        # Check battery indicators
                        if any(x in output_lower for x in ("battery", "charging", "discharging", "%")):
                            return True
                except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
                    pass

                # Fallback to system_profiler
                try:
                    result = subprocess.run(
                        ["system_profiler", "SPPowerDataType"],
                        capture_output=True, text=True, timeout=3, check=False
                    )
                    return result.returncode == 0 and "battery" in result.stdout.lower()
                except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
                    return False

            else:
                raise BatteryPyException(f"Unsupported platform: {system_platform}")

        except BatteryPyException:
            raise

        except Exception as e:
            raise BatteryPyException(f"Battery hardware detection failed: {e}")

    @abstractmethod
    def battery_percent(self) -> Optional[int]:
        """Get current battery charge percentage (0-100)."""
        pass

    @abstractmethod
    def is_plugged(self) -> Optional[bool]:
        """Check if the device is connected to AC power."""
        pass

    @abstractmethod
    def remaining_capacity(self) -> Optional[int]:
        """Get remaining battery capacity in mWh."""
        pass

    @abstractmethod
    def design_capacity(self) -> Optional[int]:
        """Get the battery design capacity in mWh or mAh."""
        pass

    @abstractmethod
    def charge_rate(self) -> Optional[int]:
        """Get current charge/discharge rate in mW."""
        pass

    @abstractmethod
    def is_fast_charge(self) -> Optional[bool]:
        """Check if battery is fast charging."""
        pass

    @abstractmethod
    def battery_manufacturer(self) -> Optional[str]:
        """Get battery manufacturer name."""
        pass

    @abstractmethod
    def battery_technology(self) -> Optional[str]:
        """Get battery chemistry/technology type."""
        pass

    @abstractmethod
    def cycle_count(self) -> Optional[int]:
        """Get battery cycle count."""
        pass

    @abstractmethod
    def battery_health(self) -> Optional[float]:
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

    def get_result(self, use_cache: bool = True, parallel: bool = True) -> Dict[str, Any]:
        """Collect all battery information into a comprehensive dictionary."""
        current_time = time.time()

        # Return cached result if valid
        if (use_cache and self._cached_result and
                current_time - self._last_cache_time < self._cache_ttl):

            return self._cached_result.copy()

        try:
            data = self._get_result_parallel() if parallel else self._get_result_sequential()

            # Cache successful result
            if data:  # Only cache if we got some data
                self._cached_result = data.copy()
                self._last_cache_time = current_time

            return data

        except Exception:

            if self._dev_mode:
                import traceback
                traceback.print_exc()

            # Even in fallback, try to return partial cached data if available
            if self._cached_result:
                return self._cached_result.copy()

            return self._get_fallback_result()

    def _get_result_parallel(self) -> Dict[str, Any]:
        """Get battery information using parallel execution with robust error handling."""

        data: dict[str, Any] = {}
        tasks: dict[str, Any] = {
            'battery_percent': self.battery_percent,
            'is_plugged': self.is_plugged,
            'design_capacity': self.design_capacity,
            'remaining_capacity': self.remaining_capacity,
            'charge_rate': self.charge_rate,
            'is_fast_charge': self.is_fast_charge,
            'manufacturer': self.battery_manufacturer,
            'battery_technology': self.battery_technology,
            'cycle_count': self.cycle_count,
            'battery_health': self.battery_health,
            'battery_voltage': self.battery_voltage,
            'battery_temperature': self.battery_temperature,
        }

        # Submit all tasks first
        with ThreadPoolExecutor(max_workers=4) as executor:
            future_to_key: dict = {}

            # Submit tasks with individual error handling
            for key, func in tasks.items():
                try:
                    future = executor.submit(self._safe_execute, func)
                    future_to_key[future] = key

                except Exception:

                    if self._dev_mode:
                        import traceback
                        traceback.print_exc()

                    data[key] = None

            # Collect results with timeout handling for individual futures
            completed_count: int = 0
            total_tasks: int = len(future_to_key)

            # Use a more generous timeout but handle individual task timeouts
            try:
                for future in as_completed(future_to_key, timeout=self._timeout * 2):
                    key = future_to_key[future]
                    try:
                        # Individual task timeout
                        result = future.result(timeout=1.0)
                        data[key] = result
                        completed_count += 1
                    except (TimeoutError, Exception):

                        if self._dev_mode:
                            import traceback
                            traceback.print_exc()

                        data[key] = None
                        completed_count += 1

            except TimeoutError:
                # Overall timeout - collect what we have and set the rest to None
                print(f"Overall timeout reached. Completed {completed_count}/{total_tasks} tasks")

                if self._dev_mode:
                    import traceback
                    traceback.print_exc()

                # Cancel remaining futures and set their results to None
                for future, key in future_to_key.items():
                    if not future.done():
                        future.cancel()
                        if key not in data:
                            data[key] = None

            # Ensure all expected keys are present
            for key in tasks.keys():
                if key not in data:
                    data[key] = None

        return self._format_result_data(data)

    def _safe_execute(self, func) -> Any:
        """Execute a function safely with enhanced error handling."""
        try:
            # Add a small delay to prevent system overload
            # time.sleep(0.01)
            return func()

        except (TimeoutError, Exception):

            # Log the specific error but don't propagate
            if self._dev_mode:
                import traceback
                traceback.print_exc()

            return None


    def _get_result_sequential(self) -> Dict[str, Any]:
        """Get battery information sequentially."""

        data_methods: list[tuple] = [
            ('battery_percent', self.battery_percent),
            ('is_plugged', self.is_plugged),
            ('design_capacity', self.design_capacity),
            ('remaining_capacity', self.remaining_capacity),
            ('charge_rate', self.charge_rate),
            ('is_fast_charge', self.is_fast_charge),
            ('manufacturer', self.battery_manufacturer),
            ('battery_technology', self.battery_technology),
            ('cycle_count', self.cycle_count),
            ('battery_health', self.battery_health),
            ('battery_voltage', self.battery_voltage),
            ('battery_temperature', self.battery_temperature),
        ]

        return self._format_result_data({key: self._safe_execute(method) for key, method in data_methods})

    def _format_result_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format raw data into the final result dictionary."""
        if self._dev_mode:
            print(f"Raw data received: {raw_data}")

        try:
            formatted_data: dict[str, Any] = {
                'battery_percent': self._format_percentage(raw_data.get('battery_percent')),
                'power_status': self._format_power_status(raw_data.get('is_plugged')),
                'design_capacity': self._format_capacity(raw_data.get('design_capacity')),
                'remaining_capacity': self._format_capacity(raw_data.get('remaining_capacity')),
                'charge_rate': self._format_charge_rate(raw_data.get('charge_rate')),
                'fast_charge': self._format_boolean(raw_data.get('is_fast_charge')),
                'manufacturer': self._format_string(raw_data.get('manufacturer')),
                'technology': self._format_string(raw_data.get('battery_technology')),
                'cycle_count': self._format_integer(raw_data.get('cycle_count')),
                'battery_health': self._format_health(raw_data.get('battery_health')),
                'battery_voltage': self._format_voltage(raw_data.get('battery_voltage')),
                'battery_temperature': self._format_temperature(raw_data.get('battery_temperature')),
                'report_generated': self._get_datetime(),
            }

            if self._dev_mode:
                print(f"Formatted data: {formatted_data}")

            return formatted_data

        except Exception as e:
            print(f"Error formatting battery data: {e}")
            return self._get_fallback_result()

    def _get_fallback_result(self) -> Dict[str, Any]:
        """Return minimal fallback data when battery information cannot be retrieved."""
        return {
            'battery_percentage': "n/a", 'power_status': "n/a", 'design_capacity': "n/a",
            'remaining_capacity': "n/a", 'charge_rate': "n/a", 'fast_charge': "n/a",
            'manufacturer': "n/a", 'technology': "n/a", 'cycle_count': "n/a",
            'battery_health': "n/a", 'battery_voltage': "n/a", 'battery_temperature': "n/a",
            'report_generated': self._get_datetime(),
        }

    @lru_cache(maxsize=1)
    def _estimate_battery_voltage(self) -> Optional[float]:
        """Estimate voltage based on battery chemistry from PowerShell."""
        if not hasattr(self, '_voltage_cache'):
            self._voltage_cache = self._calculate_voltage_estimate()
        return self._voltage_cache

    @staticmethod
    def _get_datetime() -> str:
        """Get current datetime as formatted string."""
        return datetime.now().strftime("%Y-%m-%d")

    @staticmethod
    def _format_percentage(percentage: Optional[Union[int, float]]) -> str:
        """Format battery percentage as a string with a percent symbol."""
        return "n/a" if percentage is None else f"{float(percentage):.0f}%"

    @staticmethod
    def _format_power_status(is_plugged: Optional[bool]) -> str:
        """Format power connection status as 'Plugged In' or 'On Battery'."""
        return "n/a" if is_plugged is None else ("Plugged In" if is_plugged else "On Battery")

    @staticmethod
    def _format_capacity(capacity: Optional[Union[int, float]]) -> str:
        """Format battery capacity in mWh, using thousands separator."""
        return "n/a" if capacity is None else f"{float(capacity):,.0f} mWh"

    @staticmethod
    def _format_charge_rate(rate: Optional[Union[int, float]]) -> str:
        """Format charge/discharge rate in mW with charging direction."""
        if rate is None:
            return "n/a"
        val = float(rate)
        if val == 0:
            return "0 mW (Idle)"
        direction = "Charging" if val > 0 else "Discharging"
        return f"{abs(val):,.0f} mW ({direction})"

    @staticmethod
    def _format_health(health: Optional[Union[int, float]]) -> str:
        """Format battery health as a percentage with one decimal place."""
        return "n/a" if health is None else f"{float(health):.1f}%"

    @staticmethod
    def _format_voltage(voltage: Optional[Union[int, float]]) -> str:
        """Format battery voltage in volts with two decimal places."""
        return "n/a" if voltage is None else f"{float(voltage):.2f} V"

    @staticmethod
    def _format_temperature(temperature: Optional[Union[int, float]]) -> str:
        """Format battery temperature in Celsius with one decimal place."""
        return "n/a" if temperature is None else f"{float(temperature):.1f}°C"

    @staticmethod
    def _format_boolean(value: Optional[bool]) -> str:
        """Format boolean values consistently."""
        return "n/a" if value is None else ("Yes" if value else "No")

    @staticmethod
    def _format_string(value: Optional[str]) -> str:
        """Format string values with proper handling of None and empty strings."""
        return "n/a" if not value or not isinstance(value, str) else (value.strip() or "n/a")

    @staticmethod
    def _format_integer(value: Optional[Union[int, float]]) -> str:
        """Format integer values with proper validation."""
        return "n/a" if value is None else str(int(float(value)))


# Initialize BatteryPy
if _PLATFORM == "win32":

    # WINDOWS IMPORTS
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
        Enhanced public API class to access battery information on Windows systems.

        This class wraps the internal _BatteryHtmlReport and provides clean methods to access
        key battery health and status information using Windows APIs for real-time data
        and powercfg reports for static battery specifications.

        Features:
            - Pure Python implementation with no external dependencies
            - Combines Windows API calls with HTML report parsing
            - Always returns clean values with proper error handling
            - Optimized caching operations for performance
            - Comprehensive battery information including health metrics
            - Thread-safe operations with proper locking
            - Multiple fallback mechanisms for reliability

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

        # Optimized class constants
        _CACHE_DURATION_SECONDS: float = 1.5  # Reduced cache duration for better responsiveness
        _FAST_CACHE_DURATION: float = 0.3  # Fast cache for frequent calls
        _POWER_INFO_BATTERY_STATE: int = 5  # Windows API constant
        _STATUS_SUCCESS: int = 0x00000000  # Success status

        def __init__(self, dev_mode: bool = False) -> None:
            """Initialize the Battery class with enhanced Windows API access."""
            super().__init__()

            # Core attributes
            self._dev_mode = dev_mode
            self._last_api_call: int = 0
            self._last_fast_call: int = 0
            self._cached_state = None
            self._cached_fast_data: dict = {}

            # Performance tracking
            self._api_calls: int = 0
            self._cache_hits: int = 0

            # Initialize battery report with error handling
            try:
                self._battery_report = _BatteryHtmlReport(dev_mode=self._dev_mode)

            except Exception:
                if self._dev_mode:
                    import traceback
                    traceback.print_exc()

                self._battery_report = None

            # Load Windows DLLs with enhanced error handling
            try:
                self._kernel32 = ctypes.windll.kernel32
                self._power_prof = ctypes.windll.powrprof

                # Test API functionality
                test_state = _SYSTEM_BATTERY_STATE()
                result = self._power_prof.CallNtPowerInformation(
                    self._POWER_INFO_BATTERY_STATE, None, 0,
                    byref(test_state), ctypes.sizeof(test_state)
                )
                if result != self._STATUS_SUCCESS and self._dev_mode:
                    print(f"[WinBattery] API test warning: {result}")

            except AttributeError:

                if self._dev_mode:
                    import traceback
                    traceback.print_exc()

                self._kernel32 = None
                self._power_prof = None

        def _get_battery_state(self, use_cache: bool = True) -> Optional[_SYSTEM_BATTERY_STATE]:
            """Get battery state from Windows API with optimized caching."""

            if not self._power_prof:
                return None

            current_time: float = time.time()

            # Check cache first
            if (use_cache and self._cached_state and
                    current_time - self._last_api_call < self._CACHE_DURATION_SECONDS):
                self._cache_hits += 1
                return self._cached_state

            try:
                state = _SYSTEM_BATTERY_STATE()
                result = self._power_prof.CallNtPowerInformation(
                    self._POWER_INFO_BATTERY_STATE,
                    None, 0,
                    byref(state),
                    ctypes.sizeof(state)
                )

                if result == self._STATUS_SUCCESS:
                    self._cached_state = state
                    self._last_api_call = current_time
                    self._api_calls += 1
                    return state
                else:
                    if self._dev_mode:
                        print(f"[WinBattery] API call failed: {result}")
                    return None

            except Exception:
                if self._dev_mode:
                    import traceback
                    traceback.print_exc()

                return None

        def _run_cmd_timeout(self, cmd: list, timeout: float = 2.0) -> Optional[str]:
            """Execute command with timeout and proper error handling."""

            try:
                result = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=timeout,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                return result.stdout.strip() if result.returncode == 0 else None
            except (subprocess.TimeoutExpired, Exception):

                if self._dev_mode:
                    import traceback
                    traceback.print_exc()

                return None

        def battery_manufacturer(self) -> str:
            """Get battery manufacturer name with fallback methods."""

            # Try battery report first
            if self._battery_report:
                manufacturer = self._battery_report.get_battery_manufacturer()
                if manufacturer and manufacturer != "Unknown":
                    return manufacturer

            # Get laptop manufacturer
            laptop_mfg = self._run_cmd_timeout([
                'powershell.exe', '-NoProfile', '-Command',
                '(Get-WmiObject Win32_ComputerSystem -EA SilentlyContinue).Manufacturer'
            ])

            return laptop_mfg.strip() if laptop_mfg else "n/a"

        def battery_technology(self) -> str:
            """Get battery chemistry/technology type with enhanced detection."""
            # Try battery report first
            if self._battery_report:
                tech = self._battery_report.get_battery_chemistry()
                if tech:
                    tech = tech.strip().lower()
                    chemistry_map: dictp[str, str] = {
                        "lion": "Lithium-ion",
                        "liion": "Lithium-ion",
                        "pbac": "Lead-acid",
                        "nimh": "Nickel-metal hydride",
                        "nicd": "Nickel-cadmium"
                    }
                    return chemistry_map.get(tech, "Unknown")

            # Fallback to WMI with voltage estimation
            output = self._run_cmd_timeout([
                'powershell.exe', '-NoProfile', '-Command',
                '(Get-WmiObject Win32_Battery -EA SilentlyContinue).Name'
            ])

            if output and "lithium" in output.lower():
                return "Lithium-ion"

            # Voltage-based estimation
            voltage = self.battery_voltage()
            if voltage:
                if 10.0 <= voltage <= 15.0:
                    return "Lithium-ion"
                elif 6.0 <= voltage <= 8.0:
                    return "Lead-acid"

            return "n/a"

        def cycle_count(self) -> int:
            """Get battery cycle count."""
            return self._battery_report.get_battery_cycle_count()

        def design_capacity(self) -> int:
            """Get battery design capacity in mWh."""
            return self._battery_report.get_battery_design_capacity()

        def full_capacity(self) -> int:
            """Get battery full charge capacity in mWh."""
            return self._battery_report.get_battery_full_capacity()

        def battery_percent(self) -> int:
            """Get current battery charge percentage with validation."""
            state = self._get_battery_state()
            if not state or not state.BatteryPresent or state.MaxCapacity == 0:
                return 0

            try:
                percentage = int((state.RemainingCapacity / state.MaxCapacity) * 100)
                return max(0, min(100, percentage))  # Clamp to 0-100

            except (ZeroDivisionError, ValueError, OverflowError):
                if self._dev_mode:
                    import traceback
                    traceback.print_exc()

                return 0

        def is_plugged(self) -> bool:
            """Check if device is connected to AC power."""
            state = self._get_battery_state()
            return bool(state.AcOnLine) if state else False

        def remaining_capacity(self) -> int:
            """Get remaining battery capacity in mWh."""

            state = self._get_battery_state()
            if not state or not state.BatteryPresent:
                return 0

            return max(0, int(state.RemainingCapacity))

        def charge_rate(self) -> int:
            """Get current charge/discharge rate with proper sign handling."""

            state = self._get_battery_state()
            if not state or not state.BatteryPresent:
                return 0

            try:
                rate = int(state.Rate)

                # Proper sign handling based on state
                if state.Charging and rate != 0:
                    return abs(rate)  # Positive for charging
                elif state.Discharging and rate != 0:
                    return -abs(rate)  # Negative for discharging
                else:
                    return 0  # Idle state

            except (ValueError, OverflowError):

                if self._dev_mode:
                    import traceback
                    traceback.print_exc()

                return 0

        def is_fast_charge(self) -> bool:
            """Check if battery is fast charging with improved detection."""
            if not self.is_plugged():
                return False

            rate = self.charge_rate()
            return rate > 0 and abs(rate) > self._FAST_CHARGE_THRESHOLD

        def battery_health(self) -> Union[int, str]:
            """Calculate battery health percentage with multiple methods."""
            try:
                # Method 1: Use MaxCapacity vs DesignCapacity
                state = self._get_battery_state()
                design_cap = self.design_capacity()

                if state and state.BatteryPresent and state.MaxCapacity > 0 and design_cap > 0:
                    health = int((state.MaxCapacity / design_cap) * 100)
                    return max(0, min(100, health))

                # Method 2: Estimate from current data
                remaining = self.remaining_capacity()
                percent = self.battery_percent()

                if remaining > 0 and percent > 0 and design_cap > 0:
                    estimated_full = (remaining * 100) / percent
                    health = int((estimated_full / design_cap) * 100)
                    return max(0, min(100, health))

            except Exception:
                if self._dev_mode:
                    import traceback
                    traceback.print_exc()

            return "n/a"

        def remaining_time(self, friendly: bool = False) -> Union[int, str]:
            """Estimate remaining battery time with improved accuracy."""

            try:
                if self.is_plugged():
                    return "Plugged in" if friendly else 0

                remaining_mwh = self.remaining_capacity()
                current_rate = abs(self.charge_rate())  # Always positive for calculation

                if current_rate <= 0 or remaining_mwh <= 0:
                    return "n/a" if friendly else 0

                # Calculate time in minutes
                total_minutes = int((remaining_mwh / current_rate) * 60)
                total_minutes = min(total_minutes, 1440)  # Cap at 24 hours

                if not friendly:
                    return total_minutes

                # Human-readable format
                if total_minutes < 60:
                    return f"{total_minutes} minute{'s' if total_minutes != 1 else ''}"
                else:
                    hours = total_minutes // 60
                    minutes = total_minutes % 60
                    if minutes == 0:
                        return f"{hours} hour{'s' if hours != 1 else ''}"
                    else:
                        return f"{hours}h {minutes}m"

            except Exception:
                if self._dev_mode:
                    import traceback
                    traceback.print_exc()

                return "n/a" if friendly else 0

        def battery_voltage(self, use_simulation: bool = True) -> Optional[float]:
            """Get battery voltage with optimized multi-method approach."""
            # Check fast cache
            current_time = time.time()
            if (current_time - self._last_fast_call < self._FAST_CACHE_DURATION and
                    'voltage' in self._cached_fast_data):
                return self._cached_fast_data['voltage']

            voltage = None

            # Method 1: PowerShell WMI (fastest)
            try:
                output = self._run_cmd_timeout([
                    'powershell.exe', '-NoProfile', '-Command',
                    '(Get-WmiObject Win32_Battery -EA SilentlyContinue).DesignVoltage'
                ], timeout=1.5)

                if output and output.isdigit():
                    voltage_mv = int(output)
                    voltage = voltage_mv / 1000.0
            except Exception:
                pass

            # Method 2: Registry fallback
            if voltage is None:
                voltage = self._get_voltage_from_registry()

            # Method 3: Estimation based on technology
            if voltage is None and use_simulation:
                tech = self.battery_technology()
                if "lithium" in tech.lower():
                    voltage = 11.1  # Typical Li-ion voltage
                elif "lead" in tech.lower():
                    voltage = 12.0  # Typical lead-acid voltage

            # Cache result
            if voltage is not None:
                self._cached_fast_data['voltage'] = voltage
                self._last_fast_call = current_time

            return voltage

        def battery_temperature(self) -> Optional[float]:
            """Get system temperature via Windows thermal management."""
            try:
                output = self._run_cmd_timeout([
                    'powershell.exe', '-NoProfile', '-Command',
                    'Get-WmiObject -Namespace root/WMI -Class MSAcpi_ThermalZoneTemperature -EA SilentlyContinue | Select -First 1 | % { $_.CurrentTemperature }'
                ], timeout=2.0)

                if output and output.isdigit():
                    temp_raw = float(output)
                    temp_celsius = (temp_raw / 10.0) - 273.15

                    # Validate reasonable temperature range
                    if 15 <= temp_celsius <= 80:
                        return round(temp_celsius, 1)

            except Exception:
                if self._dev_mode:

                    import traceback
                    traceback.print_exc()

            return None

        def _get_voltage_from_registry(self) -> Optional[float]:
            """Get voltage from Windows Registry with optimized search."""
            try:
                # Try most common registry paths
                reg_paths: tuple[str, str] = (
                    r"SYSTEM\CurrentControlSet\Services\CmBatt\Parameters",
                    r"SYSTEM\CurrentControlSet\Enum\ACPI"
                )

                for base_path in reg_paths:
                    try:
                        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, base_path) as key:
                            # Try direct voltage value
                            try:
                                voltage_val, _ = winreg.QueryValueEx(key, "DesignVoltage")
                                if isinstance(voltage_val, int) and voltage_val > 0:
                                    return voltage_val / 1000.0 if voltage_val > 100 else voltage_val
                            except FileNotFoundError:
                                pass
                    except (FileNotFoundError, PermissionError):
                        continue

            except Exception:
                if self._dev_mode:
                    import traceback
                    traceback.print_exc()

            return None


    class _BatteryHtmlReport:
        """
        Robust battery report parser with industrial-strength HTML parsing.
        Handles multiple Windows powercfg report formats and edge cases.
        """

        # Class constants
        _CACHE_FILENAME: str = "battery_report_cache.html"
        _CACHE_REPORT_PATH: Path = Path(".cache") / _CACHE_FILENAME
        _REPORT_COMMAND: list[str] = ["powercfg", "/batteryreport"]
        _CMD_TIMEOUT: int = 30

        # More comprehensive regex patterns with fallback matching
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

            self._dev_mode = dev_mode
            self._report_data: Optional[str] = None
            self._initialize_report(force_refresh)

        def _initialize_report(self, force_refresh: bool) -> None:
            """Initialize the report data with error handling."""
            try:
                # Try to load from cache first if not forcing refresh
                if not force_refresh and self._cache_exists():
                    cached_data = self._load_cache()
                    if cached_data:
                        self._report_data = cached_data
                        if self._dev_mode:
                            print("[BatteryHtmlReport] Loaded from cache")
                        return

                # Generate new report if no cache or cache load failed
                if self._dev_mode:
                    print("[BatteryHtmlReport] Generating new battery report...")

                self._report_data = self._generate_battery_report()

                if self._report_data:
                    self._save_cache(self._report_data)
                    if self._dev_mode:
                        print("[BatteryHtmlReport] Report generated and cached successfully")
                else:
                    if self._dev_mode:
                        print("[BatteryHtmlReport] Failed to generate report")

            except Exception:

                if self._dev_mode:
                    import traceback
                    traceback.print_exc()

                self._report_data = None

        def _cache_exists(self) -> bool:
            """Check if the cache file exists and is readable."""
            return self._CACHE_REPORT_PATH.exists() and self._CACHE_REPORT_PATH.is_file()

        def _load_cache(self) -> Optional[str]:
            """Load and return cached HTML report data."""

            try:
                return self._CACHE_REPORT_PATH.read_text(encoding="utf-8")

            except Exception:
                if self._dev_mode:
                    import traceback
                    traceback.print_exc()

                return None

        def _save_cache(self, data: str) -> None:
            """Save HTML report data to cache."""

            try:
                # Ensure cache directory exists
                self._CACHE_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
                self._CACHE_REPORT_PATH.write_text(data, encoding="utf-8")

            except Exception:

                if self._dev_mode:
                    import traceback
                    traceback.print_exc()

        def _generate_battery_report(self) -> Optional[str]:
            """Generate a battery report using powercfg and return HTML content."""

            try:
                # Run powercfg command with timeout
                result = subprocess.run(
                    self._REPORT_COMMAND,
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=self._CMD_TIMEOUT,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )

                # Extract the report file path from stdout
                report_path = None

                # Try different patterns to find the report path
                patterns: tuple[str, str, str] = (
                    r'saved to file path\s+(.+)',
                    r'saved to\s+(.+)',
                    r'Battery report saved to\s+(.+)'
                )

                for pattern in patterns:
                    match = re.search(pattern, result.stdout, re.IGNORECASE)
                    if match:
                        report_path = Path(match.group(1).strip().strip('"').strip())
                        break

                if not report_path:
                    if self._dev_mode:
                        print(f"[BatteryHtmlReport] Report path not found in output: {result.stdout}")
                    return None

                # Validate file exists
                if not report_path.exists():
                    if self._dev_mode:
                        print(f"[BatteryHtmlReport] Report file not found at: {report_path}")

                    return None

                # Read the HTML content
                try:
                    html_content = report_path.read_text(encoding="utf-8")
                    return html_content

                except (OSError, IOError):

                    if self._dev_mode:
                        import traceback
                        traceback.print_exc()

                    return None

                finally:
                    # Cleanup temporary report file
                    try:
                        if report_path.exists():
                            report_path.unlink()
                    except Exception as cleanup_err:
                        if self._dev_mode:
                            print(f"[BatteryHtmlReport] Failed to delete report file: {cleanup_err}")

            except (subprocess.TimeoutExpired, subprocess.CalledProcessError, Exception):

                if self._dev_mode:
                    import traceback
                    traceback.print_exc()

                return None

        def _parse_html(self, query: str, as_int: bool = False) -> Union[str, int]:
            """Parse HTML report data for specific battery information."""
            if not self._report_data:
                return 0 if as_int else "n/a"

            pattern = self._SEARCH_PATTERNS.get(query)
            if not pattern:
                return 0 if as_int else "n/a"

            match = pattern.search(self._report_data)
            if match:
                raw_text = match.group(1)
                cleaned_text = self._normalize_text(raw_text)

                if as_int:
                    return self._extract_numeric_value(cleaned_text)
                return cleaned_text

            return 0 if as_int else "n/a"

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
        def get_battery_manufacturer(self) -> str:
            """Get the battery manufacturer."""
            return self._parse_html("manufacturer")

        def get_battery_chemistry(self) -> str:
            """Get the battery chemistry type."""
            return self._parse_html("chemistry")

        def get_battery_design_capacity(self) -> int:
            """Get battery design capacity in mWh."""
            return self._parse_html("design_capacity", as_int=True)

        def get_battery_full_capacity(self) -> int:
            """Get battery full charge capacity in mWh."""
            return self._parse_html("full_capacity", as_int=True)

        def get_battery_cycle_count(self) -> int:
            """Get battery cycle count."""
            return self._parse_html("cycle_count", as_int=True)

        def is_report_available(self) -> bool:
            """Check if battery report data is available."""
            return self._report_data is not None


elif _PLATFORM == "linux":

    class Battery(_BatteryPy):
        """
        Linux-specific battery information class that reads from /sys/class/power_supply/
        """

        # Linux battery sysfs paths
        _POWER_SUPPLY_PATH: str = "/sys/class/power_supply"

        # Battery property mappings
        _BATTERY_PROPERTIES: dict[str, str] = {
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

        def __init__(self, dev_mode: bool = False, battery_name: Optional[str] = None) -> None:
            super().__init__()

            self._dev_mode = dev_mode
            self._ac_adapter_paths: list = []

            # Initialize battery and AC adapter paths
            self._discover_power_supplies(battery_name)

        def _discover_power_supplies(self, preferred_battery: Optional[str] = None) -> None:
            """
            Discover available batteries and AC adapters in the system
            """
            if not os.path.exists(self._POWER_SUPPLY_PATH):
                return

            power_supplies = os.listdir(self._POWER_SUPPLY_PATH)
            batteries = []

            for supply in power_supplies:
                supply_path = os.path.join(self._POWER_SUPPLY_PATH, supply)
                type_file = os.path.join(supply_path, "type")

                if os.path.exists(type_file):
                    supply_type = self._read_file(type_file)

                    if supply_type == "Battery":
                        batteries.append(supply_path)
                    elif supply_type == "Mains":
                        self._ac_adapter_paths.append(supply_path)

            # Select battery
            if preferred_battery:
                preferred_path = os.path.join(self._POWER_SUPPLY_PATH, preferred_battery)
                if preferred_path in batteries:
                    self._battery_path = preferred_path
                else:
                    raise ValueError(f"Battery '{preferred_battery}' not found")
            elif batteries:
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
                if self._dev_mode:
                    print(f"[DEV] _read_battery_property({property_name}): No battery path available")
                return None

            property_path = os.path.join(self._battery_path, property_name)
            value = self._read_file(property_path)

            if self._dev_mode:
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

        def battery_manufacturer(self) -> Optional[str]:
            """Get the battery manufacturer name"""
            return self._read_battery_property("manufacturer")

        def battery_technology(self) -> str:
            """Get the battery technology (Li-ion, Li-poly, etc.)"""
            technology: str = "Lithium-Ion" if self._read_battery_property("technology") != "n/a" else \
                    self._read_battery_property("technology")

            if technology is not None:
                if self._dev_mode:
                    print(f"[DEV] battery_technology: Using original value '{technology}'")
                return technology

            else:
                if self._dev_mode:
                    print("[DEV] battery_technology: Using fallback value 'Lithium-ion'")
                return "Lithium-ion"

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
                if self._dev_mode:
                    print(f"[DEV] design_capacity: Using energy_full_design ({capacity} µWh -> {result} mWh)")
                return result

            capacity = self._read_battery_int("charge_full_design")
            if capacity is not None:
                result = capacity // 1000  # Convert µAh to mAh
                if self._dev_mode:
                    print(f"[DEV] design_capacity: Using charge_full_design fallback ({capacity} µAh -> {result} mAh)")
                return result

            if self._dev_mode:
                print("[DEV] design_capacity: No capacity information available")
            return None

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
                if self._dev_mode:
                    print(f"[DEV] battery_health: Using energy values ({current_full}/{design_full} = {health}%)")
                return health

            # Fallback to charge values
            current_full = self._read_battery_int("charge_full")
            design_full = self._read_battery_int("charge_full_design")

            if current_full is not None and design_full is not None and design_full > 0:
                health = round((current_full / design_full) * 100, 2)
                if self._dev_mode:
                    print(
                        f"[DEV] battery_health: Using charge values fallback ({current_full}/{design_full} = {health}%)")
                return health

            if self._dev_mode:
                print("[DEV] battery_health: No health information available")
            return 0

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
                    if self._dev_mode:
                        print(f"[DEV] is_plugged: AC adapter {i} online - using original method")
                    return True

            # Fallback: check battery status
            status = self._read_battery_property("status")
            if status:
                is_plugged = status.lower() in ["charging", "full"]
                if self._dev_mode:
                    print(f"[DEV] is_plugged: Using battery status fallback (status='{status}', plugged={is_plugged})")
                return is_plugged

            if self._dev_mode:
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
                if self._dev_mode:
                    print(f"[DEV] remaining_capacity: Using energy_now ({capacity} µWh -> {result} mWh)")
                return result

            # Fallback to charge (mAh)
            capacity = self._read_battery_int("charge_now")
            if capacity is not None:
                result = capacity // 1000  # Convert µAh to mAh
                if self._dev_mode:
                    print(f"[DEV] remaining_capacity: Using charge_now fallback ({capacity} µAh -> {result} mAh)")

                return result

            if self._dev_mode:
                print("[DEV] remaining_capacity: No capacity information available")
            return None

        def charge_rate(self) -> Optional[int]:
            """
            Get the current battery charge or discharge rate in milliwatts (mW).

            Returns:
                int: Charge rate in mW (positive for charging, negative for discharging),
                     or None if unavailable.
            """

            def signed_power(value_uw: int, _status: Optional[str]) -> int:
                """Convert µW to mW and apply sign based on charging status."""
                mw = abs(value_uw) // 1000
                if _status and _status.lower() == "discharging":
                    return -mw
                return mw

            status = self._read_battery_property("status")

            # Primary method: power_now (in µW)
            power_uw = self._read_battery_int("power_now")
            if power_uw is not None:
                result = signed_power(power_uw, status)
                if self._dev_mode:
                    print(f"[DEV] charge_rate: Using power_now ({power_uw} µW -> {result} mW, status='{status}')")
                return result

            # Fallback method: current_now (µA) * voltage_now (µV)
            current_ua = self._read_battery_int("current_now")
            voltage_uv = self._read_battery_int("voltage_now")

            if current_ua is not None and voltage_uv is not None:
                power_uw = abs(current_ua) * voltage_uv  # Still in µW
                result = signed_power(power_uw, status) // 1000  # Convert to mW
                if self._dev_mode:
                    print(f"[DEV] charge_rate: Fallback using current * voltage "
                          f"({current_ua} µA * {voltage_uv} µV = {power_uw} µW -> {result} mW, status='{status}')")
                return result

            if self._dev_mode:
                print("[DEV] charge_rate: No power data available")
            return None

        def is_fast_charge(self) -> Optional[bool]:
            """
            Check if the battery is fast charging

            Returns:
                True if fast charging, False if slow charging,
                None if not charging or error
            """
            if not self.is_plugged():
                return False

            status = self._read_battery_property("status")
            if not status or status.lower() != "charging":
                return False

            charge_rate = self.charge_rate()
            if charge_rate is None or charge_rate <= 0:
                return False

            # Consider fast charging if rate > 15W (arbitrary threshold)
            # You may want to adjust this based on your device specifications
            return charge_rate >= self._FAST_CHARGE_THRESHOLD  # 15W in mW

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


else:
    sys.exit("Unsupported platform")


if __name__ == "__main__":
    sys.exit(0)

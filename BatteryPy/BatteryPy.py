"""
This code or file is part of 'BatteryPy' project
copyright (c) 2023, Aymen Brahim Djelloul, All rights reserved.
use of this source code is governed by MIT License that can be found on the project folder.

@author: Aymen Brahim Djelloul
version: 0.0.1
date: 29.07.2023
License: MIT

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
        BatteryPy uses integrated tools on the operating system it self to gather
        battery and power management information and parse it

    sources :

        // For Windows :
        - https://learn.microsoft.com/en-us/windows-hardware/design/device-experiences/powercfg-command-line-options
        - https://learn.microsoft.com/en-us/windows/win32/cimwin32prov/win32-battery
        - https://devblogs.microsoft.com/scripting/using-windows-powershell-to-determine-if-a-laptop-is-on-battery-power/
        - https://learn.microsoft.com/en-us/windows/win32/power/battery-status-str

"""

# IMPORTS
import sys
import re
import csv
import os
import platform
import subprocess
import datetime
from exceptions import (NotSupportedPlatform, NotSupportedDriver, NotSupportedDeviceType
                        )

# DEFINE GLOBAL VARIABLES
AUTHOR = "Aymen Brahim Djelloul"
VERSION = "0.0.1"

supported_platforms = ("Windows",)


class Battery:

    def __init__(self):

        # CHECK PLATFORM COMPATIBILITY
        _platform = platform.system()

        if _platform not in supported_platforms:
            raise NotSupportedPlatform(_platform)

        # CHECK IF THE 'powercfg' is enabled
        _powercfg_output = subprocess.check_output(["powercfg", "/L"], text=True)

        # CHECK IF THE 'Win32_Battery' CLASS IS SUPPORTED
        _win32_battery_output = subprocess.run(["WMIC", "Path", "Win32_Battery"],
                                               text=True, capture_output=True).stdout.split()

        if "Power" not in _powercfg_output.split():
            raise NotSupportedDriver("powercfg")

        if "BatteryStatus" not in _win32_battery_output:
            raise NotSupportedDriver("Win32_Battery")

        # CLEAR MEMORY
        del _platform, _powercfg_output, _win32_battery_output

        # MAKE A BATTERY REPORT
        _battery_report_output = subprocess.run(["powercfg", "/batteryreport"], capture_output=True).stdout.split()

        # GET THE HTML BATTERY REPORT PATH
        self.__battery_report_path = _battery_report_output[_battery_report_output.index(b'path') + 1] \
            .decode("UTF-8")[:-1]

        # READ THE HTML BATTERY REPORT
        with open(self.__battery_report_path, 'r') as f:
            self.__html_content = self.__parse_html_file(f.read())
            f.close()

        # CHECK THE DEVICE PLATFORM
        if not self.__is_mobile_platform():
            print(self.__battery_report_path)
            os.system(f"del {self.__battery_report_path}")
            raise NotSupportedDeviceType

        # CLEAR MEMORY
        del self.__battery_report_path

    @property
    def manufacturer(self) -> str | None:
        """ This method will return the battery manufacturer"""
        # GET THE BATTERY MANUFACTURER USING THE BATTERY REPORT
        return self.__get_html_text(r'<span class="label">MANUFACTURER</span>', "MANUFACTURER")

    @property
    def chemistry(self) -> str | None:
        """ This method will return the battery chemistry"""
        # GET THE BATTERY CHEMISTRY USING THE BATTERY REPORT
        return self.__get_html_text(r'<span class="label">CHEMISTRY</span>', "CHEMISTRY")

    @property
    def type(self) -> str | None:
        """ This method will return the device battery type"""
        process_output = subprocess.run(["WMIC", "Path", "Win32_Battery", "get", "Caption"],
                                        text=True, capture_output=True).stdout.split()
        # RETURN THE BATTERY TYPE
        return f"{process_output[1]} Battery" if len(process_output) > 0 else None

    @staticmethod
    def get_current_voltage(friendly_output: bool = True) -> str | int | None:
        """ This method will return the battery design voltage"""

        # DEFINE EMPTY VARIABLE
        design_voltage: str | int = -1

        process_output = subprocess.run(["WMIC", "Path", "Win32_Battery", "get", "DesignVoltage"],
                                        text=True, capture_output=True).stdout.split()

        # GET VOLTAGE FORMAT
        if friendly_output:
            design_voltage = f"{int(process_output[1]) / 1000.0:.2f}v"

        elif not friendly_output:
            design_voltage = process_output[1]

        # RETURN THE BATTERY VOLTAGE
        return design_voltage if len(process_output) > 0 else None

    @property
    def battery_percentage(self) -> int | None:
        """ This method will return the current battery percentage"""

        # GET BATTERY STATUS
        process_output = subprocess.run(["WMIC", "Path", "Win32_Battery", "get", "EstimatedChargeRemaining"],
                                        text=True, capture_output=True).stdout.split()

        # RETURN THE BATTERY PERCENTAGE
        return process_output[1] if len(process_output) > 0 else None

    @property
    def battery_health(self) -> int | None:
        """ This method will calculate and return the battery heath percentage"""

        # DEFINE VARIABLES
        design_charge_capacity: int | None = self.__design_battery_capacity()
        full_charge_capacity: int | None = self.__full_battery_capacity()

        if design_charge_capacity and full_charge_capacity is None:
            return None

        # CALCULATE BATTERY HEALTH PERCENTAGE
        battery_health: int = int(full_charge_capacity * 100 / design_charge_capacity)

        # CLEAR MEMORY
        del design_charge_capacity, full_charge_capacity

        return battery_health if battery_health <= 100 else 100

    @property
    def is_plugged(self) -> bool:
        """ This method will tell if the battery is plugged to the power or not"""

        # DEFINE EMPTY PLUGGED VARIABLE
        is_plugged: bool | None

        process_output: int = int(subprocess.run(["WMIC", "Path", "Win32_Battery", "get", "BatteryStatus"],
                                                 text=True, capture_output=True).stdout.split()[1])

        if process_output == 1:
            is_plugged = False

        elif process_output == 2:
            is_plugged = True

        else:
            is_plugged = None

        # CLEAR MEMORY
        del process_output

        return is_plugged

    @property
    def power_management_mode(self) -> tuple | None:
        """ This method will return the current operating system power mode used"""

        # GET THE POWER MANAGEMENT MODE
        power_mode_output = subprocess.run(["powercfg", "/L"], text=True, capture_output=True).stdout.split()

        # Check for None output
        if 'GUID:' not in power_mode_output:
            return None

        power_mode_id: str = power_mode_output[power_mode_output.index('GUID:') + 1]
        power_mode_text: str = power_mode_output[power_mode_output.index('GUID:') + 2]

        # CLEAR MEMORY
        del power_mode_output

        return power_mode_id, power_mode_text.strip('()')

    @property
    def is_fast_charging(self) -> bool | None:
        """ This method will return if the device is fast charged or not"""

        # DEFINE THE MINIMUM FAST CHARGE WATTAGE VALUE SOURCE :
        # https://www.pcworld.com/article/1915376/best-laptop-usb-c-pd-chargers.html#:~:text=Smaller%20laptops%20may
        # %20require%20just,15%2Dinch%20and%20larger%20notebooks.
        fast_charge_wattage: int = 40

        # CONVERT THE CHARGE RATING VALUE FROM MILLI-WATTS-HOURS TO WATTS-HOURS
        charge_rate_watts = self.__milliwatts_to_watts(self.__get_charge_rate())

        # CHECK IF THE BATTERY IS CHARGING
        if charge_rate_watts == 0:
            return None

        return True if charge_rate_watts >= fast_charge_wattage else False

    # @staticmethod
    # def get_estimated_full_charge_time(friendly_format: bool = False) -> int | str | None:
    #     """ This method will calculate the time remaining to full charge the battery in seconds"""

    # @staticmethod
    # def get_estimated_time_remaining(friendly_format: bool = False) -> int | str | None:
    #     """ This method will calculate and return the estimated time for battery duration in seconds"""

    def get_text_report(self, file_path: str = os.getcwd()) -> str:
        """ This method will create a battery report in text file"""

        battery_info_dict: dict = self.get_all_info()

        # FORMAT THE DICTIONARY TO MAKE IT READABLE
        max_key_length: int = max(len(str(key)) for key in battery_info_dict.keys())
        max_value_length: int = max(len(str(value)) for value in battery_info_dict.values())
        formatted_string: str = ""

        with open(f"{file_path}\\BatteryPy-report.txt", 'w') as file:

            for key, value in battery_info_dict.items():
                # REFORMAT THE KEY
                key: str = key.title().replace('_', ' ')

                key_padding: str = " " * (max_key_length - len(str(key)))
                value_padding: str = " " * (max_value_length - len(str(value)))

                formatted_string += f"{str(key)} :{key_padding}     {str(value)}{value_padding}\n"

            # CLEAR MEMORY
            del (key_padding, value_padding, key, value,
                 max_key_length, max_value_length, battery_info_dict)

            for row in formatted_string:
                file.write(row)

            file.close()

        # CLEAR MEMORY
        del row, formatted_string, file

        # RETURN FILE REPORT PATH
        return f"{file_path}\\BatteryPy-report.txt"

    def get_csv_report(self, file_path: str = os.getcwd()):
        """ This method will create a battery report in csv file"""

        battery_info_dict: dict = self.get_all_info()

        with open(f"{file_path}\\BatteryPy-report.csv", 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(["Key", "Value"])  # Write Header row

            for key, value in battery_info_dict.items():
                writer.writerow([key, value])

            file.close()

        # Return the file report path
        return f"{file_path}\\BatteryPy-report.csv"

    def get_all_info(self) -> dict:
        """ This method will return all information that BatteryPy can retrieve"""

        # DEFINE THE INFORMATION DICT
        return {'python_version': platform.python_version(), 'BatteryPy_version': VERSION,
                'battery_manufacturer': self.manufacturer, 'battery_chemistry': self.chemistry,
                'battery_voltage': self.get_current_voltage(False),
                'friendly_battery_voltage': self.get_current_voltage(True),
                'operating_system': platform.system(),
                'battery_type': self.type, 'battery_health': f"{self.battery_health} %",
                'design_capacity': self.__design_battery_capacity(),
                'full_charge_capacity': self.__full_battery_capacity(),
                'report_date': datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")}

    def __design_battery_capacity(self) -> int:
        """ This method will get the design battery capacity in milliwatts-hour"""

        # DEFINE VARIABLES
        design_capacity: str = ""
        extracted_text: str = self.__get_html_text(r'<span class="label">DESIGN CAPACITY</span>')

        for char in extracted_text:
            if char.isdigit():
                design_capacity = design_capacity + char

        # CLEAR MEMORY
        del extracted_text, char
        return int(design_capacity)

    def __full_battery_capacity(self) -> int:
        """ This method will get the full charge battery capacity"""

        # DEFINE VARIABLES
        full_capacity: str = ""
        extracted_text: str = self.__get_html_text(r'<span class="label">FULL CHARGE CAPACITY</span>')

        for char in extracted_text:
            if char.isdigit():
                full_capacity = full_capacity + char

        # CLEAR MEMORY
        del extracted_text, char
        return int(full_capacity)

    @staticmethod
    def __get_charge_rate() -> int | None:
        """ This method will return the battery charge rate when it is charging in milli-watts"""

        # GET THE CHARGE RATE USING THE 'gwmi' tool
        process_output = subprocess.run(["C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe",
                                         "gwmi", "-Class", "batterystatus", "-Namespace", "root\\wmi",
                                         # "|", "Select-Object", "Property", "ChargeRate"
                                         ], capture_output=True, text=True).stdout.split()

        # RETURN THE CURRENT BATTERY CHARGE RATE
        return int(process_output[process_output.index("ChargeRate") + 2]) if "ChargeRate" in process_output else None

    def __is_mobile_platform(self) -> bool:
        """ This method will return the platform role 'Desktop' or 'Mobile'"""

        # DEFINE VARIABLES
        search_pattern: str = r"Mobile"
        html_text_output: str = self.__get_html_text(search_pattern)

        # GET SEARCH PATTERN MATCH
        return True if re.match(search_pattern, html_text_output, re.IGNORECASE) else False

    @staticmethod
    def __milliwatts_to_watts(value: int) -> int:
        """ This method will convert milliwats to watts"""
        return int(value / 1000)

    def __milliwattshour_to_milliamperehour(self, value: int) -> int:
        """ This method will convert milliwatts-hour to milliampere-hour"""
        return int(value / int(self.get_current_voltage(False)))

    def __get_html_text(self, search_pattern: str, info_text: str = "", _chars_count: int = 75) -> str | None:
        """ This method will extract the requested information from the body html parsed content"""

        # DEFINE VARIABLES
        __html_text: str
        search_pattern_index: int = -1

        # GET SEARCH PATTERN MATCH
        search_pattern_match = re.search(search_pattern, self.__html_content, re.IGNORECASE)

        if search_pattern_match:
            search_pattern_index: int = search_pattern_match.start()

        # STORE THE HTML TEXT
        __html_text: str = self.__html_content[search_pattern_index:search_pattern_index + _chars_count]

        # CLEAR MEMORY
        del search_pattern_match

        # CLEAR & NORMALIZE THE HTML TEXT FROM HTML TAG AND RETURN IT
        return self.__html_text_normalization(__html_text, info_text)

    @staticmethod
    def __html_text_normalization(html_text: str, info_text: str = "") -> str:
        """ This method will normalize and clean the extracted html text"""

        # Define the normalized text variable
        normalized_text: str = ""

        # Implement a smple algorithm to detect and remove html tags & attributes
        # from the html text
        inside_tag: bool = False
        inside_single_quote: bool = False
        inside_double_quote: bool = False

        for char in html_text:
            if char == "<" and not inside_tag:
                inside_tag = True
                continue

            elif char == ">" and inside_tag:
                inside_tag = False
                continue

            if inside_tag:
                if char == "'" and not inside_double_quote:
                    inside_single_quote = not inside_single_quote

                elif char == '"' and not inside_single_quote:
                    inside_double_quote = not inside_double_quote

            else:
                normalized_text += char

        # Return the normalized text
        return normalized_text.replace(info_text, "")

    @staticmethod
    def __parse_html_file(html_content: str) -> str:
        """ This method will extract the body section from the html content"""

        # DEFINE EMPTY VARIABLE
        body_tag_index: int = -1
        closing_body_index: int = -1

        body_tag_match = re.search(r"<body>", html_content, re.IGNORECASE)
        if body_tag_match:
            body_tag_index = body_tag_match.start()

        closing_tag_match = re.search(r"</body>", html_content, re.IGNORECASE)

        if closing_tag_match:
            closing_body_index = closing_tag_match.start()

        # RETURN THE EXTRACTED HTML BODY
        return html_content[body_tag_index + 6:closing_body_index] if body_tag_match and closing_tag_match \
            else html_content


if __name__ == "__main__":
    sys.exit()

"""
@author : Aymen Brahim Djelloul.
date : 29.07.2024

This file is for testing BatteryPy which we will get the battery information
"""

# IMPORTS
from BatteryPy.exceptions import *
from BatteryPy.battery_py import Battery, AUTHOR, VERSION, PLATFORM
from time import perf_counter
import os

# Check if the OS to apply color and title changes
if PLATFORM == "Windows":
    # Set terminal window title
    os.system(f"title BatteryPy - {VERSION}")

    # Change colors
    os.system("color F0")

# Print the software header
print(f"\n{' ' * 5}[ BatteryPy - v{VERSION}{' ' * 5}|{' '*5} Developed by {AUTHOR} ]\n\n")


def main():
    """ This function will perform the test of BatteryPy"""

    # Create the Battery object
    battery = Battery()

    # Print out all battery information
    print(f"  Battery manufacturer  :   {battery.manufacturer}\n")
    # Get the Battery manufacturer name

    print(f"  Battery Type          :   {battery.type}\n")
    # Get the battery type (Internal Battery or external)

    print(f"  Battery Chemistry     :   {battery.chemistry}\n")
    # Get the Battery chemistry technology (Lithium-Ion in most cases)

    print(f"  Battery Charge        :   {battery.battery_percentage}%\n")
    # Get the battery percentage (charging level)

    print(f"  Battery Health        :   {battery.battery_health}%\n")
    # Get the battery health or battery maximum capacity in percentage

    print(f"  Is Fast Charge ?      :   {'YES' if battery.is_fast_charging else 'NO'}\n")
    # tells if the battery is fast charging or not

    print(f"  Is Charging ?         :   {'YES' if battery.is_plugged else 'NO'}\n")
    # tells if the battery is plugged to the power source

    print(f"  Battery Voltage       :   {battery.get_current_voltage()}\n")
    # Get the current battery output voltage

    print(f"  Power Mode            :   {battery.power_management_mode(aliased=True)}\n")
    # Get the power management mode is it 'balanced' or 'performance' or 'economy'


if __name__ == "__main__":

    try:
        # Store the start time
        s_time: float = perf_counter()
        main()

        # print the execution duration
        print(f"  [ Finished in : {perf_counter() - s_time:.3f} s ]\n")

    except NotSupportedPlatform:
        print("\n   BatteryPy do not support this OS\n")
    except NotSupportedDeviceType:
        # This will occur when BatteryPy running on PC
        print("\n   BatteryPy do not support Desktop Computer\n")
    except NotSupportedDriver:
        print("\n   BatteryPy can not reach the needed driver to run.\n")

    # remove the report html file
    os.system("del battery-report.html")

    input("  PRESS ENTER TO QUIT .")

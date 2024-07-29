"""
@author : Aymen Brahim Djelloul.
This file is for testing BatteryPy which we will get the battery information
"""

# Import the Battery Object class from BatteryPy module
from BatteryPy.battery_py import Battery, AUTHOR, VERSION
import os


def main():
    """ This function will perform the test of BatteryPy"""

    # Create the Battery object
    battery = Battery()

    # Set terminal window title
    os.system(f"title BatteryPy - {VERSION}")
    # Print the software header
    print(f"\n{' '*10}BatteryPy - v{VERSION}{' '*15} Developed by {AUTHOR}\n\n\n")

    # Print out all battery information
    print(f"Battery manufacturer : {battery.manufacturer}\n")
    # Get the Battery manufacturer namedd

    print(f"Battery Type : {battery.type}\n")
    # Get the battery type (Internal Battery or external)

    print(f"battery Chemistry : {battery.chemistry}\n")
    # Get the Battery chemistry technology (Lithium-Ion in most cases)

    print(f"Battery Charge : {battery.battery_percentage}\n")
    # Get the battery percentage (charging level)

    print(f"Battery Health : {battery.battery_health}\n")
    # Get the battery health or battery maximum capacity in percentage

    print(f"Is Fast Charge ? : {'YES' if battery.is_fast_charging else 'NO'}\n")
    # tells if the battery is fast charging or not

    print(f"Is Charging ? : {'YES' if battery.is_plugged else 'NO'}\n")
    # tells if the battery is plugged to the power source

    print(f"Battery Voltage : {battery.get_current_voltage()}\n")
    # Get the current battery output voltage

    print(f"Power Mode : {battery.power_management_mode}\n")
    # Get the power management mode is it 'balanced' or 'performance' or 'economy'
    input("PRESS ENTER TO QUIT .")


if __name__ == "__main__":
    main()

"""
@author : Aymen Brahim Djelloul.
This file is for testing BatteryPy which we will get the battery informations
"""

# Import the Battery Object class from BatteryPy module
from BatteryPy.BattryPy import Battery

# Create the Battery object 
battery = Battery()

# Print out all battery informations
print(battery.manufacturer)              # Get the Battery manufacturer name
print(battery.type)                      # Get the battery type (Interna Battery or external)
print(battery.chemistry)                 # Get the Battery chemistry technology (Lithuim Ion in most cases)
print(battery.battery_percentage)        # Get the battery percentage (charging level)
print(battery.battery_health)            # Get the battery health or battery maximum capacity in percentage
print(battery.is_fast_charging)          # tells if the battery is fast charging or not
print(battery.is_plugged)                # tells if the battery is plugged to the power source
print(battery.get_current_voltage())     # Get the current battery output voltage
print(battery.power_management_mode)     # Get the power maangement mode is it 'balanced' or 'performance' or 'economy'

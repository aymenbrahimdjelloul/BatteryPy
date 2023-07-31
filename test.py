from BatteryPy import Battery


battery = Battery()

print(battery.manufacturer)
print(battery.type)
print(battery.chemistry)
print(battery.battery_percentage)
print(battery.battery_health)
print(battery.is_fast_charging)
print(battery.is_plugged)
print(battery.get_current_voltage())
print(battery.power_management_mode)

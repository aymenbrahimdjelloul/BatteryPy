"""
@_AUTHOR : Aymen Brahim Djelloul
date : 15.06.2025
License : MIT License

"""

# IMPORTS
import batterypy
from time import perf_counter


def run_performance_test() -> None:
    """ This function will run the performance test"""

    print("\n" + "=" * 60)
    print("PERFORMANCE TESTS")
    print("=" * 60)

    battery = batterypy.Battery(dev_mode=False)
    methods: list[tuple] = [
        ('battery_percent', battery.battery_percent),
        ('battery_health', battery.battery_health),
        ('battery_technology', battery.battery_technology),
        ('cycle_count', battery.cycle_count),
        ('charge_rate', battery.charge_rate),
        ('is_fast_charge', battery.is_fast_charge),
        ('is_plugged', battery.is_plugged),
        ('battery_voltage', battery.battery_voltage),
        ('battery_temperature', battery.battery_temperature),
        ('get_result', battery.get_result),
    ]

    for method_name, method_call in methods:
        times = []
        for _ in range(10):
            start = perf_counter()
            try:
                method_call()
            except Exception as e:
                print(f"{method_name}: ERROR - {e}")
                break
            times.append(perf_counter() - start)

        if times:
            avg_time = sum(times) / len(times)
            print(f"{method_name:20} | Avg: {avg_time:.4f}s | Min: {min(times):.4f}s | Max: {max(times):.4f}s")


if __name__ == "__main__":
    run_performance_test()

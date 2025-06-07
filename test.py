"""
@author : Aymen Brahim Djelloul
date : 06.07.2025
License : MIT License

"""

# IMPORTS
import sys
import batterypy
import unittest
from time import perf_counter


class BatteryPyTestSuite(unittest.TestCase):
    """Comprehensive test suite for batterypy library"""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures before running tests"""
        cls.battery = batterypy.Battery(dev_mode=False)
        print("=" * 60)
        print("BatteryPy Test Suite")
        print("=" * 60)

    def setUp(self):
        self.start_time = perf_counter()

    def tearDown(self):
        elapsed = perf_counter() - self.start_time
        print(f"Test completed in: {elapsed:.4f}s")
        print("-" * 40)

    def _assert_and_print(self, attr_name, value, expected_type=None, extra_checks=None):
        print(f"Testing {attr_name}...")
        print(f"{attr_name}: {value}")
        if expected_type:
            self.assertIsInstance(value, expected_type)
        if extra_checks:
            extra_checks(value)

    def test_battery_percent(self):
        value = self.battery.battery_percent
        self._assert_and_print(
            "battery_percent",
            value,
            (int, float),
            lambda v: (self.assertGreaterEqual(v, 0), self.assertLessEqual(v, 100))
        )

    def test_battery_health(self):
        value = self.battery.battery_health
        self._assert_and_print("battery_health", value)
        self.assertIsNotNone(value)

    def test_battery_technology(self):
        value = self.battery.battery_technology
        self._assert_and_print("battery_technology", value, str)

    def test_cycle_count(self):
        value = self.battery.cycle_count
        self._assert_and_print("cycle_count", value, (int, type(None)))
        if value is not None:
            self.assertGreaterEqual(value, 0)

    def test_charge_rate(self):
        value = self.battery.charge_rate()
        self._assert_and_print("charge_rate", value)
        self.assertIsNotNone(value)

    def test_is_fast_charge(self):
        value = self.battery.is_fast_charge()
        self._assert_and_print("is_fast_charge", value, bool)

    def test_is_plugged(self):
        value = self.battery.is_plugged()
        self._assert_and_print("is_plugged", value, bool)

    def test_battery_voltage(self):
        value = self.battery.battery_voltage()
        self._assert_and_print("battery_voltage", value, (int, float, type(None)))
        if value is not None:
            self.assertGreater(value, 0)

    def test_battery_temperature(self):
        value = self.battery.battery_temperature()
        self._assert_and_print("battery_temperature", value)
        self.assertIsNotNone(value)

    def test_get_result(self):
        value = self.battery.get_result()
        self._assert_and_print("get_result", value)
        self.assertIsNotNone(value)


def run_performance_test() -> None:
    """ This function will run the performance test"""

    print("\n" + "=" * 60)
    print("PERFORMANCE TESTS")
    print("=" * 60)

    battery = batterypy.Battery(dev_mode=False)
    methods: list[tuple] = [
        ('battery_percent', lambda: battery.battery_percent),
        ('battery_health', lambda: battery.battery_health),
        ('battery_technology', lambda: battery.battery_technology),
        ('cycle_count', lambda: battery.cycle_count),
        ('charge_rate', lambda: battery.charge_rate()),
        ('is_fast_charge', lambda: battery.is_fast_charge()),
        ('is_plugged', lambda: battery.is_plugged()),
        ('battery_voltage', lambda: battery.battery_voltage()),
        ('battery_temperature', lambda: battery.battery_temperature()),
        ('get_result', lambda: battery.get_result()),
    ]

    for method_name, method_call in methods:
        times = []
        for _ in range(5):
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


def run_quick_test() -> None:
    """ This function will run quick test"""

    print("\n" + "=" * 60)
    print("QUICK TEST MODE")
    print("=" * 60)

    battery = batterypy.Battery(dev_mode=False)

    tests: list[tuple] = [
        ("Battery Percent", lambda: battery.battery_percent),
        ("Battery Health", lambda: battery.battery_health),
        ("Battery Technology", lambda: battery.battery_technology),
        ("Cycle Count", lambda: battery.cycle_count),
        ("Charge Rate", lambda: battery.charge_rate()),
        ("Fast Charge", lambda: battery.is_fast_charge()),
        ("Is Plugged", lambda: battery.is_plugged()),
        ("Battery Voltage", lambda: battery.battery_voltage()),
        ("Battery Temperature", lambda: battery.battery_temperature()),
        ("Complete Result", lambda: battery.get_result()),
    ]

    total_start = perf_counter()

    for test_name, test_func in tests:
        start = perf_counter()
        try:
            result = test_func()
            print(f"{test_name:20} | {result} | Time: {perf_counter() - start:.4f}s")
        except Exception as e:
            print(f"{test_name:20} | ERROR: {e}")

    print(f"\nTotal execution time: {perf_counter() - total_start:.4f}s")


if __name__ == "__main__":
    # Run all tests by default, ignoring CLI args for simplicity
    run_quick_test()
    run_performance_test()
    unittest.main(argv=[''], exit=False, verbosity=2)

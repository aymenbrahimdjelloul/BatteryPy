
import batterypy
from time import perf_counter

r = batterypy.Battery()

s_time = perf_counter()
print(r.manufacturer)

print(f"Finished in : {perf_counter() - s_time:.4f}")
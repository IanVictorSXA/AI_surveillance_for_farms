from datetime import datetime
import time

now = datetime.now()

later = datetime(9999, 6, 30, 12, 0, 0)
print("Current date and time:", now)
print("Later date and time:", later)
print("Time difference in seconds:", (later - now))
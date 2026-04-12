import os
import time

def cpu_temp():
    return os.popen("sensors | grep 'Core 0' | awk '{print $3}'").read().strip()

def ram_percent():
    return os.popen("free | awk '/^Mem/ {printf \"%.0f%%\\n\", $3/$2*100}'").read().strip()

def net_check():
    result = os.popen("ping -c 1 8.8.8.8 | grep '1 received'").read().strip()
    return "\033[32monline" if result else "\033[31moffline"

while True:
    cputemp = cpu_temp()
    cputemp = float(cputemp.replace("+", "").replace("°C", ""))
    ramps = ram_percent()
    ramps = float(ramps.replace("%", ""))
    if cputemp >= 80:
        print(f"\033[30mCPU TEMP:\033[31m {cputemp} — running hot!\033[0m" , end="  ")
    else:
        print(f"\033[30mCPU TEMP:\033[32m {cputemp} — normal\033[0m", end="  ")
    if ramps >= 80:
        print(f"\033[30mram percent:\033[31m {ramps} - running high!\033[0m", end=" ")
    else:
        print(f"\033[30mram percent:\033[32m {ramps} - ok\033[0m", end=" ")
    print(f"\033[30mnetwork: {net_check()}\033[0m")
    time.sleep(2)
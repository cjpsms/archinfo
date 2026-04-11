import os
import time

def cpu_temp():
    return os.popen("sensors | grep 'Core 0' | awk '{print $3}'").read().strip()

while True:
    temp = cpu_temp()
    temp_num = float(temp.replace("+", "").replace("°C", ""))
    if temp_num >= 80:
        print(f"\033[31mCPU TEMP: {temp} — running hot!\033[0m")
    else:
        print(f"\033[32mCPU TEMP: {temp} — normal\033[0m")
    time.sleep(2)
import subprocess
import time

RED = "\033[31m"
GRN = "\033[32m"
YLW = "\033[33m"
DIM = "\033[2m"
RST = "\033[0m"

def cpu_temp():
    try:
        out = subprocess.check_output(["sensors"], text=True, stderr=subprocess.DEVNULL)
        for line in out.splitlines():
            if "Core 0" in line or "Tctl" in line or "temp1" in line:
                val = line.split()[1].lstrip("+").rstrip("°C")
                return float(val)
    except Exception:
        pass
    return None

def ram_percent():
    try:
        out = subprocess.check_output(["free"], text=True).splitlines()
        for line in out:
            if line.startswith("Mem:"):
                parts = line.split()
                return round(int(parts[2]) / int(parts[1]) * 100)
    except Exception:
        pass
    return None

def net_check():
    try:
        subprocess.check_call(
            ["ping", "-c", "1", "-W", "2", "8.8.8.8"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        return f"{GRN}online{RST}"
    except subprocess.CalledProcessError:
        return f"{RED}offline{RST}"

def color(val, warn, crit):
    if val is None:
        return f"{YLW}N/A{RST}"
    c = RED if val >= crit else YLW if val >= warn else GRN
    return f"{c}{val}{RST}"

while True:
    temp = cpu_temp()
    ram = ram_percent()
    net = net_check()

    temp_str = f"{color(temp, 70, 85)}°C" if temp is not None else f"{YLW}N/A{RST}"
    ram_str  = f"{color(ram,  70, 85)}%"  if ram  is not None else f"{YLW}N/A{RST}"

    print(f"{DIM}cpu:{RST} {temp_str}  {DIM}ram:{RST} {ram_str}  {DIM}net:{RST} {net}")
    time.sleep(2)

#!/usr/bin/env python3
"""archinfo - small live system monitor for Arch Linux.

Reads straight from /proc and /sys, so it needs nothing beyond Python.
"""
import argparse
import os
import platform
import shutil
import socket
import subprocess
import sys
import threading
import time

RED = "\033[31m"
GRN = "\033[32m"
YLW = "\033[33m"
CYN = "\033[36m"
DIM = "\033[2m"
BLD = "\033[1m"
RST = "\033[0m"

BAR_WIDTH = 20
# checked in this order; the first one present wins
CPU_SENSORS = ("coretemp", "k10temp", "zenpower", "cpu_thermal", "acpitz")


def use_color(enabled):
    global RED, GRN, YLW, CYN, DIM, BLD, RST
    if not enabled:
        RED = GRN = YLW = CYN = DIM = BLD = RST = ""


def read(path):
    try:
        with open(path) as f:
            return f.read().strip()
    except OSError:
        return None


# ---------- readers ----------

def cpu_times():
    vals = [int(v) for v in read("/proc/stat").splitlines()[0].split()[1:]]
    idle = vals[3] + vals[4]  # idle + iowait
    return idle, sum(vals)


def cpu_temp():
    base = "/sys/class/hwmon"
    found = {}
    for h in os.listdir(base) if os.path.isdir(base) else []:
        name = read(f"{base}/{h}/name")
        if name in CPU_SENSORS and name not in found:
            found[name] = f"{base}/{h}/temp1_input"
    for name in CPU_SENSORS:
        val = read(found[name]) if name in found else None
        if val:
            return round(int(val) / 1000)
    val = read("/sys/class/thermal/thermal_zone0/temp")
    return round(int(val) / 1000) if val else None


def meminfo():
    info = {}
    for line in (read("/proc/meminfo") or "").splitlines():
        key, val = line.split(":", 1)
        info[key] = int(val.split()[0]) * 1024
    total = info.get("MemTotal", 0)
    used = total - info.get("MemAvailable", 0)
    swap_total = info.get("SwapTotal", 0)
    swap_used = swap_total - info.get("SwapFree", 0)
    return used, total, swap_used, swap_total


def battery():
    base = "/sys/class/power_supply"
    for d in sorted(os.listdir(base)) if os.path.isdir(base) else []:
        if read(f"{base}/{d}/type") == "Battery":
            cap = read(f"{base}/{d}/capacity")
            if cap is not None:
                return int(cap), (read(f"{base}/{d}/status") or "unknown").lower()
    return None


def default_iface():
    for line in (read("/proc/net/route") or "").splitlines()[1:]:
        parts = line.split()
        if parts[1] == "00000000":
            return parts[0]
    return None


def net_bytes(iface):
    rx = read(f"/sys/class/net/{iface}/statistics/rx_bytes")
    tx = read(f"/sys/class/net/{iface}/statistics/tx_bytes")
    return (int(rx), int(tx)) if rx and tx else None


def uptime():
    secs = int(float(read("/proc/uptime").split()[0]))
    d, rem = divmod(secs, 86400)
    h, m = divmod(rem // 60, 60)
    return f"{d}d {h}h {m}m" if d else f"{h}h {m}m"


def is_online():
    try:
        socket.create_connection(("1.1.1.1", 53), timeout=2).close()
        return True
    except OSError:
        return False


def pending_updates():
    """checkupdates (pacman-contrib) syncs a throwaway db, so it's live.
    Plain `pacman -Qu` only knows what the last `pacman -Sy` saw."""
    if shutil.which("checkupdates"):
        cmd, stale = ["checkupdates"], False
    elif shutil.which("pacman"):
        cmd, stale = ["pacman", "-Qu"], True
    else:
        return None
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except (subprocess.TimeoutExpired, OSError):
        return None
    # checkupdates exits 2 and pacman -Qu exits 1 when nothing is outdated
    if r.returncode not in (0, 1, 2):
        return None
    return len([l for l in r.stdout.splitlines() if l.strip()]), stale


class Background:
    """Runs a slow check on a timer so it never stalls the redraw."""

    def __init__(self, fn, every):
        self.value, self.done = None, False
        self._fn, self._every = fn, every
        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        while True:
            self.value = self._fn()
            self.done = True
            time.sleep(self._every)


# ---------- formatting ----------

def level(val, warn, crit):
    return RED if val >= crit else YLW if val >= warn else GRN


def bar(pct, color):
    filled = round(pct / 100 * BAR_WIDTH)
    return f"{color}{'█' * filled}{DIM}{'░' * (BAR_WIDTH - filled)}{RST}"


def gauge(pct, color):
    return f"{color}{pct:3d}%{RST} {bar(pct, color)}"


def gib(n):
    return f"{n / 1024**3:.1f}"


def rate(bps):
    for unit in ("B", "KB", "MB"):
        if bps < 1024:
            return f"{bps:.0f} {unit}/s" if unit == "B" else f"{bps:.1f} {unit}/s"
        bps /= 1024
    return f"{bps:.1f} GB/s"


def label(name):
    return f"{DIM}{name:<5}{RST}"


def na():
    return f"{YLW}N/A{RST}"


def render(cpu_pct, iface, net_rate, online, updates):
    lines = [f"{BLD}{CYN}archinfo{RST}  {platform.node()}  {DIM}·{RST}  "
             f"{platform.release()}  {DIM}· up{RST} {uptime()}"]

    temp = cpu_temp()
    temp_s = f"{level(temp, 70, 85)}{temp}°C{RST}" if temp is not None else na()
    cpu = gauge(cpu_pct, level(cpu_pct, 70, 90)) if cpu_pct is not None else na()
    lines.append(f"{label('cpu')}{cpu}  {temp_s}")

    used, total, s_used, s_total = meminfo()
    if total:
        p = round(used / total * 100)
        swap = f"   {DIM}swap{RST} {round(s_used / s_total * 100)}%" if s_total else ""
        lines.append(f"{label('ram')}{gauge(p, level(p, 70, 85))}  "
                     f"{gib(used)}/{gib(total)} GiB{swap}")
    else:
        lines.append(f"{label('ram')}{na()}")

    du = shutil.disk_usage("/")
    p = round(du.used / du.total * 100)
    lines.append(f"{label('disk')}{gauge(p, level(p, 80, 90))}  "
                 f"{gib(du.used)}/{gib(du.total)} GiB  {DIM}/{RST}")

    bat = battery()
    if bat:
        cap, status = bat
        # low is the bad direction here
        c = RED if cap <= 15 else YLW if cap <= 30 else GRN
        lines.append(f"{label('bat')}{gauge(cap, c)}  {DIM}{status}{RST}")

    if online is None:
        conn = f"{DIM}checking…{RST}"
    else:
        conn = f"{GRN}online{RST}" if online else f"{RED}offline{RST}"
    net = f"{label('net')}{conn}"
    if iface:
        net += f"  {DIM}{iface}{RST}"
        if net_rate:
            net += f"  ↓ {rate(net_rate[0])}  ↑ {rate(net_rate[1])}"
    lines.append(net)

    if updates is not None:
        if not updates.done:
            pkg = f"{DIM}checking…{RST}"
        elif updates.value is None:
            pkg = na()
        else:
            n, stale = updates.value
            c = GRN if n == 0 else YLW if n < 50 else RED
            pkg = f"{c}{n}{RST} update{'' if n == 1 else 's'} pending"
            if stale:
                pkg += f"  {DIM}(as of last pacman -Sy — install pacman-contrib for live){RST}"
        lines.append(f"{label('pkg')}{pkg}")

    return lines


def main():
    ap = argparse.ArgumentParser(description="Small live system monitor for Arch Linux.")
    ap.add_argument("-i", "--interval", type=float, default=2, help="refresh seconds (default 2)")
    ap.add_argument("--once", action="store_true", help="print one snapshot and exit")
    ap.add_argument("--no-color", action="store_true", help="plain output (also honours NO_COLOR)")
    ap.add_argument("--no-updates", action="store_true", help="skip the pacman update check")
    args = ap.parse_args()

    tty = sys.stdout.isatty()
    use_color(tty and not args.no_color and "NO_COLOR" not in os.environ)
    live = tty and not args.once

    online = Background(is_online, 15)
    updates = Background(pending_updates, 1800) if live and not args.no_updates else None

    iface = default_iface()
    prev_cpu = cpu_times()
    prev_net = net_bytes(iface) if iface else None
    prev_t = time.monotonic()

    if not live:
        # take one short sample so cpu % and net speed mean something,
        # and give the online check a moment to answer
        time.sleep(0.5)
        deadline = time.monotonic() + 2.5
        while not online.done and time.monotonic() < deadline:
            time.sleep(0.05)

    drawn = 0
    if live:
        sys.stdout.write("\033[?25l")  # hide cursor
    try:
        while True:
            now = time.monotonic()
            dt = max(now - prev_t, 1e-6)

            idle, total = cpu_times()
            d_total = total - prev_cpu[1]
            cpu_pct = round(100 * (1 - (idle - prev_cpu[0]) / d_total)) if d_total else None
            prev_cpu = (idle, total)

            cur_iface = default_iface()
            if cur_iface != iface:  # switched wifi/ethernet: restart the rate
                iface, prev_net = cur_iface, None
            cur_net = net_bytes(iface) if iface else None
            net_rate = None
            if cur_net and prev_net:
                net_rate = ((cur_net[0] - prev_net[0]) / dt, (cur_net[1] - prev_net[1]) / dt)
            prev_net, prev_t = cur_net, now

            lines = render(cpu_pct, iface, net_rate, online.value, updates)

            if not live:
                print("\n".join(lines))
                break
            if drawn:
                sys.stdout.write(f"\033[{drawn}F")  # back to the top of our block
            sys.stdout.write("".join(f"{l}\033[K\n" for l in lines))
            if drawn > len(lines):  # e.g. battery unplugged: wipe leftovers
                sys.stdout.write("\033[J")
            sys.stdout.flush()
            drawn = len(lines)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        pass
    finally:
        if live:
            sys.stdout.write("\033[?25h")
            sys.stdout.flush()


if __name__ == "__main__":
    main()

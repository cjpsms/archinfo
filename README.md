# archinfo

A small live system monitor for Arch Linux that stays in one place in your
terminal instead of scrolling. It reads straight from `/proc` and `/sys`, so the
only thing it needs is Python 3.

```
archinfo  archlinux  ·  7.2.6-arch2-1  · up 3h 5m
cpu   15% ███░░░░░░░░░░░░░░░░░  47°C
ram   30% ██████░░░░░░░░░░░░░░  4.5/15.2 GiB   swap 0%
disk  75% ███████████████░░░░░  93.4/125.0 GiB  /
bat  100% ████████████████████  full
net  online  wlan0  ↓ 13.6 KB/s  ↑ 17.1 KB/s
pkg   12 updates pending
```

## Install

```bash
git clone https://github.com/cjpsms/archinfo && cd archinfo
./install.sh            # symlinks ~/.local/bin/archinfo
sudo pacman -S pacman-contrib   # optional: live update count
```

## Usage

```bash
archinfo                # live dashboard, redraws every 2s, Ctrl+C to quit
archinfo -i 1           # refresh every second
archinfo --once         # print one snapshot and exit (also when piped)
archinfo --no-updates   # skip the pacman check
archinfo --no-color     # plain text (NO_COLOR is honoured too)
```

## What it shows

- **cpu**: usage % (from `/proc/stat`) and temperature (hwmon `coretemp`,
  `k10temp`, `zenpower`, `cpu_thermal`, or `acpitz`)
- **ram**: used/total and swap
- **disk**: usage of `/`
- **bat**: charge and status. Only shown on machines with a battery.
- **net**: online/offline (TCP check every 15s), default interface, live ↓/↑ speed.
  Follows you when you switch between Wi-Fi and Ethernet.
- **pkg**: pending pacman updates, checked every 30 min in the background.
  It uses `checkupdates` when available; otherwise it falls back to
  `pacman -Qu`, which only knows what your last `pacman -Sy` saw.

Colors go green → yellow → red as each value gets worse. Anything that can't be
read shows `N/A` instead of crashing.

Linux only.

## License

0BSD

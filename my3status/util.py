import io
import time
from socket import AF_INET

import psutil

colors = {
    "red": "#ff0000",
    "green": "#00ff00",
    "blue": "#0000ff",
    "yellow": "#ffff00",
    "white": "#ffffff"
}

def bytes_str(num):
    i = 0
    suffix = ["B", "K", "M", "G", "T"]
    while num >= 1000 and i < len(suffix):
        num /= 1024
        i += 1
    return "{0:.1f}{1}".format(num, suffix[i])

def bytes_str_s(num):
    return bytes_str(num) + "/s"

def read_file_line(path):
    with io.open(path, "rb") as file:
        return file.read().decode("utf-8").rstrip('\n')

def get_bat_stat(bat):
    path = "/sys/class/power_supply/{0}/".format(bat)
    cap = int(read_file_line(path + "capacity"))

    status = read_file_line(path + "status")
    abr = {
        "Full": "FULL",
        "Charging": "CHR",
        "Discharging": "DIS",
        #"Unknown": "UNK"
    }
    status = abr[status] if status in abr else None

    # this will break if any of these files are missing
    def read_int(filename):
        return int(read_file_line(path + filename))

    voltage = read_int("voltage_now") / 1000
    def read_mah(filename):
        return read_int(filename) / voltage

    energy_now = read_mah("energy_now")
    energy_full = read_mah("energy_full")
    power_now = read_mah("power_now")

    seconds = 0
    if power_now > 0:
        if status == "CHR":
            seconds = 3600 * (energy_full - energy_now) / power_now
        elif status in ["DIS", "FULL"]:
            seconds = 3600 * energy_now / power_now

    return (cap, status, seconds)

def get_bat_format(bat):
    value = "{0}%".format(bat[0])
    if bat[1]:
        value += " {0}".format(bat[1])
    if bat[2] != 0:
        value += time.strftime(" (%H:%M)", time.gmtime(bat[2]))
    color = colors["white"]
    if bat[0] > 5:
        if bat[0] <= 20:
            color = colors["red"]
        elif bat[0] <= 50:
            color = colors["yellow"]
        elif bat[0] <= 95:
            color = colors["green"]
    return pango_color(value, color)

# todo: rewrite this whole mess
def get_nics():
    nics = {}

    stats = psutil.net_if_stats()
    for nic in stats:
        if nic in ["lo", "sit0"] or not stats[nic].isup:
            continue
        nics[nic] = {}

    addrs = psutil.net_if_addrs()
    for nic, values in addrs.items():
        if not nic in nics:
            continue
        addr = None
        for value in values:
            if value.family == AF_INET:
                addr = value.address
        if not addr:
            del nics[nic]
            continue
        nics[nic]["addr"] = values[0].address

    return nics

# todo: construct these xml elements with beautifulsoup instead of this mess
def pango_color(s, color):
    return "<span fgcolor=\"{0}\">{1}</span>".format(color, s)

def pango_weight(s, weight):
    return "<span font_weight=\"{0}\">{1}</span>".format(weight, s)

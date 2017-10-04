import io
from socket import AF_INET

import psutil

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

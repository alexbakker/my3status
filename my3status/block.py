from subprocess import check_output
import time

import psutil

import my3status.util as util

_colors = {
    "red": "#ff0000",
    "green": "#00ff00",
    "blue": "#0000ff",
    "white": "#ffffff"
}

class Block:
    def __init__(self, label=None, markup=False, separator=True, align="left"):
        self._label = label
        self._value = None
        self._markup = "pango" if markup else "none"
        self._separator = separator
        self._align = align

    def has_id(self, instance):
        return str(id(self)) == instance

    def update(self):
        pass

    def get_color(self):
        return _colors["white"]

    def get_value(self):
        return str(self._value)

    def get_text(self, width=False):
        text = self.get_width() if width else self.get_value()
        if not text:
            return None
        if not self._label:
            return " {0} ".format(text)
        return " {0} {1} ".format(self._label, text)

    def get_width(self):
        return None

    def get_json(self):
        res = {
            "instance": str(id(self)),
            "full_text": self.get_text(),
            "color": self.get_color(),
            "markup": self._markup,
            "separator": self._separator,
            "align": self._align
        }

        width = self.get_text(width=True)
        if width:
            res["min_width"] = width

        return res

    def on_click(self, event):
        self.update()
        return True

class CPUBlock(Block):
    def __init__(self, **kwargs):
        super().__init__("CPU", **kwargs)
        self._fmt = "{0:.2f}%"

    def update(self):
        percents = psutil.cpu_percent(percpu=True)
        self._value = sum(percents) / len(percents)

    def get_width(self):
        return self._fmt.format(100)

    def get_value(self):
        return self._fmt.format(self._value)

class DiskBlock(Block):
    def __init__(self, label, path, **kwargs):
        super().__init__(label, **kwargs)
        self._path = path

    def update(self):
        disk = psutil.disk_usage(self._path)
        self._value = disk.free

    def get_value(self):
        return util.bytes_str(self._value)

class MemBlock(Block):
    def __init__(self, **kwargs):
        super().__init__("MEM", **kwargs)

    def update(self):
        mem = psutil.virtual_memory()
        self._value = mem.available

    def get_value(self):
        return util.bytes_str(self._value)

class SwapBlock(Block):
    def __init__(self, **kwargs):
        super().__init__("SWAP", **kwargs)

    def update(self):
        swap = psutil.swap_memory()
        self._value = swap.free

    def get_value(self):
        return util.bytes_str(self._value)

class NetBlock(Block):
    def __init__(self, **kwargs):
        super().__init__("NET", markup=True, **kwargs)

    def update(self):
        self._value = None
        nics = util.get_nics()
        for nic, values in nics.items():
            self._value = (nic.upper(), values["addr"])

    def get_value(self):
        if not self._value:
            return util.pango_color(" OFFLINE", _colors["red"])
        return "({0}) {1}".format(self._value[0], util.pango_color(self._value[1], _colors["green"]))

class NetIOBlock(Block):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._value = (0, 0)
        self._tx, self._rx = 0, 0
        self._time = 0
        self._fmt = "{0}   {1}"

    # todo: reset self._tx and self._rx to zero when swithing interfaces
    def update(self):
        t = self._time
        self._time = time.time()
        delta = self._time - t

        nics = util.get_nics()
        net = psutil.net_io_counters(pernic=True)

        tx, rx = self._tx, self._rx
        self._tx, self._rx = 0, 0
        for nic in nics:
            if nic in net:
                self._tx += net[nic].bytes_sent
                self._rx += net[nic].bytes_recv

        if self._tx != 0 and self._rx != 0:
            self._value = ((self._tx - tx) * (1 / delta), (self._rx - rx) * (1 / delta))
        else:
            self._value = (0, 0)

    def get_width(self):
        return self._fmt.format(util.bytes_str_s(100), util.bytes_str_s(100))

    def get_value(self):
        return self._fmt.format(util.bytes_str_s(self._value[0]), util.bytes_str_s(self._value[1]))

class BatteryBlock(Block):
    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)

    def update(self):
        path = "/sys/class/power_supply/{0}/".format(self._label)
        cap = util.read_file_line(path + "capacity")
        self._value = "{0}%".format(cap)

        status = util.read_file_line(path + "status")
        abr = {
            "Full": "FULL",
            "Charging": "CHR",
            "Discharging": "DIS",
            #"Unknown": "UNK"
        }
        if status in abr:
            status = abr[status]
            self._value += " {0}".format(status)

        # this will break if any of these files are missing
        def read_int(filename):
            return int(util.read_file_line(path + filename))

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
            elif status == "DIS":
                seconds = 3600 * energy_now / power_now

        if seconds != 0:
            self._value += time.strftime(" (%H:%M)", time.gmtime(seconds))

    def get_value(self):
        return self._value

class DateTimeBlock(Block):
    def __init__(self, fmt="%a %d-%m-%Y %H:%M:%S", **kwargs):
        super().__init__(markup=True, **kwargs)
        self._fmt = fmt

    def update(self):
        stamp = time.strftime(self._fmt, time.localtime())
        self._value = util.pango_weight(stamp, "bold")

class SensorBlock(Block):
    def __init__(self, dev, name, **kwargs):
        super().__init__(**kwargs)
        self._dev = dev
        self._name = name

    def update(self):
        self._value = ""

        temps = psutil.sensors_temperatures()
        if not self._dev in temps:
            return

        for temp in temps[self._dev]:
            if temp.label == self._name:
                self._value = temp.current
                break

    def get_value(self):
        return "{0:.1f}°C".format(self._value)

class ScriptBlock(Block):
    def __init__(self, args, **kwargs):
        super().__init__(**kwargs)
        self._args = args

    def get_value(self):
        return check_output(self._args).decode("utf-8").rstrip('\n')

class KeymapBlock(Block):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
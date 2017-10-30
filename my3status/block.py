import subprocess
import time

import psutil

import my3status.util as util

_colors = {
    "red": "#ff0000",
    "green": "#00ff00",
    "blue": "#0000ff",
    "yellow": "#ffff00",
    "white": "#ffffff"
}

have_requests = False
try:
    import requests
    have_requests = True
except:
    pass

have_pulsectl = False
try:
    import pulsectl
    have_pulsectl = True
except:
    pass

class Block:
    def __init__(self, label=None, interval=1, markup=False, separator=True, align="left"):
        self._label = label
        # todo: allow setting interval -1 to make updates manual-only
        self.interval = interval
        self._last_update = 0
        self._value = None
        self._markup = "pango" if markup else "none"
        self._separator = separator
        self._align = align
        self.set_button_map({
            1: self.on_button_left,
            2: self.on_button_middle,
            3: self.on_button_right,
            4: self.on_button_wheel_up,
            5: self.on_button_wheel_down,
            6: self.on_button_wheel_left,
            7: self.on_button_wheel_right,
            8: self.on_button_thumb1,
            9: self.on_button_thumb2,
            10: self.on_button_ext1,
            11: self.on_button_ext2
        })

    def has_id(self, instance):
        return str(id(self)) == instance

    def needs_update(self):
        return time.time() - self._last_update >= self.interval

    def update(self):
        return False

    def get_color(self):
        return _colors["white"]

    def is_urgent(self):
        return False

    def get_value(self):
        return str(self._value)

    def set_value(self, value):
        changed = self._value != value
        self._value = value
        self._last_update = time.time()
        return changed

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
            "urgent": self.is_urgent(),
            "markup": self._markup,
            "separator": self._separator,
            "align": self._align
        }

        width = self.get_text(width=True)
        if width:
            res["min_width"] = width

        return res

    def set_button_map(self, button_map):
        self._button_map = button_map

    def on_button(self, event):
        if self._button_map is None:
            return False
        i = event["button"]
        if not i in self._button_map:
            return self.on_button_unknown(event)
        return self._button_map[i](event)

    def on_button_left(self, event):
        return self.update()

    def on_button_middle(self, event):
        return self.update()

    def on_button_right(self, event):
        return self.update()

    def on_button_wheel_up(self, event):
        return self.update()

    def on_button_wheel_down(self, event):
        return self.update()

    def on_button_wheel_left(self, event):
        return self.update()

    def on_button_wheel_right(self, event):
        return self.update()

    def on_button_thumb1(self, event):
        return self.update()

    def on_button_thumb2(self, event):
        return self.update()

    def on_button_ext1(self, event):
        return self.update()

    def on_button_ext2(self, event):
        return self.update()

    def on_button_unknown(self, event):
        return self.update()

class CPUBlock(Block):
    def __init__(self, **kwargs):
        super().__init__("CPU", **kwargs)
        self._fmt = "{0:.2f}%"

    def update(self):
        percents = psutil.cpu_percent(percpu=True)
        return self.set_value(sum(percents) / len(percents))

    def is_urgent(self):
        return self._value >= 95

    def get_color(self):
        if self._value >= 50 and self._value < 95:
            return _colors["yellow"]
        return _colors["white"]

    def get_width(self):
        return self._fmt.format(100)

    def get_value(self):
        return self._fmt.format(self._value)

class DiskBlock(Block):
    def __init__(self, label, path, interval=5, **kwargs):
        super().__init__(label, interval=interval, **kwargs)
        self._path = path

    def update(self):
        disk = psutil.disk_usage(self._path)
        return self.set_value(disk.free)

    def get_value(self):
        return util.bytes_str(self._value)

class MemBlock(Block):
    def __init__(self, interval=5, **kwargs):
        super().__init__("MEM", interval=interval, **kwargs)

    def update(self):
        mem = psutil.virtual_memory()
        return self.set_value(mem.available)

    def get_value(self):
        return util.bytes_str(self._value)

class SwapBlock(Block):
    def __init__(self, interval=5, **kwargs):
        super().__init__("SWAP", interval=interval, **kwargs)

    def update(self):
        swap = psutil.swap_memory()
        return self.set_value(swap.free)

    def get_value(self):
        return util.bytes_str(self._value)

class NetBlock(Block):
    def __init__(self, interval=2, **kwargs):
        super().__init__("NET", interval=interval, markup=True, **kwargs)

    def update(self):
        value = None
        nics = util.get_nics()
        for nic, values in nics.items():
            value = (nic.upper(), values["addr"])
            break
        return self.set_value(value)

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

    # todo: reset self._tx and self._rx to zero when switching interfaces
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

        if self._tx == 0 or self._rx == 0:
            return self.set_value((0, 0))

        return self.set_value(((self._tx - tx) * (1 / delta), (self._rx - rx) * (1 / delta)))

    def get_width(self):
        return self._fmt.format(util.bytes_str_s(100), util.bytes_str_s(100))

    def get_value(self):
        return self._fmt.format(util.bytes_str_s(self._value[0]), util.bytes_str_s(self._value[1]))

class BatteryBlock(Block):
    def __init__(self, name, interval=2, **kwargs):
        super().__init__(name, interval=interval, **kwargs)
        self._value = (0, None, 0)

    def update(self):
        path = "/sys/class/power_supply/{0}/".format(self._label)
        cap = util.read_file_line(path + "capacity")

        status = util.read_file_line(path + "status")
        abr = {
            "Full": "FULL",
            "Charging": "CHR",
            "Discharging": "DIS",
            #"Unknown": "UNK"
        }
        status = abr[status] if status in abr else None

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

        return self.set_value((cap, status, seconds))

    def get_value(self):
        value = "{0}%".format(self._value[0])
        if self._value[1]:
            value += " {0}".format(self._value[1])
        if self._value[2] != 0:
            value += time.strftime(" (%H:%M)", time.gmtime(self._value[2]))
        return value

class DateTimeBlock(Block):
    def __init__(self, fmt="%a %d-%m-%Y %H:%M:%S", **kwargs):
        super().__init__(markup=True, **kwargs)
        self._fmt = fmt

    def update(self):
        return self.set_value(time.localtime())

    def get_value(self):
        stamp = time.strftime(self._fmt, self._value)
        return util.pango_weight(stamp, "bold")

class SensorBlock(Block):
    def __init__(self, dev, name="", interval=5, **kwargs):
        super().__init__(interval=interval, **kwargs)
        self._dev = dev
        self._name = name

    def update(self):
        value = -1
        temps = psutil.sensors_temperatures()
        if self._dev in temps:
            for temp in temps[self._dev]:
                if temp.label == self._name:
                    value = temp.current
                    break
        return self.set_value(value)

    def get_value(self):
        return "{0:.1f}°C".format(self._value)

class ScriptBlock(Block):
    def __init__(self, args, **kwargs):
        super().__init__(**kwargs)
        self._args = args

    def update(self):
        value = subprocess.check_output(self._args).decode("utf-8").rstrip('\n')
        return self.set_value(value)

if have_pulsectl:
    class VolumeBlock(Block):
        def __init__(self, step=0.05, exe="pavucontrol", **kwargs):
            super().__init__("VOL", **kwargs)
            self._step = step
            self._exe = exe
            self._pulse = pulsectl.Pulse("my3status-volume")

        def _get_sink(self):
            name = self._pulse.server_info().default_sink_name
            return self._pulse.get_sink_by_name(name)

        def _change_vol(self, change):
            sink = self._get_sink()
            volume = self._pulse.volume_get_all_chans(sink) + change
            if volume < 0.0:
                volume = 0.0
            elif volume > 1.0:
                volume = 1.0
            self._pulse.volume_set_all_chans(sink, volume)
            return self.update()

        def on_button_left(self, event):
            subprocess.Popen([self._exe])
            return False

        def on_button_wheel_up(self, event):
            return self._change_vol(self._step)

        def on_button_wheel_down(self, event):
            return self._change_vol(-self._step)

        def update(self):
            sink = self._get_sink()
            volume = self._pulse.volume_get_all_chans(sink)
            return self.set_value((int(volume * 100), bool(sink.mute)))

        def get_value(self):
            if self._value[1]:
                return "MUTE"
            else:
                return "{0}%".format(self._value[0])

if have_requests:
    class PoloniexTickerBlock(Block):
        def __init__(self, market, interval=30, **kwargs):
            self._market = market.split("_")
            super().__init__(self._market[1], interval=interval, markup=True, **kwargs)

        def update(self):
            try:
                data = requests.get("https://poloniex.com/public?command=returnTicker").json()
                value = float(data["_".join(self._market)]["highestBid"])
            except:
                return self.set_value(None)
            return self.set_value((value if self._value is None else self._value[0], value))

        def get_value(self):
            if not self._value:
                return util.pango_color("ERROR", _colors["red"])
            if self._value[0] > self._value[1]:
                arrow = "↓"
                color = _colors["red"]
            elif self._value[0] < self._value[1]:
                arrow = "↑"
                color = _colors["green"]
            else:
                arrow = ""
                color = _colors["white"]
            return util.pango_color("{0}{1:.2f} {2}".format(arrow, self._value[1], self._market[0]), color)

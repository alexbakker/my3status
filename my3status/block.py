import asyncio
import subprocess
import time
import threading
import async_timeout

import psutil
import my3status.util as util

have_aiohttp = False
try:
    import aiohttp
    have_aiohttp = True
except:
    pass

have_pulsectl = False
try:
    import pulsectl
    have_pulsectl = True
except:
    pass

class Block:
    def __init__(self, label=None, label_weight="bold", interval=1, markup=False, separator=True, align="left"):
        self._label = label
        self._label_weight = label_weight
        # todo: allow setting interval -1 to make updates manual-only
        self.interval = interval
        self._last_update = 0
        self._lock = threading.Lock()
        self._value = None
        self._markup = "pango" if markup or (self._label_weight is not None and label is not None) else "none"
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

    def has_value(self):
        return self._value is not None

    def get_color(self):
        return util.colors["white"]

    def is_urgent(self):
        return False

    def get_value(self):
        return str(self._value)

    def needs_update(self):
        return not self._lock.locked() and time.time() - self._last_update >= self.interval

    async def do_update(self):
        if self._lock.acquire(False):
            try:
                return await asyncio.coroutine(self.update)()
            finally:
                self._lock.release()
        return False

    def update(self):
        return self.set_value(None)

    def set_value(self, value):
        changed = self._value != value
        self._value = value
        self._last_update = time.time()
        return changed

    def get_text(self, width=False):
        text = self.get_width() if width else self.get_value()
        if not text:
            return None
        if self._label is None:
            return " {0} ".format(text)
        label = self._label
        if self._label_weight is not None:
            label = util.pango_weight(label, self._label_weight)
        return " {0} {1} ".format(label, text)

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

    async def on_button(self, event):
        if self._button_map is None:
            return False
        i = event["button"]
        if not i in self._button_map:
            return await asyncio.coroutine(self.on_button_unknown)(event)
        return await asyncio.coroutine(self._button_map[i])(event)

    async def on_button_left(self, event):
        return await self.do_update()

    async def on_button_middle(self, event):
        return await self.do_update()

    async def on_button_right(self, event):
        return await self.do_update()

    async def on_button_wheel_up(self, event):
        return await self.do_update()

    async def on_button_wheel_down(self, event):
        return await self.do_update()

    async def on_button_wheel_left(self, event):
        return await self.do_update()

    async def on_button_wheel_right(self, event):
        return await self.do_update()

    async def on_button_thumb1(self, event):
        return await self.do_update()

    async def on_button_thumb2(self, event):
        return await self.do_update()

    async def on_button_ext1(self, event):
        return await self.do_update()

    async def on_button_ext2(self, event):
        return await self.do_update()

    async def on_button_unknown(self, event):
        return await self.do_update()

class CPUBlock(Block):
    def __init__(self, **kwargs):
        super().__init__("CPU", markup=True, **kwargs)
        self._fmt = "{0:.2f}%"

    def update(self):
        percents = psutil.cpu_percent(percpu=True)
        return self.set_value(sum(percents) / len(percents))

    def is_urgent(self):
        return self._value >= 95

    def get_width(self):
        return self._fmt.format(100)

    def get_value(self):
        color = util.colors["white"]
        if self._value >= 50 and self._value < 95:
            color = util.colors["yellow"]
        return util.pango_color(self._fmt.format(self._value), color)

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
            return util.pango_color(" OFFLINE", util.colors["red"])
        return "({0}) {1}".format(self._value[0], util.pango_color(self._value[1], util.colors["green"]))

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
    def __init__(self, names, interval=2, **kwargs):
        super().__init__("BAT", interval=interval, markup=True, **kwargs)
        self._names = names
        self._value = (0, None, 0)

    def is_urgent(self):
        return self._value[0] <= 5

    def update(self):
        values = [util.get_bat_stat(bat) for bat in self._names]
        cap = int(sum([value[0] for value in values]) / len(values))
        statuses = [value[1] for value in values]
        status = None
        if "CHR" in statuses:
            status = "CHR"
        elif "DIS" in statuses:
            status = "DIS"
        elif "FULL" in statuses:
            status = "FULL"
        seconds = sum([value[2] for value in values])
        value = (cap, status, seconds)
        return self.set_value(value)

    def get_value(self):
        return util.get_bat_format(self._value)

class DateTimeBlock(Block):
    def __init__(self, label=None, fmt="%a %d-%m-%Y %H:%M:%S", **kwargs):
        super().__init__(label=label, **kwargs)
        self._fmt = fmt

    def update(self):
        return self.set_value(time.localtime())

    def get_value(self):
        return time.strftime(self._fmt, self._value).upper()

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
        if self._value == -1:
            return util.pango_color("ERROR", util.colors["red"])
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

        async def _change_vol(self, change):
            sink = self._get_sink()
            volume = self._pulse.volume_get_all_chans(sink) + change
            if volume < 0.0:
                volume = 0.0
            elif volume > 1.0:
                volume = 1.0
            self._pulse.volume_set_all_chans(sink, volume)
            return await self.do_update()

        def on_button_left(self, event):
            subprocess.Popen([self._exe])
            return False

        async def on_button_right(self, event):
            sink = self._get_sink()
            self._pulse.mute(sink, not bool(sink.mute))
            return await self.do_update()

        async def on_button_wheel_up(self, event):
            return await self._change_vol(self._step)

        async def on_button_wheel_down(self, event):
            return await self._change_vol(-self._step)

        def update(self):
            sink = self._get_sink()
            volume = self._pulse.volume_get_all_chans(sink)
            return self.set_value((int(volume * 100), bool(sink.mute)))

        def get_value(self):
            if self._value[1]:
                return "MUTE"
            return "{0}%".format(self._value[0])

if have_aiohttp:
    class CoinMarketCapBlock(Block):
        def __init__(self, symbol, coin, interval=60, **kwargs):
            super().__init__(symbol, interval=interval, markup=True, **kwargs)
            self._coin = coin
            self.set_button_map(None)

        async def update(self):
            try:
                with async_timeout.timeout(5):
                    async with aiohttp.ClientSession() as session:
                        async with session.get("https://api.coinmarketcap.com/v1/ticker/{0}".format(self._coin)) as res:
                            data = await res.json()
                            value = float(data[0]["price_usd"])
            except:
                value = -1
            return self.set_value((value if self._value is None else self._value[1], value))

        def get_value(self):
            if self._value[1] == -1:
                if self._value[0] != -1:
                    return "{1:.2f} {2}".format(self._value[0], "USD")
                return util.pango_color("ERROR", util.colors["red"])
            if self._value[0] > self._value[1]:
                arrow = "⬇"
                color = util.colors["red"]
            elif self._value[0] < self._value[1]:
                arrow = "⬆"
                color = util.colors["green"]
            else:
                arrow = ""
                color = util.colors["white"]
            return util.pango_color("{0}{1:.2f} {2}".format(arrow, self._value[1], "USD"), color)

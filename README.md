# my3status

__my3status__ is a very simple alternative to i3status. It is written and
configured entirely in Python.

![](/screenshots/example.png)

As the name suggests, this is __my__ i3status. I will probably not accept any
feature requests, but feel free to submit bug fixes.

## Installation and configuration

The installation process consists of a few simple steps.

* Clone this repository
* Run ``pip install --user --upgrade .[volume,net]``
* Copy the example python script below and customize it to your liking
* Call the script from your i3 config

```python
#!/usr/bin/env python3

from my3status.bar import Bar
from my3status.block import *

def main():
    Bar([
        DiskBlock("ROOT", "/", separator=False),
        DiskBlock("HOME", "/home"),
        MemBlock(separator=False),
        SwapBlock(),
        NetBlock(separator=False),
        NetIOBlock(align="right"),
        CPUBlock(),
        DateTimeBlock()
    ]).run()

if __name__ == "__main__":
    main()
```

## Writing a custom block

Eventhough my3status wasn't written with widespread use in mind, it is pretty
extensible. Here's a simple block that obtains and displays your public IP
address.

```python
from my3status.block import Block
import my3status.util as util

import aiohttp
import async_timeout

class IPBlock(Block):
    def __init__(self, interval=60, **kwargs):
        super().__init__("IP", interval=interval, **kwargs)

    async def update(self):
        try:
            with async_timeout.timeout(5):
                async with aiohttp.ClientSession() as session:
                    async with session.get("https://icanhazip.com") as res:
                        text = await res.text()
                        value = text.rstrip('\n')
        except:
            value = ""
        return self.set_value(value)

    def get_text(self):
        if self._value == "":
            return util.pango_color("ERROR", util.colors["red"])
        return self._value
```

Obviously, you shouldn't send a request to icanhazip.com every 60 seconds, but
you get the idea.

#!/usr/bin/env python3

import asyncio
import json
import threading
import time
import sys
from concurrent.futures import ThreadPoolExecutor

def _out(*args, **kwargs):
    print(*args, flush=True, **kwargs)

def _error(*args, **kwargs):
    print(*args, file=sys.stderr, flush=True, **kwargs)

class Bar:
    def __init__(self, blocks):
        self._blocks = [b for b in blocks if b is not None]

    def _find_block(self, instance):
        for block in self._blocks:
            if block.has_id(instance):
                return block
        return None

    def _print_blocks(self):
        output = []
        for blk in self._blocks:
            if blk.has_value():
                output.append(blk.get_json())
        _out(',' + json.dumps(output))

    async def _update_block(self, block):
        if await block.do_update():
            self._print_blocks()

    async def _read_stdin(self, loop):
        executor = ThreadPoolExecutor(max_workers=1)
        while True:
            line = await loop.run_in_executor(executor, sys.stdin.readline)
            line = line.rstrip('\n')
            if line in ["[", "]"]:
                continue
            line = line.lstrip(',')
            event = json.loads(line)
            if "instance" not in event:
                continue
            block = self._find_block(event["instance"])
            if not block:
                _error("error: unable to find block for click event")
                continue
            del event["instance"]
            if await block.on_button(event):
                self._print_blocks()

    def _run(self, loop):
        asyncio.set_event_loop(loop)
        loop.run_forever()

    def run(self):
        # start a task thread
        loop = asyncio.new_event_loop()
        thread = threading.Thread(target=self._run, args=(loop,), daemon=True)
        thread.start()

        # start a task that listens for click events
        asyncio.run_coroutine_threadsafe(self._read_stdin(loop), loop=loop)

        # write the header
        header = {
            "version": 1,
            "click_events": True
        }
        _out(json.dumps(header))
        _out('[')
        _out("[]")

        # update the blocks at the given interval forever
        interval = min(b.interval for b in self._blocks)
        while True:
            for block in self._blocks:
                if block.needs_update():
                    asyncio.run_coroutine_threadsafe(self._update_block(block), loop=loop)
            time.sleep(interval)

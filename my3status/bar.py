#!/usr/bin/env python3

import json
import threading
import time
import signal
import sys

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

    def _read_stdin(self):
        while True:
            line = sys.stdin.readline().rstrip('\n')
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
            if block.on_click(event):
                self._print_blocks()

    def _print_blocks(self):
        output = []
        for blk in self._blocks:
            output.append(blk.get_json())
        _out(',' + json.dumps(output))

    def run(self):
        # start a thread that listens for click events
        thread = threading.Thread(target=self._read_stdin, daemon=True)
        thread.start()

        # write the header
        header = {
            "version": 1,
            "stop_signal": signal.SIGSTOP,
            "cont_signal": signal.SIGCONT,
            "click_events": True
        }
        _out(json.dumps(header))
        _out('[')
        _out("[]")

        # update the blocks at the given interval forever
        interval = min(b.interval for b in self._blocks)
        while True:
            # todo: consider making this more efficient by checking if the value actually changed
            for block in self._blocks:
                if block.needs_update():
                    block.update()
            self._print_blocks()
            time.sleep(interval)

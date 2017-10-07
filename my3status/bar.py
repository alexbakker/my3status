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
    def __init__(self, blocks, interval=0.5):
        self._blocks = [b for b in blocks if b is not None]
        self._interval = interval

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
            block.on_click(event)

    def run(self):
        # start a thread that listens for click events
        thread = threading.Thread(target=self._read_stdin, daemon=True)
        thread.start()

        header = {
            "version": 1,
            "stop_signal": signal.SIGSTOP,
            "cont_signal": signal.SIGCONT,
            "click_events": True
        }
        _out(json.dumps(header))
        _out('[')
        _out("[]")

        while True:
            output = []
            for blk in self._blocks:
                blk.update()
                output.append(blk.get_json())

            _out(',' + json.dumps(output))
            time.sleep(0.5)

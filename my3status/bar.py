#!/usr/bin/env python3

import json
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

    def run(self):
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

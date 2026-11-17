#!/usr/bin/env python3
"""Check real terminal startup; suppress authentication prompts/transcripts."""
import argparse
import fcntl
import os
import pty
import re
import select
import signal
import struct
import subprocess
import termios
import time

parser = argparse.ArgumentParser()
parser.add_argument('--herdr', action='store_true')
parser.add_argument('command', nargs=argparse.REMAINDER)
args = parser.parse_args()
command = args.command[1:] if args.command[:1] == ['--'] else args.command
master, slave = pty.openpty()
fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 40, 140, 0, 0))
def controlling_terminal():
    os.setsid()
    fcntl.ioctl(0, termios.TIOCSCTTY, 0)

proc = subprocess.Popen(command, stdin=slave, stdout=slave, stderr=slave, preexec_fn=controlling_terminal)
os.close(slave)
output = b''
text = b''
pattern = rb'agents|workspaces|spaces|settings' if args.herdr else rb'login|log in|sign in|authenticat|api.?key|trust|welcome|connect|provider|model|ask anything|what do you want'
try:
    deadline = time.monotonic() + 35
    while time.monotonic() < deadline:
        if select.select([master], [], [], 0.5)[0]:
            try:
                data = os.read(master, 65536)
            except OSError:
                break
            output += data
            # Terminal capability probes must receive replies or some TUIs wait.
            if b'\x1b[6n' in data:
                os.write(master, b'\x1b[1;1R')
            if b'\x1b[c' in data:
                os.write(master, b'\x1b[?1;2c')
        text = re.sub(rb'\x1b\[[0-?]*[ -/]*[@-~]', b'', output).lower()
        if re.search(pattern, text):
            if re.search(rb'module_not_found|traceback|error while loading shared libraries|command not found', text):
                raise RuntimeError('CLI terminal startup encountered a runtime error')
            os.write(master, b'\x02q' if args.herdr else b'\x03')
            print('Interactive terminal reached its startup/attachment surface.')
            break
        if proc.poll() is not None:
            break
    else:
        raise RuntimeError('Terminal startup timed out')
    if not re.search(pattern, text):
        raise RuntimeError('Terminal exited before its startup surface')
finally:
    if proc.poll() is None:
        os.killpg(proc.pid, signal.SIGTERM)
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
    os.close(master)

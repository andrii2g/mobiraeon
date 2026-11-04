"""Persistent protected per-Task actuation inode; never removed or recreated."""

import hashlib
import os
import signal
import threading
from contextlib import contextmanager
from dataclasses import dataclass

from mobiraeon.errors import Reason, SafeError
from mobiraeon.forge_credentials import verify_installation
from mobiraeon.private_state import harden, protected


@dataclass
class Interruption:
    pending: bool = False


@contextmanager
def signals():
    interruption = Interruption()
    previous = {}

    def pending(signum, frame):
        interruption.pending = True

    try:
        if threading.current_thread() is threading.main_thread():
            for signum in (signal.SIGINT, signal.SIGTERM):
                previous[signum] = signal.signal(signum, pending)
            if os.name == "nt":
                previous[signal.SIGBREAK] = signal.signal(signal.SIGBREAK, pending)
        yield interruption
    finally:
        for signum, handler in previous.items():
            signal.signal(signum, handler)


@contextmanager
def guard(private, task):
    verify_installation(private)
    path = private.directory / ("forge-" + hashlib.sha256(task.encode()).hexdigest() + ".lock")
    descriptor = None
    locked = False
    try:
        try:
            descriptor = os.open(path, os.O_RDWR | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            protected(path)
            descriptor = os.open(path, os.O_RDWR)
        else:
            harden(path)
            os.write(descriptor, b"\0")
            os.fsync(descriptor)
        protected(path)
        try:
            if os.name == "nt":
                import msvcrt

                os.lseek(descriptor, 0, os.SEEK_SET)
                msvcrt.locking(descriptor, msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            locked = True
        except OSError:
            raise SafeError(Reason.UNAVAILABLE) from None
        yield
    finally:
        if descriptor is not None:
            try:
                if locked:
                    if os.name == "nt":
                        import msvcrt

                        os.lseek(descriptor, 0, os.SEEK_SET)
                        msvcrt.locking(descriptor, msvcrt.LK_UNLCK, 1)
                    else:
                        import fcntl

                        fcntl.flock(descriptor, fcntl.LOCK_UN)
            finally:
                os.close(descriptor)

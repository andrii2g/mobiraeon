"""Installation-owner proof and protected delivery; no credential transport in argv."""

import ctypes
import hashlib
import json
import os
import stat
from contextlib import contextmanager
from functools import cache
from pathlib import Path
from uuid import uuid4

from mobiraeon.errors import Reason, SafeError


@cache
def _windows():
    from ctypes import wintypes as w

    adv = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    void = ctypes.c_void_p
    declarations = [
        (adv, "OpenProcessToken", [w.HANDLE, w.DWORD, ctypes.POINTER(w.HANDLE)], w.BOOL),
        (
            adv,
            "GetTokenInformation",
            [w.HANDLE, ctypes.c_int, void, w.DWORD, ctypes.POINTER(w.DWORD)],
            w.BOOL,
        ),
        (adv, "ConvertSidToStringSidW", [void, ctypes.POINTER(w.LPWSTR)], w.BOOL),
        (
            adv,
            "GetNamedSecurityInfoW",
            [
                w.LPWSTR,
                ctypes.c_int,
                w.DWORD,
                ctypes.POINTER(void),
                void,
                ctypes.POINTER(void),
                void,
                ctypes.POINTER(void),
            ],
            w.DWORD,
        ),
        (adv, "GetAclInformation", [void, void, w.DWORD, ctypes.c_int], w.BOOL),
        (adv, "GetAce", [void, w.DWORD, ctypes.POINTER(void)], w.BOOL),
        (
            adv,
            "ConvertStringSecurityDescriptorToSecurityDescriptorW",
            [w.LPCWSTR, w.DWORD, ctypes.POINTER(void), void],
            w.BOOL,
        ),
        (adv, "SetFileSecurityW", [w.LPCWSTR, w.DWORD, void], w.BOOL),
        (kernel, "GetCurrentProcess", [], w.HANDLE),
        (kernel, "CloseHandle", [w.HANDLE], w.BOOL),
        (kernel, "LocalFree", [void], void),
        (kernel, "MoveFileExW", [w.LPCWSTR, w.LPCWSTR, w.DWORD], w.BOOL),
    ]
    for library, name, args, returns in declarations:
        function = getattr(library, name)
        function.argtypes, function.restype = args, returns
    return adv, kernel


def _sid(pointer):
    from ctypes import wintypes as w

    adv, kernel = _windows()
    text = w.LPWSTR()
    if not adv.ConvertSidToStringSidW(pointer, ctypes.byref(text)):
        raise SafeError(Reason.PROTECTION)
    try:
        return text.value
    finally:
        kernel.LocalFree(ctypes.cast(text, ctypes.c_void_p))


def principal():
    if os.name != "nt":
        return "uid-" + str(os.geteuid())
    from ctypes import wintypes as w

    adv, kernel = _windows()
    token = w.HANDLE()
    if not adv.OpenProcessToken(kernel.GetCurrentProcess(), 8, ctypes.byref(token)):
        raise SafeError(Reason.PROTECTION)
    try:
        needed = w.DWORD()
        adv.GetTokenInformation(token, 1, None, 0, ctypes.byref(needed))
        buffer = ctypes.create_string_buffer(needed.value)
        if not adv.GetTokenInformation(token, 1, buffer, needed, ctypes.byref(needed)):
            raise SafeError(Reason.PROTECTION)
        return _sid(ctypes.cast(buffer, ctypes.POINTER(ctypes.c_void_p))[0])
    finally:
        kernel.CloseHandle(token)


def harden(path):
    path = Path(path)
    if os.name != "nt":
        path.chmod(0o700 if path.is_dir() else 0o600)
        return
    adv, kernel = _windows()
    who = principal()
    flags = "OICI" if path.is_dir() else ""
    sddl = f"O:{who}D:P(A;{flags};FA;;;{who})(A;{flags};FA;;;SY)"
    descriptor = ctypes.c_void_p()
    if not adv.ConvertStringSecurityDescriptorToSecurityDescriptorW(
        sddl, 1, ctypes.byref(descriptor), None
    ):
        raise SafeError(Reason.PROTECTION)
    try:
        if not adv.SetFileSecurityW(str(path), 5 | 0x80000000, descriptor):
            raise SafeError(Reason.PROTECTION)
    finally:
        kernel.LocalFree(descriptor)


def protected(path, *, directory=False):
    path = Path(path)
    info = path.lstat()
    if path.is_symlink() or (os.name == "nt" and path.is_junction()):
        raise SafeError(Reason.PROTECTION)
    if directory != stat.S_ISDIR(info.st_mode):
        raise SafeError(Reason.PROTECTION)
    if not directory and (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1):
        raise SafeError(Reason.PROTECTION)
    if os.name != "nt":
        if info.st_uid != os.geteuid() or info.st_mode & 0o077:
            raise SafeError(Reason.PROTECTION)
        return
    from ctypes import wintypes as w

    adv, kernel = _windows()
    owner, acl, descriptor = ctypes.c_void_p(), ctypes.c_void_p(), ctypes.c_void_p()
    error = adv.GetNamedSecurityInfoW(
        str(path),
        1,
        5,
        ctypes.byref(owner),
        None,
        ctypes.byref(acl),
        None,
        ctypes.byref(descriptor),
    )
    if error:
        raise SafeError(Reason.PROTECTION)
    try:
        who = principal()
        if _sid(owner) != who or not acl:
            raise SafeError(Reason.PROTECTION)
        sizes = (w.DWORD * 3)()
        if not adv.GetAclInformation(acl, sizes, ctypes.sizeof(sizes), 2):
            raise SafeError(Reason.PROTECTION)
        owner_full = False
        for index in range(sizes[0]):
            ace = ctypes.c_void_p()
            if not adv.GetAce(acl, index, ctypes.byref(ace)):
                raise SafeError(Reason.PROTECTION)
            header = (ctypes.c_ubyte * 4).from_address(ace.value)
            mask = w.DWORD.from_address(ace.value + 4).value
            identity = _sid(ace.value + 8)
            if header[0] != 0 or identity not in {who, "S-1-5-18"}:
                raise SafeError(Reason.PROTECTION)
            owner_full |= identity == who and mask & 0x1F01FF == 0x1F01FF
        if not owner_full:
            raise SafeError(Reason.PROTECTION)
    finally:
        kernel.LocalFree(descriptor)


def durable_new(path, content):
    """No overwrite. Private temp file is flushed before durable delivery rename."""
    path = Path(path)
    protected(path.parent, directory=True)
    pending = path.parent / ("pending-" + uuid4().hex)
    try:
        with pending.open("xb") as stream:
            harden(pending)
            protected(pending)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        if os.name == "nt":
            _, kernel = _windows()
            if not kernel.MoveFileExW(str(pending), str(path), 8):
                raise SafeError(Reason.DELIVERY)
        else:
            os.link(pending, path)  # Atomic, fails if destination already exists.
            pending.unlink()
            descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
        protected(path)
    except Exception:
        # Only our unregistered staging file is cleaned up. Delivered files remain
        # available for reconciliation even when later protection/DB checks fail.
        if pending.exists():
            pending.unlink()
        raise SafeError(Reason.DELIVERY) from None


class PrivateState:
    def __init__(self, directory, database):
        if directory is None:
            raise SafeError(Reason.PROTECTION)
        self.directory = Path(directory).absolute()
        self.database = Path(database).absolute()

    def provision(self):
        if any((parent / ".git").exists() for parent in self.directory.parents):
            raise SafeError(Reason.PROTECTION)
        if self.database.parent != self.directory:
            raise SafeError(Reason.PROTECTION)
        try:
            self.directory.mkdir(mode=0o700)
            harden(self.directory)
            credentials = self.directory / "credentials"
            credentials.mkdir(mode=0o700)
            harden(credentials)
            marker = {
                "installation": uuid4().hex,
                "principal": principal(),
                "database": hashlib.sha256(str(self.database).encode()).hexdigest(),
            }
            durable_new(self.directory / "installation.json", json.dumps(marker).encode())
            return marker["installation"]
        except Exception:
            raise SafeError(Reason.PROTECTION) from None

    def verify(self, *, require_database=True):
        try:
            if self.database.parent != self.directory:
                raise SafeError(Reason.PROTECTION)
            protected(self.directory, directory=True)
            protected(self.directory / "credentials", directory=True)
            protected(self.directory / "installation.json")
            if require_database:
                protected(self.database)
            marker = json.loads((self.directory / "installation.json").read_text())
            if (
                marker["principal"] != principal()
                or marker["database"] != hashlib.sha256(str(self.database).encode()).hexdigest()
            ):
                raise SafeError(Reason.PROTECTION)
            return marker
        except Exception:
            raise SafeError(Reason.PROTECTION) from None

    def credential_path(self, name):
        from mobiraeon.contracts import _token

        _token(name)
        if name in {".", ".."} or ".." in name:
            raise SafeError(Reason.INVALID_INPUT)
        return self.directory / "credentials" / name

    @contextmanager
    def credential_lifecycle(self):
        """Cross-process exclusion for delivery/registration and deliberate cleanup.

        The persistent inode must never be unlinked. No DB transaction is open
        while this file is created or its OS lock is acquired/released.
        """
        self.verify()
        path = self.directory / "credential-lifecycle.lock"
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
            # Independent handles/open-file descriptions exclude threads as well
            # as separate CLI and API processes. Lock acquisition never waits.
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
            try:
                if locked:
                    if os.name == "nt":
                        import msvcrt

                        os.lseek(descriptor, 0, os.SEEK_SET)
                        msvcrt.locking(descriptor, msvcrt.LK_UNLCK, 1)
                    else:
                        import fcntl

                        fcntl.flock(descriptor, fcntl.LOCK_UN)
            except OSError:
                raise SafeError(Reason.CLEANUP_FAILED) from None
            finally:
                if descriptor is not None:
                    os.close(descriptor)

    def read_credential(self, path):
        if path is None:
            raise SafeError(Reason.CONFIG_INVALID, setting="access.credential_file")
        self.verify()
        path = Path(path).absolute()
        if path.parent != self.directory / "credentials":
            raise SafeError(Reason.PROTECTION)
        try:
            protected(path)
            with path.open("r", encoding="ascii") as stream:
                value = stream.read(128).strip()
            return value
        except Exception:
            raise SafeError(Reason.PROTECTION) from None

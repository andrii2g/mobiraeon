"""Protected forge token delivery. Values are never command arguments or results."""

import ctypes
import json
import os
import re
import stat
from pathlib import Path

from mobiraeon.access import Access
from mobiraeon.configuration import resolve_configuration
from mobiraeon.errors import Reason, SafeError
from mobiraeon.persistence import Store
from mobiraeon.private_state import (
    PrivateState,
    _sid,
    _windows,
    durable_new,
    principal,
    protected,
)


def ancestry(path):
    """Check every lexical ancestor before resolving; trusted OS anchors are allowed."""
    path = Path(path).absolute()
    for parent in (path, *path.parents):
        info = parent.lstat()
        if parent.is_symlink() or (os.name == "nt" and parent.is_junction()):
            raise SafeError(Reason.PROTECTION)
        if (parent / ".git").exists():
            raise SafeError(Reason.PROTECTION)
        if not stat.S_ISDIR(info.st_mode):
            continue
        if os.name != "nt":
            trusted_tmp = info.st_uid == 0 and bool(info.st_mode & stat.S_ISVTX)
            if info.st_uid not in {0, os.geteuid()} or (
                info.st_mode & 0o022 and not trusted_tmp
            ):
                raise SafeError(Reason.PROTECTION)
        else:
            _windows_parent(parent)
    return path


def _windows_parent(path):
    from ctypes import wintypes as w

    adv, kernel = _windows()
    owner, acl, descriptor = ctypes.c_void_p(), ctypes.c_void_p(), ctypes.c_void_p()
    if adv.GetNamedSecurityInfoW(
        str(path),
        1,
        5,
        ctypes.byref(owner),
        None,
        ctypes.byref(acl),
        None,
        ctypes.byref(descriptor),
    ):
        raise SafeError(Reason.PROTECTION)
    try:
        trusted = {
            principal(),
            "S-1-5-18",
            "S-1-5-32-544",
            "S-1-5-80-956008885-3418522649-1831038044-1853292631-2271478464",
        }  # Windows TrustedInstaller
        if not acl or _sid(owner) not in trusted:
            raise SafeError(Reason.PROTECTION)
        sizes = (w.DWORD * 3)()
        if not adv.GetAclInformation(acl, sizes, ctypes.sizeof(sizes), 2):
            raise SafeError(Reason.PROTECTION)
        for index in range(sizes[0]):
            ace = ctypes.c_void_p()
            if not adv.GetAce(acl, index, ctypes.byref(ace)):
                raise SafeError(Reason.PROTECTION)
            header = (ctypes.c_ubyte * 4).from_address(ace.value)
            # Skip inherit-only entries; they do not grant access to this parent.
            if header[1] & 8:
                continue
            if header[0] == 1:  # denial cannot introduce write authority
                continue
            if header[0] != 0:
                raise SafeError(Reason.PROTECTION)
            mask = w.DWORD.from_address(ace.value + 4).value
            # Creating a different child does not confer replacement of this existing
            # path. Reject generic write/all, delete, delete-child and ACL/owner writes.
            if mask & 0x500D0040 and _sid(ace.value + 8) not in trusted:
                raise SafeError(Reason.PROTECTION)
    finally:
        kernel.LocalFree(descriptor)


def validate_token(raw):
    if raw.endswith(b"\r\n"):
        raw = raw[:-2]
    elif raw.endswith(b"\n"):
        raw = raw[:-1]
    if not 1 <= len(raw) <= 4096 or any(byte < 33 or byte > 126 for byte in raw):
        raise SafeError(Reason.PROTECTION)
    if re.fullmatch(rb"mbr_[0-9a-f]{32}_[A-Za-z0-9_-]{43}", raw):
        raise SafeError(Reason.PROTECTION)
    return raw.decode("ascii")


def read_file(path):
    path = ancestry(path)
    protected(path)
    with path.open("rb") as stream:
        raw = stream.read(4099)  # 4096 plus CRLF plus one overflow-detection byte
    return validate_token(raw)


def verify_installation(private):
    ancestry(private.directory)
    private.verify()
    ancestry(private.database)
    ancestry(private.directory / "credentials")


def owner_binding(store, private):
    verify_installation(private)
    if Path(store.path).absolute() != private.database:
        raise SafeError(Reason.PROTECTION)
    access = Access(store, private)
    proof = access.owner_proof()
    with store.engine.connect() as tx:
        if not access.owner_valid(proof, tx):
            raise SafeError(Reason.PROTECTION)


def read_token(private, name, *, store):
    owner_binding(store, private)
    return read_file(private.credential_path(name))


def import_token(store, private, source, destination):
    owner_binding(store, private)
    value = read_file(source)
    path = private.credential_path(destination)
    durable_new(path, value.encode("ascii") + b"\n")
    return destination


def main():
    from mobiraeon.cli import SafeParser

    parser = SafeParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--config", required=True)
    parser.add_argument("--source-file", required=True, type=Path)
    parser.add_argument("--destination-name", required=True)
    store = None
    try:
        args = parser.parse_args()
        config = resolve_configuration(options={"config": args.config})
        store = Store(config.database_path, config.timeout_seconds)
        store.check()
        name = import_token(
            store,
            PrivateState(config.private_dir, config.database_path),
            args.source_file,
            args.destination_name,
        )
        print(json.dumps({"outcome": "success", "reference": name}))
        return 0
    except Exception:
        print(json.dumps({"outcome": "known_failure", "reason": "private_state_unprotected"}))
        return 1
    finally:
        if store:
            store.close()


if __name__ == "__main__":
    raise SystemExit(main())

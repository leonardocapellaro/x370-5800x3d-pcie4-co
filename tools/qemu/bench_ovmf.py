#!/usr/bin/env python3
"""Boot bench_app.c on an emulated USB stick under OVMF and check the FAT logs.

What: builds a 32 MB FAT disk image with mformat/mmd/mcopy, places the built
bench_app EFI at EFI/BOOT/BOOTX64.EFI, the chosen list at C6HLAB/LISTA.TXT and
(optionally) the capture at C6HLAB/A2.BIN, boots it on q35/TCG with a temp
OVMF_VARS, waits for the app to write C6HLAB/LOG001.TXT on the serial log,
then asserts the log lines. The battery covers: a 64-address REPLAY against a
capture (expected lines computed from the capture bytes directly), LIVE on
q35 (app must refuse cleanly: SKIP unsupported-platform), invalid-list,
missing-list, truncated-capture, and a subset replay. It also asserts an
old LOG000.TXT on the disk is never touched.
Why: this is the OVMF harness every probe CAP passed before staging — it
proves the app reads its inputs, honors WRITE-ONLY-TO-NEW-LOG, and validates
the capture format, without ever touching a board.
How (needs qemu-system-x86_64, mtools (mformat/mmd/mcopy/mtype), OVMF):
    python3 -I bench_ovmf.py --efi BUILD/BOOTX64.EFI --list mylist.txt \
        --capture A2.BIN
Build the EFI from bench_app.c with EDK2 (UefiApplicationEntryPoint) or the
clang/lld pattern from replay_run.py (entry UefiMain). The capture file (and
its 1168 readings) are board data and NOT shipped — see capture_format.h.
LISTA format: first line LIVE or REPLAY, then 1..64 8-hex-digit addresses
aligned in the NBIO block 0x03810000..0x000000ff.
Exit codes: 0 all cases passed; anything else failed (assert message printed).
"""
from pathlib import Path
from tempfile import TemporaryDirectory
from concurrent.futures import ThreadPoolExecutor
import argparse
import hashlib
import json
import os
import shutil
import struct
import subprocess
import time

OVMF = Path(os.environ.get("OVMF_DIR", "/usr/share/edk2/ovmf"))
BASE = 0x03810000


def run(*args):
    return subprocess.check_output(args, stderr=subprocess.STDOUT)


def check(case, config, expected, capture=None, efi=None):
    with TemporaryDirectory(prefix="c6h-ovmf-") as tmp:
        tmp = Path(tmp)
        disk = tmp / "usb.img"
        with disk.open("wb") as stream:
            stream.truncate(32 * 1024**2)
        run("mformat", "-i", disk, "::")
        run("mmd", "-i", disk, "::EFI", "::EFI/BOOT", "::C6HLAB")
        run("mcopy", "-i", disk, efi, "::EFI/BOOT/BOOTX64.EFI")
        if config is not None:
            (tmp / "list").write_bytes(config.encode())
            run("mcopy", "-i", disk, tmp / "list", "::C6HLAB/LISTA.TXT")
        if capture is not None:
            (tmp / "capture").write_bytes(capture)
            run("mcopy", "-i", disk, tmp / "capture", "::C6HLAB/A2.BIN")
        (tmp / "old").write_bytes(b"preserve")
        run("mcopy", "-i", disk, tmp / "old", "::C6HLAB/LOG000.TXT")
        var = tmp / "vars.fd"
        shutil.copyfile(OVMF / "OVMF_VARS.fd", var)
        serial = tmp / "serial"
        args = ["qemu-system-x86_64", "-machine", "q35,accel=tcg", "-m", "256",
                "-drive", f"if=pflash,format=raw,readonly=on,file={OVMF}/OVMF_CODE.fd",
                "-drive", f"if=pflash,format=raw,file={var}", "-device", "qemu-xhci",
                "-drive", f"if=none,id=stick,format=raw,file={disk}", "-device",
                "usb-storage,drive=stick,bootindex=1", "-display", "none", "-serial",
                f"file:{serial}", "-monitor", "none", "-nic", "none", "-no-reboot"]
        with subprocess.Popen(args, stderr=subprocess.DEVNULL) as vm:
            try:
                deadline = time.monotonic() + 45
                while time.monotonic() < deadline and vm.poll() is None:
                    if serial.exists() and b"LOG001.TXT" in serial.read_bytes():
                        break
                    time.sleep(.15)
                else:
                    raise RuntimeError(f"{case}: {serial.read_bytes()[-700:]}")
            finally:
                vm.terminate()
                vm.wait(timeout=10)
        assert run("mtype", "-i", disk, "::C6HLAB/LOG000.TXT") == b"preserve"
        lines = run("mtype", "-i", disk, "::C6HLAB/LOG001.TXT").decode().splitlines()
        assert lines == expected, (case, lines, expected)
        return case


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--efi", type=Path, required=True, metavar="BOOTX64.EFI",
                        help="built bench_app EFI binary")
    parser.add_argument("--list", type=Path, required=True, metavar="LISTA",
                        help="address list file (first line LIVE or REPLAY)")
    parser.add_argument("--capture", type=Path, metavar="A2.BIN",
                        help="capture file; enables the REPLAY battery cases")
    args = parser.parse_args()
    live = args.list.read_text(encoding="ascii")
    fields = live.splitlines()
    if not fields or fields[0] not in {"LIVE", "REPLAY"}:
        parser.error("first line must be LIVE or REPLAY")
    addresses = [int(line, 16) for line in fields[1:] if line]
    if not addresses or len(addresses) > 64 or any(
        not BASE <= a < BASE + 256 or a % 4 for a in addresses
    ):
        parser.error("expected 1 to 64 aligned addresses in the NBIO block")
    if args.capture:
        raw = args.capture.read_bytes()
        # capture wire (capture_format.h): 4 B attrs + 32-word header + Raw[]
        expected = ["REPLAY A2 DXE"]
        for address in addresses:
            i = 1024 + (address - BASE) // 4
            value, = struct.unpack_from("<I", raw, 4 + 128 + 4 * i)
            expected.append(f"{address:08x},{value:08x}")
        expected.append("COMPLETE")
        cases = [
            ("replay-64", live.replace(fields[0], "REPLAY", 1), expected, raw),
            ("live-q35", live.replace(fields[0], "LIVE", 1), ["LIVE UEFI application", "SKIP unsupported-platform"], None),
            ("lista-invalida", "LIVE\nffffffff\n", ["ERROR invalid-list"], None),
            ("arquivo-truncado", "REPLAY\r\n03810054", ["REPLAY A2 DXE", "ERROR invalid-capture"], raw[:-1]),
            ("lista-ausente", None, ["ERROR cannot-read-list"], None),
            ("subconjunto", "REPLAY\r\n03810054", ["REPLAY A2 DXE", "03810054,00000001", "COMPLETE"], raw),
        ]
    else:
        cases = [
            ("live-q35", live.replace(fields[0], "LIVE", 1), ["LIVE UEFI application", "SKIP unsupported-platform"], None),
            ("lista-invalida", "LIVE\nffffffff\n", ["ERROR invalid-list"], None),
            ("lista-ausente", None, ["ERROR cannot-read-list"], None),
        ]
    with ThreadPoolExecutor(max_workers=2) as pool:
        tasks = [pool.submit(check, *c, efi=args.efi) for c in cases]
        passed = [task.result() for task in tasks]
    summary = dict(tests=passed, efi_sha256=hashlib.sha256(args.efi.read_bytes()).hexdigest())
    if args.capture:
        summary["capture_sha256"] = hashlib.sha256(args.capture.read_bytes()).hexdigest()
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

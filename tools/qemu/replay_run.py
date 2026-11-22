#!/usr/bin/env python3
"""Run probe logic against a board capture inside an ephemeral QEMU/OVMF VM.

What: compiles replay_guest.c + your probe C (a file implementing
BOOLEAN probe_check(VOID) against probe_api.h) with clang (COFF) and lld into
BOOTX64.EFI, drops it together with your capture file (A2.BIN) on a temporary
FAT disk, boots OVMF under QEMU/TCG with a temp copy of OVMF_VARS, and turns
the debug-console transcript into a verdict.
Why: test the DECISION LOGIC of a new probe (the part that will later run on
the board) against a real, archived boot — 1168 SMN readings of the A2 map
from the 5800X3D board at DXE entry — with zero risk and no board. The
capture is a board read and is NOT shipped in this repo; recreate one with
tools/probes/smn_dxe_probe.c + dumping the EFI variable (see capture_format.h
for the exact wire and docs/08 for the method).
How (needs clang, lld-link, qemu-system-x86_64, OVMF, and an EDK2 checkout):
    EDK2_INCLUDE=~/edk2/MdePkg/Include \
    python3 -I replay_run.py --capture A2.BIN 0x03810054 0x12345678
    python3 -I replay_run.py --capture A2.BIN --probe probe_example.c
Each `read_captured(0x..., &v)` consult prints `SMN <addr> MEASURED <value>`
(MEASURED = that address WAS recorded in that boot phase) or
`SMN <addr> NOT_CAPTURED` and forces INCONCLUSIVE. Zero and 0xFFFFFFFF are
possible raw answers; one value alone never proves a register's meaning,
writability, or a phase where it was not sampled.

Exit codes: 0 PASS (covered reads, assertions hold)
            1 FAIL (all reads covered, probe rejected the data)
            2 INCONCLUSIVE (probe asked for an address outside the capture,
              or made no consults)
            3 infrastructure failure (compile, capture, boot, VM)
The table reprints the same value for every consult of an address;
accessibility in another phase/base, temporal order, write effects,
asynchronous changes and brand-new addresses all need extra evidence.
"""
import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent


def address(text):
    try:
        value = int(text, 16)
    except ValueError:
        raise argparse.ArgumentTypeError("use hexadecimal")
    if not 0 <= value <= 0xffffffff:
        raise argparse.ArgumentTypeError("address out of 32-bit range")
    return value


def main():
    parser = argparse.ArgumentParser(
        description="Replay probe logic against an archived SMN capture in QEMU/OVMF.",
        epilog="env: EDK2_INCLUDE (required: path to an EDK2 MdePkg/Include), "
               "OVMF_DIR (default /usr/share/edk2/ovmf)")
    parser.add_argument("--capture", type=Path, required=True,
                        help="A2-style capture file (wire: capture_format.h)")
    parser.add_argument("--expect-sha256", help="refuse if the capture digest differs")
    parser.add_argument("--probe", type=Path, help="C source implementing probe_check()")
    parser.add_argument("enderecos", type=address, nargs="*",
                        help="addresses to consult (alternative to --probe)")
    args = parser.parse_args()
    if bool(args.probe) == bool(args.enderecos):
        parser.error("give one or more addresses OR --probe file.c")
    raw = args.capture.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if args.expect_sha256 and digest != args.expect_sha256:
        print(f"capture digest {digest} != expected {args.expect_sha256}", file=sys.stderr)
        return 3
    if not os.environ.get("EDK2_INCLUDE"):
        print("set EDK2_INCLUDE to an EDK2 MdePkg/Include directory", file=sys.stderr)
        return 3
    include = Path(os.environ["EDK2_INCLUDE"]).resolve()
    ovmf = Path(os.environ.get("OVMF_DIR", "/usr/share/edk2/ovmf")).resolve()
    with tempfile.TemporaryDirectory(prefix="c6h-replay-") as directory:
        work = Path(directory)
        fat = work / "fat"
        boot = fat / "EFI/BOOT"
        boot.mkdir(parents=True)
        shutil.copyfile(args.capture, fat / "A2.BIN")
        source = args.probe
        if source is None:
            source = work / "consulta.c"
            reads = "".join(f"    read_captured(0x{a:08x}U, &v);\n" for a in args.enderecos)
            source.write_text('#include "probe_api.h"\nBOOLEAN probe_check(VOID) {\n'
                              '    UINT32 v;\n' + reads + '    return TRUE;\n}\n')
        for src, obj in [(HERE / "replay_guest.c", "guest.obj"), (source, "sonda.obj")]:
            subprocess.run(["clang", "--target=x86_64-pc-win32-coff", "-Os", "-ffreestanding",
                            "-fshort-wchar", "-fno-builtin", "-fno-stack-protector", "-mno-red-zone",
                            "-Wall", "-Wextra", "-Werror", "-DUSE_EDK2_HEADERS",
                            "-I", include, "-I", include / "X64", "-I", HERE,
                            "-c", src, "-o", work / obj], check=True)
        subprocess.run(["lld-link", "/subsystem:efi_application", "/entry:ReplayMain",
                        "/nodefaultlib", "/timestamp:0", f"/out:{boot}/BOOTX64.EFI",
                        work / "guest.obj", work / "sonda.obj"], check=True)
        var = work / "vars.fd"
        shutil.copyfile(ovmf / "OVMF_VARS.fd", var)
        trace = work / "trace.txt"
        cmd = ["qemu-system-x86_64", "-machine", "q35,accel=tcg", "-m", "256",
               "-drive", f"if=pflash,format=raw,readonly=on,file={ovmf}/OVMF_CODE.fd",
               "-drive", f"if=pflash,format=raw,file={var}",
               "-drive", f"format=raw,file=fat:rw:{fat}",
               "-debugcon", f"file:{trace}", "-global", "isa-debugcon.iobase=0xe9",
               "-device", "isa-debug-exit,iobase=0xf4,iosize=4",
               "-display", "none", "-monitor", "none", "-serial", "none", "-nic", "none", "-no-reboot"]
        try:
            status = subprocess.run(cmd, timeout=45).returncode
        except subprocess.TimeoutExpired:
            status = -1
        transcript = trace.read_text() if trace.exists() else ""
        print(transcript, end="")
        for code, marker in enumerate(("PASS", "FAIL", "INCONCLUSIVE")):
            if status == 2 * code + 1 and transcript.endswith(marker + "\n"):
                return code
        print(f"infrastructure or boot failure (QEMU {status})", file=sys.stderr)
        return 3


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, subprocess.CalledProcessError) as error:
        print(f"infrastructure failure: {error}", file=sys.stderr)
        sys.exit(3)

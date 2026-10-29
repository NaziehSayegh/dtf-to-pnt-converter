#!/usr/bin/env python3
"""
dtf2pnt.py - Convert survey .DTF point files to .PNT text files.

Output format (one point per line, space separated):
    <point number> <X> <Y> <Z>

Usage:
    python dtf2pnt.py                           -> opens the window (GUI)
    python dtf2pnt.py FILE.DTF [...]            -> converts each file to FILE.pnt
    python dtf2pnt.py FOLDER                    -> converts every .DTF in the folder
"""
import os
import struct
import sys

HEADER_SIZE = 40           # bytes before the first point record
RECORD_SIZE = 20           # 8 bytes X + 8 bytes Y + 4 bytes Z


def mbf_double(b):
    """Decode an 8-byte Microsoft Binary Format (MBF) double."""
    exponent = b[7]
    if exponent == 0:
        return 0.0
    sign = -1.0 if b[6] & 0x80 else 1.0
    mantissa = int.from_bytes(bytes(b[0:6]) + bytes([(b[6] & 0x7F) | 0x80]), "little")
    return sign * mantissa / 2.0 ** 56 * 2.0 ** (exponent - 128)


def mbf_single(b):
    """Decode a 4-byte Microsoft Binary Format (MBF) single."""
    exponent = b[3]
    if exponent == 0:
        return 0.0
    sign = -1.0 if b[2] & 0x80 else 1.0
    mantissa = int.from_bytes(bytes(b[0:2]) + bytes([(b[2] & 0x7F) | 0x80]), "little")
    return sign * mantissa / 2.0 ** 24 * 2.0 ** (exponent - 128)


def read_dtf(path):
    """Return (header_info, points). points = [(number, x, y, z), ...]"""
    with open(path, "rb") as f:
        data = f.read()
    if len(data) < HEADER_SIZE:
        raise ValueError("File is too small to be a DTF file")

    name = data[0:16].decode("latin-1").strip()
    count = struct.unpack("<I", data[16:20])[0]
    info = data[20:40].decode("latin-1").strip()

    expected = HEADER_SIZE + RECORD_SIZE * count
    if len(data) < expected:
        raise ValueError(f"File size {len(data)} does not match {count} records")

    points = []
    for i in range(count):
        start = HEADER_SIZE + RECORD_SIZE * i
        rec = data[start:start + RECORD_SIZE]
        x = mbf_double(rec[0:8])
        y = mbf_double(rec[8:16])
        z = mbf_single(rec[16:20])
        # Empty slots hold the value 0.0001 (or 0) - skip them
        if abs(x) < 1 and abs(y) < 1:
            continue
        points.append((i + 1, x, y, z))
    return {"name": name, "slots": count, "info": info}, points


def write_pnt(points, out_path):
    with open(out_path, "w", newline="\r\n") as f:
        for n, x, y, z in points:
            f.write(f"{n} {x:.3f} {y:.3f} {z:.2f}\n")


def convert(path):
    header, points = read_dtf(path)
    out_path = os.path.splitext(path)[0] + ".pnt"
    write_pnt(points, out_path)
    no_z = sum(1 for p in points if abs(p[3]) < 0.005)
    return out_path, header, len(points), no_z


def collect(paths):
    files = []
    for p in paths:
        if os.path.isdir(p):
            files += [os.path.join(p, f) for f in sorted(os.listdir(p))
                      if f.lower().endswith(".dtf")]
        else:
            files.append(p)
    return files


def run_cli(args):
    for path in collect(args):
        try:
            out, h, n, no_z = convert(path)
            print(f"OK {path} -> {out} ({n} points, {no_z} without height)"
                  f" [{h['name']} {h['info']}]")
        except Exception as e:
            print(f"ERR {path}: {e}")


def run_gui():
    import tkinter as tk
    from tkinter import filedialog, scrolledtext

    root = tk.Tk()
    root.title("DTF to PNT Converter")
    root.geometry("640x400")

    log = scrolledtext.ScrolledText(root, font=("Consolas", 10))
    log.pack(fill="both", expand=True, padx=8, pady=8)

    def do(paths):
        for path in collect(paths):
            try:
                out, h, n, no_z = convert(path)
                log.insert("end", f"OK {os.path.basename(path)} -> "
                                  f"{os.path.basename(out)} {n} points, "
                                  f"{no_z} without height\n")
            except Exception as e:
                log.insert("end", f"ERR {os.path.basename(path)}: {e}\n")
        log.see("end")

    bar = tk.Frame(root)
    bar.pack(pady=(0, 8))
    tk.Button(bar, text="Convert files...", width=18, command=lambda: do(
        filedialog.askopenfilenames(filetypes=[("DTF files", "*.dtf *.DTF")]))
    ).pack(side="left", padx=4)
    tk.Button(bar, text="Convert folder...", width=18, command=lambda: do(
        [d] if (d := filedialog.askdirectory()) else [])
    ).pack(side="left", padx=4)

    log.insert("end", "Choose DTF files or a folder. Each file is saved as .pnt "
                      "next to the original.\n\n")
    root.mainloop()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_cli(sys.argv[1:])
    else:
        run_gui()

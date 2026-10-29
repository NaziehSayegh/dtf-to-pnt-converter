#!/usr/bin/env python3
"""
dtf2pnt.py - Convert survey .DTF point files to .PNT text files.

Output format (one point per line, space separated):
    <point number> <X> <Y> <Z>

Usage:
    python dtf2pnt.py                                 -> opens the window (GUI)
    python dtf2pnt.py FILE.DTF [...] --out DIR        -> converts each file into DIR
    python dtf2pnt.py FOLDER --out DIR                -> converts every .DTF in the folder
    python dtf2pnt.py ... --skip-no-height            -> leave out points with Z = 0

The output folder is always chosen by you (--out is required); results are
never written next to the originals unless you pick that folder yourself.
"""
import os
import struct
import sys

APP_NAME = "DTF to PNT Converter"
APP_VERSION = "2.0"

HEADER_SIZE = 40           # bytes before the first point record
RECORD_SIZE = 20           # 8 bytes X + 8 bytes Y + 4 bytes Z


# --------------------------------------------------------------------------
# Core conversion
# --------------------------------------------------------------------------

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


def convert(path, out_dir, skip_no_height=False):
    """Convert one file into out_dir (always chosen by the user, never implied).
    Returns (out_path, header, points_written, no_height)."""
    if not out_dir:
        raise ValueError("No output folder chosen")
    header, points = read_dtf(path)
    no_z = sum(1 for p in points if abs(p[3]) < 0.005)
    if skip_no_height:
        points = [p for p in points if abs(p[3]) >= 0.005]
    base = os.path.splitext(os.path.basename(path))[0] + ".pnt"
    out_path = os.path.join(out_dir, base)
    write_pnt(points, out_path)
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


# --------------------------------------------------------------------------
# Command line
# --------------------------------------------------------------------------

def run_cli(args):
    out_dir = None
    skip = False
    paths = []
    it = iter(args)
    for a in it:
        if a == "--out":
            out_dir = next(it, None)
        elif a == "--skip-no-height":
            skip = True
        else:
            paths.append(a)
    if not out_dir:
        print("ERR: choose where to save with --out FOLDER "
              "(results are never saved next to the originals by default)")
        return
    os.makedirs(out_dir, exist_ok=True)
    for path in collect(paths):
        try:
            out, h, n, no_z = convert(path, out_dir, skip)
            print(f"OK {path} -> {out} ({n} points, {no_z} without height)"
                  f" [{h['name']} {h['info']}]")
        except Exception as e:
            print(f"ERR {path}: {e}")


# --------------------------------------------------------------------------
# Window
# --------------------------------------------------------------------------

def run_gui():
    import subprocess
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    # Palette
    NAVY = "#0F1B2D"
    NAVY_2 = "#1B2B45"
    ACCENT = "#2563EB"
    ACCENT_HOVER = "#1D4ED8"
    ACCENT_DOWN = "#1E40AF"
    BG = "#F3F5F9"
    CARD = "#FFFFFF"
    BORDER = "#DDE2EA"
    TEXT = "#111827"
    MUTED = "#6B7280"
    OK = "#15803D"
    WARN = "#B45309"
    ERR = "#B91C1C"

    import tkinter.font as tkfont
    try:                                   # optional: drag-and-drop support
        from tkinterdnd2 import DND_FILES, TkinterDnD
        root = TkinterDnD.Tk()
        dnd = True
    except Exception:
        root = tk.Tk()
        dnd = False
    families = set(tkfont.families(root))
    FONT = next((f for f in ("Segoe UI", "SF Pro Text", "Helvetica Neue", "Ubuntu",
                             "DejaVu Sans") if f in families), "TkDefaultFont")

    root.title(APP_NAME)
    root.geometry("940x640")
    root.minsize(780, 520)
    root.configure(bg=BG)

    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure(".", font=(FONT, 10), background=BG, foreground=TEXT)
    style.configure("Card.TFrame", background=CARD)
    style.configure("TFrame", background=BG)
    style.configure("Card.TLabel", background=CARD, foreground=TEXT)
    style.configure("Muted.TLabel", background=CARD, foreground=MUTED)
    style.configure("TCheckbutton", background=CARD, foreground=TEXT)
    style.map("TCheckbutton", background=[("active", CARD)])
    style.configure("TRadiobutton", background=CARD, foreground=TEXT)
    style.map("TRadiobutton", background=[("active", CARD)])

    style.configure("Primary.TButton", background=ACCENT, foreground="white",
                    borderwidth=0, focusthickness=0, padding=(22, 10),
                    font=(FONT, 10, "bold"))
    style.map("Primary.TButton",
              background=[("disabled", "#9DB5EE"), ("pressed", ACCENT_DOWN),
                          ("active", ACCENT_HOVER)],
              foreground=[("disabled", "white")])
    style.configure("Secondary.TButton", background=CARD, foreground=TEXT,
                    bordercolor=BORDER, lightcolor=CARD, darkcolor=CARD,
                    borderwidth=1, focusthickness=0, padding=(14, 8))
    style.map("Secondary.TButton",
              background=[("pressed", "#E5E9F0"), ("active", "#F3F5F9")])
    style.configure("Link.TButton", background=CARD, foreground=ACCENT,
                    borderwidth=0, focusthickness=0, padding=(6, 4))
    style.map("Link.TButton", foreground=[("active", ACCENT_HOVER)],
              background=[("active", CARD)])

    style.configure("Treeview", background=CARD, fieldbackground=CARD,
                    foreground=TEXT, rowheight=32, borderwidth=0,
                    font=(FONT, 10))
    style.configure("Treeview.Heading", background="#EEF1F6", foreground=MUTED,
                    relief="flat", padding=(10, 8), font=(FONT, 9, "bold"))
    style.map("Treeview.Heading", background=[("active", "#E5E9F0")])
    style.map("Treeview", background=[("selected", "#DBE7FF")],
              foreground=[("selected", TEXT)])
    style.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
    style.configure("Vertical.TScrollbar", background="#E5E9F0", troughcolor=CARD,
                    bordercolor=CARD, arrowcolor=MUTED, relief="flat")
    style.configure("Accent.Horizontal.TProgressbar", background=ACCENT,
                    troughcolor="#E5E9F0", borderwidth=0, thickness=6)

    # ---- Header ----------------------------------------------------------
    header = tk.Frame(root, bg=NAVY)
    header.pack(fill="x")
    badge = tk.Canvas(header, width=44, height=44, bg=NAVY, highlightthickness=0)
    badge.create_rectangle(2, 2, 42, 42, fill=ACCENT, outline="")
    badge.create_text(22, 22, text="D→P", fill="white", font=(FONT, 11, "bold"))
    badge.pack(side="left", padx=(24, 14), pady=18)
    titles = tk.Frame(header, bg=NAVY)
    titles.pack(side="left", pady=16)
    tk.Label(titles, text=APP_NAME, bg=NAVY, fg="white",
             font=(FONT, 16, "bold")).pack(anchor="w")
    tk.Label(titles, text="Survey .DTF point files  →  .PNT text files",
             bg=NAVY, fg="#9FB0CC", font=(FONT, 10)).pack(anchor="w")
    tk.Label(header, text=f"v{APP_VERSION}", bg=NAVY, fg="#6F84A8",
             font=(FONT, 9)).pack(side="right", padx=24)
    tk.Frame(root, bg=NAVY_2, height=3).pack(fill="x")

    body = ttk.Frame(root)
    body.pack(fill="both", expand=True, padx=24, pady=(18, 0))

    # ---- Toolbar card ----------------------------------------------------
    def card(parent):
        return tk.Frame(parent, bg=CARD, highlightthickness=1,
                        highlightbackground=BORDER, highlightcolor=BORDER)

    bar = card(body)
    bar.pack(fill="x")
    inner = ttk.Frame(bar, style="Card.TFrame")
    inner.pack(fill="x", padx=16, pady=14)

    ttk.Button(inner, text="＋  Add files", style="Secondary.TButton",
               command=lambda: add_paths(filedialog.askopenfilenames(
                   title="Choose DTF files",
                   filetypes=[("DTF files", "*.dtf *.DTF"), ("All files", "*.*")]))
               ).pack(side="left")
    ttk.Button(inner, text="Add folder", style="Secondary.TButton",
               command=lambda: add_paths(
                   [d] if (d := filedialog.askdirectory(title="Choose a folder")) else [])
               ).pack(side="left", padx=(8, 0))
    ttk.Button(inner, text="Clear list", style="Link.TButton",
               command=lambda: clear()).pack(side="left", padx=(8, 0))
    convert_btn = ttk.Button(inner, text="Convert all", style="Primary.TButton",
                             command=lambda: run_all())
    convert_btn.pack(side="right")

    # ---- Options ---------------------------------------------------------
    opts = card(body)
    opts.pack(fill="x", pady=(10, 0))
    oi = ttk.Frame(opts, style="Card.TFrame")
    oi.pack(fill="x", padx=16, pady=12)

    out_dir = tk.StringVar(value="")
    skip_var = tk.BooleanVar(value=False)

    ttk.Label(oi, text="Save results to", style="Card.TLabel",
              font=(FONT, 10, "bold")).grid(row=0, column=0, sticky="w")
    out_label = ttk.Label(oi, style="Muted.TLabel",
                          text="You will choose the folder when you click Convert")
    out_label.grid(row=0, column=1, sticky="w", padx=(18, 0))
    oi.columnconfigure(1, weight=1)

    def choose_out():
        d = filedialog.askdirectory(
            title="Choose where to save the .PNT files",
            initialdir=out_dir.get() or None, mustexist=False)
        if d:
            out_dir.set(d)
            out_label.configure(text=d)
        return d
    ttk.Button(oi, text="Choose folder…", style="Secondary.TButton",
               command=choose_out).grid(row=0, column=2, sticky="e")
    ttk.Checkbutton(oi, text="Leave out points without height (Z = 0)",
                    variable=skip_var).grid(row=1, column=0, columnspan=3,
                                            sticky="w", pady=(10, 0))

    # ---- File table ------------------------------------------------------
    table_card = card(body)
    table_card.pack(fill="both", expand=True, pady=(10, 0))

    cols = ("file", "job", "date", "points", "noz", "status")
    tree = ttk.Treeview(table_card, columns=cols, show="headings",
                        selectmode="extended")
    heads = {"file": ("File", 190, "w"), "job": ("Job name", 130, "w"),
             "date": ("Date / place", 170, "w"), "points": ("Points", 70, "e"),
             "noz": ("No height", 100, "e"), "status": ("Status", 190, "w")}
    for c, (t, w, a) in heads.items():
        tree.heading(c, text=t, anchor=a)
        tree.column(c, width=w, anchor=a, stretch=(c in ("file", "status")))
    sb = ttk.Scrollbar(table_card, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=sb.set)
    sb.pack(side="right", fill="y")
    tree.pack(fill="both", expand=True)
    tree.tag_configure("ok", foreground=TEXT)
    tree.tag_configure("err", foreground=ERR)
    tree.tag_configure("ready", foreground=TEXT)
    tree.tag_configure("odd", background="#FAFBFD")

    empty = tk.Label(table_card, bg=CARD, fg=MUTED, justify="center",
                     font=(FONT, 11),
                     text="No files yet\n\n" + ("Drag and drop .DTF files or folders here,\nor use " if dnd else "Use ")
                          + "“Add files” / “Add folder”.\nResults are saved as .PNT files.")
    empty.place(relx=0.5, rely=0.5, anchor="center")

    # ---- Footer ----------------------------------------------------------
    foot = ttk.Frame(root)
    foot.pack(fill="x", padx=24, pady=14)
    status = tk.StringVar(value="Ready")
    tk.Label(foot, textvariable=status, bg=BG, fg=MUTED,
             font=(FONT, 10)).pack(side="left")
    open_btn = ttk.Button(foot, text="Open output folder", style="Link.TButton",
                          command=lambda: open_out())
    progress = ttk.Progressbar(foot, style="Accent.Horizontal.TProgressbar",
                               length=180, mode="determinate")

    state = {"files": {}, "last_dir": None}   # iid -> path

    def refresh_empty():
        if state["files"]:
            empty.place_forget()
        else:
            empty.place(relx=0.5, rely=0.5, anchor="center")

    def stripe():
        for i, iid in enumerate(tree.get_children()):
            tags = set(tree.item(iid, "tags")) - {"odd"}
            if i % 2:
                tags.add("odd")
            tree.item(iid, tags=tuple(tags))

    def add_paths(paths):
        known = set(state["files"].values())
        for path in collect(list(paths)):
            if path in known:
                continue
            known.add(path)
            name = os.path.basename(path)
            try:
                h, pts = read_dtf(path)
                no_z = sum(1 for p in pts if abs(p[3]) < 0.005)
                iid = tree.insert("", "end", tags=("ready",), values=(
                    name, h["name"], h["info"], len(pts), no_z, "Ready"))
            except Exception as e:
                iid = tree.insert("", "end", tags=("err",), values=(
                    name, "", "", "", "", f"Cannot read: {e}"))
            state["files"][iid] = path
        refresh_empty()
        stripe()
        n = len(state["files"])
        status.set(f"{n} file{'s' if n != 1 else ''} ready" if n else "Ready")

    def clear():
        tree.delete(*tree.get_children())
        state["files"].clear()
        state["last_dir"] = None
        open_btn.pack_forget()
        refresh_empty()
        status.set("Ready")

    def run_all():
        if not state["files"]:
            messagebox.showinfo(APP_NAME, "Add some DTF files first.")
            return
        target = choose_out()          # always ask where to save
        if not target:
            status.set("Cancelled — no output folder chosen")
            return
        os.makedirs(target, exist_ok=True)
        convert_btn.state(["disabled"])
        progress.pack(side="right")
        progress.configure(maximum=len(state["files"]), value=0)
        done = failed = total_pts = 0
        for iid, path in state["files"].items():
            try:
                out, h, n, no_z = convert(path, target, skip_var.get())
                tree.item(iid, tags=("ok",))
                tree.set(iid, "status", f"✓ Saved {os.path.basename(out)} ({n} pts)")
                total_pts += n
                done += 1
                state["last_dir"] = os.path.dirname(out)
            except Exception as e:
                tree.item(iid, tags=("err",))
                tree.set(iid, "status", f"✗ {e}")
                failed += 1
            progress.step(1)
            root.update_idletasks()
        stripe()
        progress.pack_forget()
        convert_btn.state(["!disabled"])
        msg = f"Done — {done} file{'s' if done != 1 else ''} converted, {total_pts} points"
        if failed:
            msg += f", {failed} failed"
        status.set(msg)
        if state["last_dir"]:
            open_btn.pack(side="right", padx=(0, 12))

    def open_out():
        d = state["last_dir"]
        if not d:
            return
        if sys.platform.startswith("win"):
            os.startfile(d)                       # noqa: B606
        elif sys.platform == "darwin":
            subprocess.Popen(["open", d])
        else:
            subprocess.Popen(["xdg-open", d])

    if dnd:
        def on_drop(event):
            add_paths(root.tk.splitlist(event.data))
            return event.action
        for w in (root, tree, empty, table_card):
            w.drop_target_register(DND_FILES)
            w.dnd_bind("<<Drop>>", on_drop)

    root.bind("<Delete>", lambda e: [
        (state["files"].pop(i, None), tree.delete(i)) for i in tree.selection()
    ] and (refresh_empty(), stripe()))

    root.mainloop()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_cli(sys.argv[1:])
    else:
        run_gui()

#!/usr/bin/env python3
"""
PPM3 GUI — Positioning of Proteins in Membranes (v3.0)
macOS M2 compatible. Pure stdlib — no pip installs needed.

Launch:
    python3 ppm3_gui.py
"""

import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
import subprocess, threading, os, sys, shutil
from pathlib import Path
from datetime import datetime
from html import escape
import re

# ── Membrane types ─────────────────────────────────────────────────────────────
MEMBRANE_CODES = [
    ("   ", "Undefined membrane"),
    ("PMm", "Plasma membrane (mammalian)"),
    ("PMp", "Plasma membrane (plants)"),
    ("PMf", "Plasma membrane (fungi)"),
    ("Erf", "ER (fungi)"),
    ("ERm", "ER (mammalian)"),
    ("GOL", "Golgi membrane"),
    ("LYS", "Lysosome membrane"),
    ("END", "Endosome membrane"),
    ("VAC", "Vacuole membrane"),
    ("MOM", "Outer mitochondrial membrane"),
    ("MIM", "Inner mitochondrial membrane"),
    ("THp", "Thylakoid membrane (plants)"),
    ("THb", "Thylakoid membrane (bacteria)"),
    ("GnO", "Gram-negative bacteria outer membrane"),
    ("GnI", "Gram-negative bacteria inner membrane"),
    ("GpI", "Gram-positive bacteria inner membrane"),
    ("ARC", "Archaebacteria cell membrane"),
    ("LPC", "DLPC (diC12:0 PC) bilayer"),
    ("MPC", "DMPC (diC14:0 PC) bilayer"),
    ("OPC", "DOPC (diC18:1 PC) bilayer"),
    ("EPC", "DEuPC (diC22:1 PC) bilayer"),
    ("MIC", "DPC (C12PC) micelle"),
]
MEM_DISPLAY = [f"{code}  —  {name}" for code, name in MEMBRANE_CODES]
MEM_TO_CODE = {d: code for (code, _), d in zip(MEMBRANE_CODES, MEM_DISPLAY)}

# ── Colours ────────────────────────────────────────────────────────────────────
C = dict(
    bg      = "#1a1b26",
    panel   = "#24253a",
    card    = "#2d2f45",
    entry   = "#1f2133",
    border  = "#414268",
    accent  = "#7aa2f7",
    green   = "#9ece6a",
    red     = "#f7768e",
    orange  = "#e0af68",
    text    = "#c0caf5",
    dim     = "#565f89",
)

MAC = sys.platform == "darwin"
F = dict(
    h1    = ("SF Pro Display" if MAC else "Helvetica", 15, "bold"),
    h2    = ("SF Pro Display" if MAC else "Helvetica", 12, "bold"),
    body  = ("SF Pro Text"    if MAC else "Helvetica", 12),
    small = ("SF Pro Text"    if MAC else "Helvetica", 10),
    mono  = ("SF Mono"        if MAC else "Courier",   11),
)


def apply_ttk_style():
    s = ttk.Style()
    try:
        s.theme_use("clam")
    except Exception:
        pass
    s.configure("TCombobox",
                 fieldbackground=C["entry"],
                 background=C["entry"],
                 foreground=C["text"],
                 selectbackground=C["accent"],
                 selectforeground=C["bg"],
                 arrowcolor=C["text"],
                 borderwidth=0)
    s.map("TCombobox",
          fieldbackground=[("readonly", C["entry"])],
          foreground=[("readonly", C["text"])],
          background=[("readonly", C["entry"])])
    s.configure("Horizontal.TProgressbar",
                 troughcolor=C["panel"],
                 background=C["accent"],
                 borderwidth=0)


# ── Single-membrane card ───────────────────────────────────────────────────────

class SingleMemCard(tk.Frame):
    """
    Card for one protein with one membrane.
    Each field is on its own clearly-labelled row — nothing hidden.
    """
    def __init__(self, parent, index, remove_cb):
        super().__init__(parent, bg=C["card"],
                         highlightbackground=C["accent"],
                         highlightthickness=1)
        self._index     = index
        self._remove_cb = remove_cb
        self._pdb       = tk.StringVar()
        self._het       = tk.IntVar(value=0)
        self._mem       = tk.StringVar(value=MEM_DISPLAY[0])
        self._topo      = tk.StringVar(value="out")
        self._build()

    def _build(self):
        # ── stripe + header ───────────────────────────────────────────────────
        tk.Frame(self, bg=C["accent"], height=3).pack(fill="x")
        hdr = tk.Frame(self, bg=C["card"])
        hdr.pack(fill="x", padx=12, pady=(6, 4))
        self._title_lbl = tk.Label(hdr, text=f"Protein #{self._index + 1}",
                                   font=F["h2"], fg=C["accent"], bg=C["card"])
        self._title_lbl.pack(side="left")
        tk.Button(hdr, text="✕  Remove", command=self._remove_cb,
                  bg=C["card"], fg=C["red"], relief="flat",
                  font=F["small"], cursor="hand2", bd=0).pack(side="right")

        body = tk.Frame(self, bg=C["card"])
        body.pack(fill="x", padx=14, pady=(2, 12))

        # ── Row 1: PDB file ────────────────────────────────────────────────────
        r = tk.Frame(body, bg=C["card"])
        r.pack(fill="x", pady=4)
        tk.Label(r, text="PDB file:", font=F["small"],
                 fg=C["dim"], bg=C["card"],
                 width=18, anchor="e").pack(side="left", padx=(0, 8))
        tk.Entry(r, textvariable=self._pdb,
                 bg=C["entry"], fg=C["text"],
                 insertbackground=C["text"],
                 relief="flat", font=F["mono"], bd=4
                 ).pack(side="left", fill="x", expand=True)
        tk.Button(r, text="  Browse…  ",
                  command=self._browse_pdb,
                  bg=C["border"], fg=C["text"], relief="flat",
                  font=F["small"], cursor="hand2", bd=0,
                  padx=4, pady=3).pack(side="left", padx=(6, 0))

        # ── Row 2: Heteroatoms ─────────────────────────────────────────────────
        r = tk.Frame(body, bg=C["card"])
        r.pack(fill="x", pady=4)
        tk.Label(r, text="Heteroatoms:", font=F["small"],
                 fg=C["dim"], bg=C["card"],
                 width=18, anchor="e").pack(side="left", padx=(0, 8))
        tk.Checkbutton(r, text="Include non-solvent heteroatoms",
                       variable=self._het,
                       bg=C["card"], fg=C["text"],
                       selectcolor=C["card"],
                       activebackground=C["card"],
                       font=F["body"]).pack(side="left")

        # ── Row 3: Membrane type (full-width combobox) ─────────────────────────
        r = tk.Frame(body, bg=C["card"])
        r.pack(fill="x", pady=4)
        tk.Label(r, text="Membrane type:", font=F["small"],
                 fg=C["dim"], bg=C["card"],
                 width=18, anchor="e").pack(side="left", padx=(0, 8))
        # Use pack + fill="x" so the combobox stretches
        cb_frame = tk.Frame(r, bg=C["card"])
        cb_frame.pack(side="left", fill="x", expand=True)
        self._mem_cb = ttk.Combobox(cb_frame,
                                     textvariable=self._mem,
                                     values=MEM_DISPLAY,
                                     state="readonly",
                                     font=F["small"])
        self._mem_cb.pack(fill="x")

        # ── Row 4: N-terminus topology (radio buttons) ─────────────────────────
        r = tk.Frame(body, bg=C["card"])
        r.pack(fill="x", pady=4)
        tk.Label(r, text="N-term topology:", font=F["small"],
                 fg=C["dim"], bg=C["card"],
                 width=18, anchor="e").pack(side="left", padx=(0, 8))
        topo_wrap = tk.Frame(r, bg=C["card"])
        topo_wrap.pack(side="left", fill="x", expand=True)
        for val, desc in [
            ("in",  "in  (N-terminus faces inside membrane)"),
            ("out", "out  (N-terminus faces outside membrane)"),
        ]:
            tk.Radiobutton(topo_wrap, text=desc,
                           variable=self._topo, value=val,
                           bg=C["card"], fg=C["text"],
                           selectcolor=C["card"],
                           activebackground=C["card"],
                           anchor="w",
                           font=F["body"]).pack(anchor="w")

    def _browse_pdb(self):
        p = filedialog.askopenfilename(
            title="Select PDB file",
            filetypes=[("PDB files", "*.pdb"), ("All files", "*.*")])
        if p:
            self._pdb.set(p)

    def get_pdb_path(self):
        return self._pdb.get().strip()

    def set_index(self, i):
        self._index = i
        self._title_lbl.config(text=f"Protein #{self._index + 1}")

    def to_inp_line(self):
        het  = self._het.get()
        code = MEM_TO_CODE.get(self._mem.get(), "MOM").strip() or "MOM"
        topo = self._topo.get().strip()
        pdb  = os.path.basename(self._pdb.get().strip())
        # opm.f reads this with fixed format: (i2,1x,2(a3,1x),a80)
        # Keep topology as width-3 to avoid eating the first char of filename.
        return f"{het:2d} {code:<3} {topo:<3} {pdb}"


# ── Sub-membrane block (inside DualMemCard) ────────────────────────────────────

class MemSubBlock(tk.Frame):
    def __init__(self, parent, index, remove_cb):
        super().__init__(parent, bg=C["entry"],
                         highlightbackground=C["border"],
                         highlightthickness=1)
        self._index     = index
        self._remove_cb = remove_cb
        self._mem       = tk.StringVar(value=MEM_DISPLAY[0])
        self._shape     = tk.StringVar(value="planar")
        self._topo      = tk.StringVar(value="in")
        self._chains    = tk.StringVar()
        self._build()

    def set_index(self, i):
        self._index = i
        self._title_lbl.config(text=f"  Membrane {i + 1}")

    def _build(self):
        tk.Frame(self, bg=C["green"], height=2).pack(fill="x")
        hdr = tk.Frame(self, bg=C["entry"])
        hdr.pack(fill="x", padx=10, pady=(6, 2))
        self._title_lbl = tk.Label(hdr,
                                    text=f"  Membrane {self._index + 1}",
                                    font=F["h2"], fg=C["green"],
                                    bg=C["entry"])
        self._title_lbl.pack(side="left")
        tk.Button(hdr, text="✕", command=lambda: self._remove_cb(self),
                  bg=C["entry"], fg=C["red"], relief="flat",
                  font=F["small"], cursor="hand2", bd=0).pack(side="right")

        pad = tk.Frame(self, bg=C["entry"])
        pad.pack(fill="x", padx=12, pady=(0, 10))

        # Membrane type
        r = tk.Frame(pad, bg=C["entry"])
        r.pack(fill="x", pady=3)
        tk.Label(r, text="Membrane type:", font=F["small"],
                 fg=C["dim"], bg=C["entry"],
                 width=18, anchor="e").pack(side="left", padx=(0, 8))
        cb_wrap = tk.Frame(r, bg=C["entry"])
        cb_wrap.pack(side="left", fill="x", expand=True)
        ttk.Combobox(cb_wrap, textvariable=self._mem,
                     values=MEM_DISPLAY, state="readonly",
                     font=F["small"]).pack(fill="x")

        # Shape
        r = tk.Frame(pad, bg=C["entry"])
        r.pack(fill="x", pady=3)
        tk.Label(r, text="Membrane shape:", font=F["small"],
                 fg=C["dim"], bg=C["entry"],
                 width=18, anchor="e").pack(side="left", padx=(0, 8))
        for val in ["planar", "curved"]:
            tk.Radiobutton(r, text=val.capitalize(),
                           variable=self._shape, value=val,
                           bg=C["entry"], fg=C["text"],
                           selectcolor=C["entry"],
                           activebackground=C["entry"],
                           font=F["body"]).pack(side="left", padx=(0, 20))

        # N-term topology
        r = tk.Frame(pad, bg=C["entry"])
        r.pack(fill="x", pady=3)
        tk.Label(r, text="N-term topology:", font=F["small"],
                 fg=C["dim"], bg=C["entry"],
                 width=18, anchor="e").pack(side="left", padx=(0, 8))
        for val, desc in [("in", "in"), ("out", "out")]:
            tk.Radiobutton(r, text=desc,
                           variable=self._topo, value=val,
                           bg=C["entry"], fg=C["text"],
                           selectcolor=C["entry"],
                           activebackground=C["entry"],
                           font=F["body"]).pack(side="left", padx=(0, 20))

        # Chain IDs
        r = tk.Frame(pad, bg=C["entry"])
        r.pack(fill="x", pady=3)
        tk.Label(r, text="Chain IDs:", font=F["small"],
                 fg=C["dim"], bg=C["entry"],
                 width=18, anchor="e").pack(side="left", padx=(0, 8))
        tk.Entry(r, textvariable=self._chains,
                 bg=C["panel"], fg=C["text"],
                 insertbackground=C["text"],
                 relief="flat", font=F["mono"], bd=4,
                 width=20).pack(side="left")
        tk.Label(r, text="  comma-separated, e.g.  A,B,C",
                 font=F["small"], fg=C["dim"],
                 bg=C["entry"]).pack(side="left")

    def to_lines(self):
        code  = MEM_TO_CODE.get(self._mem.get(), "MOM").strip() or "MOM"
        lines = [code, self._shape.get(), self._topo.get()]
        ch    = self._chains.get().strip()
        # opm.f always reads an extra free-form line for subunit chain IDs.
        # Keep a placeholder blank line when no chains are provided.
        lines.append(ch)
        return lines


# ── Dual-membrane card ─────────────────────────────────────────────────────────

class DualMemCard(tk.Frame):
    def __init__(self, parent, index, remove_cb):
        super().__init__(parent, bg=C["card"],
                         highlightbackground=C["green"],
                         highlightthickness=1)
        self._index     = index
        self._remove_cb = remove_cb
        self._pdb       = tk.StringVar()
        self._het       = tk.StringVar(value="no")
        self._subs      = []
        self._build()

    def _build(self):
        tk.Frame(self, bg=C["green"], height=3).pack(fill="x")
        hdr = tk.Frame(self, bg=C["card"])
        hdr.pack(fill="x", padx=12, pady=(6, 4))
        self._title_lbl = tk.Label(hdr, text=f"Protein #{self._index + 1}",
                                   font=F["h2"], fg=C["green"], bg=C["card"])
        self._title_lbl.pack(side="left")
        tk.Button(hdr, text="✕  Remove", command=self._remove_cb,
                  bg=C["card"], fg=C["red"], relief="flat",
                  font=F["small"], cursor="hand2", bd=0).pack(side="right")

        body = tk.Frame(self, bg=C["card"])
        body.pack(fill="x", padx=14, pady=(2, 4))

        # PDB file
        r = tk.Frame(body, bg=C["card"])
        r.pack(fill="x", pady=4)
        tk.Label(r, text="PDB file:", font=F["small"],
                 fg=C["dim"], bg=C["card"],
                 width=18, anchor="e").pack(side="left", padx=(0, 8))
        tk.Entry(r, textvariable=self._pdb,
                 bg=C["entry"], fg=C["text"],
                 insertbackground=C["text"],
                 relief="flat", font=F["mono"], bd=4
                 ).pack(side="left", fill="x", expand=True)
        tk.Button(r, text="  Browse…  ",
                  command=self._browse,
                  bg=C["border"], fg=C["text"], relief="flat",
                  font=F["small"], cursor="hand2", bd=0,
                  padx=4, pady=3).pack(side="left", padx=(6, 0))

        # Heteroatoms
        r = tk.Frame(body, bg=C["card"])
        r.pack(fill="x", pady=4)
        tk.Label(r, text="Heteroatoms:", font=F["small"],
                 fg=C["dim"], bg=C["card"],
                 width=18, anchor="e").pack(side="left", padx=(0, 8))
        tk.Checkbutton(r, text="Include non-solvent heteroatoms",
                       variable=self._het, onvalue="yes", offvalue="no",
                       bg=C["card"], fg=C["text"],
                       selectcolor=C["card"],
                       activebackground=C["card"],
                       font=F["body"]).pack(side="left")

        # Sub-membrane container
        self._sub_cont = tk.Frame(body, bg=C["card"])
        self._sub_cont.pack(fill="x", pady=(8, 4))

        tk.Button(body, text="＋  Add Membrane",
                  command=self._add_sub,
                  bg=C["border"], fg=C["text"],
                  relief="flat", font=F["small"],
                  cursor="hand2", bd=0, padx=8, pady=4
                  ).pack(anchor="w", pady=(4, 8))

        self._add_sub()
        self._add_sub()

    def _browse(self):
        p = filedialog.askopenfilename(
            title="Select PDB file",
            filetypes=[("PDB files", "*.pdb"), ("All files", "*.*")])
        if p:
            self._pdb.set(p)

    def _add_sub(self):
        if len(self._subs) >= 2:
            messagebox.showinfo("Limit", "Maximum 2 membranes per protein.")
            return
        idx = len(self._subs)
        sub = MemSubBlock(self._sub_cont, idx, remove_cb=self._remove_sub)
        sub.pack(fill="x", pady=4)
        self._subs.append(sub)

    def _remove_sub(self, sub):
        if len(self._subs) <= 1:
            messagebox.showinfo("Info", "At least one membrane is required.")
            return
        if sub not in self._subs:
            return
        self._subs.remove(sub)
        sub.destroy()
        for i, s in enumerate(self._subs):
            s.set_index(i)

    def get_pdb_path(self):
        return self._pdb.get().strip()

    def set_index(self, i):
        self._index = i
        self._title_lbl.config(text=f"Protein #{self._index + 1}")

    def to_inp_block(self):
        pdb  = os.path.basename(self._pdb.get().strip())
        het  = self._het.get()
        lines = [het, pdb, str(len(self._subs))]
        for s in self._subs:
            lines.extend(s.to_lines())
        return "\n".join(lines)


# ── Main Application ───────────────────────────────────────────────────────────

class PPM3App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PPM 3.0  —  Protein Membrane Positioning")
        self.configure(bg=C["bg"])
        self.geometry("1200x880")
        self.minsize(980, 700)

        self._immers  = tk.StringVar()
        self._reslib  = tk.StringVar()
        self._workdir = tk.StringVar(value=str(Path.home()))
        self._mode    = tk.IntVar(value=1)
        self._cards   = []
        self._bulk_pdbs = []
        self._bulk_active = False
        self._bulk_mem = tk.StringVar(value=MEM_DISPLAY[9])  # MOM default
        self._bulk_het = tk.IntVar(value=1)
        self._bulk_topo = tk.StringVar(value="out")
        self._bulk_mem1 = tk.StringVar(value=MEM_DISPLAY[9])
        self._bulk_shape1 = tk.StringVar(value="planar")
        self._bulk_topo1 = tk.StringVar(value="in")
        self._bulk_mem2 = tk.StringVar(value=MEM_DISPLAY[9])
        self._bulk_shape2 = tk.StringVar(value="planar")
        self._bulk_topo2 = tk.StringVar(value="in")
        self._running = False
        self._proc    = None
        self._last_run_dir = ""
        self._run_output_lines = []

        apply_ttk_style()
        self._build()
        self._auto_detect()

    def _auto_detect(self):
        p = shutil.which("immers")
        if p:
            self._immers.set(p)

    # ── Root layout ────────────────────────────────────────────────────────────
    def _build(self):
        top = tk.Frame(self, bg="#0f0f17", pady=10, padx=18)
        top.pack(fill="x")
        tk.Label(top, text="⬡  PPM 3.0",
                 bg="#0f0f17", fg=C["accent"], font=F["h1"]).pack(side="left")
        tk.Label(top,
                 text="Positioning of Proteins in Membranes",
                 bg="#0f0f17", fg=C["dim"], font=F["small"]).pack(side="left", padx=14)

        pw = tk.PanedWindow(self, orient="horizontal",
                            bg=C["bg"], sashrelief="flat", sashwidth=5)
        pw.pack(fill="both", expand=True)

        left  = tk.Frame(pw, bg=C["bg"])
        right = tk.Frame(pw, bg=C["bg"])
        pw.add(left,  minsize=580)
        pw.add(right, minsize=400)

        self._build_left(left)
        self._build_right(right)

    # ── Left panel (scrollable) ────────────────────────────────────────────────
    def _build_left(self, parent):
        canvas = tk.Canvas(parent, bg=C["bg"], highlightthickness=0)
        sb = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        self._left_body = tk.Frame(canvas, bg=C["bg"])
        win_id = canvas.create_window((0, 0), window=self._left_body, anchor="nw")

        self._left_body.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind(
            "<Configure>",
            lambda e: canvas.itemconfig(win_id, width=e.width))
        # macOS trackpad scroll
        canvas.bind_all(
            "<MouseWheel>",
            lambda e: canvas.yview_scroll(-(e.delta // 120), "units"))

        self._build_paths(self._left_body)
        self._build_mode(self._left_body)
        self._build_jobs(self._left_body)
        self._build_run(self._left_body)

    # ── Paths section ──────────────────────────────────────────────────────────
    def _build_paths(self, parent):
        wrap = tk.Frame(parent, bg=C["bg"])
        wrap.pack(fill="x", padx=16, pady=(16, 6))

        tk.Label(wrap, text="⚙  Setup", font=F["h2"],
                 fg=C["accent"], bg=C["bg"]).pack(anchor="w", pady=(0, 6))

        card = tk.Frame(wrap, bg=C["panel"],
                        highlightbackground=C["border"], highlightthickness=1)
        card.pack(fill="x")
        g = tk.Frame(card, bg=C["panel"])
        g.pack(fill="x", padx=14, pady=12)

        def path_row(row, lbl_text, var, is_dir=False, ft=None):
            tk.Label(g, text=lbl_text, font=F["small"],
                     fg=C["dim"], bg=C["panel"],
                     width=22, anchor="e"
                     ).grid(row=row, column=0, padx=(0, 8), pady=5, sticky="e")
            tk.Entry(g, textvariable=var,
                     bg=C["entry"], fg=C["text"],
                     insertbackground=C["text"],
                     relief="flat", font=F["mono"], bd=4
                     ).grid(row=row, column=1, pady=5, sticky="ew", padx=(0, 6))

            def _browse(v=var, d=is_dir, f=ft):
                p = (filedialog.askdirectory(title="Select folder") if d
                     else filedialog.askopenfilename(
                         filetypes=f or [("All files", "*.*")]))
                if p:
                    v.set(p)

            tk.Button(g, text="Browse…", command=_browse,
                      bg=C["border"], fg=C["text"], relief="flat",
                      font=F["small"], cursor="hand2", bd=0,
                      padx=6, pady=3).grid(row=row, column=2, pady=5)

        path_row(0, "immers executable:", self._immers,
                 ft=[("All files", "*.*")])
        path_row(1, "res.lib library:",   self._reslib,
                 ft=[("Library", "*.lib"), ("All", "*.*")])
        path_row(2, "Working directory:", self._workdir, is_dir=True)
        g.columnconfigure(1, weight=1)

        extra = tk.Frame(g, bg=C["panel"])
        extra.grid(row=3, column=0, columnspan=3, sticky="w", pady=(8, 0))
        tk.Button(extra, text="🔨  Compile from source…",
                  command=self._compile_dialog,
                  bg=C["border"], fg=C["text"], relief="flat",
                  font=F["small"], cursor="hand2", bd=0,
                  padx=8, pady=4).pack(side="left")
        tk.Label(extra, text="  requires gfortran",
                 font=F["small"], fg=C["dim"],
                 bg=C["panel"]).pack(side="left")

    # ── Mode section ───────────────────────────────────────────────────────────
    def _build_mode(self, parent):
        wrap = tk.Frame(parent, bg=C["bg"])
        wrap.pack(fill="x", padx=16, pady=6)
        tk.Label(wrap, text="🧬  Input Mode", font=F["h2"],
                 fg=C["accent"], bg=C["bg"]).pack(anchor="w", pady=(0, 6))
        card = tk.Frame(wrap, bg=C["panel"],
                        highlightbackground=C["border"], highlightthickness=1)
        card.pack(fill="x")
        inner = tk.Frame(card, bg=C["panel"])
        inner.pack(fill="x", padx=14, pady=10)
        for val, text in [
            (1, "Single membrane  —  one membrane per protein"),
            (2, "Two membranes  —  up to 2 independent membranes per protein"),
        ]:
            tk.Radiobutton(inner, text=text,
                           variable=self._mode, value=val,
                           command=self._switch_mode,
                           bg=C["panel"], fg=C["text"],
                           selectcolor=C["panel"],
                           activebackground=C["panel"],
                           font=F["body"]).pack(anchor="w", pady=3)

    # ── Jobs section ───────────────────────────────────────────────────────────
    def _build_jobs(self, parent):
        wrap = tk.Frame(parent, bg=C["bg"])
        wrap.pack(fill="x", padx=16, pady=6)

        hdr = tk.Frame(wrap, bg=C["bg"])
        hdr.pack(fill="x", pady=(0, 8))
        tk.Label(hdr, text="📂  Protein Jobs", font=F["h2"],
                 fg=C["accent"], bg=C["bg"]).pack(side="left")

        btn_frame = tk.Frame(hdr, bg=C["bg"])
        btn_frame.pack(side="right")
        tk.Button(btn_frame, text="📁  Import PDB Folder",
                  command=self._import_pdb_folder,
                  bg=C["border"], fg=C["text"], relief="flat",
                  font=F["small"], cursor="hand2", bd=0,
                  padx=8, pady=4).pack(side="right", padx=(6, 0))
        tk.Button(btn_frame, text="📄  Select PDB File(s)",
                  command=self._import_pdb_files,
                  bg=C["border"], fg=C["text"], relief="flat",
                  font=F["small"], cursor="hand2", bd=0,
                  padx=8, pady=4).pack(side="right", padx=(6, 0))
        tk.Button(btn_frame, text="Clear All",
                  command=self._clear_cards,
                  bg=C["border"], fg=C["text"], relief="flat",
                  font=F["small"], cursor="hand2", bd=0,
                  padx=8, pady=4).pack(side="right", padx=(6, 0))
        tk.Button(btn_frame, text="＋  Add Protein",
                  command=self._add_card,
                  bg=C["accent"], fg=C["bg"], relief="flat",
                  font=F["body"], cursor="hand2", bd=0,
                  padx=10, pady=4).pack(side="right")

        self._card_cont = tk.Frame(wrap, bg=C["bg"])
        self._card_cont.pack(fill="x")

        bulk = tk.Frame(wrap, bg=C["panel"],
                        highlightbackground=C["border"], highlightthickness=1)
        bulk.pack(fill="x", pady=(6, 0))
        self._batch_panel = bulk
        self._batch_cfg = tk.Frame(bulk, bg=C["panel"])
        self._batch_cfg.pack(fill="x", padx=12, pady=10)
        self._bulk_info = tk.StringVar(value="No batch folder imported.")
        tk.Label(self._batch_cfg, textvariable=self._bulk_info, bg=C["panel"], fg=C["dim"],
                 font=F["small"]).grid(row=2, column=0, columnspan=3, sticky="w", pady=(6, 0))
        self._render_batch_controls()

        self._add_card()
        self._refresh_jobs_layout()

    def _refresh_jobs_layout(self):
        if self._bulk_active:
            if self._card_cont.winfo_ismapped():
                self._card_cont.pack_forget()
            if not self._batch_panel.winfo_ismapped():
                self._batch_panel.pack(fill="x", pady=(6, 0))
        else:
            if not self._card_cont.winfo_ismapped():
                self._card_cont.pack(fill="x")
            if self._batch_panel.winfo_ismapped():
                self._batch_panel.pack_forget()

    # ── Run section ────────────────────────────────────────────────────────────
    def _build_run(self, parent):
        wrap = tk.Frame(parent, bg=C["bg"])
        wrap.pack(fill="x", padx=16, pady=(6, 18))
        tk.Label(wrap, text="▶  Run", font=F["h2"],
                 fg=C["accent"], bg=C["bg"]).pack(anchor="w", pady=(0, 6))
        card = tk.Frame(wrap, bg=C["panel"],
                        highlightbackground=C["border"], highlightthickness=1)
        card.pack(fill="x")
        inner = tk.Frame(card, bg=C["panel"])
        inner.pack(fill="x", padx=14, pady=12)

        row = tk.Frame(inner, bg=C["panel"])
        row.pack(fill="x")
        self._run_btn = tk.Button(row, text="▶  Run PPM3",
                                   command=self._run,
                                   bg=C["accent"], fg=C["bg"],
                                   relief="flat", font=F["body"],
                                   cursor="hand2", bd=0,
                                   padx=16, pady=7)
        self._run_btn.pack(side="left", padx=(0, 10))
        self._stop_btn = tk.Button(row, text="⏹  Stop",
                                    command=self._stop,
                                    bg=C["red"], fg=C["bg"],
                                    relief="flat", font=F["body"],
                                    cursor="hand2", bd=0,
                                    padx=12, pady=7, state="disabled")
        self._stop_btn.pack(side="left")

        self._status = tk.StringVar(value="Ready.")
        tk.Label(inner, textvariable=self._status,
                 font=F["small"], fg=C["dim"],
                 bg=C["panel"], anchor="w").pack(fill="x", pady=(8, 2))
        self._prog = ttk.Progressbar(inner, mode="indeterminate",
                                      style="Horizontal.TProgressbar")
        self._prog.pack(fill="x")

    # ── Right panel (console + results) ───────────────────────────────────────
    def _build_right(self, parent):
        hdr = tk.Frame(parent, bg=C["bg"], padx=12, pady=10)
        hdr.pack(fill="x")
        tk.Label(hdr, text="📋  Console Output",
                 font=F["h2"], fg=C["accent"], bg=C["bg"]).pack(side="left")
        tk.Button(hdr, text="Save Log…",
                  command=self._save_log,
                  bg=C["border"], fg=C["text"], relief="flat",
                  font=F["small"], cursor="hand2", bd=0,
                  padx=6, pady=3).pack(side="right")
        tk.Button(hdr, text="Clear",
                  command=self._clear_log,
                  bg=C["border"], fg=C["text"], relief="flat",
                  font=F["small"], cursor="hand2", bd=0,
                  padx=6, pady=3).pack(side="right", padx=6)

        self._log = scrolledtext.ScrolledText(
            parent, bg="#0d0e1a", fg=C["text"],
            font=F["mono"], relief="flat",
            padx=10, pady=10, wrap="word",
            insertbackground=C["text"], state="disabled")
        self._log.pack(fill="both", expand=True, padx=12)
        self._log.tag_config("ok",      foreground=C["green"])
        self._log.tag_config("warn",    foreground=C["orange"])
        self._log.tag_config("error",   foreground=C["red"])
        self._log.tag_config("section", foreground=C["accent"])
        self._log.tag_config("info",    foreground=C["text"])

        # Results
        res_hdr = tk.Frame(parent, bg=C["bg"])
        res_hdr.pack(fill="x", padx=12, pady=(10, 4))
        tk.Label(res_hdr, text="📊  Results Summary",
                 font=F["h2"], fg=C["accent"], bg=C["bg"]).pack(side="left")
        tk.Button(res_hdr, text="📁  Open Folder",
                  command=self._open_workdir,
                  bg=C["border"], fg=C["text"], relief="flat",
                  font=F["small"], cursor="hand2", bd=0,
                  padx=6, pady=3).pack(side="right")

        res_card = tk.Frame(parent, bg=C["panel"],
                            highlightbackground=C["border"], highlightthickness=1)
        res_card.pack(fill="x", padx=12, pady=(0, 12))
        self._res_lbl = tk.Label(res_card,
                                  text="No results yet. Run PPM3 to see output.",
                                  font=F["small"], fg=C["dim"],
                                  bg=C["panel"], justify="left",
                                  anchor="w", wraplength=420,
                                  padx=12, pady=10)
        self._res_lbl.pack(fill="x")

    # ── Card management ────────────────────────────────────────────────────────
    def _add_card(self, pdb_path=None):
        self._bulk_active = False
        self._bulk_pdbs = []
        self._bulk_info.set("No batch folder imported.")
        self._refresh_jobs_layout()
        idx = len(self._cards)
        if self._mode.get() == 1:
            c = SingleMemCard(self._card_cont, idx, remove_cb=self._remove_card)
            if pdb_path:
                c._pdb.set(pdb_path)
        else:
            c = DualMemCard(self._card_cont, idx, remove_cb=self._remove_card)
            if pdb_path:
                c._pdb.set(pdb_path)
        c.pack(fill="x", pady=6)
        self._cards.append(c)

    def _remove_card(self, card):
        if len(self._cards) <= 1:
            messagebox.showinfo("Info", "At least one protein entry is required.")
            return
        if card not in self._cards:
            return
        self._cards.remove(card)
        card.destroy()
        for i, c in enumerate(self._cards):
            c.set_index(i)

    def _clear_cards(self):
        if not messagebox.askyesno("Clear All", "Remove all protein entries?"):
            return
        for c in self._cards:
            c.destroy()
        self._cards = []
        self._bulk_active = False
        self._bulk_pdbs = []
        self._bulk_info.set("No batch folder imported.")
        self._add_card()

    def _switch_mode(self):
        for c in self._cards:
            c.destroy()
        self._cards = []
        self._render_batch_controls()
        if self._bulk_active and self._bulk_pdbs:
            mode_name = "Single membrane" if self._mode.get() == 1 else "Two membranes"
            self._bulk_info.set(f"{len(self._bulk_pdbs)} PDB files imported (batch mode, {mode_name}).")
            self._refresh_jobs_layout()
        else:
            self._add_card()

    def _render_batch_controls(self):
        for w in self._batch_cfg.winfo_children():
            if w is not None:
                w.destroy()
        tk.Label(self._batch_cfg, text="Batch settings (used for imported/selected PDB files):",
                 bg=C["panel"], fg=C["dim"], font=F["small"]).grid(
            row=0, column=0, columnspan=4, sticky="w", pady=(0, 6))
        tk.Checkbutton(self._batch_cfg, text="Include non-solvent heteroatoms",
                       variable=self._bulk_het, bg=C["panel"], fg=C["text"],
                       selectcolor=C["panel"], activebackground=C["panel"],
                       font=F["small"]).grid(row=1, column=0, columnspan=4, sticky="w", pady=(0, 6))
        r = 2
        if self._mode.get() == 1:
            tk.Label(self._batch_cfg, text="Membrane type:", bg=C["panel"], fg=C["text"], font=F["small"]).grid(
                row=r, column=0, sticky="e", padx=(0, 8))
            ttk.Combobox(self._batch_cfg, textvariable=self._bulk_mem, values=MEM_DISPLAY,
                         state="readonly", font=F["small"], width=38).grid(row=r, column=1, sticky="w")
            r += 1
            tk.Label(self._batch_cfg, text="N-term topology:", bg=C["panel"], fg=C["text"], font=F["small"]).grid(
                row=r, column=0, sticky="e", padx=(0, 8))
            tk.Radiobutton(self._batch_cfg, text="in", variable=self._bulk_topo, value="in",
                           bg=C["panel"], fg=C["text"], selectcolor=C["panel"],
                           activebackground=C["panel"], font=F["small"]).grid(row=r, column=1, sticky="w")
            tk.Radiobutton(self._batch_cfg, text="out", variable=self._bulk_topo, value="out",
                           bg=C["panel"], fg=C["text"], selectcolor=C["panel"],
                           activebackground=C["panel"], font=F["small"]).grid(row=r, column=2, sticky="w")
        else:
            def membr_block(row, title, mem_var, shape_var, topo_var):
                tk.Label(self._batch_cfg, text=title, bg=C["panel"], fg=C["green"], font=F["h2"]).grid(
                    row=row, column=0, columnspan=4, sticky="w", pady=(4, 2))
                tk.Label(self._batch_cfg, text="Membrane type:", bg=C["panel"], fg=C["text"], font=F["small"]).grid(
                    row=row+1, column=0, sticky="e", padx=(0, 8))
                ttk.Combobox(self._batch_cfg, textvariable=mem_var, values=MEM_DISPLAY,
                             state="readonly", font=F["small"], width=38).grid(row=row+1, column=1, columnspan=3, sticky="w")
                tk.Label(self._batch_cfg, text="Membrane shape:", bg=C["panel"], fg=C["text"], font=F["small"]).grid(
                    row=row+2, column=0, sticky="e", padx=(0, 8))
                tk.Radiobutton(self._batch_cfg, text="Planar", variable=shape_var, value="planar",
                               bg=C["panel"], fg=C["text"], selectcolor=C["panel"],
                               activebackground=C["panel"], font=F["small"]).grid(row=row+2, column=1, sticky="w")
                tk.Radiobutton(self._batch_cfg, text="Curved", variable=shape_var, value="curved",
                               bg=C["panel"], fg=C["text"], selectcolor=C["panel"],
                               activebackground=C["panel"], font=F["small"]).grid(row=row+2, column=2, sticky="w")
                tk.Label(self._batch_cfg, text="N-term topology:", bg=C["panel"], fg=C["text"], font=F["small"]).grid(
                    row=row+3, column=0, sticky="e", padx=(0, 8))
                tk.Radiobutton(self._batch_cfg, text="in", variable=topo_var, value="in",
                               bg=C["panel"], fg=C["text"], selectcolor=C["panel"],
                               activebackground=C["panel"], font=F["small"]).grid(row=row+3, column=1, sticky="w")
                tk.Radiobutton(self._batch_cfg, text="out", variable=topo_var, value="out",
                               bg=C["panel"], fg=C["text"], selectcolor=C["panel"],
                               activebackground=C["panel"], font=F["small"]).grid(row=row+3, column=2, sticky="w")
                return row + 4

            r = membr_block(r, "Membrane 1", self._bulk_mem1, self._bulk_shape1, self._bulk_topo1)
            r = membr_block(r, "Membrane 2", self._bulk_mem2, self._bulk_shape2, self._bulk_topo2)

        self._bulk_info.set(self._bulk_info.get())
        tk.Label(self._batch_cfg, textvariable=self._bulk_info, bg=C["panel"], fg=C["dim"],
                 font=F["small"]).grid(row=r+1, column=0, columnspan=4, sticky="w", pady=(8, 0))

    def _import_pdb_folder(self):
        folder = filedialog.askdirectory(title="Select folder with PDB files")
        if not folder:
            return
        try:
            pdbs = sorted(
                str(p) for p in Path(folder).iterdir()
                if p.is_file() and p.suffix.lower() == ".pdb")
        except Exception as e:
            messagebox.showerror("Folder Error", str(e))
            return

        if not pdbs:
            messagebox.showinfo("No PDB Files", "No .pdb files found in selected folder.")
            return

        for c in self._cards:
            c.destroy()
        self._cards = []
        self._bulk_pdbs = pdbs
        self._bulk_active = True
        self._refresh_jobs_layout()

        mode_name = "Single membrane" if self._mode.get() == 1 else "Two membranes"
        self._bulk_info.set(f"{len(pdbs)} PDB files imported (batch mode, {mode_name}).")
        self._status.set(f"Loaded {len(pdbs)} PDB files in batch mode.")
        self._log_write(
            f"\nImported {len(pdbs)} PDB files from:\n  {folder}\n"
            f"Mode: {mode_name}\n",
            "section")

    def _import_pdb_files(self):
        files = filedialog.askopenfilenames(
            title="Select PDB file(s)",
            filetypes=[("PDB files", "*.pdb"), ("All files", "*.*")]
        )
        if not files:
            return
        pdbs = sorted(str(Path(p)) for p in files if str(p).lower().endswith(".pdb"))
        if not pdbs:
            messagebox.showinfo("No PDB Files", "No .pdb files selected.")
            return
        for c in self._cards:
            c.destroy()
        self._cards = []
        self._bulk_pdbs = pdbs
        self._bulk_active = True
        self._refresh_jobs_layout()
        mode_name = "Single membrane" if self._mode.get() == 1 else "Two membranes"
        self._bulk_info.set(f"{len(pdbs)} PDB files selected (batch mode, {mode_name}).")
        self._status.set(f"Loaded {len(pdbs)} PDB files in batch mode.")
        self._log_write(
            f"\nSelected {len(pdbs)} PDB files manually.\nMode: {mode_name}\n",
            "section")

    def _get_selected_pdb_paths(self):
        if self._bulk_active and self._bulk_pdbs:
            return list(self._bulk_pdbs)
        return [c.get_pdb_path() for c in self._cards]

    # ── Input file builder ─────────────────────────────────────────────────────
    def _build_inp(self):
        if self._bulk_active and self._bulk_pdbs:
            het = self._bulk_het.get()
            if self._mode.get() == 1:
                code = MEM_TO_CODE.get(self._bulk_mem.get(), "MOM").strip() or "MOM"
                topo = self._bulk_topo.get().strip() or "in"
                lines = [f"{het:2d} {code:<3} {topo:<3} {os.path.basename(p)}" for p in self._bulk_pdbs]
                return "1\n" + "\n".join(lines) + "\n"
            yesno = "yes" if het == 1 else "no"
            code1 = MEM_TO_CODE.get(self._bulk_mem1.get(), "MOM").strip() or "MOM"
            code2 = MEM_TO_CODE.get(self._bulk_mem2.get(), "MOM").strip() or "MOM"
            lines = ["2"]
            for p in self._bulk_pdbs:
                lines.extend([
                    yesno,
                    os.path.basename(p),
                    "2",
                    code1,
                    self._bulk_shape1.get(),
                    self._bulk_topo1.get(),
                    "",
                    code2,
                    self._bulk_shape2.get(),
                    self._bulk_topo2.get(),
                    "",
                ])
            return "\n".join(lines) + "\n"
        if self._mode.get() == 1:
            return "1\n" + "\n".join(c.to_inp_line() for c in self._cards) + "\n"
        else:
            return "2\n" + "\n".join(c.to_inp_block() for c in self._cards) + "\n"

    # ── Run ────────────────────────────────────────────────────────────────────
    def _run(self):
        if self._running:
            return
        immers  = self._immers.get().strip()
        reslib  = self._reslib.get().strip()
        workdir = self._workdir.get().strip()

        errs = []
        if not os.path.isfile(immers):
            errs.append("• immers executable not found.")
        if not os.path.isfile(reslib):
            errs.append("• res.lib not found.")
        if not os.path.isdir(workdir):
            errs.append("• Working directory does not exist.")
        for p in self._get_selected_pdb_paths():
            if not p:
                errs.append("• One or more PDB paths are empty.")
                break
            if not os.path.isfile(p):
                errs.append(f"• PDB not found: {p}")
        if errs:
            messagebox.showerror("Validation Error", "\n".join(errs))
            return

        inp = self._build_inp()
        self._log_write(
            f"\n{'═'*60}\nRun started  {datetime.now():%Y-%m-%d %H:%M:%S}\n{'═'*60}\n",
            "section")
        self._log_write("Input file:\n" + inp + "\n", "info")

        run_dir = os.path.join(workdir, f"ppm3_run_{datetime.now():%Y%m%d_%H%M%S}")
        try:
            os.makedirs(run_dir, exist_ok=False)
            shutil.copy(reslib, os.path.join(run_dir, "res.lib"))
            for p in self._get_selected_pdb_paths():
                if p:
                    shutil.copy(p, os.path.join(run_dir, os.path.basename(p)))
        except Exception as e:
            messagebox.showerror("File Error", str(e))
            return

        inp_path = os.path.join(run_dir, "ppm3_run.inp")
        with open(inp_path, "w") as f:
            f.write(inp)
        self._last_run_dir = run_dir
        self._log_write(f"Run folder: {run_dir}\n", "info")

        self._running = True
        self._run_output_lines = []
        self._run_btn.config(state="disabled")
        self._stop_btn.config(state="normal")
        self._prog.start(12)
        self._status.set("Running…")

        def worker():
            try:
                self._proc = subprocess.Popen(
                    [immers],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    cwd=run_dir, text=True)
                self._proc.stdin.write(inp)
                self._proc.stdin.close()
                for line in self._proc.stdout:
                    self._run_output_lines.append(line.rstrip("\n"))
                    self.after(0, self._log_write, line, "info")
                self._proc.wait()
                self.after(0, self._on_done, self._proc.returncode, run_dir)
            except Exception as e:
                self.after(0, self._log_write, f"\nERROR: {e}\n", "error")
                self.after(0, self._on_done, -1, run_dir)

        threading.Thread(target=worker, daemon=True).start()

    def _stop(self):
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
            self._log_write("\n[Stopped by user]\n", "warn")

    def _on_done(self, rc, workdir):
        self._running = False
        self._run_btn.config(state="normal")
        self._stop_btn.config(state="disabled")
        self._prog.stop()
        if rc == 0:
            self._status.set("✓ Completed successfully.")
            self._log_write("\n✓ PPM3 finished successfully.\n", "ok")
            self._log_write(f"Run folder: {workdir}\n", "info")
        else:
            self._status.set(f"✗ Exited with code {rc}.")
            self._log_write(f"\nProcess exited (code {rc}).\n", "warn")
        self._parse_results(workdir)

    def _parse_results(self, workdir):
        parts = []
        for fname in ("datapar1", "datapar2", "datasub1"):
            fp = os.path.join(workdir, fname)
            if os.path.isfile(fp):
                txt = open(fp).read().strip()
                if txt:
                    parts.append(f"── {fname} ──\n{txt}")
        out_pdbs = [f for f in os.listdir(workdir) if f.endswith("out.pdb")]
        if out_pdbs:
            parts.append("Output PDBs:\n" + "\n".join(f"  • {f}" for f in out_pdbs))
            report_files = self._generate_html_reports(workdir, out_pdbs)
            if report_files:
                parts.append("Generated Reports:\n" + "\n".join(f"  • {f}" for f in report_files))
        if parts:
            summary = "\n\n".join(parts)
            self._res_lbl.config(text=summary, fg=C["text"])
            self._log_write("\n" + summary + "\n", "ok")
        else:
            self._res_lbl.config(
                text="Run completed but no result files found yet.\n"
                     "Check the working directory.",
                fg=C["orange"])

    def _parse_datapar1(self, workdir):
        rows = {}
        fp = os.path.join(workdir, "datapar1")
        if not os.path.isfile(fp):
            return rows
        for line in open(fp):
            s = line.strip()
            if not s:
                continue
            parts = [p.strip() for p in s.split(";")]
            if len(parts) < 7:
                continue
            pdb = parts[0]
            rows[pdb] = {
                "thickness": parts[1],
                "thickness_pm": parts[2],
                "tilt": parts[3],
                "tilt_pm": parts[4],
                "dG": parts[5],
            }
        return rows

    def _parse_datasub1(self, workdir):
        rows = {}
        fp = os.path.join(workdir, "datasub1")
        if not os.path.isfile(fp):
            return rows
        for line in open(fp):
            s = line.strip()
            if not s:
                continue
            parts = [p.strip() for p in s.split(";")]
            if len(parts) < 4:
                continue
            pdb, sub, tilt, segs = parts[0], parts[1], parts[2], parts[3]
            rows.setdefault(pdb, []).append({
                "subunit": sub,
                "tilt": tilt,
                "segments": segs,
            })
        return rows

    def _parse_embedded_residues(self):
        rows = {}
        rx = re.compile(r"^#([^;]+);([^;]+);([^;]+);(.+)$")
        for ln in self._run_output_lines:
            m = rx.match(ln.strip())
            if not m:
                continue
            pdb_id, sub, tilt, residues = m.groups()
            pdb = f"{pdb_id}.pdb"
            rows.setdefault(pdb, []).append({
                "subunit": sub,
                "tilt": tilt.strip(),
                "residues": residues.strip(),
            })
        return rows

    def _infer_input_pdb_from_out(self, out_pdb):
        if out_pdb.endswith("out.pdb"):
            return out_pdb[:-7] + ".pdb"
        return out_pdb

    def _render_report_html(self, out_pdb, param, embedded_rows, seg_rows, message):
        param_row = (
            f"<tr><td>{escape(param.get('thickness', '-'))} ± {escape(param.get('thickness_pm', '-'))} Å</td>"
            f"<td>{escape(param.get('dG', '-'))} kcal/mol</td>"
            f"<td>{escape(param.get('tilt', '-'))} ± {escape(param.get('tilt_pm', '-'))}°</td></tr>"
            if param else
            "<tr><td colspan='3'>No parameter row found</td></tr>"
        )

        emb_rows_html = "".join(
            f"<tr><td>{escape(r['subunit'])}</td><td>{escape(r['tilt'])}</td><td>{escape(r['residues'])}</td></tr>"
            for r in embedded_rows
        ) or "<tr><td colspan='3'>No embedded residue rows found</td></tr>"

        seg_rows_html = "".join(
            f"<tr><td>{escape(r['subunit'])}</td><td>{escape(r['tilt'])}</td><td>{escape(r['segments'])}</td></tr>"
            for r in seg_rows
        ) or "<tr><td colspan='3'>No transmembrane segment rows found</td></tr>"

        return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>{escape(out_pdb)} report</title>
  <style>
    body {{ font-family: Arial, Helvetica, sans-serif; background:#f2f4f6; color:#1a1a1a; }}
    .wrap {{ width: 920px; margin: 20px auto; }}
    h1, h2 {{ color:#0b58b0; text-align:center; margin: 8px 0; }}
    table {{ width: 100%; border-collapse: collapse; background:#fff; margin: 8px 0 16px; }}
    th, td {{ border: 1px solid #c8cdd2; padding: 8px; text-align:center; }}
    th {{ background:#e6edf5; color:#0a4a91; }}
    .section {{ background:#eef3f8; font-weight: bold; color:#0a4a91; }}
    .msg {{ text-align:left; font-family: "Courier New", monospace; white-space: pre-wrap; }}
  </style>
</head>
<body>
  <div class="wrap">
    <h1>Parameters of Protein in Membrane</h1>
    <table>
      <tr><th>Depth/Hydrophobic Thickness</th><th>ΔG<sub>transfer</sub></th><th>Tilt Angle</th></tr>
      {param_row}
    </table>

    <h2>Membrane Embedded Residues (in Hydrocarbon Core)</h2>
    <table>
      <tr><th>Subunits</th><th>Tilt</th><th>Embedded residues</th></tr>
      {emb_rows_html}
      <tr><td class="section" colspan="3">Transmembrane secondary structure segments</td></tr>
      <tr><th>Subunits</th><th>Tilt</th><th>Segments</th></tr>
      {seg_rows_html}
    </table>

    <table>
      <tr><th>Output Messages</th></tr>
      <tr><td class="msg">{escape(message)}</td></tr>
    </table>
  </div>
</body>
</html>
"""

    def _generate_html_reports(self, workdir, out_pdbs):
        datapar = self._parse_datapar1(workdir)
        datasub = self._parse_datasub1(workdir)
        embedded = self._parse_embedded_residues()
        sections = []
        for out_pdb in sorted(out_pdbs):
            in_pdb = self._infer_input_pdb_from_out(out_pdb)
            p = datapar.get(in_pdb, {})
            e_rows = embedded.get(in_pdb, [])
            s_rows = datasub.get(in_pdb, [])
            msg = (
                f"Protein: {in_pdb}\n"
                f"Output: {out_pdb}\n"
                f"emin={p.get('dG', '-')}, thickn={p.get('thickness', '-')}"
                f"+-{p.get('thickness_pm', '-')}, tilt={p.get('tilt', '-')}"
                f"+-{p.get('tilt_pm', '-')}"
            )
            section = self._render_report_html(out_pdb, p, e_rows, s_rows, msg)
            section_body = section.split("<body>", 1)[1].rsplit("</body>", 1)[0].strip()
            sections.append(section_body)

        if not sections:
            return []

        all_html = """<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>PPM3 Combined Report</title>
  <style>
    body { font-family: Arial, Helvetica, sans-serif; background:#f2f4f6; color:#1a1a1a; }
    .wrap { width: 980px; margin: 20px auto; }
    .card { background:#fff; border:1px solid #c8cdd2; margin: 0 0 24px; padding: 10px; }
    h1, h2 { color:#0b58b0; text-align:center; margin: 8px 0; }
    .run-title { text-align:center; color:#0a4a91; }
    table { width: 100%; border-collapse: collapse; background:#fff; margin: 8px 0 16px; }
    th, td { border: 1px solid #c8cdd2; padding: 8px; text-align:center; }
    th { background:#e6edf5; color:#0a4a91; }
    .section { background:#eef3f8; font-weight: bold; color:#0a4a91; }
    .msg { text-align:left; font-family: "Courier New", monospace; white-space: pre-wrap; }
  </style>
</head>
<body>
  <div class="wrap">
    <h1>PPM3 Combined Report</h1>
    <div class="run-title">Run folder: """ + escape(workdir) + """</div>
    """ + "\n".join(f'<div class="card">{s}</div>' for s in sections) + """
  </div>
</body>
</html>
"""
        out_name = "ppm3_combined_report.html"
        out_path = os.path.join(workdir, out_name)
        with open(out_path, "w") as f:
            f.write(all_html)
        return [out_name]

    # ── Compile ────────────────────────────────────────────────────────────────
    def _compile_dialog(self):
        src = filedialog.askdirectory(title="Select folder with .f sources + Makefile")
        if not src:
            return
        self._log_write(f"\nCompiling in {src}…\n", "section")
        self._prog.start(12)

        def do():
            try:
                r = subprocess.run(["make"], cwd=src,
                                   capture_output=True, text=True)
                self.after(0, self._log_write, r.stdout or r.stderr, "info")
                exe = os.path.join(src, "immers")
                res = os.path.join(src, "res.lib")
                if r.returncode == 0 and os.path.isfile(exe):
                    self.after(0, self._immers.set, exe)
                    if os.path.isfile(res):
                        self.after(0, self._reslib.set, res)
                    self.after(0, self._log_write,
                               f"\n✓ Compiled!  immers path set to:\n  {exe}\n", "ok")
                    if os.path.isfile(res):
                        self.after(0, self._log_write,
                                   f"res.lib path set to:\n  {res}\n", "ok")
                else:
                    self.after(0, self._log_write,
                               "\n✗ Compilation failed.\n", "error")
            except FileNotFoundError:
                self.after(0, self._log_write,
                           "\n✗ 'make' not found.\n"
                           "Install Xcode Command Line Tools:\n"
                           "   xcode-select --install\n", "error")
            finally:
                self.after(0, self._prog.stop)

        threading.Thread(target=do, daemon=True).start()

    # ── Log helpers ────────────────────────────────────────────────────────────
    def _log_write(self, text, tag="info"):
        self._log.config(state="normal")
        self._log.insert("end", text, tag)
        self._log.see("end")
        self._log.config(state="disabled")

    def _clear_log(self):
        self._log.config(state="normal")
        self._log.delete("1.0", "end")
        self._log.config(state="disabled")

    def _save_log(self):
        p = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text", "*.txt"), ("All", "*.*")],
            initialfile=f"ppm3_{datetime.now():%Y%m%d_%H%M%S}.log")
        if p:
            with open(p, "w") as f:
                f.write(self._log.get("1.0", "end"))
            self._log_write(f"\nLog saved → {p}\n", "ok")

    def _open_workdir(self):
        wd = self._last_run_dir or self._workdir.get().strip()
        if wd and os.path.isdir(wd):
            subprocess.run(["open" if MAC else "xdg-open", wd])


if __name__ == "__main__":
    app = PPM3App()
    app.mainloop()

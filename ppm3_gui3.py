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

# ── Membrane types ─────────────────────────────────────────────────────────────
MEMBRANE_CODES = [
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
    ("   ", "Undefined membrane"),
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
        for val, desc in [
            ("in",  "in  (N-terminus faces inside membrane)"),
            ("out", "out  (N-terminus faces outside membrane)"),
        ]:
            tk.Radiobutton(r, text=desc,
                           variable=self._topo, value=val,
                           bg=C["card"], fg=C["text"],
                           selectcolor=C["card"],
                           activebackground=C["card"],
                           font=F["body"]).pack(side="left", padx=(0, 24))

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
        if ch:
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
        self._running = False
        self._proc    = None
        self._last_run_dir = ""

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

        self._add_card()

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
    def _add_card(self):
        idx = len(self._cards)
        if self._mode.get() == 1:
            c = SingleMemCard(self._card_cont, idx, remove_cb=self._remove_card)
        else:
            c = DualMemCard(self._card_cont, idx, remove_cb=self._remove_card)
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
        self._add_card()

    def _switch_mode(self):
        for c in self._cards:
            c.destroy()
        self._cards = []
        self._add_card()

    # ── Input file builder ─────────────────────────────────────────────────────
    def _build_inp(self):
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
        for c in self._cards:
            p = c.get_pdb_path()
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
            for c in self._cards:
                p = c.get_pdb_path()
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
        if parts:
            summary = "\n\n".join(parts)
            self._res_lbl.config(text=summary, fg=C["text"])
            self._log_write("\n" + summary + "\n", "ok")
        else:
            self._res_lbl.config(
                text="Run completed but no result files found yet.\n"
                     "Check the working directory.",
                fg=C["orange"])

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
                if r.returncode == 0 and os.path.isfile(exe):
                    self.after(0, self._immers.set, exe)
                    self.after(0, self._log_write,
                               f"\n✓ Compiled!  immers path set to:\n  {exe}\n", "ok")
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

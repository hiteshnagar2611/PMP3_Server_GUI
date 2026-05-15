# PPM3 GUI — macOS Setup & Usage Guide

A native-feeling Python/Tkinter GUI wrapper for the **PPM 3.0** (`immers`) Fortran program.

---

## Requirements

- **macOS** (M2 / Apple Silicon or Intel) — also works on Linux
- **Python 3.8+** — pre-installed on macOS
- **Tkinter** — usually bundled with Python; see below if missing
- **gfortran** — only needed if you want to compile from source inside the app

---

## Step 1 — Install Python with Tkinter

The system Python on macOS sometimes lacks Tkinter. Use Homebrew:

```bash
# Install Homebrew if you don't have it
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python (includes Tkinter)
brew install python-tk
```

Verify:
```bash
python3 -c "import tkinter; print('Tkinter OK')"
```

---

## Step 2 — Compile `immers` (if not already done)

Either compile manually or use the **"Compile from source…"** button in the GUI:

```bash
# Put all .f files + Makefile + res.lib in one folder, then:
cd /path/to/ppm3_sources
make
# Produces: ./immers
```

On Apple Silicon (M2), gfortran from Homebrew works fine:
```bash
brew install gfortran
```

---

## Step 3 — Launch the GUI

```bash
python3 ppm3_gui.py
```

Or make it directly runnable:
```bash
chmod +x ppm3_gui.py
./ppm3_gui.py
```

---

## How to Use the GUI

### Paths & Setup (top-left)

| Field | What to set |
|---|---|
| **immers executable** | Path to the compiled `immers` binary |
| **res.lib library** | Path to `res.lib` (amino acid library) |
| **Working directory** | Folder where results will be written |

The app copies your PDB files and `res.lib` into the working directory automatically before running.

---

### Input Mode

- **Single membrane** — one membrane per protein (generates `1membrane.inp` style input)
- **Two membranes** — up to 2 independent membranes per protein (generates `2membranes.inp` style)

---

### Adding Protein Jobs

Click **"+ Add Entry"** for each protein you want to process.

**Single membrane mode fields:**
- PDB file path (Browse button available)
- Heteroatoms checkbox (include non-solvent heteroatoms)
- Membrane type dropdown (all 23 types)
- N-terminus topology: `in` or `out`

**Two membrane mode fields:**
- PDB file + heteroatoms
- Up to 2 membrane sub-blocks, each with: type, shape (planar/curved), topology, chain list (e.g. `A,B,C`)

---

### Running

Click **▶ Run PPM3**. The console on the right shows live output. Click **⏹ Stop** to terminate early.

---

### Output

After a successful run, the **Results Summary** panel shows parsed output from:

| File | Contents |
|---|---|
| `datapar1` | Flat membrane proteins: thickness, tilt angle, transfer energy |
| `datapar2` | Curved membrane proteins: thickness, radius, tilt, energy |
| `datasub1` | TM segment assignments per subunit |
| `*out.pdb` | PDB coordinates with membrane boundary atoms |

Click **📁 Open Working Directory** to view all output files in Finder.

---

## Membrane Type Codes (Quick Reference)

| Code | Membrane |
|---|---|
| `PMm` | Plasma membrane (mammalian) |
| `MOM` | Outer mitochondrial membrane |
| `MIM` | Inner mitochondrial membrane |
| `GnO` | Gram-negative bacteria outer |
| `GnI` | Gram-negative bacteria inner |
| `ERm` | ER (mammalian) |
| `GOL` | Golgi |
| `OPC` | DOPC bilayer |
| `MIC` | DPC micelle |

> ⚠️ Case matters — `PMm` ≠ `pmm`

---

## Troubleshooting

**"Tkinter not found"**
```bash
brew install python-tk@3.12   # match your Python version
```

**"immers not found" / permission denied**
```bash
chmod +x /path/to/immers
```

**"make not found" when compiling**
```bash
xcode-select --install   # installs macOS Command Line Tools
```

**Floating-point exceptions in console** — Normal, ignore them. PPM3 produces valid results regardless.

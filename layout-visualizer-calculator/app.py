#!/usr/bin/env python3
"""
Soffit Layout Visualizer - Actual Reveal Calculator

Tkinter desktop app for planning soffit board / vent-strip layouts using real
installed reveal widths.

Key project assumptions built in:
- Wood reveal:       3 3/8"
- Vent reveal:       2 1/2"
- Main house depth:  23"
- Entrance depth:    24"
- Total soffit run:  238 LF
- Wood order:        103 @ 12', 55 @ 11', 2 @ 6' = 1853 LF
- Waste allowance:   10%

Run:
    python app.py
"""

from __future__ import annotations

import math
import tkinter as tk
from dataclasses import dataclass
from tkinter import ttk, messagebox
from typing import Dict, List, Optional, Tuple


DEFAULT_WOOD_REVEAL_IN = 3.375
DEFAULT_VENT_REVEAL_IN = 2.5
DEFAULT_MAIN_23_LF = 238.0
DEFAULT_ENTRANCE_24_LF = 0.0
DEFAULT_PCS_12FT = 103
DEFAULT_PCS_11FT = 55
DEFAULT_PCS_6FT = 2
DEFAULT_WASTE_PERCENT = 10.0
DEFAULT_MIN_RIP_IN = 1.0
DEFAULT_TOLERANCE_IN = 0.125


@dataclass(frozen=True)
class Course:
    kind: str      # wood, vent, rip
    width: float
    label: str


@dataclass(frozen=True)
class Layout:
    courses: List[Course]
    depth: float
    wood_reveal: float
    vent_reveal: float
    vent_count: int
    wood_count: int
    rip_count: int
    rip_width: float
    total_used: float
    difference: float
    vent_position: int
    max_vent_position: int
    rip_placement: str
    warnings: List[str]


@dataclass(frozen=True)
class MathCheck:
    depth: float
    wood_width_total: float
    vent_width_total: float
    rip_width_total: float
    total: float
    difference: float
    passed: bool
    formula: str


@dataclass(frozen=True)
class Inventory:
    pcs_12: int
    pcs_11: int
    pcs_6: int
    total_lf: float
    gross_coverage_sqft: float
    usable_coverage_sqft: float
    planned_area_sqft: float
    surplus_sqft_after_waste: float
    surplus_percent_after_waste: float


@dataclass(frozen=True)
class PieceAllocation:
    required_lf: float
    used_12: int
    used_11: int
    used_6: int
    left_12: int
    left_11: int
    left_6: int
    gross_used_lf: float
    unused_piece_lf: float
    overage_from_used_pieces_lf: float
    shortage_lf: float


# -----------------------------------------------------------------------------
# Formatting / parsing
# -----------------------------------------------------------------------------
def format_inches(value: float, denominator: int = 16) -> str:
    if abs(value) < 1e-9:
        return '0"'
    sign = "-" if value < 0 else ""
    value = abs(value)
    whole = int(math.floor(value))
    numerator = int(round((value - whole) * denominator))
    if numerator == denominator:
        whole += 1
        numerator = 0
    if numerator == 0:
        return f'{sign}{whole}"'
    div = math.gcd(numerator, denominator)
    numerator //= div
    denominator //= div
    if whole == 0:
        return f'{sign}{numerator}/{denominator}"'
    return f'{sign}{whole} {numerator}/{denominator}"'


def parse_inches(text: str, field_name: str) -> float:
    raw = text.strip().replace('"', '').replace("inches", "").replace("inch", "")
    raw = raw.replace("IN", "").replace("in", "").replace("-", " ")
    if not raw:
        raise ValueError(f"{field_name} is blank.")
    total = 0.0
    for part in raw.split():
        if "/" in part:
            n, d = part.split("/", 1)
            total += float(n) / float(d)
        else:
            total += float(part)
    return total


def parse_float(text: str, field_name: str) -> float:
    raw = text.strip()
    if not raw:
        raise ValueError(f"{field_name} is blank.")
    return float(raw)


def parse_int(text: str, field_name: str) -> int:
    return int(round(parse_float(text, field_name)))


# -----------------------------------------------------------------------------
# Layout math
# -----------------------------------------------------------------------------
def build_sequence(wood_count: int, vent_count: int, vent_position: int) -> Tuple[List[str], int, int]:
    if vent_count <= 0:
        return ["wood"] * wood_count, 0, max(0, wood_count)
    max_pos = max(0, wood_count)
    pos = max(0, min(int(vent_position), max_pos))
    return ["wood"] * pos + ["vent"] * vent_count + ["wood"] * (wood_count - pos), pos, max_pos


def auto_wood_count(
    depth: float,
    wood_reveal: float,
    vent_reveal: float,
    vent_count: int,
    rip_placement: str,
    min_rip: float,
    tolerance: float,
) -> int:
    max_wood = int(math.floor((depth - vent_count * vent_reveal) / wood_reveal))
    if max_wood < 0:
        raise ValueError("Vent strips alone exceed the soffit depth.")

    balanced = rip_placement == "Both sides balanced"
    for candidate in range(max_wood, -1, -1):
        fixed = candidate * wood_reveal + vent_count * vent_reveal
        leftover = depth - fixed
        if leftover < -tolerance:
            continue
        rip_width = leftover / 2.0 if balanced else leftover
        if leftover <= tolerance or rip_width >= min_rip:
            return candidate
    return max_wood


def calculate_layout(
    depth: float,
    wood_reveal: float,
    vent_reveal: float,
    vent_count: int,
    mode: str,
    manual_wood_count: int,
    vent_position: int,
    rip_placement: str,
    min_rip: float,
    tolerance: float,
) -> Layout:
    warnings: List[str] = []
    if depth <= 0:
        raise ValueError("Soffit depth must be greater than zero.")
    if wood_reveal <= 0:
        raise ValueError("Wood reveal must be greater than zero.")
    if vent_reveal <= 0:
        raise ValueError("Vent reveal must be greater than zero.")
    if vent_count < 0:
        raise ValueError("Vent strip count cannot be negative.")
    if min_rip < 0 or tolerance < 0:
        raise ValueError("Minimum rip and tolerance cannot be negative.")

    if mode == "Manual":
        wood_count = int(manual_wood_count)
        if wood_count < 0:
            raise ValueError("Manual wood count cannot be negative.")
    else:
        wood_count = auto_wood_count(depth, wood_reveal, vent_reveal, vent_count, rip_placement, min_rip, tolerance)

    fixed = wood_count * wood_reveal + vent_count * vent_reveal
    leftover = depth - fixed
    if leftover < -tolerance:
        raise ValueError(f"Selected layout exceeds soffit depth by {format_inches(abs(leftover))}.")
    if abs(leftover) <= tolerance:
        leftover = 0.0

    balanced = rip_placement == "Both sides balanced"
    rip_left = rip_placement == "One side - wall/left"
    rip_right = rip_placement == "One side - fascia/right"
    rip_width = leftover / 2.0 if balanced and leftover > 0 else max(0.0, leftover)
    rip_count = 2 if balanced and rip_width > tolerance else (1 if rip_width > tolerance else 0)

    if rip_count and rip_width < min_rip:
        warnings.append(f"Rip width {format_inches(rip_width)} is below preferred minimum {format_inches(min_rip)}.")

    sequence, actual_pos, max_pos = build_sequence(wood_count, vent_count, vent_position)
    courses: List[Course] = []

    if rip_count and (balanced or rip_left):
        courses.append(Course("rip", rip_width, f"Rip {format_inches(rip_width)}"))

    for item in sequence:
        if item == "wood":
            courses.append(Course("wood", wood_reveal, f"Wood {format_inches(wood_reveal)}"))
        else:
            courses.append(Course("vent", vent_reveal, f"Vent {format_inches(vent_reveal)}"))

    if rip_count and (balanced or rip_right):
        courses.append(Course("rip", rip_width, f"Rip {format_inches(rip_width)}"))

    total_used = sum(c.width for c in courses)
    difference = depth - total_used
    if abs(difference) > tolerance:
        warnings.append(f"Calculated layout differs from target by {format_inches(difference)}.")

    return Layout(
        courses=courses,
        depth=depth,
        wood_reveal=wood_reveal,
        vent_reveal=vent_reveal,
        vent_count=vent_count,
        wood_count=wood_count,
        rip_count=rip_count,
        rip_width=rip_width,
        total_used=total_used,
        difference=difference,
        vent_position=actual_pos,
        max_vent_position=max_pos,
        rip_placement=rip_placement,
        warnings=warnings,
    )


def verify_layout_math(layout: Layout, tolerance: float) -> MathCheck:
    wood_total = layout.wood_count * layout.wood_reveal
    vent_total = layout.vent_count * layout.vent_reveal
    rip_total = layout.rip_count * layout.rip_width
    total = wood_total + vent_total + rip_total
    difference = layout.depth - total
    passed = abs(difference) <= tolerance
    formula = (
        f"({layout.wood_count} x {format_inches(layout.wood_reveal)}) + "
        f"({layout.vent_count} x {format_inches(layout.vent_reveal)}) + "
        f"({layout.rip_count} x {format_inches(layout.rip_width)}) = "
        f"{format_inches(total)}"
    )
    return MathCheck(layout.depth, wood_total, vent_total, rip_total, total, difference, passed, formula)


# -----------------------------------------------------------------------------
# Whole-job / inventory math
# -----------------------------------------------------------------------------
def calculate_inventory(
    pcs_12: int,
    pcs_11: int,
    pcs_6: int,
    wood_reveal_in: float,
    lf_23: float,
    lf_24: float,
    waste_percent: float,
) -> Inventory:
    total_lf = pcs_12 * 12.0 + pcs_11 * 11.0 + pcs_6 * 6.0
    gross = total_lf * wood_reveal_in / 12.0
    usable = gross * (1.0 - waste_percent / 100.0)
    planned = (lf_23 * 23.0 + lf_24 * 24.0) / 12.0
    surplus = usable - planned
    pct = surplus / planned * 100.0 if planned > 0 else 0.0
    return Inventory(pcs_12, pcs_11, pcs_6, total_lf, gross, usable, planned, surplus, pct)


def wood_courses_per_run(layout: Layout) -> int:
    return layout.wood_count + layout.rip_count


def allocate_pieces_no_waste(required_lf: float, pcs_12: int, pcs_11: int, pcs_6: int) -> PieceAllocation:
    """
    Simple no-waste starting allocation.

    This allocates board inventory by total linear feet, using 12' pieces first,
    then 11', then 6'. It does not optimize actual cut nesting, seams, mitres,
    defects, or sequencing. The overage_from_used_pieces_lf value is the excess
    length in the last consumed piece(s) beyond the exact required LF.
    """
    remaining = max(0.0, required_lf)
    used_12 = min(pcs_12, int(remaining // 12.0))
    remaining -= used_12 * 12.0
    if remaining > 1e-9 and used_12 < pcs_12:
        used_12 += 1
        remaining = 0.0

    if remaining > 1e-9:
        used_11 = min(pcs_11, int(remaining // 11.0))
        remaining -= used_11 * 11.0
        if remaining > 1e-9 and used_11 < pcs_11:
            used_11 += 1
            remaining = 0.0
    else:
        used_11 = 0

    if remaining > 1e-9:
        used_6 = min(pcs_6, int(remaining // 6.0))
        remaining -= used_6 * 6.0
        if remaining > 1e-9 and used_6 < pcs_6:
            used_6 += 1
            remaining = 0.0
    else:
        used_6 = 0

    gross_used = used_12 * 12.0 + used_11 * 11.0 + used_6 * 6.0
    shortage = max(0.0, required_lf - gross_used)
    overage = max(0.0, gross_used - required_lf)
    left_12 = pcs_12 - used_12
    left_11 = pcs_11 - used_11
    left_6 = pcs_6 - used_6
    unused_lf = left_12 * 12.0 + left_11 * 11.0 + left_6 * 6.0
    return PieceAllocation(
        required_lf=required_lf,
        used_12=used_12,
        used_11=used_11,
        used_6=used_6,
        left_12=left_12,
        left_11=left_11,
        left_6=left_6,
        gross_used_lf=gross_used,
        unused_piece_lf=unused_lf,
        overage_from_used_pieces_lf=overage,
        shortage_lf=shortage,
    )


def combined_required_wood_lf(layout_23: Layout, lf_23: float, layout_24: Layout, lf_24: float) -> float:
    return wood_courses_per_run(layout_23) * lf_23 + wood_courses_per_run(layout_24) * lf_24


def combined_required_vent_lf(layout_23: Layout, lf_23: float, layout_24: Layout, lf_24: float) -> float:
    return layout_23.vent_count * lf_23 + layout_24.vent_count * lf_24


class SoffitVisualizer:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Soffit Layout Visualizer - Actual Reveal Calculator")
        self.root.geometry("1380x880")
        self.root.minsize(1160, 740)
        self.root.configure(bg="#1e1e24")

        # Layout inputs
        self.depth_var = tk.StringVar(value="24")
        self.wood_reveal_var = tk.StringVar(value="3 3/8")
        self.vent_reveal_var = tk.StringVar(value="2 1/2")
        self.vent_count_var = tk.IntVar(value=1)
        self.mode_var = tk.StringVar(value="Auto")
        self.manual_wood_count_var = tk.StringVar(value="6")
        self.vent_position_var = tk.IntVar(value=3)
        self.rip_placement_var = tk.StringVar(value="Both sides balanced")
        self.min_rip_var = tk.StringVar(value="1")
        self.tolerance_var = tk.StringVar(value="1/8")

        # Whole-job inputs
        self.lf_23_var = tk.StringVar(value=str(int(DEFAULT_MAIN_23_LF)))
        self.lf_24_var = tk.StringVar(value=str(int(DEFAULT_ENTRANCE_24_LF)))
        self.pcs_12_var = tk.StringVar(value=str(DEFAULT_PCS_12FT))
        self.pcs_11_var = tk.StringVar(value=str(DEFAULT_PCS_11FT))
        self.pcs_6_var = tk.StringVar(value=str(DEFAULT_PCS_6FT))
        self.waste_percent_var = tk.StringVar(value=str(int(DEFAULT_WASTE_PERCENT)))

        self.last_layout: Optional[Layout] = None
        self.last_layout_23: Optional[Layout] = None
        self.last_layout_24: Optional[Layout] = None
        self.last_inventory: Optional[Inventory] = None
        self.last_allocation: Optional[PieceAllocation] = None
        self.last_math_check: Optional[MathCheck] = None

        self._build_styles()
        self._build_ui()
        self.update_calculations()

    def _build_styles(self) -> None:
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TFrame", background="#1e1e24")
        style.configure("Panel.TFrame", background="#292933")
        style.configure("TLabel", background="#1e1e24", foreground="#f2f2f2", font=("Segoe UI", 10))
        style.configure("Panel.TLabel", background="#292933", foreground="#f2f2f2", font=("Segoe UI", 10))
        style.configure("Header.TLabel", background="#1e1e24", foreground="#ffffff", font=("Segoe UI", 16, "bold"))
        style.configure("Subtle.TLabel", background="#1e1e24", foreground="#bdbdc7", font=("Segoe UI", 9))
        style.configure("PanelSubtle.TLabel", background="#292933", foreground="#bdbdc7", font=("Segoe UI", 9))
        style.configure("TButton", font=("Segoe UI", 10))

    def _build_ui(self) -> None:
        outer = ttk.Frame(self.root, padding=14)
        outer.pack(fill=tk.BOTH, expand=True)

        header = ttk.Frame(outer)
        header.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(header, text="Soffit Layout Visualizer", style="Header.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="Auto calculates layout. Whole-job estimate separates 23\" main-house LF and 24\" entrance LF, then estimates no-waste pieces used/left.",
            style="Subtle.TLabel",
        ).pack(anchor="w")

        main = ttk.Frame(outer)
        main.pack(fill=tk.BOTH, expand=True)
        controls = ttk.Frame(main, style="Panel.TFrame", padding=12)
        controls.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 12))
        right = ttk.Frame(main)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._build_controls(controls)
        self._build_visual_area(right)

    def _add_entry(self, parent: ttk.Frame, label: str, var: tk.StringVar, row: int) -> ttk.Entry:
        ttk.Label(parent, text=label, style="Panel.TLabel").grid(row=row, column=0, sticky="w", pady=4)
        entry = ttk.Entry(parent, textvariable=var, width=15)
        entry.grid(row=row, column=1, sticky="ew", pady=4, padx=(8, 0))
        entry.bind("<KeyRelease>", lambda _event: self.update_calculations())
        entry.bind("<FocusOut>", lambda _event: self.update_calculations())
        return entry

    def _build_controls(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(1, weight=1)
        r = 0
        ttk.Label(parent, text="Sample Layout", style="Panel.TLabel", font=("Segoe UI", 11, "bold")).grid(row=r, column=0, columnspan=2, sticky="w", pady=(0, 6)); r += 1
        self._add_entry(parent, "Sample soffit depth", self.depth_var, r); r += 1
        self._add_entry(parent, "Wood reveal", self.wood_reveal_var, r); r += 1
        self._add_entry(parent, "Vent reveal", self.vent_reveal_var, r); r += 1

        ttk.Separator(parent).grid(row=r, column=0, columnspan=2, sticky="ew", pady=12); r += 1
        ttk.Label(parent, text="Layout Controls", style="Panel.TLabel", font=("Segoe UI", 11, "bold")).grid(row=r, column=0, columnspan=2, sticky="w", pady=(0, 6)); r += 1

        ttk.Label(parent, text="Vent strips", style="Panel.TLabel").grid(row=r, column=0, sticky="w", pady=4)
        spin = ttk.Spinbox(parent, from_=0, to=6, textvariable=self.vent_count_var, width=12, command=self.update_calculations)
        spin.grid(row=r, column=1, sticky="ew", pady=4, padx=(8, 0))
        spin.bind("<KeyRelease>", lambda _event: self.update_calculations()); r += 1

        ttk.Label(parent, text="Wood count mode", style="Panel.TLabel").grid(row=r, column=0, sticky="w", pady=4)
        mode = ttk.Combobox(parent, textvariable=self.mode_var, values=["Auto", "Manual"], state="readonly", width=15)
        mode.grid(row=r, column=1, sticky="ew", pady=4, padx=(8, 0))
        mode.bind("<<ComboboxSelected>>", lambda _event: self.update_calculations()); r += 1

        self.manual_entry = self._add_entry(parent, "Manual wood count", self.manual_wood_count_var, r); r += 1

        ttk.Label(parent, text="Rip placement", style="Panel.TLabel").grid(row=r, column=0, sticky="w", pady=4)
        rip = ttk.Combobox(
            parent,
            textvariable=self.rip_placement_var,
            values=["Both sides balanced", "One side - wall/left", "One side - fascia/right"],
            state="readonly",
            width=22,
        )
        rip.grid(row=r, column=1, sticky="ew", pady=4, padx=(8, 0))
        rip.bind("<<ComboboxSelected>>", lambda _event: self.update_calculations()); r += 1

        ttk.Label(parent, text="Vent location", style="Panel.TLabel").grid(row=r, column=0, sticky="w", pady=4)
        self.vent_position_label = ttk.Label(parent, text="", style="Panel.TLabel")
        self.vent_position_label.grid(row=r, column=1, sticky="w", pady=4, padx=(8, 0)); r += 1

        move = ttk.Frame(parent, style="Panel.TFrame")
        move.grid(row=r, column=0, columnspan=2, sticky="ew", pady=(2, 8))
        for c in range(3):
            move.columnconfigure(c, weight=1)
        self.btn_left = ttk.Button(move, text="← Vent left", command=lambda: self.move_vent(-1))
        self.btn_left.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        self.btn_center = ttk.Button(move, text="Centre", command=self.center_vent)
        self.btn_center.grid(row=0, column=1, sticky="ew", padx=4)
        self.btn_right = ttk.Button(move, text="Vent right →", command=lambda: self.move_vent(1))
        self.btn_right.grid(row=0, column=2, sticky="ew", padx=(4, 0)); r += 1

        self._add_entry(parent, "Preferred min rip", self.min_rip_var, r); r += 1
        self._add_entry(parent, "Tolerance", self.tolerance_var, r); r += 1

        ttk.Separator(parent).grid(row=r, column=0, columnspan=2, sticky="ew", pady=12); r += 1
        ttk.Label(parent, text="Whole-Job Assumptions", style="Panel.TLabel", font=("Segoe UI", 11, "bold")).grid(row=r, column=0, columnspan=2, sticky="w", pady=(0, 6)); r += 1
        self._add_entry(parent, "23 in soffit LF", self.lf_23_var, r); r += 1
        self._add_entry(parent, "24 in entrance LF", self.lf_24_var, r); r += 1
        self._add_entry(parent, "12 ft pieces", self.pcs_12_var, r); r += 1
        self._add_entry(parent, "11 ft pieces", self.pcs_11_var, r); r += 1
        self._add_entry(parent, "6 ft pieces", self.pcs_6_var, r); r += 1
        self._add_entry(parent, "Waste %", self.waste_percent_var, r); r += 1

        ttk.Button(parent, text="Recalculate", command=self.update_calculations).grid(row=r, column=0, columnspan=2, sticky="ew", pady=(12, 4)); r += 1
        ttk.Button(parent, text="Run Math Check", command=self.run_math_check).grid(row=r, column=0, columnspan=2, sticky="ew", pady=4); r += 1
        ttk.Button(parent, text="Copy Summary", command=self.copy_summary).grid(row=r, column=0, columnspan=2, sticky="ew", pady=4); r += 1

        ttk.Label(
            parent,
            text="For your case: set most LF under 23 in soffit LF, and only the entrance run under 24 in entrance LF. No-waste pieces used is a starting estimate only, not cut optimization.",
            style="PanelSubtle.TLabel",
            wraplength=310,
        ).grid(row=r, column=0, columnspan=2, sticky="w", pady=(12, 0))

    def _build_visual_area(self, parent: ttk.Frame) -> None:
        canvas_frame = ttk.Frame(parent, style="Panel.TFrame", padding=8)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        self.canvas = tk.Canvas(canvas_frame, bg="#15151b", highlightthickness=0, height=360)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Configure>", lambda _event: self.draw_layout())

        bottom = ttk.Frame(parent)
        bottom.pack(fill=tk.BOTH, expand=True, pady=(12, 0))

        summary_frame = ttk.Frame(bottom, style="Panel.TFrame", padding=8)
        summary_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))
        ttk.Label(summary_frame, text="Summary", style="Panel.TLabel", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        self.summary_text = tk.Text(summary_frame, height=16, wrap=tk.WORD, bg="#101016", fg="#f2f2f2", insertbackground="#ffffff", relief=tk.FLAT, font=("Consolas", 10))
        self.summary_text.pack(fill=tk.BOTH, expand=True, pady=(6, 0))

        calc_frame = ttk.Frame(bottom, style="Panel.TFrame", padding=8)
        calc_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False)
        ttk.Label(calc_frame, text="Calculation Block", style="Panel.TLabel", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        self.calc_text = tk.Text(calc_frame, width=58, height=16, wrap=tk.WORD, bg="#101016", fg="#f2f2f2", insertbackground="#ffffff", relief=tk.FLAT, font=("Consolas", 10))
        self.calc_text.pack(fill=tk.BOTH, expand=True, pady=(6, 0))

    def read_inputs(self):
        depth = parse_inches(self.depth_var.get(), "Sample soffit depth")
        wood = parse_inches(self.wood_reveal_var.get(), "Wood reveal")
        vent = parse_inches(self.vent_reveal_var.get(), "Vent reveal")
        vent_count = int(self.vent_count_var.get())
        manual_wood = int(parse_inches(self.manual_wood_count_var.get(), "Manual wood count"))
        min_rip = parse_inches(self.min_rip_var.get(), "Preferred minimum rip")
        tolerance = parse_inches(self.tolerance_var.get(), "Tolerance")
        lf_23 = parse_float(self.lf_23_var.get(), "23 inch soffit LF")
        lf_24 = parse_float(self.lf_24_var.get(), "24 inch entrance LF")
        pcs_12 = parse_int(self.pcs_12_var.get(), "12 ft pieces")
        pcs_11 = parse_int(self.pcs_11_var.get(), "11 ft pieces")
        pcs_6 = parse_int(self.pcs_6_var.get(), "6 ft pieces")
        waste = parse_float(self.waste_percent_var.get(), "Waste percent")

        if lf_23 < 0 or lf_24 < 0:
            raise ValueError("23 in and 24 in linear feet cannot be negative.")
        if pcs_12 < 0 or pcs_11 < 0 or pcs_6 < 0:
            raise ValueError("Piece counts cannot be negative.")
        if waste < 0 or waste >= 100:
            raise ValueError("Waste percent must be between 0 and 99.")

        return depth, wood, vent, vent_count, manual_wood, min_rip, tolerance, lf_23, lf_24, pcs_12, pcs_11, pcs_6, waste

    def layout_for_depth(self, depth: float) -> Layout:
        _sample, wood, vent, vent_count, manual_wood, min_rip, tolerance, *_ = self.read_inputs()
        return calculate_layout(
            depth=depth,
            wood_reveal=wood,
            vent_reveal=vent,
            vent_count=vent_count,
            mode=self.mode_var.get(),
            manual_wood_count=manual_wood,
            vent_position=self.vent_position_var.get(),
            rip_placement=self.rip_placement_var.get(),
            min_rip=min_rip,
            tolerance=tolerance,
        )

    def update_calculations(self) -> None:
        try:
            depth, wood, vent, vent_count, manual_wood, min_rip, tolerance, lf_23, lf_24, pcs_12, pcs_11, pcs_6, waste = self.read_inputs()
            sample_layout = calculate_layout(depth, wood, vent, vent_count, self.mode_var.get(), manual_wood, self.vent_position_var.get(), self.rip_placement_var.get(), min_rip, tolerance)
            layout_23 = calculate_layout(23.0, wood, vent, vent_count, self.mode_var.get(), manual_wood, self.vent_position_var.get(), self.rip_placement_var.get(), min_rip, tolerance)
            layout_24 = calculate_layout(24.0, wood, vent, vent_count, self.mode_var.get(), manual_wood, self.vent_position_var.get(), self.rip_placement_var.get(), min_rip, tolerance)
            inventory = calculate_inventory(pcs_12, pcs_11, pcs_6, wood, lf_23, lf_24, waste)
            required_lf = combined_required_wood_lf(layout_23, lf_23, layout_24, lf_24)
            allocation = allocate_pieces_no_waste(required_lf, pcs_12, pcs_11, pcs_6)
            math_check = verify_layout_math(sample_layout, tolerance)

            self.last_layout = sample_layout
            self.last_layout_23 = layout_23
            self.last_layout_24 = layout_24
            self.last_inventory = inventory
            self.last_allocation = allocation
            self.last_math_check = math_check
            self.vent_position_var.set(sample_layout.vent_position)
            self.update_control_states()
            self.draw_layout()
            self.write_summary(sample_layout, layout_23, layout_24, inventory, allocation, lf_23, lf_24, waste, math_check)
            self.write_calculation_block(sample_layout, layout_23, layout_24, inventory, allocation, lf_23, lf_24, waste, math_check)
        except Exception as exc:
            self.last_layout = None
            self.last_layout_23 = None
            self.last_layout_24 = None
            self.last_inventory = None
            self.last_allocation = None
            self.last_math_check = None
            if hasattr(self, "canvas"):
                self.canvas.delete("all")
                self.canvas.create_text(20, 20, anchor="nw", fill="#ffb4b4", font=("Segoe UI", 11, "bold"), text=f"Input error: {exc}", width=max(300, self.canvas.winfo_width() - 40))
            if hasattr(self, "summary_text"):
                self.summary_text.delete("1.0", tk.END)
                self.summary_text.insert(tk.END, f"Input error: {exc}\n")
            if hasattr(self, "calc_text"):
                self.calc_text.delete("1.0", tk.END)
                self.calc_text.insert(tk.END, f"Input error: {exc}\n")

    def update_control_states(self) -> None:
        auto = self.mode_var.get() == "Auto"
        self.manual_entry.configure(state="disabled" if auto else "normal")
        if self.last_layout:
            mode_label = "auto wood count" if auto else "manual wood count"
            self.vent_position_label.configure(text=f"{self.last_layout.vent_position} wood before vent / max {self.last_layout.max_vent_position} ({mode_label})")
            state = "disabled" if self.last_layout.vent_count == 0 else "normal"
        else:
            self.vent_position_label.configure(text="")
            state = "normal"
        self.btn_left.configure(state=state)
        self.btn_center.configure(state=state)
        self.btn_right.configure(state=state)

    def move_vent(self, delta: int) -> None:
        max_pos = self.last_layout.max_vent_position if self.last_layout else 0
        self.vent_position_var.set(max(0, min(self.vent_position_var.get() + delta, max_pos)))
        self.update_calculations()

    def center_vent(self) -> None:
        max_pos = self.last_layout.max_vent_position if self.last_layout else 0
        self.vent_position_var.set(max(0, max_pos // 2))
        self.update_calculations()

    def run_math_check(self) -> None:
        self.update_calculations()
        if not self.last_layout or not self.last_layout_23 or not self.last_layout_24:
            messagebox.showerror("Math Check", "No valid layout to check.")
            return
        _depth, _wood, _vent, _vc, _mw, _min_rip, tolerance, *_ = self.read_inputs()
        checks = [
            verify_layout_math(self.last_layout, tolerance),
            verify_layout_math(self.last_layout_23, tolerance),
            verify_layout_math(self.last_layout_24, tolerance),
        ]
        passed = all(c.passed for c in checks)
        msg = "PASS: sample, 23\", and 24\" layout arithmetic balances." if passed else "FAIL: at least one layout arithmetic check failed."
        messagebox.showinfo("Math Check", msg + "\n\nDetails are shown in the Calculation Block.")

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------
    def draw_layout(self) -> None:
        self.canvas.delete("all")
        layout = self.last_layout
        if not layout:
            return
        w = max(650, self.canvas.winfo_width())
        h = max(300, self.canvas.winfo_height())
        y0 = 98
        bar_h = min(135, max(85, h // 3))
        y1 = y0 + bar_h
        wall_w = 58
        fascia_w = 70
        left_pad = 28
        gap = 12
        wall_x0 = left_pad
        wall_x1 = wall_x0 + wall_w
        soffit_x0 = wall_x1 + gap
        fascia_x1 = w - 34
        fascia_x0 = fascia_x1 - fascia_w
        soffit_x1 = fascia_x0 - gap
        usable = max(220, soffit_x1 - soffit_x0)
        scale = usable / layout.depth

        self.canvas.create_text(soffit_x0, 18, anchor="nw", fill="#ffffff", font=("Segoe UI", 13, "bold"), text=f"Sample depth: {format_inches(layout.depth)}  |  Total used: {format_inches(layout.total_used)}")

        self.canvas.create_rectangle(wall_x0, y0 - 18, wall_x1, y1 + 18, fill="#d9c7a8", outline="#f1dfbd", width=2)
        for yy in range(int(y0 - 12), int(y1 + 18), 14):
            self.canvas.create_line(wall_x0 + 4, yy, wall_x1 - 4, yy + 5, fill="#b9a47e", width=1)
        self.canvas.create_text((wall_x0 + wall_x1) / 2, y0 - 36, fill="#e8e0cf", font=("Segoe UI", 9, "bold"), text="House\nstucco\nwall", justify=tk.CENTER)

        self.canvas.create_rectangle(fascia_x0, y0 - 18, fascia_x1, y1 + 18, fill="#8b4a22", outline="#c88950", width=2)
        self.canvas.create_rectangle(fascia_x0 - 6, y0 - 30, fascia_x1 + 5, y0 - 14, fill="#4d5961", outline="#83909a", width=1)
        self.canvas.create_text((fascia_x0 + fascia_x1) / 2, y0 - 50, fill="#dfe8ee", font=("Segoe UI", 9, "bold"), text="Gutter /\nfascia\nboard", justify=tk.CENTER)

        self.canvas.create_line(soffit_x0, y0 - 20, soffit_x1, y0 - 20, fill="#d7d7df", width=1)
        self.canvas.create_line(soffit_x0, y0 - 26, soffit_x0, y0 - 14, fill="#d7d7df", width=1)
        self.canvas.create_line(soffit_x1, y0 - 26, soffit_x1, y0 - 14, fill="#d7d7df", width=1)
        self.canvas.create_text((soffit_x0 + soffit_x1) / 2, y0 - 36, fill="#d7d7df", font=("Segoe UI", 10), text=format_inches(layout.depth))

        colors = {"wood": "#c86f2f", "rip": "#e09a55", "vent": "#121217"}
        outlines = {"wood": "#f3b16e", "rip": "#ffd19a", "vent": "#4b4b56"}
        x = soffit_x0
        for idx, course in enumerate(layout.courses, start=1):
            x2 = x + max(1, course.width * scale)
            self.canvas.create_rectangle(x, y0, x2, y1, fill=colors[course.kind], outline=outlines[course.kind], width=2)
            if course.kind == "vent":
                self._draw_vent_holes(x, y0, x2, y1)
            else:
                self._draw_wood_grain(x, y0, x2, y1)
            cw = x2 - x
            if cw >= 58:
                fill = "#ffffff" if course.kind == "vent" else "#1d1209"
                self.canvas.create_text((x + x2) / 2, y0 + bar_h / 2, fill=fill, font=("Segoe UI", 9, "bold"), text=course.label, width=max(48, cw - 8))
            else:
                self.canvas.create_text((x + x2) / 2, y1 + 14, fill="#f2f2f2", font=("Segoe UI", 8), text=str(idx))
            self.canvas.create_line(x, y1 + 4, x, y1 + 12, fill="#888894")
            self.canvas.create_text((x + x2) / 2, y1 + 32, fill="#cfcfd8", font=("Segoe UI", 8), text=format_inches(course.width))
            x = x2
        self.canvas.create_line(soffit_x1, y1 + 4, soffit_x1, y1 + 12, fill="#888894")

        legend_y = y1 + 66
        self._legend_item(soffit_x0, legend_y, "#c86f2f", "Full wood reveal")
        self._legend_item(soffit_x0 + 170, legend_y, "#e09a55", "Rip-cut wood")
        self._legend_item(soffit_x0 + 330, legend_y, "#121217", "Vent strip")
        self.canvas.create_text(soffit_x0, y1 + 57, anchor="w", fill="#bfc7d0", font=("Segoe UI", 8), text="← house / wall side")
        self.canvas.create_text(soffit_x1, y1 + 57, anchor="e", fill="#bfc7d0", font=("Segoe UI", 8), text="fascia / gutter side →")

    def _draw_vent_holes(self, x0: float, y0: float, x1: float, y1: float) -> None:
        spacing = 11
        radius = 2.2
        col = 0
        xx = x0 + 8
        while xx < x1 - 6:
            yy = y0 + 8 + (spacing / 2 if col % 2 else 0)
            while yy < y1 - 6:
                self.canvas.create_oval(xx - radius, yy - radius, xx + radius, yy + radius, fill="#000000", outline="")
                yy += spacing
            xx += spacing
            col += 1

    def _draw_wood_grain(self, x0: float, y0: float, x1: float, y1: float) -> None:
        if x1 - x0 < 12:
            return
        for offset in (0.25, 0.48, 0.72):
            yy = y0 + (y1 - y0) * offset
            self.canvas.create_line(x0 + 6, yy, x1 - 6, yy + 2, fill="#9f4f1e", width=1, smooth=True)

    def _legend_item(self, x: int, y: int, color: str, text: str) -> None:
        self.canvas.create_rectangle(x, y, x + 18, y + 18, fill=color, outline="#d0d0d0")
        self.canvas.create_text(x + 25, y + 9, anchor="w", fill="#e7e7ee", font=("Segoe UI", 9), text=text)

    # ------------------------------------------------------------------
    # Text outputs
    # ------------------------------------------------------------------
    def math_check_lines(self, check: MathCheck, label: str) -> List[str]:
        status = "PASS" if check.passed else "FAIL"
        return [
            f"{label}: {format_inches(check.depth)} [{status}]",
            f"  Wood:  {format_inches(check.wood_width_total)}",
            f"  Vent:  {format_inches(check.vent_width_total)}",
            f"  Rip:   {format_inches(check.rip_width_total)}",
            f"  Total: {format_inches(check.total)}",
            f"  Diff:  {format_inches(check.difference)}",
            f"  {check.formula}",
        ]

    def write_summary(
        self,
        sample: Layout,
        layout_23: Layout,
        layout_24: Layout,
        inventory: Inventory,
        allocation: PieceAllocation,
        lf_23: float,
        lf_24: float,
        waste: float,
        math_check: MathCheck,
    ) -> None:
        total_lf = lf_23 + lf_24
        vent_lf = combined_required_vent_lf(layout_23, lf_23, layout_24, lf_24)
        lines: List[str] = []
        lines.append("SOFFIT LAYOUT SUMMARY")
        lines.append("=" * 72)
        lines.append(f"Sample soffit depth:       {format_inches(sample.depth)}")
        lines.append(f"Wood reveal used:          {format_inches(sample.wood_reveal)}")
        lines.append(f"Vent reveal used:          {format_inches(sample.vent_reveal)}")
        lines.append(f"Wood count mode:           {self.mode_var.get()}")
        lines.append(f"Vent strips across depth:  {sample.vent_count}")
        lines.append(f"Rip placement:             {sample.rip_placement}")
        lines.append(f"Math check:                {'PASS' if math_check.passed else 'FAIL'}")
        lines.append("")
        lines.append("CURRENT SAMPLE COURSE ORDER")
        lines.append("-" * 72)
        for i, c in enumerate(sample.courses, start=1):
            lines.append(f"{i:>2}. {c.kind.upper():<5} {format_inches(c.width):>8}   {c.label}")
        lines.append("")
        lines.append("23 IN / 24 IN WHOLE-JOB SPLIT")
        lines.append("-" * 72)
        lines.append(f"23 in soffit LF:           {lf_23:.1f} LF")
        lines.append(f"24 in entrance LF:         {lf_24:.1f} LF")
        lines.append(f"Total measured LF:         {total_lf:.1f} LF")
        lines.append(f"23 in wood courses/run:    {wood_courses_per_run(layout_23)} ({layout_23.wood_count} full + {layout_23.rip_count} rip)")
        lines.append(f"24 in wood courses/run:    {wood_courses_per_run(layout_24)} ({layout_24.wood_count} full + {layout_24.rip_count} rip)")
        lines.append(f"Wood LF required/no waste: {allocation.required_lf:.1f} LF")
        lines.append(f"Vent LF required/no waste: {vent_lf:.1f} LF")
        lines.append("")
        lines.append("NO-WASTE PIECE ALLOCATION, USING 12' THEN 11' THEN 6'")
        lines.append("-" * 72)
        lines.append(f"Used:                      {allocation.used_12} @ 12', {allocation.used_11} @ 11', {allocation.used_6} @ 6'")
        lines.append(f"Left over full pieces:     {allocation.left_12} @ 12', {allocation.left_11} @ 11', {allocation.left_6} @ 6'")
        lines.append(f"Gross LF consumed:         {allocation.gross_used_lf:.1f} LF")
        lines.append(f"Unused full-piece LF:      {allocation.unused_piece_lf:.1f} LF")
        lines.append(f"Offcut/rounding overage:   {allocation.overage_from_used_pieces_lf:.1f} LF")
        if allocation.shortage_lf > 0:
            lines.append(f"SHORTAGE:                  {allocation.shortage_lf:.1f} LF")
        lines.append("")
        lines.append("WHOLE-JOB MATERIAL CHECK")
        lines.append("-" * 72)
        lines.append(f"Wood order total LF:       {inventory.total_lf:.0f} LF")
        lines.append(f"Gross reveal coverage:     {inventory.gross_coverage_sqft:.1f} sq ft")
        lines.append(f"Usable after {waste:g}% waste:   {inventory.usable_coverage_sqft:.1f} sq ft")
        lines.append(f"Planned area by split:     {inventory.planned_area_sqft:.1f} sq ft")
        lines.append(f"Surplus after waste:       {inventory.surplus_sqft_after_waste:.1f} sq ft ({inventory.surplus_percent_after_waste:.1f}%)")
        lines.append("")
        lines.append("NOTE")
        lines.append("-" * 72)
        lines.append("- No-waste piece allocation is a starting estimate only. Actual cutting will need extra for joints, stagger, defects, mitres, mistakes, and usable offcuts.")
        lines.append("- The floorplan image is useful for layout context, but exact LF should come from measured soffit runs rather than the screenshot scale.")
        self.summary_text.delete("1.0", tk.END)
        self.summary_text.insert(tk.END, "\n".join(lines))

    def layout_card_lines(self, label: str, layout: Layout, lf: float) -> List[str]:
        wood_courses = wood_courses_per_run(layout)
        return [
            f"{label}",
            f"  LF: {lf:.1f}",
            f"  Wood courses/run: {wood_courses}",
            f"  Full/rip: {layout.wood_count}/{layout.rip_count}",
            f"  Rip width: {format_inches(layout.rip_width)}",
            f"  Wood LF: {wood_courses * lf:.1f}",
            f"  Vent LF: {layout.vent_count * lf:.1f}",
        ]

    def comparison_lines(self, wood: float, vent: float, vent_count: int, mode: str, manual_wood: int, vent_position: int, min_rip: float, tolerance: float, lf_23: float, lf_24: float, pcs_12: int, pcs_11: int, pcs_6: int) -> List[str]:
        lines = []
        lines.append("RIP-PLACEMENT COMPARISON, NO WASTE")
        lines.append("-" * 58)
        for rip in ["Both sides balanced", "One side - wall/left", "One side - fascia/right"]:
            try:
                l23 = calculate_layout(23.0, wood, vent, vent_count, mode, manual_wood, vent_position, rip, min_rip, tolerance)
                l24 = calculate_layout(24.0, wood, vent, vent_count, mode, manual_wood, vent_position, rip, min_rip, tolerance)
                required = combined_required_wood_lf(l23, lf_23, l24, lf_24)
                alloc = allocate_pieces_no_waste(required, pcs_12, pcs_11, pcs_6)
                lines.append(rip)
                lines.append(f"  23in courses: {wood_courses_per_run(l23)} | 24in courses: {wood_courses_per_run(l24)}")
                lines.append(f"  Wood LF req:  {required:.1f}")
                lines.append(f"  Use pieces:   {alloc.used_12}@12, {alloc.used_11}@11, {alloc.used_6}@6")
                lines.append(f"  Left pieces:  {alloc.left_12}@12, {alloc.left_11}@11, {alloc.left_6}@6")
            except Exception as exc:
                lines.append(f"{rip}: ERROR {exc}")
            lines.append("")
        return lines

    def write_calculation_block(
        self,
        sample: Layout,
        layout_23: Layout,
        layout_24: Layout,
        inventory: Inventory,
        allocation: PieceAllocation,
        lf_23: float,
        lf_24: float,
        waste: float,
        math_check: MathCheck,
    ) -> None:
        depth, wood, vent, vent_count, manual_wood, min_rip, tolerance, _lf23, _lf24, pcs_12, pcs_11, pcs_6, _waste = self.read_inputs()
        lines: List[str] = []
        lines.append("MATH CHECK")
        lines.append("-" * 58)
        lines.extend(self.math_check_lines(math_check, "Current sample"))
        lines.append("")
        lines.extend(self.math_check_lines(verify_layout_math(layout_23, tolerance), "23 in standard"))
        lines.append("")
        lines.extend(self.math_check_lines(verify_layout_math(layout_24, tolerance), "24 in entrance"))
        lines.append("")
        lines.append("NO-WASTE PIECE ESTIMATE")
        lines.append("-" * 58)
        lines.append(f"Required wood LF: {allocation.required_lf:.1f}")
        lines.append(f"Inventory LF:     {inventory.total_lf:.1f}")
        lines.append(f"Used pieces:      {allocation.used_12}@12', {allocation.used_11}@11', {allocation.used_6}@6'")
        lines.append(f"Left pieces:      {allocation.left_12}@12', {allocation.left_11}@11', {allocation.left_6}@6'")
        lines.append(f"Unused full LF:   {allocation.unused_piece_lf:.1f}")
        lines.append(f"Offcut overage:   {allocation.overage_from_used_pieces_lf:.1f}")
        if allocation.shortage_lf > 0:
            lines.append(f"SHORTAGE LF:      {allocation.shortage_lf:.1f}")
        lines.append("")
        lines.append("23 / 24 DEPTH CARDS")
        lines.append("-" * 58)
        lines.extend(self.layout_card_lines("23 in main house", layout_23, lf_23))
        lines.append("")
        lines.extend(self.layout_card_lines("24 in entrance", layout_24, lf_24))
        lines.append("")
        lines.extend(self.comparison_lines(wood, vent, vent_count, self.mode_var.get(), manual_wood, self.vent_position_var.get(), min_rip, tolerance, lf_23, lf_24, pcs_12, pcs_11, pcs_6))
        lines.append("AREA / COVERAGE")
        lines.append("-" * 58)
        lines.append(f"23in area: {lf_23:.1f} x 23/12 = {lf_23 * 23 / 12:.1f} sq ft")
        lines.append(f"24in area: {lf_24:.1f} x 24/12 = {lf_24 * 24 / 12:.1f} sq ft")
        lines.append(f"Plan area: {inventory.planned_area_sqft:.1f} sq ft")
        lines.append(f"Gross wood coverage: {inventory.gross_coverage_sqft:.1f} sq ft")
        lines.append(f"After {waste:g}% waste: {inventory.usable_coverage_sqft:.1f} sq ft")
        lines.append(f"Enough after waste? {'YES' if inventory.surplus_sqft_after_waste >= 0 else 'NO'}")
        self.calc_text.delete("1.0", tk.END)
        self.calc_text.insert(tk.END, "\n".join(lines))

    def copy_summary(self) -> None:
        left = self.summary_text.get("1.0", tk.END).strip()
        right = self.calc_text.get("1.0", tk.END).strip()
        text = left + "\n\n" + right if right else left
        if not text.strip():
            messagebox.showinfo("Copy Summary", "No summary to copy yet.")
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.root.update()
        messagebox.showinfo("Copy Summary", "Summary and calculation block copied to clipboard.")


def main() -> None:
    root = tk.Tk()
    SoffitVisualizer(root)
    root.mainloop()


if __name__ == "__main__":
    main()

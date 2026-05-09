#!/usr/bin/env python3
"""
light_planner.py — Interactive soffit/wall/camera light placement editor.

Usage:
    python3 light_planner.py

Requires (for SVG background):
    pip install cairosvg Pillow
"""
import os, sys

# Re-exec with Homebrew lib path so cairocffi's dlopen finds libcairo on macOS.
# Must happen before any other imports. Guarded by sentinel env var to avoid loops.
if sys.platform == "darwin" and not os.environ.get("_PLANNER_REEXEC") and os.path.isfile(sys.argv[0] if sys.argv else ""):
    brew_lib = "/opt/homebrew/lib"
    local_lib = "/usr/local/lib"
    dyld = os.environ.get("DYLD_LIBRARY_PATH", "")
    if brew_lib not in dyld:
        env = os.environ.copy()
        env["DYLD_LIBRARY_PATH"] = f"{brew_lib}:{local_lib}:{dyld}".rstrip(":")
        env["_PLANNER_REEXEC"] = "1"
        os.execve(sys.executable, [sys.executable] + sys.argv, env)

import json, io, subprocess, math, re

UNITS_PER_INCH = 1.3   # canvas units per inch (used for dimension label computation)

def _units_to_imperial(units: float) -> str:
    total_in = abs(units) / UNITS_PER_INCH
    feet = int(total_in // 12)
    inches = total_in % 12
    q = round(inches * 4) / 4
    if q >= 12:
        feet += 1; q = 0.0
    frac = {0.0:"", 0.25:"¼", 0.5:"½", 0.75:"¾"}.get(q - int(q), "")
    return f"{feet}'{int(q)}{frac}\""
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
LIGHTS_JSON = os.path.join(BASE_DIR, "perimeter_lights.json")
DIM_JSON    = os.path.join(BASE_DIR, "dimension_lines.json")
GRID_SVG    = os.path.join(BASE_DIR, "floorplan_grid.svg")
ANNOT_SVG   = os.path.join(BASE_DIR, "floorplan_annotated.svg")
SCRIPTS_DIR = os.path.join(BASE_DIR, "scripts")

# ── Scale / viewBox ──────────────────────────────────────────────────────────
UNITS_PER_FOOT = 15.6          # 1.3 units/inch × 12 inches
VB_X, VB_Y, VB_W, VB_H = -150, -150, 1100, 1400   # matches create_grid_floorplan.py

# ── Visual config per light type ─────────────────────────────────────────────
LIGHT_CFG = {
    "soffit": {"color": "#FF0000", "outline": "#FFFFFF", "shape": "circle", "r": 8},
    "wall":   {"color": "#00D2FF", "outline": "#FFFFFF", "shape": "rect",   "r": 8},
    "camera": {"color": "#FF8C00", "outline": "#FFFFFF", "shape": "star",   "r": 13},
}

STAR_PTS_SVG = "0,-10.5 3,-4 10.5,-4 5,1 6,8.5 0,4.5 -6,8.5 -5,1 -10.5,-4 -3,-4"

def zone_type(name: str) -> str:
    if name == "Wall lights":
        return "wall"
    if name == "Security Cameras":
        return "camera"
    return "soffit"


# ── Main application ──────────────────────────────────────────────────────────
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Soffit Light Planner")
        self.geometry("1350x920")
        self.minsize(900, 600)

        # ── Load JSON data ──
        with open(LIGHTS_JSON) as f:
            raw = json.load(f)
        with open(DIM_JSON) as f:
            self._dims = json.load(f)

        # zones: {zone_name: [{x, y}, ...]}
        self.zones = {k: [dict(p) for p in v] for k, v in raw.items()}

        # ── UI state ──
        self.mode      = tk.StringVar(value="select")
        self.add_type  = tk.StringVar(value="soffit")
        self.zone_var  = tk.StringVar()
        self.snap_ft   = tk.DoubleVar(value=1.0)

        self.sel_label  = tk.StringVar()   # editable dim label
        self._zoom      = 1.0
        self.zoom_label = tk.StringVar(value="100%")

        self._selected         = None   # (zone, idx) or None  — light selection
        self._drag_mouse_start = None   # (px, py) on press
        self._drag_svg_origin  = None   # (sx, sy) of light on press

        # Dimension handle selection: (dim_id, "p1"|"p2"|"line") or None
        self._sel_dim          = None
        self._dim_drag_origin  = None   # dict snapshot of {x1,y1,x2,y2} on press

        self.show_dims = tk.BooleanVar(value=True)

        # ── Canvas rendering state ──
        self._render_w   = VB_W
        self._render_h   = VB_H
        self._off_x      = 0.0
        self._off_y      = 0.0
        self._bg_photo   = None
        self._item_map   = {}   # canvas item id → (zone, idx)
        self._dim_item_map = {} # canvas item id → (dim_id, "p1"|"p2"|"line")

        # ── Optional: cairosvg + Pillow ──
        try:
            from PIL import Image, ImageTk
            import cairosvg
            self._PIL    = Image
            self._ITK    = ImageTk
            self._cairo  = cairosvg
            self._has_render = True
        except (ImportError, OSError):
            self._has_render = False

        self._build_ui()
        self._refresh_zone_combo()
        self.after(120, self._initial_render)

    # ── Coordinate transforms ─────────────────────────────────────────────────
    def _svg_to_px(self, sx, sy):
        cx = (sx - VB_X) / VB_W * self._render_w + self._off_x
        cy = (sy - VB_Y) / VB_H * self._render_h + self._off_y
        return cx, cy

    def _px_to_svg(self, cx, cy):
        sx = (cx - self._off_x) / self._render_w * VB_W + VB_X
        sy = (cy - self._off_y) / self._render_h * VB_H + VB_Y
        return sx, sy

    def _snap(self, v):
        s = self.snap_ft.get() * UNITS_PER_FOOT
        return round(v / s) * s if s > 0 else v

    # ── UI construction ───────────────────────────────────────────────────────
    def _build_ui(self):
        self.columnconfigure(0, weight=3)
        self.columnconfigure(1, weight=0)
        self.rowconfigure(0, weight=1)

        # ── Menu bar ──────────────────────────────────────────────────────────
        menubar = tk.Menu(self)
        self.configure(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Save & Refresh SVG",
                              accelerator="Cmd+S" if sys.platform == "darwin" else "Ctrl+S",
                              command=self._save)
        file_menu.add_separator()
        file_menu.add_command(label="Quit", accelerator="Cmd+Q" if sys.platform == "darwin" else "Alt+F4",
                              command=self.quit)

        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Zoom In  (+)",   command=lambda: self._zoom_by(1.3))
        view_menu.add_command(label="Zoom Out  (−)",  command=lambda: self._zoom_by(1/1.3))
        view_menu.add_command(label="Reset Zoom  (0)", command=self._zoom_reset)
        view_menu.add_separator()
        view_menu.add_checkbutton(label="Show Dim Handles",
                                  variable=self.show_dims,
                                  command=self._render_lights)

        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Delete Selected  [Del]", command=self._delete_selected)
        edit_menu.add_command(label="Edit Dimensions...",     command=self._open_dim_editor)

        # ── Canvas pane ──
        cf = ttk.Frame(self)
        cf.grid(row=0, column=0, sticky="nsew")
        cf.rowconfigure(0, weight=1)
        cf.columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(cf, bg="#c8c8c8", cursor="arrow", highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        ys = ttk.Scrollbar(cf, orient="vertical",   command=self.canvas.yview)
        xs = ttk.Scrollbar(cf, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=ys.set, xscrollcommand=xs.set)
        ys.grid(row=0, column=1, sticky="ns")
        xs.grid(row=1, column=0, sticky="ew")

        self.canvas.bind("<Configure>",       self._on_resize)
        self.canvas.bind("<ButtonPress-1>",   self._on_press)
        self.canvas.bind("<B1-Motion>",       self._on_motion)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<Button-3>",        self._on_rclick)

        # ── Control panel ──
        panel = ttk.Frame(self, padding=8, width=230)
        panel.grid(row=0, column=1, sticky="nsew")
        panel.columnconfigure(0, weight=1)
        panel.grid_propagate(False)

        r = 0
        def sep():
            nonlocal r
            ttk.Separator(panel, orient="horizontal").grid(
                row=r, column=0, sticky="ew", pady=4); r += 1

        def hdr(text):
            nonlocal r
            ttk.Label(panel, text=text, font=("", 9, "bold")).grid(
                row=r, column=0, sticky="w"); r += 1

        # ── Save at top — always visible ──────────────────────────────────────
        save_btn = tk.Button(panel, text="Save & Refresh SVG",
                             command=self._save,
                             bg="#2a7a2a", fg="white",
                             font=("", 11, "bold"),
                             relief="raised", bd=2, padx=4, pady=6,
                             activebackground="#1e5c1e", activeforeground="white")
        save_btn.grid(row=r, column=0, sticky="ew"); r += 1

        self.status_var = tk.StringVar(value="Ready — Cmd+S to save")
        ttk.Label(panel, textvariable=self.status_var,
                  font=("", 8), foreground="darkgreen",
                  wraplength=210).grid(row=r, column=0, sticky="nw"); r += 1

        sep()

        # Mode
        hdr("Mode  (A = Add   S = Select)")
        mf = ttk.Frame(panel); mf.grid(row=r, column=0, sticky="ew"); r += 1
        ttk.Radiobutton(mf, text="Select/Move",  variable=self.mode, value="select",
                        command=self._on_mode_change).pack(side="left")
        ttk.Radiobutton(mf, text="Add",          variable=self.mode, value="add",
                        command=self._on_mode_change).pack(side="left")

        sep()
        hdr("Light Type")
        for val, label in [("soffit","● Soffit Light"), ("wall","■ Wall Light"), ("camera","★ Security Camera")]:
            ttk.Radiobutton(panel, text=label, variable=self.add_type, value=val,
                            command=self._on_type_change).grid(row=r, column=0, sticky="w"); r += 1

        sep()
        hdr("Zone")
        self.zone_combo = ttk.Combobox(panel, textvariable=self.zone_var, width=26)
        self.zone_combo.grid(row=r, column=0, sticky="ew"); r += 1
        zf = ttk.Frame(panel); zf.grid(row=r, column=0, sticky="ew"); r += 1
        ttk.Button(zf, text="New Zone",  command=self._new_zone,  width=12).pack(side="left", padx=(0,2))
        ttk.Button(zf, text="Del Zone",  command=self._del_zone,  width=12).pack(side="left")

        sep()
        hdr("Snap Grid")
        sf = ttk.Frame(panel); sf.grid(row=r, column=0, sticky="ew"); r += 1
        for v, lbl in [(0.5,"½ft"), (1.0,"1ft"), (2.0,"2ft"), (0,"Off")]:
            ttk.Radiobutton(sf, text=lbl, variable=self.snap_ft, value=v).pack(side="left")

        sep()
        hdr("Zoom  (scroll wheel)")
        zf2 = ttk.Frame(panel); zf2.grid(row=r, column=0, sticky="ew"); r += 1
        ttk.Button(zf2, text="−",     command=lambda: self._zoom_by(1/1.3), width=3).pack(side="left")
        ttk.Button(zf2, text="Reset", command=self._zoom_reset,              width=6).pack(side="left", padx=2)
        ttk.Button(zf2, text="+",     command=lambda: self._zoom_by(1.3),   width=3).pack(side="left")
        ttk.Label(zf2, textvariable=self.zoom_label, width=6).pack(side="left", padx=4)

        sep()
        hdr("Light Counts")
        self.counts_var = tk.StringVar()
        ttk.Label(panel, textvariable=self.counts_var, justify="left",
                  font=("Courier", 9)).grid(row=r, column=0, sticky="nw"); r += 1

        sep()
        hdr("Selected")
        self.sel_info = tk.StringVar(value="—")
        ttk.Label(panel, textvariable=self.sel_info, justify="left",
                  font=("Courier", 9)).grid(row=r, column=0, sticky="nw"); r += 1

        # Position / label editor
        pf = ttk.LabelFrame(panel, text="Position (canvas units)")
        pf.grid(row=r, column=0, sticky="ew", pady=2); r += 1
        pf.columnconfigure(1, weight=1)
        self.sel_x = tk.DoubleVar()
        self.sel_y = tk.DoubleVar()
        ttk.Label(pf, text="X:").grid(row=0, column=0, sticky="e")
        ttk.Entry(pf, textvariable=self.sel_x, width=9).grid(row=0, column=1, sticky="ew", padx=2)
        ttk.Label(pf, text="Y:").grid(row=1, column=0, sticky="e")
        ttk.Entry(pf, textvariable=self.sel_y, width=9).grid(row=1, column=1, sticky="ew", padx=2)
        ttk.Label(pf, text="Label:").grid(row=2, column=0, sticky="e")
        self._label_entry = ttk.Entry(pf, textvariable=self.sel_label, width=9)
        self._label_entry.grid(row=2, column=1, sticky="ew", padx=2)
        ttk.Label(pf, text="(dim only)", font=("",7)).grid(row=3, column=1, sticky="w")
        ttk.Button(pf, text="Apply", command=self._apply_coord).grid(
            row=4, column=0, columnspan=2, pady=3)

        sep()
        ttk.Button(panel, text="Delete Selected  [Del]",
                   command=self._delete_selected).grid(row=r, column=0, sticky="ew"); r += 1
        ttk.Checkbutton(panel, text="Show Dim Handles",
                        variable=self.show_dims,
                        command=self._render_lights).grid(row=r, column=0, sticky="w"); r += 1
        ttk.Button(panel, text="Edit Dimensions...",
                   command=self._open_dim_editor).grid(row=r, column=0, sticky="ew"); r += 1

        # ── Keyboard shortcuts ──
        self.bind("<Delete>",    lambda _: self._delete_selected())
        self.bind("<BackSpace>", lambda _: self._delete_selected())
        self.bind("<Escape>",    lambda _: self._deselect())
        self.bind("a",           lambda _: (self.mode.set("add"),    self._on_mode_change()))
        self.bind("s",           lambda _: (self.mode.set("select"), self._on_mode_change()))
        self.bind("+",           lambda _: self._zoom_by(1.3))
        self.bind("-",           lambda _: self._zoom_by(1/1.3))
        self.bind("0",           lambda _: self._zoom_reset())
        save_key = "<Command-s>" if sys.platform == "darwin" else "<Control-s>"
        self.bind(save_key, lambda _: self._save())
        self.canvas.bind("<MouseWheel>", self._on_mouse_wheel)
        self.canvas.bind("<Button-4>",   lambda e: self._zoom_at(self.canvas.canvasx(e.x), self.canvas.canvasy(e.y), 1.1))
        self.canvas.bind("<Button-5>",   lambda e: self._zoom_at(self.canvas.canvasx(e.x), self.canvas.canvasy(e.y), 1/1.1))

    # ── Render cycle ─────────────────────────────────────────────────────────
    def _initial_render(self):
        self._on_resize(None)

    def _on_resize(self, _event):
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w < 10 or h < 10:
            return
        base  = min(w / VB_W, h / VB_H) * 0.96
        scale = base * self._zoom
        self._render_w = int(VB_W * scale)
        self._render_h = int(VB_H * scale)
        self._off_x    = (w - self._render_w) / 2
        self._off_y    = (h - self._render_h) / 2
        self._update_scrollregion()
        self._render_bg()
        self._render_lights()

    def _update_scrollregion(self):
        w = self.canvas.winfo_width() or 800
        h = self.canvas.winfo_height() or 900
        pad = 60
        self.canvas.configure(scrollregion=(
            min(-pad, self._off_x - pad),
            min(-pad, self._off_y - pad),
            max(w + pad, self._off_x + self._render_w + pad),
            max(h + pad, self._off_y + self._render_h + pad),
        ))

    def _zoom_at(self, px, py, factor):
        sx, sy = self._px_to_svg(px, py)
        self._zoom = max(0.25, min(8.0, self._zoom * factor))
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        base  = min(w / VB_W, h / VB_H) * 0.96
        scale = base * self._zoom
        self._render_w = int(VB_W * scale)
        self._render_h = int(VB_H * scale)
        self._off_x = px - (sx - VB_X) / VB_W * self._render_w
        self._off_y = py - (sy - VB_Y) / VB_H * self._render_h
        self._update_scrollregion()
        self.zoom_label.set(f"{int(self._zoom * 100)}%")
        self._render_bg()
        self._render_lights()

    def _zoom_by(self, factor):
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        self._zoom_at(w / 2, h / 2, factor)

    def _zoom_reset(self):
        self._zoom = 1.0
        self.zoom_label.set("100%")
        self._on_resize(None)

    def _on_mouse_wheel(self, event):
        factor = 1.1 ** (event.delta / 120)
        self._zoom_at(self.canvas.canvasx(event.x), self.canvas.canvasy(event.y), factor)

    def _render_bg(self):
        self.canvas.delete("bg")
        if not self._has_render:
            self.canvas.create_rectangle(
                self._off_x, self._off_y,
                self._off_x + self._render_w, self._off_y + self._render_h,
                fill="#f0ede0", outline="#888", tags="bg")
            self.canvas.create_text(
                self._off_x + self._render_w / 2, self._off_y + self._render_h / 2,
                text="SVG background requires:\npip install cairosvg Pillow",
                justify="center", font=("", 12), fill="#555", tags="bg")
            return
        try:
            src = GRID_SVG if os.path.exists(GRID_SVG) else ANNOT_SVG
            with open(src, encoding="utf-8") as f:
                svg_content = f.read()
            # Strip baked dim arrows — canvas handles are authoritative
            svg_content = re.sub(
                r'<!-- DIMENSION ARROWS -->.*?<!-- /DIMENSION ARROWS -->',
                '', svg_content, flags=re.DOTALL)
            # Render at 2× for crisp display, then downsample with LANCZOS
            scale = 2
            png = self._cairo.svg2png(
                bytestring=svg_content.encode(),
                output_width=self._render_w * scale,
                output_height=self._render_h * scale)
            if not png:
                return
            resample = getattr(getattr(self._PIL, "Resampling", self._PIL), "LANCZOS", 1)
            img = self._PIL.open(io.BytesIO(png)).resize(
                (self._render_w, self._render_h), resample)
            self._bg_photo = self._ITK.PhotoImage(img)
            self.canvas.create_image(
                self._off_x, self._off_y,
                image=self._bg_photo, anchor="nw", tags="bg")
        except Exception as ex:
            self.status_var.set(f"BG render error: {ex}")

    def _render_lights(self):
        self.canvas.delete("light")
        self.canvas.delete("dim")
        self._item_map     = {}
        self._dim_item_map = {}
        if self.show_dims.get():
            self._render_dims()
        for zone, pts in self.zones.items():
            ltype = zone_type(zone)
            for idx, pt in enumerate(pts):
                self._draw_light(zone, idx, pt["x"], pt["y"], ltype)
        self._update_counts()

    def _render_dims(self):
        for d in self._dims.get("dimensions", []):
            if not d.get("visible", True):
                continue
            did    = d["id"]
            color  = d.get("color", "#0055cc")
            x1, y1 = d["x1"], d["y1"]
            x2, y2 = d["x2"], d["y2"]

            p1x, p1y = self._svg_to_px(x1, y1)
            p2x, p2y = self._svg_to_px(x2, y2)

            sel_id, sel_end = (self._sel_dim or (None, None))
            any_sel  = (did == sel_id)
            line_sel = (did == sel_id and sel_end == "line")
            p1_sel   = (did == sel_id and sel_end == "p1")
            p2_sel   = (did == sel_id and sel_end == "p2")

            draw_color = "#FFFF00" if any_sel else color
            lw = 2.0 if any_sel else 1.5

            # ── Double-headed arrow line ──────────────────────────────────
            lid = self.canvas.create_line(
                p1x, p1y, p2x, p2y,
                fill=draw_color, width=lw,
                arrow=tk.BOTH, arrowshape=(9, 11, 4),
                tags="dim")
            self._dim_item_map[lid] = (did, "line")

            # ── Endpoint diamond handles (drawn before label so label is on top) ──
            for hx, hy, end, is_sel in [(p1x, p1y, "p1", p1_sel),
                                         (p2x, p2y, "p2", p2_sel)]:
                r  = 7
                fc = "#FFFF00" if is_sel else color
                oc = "#FFFFFF" if is_sel else "#222222"
                dpts = [hx, hy-r, hx+r, hy, hx, hy+r, hx-r, hy]
                hid = self.canvas.create_polygon(
                    dpts, fill=fc, outline=oc, width=1.5, tags="dim")
                self._dim_item_map[hid] = (did, end)

            # ── Midpoint circle handle (move whole arrow) ─────────────────
            mmx, mmy = (p1x+p2x)/2, (p1y+p2y)/2
            mr = 5
            fc = "#FFFF00" if line_sel else "#FFFFFF"
            oc = "#FFFF00" if line_sel else color
            mid = self.canvas.create_oval(
                mmx-mr, mmy-mr, mmx+mr, mmy+mr,
                fill=fc, outline=oc, width=2, tags="dim")
            self._dim_item_map[mid] = (did, "line")

            # ── Dimension label (drawn last = on top of handles) ──────────
            dx_svg = x2 - x1
            dy_svg = y2 - y1
            len_svg = math.hypot(dx_svg, dy_svg)
            if len_svg > 0:
                perp_x = -dy_svg / len_svg
                perp_y =  dx_svg / len_svg
                offset = d.get("label_offset", -20)
                lsx = (x1+x2)/2 + perp_x * offset
                lsy = (y1+y2)/2 + perp_y * offset
                lx, ly = self._svg_to_px(lsx, lsy)

                label = d.get("label") or _units_to_imperial(len_svg)

                angle_deg = math.degrees(math.atan2(p2y - p1y, p2x - p1x))
                if angle_deg > 90 or angle_deg < -90:
                    angle_deg += 180

                font = ("Arial", 11, "bold")
                for dx2, dy2 in [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(1,-1),(-1,1),(1,1)]:
                    self.canvas.create_text(
                        lx+dx2, ly+dy2, text=label, font=font,
                        fill="white", angle=angle_deg, tags="dim")
                self.canvas.create_text(
                    lx, ly, text=label, font=font,
                    fill=draw_color, angle=angle_deg, tags="dim")

    def _dim_hit_test(self, px, py):
        tol = 10
        items = self.canvas.find_overlapping(px-tol, py-tol, px+tol, py+tol)
        for iid in reversed(items):
            if iid in self._dim_item_map:
                return self._dim_item_map[iid]
        return None

    def _draw_light(self, zone, idx, sx, sy, ltype):
        cx, cy = self._svg_to_px(sx, sy)
        cfg = LIGHT_CFG[ltype]
        r   = cfg["r"]
        sel = (self._selected == (zone, idx))
        outline = "#FFFF00" if sel else cfg["outline"]
        ow      = 3.0      if sel else 1.5

        if cfg["shape"] == "circle":
            iid = self.canvas.create_oval(
                cx-r, cy-r, cx+r, cy+r,
                fill=cfg["color"], outline=outline, width=ow, tags="light")
        elif cfg["shape"] == "rect":
            iid = self.canvas.create_rectangle(
                cx-r, cy-r, cx+r, cy+r,
                fill=cfg["color"], outline=outline, width=ow, tags="light")
        else:
            pts = self._star_pts(cx, cy, r, r * 0.4)
            iid = self.canvas.create_polygon(
                pts, fill=cfg["color"], outline=outline, width=ow, tags="light")

        self._item_map[iid] = (zone, idx)

    @staticmethod
    def _star_pts(cx, cy, outer, inner, n=5):
        pts = []
        for i in range(n * 2):
            a = math.pi * i / n - math.pi / 2
            r = outer if i % 2 == 0 else inner
            pts += [cx + r * math.cos(a), cy + r * math.sin(a)]
        return pts

    # ── Event handlers ────────────────────────────────────────────────────────
    def _on_mode_change(self):
        self.canvas.configure(cursor="crosshair" if self.mode.get() == "add" else "arrow")
        self._deselect()

    def _on_type_change(self):
        ltype = self.add_type.get()
        if ltype == "wall":
            self.zone_var.set("Wall lights")
        elif ltype == "camera":
            self.zone_var.set("Security Cameras")
        else:
            soffit_zones = [z for z in self.zones if zone_type(z) == "soffit"]
            if soffit_zones and self.zone_var.get() not in soffit_zones:
                self.zone_var.set(soffit_zones[0])

    def _hit_test(self, px, py):
        tol = 10
        items = self.canvas.find_overlapping(px-tol, py-tol, px+tol, py+tol)
        for iid in reversed(items):
            if iid in self._item_map:
                return self._item_map[iid]
        return None

    def _on_press(self, event):
        px = self.canvas.canvasx(event.x)
        py = self.canvas.canvasy(event.y)

        if self.mode.get() == "add":
            sx = self._snap(self._px_to_svg(px, py)[0])
            sy = self._snap(self._px_to_svg(px, py)[1])
            zone = self.zone_var.get()
            if not zone:
                messagebox.showwarning("No Zone", "Select or create a zone first.")
                return
            if zone not in self.zones:
                self.zones[zone] = []
            self.zones[zone].append({"x": round(sx, 1), "y": round(sy, 1)})
            self._refresh_zone_combo()
            self._render_lights()
            return

        # Select mode — lights first, then dim handles
        hit = self._hit_test(px, py)
        if hit:
            zone, idx = hit
            pt = self.zones[zone][idx]
            self._selected          = hit
            self._sel_dim           = None
            self._drag_mouse_start  = (px, py)
            self._drag_svg_origin   = (pt["x"], pt["y"])
            self.sel_x.set(round(pt["x"], 1))
            self.sel_y.set(round(pt["y"], 1))
            self.sel_info.set(f"Zone: {zone}\nIdx:  {idx}\nX: {pt['x']:.1f}  Y: {pt['y']:.1f}")
        else:
            dim_hit = self._dim_hit_test(px, py) if self.show_dims.get() else None
            if dim_hit:
                did, end = dim_hit
                d = next((x for x in self._dims["dimensions"] if x["id"] == did), None)
                if d:
                    self._sel_dim          = (did, end)
                    self._selected         = None
                    self._drag_mouse_start = (px, py)
                    self._dim_drag_origin  = {k: d[k] for k in ("x1","y1","x2","y2")}
                    stored_label = d.get("label") or _units_to_imperial(
                        math.hypot(d["x2"]-d["x1"], d["y2"]-d["y1"]))
                    self.sel_label.set(stored_label)
                    if end == "p1":
                        self.sel_x.set(round(d["x1"], 1))
                        self.sel_y.set(round(d["y1"], 1))
                        self.sel_info.set(f"Dim: {did}\nHandle: P1\nX: {d['x1']:.1f}  Y: {d['y1']:.1f}")
                    elif end == "p2":
                        self.sel_x.set(round(d["x2"], 1))
                        self.sel_y.set(round(d["y2"], 1))
                        self.sel_info.set(f"Dim: {did}\nHandle: P2\nX: {d['x2']:.1f}  Y: {d['y2']:.1f}")
                    else:
                        mx, my = (d["x1"]+d["x2"])/2, (d["y1"]+d["y2"])/2
                        self.sel_x.set(round(mx, 1))
                        self.sel_y.set(round(my, 1))
                        self.sel_info.set(f"Dim: {did}\nHandle: Line\nDrag to move arrow")
            else:
                self._deselect()
        self._render_lights()

    def _on_motion(self, event):
        if self.mode.get() != "select" or not self._drag_mouse_start:
            return
        epx = self.canvas.canvasx(event.x)
        epy = self.canvas.canvasy(event.y)

        if self._selected:
            sx = self._snap(self._px_to_svg(epx, epy)[0])
            sy = self._snap(self._px_to_svg(epx, epy)[1])
            zone, idx = self._selected
            self.zones[zone][idx].update({"x": round(sx, 1), "y": round(sy, 1)})
            self.sel_x.set(round(sx, 1))
            self.sel_y.set(round(sy, 1))
            self.sel_info.set(f"Zone: {zone}\nIdx:  {idx}\nX: {sx:.1f}  Y: {sy:.1f}")
            self._render_lights()

        elif self._sel_dim and self._dim_drag_origin:
            did, end = self._sel_dim
            d = next((x for x in self._dims["dimensions"] if x["id"] == did), None)
            if not d:
                return
            orig = self._dim_drag_origin
            sx = self._px_to_svg(epx, epy)[0]
            sy = self._px_to_svg(epx, epy)[1]
            if end == "p1":
                d["x1"] = round(self._snap(sx), 1)
                d["y1"] = round(self._snap(sy), 1)
                self.sel_x.set(d["x1"]); self.sel_y.set(d["y1"])
                self.sel_info.set(f"Dim: {did}\nHandle: P1\nX: {d['x1']:.1f}  Y: {d['y1']:.1f}")
            elif end == "p2":
                d["x2"] = round(self._snap(sx), 1)
                d["y2"] = round(self._snap(sy), 1)
                self.sel_x.set(d["x2"]); self.sel_y.set(d["y2"])
                self.sel_info.set(f"Dim: {did}\nHandle: P2\nX: {d['x2']:.1f}  Y: {d['y2']:.1f}")
            else:
                # Move whole arrow: compute delta from drag origin
                mpx, mpy = self._drag_mouse_start
                orig_sx, orig_sy = self._px_to_svg(mpx, mpy)
                dx = sx - orig_sx
                dy = sy - orig_sy
                d["x1"] = round(orig["x1"] + dx, 1)
                d["y1"] = round(orig["y1"] + dy, 1)
                d["x2"] = round(orig["x2"] + dx, 1)
                d["y2"] = round(orig["y2"] + dy, 1)
                mx, my = (d["x1"]+d["x2"])/2, (d["y1"]+d["y2"])/2
                self.sel_x.set(round(mx, 1)); self.sel_y.set(round(my, 1))
                self.sel_info.set(f"Dim: {did}\nHandle: Line\nMid: {mx:.1f}, {my:.1f}")
            self._render_lights()

    def _on_release(self, _event):
        self._drag_mouse_start = None
        self._drag_svg_origin  = None
        self._dim_drag_origin  = None

    def _on_rclick(self, event):
        px = self.canvas.canvasx(event.x)
        py = self.canvas.canvasy(event.y)
        hit = self._hit_test(px, py)
        if not hit:
            return
        self._selected = hit
        self._render_lights()
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Delete Light", command=self._delete_selected)
        menu.post(event.x_root, event.y_root)

    def _deselect(self):
        self._selected = None
        self._sel_dim  = None
        self.sel_info.set("—")
        self._render_lights()

    def _delete_selected(self):
        if not self._selected:
            return
        zone, idx = self._selected
        del self.zones[zone][idx]
        if not self.zones[zone]:
            del self.zones[zone]
        self._selected = None
        self._sel_dim  = None
        self.sel_info.set("—")
        self._refresh_zone_combo()
        self._render_lights()

    def _apply_coord(self):
        if self._selected:
            zone, idx = self._selected
            self.zones[zone][idx]["x"] = round(self.sel_x.get(), 1)
            self.zones[zone][idx]["y"] = round(self.sel_y.get(), 1)
            self._render_lights()
        elif self._sel_dim:
            did, end = self._sel_dim
            d = next((x for x in self._dims["dimensions"] if x["id"] == did), None)
            if d:
                if end == "p1":
                    d["x1"] = round(self.sel_x.get(), 1)
                    d["y1"] = round(self.sel_y.get(), 1)
                elif end == "p2":
                    d["x2"] = round(self.sel_x.get(), 1)
                    d["y2"] = round(self.sel_y.get(), 1)
                lbl = self.sel_label.get().strip()
                if lbl:
                    d["label"] = lbl
            self._render_lights()

    # ── Zone management ───────────────────────────────────────────────────────
    def _refresh_zone_combo(self):
        zones = list(self.zones.keys())
        self.zone_combo["values"] = zones
        if self.zone_var.get() not in zones:
            self.zone_var.set(zones[0] if zones else "")

    def _new_zone(self):
        name = simpledialog.askstring("New Zone", "Zone name:", parent=self)
        if name:
            if name not in self.zones:
                self.zones[name] = []
            self.zone_var.set(name)
            self._refresh_zone_combo()

    def _del_zone(self):
        zone = self.zone_var.get()
        if not zone:
            return
        n = len(self.zones.get(zone, []))
        if messagebox.askyesno("Delete Zone",
                               f"Delete zone '{zone}' and its {n} light(s)?", parent=self):
            self.zones.pop(zone, None)
            self._selected = None
            self._refresh_zone_combo()
            self._render_lights()

    # ── Counts display ────────────────────────────────────────────────────────
    def _update_counts(self):
        totals = {"soffit": 0, "wall": 0, "camera": 0}
        zone_lines = []
        for zone, pts in self.zones.items():
            totals[zone_type(zone)] += len(pts)
            zone_lines.append(f"  {zone[:24]}: {len(pts)}")
        self.counts_var.set(
            f"Soffit:  {totals['soffit']}\n"
            f"Wall:    {totals['wall']}\n"
            f"Camera:  {totals['camera']}\n"
            f"Total:   {sum(totals.values())}\n"
            f"\nBy zone:\n" + "\n".join(zone_lines)
        )

    # ── Dimension editor ──────────────────────────────────────────────────────
    def _open_dim_editor(self):
        win = tk.Toplevel(self)
        win.title("Edit Dimensions")
        win.geometry("820x380")
        win.transient(self)
        win.grab_set()

        cols = ("id", "label", "x1", "y1", "x2", "y2", "visible")
        widths = {"id": 170, "label": 75, "x1": 60, "y1": 60,
                  "x2": 60, "y2": 60, "visible": 55}

        frm = ttk.Frame(win)
        frm.pack(fill="both", expand=True, padx=5, pady=5)

        tree = ttk.Treeview(frm, columns=cols, show="headings", selectmode="browse")
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, width=widths[c])

        ys = ttk.Scrollbar(frm, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=ys.set)
        tree.pack(side="left", fill="both", expand=True)
        ys.pack(side="left", fill="y")

        def load():
            tree.delete(*tree.get_children())
            for d in self._dims.get("dimensions", []):
                tree.insert("", "end", iid=d["id"], values=(
                    d["id"], d["label"],
                    d["x1"], d["y1"], d["x2"], d["y2"],
                    str(d.get("visible", True))))

        load()

        def on_dbl(event):
            iid = tree.focus()
            if not iid:
                return
            col_id  = tree.identify_column(event.x)
            col_idx = int(col_id[1:]) - 1
            col_nm  = cols[col_idx]
            old_val = tree.item(iid, "values")[col_idx]
            new_val = simpledialog.askstring("Edit", f"{col_nm}:",
                                             initialvalue=str(old_val), parent=win)
            if new_val is None:
                return
            for d in self._dims["dimensions"]:
                if d["id"] != iid:
                    continue
                if col_nm == "label":   d["label"]   = new_val
                elif col_nm == "x1":   d["x1"]       = float(new_val)
                elif col_nm == "y1":   d["y1"]       = float(new_val)
                elif col_nm == "x2":   d["x2"]       = float(new_val)
                elif col_nm == "y2":   d["y2"]       = float(new_val)
                elif col_nm == "visible": d["visible"] = new_val.strip().lower() != "false"
                break
            load()

        tree.bind("<Double-Button-1>", on_dbl)

        bf = ttk.Frame(win)
        bf.pack(fill="x", padx=5, pady=4)
        ttk.Label(bf, text="Double-click any cell to edit").pack(side="left")
        ttk.Button(bf, text="Close", command=win.destroy).pack(side="right")

    # ── Save + regenerate SVG ─────────────────────────────────────────────────
    def _save(self):
        self.status_var.set("Saving…")
        self.update()

        # 1. Write perimeter_lights.json (strip internal fields)
        out = {zone: [{"x": p["x"], "y": p["y"]} for p in pts]
               for zone, pts in self.zones.items()}
        with open(LIGHTS_JSON, "w") as f:
            json.dump(out, f, indent=4)

        # 2. Write dimension_lines.json
        with open(DIM_JSON, "w") as f:
            json.dump(self._dims, f, indent=4)

        # 3. Regenerate grid SVG  (create_grid_floorplan.py → render_dimensions.py)
        errors   = []
        out_msgs = []
        for script_name in ("create_grid_floorplan.py", "render_dimensions.py"):
            script = os.path.join(SCRIPTS_DIR, script_name)
            if not os.path.exists(script):
                errors.append(f"Missing: {script_name}")
                continue
            try:
                res = subprocess.run(
                    [sys.executable, script],
                    capture_output=True, text=True, timeout=30,
                    cwd=BASE_DIR)
                if res.returncode != 0:
                    errors.append(f"{script_name}:\n{res.stderr.strip()[:300]}")
                else:
                    first_line = (res.stdout.strip().splitlines() or ["ok"])[0]
                    out_msgs.append(first_line)
            except Exception as ex:
                errors.append(f"{script_name}: {ex}")

        if errors:
            msg = "\n\n".join(errors)
            self.status_var.set("Save error — check below")
            messagebox.showerror("Save Error", msg, parent=self)
        else:
            total = sum(len(v) for v in self.zones.values())
            n_zones = len(self.zones)
            n_dims  = len([d for d in self._dims.get("dimensions", []) if d.get("visible", True)])
            self.status_var.set(
                f"✓ Saved  {total} lights · {n_zones} zones · {n_dims} dims\n"
                + "\n".join(out_msgs))

        # 4. Re-render background + lights
        self._render_bg()
        self._render_lights()


# ── Entry point ───────────────────────────────────────────────────────────────
def main():
    for path in (LIGHTS_JSON, DIM_JSON):
        if not os.path.exists(path):
            print(f"ERROR: required file not found: {path}")
            sys.exit(1)

    try:
        import cairosvg  # noqa: F401
        from PIL import Image  # noqa: F401
    except ImportError:
        print("TIP: install for SVG background rendering:")
        print("  pip install cairosvg Pillow\n")

    App().mainloop()


if __name__ == "__main__":
    main()
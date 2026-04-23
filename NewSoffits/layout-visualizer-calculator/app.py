import tkinter as tk
from tkinter import ttk

class SoffitVisualizer:
    def __init__(self, root):
        self.root = root
        self.root.title("Soffit Layout Visualizer")
        self.root.geometry("800x600")
        self.root.configure(bg="#1e1e24")

        # Variables
        self.total_depth = tk.DoubleVar(value=23.0)
        self.board_type = tk.StringVar(value="1x4")
        self.vent_pos = tk.StringVar(value="Center")
        self.custom_mode = tk.BooleanVar(value=False)
        self.custom_layout = [] # List of (width, label, color)
        self.auto_frame = None
        self.man_frame = None

        # Material Calculator Estimates
        self.run_length_ft = tk.DoubleVar(value=238.0)
        self.waste_pct = tk.IntVar(value=10) # 10% waste buffer
        self.vent_type = tk.StringVar(value="Plastic (1.75\")")

        # default Window geometry
        self.root.geometry("1150x820")

        # Square Foot Rates ($ / SqFt)
        self.item_prices = {
            "1x4": tk.DoubleVar(value=11.88),
            "1x5": tk.DoubleVar(value=11.88),
            "1x6": tk.DoubleVar(value=11.88),
            "Vent (Plastic)": tk.DoubleVar(value=8.55),
            "Vent (Metal)": tk.DoubleVar(value=20.70),
            "Rip": tk.DoubleVar(value=0.0)
        }
        
        # Board Definitions (Actual reveals)
        self.boards = {
            "1x4": 3.25,
            "1x5": 4.25,
            "1x6": 5.25
        }
        self.vent_width = 1.75

        self.setup_ui()
        layout = self.update_calculations()
        self.print_summary(layout, self.total_depth.get())

    def setup_ui(self):
        # Header
        header = tk.Label(self.root, text="Soffit Layout Visualizer", font=("Helvetica", 18, "bold"), bg="#1e1e24", fg="#f5f5f7")
        header.pack(pady=10)

        # Control Panel
        ctrl_frame = tk.Frame(self.root, bg="#2a2a35", bd=1, relief="solid")
        ctrl_frame.pack(pady=5, padx=20, fill="x")

        # Row 0: Mode Toggle
        tk.Checkbutton(ctrl_frame, text="Enable Manual Course Builder Mode", variable=self.custom_mode, 
                       bg="#2a2a35", fg="#ffd60a", selectcolor="#1e1e24", activebackground="#2a2a35", font=("Helvetica", 10, "bold"), command=self.on_change).grid(row=0, column=0, columnspan=3, pady=5)

        # Row 1: Depth Slider
        tk.Label(ctrl_frame, text="Soffit Depth (inches):", bg="#2a2a35", fg="#f5f5f7").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        slider = ttk.Scale(ctrl_frame, from_=21.0, to=26.0, variable=self.total_depth, orient="horizontal", command=self.on_change)
        slider.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
        depth_ctrl = tk.Frame(ctrl_frame, bg="#2a2a35")
        depth_ctrl.grid(row=1, column=2, padx=10, pady=5)
        
        btn_minus = tk.Label(depth_ctrl, text="-", bg="#1e1e24", fg="#ffd60a", font=("Helvetica", 11, "bold"), width=3, cursor="hand2", relief="solid", bd=1)
        btn_minus.pack(side="left", padx=2)
        btn_minus.bind("<Button-1>", lambda e: self.adjust_depth(-0.25))
        
        self.depth_ent = ttk.Entry(depth_ctrl, width=6, justify="center", font=("Helvetica", 10, "bold"))
        self.depth_ent.pack(side="left", padx=2)
        self.depth_ent.insert(0, "23.00")
        self.depth_ent.bind("<KeyRelease>", lambda e: self.on_change())
        
        btn_plus = tk.Label(depth_ctrl, text="+", bg="#1e1e24", fg="#ffd60a", font=("Helvetica", 11, "bold"), width=3, cursor="hand2", relief="solid", bd=1)
        btn_plus.pack(side="left", padx=2)
        btn_plus.bind("<Button-1>", lambda e: self.adjust_depth(0.25))

        # Row 2: Project Assumptions (Calculator)
        proj_frame = tk.Frame(ctrl_frame, bg="#2a2a35")
        proj_frame.grid(row=2, column=0, columnspan=3, sticky="ew", pady=5)
        
        tk.Label(proj_frame, text="Total Run (ft):", bg="#2a2a35", fg="#f5f5f7").grid(row=0, column=0, padx=10, sticky="w")
        len_slider = ttk.Scale(proj_frame, from_=10, to=500, variable=self.run_length_ft, orient="horizontal", command=self.on_change)
        len_slider.grid(row=0, column=1, sticky="ew", padx=10)
        self.len_lbl = tk.Label(proj_frame, text="238 ft", bg="#2a2a35", fg="#ffd60a", font=("Helvetica", 11, "bold"))
        self.len_lbl.grid(row=0, column=2, padx=10)

        tk.Label(proj_frame, text="Waste (%):", bg="#2a2a35", fg="#f5f5f7").grid(row=0, column=3, padx=15, sticky="w")
        self.waste_ent = ttk.Entry(proj_frame, width=4, justify="right")
        self.waste_ent.grid(row=0, column=4, padx=5)
        self.waste_ent.insert(0, "10")
        self.waste_ent.bind("<KeyRelease>", lambda e: self.on_change())
        
        tk.Label(proj_frame, text="Vent:", bg="#2a2a35", fg="#f5f5f7").grid(row=0, column=5, padx=15, sticky="w")
        self.vent_combo = ttk.Combobox(proj_frame, textvariable=self.vent_type, values=["Plastic (1.75\")", "Metal (2.00\")"], width=13, state="readonly")
        self.vent_combo.grid(row=0, column=6, padx=5)
        self.vent_combo.bind("<<ComboboxSelected>>", lambda e: self.on_change())

        # Row 2.5: SqFt PRICING RATES
        rates_frm = tk.LabelFrame(ctrl_frame, text="Square Foot Rates ($ / SqFt) 🪵🌬️", bg="#2a2a35", fg="#52b788", font=("Helvetica", 9, "bold"))
        rates_frm.grid(row=3, column=0, columnspan=3, sticky="ew", pady=5, padx=5)
        
        r_idx = 0
        for p_name, var in self.item_prices.items():
            if p_name == "Rip": continue
            # Place entry horizontally
            tk.Label(rates_frm, text=f"{p_name}:", bg="#2a2a35", fg="#f5f5f7").grid(row=0, column=r_idx*2, padx=8, pady=5, sticky="w")
            ent = ttk.Entry(rates_frm, textvariable=var, width=6, justify="right")
            ent.grid(row=0, column=r_idx*2 + 1, padx=5, pady=5)
            ent.bind("<KeyRelease>", lambda e: self.on_change())
            r_idx += 1

        # Separators
        ttk.Separator(ctrl_frame, orient="horizontal").grid(row=4, column=0, columnspan=3, sticky="ew", pady=5)

        # --- AUTO MODE CONTROLS ---
        self.auto_frame = tk.Frame(ctrl_frame, bg="#2a2a35")
        self.auto_frame.grid(row=5, column=0, columnspan=3, sticky="ew")
        
        tk.Label(self.auto_frame, text="Board Size:", bg="#2a2a35", fg="#f5f5f7").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        board_frame = tk.Frame(self.auto_frame, bg="#2a2a35")
        board_frame.grid(row=0, column=1, sticky="w", padx=10)
        for idx, (lbl, val) in enumerate(self.boards.items()):
            rb = tk.Radiobutton(board_frame, text=f"{lbl} ({val}\")", variable=self.board_type, value=lbl, 
                                bg="#2a2a35", fg="#f5f5f7", activebackground="#2a2a35", selectcolor="#1e1e24", command=self.on_change)
            rb.grid(row=0, column=idx, padx=10)

        tk.Label(self.auto_frame, text="Vent Style:", bg="#2a2a35", fg="#f5f5f7").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        vstyle_frame = tk.Frame(self.auto_frame, bg="#2a2a35")
        vstyle_frame.grid(row=1, column=1, sticky="w", padx=10)
        for idx, v in enumerate(["Plastic (1.75\")", "Metal (2.00\")"]):
            rb = tk.Radiobutton(vstyle_frame, text=v, variable=self.vent_type, value=v, 
                                bg="#2a2a35", fg="#f5f5f7", activebackground="#2a2a35", selectcolor="#1e1e24", command=self.on_change)
            rb.grid(row=0, column=idx, padx=10)

        tk.Label(self.auto_frame, text="Vent Position:", bg="#2a2a35", fg="#f5f5f7").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        pos_frame = tk.Frame(self.auto_frame, bg="#2a2a35")
        pos_frame.grid(row=2, column=1, sticky="w", padx=10)
        positions = ["Outer Edge", "1-Board Deep", "Center"]
        for idx, pos in enumerate(positions):
            rb = tk.Radiobutton(pos_frame, text=pos, variable=self.vent_pos, value=pos, 
                                bg="#2a2a35", fg="#f5f5f7", activebackground="#2a2a35", selectcolor="#1e1e24", command=self.on_change)
            rb.grid(row=0, column=idx, padx=10)

        # --- MANUAL MODE CONTROLS ---
        self.man_frame = tk.Frame(ctrl_frame, bg="#2a2a35")
        self.man_frame.grid(row=6, column=0, columnspan=3, sticky="ew")
        
        tk.Label(self.man_frame, text="Manual Builder (Left to Right / Stucco to Gutter):", bg="#2a2a35", fg="#f5f5f7").grid(row=0, column=0, columnspan=3, padx=10, pady=5, sticky="w")
        btn_frame = tk.Frame(self.man_frame, bg="#2a2a35")
        btn_frame.grid(row=1, column=0, columnspan=3, padx=10, pady=5)
        
        b1 = tk.Label(btn_frame, text=" + 1x4 ", bg="#c2b280", fg="#121214", font=("Helvetica", 10, "bold"), bd=1, relief="solid", cursor="hand2")
        b1.grid(row=0, column=0, padx=5)
        b1.bind("<Button-1>", lambda e: self.add_segment("1x4"))

        b2 = tk.Label(btn_frame, text=" + 1x5 ", bg="#c2b280", fg="#121214", font=("Helvetica", 10, "bold"), bd=1, relief="solid", cursor="hand2")
        b2.grid(row=0, column=1, padx=5)
        b2.bind("<Button-1>", lambda e: self.add_segment("1x5"))

        b3 = tk.Label(btn_frame, text=" + 1x6 ", bg="#c2b280", fg="#121214", font=("Helvetica", 10, "bold"), bd=1, relief="solid", cursor="hand2")
        b3.grid(row=0, column=2, padx=5)
        b3.bind("<Button-1>", lambda e: self.add_segment("1x6"))

        b4 = tk.Label(btn_frame, text=" + Plastic Vent (1.75\") ", bg="#343a40", fg="#ffffff", font=("Helvetica", 10, "bold"), bd=1, relief="solid", cursor="hand2")
        b4.grid(row=0, column=3, padx=10)
        b4.bind("<Button-1>", lambda e: self.add_segment("Vent Plastic"))

        b5 = tk.Label(btn_frame, text=" + Metal Vent (2.00\") ", bg="#343a40", fg="#ffffff", font=("Helvetica", 10, "bold"), bd=1, relief="solid", cursor="hand2")
        b5.grid(row=0, column=4, padx=10)
        b5.bind("<Button-1>", lambda e: self.add_segment("Vent Metal"))

        b6 = tk.Label(btn_frame, text=" Undo ", bg="#e07a5f", fg="#ffffff", font=("Helvetica", 10), bd=1, relief="solid", cursor="hand2")
        b6.grid(row=0, column=5, padx=5)
        b6.bind("<Button-1>", lambda e: self.undo_layout())

        b7 = tk.Label(btn_frame, text=" Clear All ", bg="#c1121f", fg="#ffffff", font=("Helvetica", 10, "bold"), bd=1, relief="solid", cursor="hand2")
        b7.grid(row=0, column=6, padx=5)
        b7.bind("<Button-1>", lambda e: self.clear_layout())

        # Canvas Frame
        self.canvas = tk.Canvas(self.root, bg="#121214", height=200, bd=0, highlightthickness=0)
        self.canvas.pack(pady=20, padx=20, fill="x")

        # Results Frame
        res_frame = tk.Frame(self.root, bg="#1e1e24")
        res_frame.pack(pady=5, fill="x", padx=20)
        
        # Left side: Text Summary
        self.results_txt = tk.Label(res_frame, text="", bg="#1e1e24", fg="#f5f5f7", font=("Helvetica", 11), justify="left")
        self.results_txt.pack(side="left", anchor="nw")

        # Center/Right: Spreadsheet Grid Sub-table
        self.table_frm = tk.Frame(res_frame, bg="#1e1e24")
        self.table_frm.pack(side="left", fill="both", expand=True, padx=40)

        # Right side: Large prominence Counter
        self.big_total_lbl = tk.Label(res_frame, text="", bg="#1e1e24", fg="#ffd60a", font=("Helvetica", 22, "bold"), justify="center")
        self.big_total_lbl.pack(side="right", anchor="ne", padx=20)

        # List Frame for Manual Mode Individual Item Deletion
        self.list_frame = tk.Frame(self.root, bg="#1e1e24")
        self.list_frame.pack(pady=5, fill="x", padx=20)

    def adjust_depth(self, amount):
        try:
            curr = float(self.depth_ent.get())
            new_val = max(10, min(36, curr + amount))
            self.total_depth.set(new_val)
            self.depth_ent.delete(0, tk.END)
            self.depth_ent.insert(0, f"{new_val:0.2f}")
            self.on_change()
        except ValueError:
            pass

    def on_change(self, *args):
        # Bidirectional Sync
        if hasattr(self, 'depth_ent') and self.root.focus_get() == self.depth_ent:
            try:
                depth = float(self.depth_ent.get())
                if 10 <= depth <= 36:
                    self.total_depth.set(depth)
            except ValueError:
                pass
        else:
            depth = round(self.total_depth.get(), 2)
            if hasattr(self, 'depth_ent') and self.depth_ent.get() != f"{depth:0.2f}":
                self.depth_ent.delete(0, tk.END)
                self.depth_ent.insert(0, f"{depth:0.2f}")

        self.len_lbl.config(text=f"{int(self.run_length_ft.get())} ft")
        
        # Parse Waste
        try:
            w = int(self.waste_ent.get())
            if 0 <= w <= 100:
                self.waste_pct.set(w)
        except ValueError:
            pass

        self.update_list_panel()
        layout = self.update_calculations()
        self.print_summary(layout, depth)

    def add_segment(self, label):
        depth = self.total_depth.get()
        current_w = sum([w for w, l, c in self.custom_layout])
        rem = depth - current_w

        if rem <= 0:
             return # No overlap space remaining

        # Lookup width
        if label == "Vent Plastic":
             w_add = 1.75
             target_lbl = "Vent (Plastic)"
             color = "#343a40"
        elif label == "Vent Metal":
             w_add = 2.00
             target_lbl = "Vent (Metal)"
             color = "#343a40"
        elif label == "Vent":
             w_add = self.vent_width
             target_lbl = "Vent"
             color = "#343a40"
        else:
             w_add = self.boards.get(label, 0.0)
             target_lbl = label
             color = "#c2b280"

        # Check Overflow
        if w_add > rem:
             # Face exceeds remaining space -> switch to custom precise Rip cap
             self.custom_layout.append((round(rem, 2), "Rip", "#e07a5f"))
        else:
             self.custom_layout.append((w_add, target_lbl, color))

        self.update_list_panel()
        self.update_calculations()

    def clear_layout(self):
        self.custom_layout = []
        self.update_list_panel()
        self.update_calculations()

    def undo_layout(self):
        if self.custom_layout:
            self.custom_layout.pop()
        self.update_list_panel()
        self.update_calculations()

    def delete_segment(self, index):
        if 0 <= index < len(self.custom_layout):
            self.custom_layout.pop(index)
        self.update_list_panel()
        self.update_calculations()

    def update_calculations(self):
        depth = self.total_depth.get()
        board_w = self.boards[self.board_type.get()]
        v_pos = self.vent_pos.get()

        # Update Dynamic Vent Width
        if "Metal" in self.vent_type.get():
            self.vent_width = 2.00
        else:
            self.vent_width = 1.75

        # Update Frame Visibility (Restating grid specs to avoid corrupting geometry tree)
        if self.custom_mode.get():
            self.auto_frame.grid_remove()
            self.man_frame.grid(row=6, column=0, columnspan=3, sticky="ew")
        else:
            self.auto_frame.grid(row=5, column=0, columnspan=3, sticky="ew")
            self.man_frame.grid_remove()

        layout = [] # List of tuples: (width, type_label, color)
        
        if self.custom_mode.get():
            layout = list(self.custom_layout)
        else:
            # Auto Layout Generation (Modified for Left=Stucco, Right=Gutter)
            if v_pos == "Outer Edge":
                # Stucco -> [Wood...] [Vent] [Rip] -> Gutter
                rem = depth - self.vent_width
                while rem >= board_w:
                    layout.append((board_w, self.board_type.get(), "#c2b280"))
                    rem -= board_w
                layout.append((self.vent_width, "Vent", "#343a40"))
                if rem > 0:
                    layout.append((rem, "Rip", "#e07a5f"))

            elif v_pos == "1-Board Deep":
                # Stucco -> [Wood...] [Vent] [Wood] [Rip] -> Gutter
                rem = depth - board_w - self.vent_width
                while rem >= board_w:
                    layout.append((board_w, self.board_type.get(), "#c2b280"))
                    rem -= board_w
                layout.append((self.vent_width, "Vent", "#343a40"))
                layout.append((board_w, self.board_type.get(), "#c2b280"))
                if rem > 0:
                    layout.append((rem, "Rip", "#e07a5f"))

            else: # Center
                full_boards_needed = int((depth - self.vent_width) // board_w)
                side = full_boards_needed // 2
                
                for _ in range(side):
                    layout.append((board_w, self.board_type.get(), "#c2b280"))
                layout.append((self.vent_width, "Vent", "#343a40"))
                
                rem = depth - (side * board_w) - self.vent_width
                while rem >= board_w:
                    layout.append((board_w, self.board_type.get(), "#c2b280"))
                    rem -= board_w
                if rem > 0:
                    layout.append((rem, "Rip", "#e07a5f"))

        self.draw_layout(layout, depth)
        self.print_summary(layout, depth)
        return layout

    def update_list_panel(self):
        # Dedicated trigger-only builder panel avoiding continuous grid/bind loops
        for widget in self.list_frame.winfo_children():
            widget.destroy()
            
        if self.custom_mode.get():
            tk.Label(self.list_frame, text="Your Layout: ", bg="#1e1e24", fg="#a0a0a5", font=("Helvetica", 9, "bold")).pack(side="left")
            for i, (w, lbl, c) in enumerate(self.custom_layout):
                frm = tk.Frame(self.list_frame, bg="#2a2a35", bd=1, relief="solid")
                frm.pack(side="left", padx=4, pady=2)
                tk.Label(frm, text=f"{lbl}", bg="#2a2a35", fg="#ffd60a", font=("Helvetica", 9, "bold")).pack(side="left", padx=6, pady=2)
                # Small delete label trigger
                btn = tk.Label(frm, text="×", bg="#2a2a35", fg="#e63946", activebackground="#2a2a35", cursor="hand2", font=("Helvetica", 10, "bold"))
                btn.pack(side="left", padx=4)
                btn.bind("<Button-1>", lambda e, idx=i: self.delete_segment(idx))

    def draw_layout(self, layout, depth):
        self.canvas.delete("all")
        c_width = self.canvas.winfo_width()
        if c_width <= 1: c_width = 760 # fallback
        
        # Dimensions for Borders (Decorative context)
        gutter_w = 60  # pixels
        wall_w = 60    # pixels
        draw_width = c_width - gutter_w - wall_w
        
        # Scale pixels per inch based on drawing zone
        scale = draw_width / depth 
        y_start = 50
        y_end = 150

        # 1. Draw STUCCO WALL (Left)
        self.canvas.create_rectangle(0, y_start-20, gutter_w, y_end+20, fill="#d5dbdb", outline="")
        self.canvas.create_text(gutter_w/2, (y_start+y_end)/2, text="STUCCO\nWALL", fill="#2c3e50", font=("Helvetica", 8, "bold"), justify="center")

        # 2. Draw WOOD LAYOUT (Center Scaling)
        curr_x = gutter_w
        for width, lbl, color in layout:
            p_width = width * scale
            # Draw board
            self.canvas.create_rectangle(curr_x, y_start, curr_x + p_width, y_end, fill=color, outline="#121214", width=2)
            # Label
            self.canvas.create_text(curr_x + (p_width/2), y_start - 15, text=f"{width:0.2f}\"", fill="#f5f5f7", font=("Helvetica", 9))
            self.canvas.create_text(curr_x + (p_width/2), (y_start+y_end)/2, text=lbl, fill="#ffffff" if lbl=="Vent" else "#121214", font=("Helvetica", 10, "bold"))
            curr_x += p_width

        # 3. Draw GUTTER / FASCIA (Right)
        self.canvas.create_rectangle(c_width - wall_w, y_start-20, c_width, y_end+20, fill="#2c3e50", outline="")
        self.canvas.create_text(c_width - (wall_w/2), (y_start+y_end)/2, text="GUTTER\n(Fascia)", fill="#ffffff", font=("Helvetica", 8, "bold"), justify="center")

    def print_summary(self, layout, depth):
        run_len = self.run_length_ft.get()
        
        # Bypass parameter lookup for layout in manual mode
        current_layout = list(self.custom_layout) if self.custom_mode.get() else layout

        full_boards = 0
        rip_w = 0.0
        for w, l, c in current_layout:
            if l == "Rip":
                rip_w += w
            elif l != "Vent" and "Vent" not in l:
                full_boards += 1

        total_custom_w = sum([w for w, l, c in current_layout])

        # Material spreadsheet math
        materials_lin = {}
        materials_sqft = {}
        for w, l, c in current_layout:
            materials_lin[l] = materials_lin.get(l, 0) + run_len
            materials_sqft[l] = materials_sqft.get(l, 0) + (run_len * (w / 12))

        total_sqft = sum(materials_sqft.values())

        if self.custom_mode.get():
            # Manual Mode Text
            txt = f"📊 **MANUAL BUILDER SUMMARY**\n"
            txt += f"• **Target Box Depth:** {depth:0.2f}\"\n"
            diff = total_custom_w - depth
            if abs(diff) < 0.05:
                txt += f"✅ **PERFECT FIT!** Matches target exactly.\n"
            elif diff > 0:
                txt += f"⚠️ Overhang: **+{diff:0.2f}\"** (Will overshoot slightly)\n"
            else:
                txt += f"🔍 Underhang: **{diff:0.2f}\"** (Gap remaining)\n"
            
            txt += f"• Segment Inventory: "
            counts = {}
            for w, l, c in layout:
                counts[l] = counts.get(l, 0) + 1
            inventory = ", ".join([f"{k} (x{v})" for k, v in counts.items()])
            txt += f"{inventory if inventory else 'Empty'}\n"

            self.big_total_lbl.config(text=f"Total Built\n{total_custom_w:0.2f}\"", fg="#ffd60a")
        else:
            # Auto Mode Text
            txt = f"📊 **AUTO LAYOUT SUMMARY FOR {depth:0.2f}\" DEPTH**\n"
            txt += f"• Board Type: {self.board_type.get()} ({self.boards[self.board_type.get()]}\" reveal)\n"
            txt += f"• Vent position: {self.vent_pos.get()}\n"
            txt += f"• Full course count: {full_boards}\n"
            txt += f"• **Back Cut-off (Rip course):** {rip_w:0.2f}\" needed.\n"
            
            if rip_w < 1.0 and rip_w > 0:
                txt += "⚠️ *Warning: Very narrow rip course might require support backing.*\n"
            elif rip_w == 0:
                txt += "✅ *Perfect alignment! No rip course needed!*\n"
            else:
                txt += "✅ *Standard fit.*\n"

            self.big_total_lbl.config(text=f"Total Width\n{total_custom_w:0.2f}\"", fg="#52b788" if rip_w==0 else "#ffd60a")

        self.results_txt.config(text=txt)

        # --- DRAW TABLE GRID METRICS ---
        for child in self.table_frm.winfo_children():
            child.destroy()

        # --- DRAW TABLE GRID METRICS ---
        for child in self.table_frm.winfo_children():
            child.destroy()

        headers = ["Product Item", "Total Lin Ft", "Face SqFt", "Cost ($)"]
        for c, h in enumerate(headers):
             tk.Label(self.table_frm, text=h, bg="#1e1e24", fg="#52b788", font=("Helvetica", 9, "bold")).grid(row=0, column=c, padx=10, pady=2, sticky="w")
        
        r_idx = 1
        subtotal_cost = 0.0
        
        for mat, lft in materials_lin.items():
             if mat == "Rip": continue
             sqft = materials_sqft[mat]
             
             # Dynamic Linear rate lookup
             rate_key = mat
             if "Vent" in mat and "Plastic" in mat: rate_key = "Vent (Plastic)"
             elif "Vent" in mat and "Metal" in mat: rate_key = "Vent (Metal)"
             elif mat not in self.item_prices: rate_key = "1x4" # fallback
             
             rate = self.item_prices.get(rate_key, tk.DoubleVar(value=0.0)).get()
             try:
                 rate = float(rate)
             except ValueError:
                 rate = 0.0
             c_row = sqft * rate 
             subtotal_cost += c_row
             
             tk.Label(self.table_frm, text=mat, bg="#1e1e24", fg="#f5f5f7", font=("Helvetica", 9)).grid(row=r_idx, column=0, padx=10, pady=2, sticky="w")
             tk.Label(self.table_frm, text=f"{int(lft)} ft", bg="#1e1e24", fg="#f5f5f7", font=("Helvetica", 9)).grid(row=r_idx, column=1, padx=10, pady=2, sticky="w")
             tk.Label(self.table_frm, text=f"{sqft:.1f}", bg="#1e1e24", fg="#f5f5f7", font=("Helvetica", 9)).grid(row=r_idx, column=2, padx=10, pady=2, sticky="w")
             tk.Label(self.table_frm, text=f"${c_row:,.2f}", bg="#1e1e24", fg="#f5f5f7", font=("Helvetica", 9)).grid(row=r_idx, column=3, padx=10, pady=2, sticky="w")
             r_idx += 1

        ttk.Separator(self.table_frm, orient="horizontal").grid(row=r_idx, column=0, columnspan=4, sticky="ew", pady=4)
        r_idx += 1

        waste_f = self.waste_pct.get() / 100.0
        waste_cost = subtotal_cost * waste_f
        grand_total = subtotal_cost + waste_cost

        tk.Label(self.table_frm, text="Subtotal Coverage", bg="#1e1e24", fg="#ffd60a", font=("Helvetica", 9, "bold")).grid(row=r_idx, column=0, padx=10, sticky="w")
        tk.Label(self.table_frm, text=f"{int(sum(materials_lin.values()))} ft total", bg="#1e1e24", fg="#f5f5f7", font=("Helvetica", 9)).grid(row=r_idx, column=1, padx=10, sticky="w")
        tk.Label(self.table_frm, text=f"${subtotal_cost:,.2f}", bg="#1e1e24", fg="#f5f5f7", font=("Helvetica", 9)).grid(row=r_idx, column=3, padx=10, sticky="w")
        r_idx += 1

        tk.Label(self.table_frm, text=f"Wastage (+{self.waste_pct.get()}%)", bg="#1e1e24", fg="#e07a5f", font=("Helvetica", 9)).grid(row=r_idx, column=0, padx=10, sticky="w")
        tk.Label(self.table_frm, text=f"${waste_cost:,.2f}", bg="#1e1e24", fg="#e07a5f", font=("Helvetica", 9)).grid(row=r_idx, column=3, padx=10, sticky="w")
        r_idx += 1

        tk.Label(self.table_frm, text="GRAND TOTAL", bg="#1e1e24", fg="#52b788", font=("Helvetica", 11, "bold")).grid(row=r_idx, column=0, padx=10, pady=5, sticky="w")
        tk.Label(self.table_frm, text=f"${grand_total:,.2f}", bg="#1e1e24", fg="#52b788", font=("Helvetica", 11, "bold")).grid(row=r_idx, column=3, padx=10, pady=5, sticky="w")

if __name__ == "__main__":
    root = tk.Tk()
    app = SoffitVisualizer(root)
    app.canvas.bind("<Configure>", lambda e: app.update_calculations())
    root.mainloop()

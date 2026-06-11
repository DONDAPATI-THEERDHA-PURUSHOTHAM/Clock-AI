import json
import os
import re
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path

import tkinter as tk
from tkinter import ttk, messagebox

# --- CONFIGURATION & THEMING ---
APP_NAME = "Clock Suite & AIML Assistant"
APP_DATA_FILE = Path.home() / ".clock_app_clone_storage.json"

# Curated warm cream palette
BG = "#f7f2e8"       # Warm beige background
BG_2 = "#efe6d6"     # Secondary background
CARD = "#fffdf8"     # Bright cream card surface
CARD_2 = "#f8f2e7"   # Secondary card surface
LINE = "#e3d7c5"     # Linen border line
TEXT = "#2b2722"     # Espresso dark text
MUTED = "#776d60"    # Roasted bean muted text
ACCENT = "#b58b55"   # Warm gold primary accent
ACCENT_2 = "#8a6f4d" # Bronze secondary accent
DANGER = "#c94c4c"   # Soft terracotta red
SUCCESS = "#4f8554"  # Sage forest green

DAY_NAMES = ["S", "M", "T", "W", "T", "F", "S"]
DAY_FULL_NAMES = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

CITY_UTC_OFFSETS = {
    "London": 1.0,      # British Summer Time (UTC+1)
    "Paris": 2.0,       # Central European Summer Time (UTC+2)
    "Berlin": 2.0,
    "Frankfurt": 2.0,
    "Moscow": 3.0,
    "Dubai": 4.0,
    "Bangkok": 7.0,
    "Singapore": 8.0,
    "Hong Kong": 8.0,
    "Beijing": 8.0,
    "Tokyo": 9.0,
    "Sydney": 10.0,
    "New York": -4.0,   # Eastern Daylight Time (UTC-4)
    "Washington DC": -4.0,
    "Chicago": -5.0,
    "Denver": -6.0,
    "Los Angeles": -7.0,
    "San Francisco": -7.0,
    "Honolulu": -10.0,
}

# --- AIML PATTERN MATCHING ALGORITHM ---
def match_pattern(pat_tokens, inp_tokens, star_index=0, stars=None):
    if stars is None:
        stars = []
    
    # Base cases
    if not pat_tokens and not inp_tokens:
        return stars
    if not pat_tokens or (not inp_tokens and pat_tokens[0] != '*'):
        return None
        
    p = pat_tokens[0]
    
    if p == '*':
        # Greedy recursive matching for wildcard
        for i in range(1, len(inp_tokens) + 1):
            star_val = " ".join(inp_tokens[:i])
            sub_stars = stars + [star_val]
            res = match_pattern(pat_tokens[1:], inp_tokens[i:], star_index + 1, sub_stars)
            if res is not None:
                return res
        return None
    else:
        # Exact token match
        if p.upper() == inp_tokens[0].upper():
            return match_pattern(pat_tokens[1:], inp_tokens[1:], star_index, stars)
        return None

class AimlEngine:
    def __init__(self):
        self.categories = []  # list of (pattern_tokens, template_str)
        
    def learn(self, file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Match categories via regex for standard support
            cats = re.findall(r'<category>\s*<pattern>(.*?)</pattern>\s*<template>(.*?)</template>\s*</category>', content, re.DOTALL)
            for pat, temp in cats:
                pat = pat.strip()
                pat_tokens = [t for t in pat.split() if t]
                self.categories.append((pat_tokens, temp.strip()))
        except Exception as e:
            print(f"Error loading AIML file {file_path}: {e}")
            
    def respond(self, query):
        query_clean = re.sub(r'[^\w\s:]', '', query).strip().upper()
        query_tokens = [t for t in query_clean.split() if t]
        if not query_tokens:
            return "I didn't catch that. Can you repeat?", []
            
        for pat_tokens, template in self.categories:
            stars = match_pattern(pat_tokens, query_tokens)
            if stars is not None:
                return self.evaluate_template(template, stars)
                
        return "I'm sorry, I don't understand that command. Type 'help' for instructions.", []
        
    def evaluate_template(self, template, stars):
        # Replace <star index="N" /> or <star />
        def rep_star(m):
            idx_str = m.group(1) or m.group(2) or "1"
            idx = int(idx_str) - 1
            if 0 <= idx < len(stars):
                return stars[idx]
            return ""
            
        temp = re.sub(r'<star\s+index="(\d+)"\s*/>|<star\s+index=\'(\d+)\'\s*/>|<star\s*/\s*>', rep_star, template)
        
        # Resolve <srai> tags recursively
        srai_match = re.search(r'<srai>(.*?)</srai>', temp, re.DOTALL)
        if srai_match:
            redirect_query = srai_match.group(1).strip()
            return self.respond(redirect_query)
            
        # Parse custom action triggers
        actions = []
        action_matches = re.finditer(r'<action\s+type="([^"]+)"([^>]*)/?>', temp)
        for m in action_matches:
            act_type = m.group(1)
            attrs_str = m.group(2)
            attrs = {}
            attr_pairs = re.findall(r'(\w+)="([^"]*)"|(\w+)=\'([^\']*)\'', attrs_str)
            for k1, v1, k2, v2 in attr_pairs:
                key = k1 or k2
                val = v1 or v2
                attrs[key] = val
            actions.append({"type": act_type, **attrs})
            
        # Clean response string of XML action elements
        output_text = re.sub(r'<action\s+type="[^"]+"[^>]*/>|<action\s+type="[^"]+"[^>]*>.*?</action>', '', temp, flags=re.DOTALL)
        output_text = re.sub(r'\s+', ' ', output_text).strip()
        
        return output_text, actions


# --- CUSTOM GRAPHICS & SHAPE HELPERS ---
def draw_rounded_rect(canvas, x1, y1, x2, y2, r, **kwargs):
    # Standard smooth polygon points for bezier rounded corners
    points = [
        x1+r, y1,
        x2-r, y1,
        x2-r, y1,
        x2, y1,
        x2, y1+r,
        x2, y1+r,
        x2, y2-r,
        x2, y2-r,
        x2, y2,
        x2-r, y2,
        x2-r, y2,
        x1+r, y2,
        x1+r, y2,
        x1, y2,
        x1, y2-r,
        x1, y2-r,
        x1, y1+r,
        x1, y1+r,
        x1, y1
    ]
    return canvas.create_polygon(points, smooth=True, **kwargs)

def gentle_open(win, target_geometry="360x520", steps=10, delay=12):
    try:
        w, h = target_geometry.split("x")
        w, h = int(w), int(h)
        win.update_idletasks()
        win.geometry(f"{max(1, int(w * 0.92))}x{max(1, int(h * 0.92))}")
        try:
            win.attributes("-alpha", 0.0)
        except Exception:
            pass

        def step(i=0):
            p = (i + 1) / steps
            ww = int(w * (0.92 + 0.08 * p))
            hh = int(h * (0.92 + 0.08 * p))
            win.geometry(f"{ww}x{hh}")
            try:
                win.attributes("-alpha", min(1.0, 0.08 + p * 0.92))
            except Exception:
                pass
            if i < steps - 1:
                win.after(delay, lambda: step(i + 1))
        step()
    except Exception:
        pass


# --- CUSTOM UI WIDGETS ---
class CanvasCard(tk.Canvas):
    def __init__(self, parent, bg_color=CARD, border_color=LINE, border_width=1, r=12, **kwargs):
        super().__init__(parent, bg=parent["bg"], highlightthickness=0, **kwargs)
        self.bg_color = bg_color
        self.border_color = border_color
        self.border_width = border_width
        self.r = r
        self.bind("<Configure>", self.draw)

    def draw(self, event=None):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        draw_rounded_rect(self, 2, 2, w-2, h-2, self.r, fill=self.bg_color, outline=self.border_color, width=self.border_width)

class CanvasSwitch(tk.Canvas):
    def __init__(self, parent, value=False, command=None, width=46, height=24):
        super().__init__(parent, width=width, height=height, bg=parent["bg"] if str(parent["bg"]) else BG, highlightthickness=0)
        self.value = value
        self.command = command
        self.r = height // 2
        
        self.bg_id = draw_rounded_rect(self, 2, 2, width-2, height-2, self.r-2, fill=SUCCESS if value else LINE, outline="")
        knob_x = width - self.r if value else self.r
        self.knob_id = self.create_oval(knob_x - (self.r-4), 4, knob_x + (self.r-4), height-4, fill=CARD, outline="")
        
        self.bind("<Button-1>", self.toggle)
        
    def toggle(self, event=None):
        self.value = not self.value
        self.animate_switch()
        if self.command:
            self.command(self.value)
            
    def set(self, val):
        self.value = bool(val)
        self.animate_switch()
        
    def animate_switch(self):
        width = int(self.cget("width"))
        height = int(self.cget("height"))
        target_x = width - self.r if self.value else self.r
        bg_color = SUCCESS if self.value else LINE
        
        self.itemconfig(self.bg_id, fill=bg_color)
        
        current_coords = self.coords(self.knob_id)
        current_x = (current_coords[0] + current_coords[2]) / 2
        
        def step(x=current_x):
            diff = target_x - x
            if abs(diff) < 2:
                self.coords(self.knob_id, target_x - (self.r-4), 4, target_x + (self.r-4), height-4)
            else:
                next_x = x + diff * 0.4
                self.coords(self.knob_id, next_x - (self.r-4), 4, next_x + (self.r-4), height-4)
                self.after(20, lambda: step(next_x))
        step()

class RollingPicker(tk.Frame):
    def __init__(self, parent, value=0, min_value=0, max_value=59, format_str="{:02d}", width=3, font_main=("Segoe UI", 16, "bold"), font_sub=("Segoe UI", 10)):
        super().__init__(parent, bg=CARD_2, bd=1, relief="solid", highlightthickness=0)
        self.configure(highlightbackground=LINE, highlightcolor=LINE)
        self.min_value = min_value
        self.max_value = max_value
        self.value = value
        self.format_str = format_str
        self._drag_y = None
        
        self.lbl_prev = tk.Label(self, text="", font=font_sub, bg=CARD_2, fg=MUTED)
        self.lbl_prev.pack(pady=2)
        
        self.sep1 = tk.Frame(self, height=1, bg=LINE)
        self.sep1.pack(fill="x", padx=4)
        
        self.lbl_curr = tk.Label(self, text="", font=font_main, bg=CARD, fg=TEXT, width=width)
        self.lbl_curr.pack(pady=4)
        
        self.sep2 = tk.Frame(self, height=1, bg=LINE)
        self.sep2.pack(fill="x", padx=4)
        
        self.lbl_next = tk.Label(self, text="", font=font_sub, bg=CARD_2, fg=MUTED)
        self.lbl_next.pack(pady=2)
        
        self.refresh()
        
        for w in (self, self.lbl_prev, self.lbl_curr, self.lbl_next):
            w.bind("<MouseWheel>", self._on_wheel)
            w.bind("<Button-4>", lambda e: self.shift(-1))
            w.bind("<Button-5>", lambda e: self.shift(1))
            w.bind("<ButtonPress-1>", self._drag_start)
            w.bind("<B1-Motion>", self._drag_move)
            w.bind("<ButtonRelease-1>", self._drag_end)
            
    def refresh(self):
        rng = self.max_value - self.min_value + 1
        
        prev_val = self.value - 1
        if prev_val < self.min_value:
            prev_val = self.max_value
            
        next_val = self.value + 1
        if next_val > self.max_value:
            next_val = self.min_value
            
        self.lbl_prev.config(text=self.format_str.format(prev_val))
        self.lbl_curr.config(text=self.format_str.format(self.value))
        self.lbl_next.config(text=self.format_str.format(next_val))
        
    def shift(self, delta):
        rng = self.max_value - self.min_value + 1
        new_val = self.value + delta
        if new_val > self.max_value:
            new_val = self.min_value + ((new_val - self.min_value) % rng)
        elif new_val < self.min_value:
            new_val = self.max_value - ((self.min_value - new_val - 1) % rng)
        self.value = new_val
        self.refresh()
        
    def get(self):
        return self.value
        
    def set(self, val):
        self.value = max(self.min_value, min(self.max_value, int(val)))
        self.refresh()
        
    def _on_wheel(self, event):
        delta = -1 if event.delta > 0 else 1
        self.shift(delta)
        
    def _drag_start(self, event):
        self._drag_y = event.y_root
        
    def _drag_move(self, event):
        if self._drag_y is None:
            return
        diff = self._drag_y - event.y_root
        if abs(diff) >= 15:
            steps = int(diff / 15)
            self.shift(steps)
            self._drag_y -= steps * 15
            
    def _drag_end(self, event):
        self._drag_y = None


# --- APP STATE DIRECT STORAGE CONTROLLER ---
def default_state():
    return {
        "alarms": [
            {
                "time": "08:00",
                "ampm": "am",
                "label": "Every day",
                "days": [0, 1, 2, 3, 4, 5, 6],
                "active": True,
                "snooze": "5 min, 3 times",
                "sound": True,
                "vibration": True,
            },
            {
                "time": "01:00",
                "ampm": "am",
                "label": "Work",
                "days": [1, 2, 3, 4, 5],
                "active": False,
                "snooze": "5 min, 3 times",
                "sound": True,
                "vibration": True,
            },
        ],
        "cities": [
            {"name": "Bangkok", "offset_str": "1 hr 30 mins ahead", "hours_off": 1.5},
            {"name": "Frankfurt", "offset_str": "3 hrs 30 mins behind", "hours_off": -3.5},
            {"name": "Washington DC", "offset_str": "9 hrs 30 mins behind", "hours_off": -9.5},
        ],
        "stopwatch_history": [],
        "timer_presets": [
            {"name": "Study", "time": "00:25:00"},
            {"name": "Break", "time": "00:10:00"},
            {"name": "Sleep", "time": "01:00:00"},
        ],
        "settings": {
            "username": "User_2050",
            "time_format": "12h",
            "alarm_sound": "Soft Bell",
            "alarm_vibration": True,
            "system_sound": True,
        },
    }

def load_storage():
    state = default_state()
    if APP_DATA_FILE.exists():
        try:
            with open(APP_DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                for key in state:
                    if key in data:
                        state[key] = data[key]
        except Exception:
            pass
    return state


# --- CLOCK PAGES (PORTABLE VIEWS) ---

class AlarmPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.edit_mode = False
        self.selected_alarms = set()
        self.setup_ui()
        self.render_alarms()

    def setup_ui(self):
        self.configure(style="TFrame")
        top = tk.Frame(self, bg=BG)
        top.pack(fill="x", padx=16, pady=(14, 8))
        left = tk.Frame(top, bg=BG)
        left.pack(side="left", fill="x", expand=True)
        tk.Label(left, text="Alarm", font=("Segoe UI", 22, "bold"), bg=BG, fg=TEXT).pack(anchor="w")
        tk.Label(left, text="Active alarms with synthesized cues", font=("Segoe UI", 9), bg=BG, fg=MUTED).pack(anchor="w", pady=(2, 0))

        tk.Button(top, text="＋", bg=BG_2, fg=ACCENT, bd=0, width=3, font=("Segoe UI", 15, "bold"), command=lambda: self.open_alarm_editor()).pack(side="right", padx=(8, 0))
        tk.Button(top, text="⋮", bg=BG_2, fg=TEXT, bd=0, width=3, font=("Segoe UI", 15, "bold"), command=self.show_menu).pack(side="right")

        self.canvas_scroll = tk.Canvas(self, bg=BG, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas_scroll.yview)
        self.alarms_frame = tk.Frame(self.canvas_scroll, bg=BG)
        
        self.alarms_frame.bind("<Configure>", lambda e: self.canvas_scroll.configure(scrollregion=self.canvas_scroll.bbox("all")))
        self.canvas_window_id = self.canvas_scroll.create_window((0, 0), window=self.alarms_frame, anchor="nw")
        self.canvas_scroll.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas_scroll.pack(side="left", fill="both", expand=True, padx=14, pady=6)
        self.scrollbar.pack(side="right", fill="y", pady=6)
        self.canvas_scroll.bind("<Configure>", self._on_resize)

    def _on_resize(self, event):
        width = max(260, event.width - 4)
        self.canvas_scroll.itemconfigure(self.canvas_window_id, width=width)

    def render_alarms(self):
        for w in self.alarms_frame.winfo_children():
            w.destroy()

        if self.edit_mode:
            bar = tk.Frame(self.alarms_frame, bg=BG)
            bar.pack(fill="x", pady=(0, 8))
            tk.Button(bar, text="Delete Selected", fg="white", bg=DANGER, bd=0, padx=12, pady=6, command=self.delete_selected).pack(side="left")
            tk.Button(bar, text="Cancel", fg=TEXT, bg=BG_2, bd=0, padx=12, pady=6, command=self.toggle_edit_mode).pack(side="right")

        alarms = self.controller.app_state.get("alarms", [])
        if not alarms:
            empty = tk.Frame(self.alarms_frame, bg=CARD, highlightthickness=1, highlightbackground=LINE)
            empty.pack(fill="x", pady=10)
            tk.Label(empty, text="No alarms set", font=("Segoe UI", 12, "bold"), bg=CARD, fg=TEXT).pack(pady=(20, 2))
            tk.Label(empty, text="Tap + or command the chatbot to add one", font=("Segoe UI", 9), bg=CARD, fg=MUTED).pack(pady=(0, 20))
            return

        for i, alarm in enumerate(alarms):
            card = tk.Frame(self.alarms_frame, bg=CARD, highlightthickness=1, highlightbackground=LINE)
            card.pack(fill="x", pady=6)

            inner = tk.Frame(card, bg=CARD)
            inner.pack(fill="x", padx=12, pady=10)

            if self.edit_mode:
                var = tk.BooleanVar(value=i in self.selected_alarms)
                tk.Checkbutton(inner, variable=var, bg=CARD, selectcolor=CARD_2, activebackground=CARD, bd=0, command=lambda idx=i: self.toggle_selection(idx)).pack(side="left", padx=(0, 8))

            info = tk.Frame(inner, bg=CARD)
            info.pack(side="left", fill="x", expand=True)

            active = alarm.get("active", True)
            time_lbl = tk.Label(info, text=f"{alarm['time']} {alarm['ampm'].upper()}", font=("Segoe UI", 20, "bold"), bg=CARD, fg=TEXT if active else MUTED)
            time_lbl.pack(anchor="w")
            
            days_str = ", ".join(DAY_NAMES[d] for d in alarm.get("days", [])) or "Never"
            tk.Label(info, text=f"{alarm.get('label','Alarm')} • {days_str}", font=("Segoe UI", 9), bg=CARD, fg=MUTED).pack(anchor="w", pady=(2, 0))

            tags = tk.Frame(info, bg=CARD)
            tags.pack(anchor="w", pady=(6, 0))
            for t in [alarm.get("snooze", "Snooze"), "Sound" if alarm.get("sound", True) else "Silent", "Vibe" if alarm.get("vibration", True) else "No vibe"]:
                tk.Label(tags, text=t, bg=CARD_2, fg=TEXT, font=("Segoe UI", 8), padx=6, pady=2).pack(side="left", padx=(0, 4))

            if not self.edit_mode:
                switch = CanvasSwitch(inner, value=active, command=lambda val, idx=i: self.toggle_alarm_active(idx, val))
                switch.pack(side="right", padx=(8, 0))
                
                # Bind open editor click
                for widget in (card, inner, info, time_lbl):
                    widget.bind("<Button-1>", lambda e, idx=i: self.open_alarm_editor(idx))

    def toggle_alarm_active(self, index, val):
        self.controller.app_state["alarms"][index]["active"] = val
        self.controller.queue_save()
        self.render_alarms()

    def toggle_edit_mode(self):
        self.edit_mode = not self.edit_mode
        self.selected_alarms.clear()
        self.render_alarms()

    def toggle_selection(self, index):
        if index in self.selected_alarms:
            self.selected_alarms.remove(index)
        else:
            self.selected_alarms.add(index)

    def delete_selected(self):
        self.controller.app_state["alarms"] = [a for idx, a in enumerate(self.controller.app_state["alarms"]) if idx not in self.selected_alarms]
        self.toggle_edit_mode()
        self.controller.queue_save()
        self.controller.refresh_all_views()

    def sort_alarms(self):
        self.controller.app_state["alarms"].sort(key=lambda a: datetime.strptime(f"{a['time']} {a['ampm']}", "%I:%M %p"))
        self.render_alarms()
        self.controller.queue_save()

    def show_menu(self):
        menu = tk.Menu(self, tearoff=0, bg=BG_2, fg=TEXT, activebackground=CARD_2, activeforeground=ACCENT)
        menu.add_command(label="Edit Mode", command=self.toggle_edit_mode)
        menu.add_command(label="Sort by Time", command=self.sort_alarms)
        menu.add_separator()
        menu.add_command(label="Settings", command=self.controller.open_settings)
        menu.tk_popup(self.winfo_pointerx(), self.winfo_pointery())

    def open_alarm_editor(self, index=None):
        dialog = tk.Toplevel(self)
        dialog.title("Alarm Editor")
        dialog.geometry("380x560")
        dialog.configure(bg=BG)
        dialog.transient(self)
        dialog.grab_set()
        gentle_open(dialog, "380x560")

        target = self.controller.app_state["alarms"][index] if index is not None else {
            "time": "08:00",
            "ampm": "am",
            "label": "Alarm Name",
            "days": [],
            "snooze": "5 min, 3 times",
            "sound": True,
            "vibration": True,
        }

        shell = tk.Frame(dialog, bg=BG)
        shell.pack(fill="both", expand=True, padx=16, pady=16)

        tk.Label(shell, text="Set Alarm", bg=BG, fg=TEXT, font=("Segoe UI", 18, "bold")).pack(anchor="w")
        tk.Label(shell, text="Drag digits to scroll values", bg=BG, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w", pady=(2, 10))

        card = tk.Frame(shell, bg=CARD, highlightthickness=1, highlightbackground=LINE)
        card.pack(fill="both", expand=True)

        time_frame = tk.Frame(card, bg=CARD)
        time_frame.pack(pady=15)
        
        hour_val, min_val = target["time"].split(":")
        hour_picker = RollingPicker(time_frame, value=int(hour_val), min_value=1, max_value=12)
        min_picker = RollingPicker(time_frame, value=int(min_val), min_value=0, max_value=59)
        ampm_picker = RollingPicker(time_frame, value=0 if target["ampm"].lower() == "am" else 1, min_value=0, max_value=1, format_str="{}", font_main=("Segoe UI", 14, "bold"))
        # Hack formatting for ampm
        ampm_picker.lbl_prev.config(text="PM" if target["ampm"].lower() == "am" else "AM")
        ampm_picker.lbl_curr.config(text=target["ampm"].upper())
        ampm_picker.lbl_next.config(text="PM" if target["ampm"].lower() == "am" else "AM")
        
        def ampm_shifted(d):
            val = ampm_picker.get()
            ampm_picker.lbl_curr.config(text="AM" if val == 0 else "PM")
            ampm_picker.lbl_prev.config(text="PM" if val == 0 else "AM")
            ampm_picker.lbl_next.config(text="PM" if val == 0 else "AM")
        ampm_picker.lbl_curr.bind("<Configure>", lambda e: ampm_shifted(0))

        hour_picker.pack(side="left", padx=4)
        tk.Label(time_frame, text=":", bg=CARD, fg=TEXT, font=("Segoe UI", 18, "bold")).pack(side="left")
        min_picker.pack(side="left", padx=4)
        ampm_picker.pack(side="left", padx=(10, 0))

        body = tk.Frame(card, bg=CARD)
        body.pack(fill="x", padx=14)

        tk.Label(body, text="Label", bg=CARD, fg=MUTED, font=("Segoe UI", 9, "bold")).pack(anchor="w")
        name_entry = tk.Entry(body, bg=BG_2, fg=TEXT, insertbackground=TEXT, relief="flat", font=("Segoe UI", 10))
        name_entry.insert(0, target["label"])
        name_entry.pack(fill="x", pady=(4, 10), ipady=6)

        tk.Label(body, text="Repeat Days", bg=CARD, fg=MUTED, font=("Segoe UI", 9, "bold")).pack(anchor="w")
        day_frame = tk.Frame(body, bg=CARD)
        day_frame.pack(fill="x", pady=6)
        day_vars = []
        for idx, d in enumerate(DAY_NAMES):
            v = tk.BooleanVar(value=idx in target["days"])
            day_vars.append(v)
            tk.Checkbutton(day_frame, text=d, variable=v, indicatoron=False, width=3, bg=BG_2, fg=TEXT, activebackground=CARD_2, selectcolor=CARD_2, bd=0, font=("Segoe UI", 9, "bold")).pack(side="left", padx=1)

        tk.Label(body, text="Snooze", bg=CARD, fg=MUTED, font=("Segoe UI", 9, "bold")).pack(anchor="w")
        snooze_combo = ttk.Combobox(body, values=["5 min, 3 times", "10 min, 3 times", "Off"], state="readonly", font=("Segoe UI", 9))
        snooze_combo.set(target["snooze"])
        snooze_combo.pack(fill="x", pady=(4, 10))

        sound_var = tk.BooleanVar(value=target["sound"])
        vib_var = tk.BooleanVar(value=target["vibration"])
        tk.Checkbutton(body, text="Alarm Sound", variable=sound_var, bg=CARD, fg=TEXT, bd=0).pack(anchor="w")
        tk.Checkbutton(body, text="Vibration Cue", variable=vib_var, bg=CARD, fg=TEXT, bd=0).pack(anchor="w", pady=(4, 0))

        def save():
            new_data = {
                "time": f"{hour_picker.get():02d}:{min_picker.get():02d}",
                "ampm": "am" if ampm_picker.get() == 0 else "pm",
                "label": name_entry.get().strip() or "Alarm",
                "days": [idx for idx, v in enumerate(day_vars) if v.get()],
                "active": True,
                "snooze": snooze_combo.get(),
                "sound": sound_var.get(),
                "vibration": vib_var.get(),
            }
            if index is None:
                self.controller.app_state["alarms"].append(new_data)
            else:
                self.controller.app_state["alarms"][index] = new_data
            self.controller.queue_save()
            self.controller.refresh_all_views()
            dialog.destroy()

        footer = tk.Frame(shell, bg=BG)
        footer.pack(fill="x", pady=(10, 0))
        tk.Button(footer, text="Save Alarm Configuration", bg=ACCENT, fg="#1b1208", bd=0, font=("Segoe UI", 10, "bold"), pady=8, command=save).pack(fill="x")


class WorldClockPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.edit_mode = False
        self.selected_cities = set()
        self.setup_ui()
        self.update_clock()

    def setup_ui(self):
        self.configure(style="TFrame")
        top = tk.Frame(self, bg=BG)
        top.pack(fill="x", padx=16, pady=(14, 8))
        left = tk.Frame(top, bg=BG)
        left.pack(side="left", fill="x", expand=True)
        tk.Label(left, text="World Clock", font=("Segoe UI", 22, "bold"), bg=BG, fg=TEXT).pack(anchor="w")
        tk.Label(left, text="Relative time tracking offsets", font=("Segoe UI", 9), bg=BG, fg=MUTED).pack(anchor="w", pady=(2, 0))

        tk.Button(top, text="＋", bg=BG_2, fg=ACCENT, bd=0, width=3, font=("Segoe UI", 15, "bold"), command=self.open_add_location).pack(side="right", padx=(8, 0))
        tk.Button(top, text="⋮", bg=BG_2, fg=TEXT, bd=0, width=3, font=("Segoe UI", 15, "bold"), command=self.show_menu).pack(side="right")

        # Large local clock card
        local_card = tk.Frame(self, bg=CARD, highlightthickness=1, highlightbackground=LINE)
        local_card.pack(fill="x", padx=16, pady=8)
        block = tk.Frame(local_card, bg=CARD)
        block.pack(fill="x", padx=14, pady=12)

        self.time_lbl = tk.Label(block, text="00:00:00 AM", font=("Segoe UI", 26, "bold"), bg=CARD, fg=ACCENT)
        self.time_lbl.pack(anchor="w")
        self.date_lbl = tk.Label(block, text="Wednesday, June 3, 2026", font=("Segoe UI", 10), bg=CARD, fg=TEXT)
        self.date_lbl.pack(anchor="w", pady=(2, 0))
        tk.Label(block, text="Local Zone Time", font=("Segoe UI", 8), bg=CARD, fg=MUTED).pack(anchor="w", pady=(2, 0))

        # Cities list
        self.canvas_scroll = tk.Canvas(self, bg=BG, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas_scroll.yview)
        self.cities_frame = tk.Frame(self.canvas_scroll, bg=BG)
        
        self.cities_frame.bind("<Configure>", lambda e: self.canvas_scroll.configure(scrollregion=self.canvas_scroll.bbox("all")))
        self.canvas_window_id = self.canvas_scroll.create_window((0, 0), window=self.cities_frame, anchor="nw")
        self.canvas_scroll.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas_scroll.pack(side="left", fill="both", expand=True, padx=14, pady=6)
        self.scrollbar.pack(side="right", fill="y", pady=6)
        self.canvas_scroll.bind("<Configure>", self._on_resize)

    def _on_resize(self, event):
        width = max(260, event.width - 4)
        self.canvas_scroll.itemconfigure(self.canvas_window_id, width=width)

    def refresh_cities_list(self):
        for w in self.cities_frame.winfo_children():
            w.destroy()

        if self.edit_mode:
            bar = tk.Frame(self.cities_frame, bg=BG)
            bar.pack(fill="x", pady=(0, 8))
            tk.Button(bar, text="Delete Selected", fg="white", bg=DANGER, bd=0, padx=12, pady=6, command=self.delete_selected).pack(side="left")
            tk.Button(bar, text="Cancel", fg=TEXT, bg=BG_2, bd=0, padx=12, pady=6, command=self.toggle_edit_mode).pack(side="right")

        cities = self.controller.app_state.get("cities", [])
        if not cities:
            empty = tk.Frame(self.cities_frame, bg=CARD, highlightthickness=1, highlightbackground=LINE)
            empty.pack(fill="x", pady=10)
            tk.Label(empty, text="No tracked zones", font=("Segoe UI", 12, "bold"), bg=CARD, fg=TEXT).pack(pady=(20, 2))
            tk.Label(empty, text="Add coordinates or cities using chatbot", font=("Segoe UI", 9), bg=CARD, fg=MUTED).pack(pady=(0, 20))
            return

        for i, city in enumerate(cities):
            card = tk.Frame(self.cities_frame, bg=CARD, highlightthickness=1, highlightbackground=LINE)
            card.pack(fill="x", pady=6)

            inner = tk.Frame(card, bg=CARD)
            inner.pack(fill="x", padx=12, pady=10)

            if self.edit_mode:
                var = tk.BooleanVar(value=i in self.selected_cities)
                tk.Checkbutton(inner, variable=var, bg=CARD, selectcolor=CARD_2, activebackground=CARD, bd=0, command=lambda idx=i: self.toggle_selection(idx)).pack(side="left", padx=(0, 8))

            info = tk.Frame(inner, bg=CARD)
            info.pack(side="left", fill="x", expand=True)

            tk.Label(info, text=city["name"], font=("Segoe UI", 13, "bold"), bg=CARD, fg=TEXT).pack(anchor="w")
            tk.Label(info, text=city["offset_str"], font=("Segoe UI", 8), bg=CARD, fg=MUTED).pack(anchor="w", pady=(2, 0))

            time_lbl = tk.Label(inner, text="--:--", font=("Segoe UI", 16, "bold"), bg=CARD, fg=ACCENT)
            time_lbl.pack(side="right", padx=(8, 0))

            if not self.edit_mode:
                for widget in (card, inner, info, time_lbl):
                    widget.bind("<Button-1>", lambda e, c=city: self.open_city_details(c))

    def update_clock(self):
        try:
            now = datetime.now()
            settings = self.controller.app_state.get("settings", {})
            fmt_24 = settings.get("time_format", "12h") == "24h"

            # 1. Update Local Clock
            if fmt_24:
                self.time_lbl.config(text=now.strftime("%H:%M:%S"))
            else:
                self.time_lbl.config(text=now.strftime("%I:%M:%S %p"))
            self.date_lbl.config(text=now.strftime("%A, %d %B %Y"))

            # 2. Update tracked cities inside scroll frame
            cities = self.controller.app_state.get("cities", [])
            children = self.cities_frame.winfo_children()
            
            # Loop and find cards to update times dynamically
            card_idx = 0
            if self.edit_mode:
                card_idx = 1 # Skip delete/cancel bar
                
            for idx, city in enumerate(cities):
                if card_idx >= len(children):
                    break
                card = children[card_idx]
                card_idx += 1
                try:
                    # Find inner time label inside card container
                    inner_frame = card.winfo_children()[0]
                    # The right-packed widget is the time label
                    time_widget = None
                    for w in inner_frame.winfo_children():
                        if isinstance(w, tk.Label) and w.cget("fg") == ACCENT:
                            time_widget = w
                            break
                    if time_widget:
                        city_time = now + timedelta(hours=city["hours_off"])
                        if fmt_24:
                            time_widget.config(text=city_time.strftime("%H:%M"))
                        else:
                            time_widget.config(text=city_time.strftime("%I:%M %p"))
                except Exception:
                    pass
        except Exception:
            pass

        self.after(1000, self.update_clock)

    def show_menu(self):
        menu = tk.Menu(self, tearoff=0, bg=BG_2, fg=TEXT, activebackground=CARD_2, activeforeground=ACCENT)
        menu.add_command(label="Edit Mode", command=self.toggle_edit_mode)
        menu.add_separator()
        menu.add_command(label="Settings", command=self.controller.open_settings)
        menu.tk_popup(self.winfo_pointerx(), self.winfo_pointery())

    def toggle_edit_mode(self):
        self.edit_mode = not self.edit_mode
        self.selected_cities.clear()
        self.refresh_cities_list()

    def toggle_selection(self, index):
        if index in self.selected_cities:
            self.selected_cities.remove(index)
        else:
            self.selected_cities.add(index)

    def delete_selected(self):
        self.controller.app_state["cities"] = [c for idx, c in enumerate(self.controller.app_state["cities"]) if idx not in self.selected_cities]
        self.toggle_edit_mode()
        self.controller.queue_save()
        self.controller.refresh_all_views()

    def open_add_location(self):
        win = tk.Toplevel(self)
        win.title("Add Location")
        win.geometry("380x480")
        win.configure(bg=BG)
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()
        gentle_open(win, "380x480")

        shell = tk.Frame(win, bg=BG)
        shell.pack(fill="both", expand=True, padx=16, pady=16)
        tk.Label(shell, text="Add World Location", bg=BG, fg=TEXT, font=("Segoe UI", 16, "bold")).pack(anchor="w")
        tk.Label(shell, text="Define target offset coordinates", bg=BG, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w", pady=(2, 10))

        card = tk.Frame(shell, bg=CARD, highlightthickness=1, highlightbackground=LINE)
        card.pack(fill="both", expand=True)

        body = tk.Frame(card, bg=CARD)
        body.pack(fill="x", padx=14, pady=10)

        tk.Label(body, text="City Name", bg=CARD, fg=MUTED, font=("Segoe UI", 9, "bold")).pack(anchor="w")
        name_entry = tk.Entry(body, bg=BG_2, fg=TEXT, insertbackground=TEXT, relief="flat", font=("Segoe UI", 10))
        name_entry.pack(fill="x", pady=(4, 10), ipady=6)

        off_row = tk.Frame(body, bg=CARD)
        off_row.pack(fill="x")
        tk.Label(off_row, text="Hours Offset", bg=CARD, fg=MUTED, font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w")
        tk.Label(off_row, text="Minutes", bg=CARD, fg=MUTED, font=("Segoe UI", 9, "bold")).grid(row=0, column=1, sticky="w", padx=(10, 0))
        tk.Label(off_row, text="Direction", bg=CARD, fg=MUTED, font=("Segoe UI", 9, "bold")).grid(row=0, column=2, sticky="w", padx=(10, 0))

        hours_picker = RollingPicker(off_row, value=0, min_value=0, max_value=14, width=3)
        mins_picker = RollingPicker(off_row, value=0, min_value=0, max_value=59, width=3)
        dir_picker = RollingPicker(off_row, value=0, min_value=0, max_value=1, format_str="{}", font_main=("Segoe UI", 11, "bold"), width=7)
        # Hack label format
        dir_picker.lbl_prev.config(text="behind")
        dir_picker.lbl_curr.config(text="ahead")
        dir_picker.lbl_next.config(text="behind")
        
        def dir_shifted():
            val = dir_picker.get()
            dir_picker.lbl_curr.config(text="ahead" if val == 0 else "behind")
            dir_picker.lbl_prev.config(text="behind" if val == 0 else "ahead")
            dir_picker.lbl_next.config(text="behind" if val == 0 else "ahead")
        dir_picker.lbl_curr.bind("<Configure>", lambda e: dir_shifted())

        hours_picker.grid(row=1, column=0, sticky="w", pady=4)
        mins_picker.grid(row=1, column=1, sticky="w", padx=(10, 0), pady=4)
        dir_picker.grid(row=1, column=2, sticky="w", padx=(10, 0), pady=4)

        preview = tk.Label(body, text="Preview: 0 hrs ahead", bg=CARD, fg=ACCENT, font=("Segoe UI", 9, "bold"))
        preview.pack(anchor="w", pady=(10, 0))

        def update_preview(event=None):
            hours = hours_picker.get()
            mins = mins_picker.get()
            total = hours + (mins / 60.0)
            sign = 1 if dir_picker.get() == 0 else -1
            preview.config(text=f"Preview: {self.format_offset(sign * total)}")
            win.after(100, update_preview)
            
        win.after(100, update_preview)

        def add_city():
            name = name_entry.get().strip()
            if not name:
                return
            hours = hours_picker.get()
            mins = mins_picker.get()
            total = hours + (mins / 60.0)
            if dir_picker.get() == 1:
                total = -total
                
            self.controller.app_state["cities"].append({
                "name": name,
                "offset_str": self.format_offset(total),
                "hours_off": total
            })
            self.controller.queue_save()
            self.controller.refresh_all_views()
            win.destroy()

        tk.Button(shell, text="Add Tracked Zone", bg=ACCENT, fg="#1b1208", bd=0, font=("Segoe UI", 10, "bold"), pady=8, command=add_city).pack(fill="x", pady=(10, 0))

    def format_offset(self, hours_off):
        total_minutes = int(round(abs(hours_off) * 60))
        hours = total_minutes // 60
        mins = total_minutes % 60
        if mins == 0:
            text = f"{hours} hr{'s' if hours != 1 else ''}"
        else:
            text = f"{hours} hr{'s' if hours != 1 else ''} {mins} mins"
        return f"{text} {'ahead' if hours_off >= 0 else 'behind'}"

    def open_city_details(self, city):
        win = tk.Toplevel(self)
        win.title(city["name"])
        win.geometry("340x400")
        win.configure(bg=BG)
        win.transient(self)
        win.grab_set()
        gentle_open(win, "340x400")

        shell = tk.Frame(win, bg=BG)
        shell.pack(fill="both", expand=True, padx=16, pady=16)

        now = datetime.now()
        target = now + timedelta(hours=city["hours_off"])

        tk.Label(shell, text=city["name"], bg=BG, fg=TEXT, font=("Segoe UI", 20, "bold")).pack(pady=(6, 4))
        
        card = tk.Frame(shell, bg=CARD, highlightthickness=1, highlightbackground=LINE)
        card.pack(fill="both", expand=True)

        tk.Label(card, text=target.strftime("%A, %d %B"), bg=CARD, fg=MUTED, font=("Segoe UI", 11)).pack(pady=(15, 4))
        
        settings = self.controller.app_state.get("settings", {})
        fmt_24 = settings.get("time_format", "12h") == "24h"
        clock_text = target.strftime("%H:%M") if fmt_24 else target.strftime("%I:%M %p")
        
        tk.Label(card, text=clock_text, bg=CARD, fg=ACCENT, font=("Segoe UI", 32, "bold")).pack(pady=6)
        tk.Label(card, text=city["offset_str"], bg=CARD, fg=TEXT, font=("Segoe UI", 9, "italic")).pack()
        
        # Simulated live coordinates widget
        viz = tk.Frame(card, bg=BG_2, height=120, highlightthickness=1, highlightbackground=LINE)
        viz.pack(fill="x", padx=16, pady=16)
        lbl_coord = tk.Label(viz, text="REAL-TIME TELEMETRY CONNECTED\nRETRIEVING GEOLOCATION COORDINATES...", bg=BG_2, fg=ACCENT_2, font=("Courier New", 8, "bold"), justify="center")
        lbl_coord.place(relx=0.5, rely=0.5, anchor="center")


class StopwatchPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.running = False
        self.start_time = 0
        self.accumulated = 0
        self.laps = []
        self.history = controller.app_state.get("stopwatch_history", [])
        self.setup_ui()

    def setup_ui(self):
        self.configure(style="TFrame")
        top = tk.Frame(self, bg=BG)
        top.pack(fill="x", padx=16, pady=(14, 8))
        tk.Label(top, text="Stopwatch", font=("Segoe UI", 22, "bold"), bg=BG, fg=TEXT).pack(side="left")
        tk.Label(top, text="High precision lap timer", font=("Segoe UI", 9), bg=BG, fg=MUTED).pack(side="left", padx=8, pady=(8, 0))
        tk.Button(top, text="⋮", bg=BG_2, fg=TEXT, bd=0, width=3, font=("Segoe UI", 15, "bold"), command=self.show_menu).pack(side="right")

        display = tk.Frame(self, bg=CARD, highlightthickness=1, highlightbackground=LINE)
        display.pack(fill="x", padx=16, pady=8)
        self.time_lbl = tk.Label(display, text="00:00.00", bg=CARD, fg=ACCENT, font=("Segoe UI", 36, "bold"))
        self.time_lbl.pack(pady=(16, 2))
        self.sub_lbl = tk.Label(display, text="Tap Start to log elapsed values", bg=CARD, fg=MUTED, font=("Segoe UI", 9))
        self.sub_lbl.pack(pady=(0, 16))

        # Controls
        ctrls = tk.Frame(self, bg=BG)
        ctrls.pack(fill="x", padx=16, pady=4)
        
        self.btn_left = tk.Button(ctrls, text="Lap", bg=BG_2, fg=TEXT, state="disabled", font=("Segoe UI", 10, "bold"), bd=0, padx=16, pady=8, command=self.do_left)
        self.btn_left.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.btn_right = tk.Button(ctrls, text="Start", bg=ACCENT, fg="#1b1208", font=("Segoe UI", 10, "bold"), bd=0, padx=16, pady=8, command=self.do_right)
        self.btn_right.pack(side="right", fill="x", expand=True, padx=(6, 0))

        # Lap listing container
        self.laps_canvas = tk.Canvas(self, bg=BG, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.laps_canvas.yview)
        self.laps_frame = tk.Frame(self.laps_canvas, bg=BG)
        
        self.laps_frame.bind("<Configure>", lambda e: self.laps_canvas.configure(scrollregion=self.laps_canvas.bbox("all")))
        self.canvas_window_id = self.laps_canvas.create_window((0, 0), window=self.laps_frame, anchor="nw")
        self.laps_canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.laps_canvas.pack(side="left", fill="both", expand=True, padx=16, pady=10)
        self.scrollbar.pack(side="right", fill="y", pady=10)
        self.laps_canvas.bind("<Configure>", self._on_resize)

    def _on_resize(self, event):
        width = max(240, event.width - 4)
        self.laps_canvas.itemconfigure(self.canvas_window_id, width=width)

    def update_ticks(self):
        if self.running:
            elapsed = self.accumulated + (time.time() - self.start_time)
            mins = int(elapsed // 60)
            secs = int(elapsed % 60)
            cents = int((elapsed * 100) % 100)
            self.time_lbl.config(text=f"{mins:02d}:{secs:02d}.{cents:02d}")
            self.after(10, self.update_ticks)

    def do_right(self):
        if not self.running:
            # Start
            self.running = True
            self.start_time = time.time()
            self.btn_right.config(text="Stop", bg=DANGER, fg="white")
            self.btn_left.config(text="Lap", state="normal")
            self.update_ticks()
        else:
            # Stop
            self.running = False
            self.accumulated += (time.time() - self.start_time)
            self.btn_right.config(text="Start", bg=ACCENT, fg="#1b1208")
            self.btn_left.config(text="Reset")

    def do_left(self):
        if self.running:
            # Lap log
            elapsed = self.accumulated + (time.time() - self.start_time)
            mins = int(elapsed // 60)
            secs = int(elapsed % 60)
            cents = int((elapsed * 100) % 100)
            lap_time = f"{mins:02d}:{secs:02d}.{cents:02d}"
            self.laps.append(lap_time)
            self.render_laps()
        else:
            # Reset
            if self.accumulated > 0:
                # Save to history session
                mins = int(self.accumulated // 60)
                secs = int(self.accumulated % 60)
                cents = int((self.accumulated * 100) % 100)
                total_duration = f"{mins:02d}:{secs:02d}.{cents:02d}"
                session = {
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "duration": total_duration,
                    "laps": list(self.laps)
                }
                self.history.append(session)
                self.controller.app_state["stopwatch_history"] = self.history
                self.controller.queue_save()
                
            self.accumulated = 0
            self.laps = []
            self.time_lbl.config(text="00:00.00")
            self.btn_left.config(text="Lap", state="disabled")
            self.render_laps()

    def render_laps(self):
        for w in self.laps_frame.winfo_children():
            w.destroy()
            
        if not self.laps:
            return
            
        # Draw table headers
        header = tk.Frame(self.laps_frame, bg=BG)
        header.pack(fill="x", pady=2)
        tk.Label(header, text="Lap Number", font=("Segoe UI", 9, "bold"), bg=BG, fg=MUTED).pack(side="left")
        tk.Label(header, text="Split Duration", font=("Segoe UI", 9, "bold"), bg=BG, fg=MUTED).pack(side="right")
        
        for idx, lap in enumerate(reversed(self.laps)):
            row = tk.Frame(self.laps_frame, bg=CARD, bd=1, relief="solid", highlightthickness=0)
            row.configure(highlightbackground=LINE, highlightcolor=LINE)
            row.pack(fill="x", pady=2, ipady=4)
            
            num = len(self.laps) - idx
            tk.Label(row, text=f"Lap {num:02d}", font=("Segoe UI", 10), bg=CARD, fg=TEXT).pack(side="left", padx=8)
            tk.Label(row, text=lap, font=("JetBrains Mono", 10, "bold"), bg=CARD, fg=ACCENT).pack(side="right", padx=8)

    def show_menu(self):
        menu = tk.Menu(self, tearoff=0, bg=BG_2, fg=TEXT, activebackground=CARD_2, activeforeground=ACCENT)
        menu.add_command(label="Clear Session History", command=self.clear_history)
        menu.tk_popup(self.winfo_pointerx(), self.winfo_pointery())
        
    def clear_history(self):
        self.history = []
        self.controller.app_state["stopwatch_history"] = []
        self.controller.queue_save()
        messagebox.showinfo("Stopwatch", "Session logs cleared.")


class TimerPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.running = False
        self.paused = False
        self.total_seconds = 0
        self.remaining_seconds = 0
        self.presets = controller.app_state.get("timer_presets", [])
        self.setup_ui()

    def setup_ui(self):
        self.configure(style="TFrame")
        top = tk.Frame(self, bg=BG)
        top.pack(fill="x", padx=16, pady=(14, 8))
        tk.Label(top, text="Timer", font=("Segoe UI", 22, "bold"), bg=BG, fg=TEXT).pack(side="left")
        tk.Label(top, text="Focused countdown intervals", font=("Segoe UI", 9), bg=BG, fg=MUTED).pack(side="left", padx=8, pady=(8, 0))
        tk.Button(top, text="⋮", bg=BG_2, fg=TEXT, bd=0, width=3, font=("Segoe UI", 15, "bold"), command=self.show_menu).pack(side="right")

        self.main_container = tk.Frame(self, bg=BG)
        self.main_container.pack(fill="both", expand=True, padx=16)

        self.show_setup_view()

    def show_setup_view(self):
        for w in self.main_container.winfo_children():
            w.destroy()

        # Preset Cards Grid
        tk.Label(self.main_container, text="Presets", font=("Segoe UI", 10, "bold"), bg=BG, fg=MUTED).pack(anchor="w", pady=(8, 4))
        presets_frame = tk.Frame(self.main_container, bg=BG)
        presets_frame.pack(fill="x", pady=4)

        for p in self.presets:
            btn = tk.Button(presets_frame, text=f"{p['name']}\n{p['time']}", font=("Segoe UI", 9, "bold"), bg=CARD, fg=TEXT, activebackground=CARD_2, relief="solid", bd=1, highlightthickness=0, padx=10, pady=8, command=lambda t=p['time']: self.start_preset(t))
            btn.pack(side="left", fill="x", expand=True, padx=2)

        # Custom Wheels Input Picker
        tk.Label(self.main_container, text="Custom Countdown Duration", font=("Segoe UI", 10, "bold"), bg=BG, fg=MUTED).pack(anchor="w", pady=(14, 4))
        card = tk.Frame(self.main_container, bg=CARD, highlightthickness=1, highlightbackground=LINE)
        card.pack(fill="x", pady=4)

        picker_row = tk.Frame(card, bg=CARD)
        picker_row.pack(pady=12)

        self.hour_picker = RollingPicker(picker_row, value=0, min_value=0, max_value=23)
        self.min_picker = RollingPicker(picker_row, value=5, min_value=0, max_value=59)
        self.sec_picker = RollingPicker(picker_row, value=0, min_value=0, max_value=59)

        self.hour_picker.pack(side="left", padx=4)
        tk.Label(picker_row, text="h", bg=CARD, fg=TEXT, font=("Segoe UI", 10, "bold")).pack(side="left", padx=2)
        self.min_picker.pack(side="left", padx=4)
        tk.Label(picker_row, text="m", bg=CARD, fg=TEXT, font=("Segoe UI", 10, "bold")).pack(side="left", padx=2)
        self.sec_picker.pack(side="left", padx=4)
        tk.Label(picker_row, text="s", bg=CARD, fg=TEXT, font=("Segoe UI", 10, "bold")).pack(side="left", padx=2)

        tk.Button(self.main_container, text="Start Interval Timer", bg=ACCENT, fg="#1b1208", font=("Segoe UI", 11, "bold"), bd=0, pady=10, command=self.start_custom).pack(fill="x", pady=14)

    def show_countdown_view(self):
        for w in self.main_container.winfo_children():
            w.destroy()

        # Canvas for drawing the circular progress ring
        self.circle_canvas = tk.Canvas(self.main_container, width=190, height=190, bg=BG, highlightthickness=0)
        self.circle_canvas.pack(pady=15)

        # Draw default background circle path
        self.circle_canvas.create_oval(10, 10, 180, 180, outline=LINE, width=6)
        # Red countdown arc overlay
        self.arc_id = self.circle_canvas.create_arc(10, 10, 180, 180, start=90, extent=360, outline=ACCENT, width=8, style="arc")

        # Dynamic inner time label text
        self.count_lbl = tk.Label(self.circle_canvas, text="00:00:00", font=("JetBrains Mono", 20, "bold"), bg=BG, fg=TEXT)
        self.circle_canvas.create_window(95, 95, window=self.count_lbl)

        # Controls row
        btn_frame = tk.Frame(self.main_container, bg=BG)
        btn_frame.pack(fill="x", pady=10)

        self.btn_pause = tk.Button(btn_frame, text="Pause", bg=BG_2, fg=TEXT, font=("Segoe UI", 10, "bold"), bd=0, padx=16, pady=8, command=self.toggle_pause)
        self.btn_pause.pack(side="left", fill="x", expand=True, padx=(0, 6))

        tk.Button(btn_frame, text="Cancel", bg=DANGER, fg="white", font=("Segoe UI", 10, "bold"), bd=0, padx=16, pady=8, command=self.cancel_timer).pack(side="right", fill="x", expand=True, padx=(6, 0))

        self.running = True
        self.tick_timer()

    def start_preset(self, time_str):
        h, m, s = map(int, time_str.split(":"))
        self.total_seconds = h * 3600 + m * 60 + s
        self.remaining_seconds = self.total_seconds
        self.show_countdown_view()

    def start_custom(self):
        h = self.hour_picker.get()
        m = self.min_picker.get()
        s = self.sec_picker.get()
        self.total_seconds = h * 3600 + m * 60 + s
        if self.total_seconds <= 0:
            return
        self.remaining_seconds = self.total_seconds
        self.show_countdown_view()

    def toggle_pause(self):
        if not self.paused:
            self.paused = True
            self.btn_pause.config(text="Resume", bg=ACCENT, fg="#1b1208")
        else:
            self.paused = False
            self.btn_pause.config(text="Pause", bg=BG_2, fg=TEXT)
            self.tick_timer()

    def cancel_timer(self):
        self.running = False
        self.paused = False
        self.show_setup_view()

    def tick_timer(self):
        if not self.running or self.paused:
            return

        if self.remaining_seconds <= 0:
            self.running = False
            self.count_lbl.config(text="00:00:00")
            self.circle_canvas.itemconfig(self.arc_id, extent=0)
            self.controller.play_sound("timer")
            messagebox.showinfo("Timer Completed", "Countdown timer completed!")
            self.show_setup_view()
            return

        # Update text
        h = self.remaining_seconds // 3600
        m = (self.remaining_seconds % 3600) // 60
        s = self.remaining_seconds % 60
        self.count_lbl.config(text=f"{h:02d}:{m:02d}:{s:02d}")

        # Update circular arc extent (360 -> 0)
        pct = self.remaining_seconds / self.total_seconds
        self.circle_canvas.itemconfig(self.arc_id, extent=pct * 360)

        self.remaining_seconds -= 1
        self.after(1000, self.tick_timer)

    def show_menu(self):
        menu = tk.Menu(self, tearoff=0, bg=BG_2, fg=TEXT, activebackground=CARD_2, activeforeground=ACCENT)
        menu.add_command(label="Presets Configuration", command=self.controller.open_settings)
        menu.tk_popup(self.winfo_pointerx(), self.winfo_pointery())


class AssistantPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.setup_ui()

    def setup_ui(self):
        self.configure(style="TFrame")
        top = tk.Frame(self, bg=BG)
        top.pack(fill="x", padx=16, pady=(14, 8))
        tk.Label(top, text="Chat Assistant", font=("Segoe UI", 20, "bold"), bg=BG, fg=TEXT).pack(side="left")
        tk.Label(top, text="Conversational AIML Engine", font=("Segoe UI", 9), bg=BG, fg=MUTED).pack(side="left", padx=8, pady=(8, 0))

        # Chat container (Canvas + Scrollbar)
        self.chat_canvas = tk.Canvas(self, bg=BG, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.chat_canvas.yview)
        self.scroll_frame = tk.Frame(self.chat_canvas, bg=BG)
        
        self.scroll_frame.bind("<Configure>", lambda e: self.chat_canvas.configure(scrollregion=self.chat_canvas.bbox("all")))
        self.canvas_window = self.chat_canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        self.chat_canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.chat_canvas.pack(side="top", fill="both", expand=True, padx=16, pady=4)
        self.scrollbar.pack(side="right", fill="y")
        self.chat_canvas.bind("<Configure>", self._on_canvas_configure)

        # Bottom text entry box
        entry_frame = tk.Frame(self, bg=CARD_2, height=54, highlightthickness=1, highlightbackground=LINE)
        entry_frame.pack(fill="x", side="bottom", padx=16, pady=12)

        self.entry_var = tk.StringVar()
        self.entry = tk.Entry(entry_frame, textvariable=self.entry_var, bg=CARD, fg=TEXT, insertbackground=TEXT, font=("Segoe UI", 10), bd=0)
        self.entry.pack(side="left", fill="both", expand=True, padx=10, pady=8)
        self.entry.bind("<Return>", self.send_message)

        btn_send = tk.Button(entry_frame, text="Send Command", font=("Segoe UI", 9, "bold"), bg=ACCENT, fg="#1b1208", bd=0, padx=14, command=self.send_message)
        btn_send.pack(side="right", fill="both", padx=2, pady=2)

        # Welcome prompt
        self.add_message("Bot", "Hello! I am your Clock Companion. Type 'help' to see what commands I can perform, or try saying 'set alarm for 08:00 AM'!")

    def _on_canvas_configure(self, event):
        self.chat_canvas.itemconfigure(self.canvas_window, width=event.width)

    def send_message(self, event=None):
        text = self.entry_var.get().strip()
        if not text:
            return
        self.entry_var.set("")
        self.add_message("User", text)

        # Get bot response and actions from custom AIML engine
        response, actions = self.controller.aiml_engine.respond(text)
        
        # Execute actions & append responses
        act_feedback = []
        for act in actions:
            feedback = self.controller.execute_action(act)
            if feedback:
                act_feedback.append(feedback)
                
        if act_feedback:
            response += "\nSystem: " + " | ".join(act_feedback)
            
        self.add_message("Bot", response)

    def add_message(self, sender, text):
        row = tk.Frame(self.scroll_frame, bg=BG)
        row.pack(fill="x", pady=4)

        align = "right" if sender == "User" else "left"
        bg_color = BG_2 if sender == "User" else CARD
        border_color = LINE if sender == "User" else LINE

        bubble = tk.Frame(row, bg=bg_color, highlightthickness=1, highlightbackground=border_color)
        bubble.pack(side=align, padx=10, ipadx=10, ipady=6)

        lbl_sender = tk.Label(bubble, text=sender, font=("Segoe UI", 8, "bold"), bg=bg_color, fg=ACCENT if sender == "Bot" else MUTED)
        lbl_sender.pack(anchor="w")

        lbl_text = tk.Label(bubble, text=text, font=("Segoe UI", 9), bg=bg_color, fg=TEXT, justify="left", wraplength=230)
        lbl_text.pack(anchor="w", pady=(2, 0))

        self.chat_canvas.update_idletasks()
        self.chat_canvas.yview_moveto(1.0)


# --- MAIN DUAL-MODEL APPLICATION ---

class ClockApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.configure(bg=BG)
        self.app_state = load_storage()
        self._save_job = None
        self._alarm_check_job = None
        self.layout_mode = "phone" # default layout

        # Load Custom AIML Engine
        self.aiml_engine = AimlEngine()
        self.aiml_engine.learn("clock_brain.aiml")

        self._setup_window()
        self._setup_styles()
        
        # Main frames containers
        self.header_frame = tk.Frame(self, bg=BG_2, height=50)
        self.header_frame.pack(fill="x", side="top")
        self._draw_header()

        self.main_content = tk.Frame(self, bg=BG)
        self.main_content.pack(fill="both", expand=True)

        # Initialize Phone notebook and pages
        self.phone_canvas = tk.Canvas(self.main_content, bg=BG, highlightthickness=0)
        self.phone_notebook = ttk.Notebook(self.phone_canvas)
        
        self.phone_pages = {
            "alarm": AlarmPage(self.phone_notebook, self),
            "world_clock": WorldClockPage(self.phone_notebook, self),
            "stopwatch": StopwatchPage(self.phone_notebook, self),
            "timer": TimerPage(self.phone_notebook, self),
            "assistant": AssistantPage(self.phone_notebook, self)
        }
        self.phone_notebook.add(self.phone_pages["alarm"], text="⏰ Alarm")
        self.phone_notebook.add(self.phone_pages["world_clock"], text="🌍 World")
        self.phone_notebook.add(self.phone_pages["stopwatch"], text="⏱️ Watch")
        self.phone_notebook.add(self.phone_pages["timer"], text="⏳ Timer")
        self.phone_notebook.add(self.phone_pages["assistant"], text="💬 Chat")
        
        # Initialize Desktop wrappers and pages
        self.desktop_wrappers = {}
        self.desktop_pages = {}
        for key in ["alarm", "world_clock", "stopwatch", "timer", "assistant"]:
            wrapper = tk.Frame(self.main_content, bg=BG, bd=1, relief="solid", highlightthickness=0)
            wrapper.configure(highlightbackground=LINE, highlightcolor=LINE)
            self.desktop_wrappers[key] = wrapper
            
            if key == "alarm":
                self.desktop_pages[key] = AlarmPage(wrapper, self)
            elif key == "world_clock":
                self.desktop_pages[key] = WorldClockPage(wrapper, self)
            elif key == "stopwatch":
                self.desktop_pages[key] = StopwatchPage(wrapper, self)
            elif key == "timer":
                self.desktop_pages[key] = TimerPage(wrapper, self)
            elif key == "assistant":
                self.desktop_pages[key] = AssistantPage(wrapper, self)
                
            self.desktop_pages[key].pack(fill="both", expand=True)

        # Start View Render
        self.apply_layout()

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
        self.after(150, self.start_alarm_monitor)
        self.after(100, self.save_state)

    def _setup_window(self):
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        # Responsive sizing
        if self.layout_mode == "phone":
            width = min(420, sw)
            height = min(820, sh)
        else:
            width = min(1180, sw)
            height = min(820, sh)
            
        x = max(0, (sw - width) // 2)
        y = max(0, (sh - height) // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def _setup_styles(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=BG_2, foreground=MUTED, padding=(12, 8), font=("Segoe UI", 9, "bold"), borderwidth=0)
        style.map("TNotebook.Tab", background=[("selected", CARD)], foreground=[("selected", ACCENT)])
        style.configure("TFrame", background=BG)
        style.configure("TScrollbar", background=LINE, troughcolor=BG, bordercolor=BG, arrowcolor=ACCENT)

    def _draw_header(self):
        for w in self.header_frame.winfo_children():
            w.destroy()
            
        # Left status logo
        tk.Label(self.header_frame, text="Clock Utility Suite", font=("Segoe UI", 12, "bold"), bg=BG_2, fg=TEXT).pack(side="left", padx=16, pady=10)
        
        # Center active alarms flag
        active_alarms = sum(1 for a in self.app_state.get("alarms", []) if a.get("active", True))
        status_text = f"● Alarms active: {active_alarms}" if active_alarms > 0 else "○ No alarms running"
        self.lbl_status = tk.Label(self.header_frame, text=status_text, font=("Segoe UI", 8, "bold"), bg=BG_2, fg=SUCCESS if active_alarms > 0 else MUTED)
        self.lbl_status.pack(side="left", padx=10)

        # Right layout switcher & settings toggles
        self.btn_layout = tk.Button(self.header_frame, text="💻 Switch to Grid" if self.layout_mode == "phone" else "📱 Switch to Phone", bg=ACCENT, fg="#1b1208", font=("Segoe UI", 9, "bold"), bd=0, padx=12, command=self.toggle_layout)
        self.btn_layout.pack(side="right", padx=12, pady=8)

        btn_set = tk.Button(self.header_frame, text="⚙ Settings", bg=BG, fg=TEXT, font=("Segoe UI", 9, "bold"), bd=0, padx=12, command=self.open_settings)
        btn_set.pack(side="right", padx=(0, 6), pady=8)

    def toggle_layout(self):
        self.layout_mode = "desktop" if self.layout_mode == "phone" else "phone"
        self._draw_header()
        
        # Resize window
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        width = min(420, sw) if self.layout_mode == "phone" else min(1180, sw)
        height = min(820, sh)
        x = max(0, (sw - width) // 2)
        y = max(0, (sh - height) // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
        
        self.apply_layout()

    def apply_layout(self):
        # Clear main content packs
        for w in self.main_content.winfo_children():
            w.pack_forget()
            w.grid_forget()

        if self.layout_mode == "phone":
            # PHONE VIEW: center phone frame mockup using canvas, and load subpages inside canvas window
            self.phone_canvas.pack(fill="both", expand=True)
            self._draw_phone_mockup()
        else:
            # DESKTOP GRID VIEW: all panels organized side-by-side inside main window
            self.main_content.columnconfigure(0, weight=1)
            self.main_content.columnconfigure(1, weight=1)
            self.main_content.columnconfigure(2, weight=1)
            self.main_content.rowconfigure(0, weight=1)
            self.main_content.rowconfigure(1, weight=1)

            # Re-pack and show all pages inside dashboard grids
            self._pack_grid_panel(self.desktop_pages["alarm"], 0, 0, rowspan=2)
            self._pack_grid_panel(self.desktop_pages["world_clock"], 1, 0)
            self._pack_grid_panel(self.desktop_pages["timer"], 1, 1)
            self._pack_grid_panel(self.desktop_pages["stopwatch"], 2, 0)
            self._pack_grid_panel(self.desktop_pages["assistant"], 2, 1)

            self.refresh_all_views()

    def _pack_grid_panel(self, frame, col, row, rowspan=1):
        wrapper = self.desktop_wrappers[ [k for k, v in self.desktop_pages.items() if v == frame][0] ]
        wrapper.grid(column=col, row=row, rowspan=rowspan, sticky="nsew", padx=6, pady=6)

    def _draw_phone_mockup(self, event=None):
        self.phone_canvas.delete("all")
        w, h = self.phone_canvas.winfo_width(), self.phone_canvas.winfo_height()
        if w < 10 or h < 10:
            w, h = 420, 820  # Fallback design sizes during init
        
        # Phone mockup offsets
        pw, ph = 360, 700
        px1 = (w - pw) // 2
        py1 = (h - ph) // 2
        px2 = px1 + pw
        py2 = py1 + ph
        
        # 1. Bezel Draw
        draw_rounded_rect(self.phone_canvas, px1, py1, px2, py2, 32, fill="#1c1815", outline=ACCENT, width=3)
        # Inner screen boundaries
        spx1, spy1 = px1 + 8, py1 + 8
        spx2, spy2 = px2 - 8, py2 - 8
        draw_rounded_rect(self.phone_canvas, spx1, spy1, spx2, spy2, 26, fill=BG, outline="")
        
        # Speaker Notch Draw
        notch_w, notch_h = 130, 20
        n_x1 = px1 + (pw - notch_w) // 2
        n_x2 = n_x1 + notch_w
        draw_rounded_rect(self.phone_canvas, n_x1, py1+6, n_x2, py1+notch_h+4, 10, fill="#1c1815", outline="")
        
        # 2. Status Bar Mockup Text/Icons
        self.phone_canvas.create_text(spx1+30, spy1+18, text=datetime.now().strftime("%I:%M"), fill=TEXT, font=("Segoe UI", 9, "bold"))
        self.phone_canvas.create_text(spx2-35, spy1+18, text="📶 🔋 98%", fill=TEXT, font=("Segoe UI", 9))
        
        # 3. Mount Notebook Frame inside inner screen using canvas create_window
        self.phone_canvas.create_window(px1 + pw // 2, py1 + 356, window=self.phone_notebook, width=pw-18, height=ph-40)
        self.refresh_all_views()

    def refresh_all_views(self):
        try:
            # Refresh phone pages
            self.phone_pages["alarm"].render_alarms()
            self.phone_pages["world_clock"].refresh_cities_list()
            self.phone_pages["stopwatch"].render_laps()
            
            # Refresh desktop pages
            self.desktop_pages["alarm"].render_alarms()
            self.desktop_pages["world_clock"].refresh_cities_list()
            self.desktop_pages["stopwatch"].render_laps()
        except Exception:
            pass

    def get_page(self, key):
        if self.layout_mode == "phone":
            return self.phone_pages[key]
        else:
            return self.desktop_pages[key]

    def save_state(self):
        try:
            with open(APP_DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(self.app_state, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def queue_save(self, delay=250):
        if self._save_job:
            try:
                self.after_cancel(self._save_job)
            except Exception:
                pass
        self._save_job = self.after(delay, self.save_state)

    def execute_action(self, act):
        # Central routing controller for chatbot AIML actions
        try:
            atype = act["type"]
            
            if atype == "set_alarm":
                time_val = act["time"]
                ampm = act["ampm"].lower()
                # Parse days or default to everyday
                self.app_state["alarms"].append({
                    "time": time_val,
                    "ampm": ampm,
                    "label": "Voice Alarm",
                    "days": [0, 1, 2, 3, 4, 5, 6],
                    "active": True,
                    "snooze": "5 min, 3 times",
                    "sound": True,
                    "vibration": True,
                })
                self.queue_save()
                self.refresh_all_views()
                return f"Alarm set at {time_val} {ampm.upper()}."
                
            elif atype == "delete_alarms":
                self.app_state["alarms"] = []
                self.queue_save()
                self.refresh_all_views()
                return "Cleared all alarms."
                
            elif atype == "show_tab":
                tab_name = act["tab"]
                tab_indices = {"alarm": 0, "world_clock": 1, "stopwatch": 2, "timer": 3, "assistant": 4}
                if self.layout_mode == "phone" and tab_name in tab_indices:
                    self.phone_notebook.select(tab_indices[tab_name])
                return f"Switched view to {tab_name} panel."
                
            elif atype == "add_city":
                city_name = act["city"].strip()
                res = lookup_city_offset(city_name)
                if res:
                    name, offset = res
                    self.app_state["cities"].append({
                        "name": name,
                        "offset_str": self.world_clock_page.format_offset(offset),
                        "hours_off": offset
                    })
                    self.queue_save()
                    self.refresh_all_views()
                    return f"Added tracked location: {name} ({offset:+g} hrs)."
                else:
                    # Fallback to default manual entry prompt
                    self.app_state["cities"].append({
                        "name": city_name,
                        "offset_str": "0 hrs ahead",
                        "hours_off": 0.0
                    })
                    self.queue_save()
                    self.refresh_all_views()
                    return f"Added untracked city: {city_name} (0.0 hrs offset)."
                    
            elif atype == "get_world_time":
                city_name = act["city"].strip().lower()
                now = datetime.now()
                # Check database
                for city in self.app_state.get("cities", []):
                    if city["name"].lower() == city_name:
                        city_time = now + timedelta(hours=city["hours_off"])
                        return f"Local time in {city['name']} is {city_time.strftime('%I:%M %p')} ({city['offset_str']})."
                # Check default catalog
                for name, utc_off in CITY_UTC_OFFSETS.items():
                    if name.lower() == city_name:
                        local_offset_seconds = -time.timezone if (time.localtime().tm_isdst == 0) else -time.altzone
                        local_offset_hours = local_offset_seconds / 3600.0
                        offset = utc_off - local_offset_hours
                        city_time = now + timedelta(hours=offset)
                        return f"Calculated time in {name} is {city_time.strftime('%I:%M %p')}."
                return f"Could not find coordinates for {act['city']}."
                
            elif atype == "stopwatch":
                cmd = act["cmd"]
                page = self.stopwatch_page
                if cmd == "start":
                    if not page.running:
                        page.do_right()
                    return "Started stopwatch ticking."
                elif cmd == "stop":
                    if page.running:
                        page.do_right()
                    return "Stopped stopwatch."
                elif cmd == "lap":
                    if page.running:
                        page.do_left()
                        return f"Recorded Lap {len(page.laps)}: {page.laps[-1]}."
                    return "Stopwatch must be running to record laps."
                elif cmd == "reset":
                    if page.running:
                        page.do_right()
                    page.do_left()
                    return "Stopwatch values reset to zero."
                    
            elif atype == "start_timer":
                duration = int(act["duration"])
                unit = act["unit"]
                secs = duration * 60 if unit == "minutes" else duration
                self.timer_page.total_seconds = secs
                self.timer_page.remaining_seconds = secs
                self.timer_page.show_countdown_view()
                return f"Countdown timer started for {duration} {unit}."
                
            elif atype == "stop_timer":
                self.timer_page.cancel_timer()
                return "Cancelled countdown timer."
                
            elif atype == "toggle_layout":
                self.toggle_layout()
                return "Toggled view."
                
            elif atype == "reset_data":
                self.app_state = default_state()
                self.queue_save()
                self.refresh_all_views()
                return "Reset all configurations to default state."
        except Exception as e:
            return f"Action execution error: {e}"
        return None

    def play_sound(self, kind="alarm"):
        settings = self.app_state.get("settings", {})
        if not settings.get("system_sound", True):
            return

        sound_name = settings.get("alarm_sound", "Soft Bell")

        def worker():
            try:
                import winsound
                presets = {
                    "Soft Bell": [(880, 150), (988, 150), (1046, 200)],
                    "Chime": [(784, 120), (988, 120), (1175, 160)],
                    "Double Beep": [(920, 140), (0, 100), (920, 140)],
                    "Classic Ring": [(659, 150), (784, 150), (659, 150), (784, 200)],
                }
                sequence = presets.get(sound_name, presets["Soft Bell"])
                if kind == "timer":
                    sequence = sequence + [(0, 100), (784, 150), (988, 150)]

                for freq, duration in sequence:
                    if freq > 0:
                        winsound.Beep(freq, duration)
                    else:
                        time.sleep(duration / 1000.0)
            except Exception:
                try:
                    self.bell()
                except Exception:
                    pass

        threading.Thread(target=worker, daemon=True).start()

    def open_settings(self):
        win = tk.Toplevel(self)
        win.title("Unified Settings Dashboard")
        win.geometry("400x560")
        win.configure(bg=BG)
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()
        gentle_open(win, "400x560")

        shell = tk.Frame(win, bg=BG)
        shell.pack(fill="both", expand=True, padx=16, pady=16)

        tk.Label(shell, text="Unified Settings", font=("Segoe UI", 18, "bold"), bg=BG, fg=TEXT).pack(anchor="w")
        tk.Label(shell, text="Global configurations control center", font=("Segoe UI", 9), bg=BG, fg=MUTED).pack(anchor="w", pady=(2, 10))

        card = tk.Frame(shell, bg=CARD, highlightthickness=1, highlightbackground=LINE)
        card.pack(fill="both", expand=True)

        settings = self.app_state.setdefault("settings", {})
        username_var = tk.StringVar(value=settings.get("username", "User_2050"))
        timefmt_var = tk.StringVar(value=settings.get("time_format", "12h"))
        sound_var = tk.StringVar(value=settings.get("alarm_sound", "Soft Bell"))
        vib_var = tk.BooleanVar(value=settings.get("alarm_vibration", True))
        system_sound_var = tk.BooleanVar(value=settings.get("system_sound", True))

        rows = tk.Frame(card, bg=CARD)
        rows.pack(fill="both", expand=True, padx=14, pady=10)

        def section_title(text):
            tk.Label(rows, text=text, bg=CARD, fg=MUTED, font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(8, 2))

        section_title("Profile Name")
        tk.Entry(rows, textvariable=username_var, bg=BG_2, fg=TEXT, insertbackground=TEXT, relief="flat", font=("Segoe UI", 10)).pack(fill="x", ipady=6)

        section_title("Display Format")
        fmt_row = tk.Frame(rows, bg=CARD)
        fmt_row.pack(fill="x")
        tk.Radiobutton(fmt_row, text="12-Hour Format", variable=timefmt_var, value="12h", bg=CARD, fg=TEXT, activebackground=CARD, selectcolor=CARD_2, bd=0).pack(side="left", padx=(0, 10))
        tk.Radiobutton(fmt_row, text="24-Hour Format", variable=timefmt_var, value="24h", bg=CARD, fg=TEXT, activebackground=CARD, selectcolor=CARD_2, bd=0).pack(side="left")

        section_title("Synthesized Alert Ring")
        sound_combo = ttk.Combobox(rows, values=["Soft Bell", "Chime", "Double Beep", "Classic Ring"], textvariable=sound_var, state="readonly", font=("Segoe UI", 9))
        sound_combo.pack(fill="x")

        section_title("Feedback Settings")
        tk.Checkbutton(rows, text="Enable haptic vibration simulator", variable=vib_var, bg=CARD, fg=TEXT, selectcolor=CARD_2, bd=0).pack(anchor="w")
        tk.Checkbutton(rows, text="Synthesize system audios on alarm/timer", variable=system_sound_var, bg=CARD, fg=TEXT, selectcolor=CARD_2, bd=0).pack(anchor="w", pady=(4, 0))

        def save_settings():
            settings["username"] = username_var.get().strip() or "User_2050"
            settings["time_format"] = timefmt_var.get()
            settings["alarm_sound"] = sound_var.get()
            settings["alarm_vibration"] = vib_var.get()
            settings["system_sound"] = system_sound_var.get()
            self.queue_save()
            self.refresh_all_views()
            win.destroy()

        def reset_all():
            if messagebox.askyesno("Confirm Reset", "Reset all alarms, locations, and settings?"):
                self.app_state = default_state()
                self.queue_save()
                self.refresh_all_views()
                win.destroy()

        btn_row = tk.Frame(rows, bg=CARD)
        btn_row.pack(fill="x", pady=14)
        tk.Button(btn_row, text="Save Settings", bg=ACCENT, fg="#1b1208", bd=0, font=("Segoe UI", 9, "bold"), padx=12, pady=6, command=save_settings).pack(side="left")
        tk.Button(btn_row, text="Reset Storage Data", bg=DANGER, fg="white", bd=0, font=("Segoe UI", 9, "bold"), padx=12, pady=6, command=reset_all).pack(side="right")

    def start_alarm_monitor(self):
        self._alarm_check_job = self.after(1000, self._check_alarm_cycle)

    def _check_alarm_cycle(self):
        try:
            now = datetime.now()
            minute_key = now.strftime("%Y-%m-%d %H:%M")
            weekday = now.weekday()
            day_idx = (weekday + 1) % 7 # Sunday = 0
            
            # Read state alarms
            alarms = self.app_state.get("alarms", [])
            for idx, alarm in enumerate(alarms):
                if not alarm.get("active", True):
                    continue
                if alarm.get("days") and day_idx not in alarm["days"]:
                    continue
                
                # Check matching time
                try:
                    alarm_h, alarm_m = map(int, alarm["time"].split(":"))
                    ampm = alarm["ampm"].lower()
                    if ampm == "pm" and alarm_h < 12:
                        alarm_h += 12
                    elif ampm == "am" and alarm_h == 12:
                        alarm_h = 0
                        
                    if now.hour == alarm_h and now.minute == alarm_m and now.second == 0:
                        self.play_sound("alarm")
                        messagebox.showinfo("Alarm Triggered", f"Alarm ringing: {alarm.get('label','Alarm')} is active!")
                except Exception:
                    pass
        finally:
            self._alarm_check_job = self.after(1000, self._check_alarm_cycle)

    def on_close(self):
        self.save_state()
        self.destroy()


def lookup_city_offset(city_name):
    # Case-insensitive lookup
    for name, utc_off in CITY_UTC_OFFSETS.items():
        if name.lower() == city_name.lower():
            local_offset_seconds = -time.timezone if (time.localtime().tm_isdst == 0) else -time.altzone
            local_offset_hours = local_offset_seconds / 3600.0
            hours_off = utc_off - local_offset_hours
            return name, hours_off
    return None


if __name__ == "__main__":
    app = ClockApp()
    app.mainloop()

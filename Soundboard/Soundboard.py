import tkinter as tk
from tkinter import filedialog, colorchooser
import os
import json
import pygame

# Initialize pygame mixer
pygame.mixer.init()

SETTINGS_FILE = "soundboard_settings.json"

class RetroSoundboard:
    def __init__(self, root):
        self.root = root
        self.root.title("PLAYER - Retro Soundboard")
        self.root.geometry("800x560")
        
        # ----------------------------------------------------
        # Load Settings or Fallback to Defaults
        # ----------------------------------------------------
        self.load_settings()
        self.root.configure(bg=self.theme_color)

        # Runtime variables
        self.sound_buttons = []
        self.current_file_path = ""
        self.current_track_title = ""
        self.is_paused = False
        self.current_time_offset = 0.0
        self.track_duration = 0.0

        # ----------------------------------------------------
        # 1. TOP PANEL (Search, Loop, Theme & Pin Management)
        # ----------------------------------------------------
        self.top_frame = tk.Frame(root, bg=self.theme_color, bd=2, relief="groove")
        self.top_frame.pack(side="top", fill="x", padx=5, pady=(5, 0))
        
        self.search_label = tk.Label(self.top_frame, text="Search:", bg=self.theme_color, font=("MS Sans Serif", 9))
        self.search_label.pack(side="left", padx=5, pady=5)
        
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self.filter_sounds)
        self.search_entry = tk.Entry(self.top_frame, textvariable=self.search_var, bd=2, relief="sunken", width=30)
        self.search_entry.pack(side="left", padx=5, pady=5)

        # Loop Checkbox
        self.loop_var = tk.BooleanVar(value=self.is_looping_enabled)
        self.chk_loop = tk.Checkbutton(self.top_frame, text="Loop Track", variable=self.loop_var, bg=self.theme_color, font=("MS Sans Serif", 9), command=self.save_settings)
        self.chk_loop.pack(side="left", padx=15)

        # Help notice for pinning sounds
        self.tip_label = tk.Label(self.top_frame, text="[Tip: Right-click pad to Pin/Unpin]", bg=self.theme_color, fg="#555555", font=("MS Sans Serif", 8, "italic"))
        self.tip_label.pack(side="left", padx=5)

        # Settings Configuration Button
        self.btn_theme = tk.Button(self.top_frame, text="⚙ Settings", font=("MS Sans Serif", 9), command=self.open_settings, relief="raised", bd=2)
        self.btn_theme.pack(side="right", padx=5, pady=5)

        # ----------------------------------------------------
        # 2. LEFT SIDEBAR (Controls & Volume)
        # ----------------------------------------------------
        self.left_frame = tk.Frame(root, bg=self.theme_color, bd=2, relief="groove")
        self.left_frame.pack(side="left", fill="y", padx=5, pady=5)
        
        self.sidebar_title = tk.Label(self.left_frame, text="CONTROLS", bg=self.title_blue, fg="white", font=("Arial", 9, "bold"), anchor="w", padx=5)
        self.sidebar_title.pack(fill="x", pady=(0, 10))

        self.btn_load = tk.Button(self.left_frame, text="Load Folder", font=("MS Sans Serif", 9), command=self.load_folder, relief="raised", bd=2)
        self.btn_load.pack(fill="x", padx=10, pady=5)

        self.vol_label = tk.Label(self.left_frame, text="VOLUME", bg=self.theme_color, font=("MS Sans Serif", 9, "bold"))
        self.vol_label.pack(pady=(15, 0))
        
        self.vol_slider = tk.Scale(self.left_frame, from_=100, to=0, orient="vertical", length=150, bg=self.theme_color, highlightthickness=0, command=self.set_volume)
        self.vol_slider.set(70)
        self.vol_slider.pack(pady=5)

        # ----------------------------------------------------
        # 3. RIGHT GRID (Audio Pads Container)
        # ----------------------------------------------------
        self.right_container = tk.Frame(root, bg=self.theme_color)
        self.right_container.pack(side="right", fill="both", expand=True)

        self.main_window_frame = tk.Frame(self.right_container, bg=self.theme_color, bd=2, relief="groove")
        self.main_window_frame.pack(side="top", fill="both", expand=True, padx=5, pady=5)
        
        self.grid_title = tk.Label(self.main_window_frame, text="AUDIO PADS", bg=self.title_blue, fg="white", font=("Arial", 9, "bold"), anchor="w", padx=5)
        self.grid_title.pack(fill="x")

        self.canvas = tk.Canvas(self.main_window_frame, bg="#ffffff", bd=2, relief="sunken", highlightthickness=0)
        self.scrollbar = tk.Scrollbar(self.main_window_frame, orient="vertical", command=self.canvas.yview)
        self.grid_frame = tk.Frame(self.canvas, bg="#ffffff")

        self.grid_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.grid_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True, padx=2, pady=2)
        self.scrollbar.pack(side="right", fill="y")
        # ----------------------------------------------------
        # 4. BOTTOM TRACK STATUS & TIMELINE BAR
        # ----------------------------------------------------
        self.playback_frame = tk.Frame(self.right_container, bg=self.theme_color, bd=2, relief="groove")
        self.playback_frame.pack(side="bottom", fill="x", padx=5, pady=(0, 5))
        
        # Audio timeline bar line
        self.timeline_canvas = tk.Canvas(self.playback_frame, height=8, bg="#ffffff", bd=1, relief="sunken", highlightthickness=0)
        self.timeline_canvas.pack(fill="x", padx=10, pady=(5, 5))
        self.progress_bar = self.timeline_canvas.create_rectangle(0, 0, 0, 8, fill=self.title_blue, width=0)

        # Control Row Layout
        self.btn_rewind = tk.Button(self.playback_frame, text="⏪ -10s", font=("MS Sans Serif", 9, "bold"), width=10, command=self.rewind_10s, relief="raised", bd=2)
        self.btn_rewind.pack(side="left", padx=5, pady=5)
        
        self.btn_pause = tk.Button(self.playback_frame, text="⏸ Pause", font=("MS Sans Serif", 9, "bold"), width=12, command=self.toggle_pause, relief="raised", bd=2)
        self.btn_pause.pack(side="left", padx=5, pady=5)
        
        self.btn_forward = tk.Button(self.playback_frame, text="⏩ +10s", font=("MS Sans Serif", 9, "bold"), width=10, command=self.forward_10s, relief="raised", bd=2)
        self.btn_forward.pack(side="left", padx=5, pady=5)

        self.status_label = tk.Label(self.playback_frame, text="No track playing", bg=self.theme_color, font=("MS Sans Serif", 9, "italic"), fg="#555555", anchor="w")
        self.status_label.pack(side="right", fill="x", expand=True, padx=10)

        # Auto-Load if folder configuration was previously saved
        if self.sound_folder and os.path.exists(self.sound_folder):
            self.refresh_sound_grid()

        # Fire continuous loop checking audio progression states
        self.update_playback_loop()

    # ----------------------------------------------------
    # Configuration Management Engines (JSON)
    # ----------------------------------------------------
    def load_settings(self):
        try:
            with open(SETTINGS_FILE, "r") as f:
                data = json.load(f)
                self.sound_folder = data.get("sound_folder", "")
                self.theme_color = data.get("theme_color", "#d4d0c8")
                self.title_blue = data.get("title_blue", "#000080")
                self.pinned_sounds = data.get("pinned_sounds", [])
                self.is_looping_enabled = data.get("loop", False)
        except Exception:
            self.sound_folder = ""
            self.theme_color = "#d4d0c8"
            self.title_blue = "#000080"
            self.pinned_sounds = []
            self.is_looping_enabled = False

    def save_settings(self):
        data = {
            "sound_folder": self.sound_folder,
            "theme_color": self.theme_color,
            "title_blue": self.title_blue,
            "pinned_sounds": self.pinned_sounds,
            "loop": self.loop_var.get()
        }
        with open(SETTINGS_FILE, "w") as f:
            json.dump(data, f)

    def open_settings(self):
        win = tk.Toplevel(self.root)
        win.title("Setup Colors")
        win.geometry("260x150")
        win.configure(bg=self.theme_color)
        win.transient(self.root)
        win.grab_set()

        def pick_bg():
            color = colorchooser.askcolor(initialcolor=self.theme_color)
            if color[1]:
                self.theme_color = color[1]
                self.apply_theme_updates()

        def pick_bars():
            color = colorchooser.askcolor(initialcolor=self.title_blue)
            if color[1]:
                self.title_blue = color[1]
                self.apply_theme_updates()

        tk.Button(win, text="Change Window Background", command=pick_bg, relief="raised", bd=2).pack(fill="x", padx=20, pady=10)
        tk.Button(win, text="Change Title Bar Color", command=pick_bars, relief="raised", bd=2).pack(fill="x", padx=20, pady=10)
        tk.Button(win, text="Close & Save Layout", command=win.destroy, relief="raised", bd=2).pack(pady=10)

    def apply_theme_updates(self):
        self.root.configure(bg=self.theme_color)
        self.top_frame.configure(bg=self.theme_color)
        self.chk_loop.configure(bg=self.theme_color)
        self.tip_label.configure(bg=self.theme_color)
        self.left_frame.configure(bg=self.theme_color)
        self.vol_label.configure(bg=self.theme_color)
        self.vol_slider.configure(bg=self.theme_color)
        self.right_container.configure(bg=self.theme_color)
        self.main_window_frame.configure(bg=self.theme_color)
        self.playback_frame.configure(bg=self.theme_color)
        self.status_label.configure(bg=self.theme_color)
        self.sidebar_title.configure(bg=self.title_blue)
        self.grid_title.configure(bg=self.title_blue)
        self.timeline_canvas.itemconfig(self.progress_bar, fill=self.title_blue)
        self.save_settings()

    # ----------------------------------------------------
    # Pad Matrix Logic & Pin Handling
    # ----------------------------------------------------
    def load_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.sound_folder = folder
            self.save_settings()
            self.refresh_sound_grid()

    def toggle_pin(self, file_name):
        if file_name in self.pinned_sounds:
            self.pinned_sounds.remove(file_name)
        else:
            self.pinned_sounds.append(file_name)
        self.save_settings()
        self.refresh_sound_grid()

    def refresh_sound_grid(self):
        for btn, _ in self.sound_buttons:
            btn.destroy()
        self.sound_buttons.clear()

        if not self.sound_folder:
            return

        all_files = [f for f in os.listdir(self.sound_folder) if f.lower().endswith(('.mp3', '.wav', '.ogg'))]
        pinned = [f for f in all_files if f in self.pinned_sounds]
        unpinned = [f for f in all_files if f not in self.pinned_sounds]
        files = pinned + unpinned

        row, col = 0, 0
        max_columns = 4

        for file_name in files:
            clean_name = os.path.splitext(file_name)[0]
            file_path = os.path.join(self.sound_folder, file_name)
            is_pinned = file_name in self.pinned_sounds

            display_text = f"📌\n{clean_name}" if is_pinned else clean_name
            bg_pad = "#e1dcd4" if is_pinned else "#d4d0c8"

            btn = tk.Button(
                self.grid_frame, 
                text=display_text, 
                font=("MS Sans Serif", 8, "bold" if is_pinned else "normal"),
                width=14, 
                height=4, 
                bg=bg_pad,
                relief="raised",
                bd=3,
                wraplength=90,
                command=lambda p=file_path, n=clean_name: self.play_sound(p, n)
            )
            btn.bind("<Button-3>", lambda e, fn=file_name: self.toggle_pin(fn))
            btn.grid(row=row, column=col, padx=8, pady=8)
            self.sound_buttons.append((btn, clean_name.lower()))
            
            col += 1
            if col >= max_columns:
                col = 0
                row += 1

    # ----------------------------------------------------
    # Audio Playback Engine Controls & Loop Trackers
    # ----------------------------------------------------
    def play_sound(self, path, track_name):
        try:
            self.current_file_path = path
            self.current_track_title = track_name
            self.current_time_offset = 0.0
            self.is_paused = False
            self.btn_pause.configure(text="⏸ Pause")
            
            sound_obj = pygame.mixer.Sound(path)
            self.track_duration = sound_obj.get_length()

            pygame.mixer.music.load(path)
            pygame.mixer.music.play()
            
            self.status_label.configure(text=f"Playing: {track_name}", fg="#000000")
        except Exception as e:
            print(f"Playback error: {e}")

    def toggle_pause(self):
        if not self.current_file_path:
            return
        if self.is_paused:
            pygame.mixer.music.unpause()
            self.is_paused = False
            self.btn_pause.configure(text="⏸ Pause")
        else:
            pygame.mixer.music.pause()
            self.is_paused = True
            self.btn_pause.configure(text="▶ Resume")

    def forward_10s(self):
        if not self.current_file_path:
            return
        current_pos = self.current_time_offset + (pygame.mixer.music.get_pos() / 1000.0)
        new_pos = min(self.track_duration, current_pos + 10.0)
        self.current_time_offset = new_pos
        pygame.mixer.music.play(start=new_pos)
        if self.is_paused: pygame.mixer.music.pause()

    def rewind_10s(self):
        if not self.current_file_path:
            return
        current_pos = self.current_time_offset + (pygame.mixer.music.get_pos() / 1000.0)
        new_pos = max(0.0, current_pos - 10.0)
        self.current_time_offset = new_pos
        pygame.mixer.music.play(start=new_pos)
        if self.is_paused: pygame.mixer.music.pause()

    def set_volume(self, val):
        pygame.mixer.music.set_volume(float(val) / 100)

    def update_playback_loop(self):
        if self.current_file_path and pygame.mixer.music.get_busy():
            current_pos = self.current_time_offset + (pygame.mixer.music.get_pos() / 1000.0)
            canvas_width = self.timeline_canvas.winfo_width()
            if self.track_duration > 0:
                fill_ratio = current_pos / self.track_duration
                self.timeline_canvas.coords(self.progress_bar, 0, 0, int(canvas_width * fill_ratio), 8)
        
        elif self.current_file_path and not self.is_paused:
            if self.loop_var.get():
                self.play_sound(self.current_file_path, self.current_track_title)
            else:
                self.timeline_canvas.coords(self.progress_bar, 0, 0, 0, 8)
                self.status_label.configure(text="Track Finished", fg="#555555")

        # FIX: This line must be out of the else block so it runs continuously
        self.root.after(200, self.update_playback_loop)

    def filter_sounds(self, *args):
        query = self.search_var.get().lower()
        row, col = 0, 0
        max_columns = 4
        for btn, name in self.sound_buttons:
            if query in name:
                btn.grid(row=row, column=col, padx=8, pady=8)
                col += 1
                if col >= max_columns:
                    col = 0
                    row += 1
            else:
                btn.grid_forget()

if __name__ == "__main__":
    root = tk.Tk()
    app = RetroSoundboard(root)
    root.mainloop()

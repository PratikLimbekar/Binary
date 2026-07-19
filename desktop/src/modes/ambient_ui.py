import tkinter as tk
from tkinter import ttk

class AmbientUI:
    def __init__(self, parent, audio_service):
        self.parent = parent
        self.audio_service = audio_service
        self.setup_ui()

    def setup_ui(self):
        self.main_frame = tk.Frame(self.parent, bg="#36454F")
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        title = tk.Label(self.main_frame, text="AMBIENT SOUNDS", font=("Segoe UI", 10, "bold"), bg="#36454F", fg="#7692FF")
        title.pack(pady=5)

        # Sounds Grid
        self.sounds_frame = tk.Frame(self.main_frame, bg="#36454F")
        self.sounds_frame.pack(fill="x")

        self.add_sound_control("Rain", "rain")
        self.add_sound_control("Cafe", "cafe")
        self.add_sound_control("Storm", "storm")
        
        self.exit_btn = tk.Button(
            self.main_frame, text="Stop All", 
            command=self.audio_service.stop_all,
            bg="#B22222", fg="white"
        )
        self.exit_btn.pack(pady=10)

    def add_sound_control(self, display_name, file_key):
        frame = tk.Frame(self.sounds_frame, bg="#36454F")
        frame.pack(fill="x", pady=2)

        lbl = tk.Label(frame, text=display_name, width=10, anchor="w", bg="#36454F", fg="white")
        lbl.pack(side="left")

        # Toggle Button
        btn = tk.Button(
            frame, text="Play", 
            command=lambda: self.toggle_sound(file_key, btn),
            bg="#353935", fg="white", width=6
        )
        btn.pack(side="left", padx=5)

        # Volume Slider
        vol = tk.Scale(
            frame, from_=0, to=100, orient="horizontal", 
            command=lambda v: self.audio_service.set_volume(file_key, float(v)/100),
            bg="#36454F", fg="white", highlightthickness=0, length=80
        )
        vol.set(50)
        vol.pack(side="left")

    def toggle_sound(self, key, btn):
        if key in self.audio_service.active_channels:
            self.audio_service.stop_ambient(key)
            btn.config(text="Play", bg="#353935")
        else:
            self.audio_service.play_ambient(key)
            btn.config(text="Stop", bg="#7692FF")

# No global instance here, instantiated by the Mode Manager/Service

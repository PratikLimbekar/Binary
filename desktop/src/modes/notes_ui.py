import tkinter as tk
from tkinter import ttk
import threading
import time
import os
from datetime import datetime

class NotesUI:
    def __init__(self, parent, initial_text=""):
        self.parent = parent
        self.initial_text = initial_text
        self._running = True
        self._last_saved_content = initial_text
        self._setup_ui()
        
        # Start autosave thread
        threading.Thread(target=self._autosave_loop, daemon=True).start()

    def _setup_ui(self):
        self.parent.config(bg="#36454F")
        
        # Header
        header = tk.Frame(self.parent, bg="#36454F")
        header.pack(fill="x", padx=10, pady=(10, 5))
        
        tk.Label(header, text="📝 QUICK NOTE", font=("Segoe UI", 10, "bold"), 
                 bg="#36454F", fg="#FEFCFB").pack(side="left")
        
        # Close button
        close_btn = tk.Button(header, text="✕", command=self._close, 
                              bg="#36454F", fg="#FEFCFB", relief="flat", font=("Segoe UI", 10))
        close_btn.pack(side="right")

        # Save status
        self.status_label = tk.Label(self.parent, text="Draft", font=("Segoe UI", 8), 
                                     bg="#36454F", fg="#90A4AE")
        self.status_label.pack(anchor="e", padx=10)

        # Text Area
        self.text_area = tk.Text(self.parent, font=("Segoe UI", 11), bg="#2C3840", fg="#FEFCFB",
                                 insertbackground="white", relief="flat", padx=10, pady=10)
        self.text_area.pack(fill="both", expand=True, padx=10, pady=5)
        self.text_area.insert("1.0", self.initial_text)

        # Controls
        controls = tk.Frame(self.parent, bg="#36454F")
        controls.pack(fill="x", padx=10, pady=10)
        
        save_btn = tk.Button(controls, text="Save Now", command=self._manual_save,
                             bg="#4CAF50", fg="black", relief="flat", padx=10, pady=5,
                             font=("Segoe UI", 9, "bold"))
        save_btn.pack(side="left")

    def _manual_save(self):
        self._save_to_file()
        self.status_label.config(text="Saved manually", fg="#4CAF50")

    def _save_to_file(self):
        content = self.text_area.get("1.0", tk.END).strip()
        if not content:
            return
        
        from src.modules.note_manager import save_note
        save_note(content)
        self._last_saved_content = content

    def _autosave_loop(self):
        while self._running:
            time.sleep(2)
            if not self._running:
                break
            
            try:
                current_content = self.text_area.get("1.0", tk.END).strip()
                if current_content != self._last_saved_content and current_content:
                    self._save_to_file()
                    def _update_status():
                        self.status_label.config(text=f"Autosaved at {datetime.now().strftime('%H:%M:%S')}", fg="#90A4AE")
                    self.parent.after(0, _update_status)
            except:
                pass

    def _close(self):
        self._running = False
        from src.core.event_bus import bus
        bus.publish("ui.remove_tab", "Note")

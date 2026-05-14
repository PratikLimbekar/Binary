import json
import os
import subprocess
import webbrowser
import time
import threading
from src.core.event_bus import bus

_BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

class WorkspaceService:
    def __init__(self, config_path=None):
        self.config_path = config_path or os.path.join(_BASE_DIR, 'data', 'workspaces.json')
        self.active_ui_label = None
        self.active_ui_progress = None
        self.active_ui_step = None

    def _load_config(self):
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                return json.load(f)
        return {}

    def launch_workspace(self, workspace_name):
        config = self._load_config()
        if workspace_name not in config:
            # Try case-insensitive partial match
            for key in config:
                if workspace_name.lower() in key.lower():
                    workspace_name = key
                    break
            else:
                available = ', '.join(config.keys())
                return f"Workspace '{workspace_name}' not found. Available: {available}"

        steps = config[workspace_name].get("steps", [])

        def execute():
            import tkinter as tk
            from tkinter import ttk

            def create_progress_ui(parent):
                parent.config(bg="#36454F")
                lbl = tk.Label(parent, text=f"Launching {workspace_name}…",
                               bg="#36454F", fg="#FEFCFB", font=("Segoe UI", 10, "bold"))
                lbl.pack(pady=(15, 5))
                prog = ttk.Progressbar(parent, length=220, mode='determinate')
                prog.pack(pady=5)
                step_lbl = tk.Label(parent, text="Preparing…", bg="#36454F",
                                    fg="#B0BEC5", font=("Segoe UI", 8))
                step_lbl.pack()
                self.active_ui_label = lbl
                self.active_ui_progress = prog
                self.active_ui_step = step_lbl

            bus.publish("ui.add_tab", "Workspace", create_progress_ui)
            time.sleep(0.3)  # Let UI build

            for i, step in enumerate(steps):
                action = step.get("action")
                target = step.get("target", "")

                # Capture i/action/target by value to avoid closure bug
                def update_ui(idx=i, act=action, tgt=target):
                    if self.active_ui_label:
                        self.active_ui_label.config(text=f"Step {idx+1}/{len(steps)}: {act}")
                    if self.active_ui_progress:
                        self.active_ui_progress['value'] = ((idx + 1) / len(steps)) * 100
                    if self.active_ui_step:
                        self.active_ui_step.config(text=tgt)

                bus.publish("ui.execute", update_ui)

                try:
                    if action == "launch_app":
                        subprocess.Popen(target, shell=True)
                    elif action == "open_url":
                        webbrowser.open(target)
                    elif action == "run_script":
                        subprocess.Popen(["python", target], shell=True)
                    elif action == "play_audio":
                        from src.services.audio_service import audio_service
                        audio_service.play_ambient(target)
                    elif action == "delay":
                        time.sleep(step.get("seconds", 1))
                except Exception as e:
                    print(f"[Workspace] Error in step {i+1} ({action}): {e}")

            time.sleep(1.5)
            bus.publish("ui.remove_tab", "Workspace")

        threading.Thread(target=execute, daemon=True).start()
        return f"Starting workspace: {workspace_name}"

# Global instance
workspace_service = WorkspaceService()

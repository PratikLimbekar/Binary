import threading
import time
import json
import os
from datetime import datetime
from src.core.event_bus import bus

# Resolve project root so data paths work from any CWD
_BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

class TimerService:
    def __init__(self, data_path=None):
        self.data_path = data_path or os.path.join(_BASE_DIR, 'data', 'timers.json')
        self.active_timers = {}
        self.focus_tab_dismissed = False   # set to True by FocusModeUI on close
        self.sessions = []
        self._load_state()
        self.lock = threading.Lock()

    def _load_state(self):
        if os.path.exists(self.data_path):
            try:
                with open(self.data_path, 'r') as f:
                    data = json.load(f)
                    self.sessions = data.get("sessions", [])
            except:
                self.sessions = []

    def _save_state(self):
        os.makedirs(os.path.dirname(self.data_path), exist_ok=True)
        with open(self.data_path, 'w') as f:
            json.dump({"sessions": self.sessions}, f, indent=4)

    def start_timer(self, name, duration_minutes, callback=None):
        duration_seconds = duration_minutes * 60
        timer_id = f"{name}_{int(time.time())}"
        
        def run_timer():
            time.sleep(duration_seconds)
            with self.lock:
                if timer_id in self.active_timers:
                    del self.active_timers[timer_id]
                    self.sessions.append({
                        "name": name,
                        "duration": duration_minutes,
                        "timestamp": datetime.now().isoformat()
                    })
                    self._save_state()
                    if callback:
                        callback(name)

        thread = threading.Thread(target=run_timer, daemon=True)
        self.active_timers[timer_id] = {
            "name": name,
            "duration": duration_minutes,
            "end_time": time.time() + duration_seconds,
            "total_duration": duration_seconds,
            "thread": thread
        }
        
        # Start a monitoring thread for progress updates
        def monitor():
            from src.modes.focus_ui import FocusModeUI
            self.focus_tab_dismissed = False
            bus.publish("ui.add_tab", "Focus", lambda p: FocusModeUI(p, self))
            
            while timer_id in self.active_timers:
                rem = self.get_remaining_time(timer_id)
                percent = (rem / duration_seconds) * 100
                bus.publish("ui.update_progress", percent)
                time.sleep(1)
            
            # Timer finished — notify the UI but keep the tab open
            bus.publish("ui.update_progress", 0)
            bus.publish("ui.timer_complete", "Focus")

            # Wait until the user dismisses the tab via Continue / End
            while not self.focus_tab_dismissed:
                time.sleep(0.5)

            bus.publish("ui.remove_tab", "Focus")

        threading.Thread(target=monitor, daemon=True).start()
        thread.start()
        return timer_id

    def get_remaining_time(self, timer_id):
        if timer_id in self.active_timers:
            remaining = self.active_timers[timer_id]["end_time"] - time.time()
            return max(0, remaining)
        return 0

    def get_all_active(self):
        return [
            {"id": tid, "name": data["name"], "remaining": self.get_remaining_time(tid)}
            for tid, data in self.active_timers.items()
        ]

# Global instance
timer_service = TimerService()

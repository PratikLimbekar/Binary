import threading
import time
import json
import os
import re
from datetime import datetime, timedelta
from src.core.event_bus import bus

_BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

class ReminderService:
    def __init__(self, data_path=None):
        self.data_path = data_path or os.path.join(_BASE_DIR, 'data', 'reminders.json')
        self.reminders = []
        self._load_reminders()
        self.lock = threading.Lock()
        self._running = True
        threading.Thread(target=self._check_reminders, daemon=True).start()

    def _load_reminders(self):
        if os.path.exists(self.data_path):
            try:
                with open(self.data_path, 'r') as f:
                    self.reminders = json.load(f)
            except:
                self.reminders = []

    def _save_reminders(self):
        os.makedirs(os.path.dirname(self.data_path), exist_ok=True)
        with open(self.data_path, 'w') as f:
            json.dump(self.reminders, f, indent=4)

    def add_reminder(self, text, time_str):
        """
        time_str can be "in 5 minutes", "at 5:00 PM", or a specific datetime string.
        For simplicity, we'll handle basic relative and absolute times.
        """
        target_time = self._parse_time(time_str)
        if not target_time:
            return "Could not understand the time for the reminder."

        reminder = {
            "id": int(time.time()),
            "text": text,
            "time": target_time.isoformat(),
            "triggered": False
        }
        
        with self.lock:
            self.reminders.append(reminder)
            self._save_reminders()
        
        return f"Reminder set for {target_time.strftime('%I:%M %p')}."

    def _parse_time(self, time_str):
        time_str = time_str.lower().strip()
        now = datetime.now()

        # Relative: "in 5 minutes", "in 1 hour"
        rel_match = re.search(r'in (\d+) (minute|min|hour|hr|second|sec)', time_str)
        if rel_match:
            val = int(rel_match.group(1))
            unit = rel_match.group(2)
            if "min" in unit:
                return now + timedelta(minutes=val)
            if "hour" in unit or "hr" in unit:
                return now + timedelta(hours=val)
            if "sec" in unit:
                return now + timedelta(seconds=val)

        # Absolute: "at 5:00 pm", "at 17:00"
        abs_match = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)?', time_str)
        if abs_match:
            hr = int(abs_match.group(1))
            mn = int(abs_match.group(2) or 0)
            ampm = abs_match.group(3)
            
            if ampm == "pm" and hr < 12:
                hr += 12
            elif ampm == "am" and hr == 12:
                hr = 0
            
            target = now.replace(hour=hr, minute=mn, second=0, microsecond=0)
            if target < now:
                target += timedelta(days=1)
            return target

        return None

    def _check_reminders(self):
        while self._running:
            now = datetime.now()
            triggered_any = False
            
            with self.lock:
                for r in self.reminders:
                    if not r["triggered"]:
                        r_time = datetime.fromisoformat(r["time"])
                        if now >= r_time:
                            r["triggered"] = True
                            triggered_any = True
                            # Notify UI
                            bus.publish("ui.reminder_triggered", r["text"])
            
            if triggered_any:
                self._save_reminders()
            
            time.sleep(10) # Check every 10 seconds

# Global instance
reminder_service = ReminderService()

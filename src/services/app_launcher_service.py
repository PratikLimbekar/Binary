import os
import subprocess
from thefuzz import process

class AppLauncherService:
    def __init__(self):
        self.app_index = {}
        self.scan_paths = [
            os.path.join(os.environ["ProgramData"], "Microsoft", "Windows", "Start Menu", "Programs"),
            os.path.join(os.environ["AppData"], "Microsoft", "Windows", "Start Menu", "Programs")
        ]
        self.index_apps()

    def index_apps(self):
        self.app_index = {}
        for path in self.scan_paths:
            if not os.path.exists(path): continue
            for root, dirs, files in os.walk(path):
                for file in files:
                    if file.endswith(".lnk"):
                        name = file.replace(".lnk", "").lower()
                        self.app_index[name] = os.path.join(root, file)

    def launch_app(self, query):
        if not self.app_index:
            self.index_apps()
            
        matches = process.extractBests(query.lower(), self.app_index.keys(), score_cutoff=60, limit=1)
        if matches:
            best_match = matches[0][0]
            path = self.app_index[best_match]
            try:
                os.startfile(path)
                return f"Launching {best_match}..."
            except Exception as e:
                return f"Failed to launch {best_match}: {e}"
        return f"Could not find an app matching '{query}'."

# Global instance
app_launcher = AppLauncherService()

import json
import os
import time

_BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

class StickyNoteService:
    def __init__(self, data_path=None):
        self.data_path = data_path or os.path.join(_BASE_DIR, 'data', 'sticky_notes.json')
        self.notes = {}
        self.settings = {
            "tab_visible": True,
            "workspace_width": 250,
            "active_note_id": "default_note"
        }
        self.load_state()

    def load_state(self):
        """Load settings and notes from sticky_notes.json."""
        if os.path.exists(self.data_path):
            try:
                with open(self.data_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.notes = data.get("notes", {})
                    self.settings = data.get("settings", self.settings)
            except Exception as e:
                print(f"[StickyNoteService] Error loading state: {e}")
        
        # Ensure we always have at least one note
        if not self.notes or not isinstance(self.notes, dict):
            self.notes = {}
            self.create_default_note()
        else:
            # Validate that the stored active_note_id actually exists
            active_id = self.settings.get("active_note_id")
            if not active_id or active_id not in self.notes:
                # Fall back to the most recently accessed note
                fallback = max(self.notes.values(), key=lambda n: n.get("last_accessed", 0))
                self.settings["active_note_id"] = fallback["id"]
                self.save_state()

    def save_state(self):
        """Save settings and notes to sticky_notes.json."""
        os.makedirs(os.path.dirname(self.data_path), exist_ok=True)
        try:
            with open(self.data_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "settings": self.settings,
                    "notes": self.notes
                }, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"[StickyNoteService] Error saving state: {e}")

    def create_default_note(self):
        """Creates the initial default note."""
        note_id = "default_note"
        self.notes[note_id] = {
            "id": note_id,
            "title": "Welcome to Sticky Notes",
            "content": "Write your thoughts here!\n\nThis workspace is draggable on the right edge.\nIt autosaves as you type and persists across restarts.",
            "last_accessed": time.time()
        }
        self.settings["active_note_id"] = note_id
        self.save_state()

    def get_active_note(self):
        """Returns the note dictionary for the active note ID."""
        active_id = self.settings.get("active_note_id")
        if active_id in self.notes:
            # Update its last accessed time
            self.notes[active_id]["last_accessed"] = time.time()
            self.save_state()
            return self.notes[active_id]
        
        # Fallback to the most recently accessed note
        sorted_notes = self.get_all_notes_sorted()
        if sorted_notes:
            fallback_id = sorted_notes[0]["id"]
            self.settings["active_note_id"] = fallback_id
            self.notes[fallback_id]["last_accessed"] = time.time()
            self.save_state()
            return self.notes[fallback_id]
        
        # If absolutely no notes, create one
        return self.create_new_note("New Note", "")

    def save_note(self, note_id, title, content):
        """Saves a note and updates its last accessed time."""
        if not note_id:
            return
        
        # Clean title, fallback if empty
        title = title.strip()
        if not title:
            title = "Untitled Note"

        # Update note
        if note_id not in self.notes:
            self.notes[note_id] = {
                "id": note_id,
                "title": title,
                "content": content,
                "last_accessed": time.time()
            }
        else:
            self.notes[note_id]["title"] = title
            self.notes[note_id]["content"] = content
            self.notes[note_id]["last_accessed"] = time.time()
            
        self.save_state()

    def create_new_note(self, title="New Note", content=""):
        """Creates a new note and sets it as the active one."""
        note_id = f"note_{int(time.time() * 1000)}"
        self.notes[note_id] = {
            "id": note_id,
            "title": title,
            "content": content,
            "last_accessed": time.time()
        }
        self.settings["active_note_id"] = note_id
        self.save_state()
        return self.notes[note_id]

    def delete_note(self, note_id):
        """Deletes a note. Handles active note fallback."""
        if note_id in self.notes:
            del self.notes[note_id]
            
            # If the deleted note was active, choose a new active note
            if self.settings.get("active_note_id") == note_id:
                sorted_notes = self.get_all_notes_sorted()
                if sorted_notes:
                    self.settings["active_note_id"] = sorted_notes[0]["id"]
                else:
                    self.create_default_note()
            self.save_state()

    def get_all_notes_sorted(self):
        """Returns all notes sorted by last_accessed descending."""
        return sorted(self.notes.values(), key=lambda x: x.get("last_accessed", 0), reverse=True)

    def set_tab_visible(self, visible):
        """Updates the tab visibility setting."""
        self.settings["tab_visible"] = bool(visible)
        self.save_state()

    def is_tab_visible(self):
        """Returns the tab visibility setting."""
        return self.settings.get("tab_visible", True)

    def set_workspace_width(self, width):
        """Updates the workspace width setting."""
        self.settings["workspace_width"] = int(width)
        self.save_state()

    def get_workspace_width(self):
        """Returns the workspace width setting."""
        return self.settings.get("workspace_width", 250)

# Global singleton service
sticky_note_service = StickyNoteService()

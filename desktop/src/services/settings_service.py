import os
import json
import uuid
from datetime import datetime
from src.core.event_bus import bus
from src.services.db import db_service

# Path to the shared settings JSON (consumed by Dock, Mobile, etc.)
_SHARED_SETTINGS_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "shared", "protocols", "settings.json")
)

DEFAULT_SETTINGS = {
    "vision": {
        "snapshot_interval_ms": 500,
        "posture_detection_enabled": True,
        "presence_threshold": 12.0
    },
    "alarm": {
        "wake_time": "07:30",
        "dismiss_gesture": "show_toothbrush"
    },
    "voice": {
        "wake_word": "binary",
        "tts_enabled": True
    },
    "system": {
        "schema_version": 1
    }
}

class SettingsService:
    def __init__(self):
        self._cache = {}
        self._initialized = False
        self._shared_path = _SHARED_SETTINGS_PATH

    async def initialize(self):
        """Pre-populate default settings and cache values from SQLite."""
        if self._initialized:
            return
        
        # Load from SQLite; if empty, populate with defaults
        for section, values in DEFAULT_SETTINGS.items():
            db_val = await db_service.get_setting(section)
            if db_val is None:
                await db_service.set_setting(section, values)
                self._cache[section] = dict(values)
            else:
                self._cache[section] = db_val

        self._initialized = True
        print("[SettingsService] Settings loaded and cached.")
        
        # Mirror full state to shared JSON file on startup
        self._write_shared_settings_file()

    def _write_shared_settings_file(self):
        """Atomically write the in-memory settings cache to shared/protocols/settings.json."""
        try:
            os.makedirs(os.path.dirname(self._shared_path), exist_ok=True)
            tmp_path = self._shared_path + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, indent=2)
            os.replace(tmp_path, self._shared_path)
        except Exception as e:
            print(f"[SettingsService] Warning: Could not write shared settings file: {e}")

    def get_section(self, section: str):
        """Retrieve settings group (e.g. 'vision')."""
        return self._cache.get(section, DEFAULT_SETTINGS.get(section, {}))

    async def get(self, key_path: str, default=None):
        """
        Get setting value using dot-notation (e.g. 'vision.snapshot_interval_ms').
        """
        await self.initialize()
        parts = key_path.split('.')
        section = parts[0]
        
        if section not in self._cache:
            return default
            
        data = self._cache[section]
        for part in parts[1:]:
            if isinstance(data, dict) and part in data:
                data = data[part]
            else:
                return default
        return data

    async def set(self, key_path: str, value, source="local"):
        """
        Set setting value using dot-notation, save to database, and sync.
        """
        await self.initialize()
        parts = key_path.split('.')
        section = parts[0]
        
        if section not in self._cache:
            self._cache[section] = {}
            
        # Update nested dict cache
        data = self._cache[section]
        for part in parts[1:-1]:
            if part not in data or not isinstance(data[part], dict):
                data[part] = {}
            data = data[part]
            
        data[parts[-1]] = value
        
        # Save to DB
        await db_service.set_setting(section, self._cache[section])
        
        # Mirror to shared JSON file so Dock/Mobile can read it on next launch
        self._write_shared_settings_file()
        
        # Notify local system
        bus.publish(f"settings.changed.{section}", self._cache[section])
        print(f"[SettingsService] Setting updated: {key_path} = {value} ({source})")

        # Broadcast settings synchronization event to connected client nodes
        if source == "local":
            await self._broadcast_settings_sync(key_path, value)

    async def handle_sync_event(self, event: dict):
        """Process incoming settings synchronization event from a client."""
        payload = event.get("payload", {})
        key_path = payload.get("key_path")
        value = payload.get("value")
        
        if key_path and value is not None:
            # Update locally without re-broadcasting back to same channel (source="sync")
            await self.set(key_path, value, source="sync")
            # Log the change
            await db_service.log_system(
                "INFO", "SettingsService", 
                f"Setting synced from {event['sender_device_id']}: {key_path}={value}"
            )

    async def _broadcast_settings_sync(self, key_path: str, value):
        # Lazy import to avoid circular dependency
        from src.services.websocket_server import websocket_server
        
        sync_event = {
            "event_id": str(uuid.uuid4()),
            "event_type": "settings.sync.update",
            "version": "1.0.0",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "sender_device_id": "desktop_brain",
            "payload": {
                "key_path": key_path,
                "value": value
            }
        }
        await websocket_server.broadcast(sync_event)

# Singleton settings service instance
settings_service = SettingsService()

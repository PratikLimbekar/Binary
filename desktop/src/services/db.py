import os
import json
import logging
from datetime import datetime
import aiosqlite

class DatabaseService:
    def __init__(self, db_path=None):
        if db_path is None:
            # Set default database location inside desktop/data
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            data_dir = os.path.join(base_dir, "data")
            os.makedirs(data_dir, exist_ok=True)
            db_path = os.path.join(data_dir, "binary_brain.db")
        self.db_path = db_path
        self._initialized = False

    async def initialize(self):
        """Create tables and indices if they do not exist."""
        if self._initialized:
            return
        
        async with aiosqlite.connect(self.db_path) as db:
            # 1. Telemetry & Event logs
            await db.execute("""
                CREATE TABLE IF NOT EXISTS event_logs (
                    event_id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    version TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    sender_device_id TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    processed_at TEXT DEFAULT (datetime('now', 'utc'))
                )
            """)
            await db.execute("CREATE INDEX IF NOT EXISTS idx_event_logs_timestamp ON event_logs(timestamp)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_event_logs_type ON event_logs(event_type)")

            # 2. Paired devices
            await db.execute("""
                CREATE TABLE IF NOT EXISTS paired_devices (
                    device_id TEXT PRIMARY KEY,
                    device_name TEXT NOT NULL,
                    device_type TEXT NOT NULL CHECK(device_type IN ('desktop', 'dock', 'mobile')),
                    public_key TEXT NOT NULL,
                    paired_at TEXT DEFAULT (datetime('now', 'utc')),
                    last_seen_at TEXT
                )
            """)

            # 3. Settings table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    settings_key TEXT PRIMARY KEY,
                    settings_value TEXT NOT NULL,
                    updated_at TEXT DEFAULT (datetime('now', 'utc'))
                )
            """)

            # 4. System execution logs
            await db.execute("""
                CREATE TABLE IF NOT EXISTS system_logs (
                    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT DEFAULT (datetime('now', 'utc')),
                    level TEXT CHECK(level IN ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')),
                    component TEXT NOT NULL,
                    message TEXT NOT NULL,
                    exception_details TEXT
                )
            """)
            await db.execute("CREATE INDEX IF NOT EXISTS idx_system_logs_level_time ON system_logs(level, timestamp)")
            
            await db.commit()
            
        self._initialized = True
        print(f"Database initialized at: {self.db_path}")

    # --- Telemetry & Event Logging API ---
    async def save_event(self, event_id: str, event_type: str, version: str, timestamp: str, sender_device_id: str, payload: dict):
        """Save a telemetry event to the database."""
        await self.initialize()
        payload_str = json.dumps(payload)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO event_logs (event_id, event_type, version, timestamp, sender_device_id, payload)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (event_id, event_type, version, timestamp, sender_device_id, payload_str)
            )
            await db.commit()

    async def get_events(self, limit: int = 50, offset: int = 0, event_type_filter: str = None):
        """Fetch telemetry events from the database."""
        await self.initialize()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            if event_type_filter:
                cursor = await db.execute(
                    """
                    SELECT * FROM event_logs 
                    WHERE event_type = ? 
                    ORDER BY timestamp DESC LIMIT ? OFFSET ?
                    """,
                    (event_type_filter, limit, offset)
                )
            else:
                cursor = await db.execute(
                    "SELECT * FROM event_logs ORDER BY timestamp DESC LIMIT ? OFFSET ?",
                    (limit, offset)
                )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    # --- Paired Devices API ---
    async def pair_device(self, device_id: str, name: str, device_type: str, public_key: str):
        """Register or update a paired client device."""
        await self.initialize()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO paired_devices (device_id, device_name, device_type, public_key, last_seen_at)
                VALUES (?, ?, ?, ?, datetime('now', 'utc'))
                """,
                (device_id, name, device_type, public_key)
            )
            await db.commit()

    async def is_device_paired(self, device_id: str) -> bool:
        """Check if a specific device ID is paired."""
        await self.initialize()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT 1 FROM paired_devices WHERE device_id = ?", (device_id,))
            row = await cursor.fetchone()
            return row is not None

    async def get_paired_device(self, device_id: str):
        """Fetch details of a paired device."""
        await self.initialize()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM paired_devices WHERE device_id = ?", (device_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def update_device_last_seen(self, device_id: str):
        """Update last seen timestamp for a paired device."""
        await self.initialize()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE paired_devices SET last_seen_at = datetime('now', 'utc') WHERE device_id = ?",
                (device_id,)
            )
            await db.commit()

    # --- Settings API ---
    async def get_setting(self, key: str, default=None):
        """Retrieve a setting by key."""
        await self.initialize()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT settings_value FROM settings WHERE settings_key = ?", (key,))
            row = await cursor.fetchone()
            if row:
                try:
                    return json.loads(row[0])
                except json.JSONDecodeError:
                    return row[0]
            return default

    async def set_setting(self, key: str, value):
        """Set or update a setting by key."""
        await self.initialize()
        value_str = json.dumps(value)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO settings (settings_key, settings_value, updated_at)
                VALUES (?, ?, datetime('now', 'utc'))
                """,
                (key, value_str)
            )
            await db.commit()

    # --- System Logs API ---
    async def log_system(self, level: str, component: str, message: str, exception_details: str = None):
        """Write an execution log entry to the system logs database."""
        await self.initialize()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO system_logs (level, component, message, exception_details)
                VALUES (?, ?, ?, ?)
                """,
                (level, component, message, exception_details)
            )
            await db.commit()

# Singleton instance for the application
db_service = DatabaseService()

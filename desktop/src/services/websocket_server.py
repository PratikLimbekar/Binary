import asyncio
import json
import uuid
from datetime import datetime
import websockets
from src.core.event_bus import bus
from src.services.db import db_service
from shared.python.schema_validator import validator

class WebSocketServer:
    def __init__(self):
        self.server = None
        self.connected_devices = {}  # device_id -> WebSocketCommonProtocol
        self._is_running = False

    async def start(self, host="0.0.0.0", port=8765):
        """Start the WebSocket server."""
        if self._is_running:
            return
        self._is_running = True
        self.server = await websockets.serve(
            self._connection_handler, host, port
        )
        print(f"[WebSocketServer] Listening on ws://{host}:{port}")
        await db_service.log_system("INFO", "WebSocketServer", f"Server started on ws://{host}:{port}")

    async def stop(self):
        """Stop the WebSocket server and close all client connections."""
        if not self._is_running:
            return
        self._is_running = False
        print("[WebSocketServer] Stopping server...")
        
        # Close all active connections
        if self.connected_devices:
            close_tasks = [
                ws.close() for ws in self.connected_devices.values()
            ]
            await asyncio.gather(*close_tasks, return_exceptions=True)
            self.connected_devices.clear()

        if self.server:
            self.server.close()
            await self.server.wait_closed()
            self.server = None
            
        print("[WebSocketServer] Server stopped.")
        await db_service.log_system("INFO", "WebSocketServer", "Server stopped.")

    async def broadcast(self, event: dict, exclude_device_id: str = None):
        """Broadcast an event to all connected devices (except optionally the sender)."""
        if not self.connected_devices:
            return
            
        message = json.dumps(event)
        send_tasks = []
        for device_id, ws in list(self.connected_devices.items()):
            if device_id != exclude_device_id:
                send_tasks.append(self._safe_send(ws, device_id, message))
                
        if send_tasks:
            await asyncio.gather(*send_tasks)

    async def _safe_send(self, ws, device_id: str, message: str):
        try:
            await ws.send(message)
        except Exception as e:
            print(f"[WebSocketServer] Failed to send message to {device_id}: {e}")
            # Clean up stale connection
            if device_id in self.connected_devices:
                del self.connected_devices[device_id]

    async def _connection_handler(self, websocket, path):
        """Handles lifecycle of a client WebSocket connection."""
        device_id = None
        print(f"[WebSocketServer] New connection from {websocket.remote_address}")
        
        try:
            async for raw_message in websocket:
                try:
                    message_data = json.loads(raw_message)
                except json.JSONDecodeError:
                    await self._send_error(websocket, "Invalid JSON format")
                    continue

                event_type = message_data.get("event_type")
                
                # --- Handshake & Pairing Protocol ---
                if event_type == "system.handshake.request":
                    payload = message_data.get("payload", {})
                    client_device_id = message_data.get("sender_device_id")
                    device_name = payload.get("device_name", "Unknown Device")
                    device_type = payload.get("device_type", "mobile")
                    public_key = payload.get("public_key", "default_key")

                    if not client_device_id:
                        await self._send_error(websocket, "Missing sender_device_id")
                        continue

                    # Verify pairing status in DB
                    is_paired = await db_service.is_device_paired(client_device_id)
                    if not is_paired:
                        # Automated pairing flow for Phase 1: auto-approve and save to DB
                        print(f"[WebSocketServer] Auto-pairing new device: {device_name} ({client_device_id})")
                        await db_service.pair_device(client_device_id, device_name, device_type, public_key)
                        # Notify the GUI about new pairing
                        bus.publish("ui.reminder_triggered", f"Paired with: {device_name}")

                    # Connection authorized
                    device_id = client_device_id
                    self.connected_devices[device_id] = websocket
                    await db_service.update_device_last_seen(device_id)
                    
                    # Respond with handshake success
                    handshake_response = {
                        "event_id": str(uuid.uuid4()),
                        "event_type": "system.handshake.response",
                        "version": "1.0.0",
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                        "sender_device_id": "desktop_brain",
                        "payload": {"success": True, "message": "Handshake successful"}
                    }
                    await websocket.send(json.dumps(handshake_response))
                    print(f"[WebSocketServer] Device {device_id} ({device_name}) authorized.")
                    await db_service.log_system("INFO", "WebSocketServer", f"Device {device_id} ({device_name}) connected.")
                    continue

                # Enforce that device must handshake first
                if not device_id:
                    await self._send_error(websocket, "Authentication required. Send system.handshake.request first.")
                    continue

                # --- General Event Processing ---
                # Validate against schema
                try:
                    validator.validate(message_data)
                except Exception as val_err:
                    print(f"[WebSocketServer] Schema validation failed for event {event_type} from {device_id}: {val_err}")
                    await self._send_error(websocket, f"Schema validation failed: {str(val_err)}")
                    continue

                # Save event to SQLite database
                await db_service.save_event(
                    event_id=message_data["event_id"],
                    event_type=message_data["event_type"],
                    version=message_data["version"],
                    timestamp=message_data["timestamp"],
                    sender_device_id=message_data["sender_device_id"],
                    payload=message_data["payload"]
                )

                # Update device presence
                await db_service.update_device_last_seen(device_id)

                # Process specific events locally
                await self._route_incoming_event(message_data)

        except websockets.exceptions.ConnectionClosed:
            print(f"[WebSocketServer] Connection closed for device: {device_id or 'Unauthorized'}")
        except Exception as e:
            print(f"[WebSocketServer] Connection handler exception: {e}")
        finally:
            if device_id and device_id in self.connected_devices:
                del self.connected_devices[device_id]
                await db_service.log_system("INFO", "WebSocketServer", f"Device {device_id} disconnected.")

    async def _route_incoming_event(self, event: dict):
        """Route valid events to local event bus and/or broadcast to other clients."""
        event_type = event["event_type"]
        sender = event["sender_device_id"]
        payload = event["payload"]

        # 1. Publish to local Python Event Bus for GUI reaction
        if event_type == "camera.detection.posture_bad":
            # Posture detection notification
            bus.publish(
                "ui.reminder_triggered", 
                f"Posture Alert: Neck angle {payload.get('neck_angle_deg')}°"
            )
        elif event_type == "camera.detection.presence_changed":
            presence = "entered" if payload.get("present") else "left"
            bus.publish("ui.reminder_triggered", f"Room Presence: User {presence}")
        elif event_type == "alarm.trigger.wake_up":
            bus.publish("ui.reminder_triggered", "🌅 WAKE UP TIME!")
            
        # 2. Re-broadcast data sync events (e.g. settings or notes changes)
        if event_type == "settings.sync.update":
            from src.services.settings_service import settings_service
            await settings_service.handle_sync_event(event)
            await self.broadcast(event, exclude_device_id=sender)
        elif event_type.startswith("notes.sync."):
            await self.broadcast(event, exclude_device_id=sender)

    async def _send_error(self, websocket, message: str):
        error_event = {
            "event_id": str(uuid.uuid4()),
            "event_type": "system.error",
            "version": "1.0.0",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "sender_device_id": "desktop_brain",
            "payload": {"message": message}
        }
        try:
            await websocket.send(json.dumps(error_event))
        except Exception:
            pass

# Singleton WebSocket server instance
websocket_server = WebSocketServer()

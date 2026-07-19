import socket
from zeroconf import IPVersion, ServiceInfo, Zeroconf

class DiscoveryService:
    def __init__(self, service_type="_binary-brain._tcp.local.", service_name="BinaryBrain"):
        self.service_type = service_type
        self.service_name = f"{service_name}.{service_type}"
        self.zeroconf = None
        self.service_info = None

    def _get_local_ip(self):
        """Utility to get the active local network IP address."""
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # We don't actually establish a connection, but this identifies the correct interface
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
        except Exception:
            ip = '127.0.0.1'
        finally:
            s.close()
        return ip

    def start(self, port: int, device_id: str):
        """Start advertising the service on the local network."""
        local_ip = self._get_local_ip()
        print(f"[mDNS] Starting advertising on {local_ip}:{port}")
        
        self.zeroconf = Zeroconf(ip_version=IPVersion.V4Only)
        
        # Build mDNS service metadata
        self.service_info = ServiceInfo(
            type_=self.service_type,
            name=self.service_name,
            addresses=[socket.inet_aton(local_ip)],
            port=port,
            properties={
                "version": "1.0.0",
                "device_id": device_id,
                "server_ip": local_ip
            }
        )
        
        try:
            self.zeroconf.register_service(self.service_info)
            print(f"[mDNS] Successfully registered service {self.service_name}")
        except Exception as e:
            print(f"[mDNS] Error registering service: {e}")

    def stop(self):
        """Unregister the service and clean up."""
        if self.zeroconf and self.service_info:
            print("[mDNS] Stopping service advertising...")
            try:
                self.zeroconf.unregister_service(self.service_info)
                self.zeroconf.close()
            except Exception as e:
                print(f"[mDNS] Error unregistering service: {e}")
            self.zeroconf = None
            self.service_info = None

# Singleton discovery instance
discovery_service = DiscoveryService()

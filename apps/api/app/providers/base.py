from abc import ABC, abstractmethod
from typing import Any


class ProviderAdapter(ABC):
    name: str
    display_name: str
    capabilities: dict[str, bool]

    @abstractmethod
    def get_stats(self) -> dict[str, Any]: ...

    @abstractmethod
    def restart(self) -> str: ...

    @abstractmethod
    def reload(self) -> str: ...

    @abstractmethod
    def read_logs(self) -> list[str]: ...


class MockXrayAdapter(ProviderAdapter):
    name = "mock"
    display_name = "MockProvider"
    capabilities = {
        "links": True,
        "profiles": True,
        "sessions": True,
        "server_control": True,
        "logs": True,
    }

    def get_stats(self) -> dict[str, Any]:
        return {
            "service_status": "running",
            "active_connections": 2,
            "traffic_24h_gb": 12.4,
            "provider": self.name,
            "capabilities": self.capabilities,
        }

    def restart(self) -> str:
        return "Mock restart executed"

    def reload(self) -> str:
        return "Mock reload executed"

    def read_logs(self) -> list[str]:
        return [
            "[INFO] mock: inbound accepted connection from 93.184.216.34",
            "[WARN] mock: reconnect spike detected",
            "[INFO] mock: uplink 1.23GB downlink 5.24GB",
        ]


class XrayProviderAdapter(ProviderAdapter):
    name = "xray"
    display_name = "Xray"
    capabilities = {
        "links": True,
        "profiles": True,
        "sessions": True,
        "server_control": True,
        "logs": True,
    }

    def get_stats(self) -> dict[str, Any]:
        return {
            "service_status": "running",
            "active_connections": 2,
            "traffic_24h_gb": 8.7,
            "provider": self.name,
            "capabilities": self.capabilities,
            "message": "Xray provider scaffold: connect real Stats API/logs in integration stage.",
        }

    def restart(self) -> str:
        return "Xray restart scaffold placeholder"

    def reload(self) -> str:
        return "Xray reload scaffold placeholder"

    def read_logs(self) -> list[str]:
        return [
            "[INFO] xray: scaffold logs source attached",
            "[INFO] xray: ready for real integration",
        ]


class WireGuardProviderAdapter(ProviderAdapter):
    name = "wg"
    display_name = "WireGuard"
    capabilities = {
        "links": False,
        "profiles": False,
        "sessions": True,
        "server_control": True,
        "logs": True,
    }

    def get_stats(self) -> dict[str, Any]:
        return {
            "service_status": "degraded",
            "active_connections": 1,
            "traffic_24h_gb": 4.1,
            "provider": self.name,
            "capabilities": self.capabilities,
            "message": "WireGuard v1 path enabled. Link/profile flows are provider-specific and currently unavailable.",
        }

    def restart(self) -> str:
        return "WireGuard runtime restart requested (v1 scaffold)"

    def reload(self) -> str:
        return "WireGuard runtime reload requested (v1 scaffold)"

    def read_logs(self) -> list[str]:
        return [
            "[INFO] wg: interface wg0 up (scaffold)",
            "[WARN] wg: peer stats integration pending",
        ]


class AvgProviderAdapter(ProviderAdapter):
    name = "avg"
    display_name = "AVG"
    capabilities = {
        "links": False,
        "profiles": False,
        "sessions": False,
        "server_control": False,
        "logs": True,
    }

    def get_stats(self) -> dict[str, Any]:
        return {
            "service_status": "degraded",
            "active_connections": 0,
            "traffic_24h_gb": 0.0,
            "provider": self.name,
            "capabilities": self.capabilities,
            "message": "AVG provider is staged in v1: runtime path exists, operational parity is intentionally limited.",
        }

    def restart(self) -> str:
        return "AVG runtime restart is unavailable in staged v1"

    def reload(self) -> str:
        return "AVG runtime reload is unavailable in staged v1"

    def read_logs(self) -> list[str]:
        return [
            "[INFO] avg: staged provider runtime up",
            "[WARN] avg: control-plane actions disabled in v1",
        ]

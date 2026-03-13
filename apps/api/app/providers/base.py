from abc import ABC, abstractmethod
from typing import Any


class ProviderAdapter(ABC):
    name: str = "unknown"

    @abstractmethod
    def get_stats(self) -> dict[str, Any]: ...

    @abstractmethod
    def restart(self) -> str: ...

    @abstractmethod
    def reload(self) -> str: ...

    @abstractmethod
    def read_logs(self) -> list[str]: ...

    @abstractmethod
    def capabilities(self) -> dict[str, bool]: ...


class MockProviderAdapter(ProviderAdapter):
    name = "mock"

    def get_stats(self) -> dict[str, Any]:
        return {"service_status": "running", "active_connections": 2, "traffic_24h_gb": 12.4}

    def restart(self) -> str:
        return "Mock restart executed"

    def reload(self) -> str:
        return "Mock reload executed"

    def read_logs(self) -> list[str]:
        return [
            "[INFO] mock inbound accepted connection from 93.184.216.34",
            "[WARN] reconnect spike detected for UUID ...a3f1",
            "[INFO] uplink 1.23GB downlink 5.24GB",
        ]

    def capabilities(self) -> dict[str, bool]:
        return {
            "links": True,
            "profiles": True,
            "sessions": True,
            "server_control": True,
            "traffic_charts": True,
        }


class XrayProviderAdapter(MockProviderAdapter):
    name = "xray"

    def read_logs(self) -> list[str]:
        return ["Xray provider: attach /var/log/xray/access.log and error.log for production telemetry"]


class WireGuardProviderAdapter(MockProviderAdapter):
    name = "wg"

    def get_stats(self) -> dict[str, Any]:
        return {
            "service_status": "running",
            "active_connections": 1,
            "traffic_24h_gb": 6.8,
            "message": "WireGuard provider v1 scaffold",
        }

    def capabilities(self) -> dict[str, bool]:
        return {
            "links": False,
            "profiles": False,
            "sessions": True,
            "server_control": True,
            "traffic_charts": True,
        }


class AvgProviderAdapter(MockProviderAdapter):
    name = "avg"

    def get_stats(self) -> dict[str, Any]:
        return {
            "service_status": "degraded",
            "active_connections": 0,
            "traffic_24h_gb": 0.4,
            "message": "AVG provider v1 scaffold",
        }

    def capabilities(self) -> dict[str, bool]:
        return {
            "links": False,
            "profiles": False,
            "sessions": False,
            "server_control": False,
            "traffic_charts": False,
        }

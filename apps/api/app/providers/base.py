from abc import ABC, abstractmethod
from typing import Any


class XrayAdapter(ABC):
    @abstractmethod
    def get_stats(self) -> dict[str, Any]: ...

    @abstractmethod
    def restart(self) -> str: ...

    @abstractmethod
    def reload(self) -> str: ...

    @abstractmethod
    def read_logs(self) -> list[str]: ...


class MockXrayAdapter(XrayAdapter):
    def get_stats(self) -> dict[str, Any]:
        return {"service_status": "running", "active_connections": 2, "traffic_24h_gb": 12.4}

    def restart(self) -> str:
        return "Mock restart executed"

    def reload(self) -> str:
        return "Mock reload executed"

    def read_logs(self) -> list[str]:
        return [
            "[INFO] inbound accepted connection from 93.184.216.34",
            "[WARN] reconnect spike detected for UUID ...a3f1",
            "[INFO] uplink 1.23GB downlink 5.24GB",
        ]


class XrayProviderAdapter(XrayAdapter):
    def get_stats(self) -> dict[str, Any]:
        return {
            "service_status": "degraded",
            "active_connections": 0,
            "traffic_24h_gb": 0,
            "message": "Xray integration scaffold: connect gRPC Stats API and parse access logs.",
        }

    def restart(self) -> str:
        return "Xray restart scaffold placeholder"

    def reload(self) -> str:
        return "Xray reload scaffold placeholder"

    def read_logs(self) -> list[str]:
        return ["XrayProvider scaffold: attach /var/log/xray/access.log and error.log"]

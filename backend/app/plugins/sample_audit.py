from typing import Any

from app.plugins.base import EnvForgePlugin


class SampleAuditPlugin(EnvForgePlugin):
    @property
    def name(self) -> str:
        return "sample-audit-plugin"

    @property
    def version(self) -> str:
        return "1.0.0"

    async def initialize(self) -> None:
        print(f"[{self.name}] Initialized version {self.version}")

    async def handle_event(self, event_name: str, payload: dict[str, Any]) -> None:
        print(f"[{self.name}] Received event '{event_name}' with payload: {payload}")
        # Audit logic goes here

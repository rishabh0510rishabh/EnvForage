from abc import ABC, abstractmethod
from typing import Any


class EnvForgePlugin(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the plugin"""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """Version of the plugin"""
        pass

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize plugin resources"""
        pass

    @abstractmethod
    async def handle_event(self, event_name: str, payload: dict[str, Any]) -> None:
        """Handle dispatched events"""
        pass

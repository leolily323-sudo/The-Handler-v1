"""
Schema / Command Registry boundary for schema_version validation.
Blueprint §5.3 + Acceptance Criteria ("Unsupported schema versions are rejected").

Handler does not own the registry. It depends on an injected port so that
schema authority remains outside the Handler (ChatGPT Finding 3).
"""

from __future__ import annotations

from typing import Protocol, Set, Optional
from abc import abstractmethod


class SchemaRegistryPort(Protocol):
    """
    Answers whether a (command_type, schema_version) pair is supported.
    Concrete registry lives with the Command Registry / Foundation layer.
    """

    @abstractmethod
    def is_supported(self, command_type: str, schema_version: str) -> bool:
        ...


class StaticSchemaRegistry:
    """
    Simple static registry for tests and early integration.
    Production will use the real Command Registry.
    """

    def __init__(self, supported: Optional[dict[str, Set[str]]] = None) -> None:
        # command_type → set of supported schema_version strings
        self._supported = supported or {
            "SendNotification": {"1.0"},
        }

    def is_supported(self, command_type: str, schema_version: str) -> bool:
        versions = self._supported.get(command_type)
        if versions is None:
            return False
        return schema_version in versions

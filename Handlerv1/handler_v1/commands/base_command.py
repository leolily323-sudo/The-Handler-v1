"""
Command Contract
Blueprint §5 — every executable Command MUST contain:
  command_id, idempotency_key, schema_version, explicit type, validated parameters.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, Optional
from abc import ABC


@dataclass(frozen=True)
class BaseCommand(ABC):
    """
    Immutable base for all typed Commands.
    Handler MUST treat Command as immutable (Blueprint §27).
    """
    command_id: str
    idempotency_key: str
    schema_version: str

    # Concrete subclasses MUST set this class variable
    command_type: ClassVar[str]

    def __post_init__(self) -> None:
        if not self.command_id:
            raise ValueError("command_id is required")
        if not self.idempotency_key:
            raise ValueError("idempotency_key is required for externally effectful Commands")
        if not self.schema_version:
            raise ValueError("schema_version is required")

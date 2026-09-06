"""
Example concrete Command types for Handler v1 demonstration and testing.
These are illustrative; production Commands live in the Command Registry.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from .base_command import BaseCommand


@dataclass(frozen=True)
class SendNotificationCommand(BaseCommand):
    """Illustrative externally-effectful Command."""
    command_type: ClassVar[str] = "SendNotification"
    recipient: str
    channel: str
    body: str
    # schema_version is inherited and required

    def __post_init__(self) -> None:
        super().__post_init__()
        if not self.recipient:
            raise ValueError("recipient is required")
        if not self.channel:
            raise ValueError("channel is required")

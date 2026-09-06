"""
Concrete Handler example: SendNotificationHandler
Demonstrates the required pattern for a single-Command Handler.
"""

from __future__ import annotations

from typing import Optional, Type

from ..commands.example_commands import SendNotificationCommand
from ..ports.external_effect import ExternalEffectPort
from .handler import Handler, HandlerContext


class SendNotificationHandler(Handler[SendNotificationCommand]):
    supported_command_type: Type[SendNotificationCommand] = SendNotificationCommand

    def __init__(
        self,
        context: HandlerContext,
        effect_port: ExternalEffectPort[SendNotificationCommand],
    ) -> None:
        super().__init__(
            context=context,
            effect_port=effect_port,
            handler_type="SendNotificationHandler",
        )

    def _validate_operation(self, command: SendNotificationCommand) -> Optional[str]:
        if not command.recipient.strip():
            return "recipient must be non-empty"
        if command.channel not in {"email", "sms", "push"}:
            return f"unsupported channel: {command.channel}"
        if not command.body:
            return "body is required"
        return None

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
HANDLER_ROOT = REPO_ROOT / "Handlerv1"
if str(HANDLER_ROOT) not in sys.path:
    sys.path.insert(0, str(HANDLER_ROOT))

from handler_v1.commands.example_commands import SendNotificationCommand
from handler_v1.core.handler import HandlerContext
from handler_v1.core.notification_handler import SendNotificationHandler
from handler_v1.ports.in_memory import (
    AlwaysAllowAuthorization,
    InMemoryIdempotency,
    RecordingEffectPort,
)
from handler_v1.ports.schema import StaticSchemaRegistry
from handler_v1.ports.external_effect import ExternalOutcome, ExternalStatus


def main() -> None:
    context = HandlerContext(
        authorization=AlwaysAllowAuthorization(),
        idempotency=InMemoryIdempotency(),
        schema_registry=StaticSchemaRegistry(),
    )

    effect = RecordingEffectPort(
        ExternalOutcome(
            status=ExternalStatus.CONFIRMED_SUCCESS,
            external_reference="demo-record-1",
        )
    )

    handler = SendNotificationHandler(context=context, effect_port=effect)
    command = SendNotificationCommand(
        command_id="demo-command-1",
        idempotency_key="demo-operation-1",
        schema_version="1.0",
        recipient="example@example.com",
        channel="email",
        body="Hello from the local Handler demo",
    )

    result = handler.handle(command)
    print(result.status.value)
    print(f"Effect calls recorded: {len(effect.calls)}")


if __name__ == "__main__":
    main()

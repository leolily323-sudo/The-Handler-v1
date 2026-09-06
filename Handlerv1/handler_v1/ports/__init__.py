"""Explicit dependency ports — Blueprint §§6, 10, 12, 35."""

from .authorization import AuthorizationPort, AuthorizationDecision
from .idempotency import (
    IdempotencyPort,
    IdempotencyClaimResult,
    IdempotencyClaimStatus,
    IdempotencyPersistenceError,
    IdempotencyClaimError,
)
from .external_effect import ExternalEffectPort, ExternalOutcome, ExternalStatus
from .schema import SchemaRegistryPort, StaticSchemaRegistry

__all__ = [
    "AuthorizationPort",
    "AuthorizationDecision",
    "IdempotencyPort",
    "IdempotencyClaimResult",
    "IdempotencyClaimStatus",
    "IdempotencyPersistenceError",
    "IdempotencyClaimError",
    "ExternalEffectPort",
    "ExternalOutcome",
    "ExternalStatus",
    "SchemaRegistryPort",
    "StaticSchemaRegistry",
]

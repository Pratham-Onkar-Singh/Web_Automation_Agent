"""Independent, trusted completion predicates."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Awaitable, Callable


class Ending(str, Enum):
    VERIFIED_SUCCESS = "verified_success"
    UNVERIFIED_DONE = "unverified_done"
    VERIFICATION_FAILED = "verification_failed"
    POLICY_BLOCKED = "policy_blocked"
    BUDGET_EXHAUSTED = "budget_exhausted"
    PROVIDER_ERROR = "provider_error"
    BROWSER_ERROR = "browser_error"
    INVALID_MODEL_OUTPUT = "invalid_model_output"


@dataclass(frozen=True)
class VerificationResult:
    ending: Ending
    reason: str


Predicate = Callable[[], bool | Awaitable[bool]]


async def verify_done(predicate: Predicate | None) -> VerificationResult:
    if predicate is None:
        return VerificationResult(Ending.UNVERIFIED_DONE, "no trusted completion predicate configured")
    result = predicate()
    if hasattr(result, "__await__"):
        result = await result
    if result:
        return VerificationResult(Ending.VERIFIED_SUCCESS, "trusted completion predicate passed")
    return VerificationResult(Ending.VERIFICATION_FAILED, "trusted completion predicate failed")

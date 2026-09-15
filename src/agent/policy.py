"""Fail-closed origin and sensitive-action policy."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit
import secrets


def origin(url: str) -> tuple[str, str, int | None]:
    p = urlsplit(url)
    if p.scheme not in {"http", "https"} or not p.hostname:
        raise ValueError(f"unsupported URL: {url}")
    port = p.port
    if port is None:
        port = 443 if p.scheme == "https" else 80
    return p.scheme.lower(), p.hostname.lower().rstrip("."), port


def same_origin(left: str, right: str) -> bool:
    try:
        return origin(left) == origin(right)
    except ValueError:
        return False


@dataclass(frozen=True)
class Approval:
    token: str
    action_id: str
    origin: tuple[str, str, int | None]
    target: str
    expires_at: datetime


class PolicyDenied(PermissionError):
    pass


class ActionPolicy:
    def __init__(self, allowed_origins: set[str] | None = None, protected_targets: set[str] | None = None, *, allow_bootstrap_navigation: bool = False):
        self.allowed_origins = {origin(x) for x in (allowed_origins or set())}
        self.protected_targets = {x.lower() for x in (protected_targets or {"submit", "delete", "send", "purchase"})}
        self.allow_bootstrap_navigation = allow_bootstrap_navigation
        self._approvals: dict[str, Approval] = {}

    def check_url(self, url: str) -> None:
        parsed = origin(url)
        if not self.allowed_origins and self.allow_bootstrap_navigation:
            self.allowed_origins.add(parsed)
            return
        if not self.allowed_origins:
            raise PolicyDenied("no allowed origins configured")
        if parsed not in self.allowed_origins:
            raise PolicyDenied(f"origin not allowed: {parsed[0]}://{parsed[1]}:{parsed[2]}")

    def is_protected(self, target: str) -> bool:
        value = target.lower()
        return any(word in value for word in self.protected_targets)

    def issue_approval(self, action_id: str, page_url: str, target: str, ttl_seconds: int = 60) -> str:
        self.check_url(page_url)
        token = secrets.token_urlsafe(18)
        self._approvals[token] = Approval(token, action_id, origin(page_url), target, datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds))
        return token

    def consume_approval(self, token: str, action_id: str, page_url: str, target: str) -> None:
        approval = self._approvals.pop(token, None)
        if not approval or approval.expires_at <= datetime.now(timezone.utc):
            raise PolicyDenied("approval missing or expired")
        self.check_url(page_url)
        if approval.action_id != action_id or approval.origin != origin(page_url) or approval.target != target:
            raise PolicyDenied("approval does not match the current action and target")

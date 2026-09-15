# Project status and reviewer map

This repository implements a screenshot-driven Python/Playwright browser
agent. The model proposes typed actions; a central controller validates policy
and executes them; trusted predicates verify completion.

## Current flow

1. Start an isolated Chromium context with no inherited storage.
2. Capture a full-resolution screenshot and viewport metadata.
3. Send the task, screenshot, and action prompt to the configured provider.
4. Parse one balanced JSON action and validate its schema and bounds.
5. Apply origin/network policy and protected-action approval checks.
6. Execute the action through `ActionController`.
7. Record sanitized JSONL events and repeat within step/action budgets.
8. Treat `done` as a verification request, not proof of success.

## Reviewer entry points

- `src/agent/actions.py`: action schema and coordinate scaling.
- `src/agent/controller.py`: single browser side-effect boundary.
- `src/agent/policy.py`: exact origin checks and expiring approvals.
- `src/agent/verification.py`: independent completion outcomes.
- `fixtures/`: owned local fixture server and scenario manifest.
- `tests/`: deterministic offline checks.
- `evaluate.py`: recorded-response evaluation entry point.

## Deliberate limitations

Bootstrap navigation is convenient for task instructions that contain a URL,
but explicit `allowed_origins` is stronger for high-assurance tasks. Request
interception is a browser-level boundary, not a complete operating-system or
arbitrary screenshot-DLP guarantee. General websites may contain sensitive
controls that cannot be classified reliably from screenshots alone.

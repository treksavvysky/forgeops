"""Event hook system — subscribe callbacks to state engine events.

Hooks fire after the transition/operation is committed. They are synchronous
and best-effort — a failing hook does not roll back the operation.

Usage:
    from core.hooks import hooks, HookEvent

    @hooks.on(HookEvent.on_state_change)
    def my_handler(payload):
        print(f"WI-{payload['task_id']} changed from {payload['old_state']} to {payload['new_state']}")

    # Or register programmatically:
    hooks.subscribe(HookEvent.on_assigned, my_callback)
"""

import enum
import logging
from collections import defaultdict
from typing import Any, Callable

logger = logging.getLogger(__name__)


class HookEvent(str, enum.Enum):
    on_state_change = "on_state_change"
    on_blocked = "on_blocked"
    on_unblocked = "on_unblocked"
    on_assigned = "on_assigned"
    on_execution_complete = "on_execution_complete"
    on_review_submitted = "on_review_submitted"
    on_repo_conflict = "on_repo_conflict"
    on_rework = "on_rework"


class HookRegistry:
    """Central registry for event hooks."""

    def __init__(self):
        self._handlers: dict[HookEvent, list[Callable]] = defaultdict(list)

    def subscribe(self, event: HookEvent, handler: Callable) -> None:
        self._handlers[event].append(handler)

    def unsubscribe(self, event: HookEvent, handler: Callable) -> None:
        try:
            self._handlers[event].remove(handler)
        except ValueError:
            pass

    def on(self, event: HookEvent):
        """Decorator to register a hook handler."""
        def decorator(fn: Callable) -> Callable:
            self.subscribe(event, fn)
            return fn
        return decorator

    def fire(self, event: HookEvent, payload: dict[str, Any]) -> None:
        """Fire all handlers for an event. Exceptions are logged, not raised."""
        for handler in self._handlers.get(event, []):
            try:
                handler(payload)
            except Exception:
                logger.exception(
                    "Hook handler %s failed for event %s",
                    handler.__name__, event.value,
                )

    def clear(self, event: HookEvent | None = None) -> None:
        """Remove all handlers, or handlers for a specific event."""
        if event is None:
            self._handlers.clear()
        else:
            self._handlers.pop(event, None)


# Singleton registry
hooks = HookRegistry()

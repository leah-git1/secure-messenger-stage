"""
broadcaster.py — SSE fan-out manager.

Maintains a registry of connected SSE clients (one queue per connection).
When a message is published, it is pushed to every queue belonging to the recipient.
"""

import queue
from typing import Dict, Set


# username -> set of SimpleQueues (one per open /stream connection)
_subscribers: Dict[str, Set[queue.SimpleQueue]] = {}


def subscribe(username: str) -> queue.SimpleQueue:
    """Register a new SSE connection for username. Returns its queue."""
    q: queue.SimpleQueue = queue.SimpleQueue()
    _subscribers.setdefault(username, set()).add(q)
    return q


def unsubscribe(username: str, q: queue.SimpleQueue) -> None:
    """Remove a queue when the client disconnects."""
    _subscribers.get(username, set()).discard(q)
    if not _subscribers.get(username):
        _subscribers.pop(username, None)


def publish(recipient: str, message: dict) -> None:
    """Push message to every open queue for recipient."""
    for q in list(_subscribers.get(recipient, [])):
        q.put_nowait(message)


def online_users() -> list:
    """Return list of usernames with at least one active connection."""
    return list(_subscribers.keys())

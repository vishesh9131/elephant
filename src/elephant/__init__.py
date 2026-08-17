"""Elephant carries coding-agent sessions between harnesses."""

from elephant.kernel import Elephant
from elephant.commands import CommandRouter
from elephant.models import Capsule, Confidence, Event, EventKind

__all__ = ["Capsule", "CommandRouter", "Confidence", "Elephant", "Event", "EventKind"]
__version__ = "0.4.2"

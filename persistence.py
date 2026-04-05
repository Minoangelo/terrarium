"""persistence.py—JSON save/load for ~/.terrarium/save.json."""

from __future__ import annotations

import json
from pathlib import Path

from entities import Entity, entity_from_dict
from events import EventLog, MilestoneTracker
from world import World

SAVE_VERSION = 1

SaveData = tuple[World, list[Entity], int, EventLog, MilestoneTracker]


def save_game(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    path: Path,
    world: World,
    entities: list[Entity],
    elapsed: int,
    event_log: EventLog,
    milestones: MilestoneTracker,
) -> None:
    """Serialise full game state to *path* as JSON (atomic write)."""

    path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "version": SAVE_VERSION,
        "elapsed": elapsed,
        "world": world.to_dict(),
        "entities": [e.to_dict() for e in entities],
        "event_log": event_log.to_dict(),
        "milestones": milestones.to_dict(),
    }

    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
    tmp.replace(path)


def load_game(path: Path) -> SaveData | None:
    """Deserialise game state from *path*. Returns `None` on any error."""

    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError):
        return None

    if data.get("version", 0) != SAVE_VERSION:
        return None

    try:
        world = World.from_dict(data["world"])
        entities = [
            e
            for e in (entity_from_dict(d) for d in data.get("entities", []))
            if e is not None
        ]
        elapsed = int(data.get("elapsed", 0))
        event_log = EventLog.from_dict(data.get("event_log", {}))
        milestones = MilestoneTracker.from_dict(data.get("milestones", {}))
    except (KeyError, ValueError, TypeError, AttributeError):
        return None

    return world, entities, elapsed, event_log, milestones

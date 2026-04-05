"""state.py—Shared state dataclasses for runtime and rendering."""

from __future__ import annotations

from dataclasses import dataclass

from entities import Entity
from events import EventLog, MilestoneTracker
from world import World


@dataclass
class GameState:
    """Mutable game state used by the orchestration loop."""

    world: World
    entities: list[Entity]
    elapsed: int
    event_log: EventLog
    milestones: MilestoneTracker

    @classmethod
    def from_tuple(
        cls,
        data: tuple[World, list[Entity], int, EventLog, MilestoneTracker],
    ) -> "GameState":
        """Build state from persisted tuple data."""

        world, entities, elapsed, event_log, milestones = data

        return cls(world, entities, elapsed, event_log, milestones)


@dataclass(frozen=True)
class RenderState:
    """Immutable view model consumed by the renderer."""

    world: World
    entities: list[Entity]
    elapsed: int
    event_log: EventLog
    milestones: MilestoneTracker
    rain_active: bool

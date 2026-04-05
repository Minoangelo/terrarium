"""Simulation invariant tests for entity tick behavior."""

from __future__ import annotations

import entities
from entities import DeadOrganic, Entity, Herbivore, Plant, Predator, process_tick
from events import EventLog
from world import World


def _make_world(width: int = 8, height: int = 8) -> World:
    """Build a deterministic non-water world for simulation tests."""

    world = World(width=width, height=height)

    for row in world.tiles:
        for tile in row:
            tile.is_water = False
            tile.moisture = 50.0
            tile.nutrients = 50.0

    return world


def test_plant_with_low_nutrients_dies_into_dead_organic() -> None:
    """A plant should die and be replaced by DeadOrganic on depleted soil."""

    world = _make_world()
    event_log = EventLog()
    plant = Plant(2, 2)
    world.tiles[2][2].nutrients = 2.5

    updated = process_tick(world, [plant], event_log)

    assert not any(isinstance(e, Plant) for e in updated)
    assert any(
        isinstance(e, DeadOrganic) and (e.x, e.y) == (2, 2)
        for e in updated
    )


def test_dead_organic_fertilizes_and_decays_away() -> None:
    """DeadOrganic should enrich soil and disappear when its timer reaches zero."""

    world = _make_world()
    event_log = EventLog()
    remnant = DeadOrganic(1, 1)
    remnant.decay_timer = 1
    world.tiles[1][1].nutrients = 10.0

    updated = process_tick(world, [remnant], event_log)

    assert updated == []
    assert world.tiles[1][1].nutrients == 10.6


def test_herbivore_eats_adjacent_plant_and_reduces_hunger() -> None:
    """Herbivore should consume adjacent plants before wandering."""

    world = _make_world()
    event_log = EventLog()
    herbivore = Herbivore(1, 1)
    herbivore.hunger = 60.0
    plant = Plant(2, 1)

    updated = process_tick(world, [herbivore, plant], event_log)

    assert not any(isinstance(e, Plant) for e in updated)
    assert any(isinstance(e, Herbivore) for e in updated)
    assert herbivore.hunger < 60.0


def test_herbivore_starvation_spawns_dead_organic_and_logs() -> None:
    """Starving herbivores should die, leave remains, and emit a log event."""

    world = _make_world()
    event_log = EventLog()
    herbivore = Herbivore(3, 3)
    herbivore.hunger = 100.0
    herbivore.health = 5.0

    updated = process_tick(world, [herbivore], event_log)

    assert not any(isinstance(e, Herbivore) for e in updated)
    assert any(isinstance(e, DeadOrganic) for e in updated)
    assert any("starved" in ev.message for ev in event_log.events)


def test_herbivore_reproduces_when_conditions_allow() -> None:
    """Low-hunger herbivores should reproduce when cooldown is clear."""

    world = _make_world()
    event_log = EventLog()
    herbivore = Herbivore(4, 4)
    herbivore.hunger = 0.0
    herbivore.reproduce_cooldown = 0

    updated = process_tick(world, [herbivore], event_log)
    herbivores = [e for e in updated if isinstance(e, Herbivore)]

    assert len(herbivores) == 2
    assert herbivore.reproduce_cooldown == Herbivore.REPR_COOLDOWN
    assert any("new herbivore" in ev.message for ev in event_log.events)


def test_herbivore_respects_population_cap() -> None:
    """Herbivore reproduction must not exceed Herbivore.MAX_POP."""

    world = _make_world(10, 10)
    event_log = EventLog()
    herd: list[Entity] = []

    for idx in range(Herbivore.MAX_POP):
        herbivore = Herbivore(idx % 10, idx // 10)
        herbivore.hunger = 0.0
        herbivore.reproduce_cooldown = 0
        herd.append(herbivore)

    updated = process_tick(world, herd, event_log)

    assert len([e for e in updated if isinstance(e, Herbivore)]) == Herbivore.MAX_POP


def test_predator_moves_toward_nearest_prey() -> None:
    """Predator pathing should target the nearest herbivore in range."""

    world = _make_world()
    event_log = EventLog()
    predator = Predator(0, 0)
    near_prey = Herbivore(3, 0)
    far_prey = Herbivore(4, 0)

    for row in world.tiles:
        for tile in row:
            tile.is_water = True

    world.tiles[0][0].is_water = False
    world.tiles[0][1].is_water = False
    world.tiles[0][3].is_water = False
    world.tiles[0][4].is_water = False

    updated = process_tick(world, [predator, near_prey, far_prey], event_log)

    assert any(isinstance(e, Predator) for e in updated)
    assert (predator.x, predator.y) == (1, 0)


def test_predator_kill_removes_prey_and_spawns_dead_organic() -> None:
    """Predator should kill adjacent prey and leave organic remains."""

    world = _make_world()
    event_log = EventLog()
    predator = Predator(1, 1)
    predator.hunger = 90.0
    prey = Herbivore(2, 1)

    for row in world.tiles:
        for tile in row:
            tile.is_water = True

    world.tiles[1][1].is_water = False
    world.tiles[1][2].is_water = False

    updated = process_tick(world, [predator, prey], event_log)

    assert not any(isinstance(e, Herbivore) for e in updated)
    assert any(
        isinstance(e, DeadOrganic) and (e.x, e.y) == (2, 1)
        for e in updated
    )
    assert predator.hunger < 90.0
    assert any("hunted a herbivore" in ev.message for ev in event_log.events)


def test_predator_starvation_spawns_dead_organic() -> None:
    """Starving predators should die and leave DeadOrganic on their tile."""

    world = _make_world()
    event_log = EventLog()
    predator = Predator(5, 5)
    predator.hunger = 100.0
    predator.health = 3.0

    updated = process_tick(world, [predator], event_log)

    assert not any(isinstance(e, Predator) for e in updated)
    assert any(isinstance(e, DeadOrganic) for e in updated)


def test_predator_gets_name_at_age_300(monkeypatch) -> None:
    """Predator should receive a name exactly when age crosses 300 ticks."""

    world = _make_world()
    event_log = EventLog()
    predator = Predator(6, 6)
    predator.age = 299
    predator.hunger = 0.0
    predator.name = None

    monkeypatch.setattr(entities.random, "choice", lambda _names: "TestName")

    updated = process_tick(world, [predator], event_log)

    assert any(isinstance(e, Predator) for e in updated)
    assert predator.name == "TestName"
    assert any("TestName" in ev.message for ev in event_log.events)

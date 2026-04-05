"""Persistence round-trip and failure-path tests."""

from __future__ import annotations

import json

from entities import EntityType, Herbivore, Plant, Predator
from events import EventLog, MilestoneTracker
from persistence import SAVE_VERSION, load_game, save_game
from world import World


def _make_world() -> World:
    """Build a deterministic world snapshot for persistence tests."""

    world = World(width=8, height=8)

    for y, row in enumerate(world.tiles):
        for x, tile in enumerate(row):
            tile.is_water = False
            tile.moisture = 40.0 + x
            tile.nutrients = 60.0 + y

    world.tiles[0][0].is_water = True
    world.tiles[0][0].moisture = 100.0
    world.tiles[0][0].nutrients = 85.0

    return world


def test_save_and_load_round_trip_preserves_core_state(tmp_path) -> None:
    """save_game/load_game should preserve world, entities, and progress fields."""

    world = _make_world()

    tree = Plant(1, 1, EntityType.TREE)
    tree.age = 12
    tree.growth_timer = 5

    herb = Herbivore(2, 2)
    herb.age = 25
    herb.hunger = 43.2
    herb.health = 77.1
    herb.reproduce_cooldown = 7

    pred = Predator(3, 2)
    pred.age = 301
    pred.hunger = 20.5
    pred.health = 88.9
    pred.reproduce_cooldown = 12
    pred.name = "Rex"

    event_log = EventLog()
    event_log.current_tick = 123
    event_log.log("test event", "green")

    milestones = MilestoneTracker()
    milestones.achieved = {"first_tree", "apex_predator"}

    save_path = tmp_path / "save.json"
    save_game(
        save_path,
        world,
        [tree, herb, pred],
        elapsed=123,
        event_log=event_log,
        milestones=milestones,
    )

    loaded = load_game(save_path)

    assert loaded is not None
    loaded_world, loaded_entities, loaded_elapsed, loaded_log, loaded_milestones = loaded

    assert loaded_elapsed == 123
    assert loaded_world.width == world.width
    assert loaded_world.height == world.height
    assert loaded_world.tiles[0][0].is_water
    assert loaded_world.tiles[1][1].moisture == world.tiles[1][1].moisture
    assert loaded_world.tiles[2][3].nutrients == world.tiles[2][3].nutrients

    assert len(loaded_entities) == 3
    assert any(e.entity_type == EntityType.TREE for e in loaded_entities)
    assert any(e.entity_type == EntityType.HERBIVORE for e in loaded_entities)
    loaded_pred = next(e for e in loaded_entities if e.entity_type == EntityType.PREDATOR)
    assert isinstance(loaded_pred, Predator)
    assert loaded_pred.name == "Rex"

    assert len(loaded_log.events) == 1
    assert loaded_log.events[0].message == "test event"
    assert loaded_milestones.achieved == milestones.achieved


def test_load_game_returns_none_for_corrupt_json(tmp_path) -> None:
    """Corrupt save files should fail safely and return None."""

    save_path = tmp_path / "save.json"
    save_path.write_text("{not valid json", encoding="utf-8")

    assert load_game(save_path) is None


def test_load_game_returns_none_for_version_mismatch(tmp_path) -> None:
    """Unexpected save versions should be rejected."""

    save_path = tmp_path / "save.json"
    payload = {
        "version": SAVE_VERSION + 1,
        "elapsed": 1,
        "world": _make_world().to_dict(),
        "entities": [],
        "event_log": {"events": []},
        "milestones": {"achieved": [], "bt": 0},
    }
    save_path.write_text(json.dumps(payload), encoding="utf-8")

    assert load_game(save_path) is None


def test_load_game_skips_unknown_entities(tmp_path) -> None:
    """Unknown entity payloads should be ignored while loading valid entries."""

    world = _make_world()
    valid_entity = Plant(1, 1).to_dict()
    unknown_entity = {"type": "mystery", "x": 2, "y": 2, "age": 4}

    payload = {
        "version": SAVE_VERSION,
        "elapsed": 9,
        "world": world.to_dict(),
        "entities": [valid_entity, unknown_entity],
        "event_log": {"events": []},
        "milestones": {"achieved": [], "bt": 0},
    }
    save_path = tmp_path / "save.json"
    save_path.write_text(json.dumps(payload), encoding="utf-8")

    loaded = load_game(save_path)

    assert loaded is not None
    _, loaded_entities, loaded_elapsed, _, _ = loaded
    assert loaded_elapsed == 9
    assert len(loaded_entities) == 1
    assert loaded_entities[0].entity_type == EntityType.SEEDLING

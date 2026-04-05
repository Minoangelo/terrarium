"""World rule tests for neighbourhood, soil, fertilisation and persistence."""

from __future__ import annotations

from world import World


def _plain_world(width: int = 8, height: int = 8) -> World:
    """Build a deterministic non-water world for rule-focused tests."""

    world = World(width=width, height=height)

    for row in world.tiles:
        for tile in row:
            tile.is_water = False
            tile.moisture = 50.0
            tile.nutrients = 50.0

    return world


def test_neighbours_respect_bounds_and_exclude_origin() -> None:
    """neighbours() should stay in bounds and never include the input position."""

    world = _plain_world()

    center = world.neighbours(3, 3)
    corner = world.neighbours(0, 0)

    assert len(center) == 8
    assert len(corner) == 3
    assert (3, 3) not in center
    assert (0, 0) not in corner
    assert all(0 <= x < world.width and 0 <= y < world.height for x, y in center)


def test_tick_soil_keeps_water_full_and_applies_rain_and_water_bonus() -> None:
    """tick_soil() should apply expected moisture rules and preserve water tiles."""

    world = _plain_world()
    world.tiles[2][2].is_water = True
    world.tiles[2][2].moisture = 10.0

    world.tiles[2][3].moisture = 50.0
    world.tiles[6][6].moisture = 50.0

    world.tick_soil(rain_active=False)

    assert world.tiles[2][2].moisture == 100.0
    assert world.tiles[2][3].moisture == 50.14
    assert world.tiles[6][6].moisture == 50.02

    world.tick_soil(rain_active=True)

    assert round(world.tiles[2][3].moisture, 2) == 50.98
    assert round(world.tiles[6][6].moisture, 2) == 50.74


def test_fertilise_region_applies_radius_and_caps_values() -> None:
    """fertilise_region() should affect only in-radius tiles and clamp at 100."""

    world = _plain_world()
    world.tiles[4][4].nutrients = 90.0
    world.tiles[0][0].nutrients = 10.0

    world.fertilise_region(4, 4, radius=1)

    assert world.tiles[4][4].nutrients == 100.0
    assert world.tiles[4][5].nutrients == 85.0
    assert world.tiles[0][0].nutrients == 10.0


def test_world_to_dict_and_from_dict_round_trip() -> None:
    """World serialisation should preserve dimensions and tile state."""

    world = _plain_world()
    world.tiles[1][2].moisture = 12.3
    world.tiles[1][2].nutrients = 45.6
    world.tiles[1][2].is_water = True

    data = world.to_dict()
    loaded = World.from_dict(data)

    assert loaded.width == world.width
    assert loaded.height == world.height
    assert loaded.tiles[1][2].moisture == 12.3
    assert loaded.tiles[1][2].nutrients == 45.6
    assert loaded.tiles[1][2].is_water

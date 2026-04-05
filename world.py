"""world.py—Grid, Tile data, and soil simulation."""

import random
import shutil
from dataclasses import dataclass


def get_grid_dims() -> tuple[int, int]:
    """Calculate grid dimensions that fit the current terminal."""

    cols, rows = shutil.get_terminal_size((120, 30))

    # viewport panel is ~70% of width; subtract 4 for borders/padding
    w = min(60, max(20, int(cols * 0.68) - 4))

    # subtract ~6 lines for panel borders and layout chrome
    h = min(24, max(10, rows - 6))

    return w, h


@dataclass
class Tile:
    """A single cell of the world grid with soil properties."""

    moisture: float = 50.0
    nutrients: float = 50.0
    is_water: bool = False

    def to_dict(self) -> dict:
        """Serialise to a compact JSON-compatible dict."""

        return {
            "m": round(self.moisture, 1),
            "n": round(self.nutrients, 1),
            "w": self.is_water,
        }


    @classmethod
    def from_dict(cls, d: dict) -> "Tile":
        """Reconstruct from a saved dict."""

        return cls(
            moisture=d.get("m", 50.0),
            nutrients=d.get("n", 50.0),
            is_water=d.get("w", False),
        )


class World:
    """The simulation grid: a 2-D array of Tiles with water and soil."""

    def __init__(self, width: int = 0, height: int = 0) -> None:
        if not width or not height:
            width, height = get_grid_dims()

        self.width = width
        self.height = height
        self.tiles: list[list[Tile]] = [
            [Tile() for _ in range(width)] for _ in range(height)
        ]
        self._place_water()
        self._randomize_soil()


    # === Initialisation ===

    def _place_water(self) -> None:
        """Scatter 3-5 small water clusters across the grid."""

        for _ in range(random.randint(3, 5)):
            cx = random.randint(2, self.width - 3)
            cy = random.randint(2, self.height - 3)
            r = random.choice([1, 1, 2])

            for dy in range(-r, r + 1):
                for dx in range(-r, r + 1):
                    if dx * dx + dy * dy <= r * r:
                        x, y = cx + dx, cy + dy

                        if 0 <= x < self.width and 0 <= y < self.height:
                            t = self.tiles[y][x]
                            t.is_water = True
                            t.moisture = 100.0
                            t.nutrients = 85.0


    def _randomize_soil(self) -> None:
        """Set each non-water tile to a random initial moisture and nutrient level."""

        for row in self.tiles:
            for t in row:
                if not t.is_water:
                    t.moisture = random.uniform(25.0, 75.0)
                    t.nutrients = random.uniform(30.0, 80.0)


    # === Accessors ===

    def get(self, x: int, y: int) -> Tile | None:
        """Return the tile at (x, y), or None if out of bounds."""

        if 0 <= x < self.width and 0 <= y < self.height:
            return self.tiles[y][x]

        return None

    def neighbours(self, x: int, y: int, r: int = 1) -> list[tuple[int, int]]:
        """Return all in-bounds positions within Chebyshev distance *r* of (x, y)."""

        result = []

        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                if dx == 0 and dy == 0:
                    continue

                nx, ny = x + dx, y + dy

                if 0 <= nx < self.width and 0 <= ny < self.height:
                    result.append((nx, ny))

        return result


    # === Simulation ===

    def tick_soil(self, rain_active: bool = False) -> None:
        """Regenerate moisture and nutrients for every non-water tile."""

        for y in range(self.height):
            for x in range(self.width):
                t = self.tiles[y][x]

                if t.is_water:
                    t.moisture = 100.0

                    continue

                # moisture: passive regen + optional rain + water-adjacency boost
                regen = 0.06

                if rain_active:
                    regen += 0.70
                for nx, ny in self.neighbours(x, y, r=2):
                    if self.tiles[ny][nx].is_water:
                        regen += 0.12
                        break

                t.moisture = min(100.0, max(0.0, t.moisture + regen - 0.04))

                # nutrients: very slow passive regen (organic matter adds more)
                t.nutrients = min(100.0, max(0.0, t.nutrients + 0.01))


    def fertilise_region(self, cx: int, cy: int, radius: int = 6) -> None:
        """Instantly boost nutrients within a circular region."""

        for y in range(max(0, cy - radius), min(self.height, cy + radius + 1)):
            for x in range(max(0, cx - radius), min(self.width, cx + radius + 1)):
                if (x - cx) ** 2 + (y - cy) ** 2 <= radius**2:
                    self.tiles[y][x].nutrients = min(
                        100.0, self.tiles[y][x].nutrients + 35.0
                    )


    # === Persistence ===

    def to_dict(self) -> dict:
        """Serialise the full grid to a JSON-compatible dict."""

        return {
            "w": self.width,
            "h": self.height,
            "tiles": [[t.to_dict() for t in row] for row in self.tiles],
        }


    @classmethod
    def from_dict(cls, d: dict) -> "World":
        """Reconstruct a World from a saved dict without re-generating terrain."""

        obj = cls.__new__(cls)
        obj.width = d["w"]
        obj.height = d["h"]
        obj.tiles = [[Tile.from_dict(t) for t in row] for row in d["tiles"]]

        return obj

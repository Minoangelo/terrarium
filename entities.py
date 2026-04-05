"""entities.py—Entity classes and per-tick simulation logic."""

from __future__ import annotations

import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from events import EventLog
    from world import World


# === Types and render info ===

class EntityType(Enum):
    """All entity types that can occupy a grid tile."""

    SEEDLING = "seedling"
    BUSH = "bush"
    TREE = "tree"
    HERBIVORE = "herbivore"
    PREDATOR = "predator"
    DEAD_ORGANIC = "dead_organic"


# (symbol, rich style)
RENDER: dict[EntityType, tuple[str, str]] = {
    EntityType.SEEDLING: (",", "green"),
    EntityType.BUSH: ("♣", "bright_green"),
    EntityType.TREE: ("↑", "bold green"),
    EntityType.HERBIVORE: ("o", "yellow"),
    EntityType.PREDATOR: ("@", "bold red"),
    EntityType.DEAD_ORGANIC: ("%", "dim yellow"),
}

PLANT_TYPES = frozenset({EntityType.SEEDLING, EntityType.BUSH, EntityType.TREE})
ANIMAL_TYPES = frozenset({EntityType.HERBIVORE, EntityType.PREDATOR})

_PREDATOR_NAMES = ["Rex", "Shadow", "Fang", "Storm", "Blaze", "Claw", "Ember", "Ruin"]


# === Shared tick state ===

@dataclass
class TickState:
    """Mutable state bundle shared across all sub-steps of one simulation tick."""

    world: World
    to_remove: set[int] = field(default_factory=set)
    to_add: list[Entity] = field(default_factory=list)
    occupied: set[tuple[int, int]] = field(default_factory=set)
    event_log: EventLog = field(default=None)

    def remove(self, entity: Entity) -> None:
        """Mark *entity* for removal and free its tile in the occupied set."""

        self.to_remove.add(id(entity))
        self.occupied.discard((entity.x, entity.y))


    def add(self, entity: Entity) -> None:
        """Queue *entity* to be added and claim its tile."""

        self.to_add.append(entity)
        self.occupied.add((entity.x, entity.y))


    def move(self, animal: Animal, nx: int, ny: int) -> None:

        """Relocate *animal* to (nx, ny), keeping the occupied set consistent."""
        self.occupied.discard((animal.x, animal.y))
        animal.x, animal.y = nx, ny
        self.occupied.add((nx, ny))


# === Base classes ===

class Entity(ABC):
    """Abstract base for every object that can occupy a grid tile."""

    def __init__(self, x: int, y: int) -> None:
        self.x = x
        self.y = y
        self.age = 0

    @property
    @abstractmethod
    def entity_type(self) -> EntityType:
        """The EntityType constant that identifies this entity."""

    def to_dict(self) -> dict:
        """Serialise to a JSON-compatible dict."""

        return {
            "type": self.entity_type.value,
            "x": self.x,
            "y": self.y,
            "age": self.age,
        }


class DeadOrganic(Entity):
    """Remnant of a dead plant or animal; fertilises soil as it decays."""

    DECAY_TICKS = 30

    def __init__(self, x: int, y: int) -> None:
        super().__init__(x, y)
        self.decay_timer = self.DECAY_TICKS

    @property
    def entity_type(self) -> EntityType:
        """Return DEAD_ORGANIC."""

        return EntityType.DEAD_ORGANIC


    def to_dict(self) -> dict:
        """Serialise including the remaining decay timer."""

        d = super().to_dict()
        d["dt"] = self.decay_timer

        return d


class Plant(Entity):
    """Vegetation that matures from seedling through bush to tree."""

    SEEDLING_GROW = 30  # ticks: seedling to bush
    BUSH_GROW = 120  # ticks: bush to tree

    def __init__(
        self,
        x: int,
        y: int,
        plant_type: EntityType = EntityType.SEEDLING,
    ) -> None:
        super().__init__(x, y)
        self.plant_type = plant_type
        self.growth_timer = 0
        self.spread_cooldown = random.randint(5, 15)

    @property
    def entity_type(self) -> EntityType:
        """Return the current growth stage as the entity type."""

        return self.plant_type


    def to_dict(self) -> dict:
        """Serialise including growth and spread state."""

        d = super().to_dict()
        d["gt"] = self.growth_timer
        d["sc"] = self.spread_cooldown

        return d


class Animal(Entity, ABC):
    """Abstract base for mobile entities with health, hunger and reproduction."""

    HUNGER_RATE = 1.0
    REPR_COOLDOWN = 60
    MAX_POP = 20
    HUNGER_THRESHOLD = 30.0

    def __init__(self, x: int, y: int) -> None:
        super().__init__(x, y)
        self.health: float = 100.0
        self.hunger: float = random.uniform(0.0, 20.0)
        self.reproduce_cooldown: int = 0
        self.name: str | None = None

    def to_dict(self) -> dict:
        """Serialise including health, hunger, cooldown and optional name."""

        d = super().to_dict()
        d.update(
            h=round(self.health, 1),
            hu=round(self.hunger, 1),
            rc=self.reproduce_cooldown,
            name=self.name,
        )

        return d


class Herbivore(Animal):
    """Plant-eating prey animal."""

    HUNGER_RATE = 1.0
    REPR_COOLDOWN = 60
    MAX_POP = 20
    HUNGER_THRESHOLD = 30.0

    @property
    def entity_type(self) -> EntityType:
        """Return HERBIVORE."""

        return EntityType.HERBIVORE


class Predator(Animal):
    """Meat-eating hunter that pursues and eats herbivores."""

    HUNGER_RATE = 0.7
    REPR_COOLDOWN = 120
    MAX_POP = 5
    HUNT_RADIUS = 5
    HUNGER_THRESHOLD = 20.0

    @property
    def entity_type(self) -> EntityType:
        """Return PREDATOR."""

        return EntityType.PREDATOR


# === Deserialisation ===

def entity_from_dict(d: dict) -> Entity | None:
    """Reconstruct an Entity from a saved dict; returns `None` on unknown type."""

    try:
        etype = EntityType(d["type"])
    except (KeyError, ValueError):
        return None

    x, y = d.get("x", 0), d.get("y", 0)

    if etype == EntityType.DEAD_ORGANIC:
        e: Entity = DeadOrganic(x, y)
        e.decay_timer = d.get("dt", DeadOrganic.DECAY_TICKS)
    elif etype in PLANT_TYPES:
        e = Plant(x, y, etype)
        e.growth_timer = d.get("gt", 0)
        e.spread_cooldown = d.get("sc", 10)
    elif etype == EntityType.HERBIVORE:
        e = Herbivore(x, y)
        e.health = d.get("h", 100.0)
        e.hunger = d.get("hu", 0.0)
        e.reproduce_cooldown = d.get("rc", 0)
        e.name = d.get("name")
    elif etype == EntityType.PREDATOR:
        e = Predator(x, y)
        e.health = d.get("h", 100.0)
        e.hunger = d.get("hu", 0.0)
        e.reproduce_cooldown = d.get("rc", 0)
        e.name = d.get("name")
    else:
        return None

    e.age = d.get("age", 0)
    return e


# === Tick logic ===

def _fmt_age(seconds: int) -> str:
    """Format an age in seconds as a human-readable string."""

    m, s = divmod(seconds, 60)

    return f"{m}m {s}s" if m else f"{s}s"


def process_tick(
    world: World,
    entities: list[Entity],
    event_log: EventLog,
) -> list[Entity]:
    """Advance the simulation by one second. Returns the updated entity list."""

    state = TickState(
        world=world,
        to_remove=set(),
        to_add=[],
        occupied={(e.x, e.y) for e in entities},
        event_log=event_log,
    )

    # age every entity; count down animal reproduction cooldowns
    for e in entities:
        e.age += 1

        if isinstance(e, Animal) and e.reproduce_cooldown > 0:
            e.reproduce_cooldown -= 1

    _tick_dead_organics(state, entities)
    _tick_plants(state, entities)
    _tick_herbivores(state, entities)
    _tick_predators(state, entities)

    return [e for e in entities if id(e) not in state.to_remove] + state.to_add


# === Sub-tick helpers ===

def _tick_dead_organics(state: TickState, entities: list[Entity]) -> None:
    """Decay all `DeadOrganic` entities, fertilising the soil beneath them."""

    for e in entities:
        if not isinstance(e, DeadOrganic):
            continue

        tile = state.world.get(e.x, e.y)

        if tile:
            tile.nutrients = min(100.0, tile.nutrients + 0.6)

        e.decay_timer -= 1

        if e.decay_timer <= 0:
            state.remove(e)


def _tick_plants(state: TickState, entities: list[Entity]) -> None:
    """Grow, spread and kill plants for this tick."""

    for plant in entities:
        if not isinstance(plant, Plant) or id(plant) in state.to_remove:
            continue

        tile = state.world.get(plant.x, plant.y)

        if tile is None:
            continue

        if tile.nutrients < 3.0:
            state.remove(plant)
            state.add(DeadOrganic(plant.x, plant.y))

            continue

        tile.nutrients = max(0.0, tile.nutrients - 0.07)
        plant.growth_timer += 1
        plant.spread_cooldown -= 1

        _plant_try_grow(plant, tile, state)

        if plant.spread_cooldown <= 0:
            _plant_try_spread(plant, state)
            plant.spread_cooldown = random.randint(8, 20)


def _plant_try_grow(plant: Plant, tile, state: TickState) -> None:
    """Promote plant to the next growth stage if conditions are met."""

    if plant.plant_type == EntityType.SEEDLING:
        if (
            plant.growth_timer >= Plant.SEEDLING_GROW
            and tile.nutrients >= 25
            and tile.moisture >= 20
        ):
            plant.plant_type = EntityType.BUSH
            plant.growth_timer = 0
    elif plant.plant_type == EntityType.BUSH:
        if (
            plant.growth_timer >= Plant.BUSH_GROW
            and tile.nutrients >= 35
            and tile.moisture >= 30
        ):
            plant.plant_type = EntityType.TREE
            plant.growth_timer = 0
            state.event_log.log(
                f"🌳 A tree matured at ({plant.x}, {plant.y})",
                "bold green",
            )


def _plant_try_spread(plant: Plant, state: TickState) -> None:
    """Attempt to spread a seed to a random fertile adjacent tile."""

    spread_p = {
        EntityType.SEEDLING: 0.04,
        EntityType.BUSH: 0.08,
        EntityType.TREE: 0.14,
    }.get(plant.plant_type, 0.04)

    if random.random() >= spread_p:
        return

    nbrs = state.world.neighbours(plant.x, plant.y)
    random.shuffle(nbrs)

    for nx, ny in nbrs:
        nt = state.world.get(nx, ny)

        if nt and not nt.is_water and (nx, ny) not in state.occupied:
            if nt.moisture >= 18 and nt.nutrients >= 18:
                state.add(Plant(nx, ny))
                state.event_log.log(
                    f"🌱 Seedling sprouted at ({nx}, {ny})",
                    "green",
                )

                break


def _tick_herbivores(state: TickState, entities: list[Entity]) -> None:
    """Process every living herbivore for this tick."""

    pos_plant: dict[tuple[int, int], Plant] = {
        (e.x, e.y): e
        for e in entities
        if isinstance(e, Plant) and id(e) not in state.to_remove
    }
    herb_count = sum(
        1 for e in entities if isinstance(e, Herbivore) and id(e) not in state.to_remove
    )

    for herb in entities:
        if not isinstance(herb, Herbivore) or id(herb) in state.to_remove:
            continue

        herb_count = _tick_single_herbivore(herb, pos_plant, herb_count, state)


def _tick_single_herbivore(
    herb: Herbivore,
    pos_plant: dict[tuple[int, int], Plant],
    herb_count: int,
    state: TickState,
) -> int:
    """Process one herbivore; returns the updated population count."""

    herb.hunger = min(100.0, herb.hunger + Herbivore.HUNGER_RATE)

    if not _herb_try_eat(herb, pos_plant, state):
        _wander(state.world, herb, state.occupied)

    if herb.hunger >= 100.0:
        herb.health = max(0.0, herb.health - 5.0)
    else:
        herb.health = min(100.0, herb.health + 0.3)

    if herb.health <= 0.0:
        n = f' "{herb.name}"' if herb.name else ""
        state.event_log.log(
            f"💀 Herbivore{n} starved (age: {_fmt_age(herb.age)})", "dim yellow"
        )
        state.remove(herb)
        state.add(DeadOrganic(herb.x, herb.y))

        return herb_count - 1

    if (
        herb.hunger < Herbivore.HUNGER_THRESHOLD
        and herb.reproduce_cooldown <= 0
        and herb_count < Herbivore.MAX_POP
    ):
        herb_count = _animal_try_reproduce(herb, Herbivore, herb_count, state)

    return herb_count


def _herb_try_eat(
    herb: Herbivore,
    pos_plant: dict[tuple[int, int], Plant],
    state: TickState,
) -> bool:
    """Try to eat an adjacent plant. Returns `True` if successful."""

    nbrs = state.world.neighbours(herb.x, herb.y)
    random.shuffle(nbrs)

    for nx, ny in nbrs:
        plant = pos_plant.get((nx, ny))
        if plant and id(plant) not in state.to_remove:
            state.to_remove.add(id(plant))
            del pos_plant[(nx, ny)]
            state.occupied.discard((nx, ny))
            herb.hunger = max(0.0, herb.hunger - 45.0)

            return True

    return False


def _tick_predators(state: TickState, entities: list[Entity]) -> None:
    """Process every living predator for this tick."""

    pos_herb: dict[tuple[int, int], Herbivore] = {
        (e.x, e.y): e
        for e in entities
        if isinstance(e, Herbivore) and id(e) not in state.to_remove
    }
    pred_count = sum(
        1 for e in entities if isinstance(e, Predator) and id(e) not in state.to_remove
    )

    for pred in entities:
        if not isinstance(pred, Predator) or id(pred) in state.to_remove:
            continue

        pred_count = _tick_single_predator(pred, pos_herb, pred_count, state)


def _tick_single_predator(
    pred: Predator,
    pos_herb: dict[tuple[int, int], Herbivore],
    pred_count: int,
    state: TickState,
) -> int:
    """Process one predator; returns the updated population count."""

    pred.hunger = min(100.0, pred.hunger + Predator.HUNGER_RATE)

    prey = _find_nearest_prey(pred, pos_herb, state.to_remove)

    if prey is not None:
        dist = abs(prey.x - pred.x) + abs(prey.y - pred.y)

        if dist <= 1:
            _predator_eat(pred, prey, pos_herb, state)
        else:
            _predator_move_toward(pred, prey, state)
    else:
        _wander(state.world, pred, state.occupied)

    if pred.hunger >= 100.0:
        pred.health = max(0.0, pred.health - 3.5)
    else:
        pred.health = min(100.0, pred.health + 0.2)

    if pred.health <= 0.0:
        n = f' "{pred.name}"' if pred.name else ""
        state.event_log.log(
            f"💀 Predator{n} died (age: {_fmt_age(pred.age)})", "bold red"
        )
        state.remove(pred)
        state.add(DeadOrganic(pred.x, pred.y))

        return pred_count - 1

    if pred.age == 300 and pred.name is None:
        pred.name = random.choice(_PREDATOR_NAMES)
        state.event_log.log(
            f'🦁 A veteran predator was named "{pred.name}"!', "bold red"
        )

    if (
        pred.hunger < Predator.HUNGER_THRESHOLD
        and pred.reproduce_cooldown <= 0
        and pred_count < Predator.MAX_POP
    ):
        pred_count = _animal_try_reproduce(pred, Predator, pred_count, state)

    return pred_count


def _find_nearest_prey(
    pred: Predator,
    pos_herb: dict[tuple[int, int], Herbivore],
    to_remove: set[int],
) -> Herbivore | None:
    """Return the nearest herbivore within hunt radius or `None`."""

    best: Herbivore | None = None
    best_dist: float = float("inf")

    for (hx, hy), herb in pos_herb.items():
        if id(herb) in to_remove:
            continue

        dist = abs(hx - pred.x) + abs(hy - pred.y)

        if dist <= Predator.HUNT_RADIUS and dist < best_dist:
            best, best_dist = herb, dist

    return best


def _predator_eat(
    pred: Predator,
    prey: Herbivore,
    pos_herb: dict[tuple[int, int], Herbivore],
    state: TickState,
) -> None:
    """Consume *prey*, leaving organic matter and logging the kill."""

    state.to_remove.add(id(prey))
    state.occupied.discard((prey.x, prey.y))
    pos_herb.pop((prey.x, prey.y), None)
    pred.hunger = max(0.0, pred.hunger - 65.0)
    state.add(DeadOrganic(prey.x, prey.y))

    n = f' "{prey.name}"' if prey.name else ""

    state.event_log.log(f"🔴 Predator hunted a herbivore{n}!", "bold red")


def _predator_move_toward(
    pred: Predator,
    target: Herbivore,
    state: TickState,
) -> None:
    """Step predator one tile toward *target*, falling back to wandering."""

    dx = 0 if target.x == pred.x else (1 if target.x > pred.x else -1)
    dy = 0 if target.y == pred.y else (1 if target.y > pred.y else -1)
    candidates = [
        (pred.x + dx, pred.y + dy),
        (pred.x + dx, pred.y),
        (pred.x, pred.y + dy),
    ]

    for tx, ty in candidates:
        nt = state.world.get(tx, ty)
        if nt and not nt.is_water and (tx, ty) not in state.occupied:
            state.move(pred, tx, ty)

            return

    _wander(state.world, pred, state.occupied)


def _animal_try_reproduce(
    animal: Animal,
    cls: type,
    pop_count: int,
    state: TickState,
) -> int:
    """Spawn one offspring on a free adjacent tile if possible.

    Returns the updated population count.
    """

    for nx, ny in state.world.neighbours(animal.x, animal.y):
        nt = state.world.get(nx, ny)

        if nt and not nt.is_water and (nx, ny) not in state.occupied:
            state.add(cls(nx, ny))
            animal.reproduce_cooldown = cls.REPR_COOLDOWN

            kind = "herbivore" if cls is Herbivore else "predator"

            state.event_log.log(f"🐾 A new {kind} was born at ({nx}, {ny})!", "yellow")

            return pop_count + 1

    return pop_count


def _wander(
    world: World,
    animal: Animal,
    occupied: set[tuple[int, int]],
) -> None:
    """Move *animal* one step to a random free adjacent non-water tile."""

    dirs = world.neighbours(animal.x, animal.y)
    random.shuffle(dirs)

    for nx, ny in dirs:
        nt = world.get(nx, ny)

        if nt and not nt.is_water and (nx, ny) not in occupied:
            occupied.discard((animal.x, animal.y))
            animal.x, animal.y = nx, ny
            occupied.add((nx, ny))

            break

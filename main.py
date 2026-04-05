"""main.py—Entry point, game loop, keyboard input."""

from __future__ import annotations

import queue
import random
import select
import shutil
import sys
import termios
import threading
import time
import tty
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.live import Live

from entities import (
    Entity,
    EntityType,
    Herbivore,
    Plant,
    Predator,
    process_tick,
)
from events import EventLog, MilestoneTracker
from persistence import load_game, save_game
from renderer import Renderer
from state import GameState, RenderState
from world import World

SAVE_PATH = Path.home() / ".terrarium" / "save.json"
AUTO_SAVE_INTERVAL = 30


# === Keyboard reader ===

class KeyReader:
    """Background thread that reads single keypresses without blocking the game loop."""

    def __init__(self) -> None:
        self._q: queue.Queue = queue.Queue()
        self._old: Any = None
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        """Put stdin into cbreak mode and start the reader thread."""

        fd = sys.stdin.fileno()
        self._old = termios.tcgetattr(fd)
        tty.setcbreak(fd)
        self._stop_event.clear()

        self._thread = threading.Thread(target=self._loop, daemon=True)

        self._thread.start()


    def stop(self) -> None:
        """Restore the original terminal settings."""

        self._stop_event.set()

        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=0.2)

        self._thread = None

        if self._old is not None:
            try:
                termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, self._old)
            except termios.error:
                pass


    def _loop(self) -> None:
        """Read characters from stdin and enqueue them."""

        while not self._stop_event.is_set():
            try:
                r, _, _ = select.select([sys.stdin], [], [], 0.1)

                if r:
                    ch = sys.stdin.read(1)

                    if ch:
                        self._q.put(ch)
            except (OSError, ValueError):
                break


    def drain(self) -> list[str]:
        """Return and clear all queued keypresses."""

        keys: list[str] = []

        while not self._q.empty():
            try:
                keys.append(self._q.get_nowait())
            except queue.Empty:
                break

        return keys


# === World initialisation helpers ===

def _place_random(
    state: GameState,
    cls: type,
    message: str = "",
    color: str = "white",
) -> bool:
    """Place one entity of *cls* at a random free land tile. Returns False if full."""

    occupied = {(e.x, e.y) for e in state.entities}
    candidates = [
        (x, y)
        for y in range(state.world.height)
        for x in range(state.world.width)
        if not state.world.get(x, y).is_water and (x, y) not in occupied
    ]

    if not candidates:
        return False

    x, y = random.choice(candidates)
    state.entities.append(cls(x, y))

    if message:
        state.event_log.log(message, color)

    return True


def _seed_initial_plants(world: World, entities: list[Entity], n: int) -> None:
    """Scatter *n* seedlings across the most fertile tiles."""

    occupied: set[tuple[int, int]] = set()
    fertile = [
        (x, y)

        for y in range(world.height)
        for x in range(world.width)

        if (
            not world.get(x, y).is_water
            and world.get(x, y).moisture > 35
            and world.get(x, y).nutrients > 35
        )
    ]
    random.shuffle(fertile)

    for x, y in fertile[:n]:
        if (x, y) not in occupied:
            entities.append(Plant(x, y))
            occupied.add((x, y))


def _new_game() -> GameState:
    """Create a brand-new terrarium with default populations."""

    world = World()
    entities: list[Entity] = []
    state = GameState(
        world=world,
        entities=entities,
        elapsed=0,
        event_log=EventLog(),
        milestones=MilestoneTracker(),
    )

    _seed_initial_plants(world, entities, 20)

    for _ in range(3):
        _place_random(state, Herbivore)

    _place_random(state, Predator)

    state.event_log.log("🌱 Terrarium awakened. Watch your world grow…", "bold green")

    return state


# === Game loop helpers ===

def _handle_key(
    key: str,
    state: GameState,
) -> str:
    """Process one keypress. Returns 'quit', 'rain', or '' for other actions."""

    if key in ("q", "Q"):
        return "quit"

    if key in ("r", "R"):
        state.event_log.log("🌧  Rain began to fall!", "bold blue")

        return "rain"

    if key in ("f", "F"):
        cx = random.randint(0, state.world.width - 1)
        cy = random.randint(0, state.world.height - 1)

        state.world.fertilize_region(cx, cy)
        state.event_log.log(f"🌾 Fertilizer spread near ({cx}, {cy})!", "bold yellow")

        return ""

    if key in ("h", "H"):
        cnt = sum(1 for e in state.entities if isinstance(e, Herbivore))

        if cnt < Herbivore.MAX_POP:
            _place_random(
                state,
                Herbivore,
                "🐾 A new herbivore was introduced!",
                "yellow",
            )
        else:
            state.event_log.log("⚠️  Herbivore population is at maximum!", "yellow")

        return ""

    if key in ("p", "P"):
        cnt = sum(1 for e in state.entities if isinstance(e, Predator))

        if cnt < Predator.MAX_POP:
            _place_random(
                state,
                Predator,
                "🔴 A new predator was placed!",
                "bold red",
            )
        else:
            state.event_log.log("⚠️  Predator population is at maximum!", "red")
        return ""

    return ""


def _check_milestones_and_warn(
    state: GameState,
) -> None:
    """Run milestone checks and emit low-population warnings."""

    trees = sum(1 for e in state.entities if e.entity_type == EntityType.TREE)
    herbs = sum(1 for e in state.entities if isinstance(e, Herbivore))
    preds = sum(1 for e in state.entities if isinstance(e, Predator))
    max_pred = max(
        (e.age for e in state.entities if isinstance(e, Predator)),
        default=0,
    )

    state.milestones.check(
        {
            "trees": trees,
            "herbivores": herbs,
            "predators": preds,
            "max_predator_age": max_pred,
            "elapsed": state.elapsed,
        },
        state.event_log,
    )

    if 0 < herbs <= 2 and state.elapsed > 30 and state.elapsed % 15 == 0:
        state.event_log.log("⚠️  Herbivores are going extinct!", "bold yellow")
    if preds == 0 and state.elapsed > 120 and state.elapsed % 30 == 0:
        state.event_log.log("⚠️  Predators have gone extinct!", "bold red")


# === Game loop ===

def run_game(state: GameState) -> GameState:
    """Run the main game loop until the player quits."""

    key_reader = KeyReader()
    key_reader.start()

    rain_ticks = 0
    second_pred_unlocked = state.elapsed >= 120
    renderer = Renderer()
    last_save_elapsed = state.elapsed

    try:
        initial_render = renderer.render(
            RenderState(
                world=state.world,
                entities=state.entities,
                elapsed=state.elapsed,
                event_log=state.event_log,
                milestones=state.milestones,
                rain_active=False,
            )
        )

        with Live(initial_render, screen=True, refresh_per_second=4) as live:
            last_tick = time.monotonic()
            tick_accumulator = 0.0

            while True:
                # process keystrokes accumulated since last frame
                for key in key_reader.drain():
                    action = _handle_key(key, state)

                    if action == "quit":
                        return state
                    if action == "rain":
                        rain_ticks = 20

                # one-second simulation ticks (accumulator-based)
                now = time.monotonic()
                tick_accumulator += now - last_tick
                last_tick = now

                while tick_accumulator >= 1.0:
                    state.elapsed += 1
                    state.event_log.current_tick = state.elapsed

                    if not second_pred_unlocked and state.elapsed >= 120:
                        second_pred_unlocked = True
                        cnt = sum(
                            1 for e in state.entities if isinstance(e, Predator)
                        )

                        if cnt < 2:
                            _place_random(
                                state,
                                Predator,
                                "🔴 A second predator enters the terrarium!",
                                "bold red",
                            )

                    state.world.tick_soil(rain_active=rain_ticks > 0)

                    if rain_ticks > 0:
                        rain_ticks -= 1

                    state.entities = process_tick(
                        state.world,
                        state.entities,
                        state.event_log,
                    )

                    _check_milestones_and_warn(state)

                    if state.elapsed - last_save_elapsed >= AUTO_SAVE_INTERVAL:
                        save_game(
                            SAVE_PATH,
                            state.world,
                            state.entities,
                            state.elapsed,
                            state.event_log,
                            state.milestones,
                        )
                        last_save_elapsed = state.elapsed

                    tick_accumulator -= 1.0

                live.update(
                    renderer.render(
                        RenderState(
                            world=state.world,
                            entities=state.entities,
                            elapsed=state.elapsed,
                            event_log=state.event_log,
                            milestones=state.milestones,
                            rain_active=rain_ticks > 0,
                        )
                    )
                )

                time.sleep(0.05)
    except KeyboardInterrupt:
        return state
    finally:
        key_reader.stop()


# === Entry point ===

def main() -> None:
    """Parse the save file, prompt the user, then launch the game."""

    console = Console()

    cols, rows = shutil.get_terminal_size()

    if cols < 80 or rows < 24:
        console.print(
            "[bold red]Terminal too small.[/bold red] "
            "Please resize to at least [cyan]80×24[/cyan] and try again."
        )
        sys.exit(1)

    state = _new_game()

    if SAVE_PATH.exists():
        console.print(
            "\n[bold green]Terrarium[/bold green] — "
            "a saved world was found.\n"
            "  Resume? ([green]y[/green]/[red]n[/red]): ",
            end="",
        )

        try:
            answer = input().strip().lower()
        except (EOFError, KeyboardInterrupt):
            answer = "n"

        if answer == "y":
            data = load_game(SAVE_PATH)

            if data:
                state = GameState.from_tuple(data)
                console.print(
                    f"[green]Resumed at {state.elapsed}s elapsed.[/green]  Starting in 1s…"
                )

                time.sleep(1.0)
            else:
                console.print(
                    "[yellow]Save file was unreadable; starting fresh.[/yellow]"
                )

                time.sleep(1.0)

    try:
        state = run_game(state)
    finally:
        save_game(
            SAVE_PATH,
            state.world,
            state.entities,
            state.elapsed,
            state.event_log,
            state.milestones,
        )
        console.print("\n[green]Terrarium saved. Goodbye![/green]")


if __name__ == "__main__":
    main()

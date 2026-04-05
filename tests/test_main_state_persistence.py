"""Regression tests for main-loop state persistence."""

from __future__ import annotations

import os

import main
from entities import Entity, Plant
from events import EventLog, MilestoneTracker
from state import GameState
from world import World


def _make_state(
    elapsed: int,
    plant_positions: list[tuple[int, int]],
) -> GameState:
    """Build a minimal, deterministic game-state tuple for tests."""

    world = World(width=20, height=10)
    entities: list[Entity] = [Plant(x, y) for x, y in plant_positions]

    return GameState(world, entities, elapsed, EventLog(), MilestoneTracker())


def test_main_saves_state_returned_by_run_game(monkeypatch, tmp_path) -> None:
    """main() should persist the state returned by run_game()."""

    initial_state = _make_state(elapsed=1, plant_positions=[(1, 1)])
    returned_state = _make_state(elapsed=42, plant_positions=[(1, 1), (2, 2)])

    monkeypatch.setattr(main, "SAVE_PATH", tmp_path / "save.json")
    monkeypatch.setattr(
        main.shutil,
        "get_terminal_size",
        lambda: os.terminal_size((120, 30)),
    )
    monkeypatch.setattr(
        main,
        "_new_game",
        lambda: initial_state,
    )
    monkeypatch.setattr(
        main,
        "run_game",
        lambda *_: returned_state,
    )

    saved: dict[str, tuple] = {}

    def _fake_save(*args) -> None:
        saved["args"] = args

    monkeypatch.setattr(main, "save_game", _fake_save)

    main.main()

    assert "args" in saved

    saved_args = saved["args"]

    assert saved_args[0] == tmp_path / "save.json"
    assert saved_args[1] is returned_state.world
    assert saved_args[2] is returned_state.entities
    assert saved_args[3] == returned_state.elapsed
    assert saved_args[4] is returned_state.event_log
    assert saved_args[5] is returned_state.milestones


class _FakeKeyReader:
    def start(self) -> None:
        """Start fake reader."""

    def stop(self) -> None:
        """Stop fake reader."""

    def drain(self) -> list[str]:
        """Return no queued keys."""

        return []


class _FakeRenderer:  # pylint: disable=too-few-public-methods
    """Minimal renderer test double."""

    def render(self, *_args, **_kwargs):
        """Return a placeholder frame object."""

        return "frame"


class _FakeLive:
    def __init__(self, *_args, **_kwargs) -> None:
        """Construct fake live context manager."""

    def __enter__(self):
        """Enter context and return self."""

        return self

    def __exit__(self, *_args) -> bool:
        """Exit context without suppressing exceptions."""

        return False

    def update(self, *_args, **_kwargs) -> None:
        """Accept updates and do nothing."""


def test_run_game_returns_latest_state_on_keyboard_interrupt(monkeypatch) -> None:
    """run_game() should return the current state when interrupted."""

    state = GameState(
        world=World(width=20, height=10),
        entities=[Plant(1, 1)],
        elapsed=0,
        event_log=EventLog(),
        milestones=MilestoneTracker(),
    )

    monkeypatch.setattr(main, "KeyReader", _FakeKeyReader)
    monkeypatch.setattr(main, "Renderer", _FakeRenderer)
    monkeypatch.setattr(main, "Live", _FakeLive)
    monkeypatch.setattr(main, "process_tick", lambda _w, e, _log: e)

    monotonic_values = iter([0.0, 1.1])

    def _fake_monotonic() -> float:
        return next(monotonic_values, 1.1)

    monkeypatch.setattr(main.time, "monotonic", _fake_monotonic)

    def _raise_interrupt(_seconds: float) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(main.time, "sleep", _raise_interrupt)

    returned_state = main.run_game(state)

    assert returned_state.elapsed == 1


def test_run_game_catches_up_multiple_ticks_when_frame_lags(monkeypatch) -> None:
    """run_game() should process multiple ticks when accumulated time exceeds 1s."""

    state = GameState(
        world=World(width=20, height=10),
        entities=[Plant(1, 1)],
        elapsed=0,
        event_log=EventLog(),
        milestones=MilestoneTracker(),
    )

    monkeypatch.setattr(main, "KeyReader", _FakeKeyReader)
    monkeypatch.setattr(main, "Renderer", _FakeRenderer)
    monkeypatch.setattr(main, "Live", _FakeLive)
    monkeypatch.setattr(main, "process_tick", lambda _w, e, _log: e)

    monotonic_values = iter([0.0, 3.3])

    def _fake_monotonic() -> float:
        return next(monotonic_values, 3.3)

    monkeypatch.setattr(main.time, "monotonic", _fake_monotonic)

    def _raise_interrupt(_seconds: float) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(main.time, "sleep", _raise_interrupt)

    returned_state = main.run_game(state)

    assert returned_state.elapsed == 3

"""Event log and milestone tracker behavior tests."""

from __future__ import annotations

from events import EventLog, MilestoneTracker


def test_event_log_keeps_only_last_50_entries() -> None:
    """EventLog should keep a bounded ring buffer of recent entries."""

    log = EventLog()

    for tick in range(55):
        log.current_tick = tick
        log.log(f"event-{tick}")

    assert len(log.events) == 50
    assert log.events[0].message == "event-5"
    assert log.events[-1].message == "event-54"


def test_event_log_recent_returns_latest_entries_in_order() -> None:
    """recent(n) should return the newest n entries in chronological order."""

    log = EventLog()

    for idx in range(6):
        log.log(f"e-{idx}")

    recent = log.recent(3)

    assert [event.message for event in recent] == ["e-3", "e-4", "e-5"]


def test_event_log_to_dict_includes_only_latest_20() -> None:
    """Serialized event payload should include only the latest 20 events."""

    log = EventLog()

    for idx in range(25):
        log.log(f"e-{idx}")

    data = log.to_dict()

    assert len(data["events"]) == 20
    assert data["events"][0]["msg"] == "e-5"
    assert data["events"][-1]["msg"] == "e-24"


def test_milestones_fire_once_even_on_repeated_checks() -> None:
    """One-shot milestones should not emit duplicate events."""

    tracker = MilestoneTracker()
    log = EventLog()
    state = {
        "trees": 1,
        "herbivores": 13,
        "predators": 1,
        "max_predator_age": 301,
        "elapsed": 180,
    }

    tracker.check(state, log)
    first_len = len(log.events)
    tracker.check(state, log)

    assert len(log.events) == first_len
    assert "first_tree" in tracker.achieved
    assert "population_boom" in tracker.achieved
    assert "apex_predator" in tracker.achieved


def test_ecosystem_balance_requires_60_consecutive_ticks() -> None:
    """Balance milestone should require uninterrupted coexistence streak."""

    tracker = MilestoneTracker()
    log = EventLog()
    balanced = {
        "trees": 2,
        "herbivores": 2,
        "predators": 1,
        "max_predator_age": 0,
        "elapsed": 10,
    }
    unbalanced = {
        "trees": 2,
        "herbivores": 0,
        "predators": 1,
        "max_predator_age": 0,
        "elapsed": 11,
    }

    for _ in range(59):
        tracker.check(balanced, log)

    assert "ecosystem_balanced" not in tracker.achieved

    tracker.check(unbalanced, log)

    for _ in range(60):
        tracker.check(balanced, log)

    assert "ecosystem_balanced" in tracker.achieved
    assert any("coexist" in event.message for event in log.events)

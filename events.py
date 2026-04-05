"""events.py—Event log and milestone tracking."""

from dataclasses import dataclass

# === Event log ===

@dataclass
class Event:
    """A single timestamped log entry."""

    message: str
    color: str
    tick: int

    def to_dict(self) -> dict:
        """Serialise to a JSON-compatible dict."""

        return {"msg": self.message, "color": self.color, "tick": self.tick}

    @classmethod
    def from_dict(cls, d: dict) -> "Event":
        """Reconstruct from a saved dict."""

        return cls(message=d["msg"], color=d["color"], tick=d.get("tick", 0))


class EventLog:
    """Ring-buffer of recent game events shown in the sidebar."""

    _KEEP = 50
    MAX_DISPLAY = 8

    def __init__(self) -> None:
        self.events: list[Event] = []
        self.current_tick: int = 0

    def log(self, message: str, color: str = "white") -> None:
        """Append a new event, trimming the buffer if needed."""

        self.events.append(Event(message, color, self.current_tick))

        if len(self.events) > self._KEEP:
            self.events = self.events[-self._KEEP :]


    def recent(self, n: int = MAX_DISPLAY) -> list[Event]:
        """Return the *n* most recent events."""

        return self.events[-n:]


    def to_dict(self) -> dict:
        """Serialise the most recent events."""

        return {"events": [e.to_dict() for e in self.events[-20:]]}


    @classmethod
    def from_dict(cls, d: dict) -> "EventLog":
        """Reconstruct from a saved dict."""

        obj = cls()
        obj.events = [Event.from_dict(e) for e in d.get("events", [])]

        return obj


# === Milestones ===

MILESTONE_NAMES: dict[str, str] = {
    "first_tree": "First Tree Matured",
    "ecosystem_balanced": "Ecosystem Balanced",
    "population_boom": "Population Boom",
    "apex_predator": "Apex Predator",
    "old_growth_forest": "Old Growth Forest",
    "great_dying": "The Great Dying",
}


class MilestoneTracker:
    """Tracks which one-shot milestones have been achieved."""

    def __init__(self) -> None:
        self.achieved: set[str] = set()
        self._balanced_ticks: int = 0

    def check(self, state: dict, event_log: EventLog) -> None:
        """Fire any newly reached milestones based on the current world state."""

        trees = state.get("trees", 0)
        herbs = state.get("herbivores", 0)
        preds = state.get("predators", 0)
        max_pred = state.get("max_predator_age", 0)
        elapsed = state.get("elapsed", 0)

        def _fire(key: str, msg: str, color: str) -> None:
            if key not in self.achieved:
                self.achieved.add(key)
                event_log.log(msg, color)

        if trees >= 1:
            _fire("first_tree", "🌳 First tree reached full maturity!", "bold green")

        if trees > 10:
            _fire(
                "old_growth_forest",
                "🌲 Old growth forest established (10+ trees)!",
                "bold green",
            )

        if herbs > 12:
            _fire(
                "population_boom",
                "🐾 Population boom! Herbivores exceed 12!",
                "bold yellow",
            )

        # ecosystem balance: all three species must coexist for 60 consecutive ticks
        if trees > 0 and herbs > 0 and preds > 0:
            self._balanced_ticks += 1
        else:
            self._balanced_ticks = 0

        if self._balanced_ticks >= 60:
            _fire(
                "ecosystem_balanced",
                "⚖️  All three species coexist in harmony!",
                "bold cyan",
            )

        if max_pred >= 300:
            _fire(
                "apex_predator",
                "🔴 Apex predator! A predator survived 5+ minutes!",
                "bold red",
            )

        if herbs == 0 and elapsed > 60:
            _fire(
                "great_dying",
                "💀 The Great Dying—herbivores are extinct!",
                "bold red",
            )


    def to_dict(self) -> dict:
        """Serialise achieved milestones and the balance counter."""

        return {"achieved": list(self.achieved), "bt": self._balanced_ticks}


    @classmethod
    def from_dict(cls, d: dict) -> "MilestoneTracker":
        """Reconstruct from a saved dict."""

        obj = cls()
        obj.achieved = set(d.get("achieved", []))
        obj._balanced_ticks = d.get("bt", 0)  # pylint: disable=protected-access

        return obj

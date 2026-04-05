"""Renderer tests for milestone ordering."""

from __future__ import annotations

from events import EventLog, MilestoneTracker
from renderer import Renderer
from state import RenderState
from world import World


def test_sidebar_renders_milestones_in_stable_display_order() -> None:
    """Milestones should render in configured order, not set iteration order."""

    milestones = MilestoneTracker()
    milestones.achieved = {
        "apex_predator",
        "first_tree",
        "population_boom",
    }

    state = RenderState(
        world=World(width=20, height=10),
        entities=[],
        elapsed=0,
        event_log=EventLog(),
        milestones=milestones,
        rain_active=False,
    )

    layout = Renderer().render(state)
    sidebar_panel = layout["sidebar"].renderable
    sidebar_text = sidebar_panel.renderable.plain

    first_idx = sidebar_text.find("First Tree Matured")
    boom_idx = sidebar_text.find("Population Boom")
    apex_idx = sidebar_text.find("Apex Predator")

    assert first_idx != -1
    assert boom_idx != -1
    assert apex_idx != -1
    assert first_idx < boom_idx < apex_idx

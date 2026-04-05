"""renderer.py—Rich layout, viewport drawing, and sidebar."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.layout import Layout
from rich.panel import Panel
from rich.text import Text

from entities import RENDER, Animal, EntityType, Herbivore, Predator
from events import MILESTONE_NAMES

if TYPE_CHECKING:
    from entities import Entity
    from events import EventLog, MilestoneTracker
    from world import World


class Renderer:  # pylint: disable=too-few-public-methods
    """Builds the full Rich Layout for one frame of the game."""

    # public entry point
    def render(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        world: World,
        entities: list[Entity],
        elapsed: int,
        event_log: EventLog,
        milestones: MilestoneTracker,
        rain_active: bool,
    ) -> Layout:
        """Build and return the full-screen Rich Layout for this frame."""

        pos_map: dict[tuple[int, int], Entity] = {(e.x, e.y): e for e in entities}

        layout = Layout()
        layout.split_row(
            Layout(name="viewport", ratio=7),
            Layout(name="sidebar", ratio=3),
        )
        layout["viewport"].update(
            Panel(
                self._render_grid(world, pos_map, rain_active),
                title="[bold green] Terrarium [/bold green]",
                border_style="green",
                padding=(0, 0),
            )
        )
        layout["sidebar"].update(
            Panel(
                self._render_sidebar(
                    entities, elapsed, event_log, milestones, rain_active
                ),
                title="[bold cyan] Status [/bold cyan]",
                border_style="cyan",
                padding=(0, 1),
            )
        )

        return layout

    # grid viewport
    def _render_grid(
        self,
        world: World,
        pos_map: dict[tuple[int, int], Entity],
        rain_active: bool,
    ) -> Text:
        text = Text(no_wrap=True, overflow="crop")

        for y in range(world.height):
            for x in range(world.width):
                tile = world.get(x, y)
                pos = (x, y)

                if pos in pos_map:
                    e = pos_map[pos]
                    sym, style = RENDER[e.entity_type]

                    # dim dying animals
                    if isinstance(e, Animal) and e.health < 30:
                        style = "dim " + style

                    text.append(sym, style=style)
                elif tile.is_water:
                    # animate water slightly with rain
                    sym = "≈" if rain_active else "~"
                    text.append(sym, style="bold blue" if rain_active else "blue")
                else:
                    # colour soil: richer green tint when fertile and moist
                    if tile.moisture > 65 and tile.nutrients > 55:
                        text.append("·", style="dim green")
                    elif tile.moisture < 20:
                        text.append("·", style="dim red")
                    else:
                        text.append("·", style="dim white")

            if y < world.height - 1:
                text.append("\n")

        return text

    # sidebar
    def _render_sidebar(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        entities: list[Entity],
        elapsed: int,
        event_log: EventLog,
        milestones: MilestoneTracker,
        rain_active: bool,
    ) -> Text:
        text = Text()
        text.append_text(self._render_time_section(elapsed, rain_active))
        text.append_text(self._render_population_section(entities))
        text.append_text(self._render_notable_section(entities))
        text.append_text(self._render_events_section(event_log))
        text.append_text(self._render_milestones_section(milestones))
        text.append_text(self._render_legend_controls_section())

        return text

    def _render_time_section(self, elapsed: int, rain_active: bool) -> Text:
        """Render the elapsed-time and rain-status section."""

        text = Text()

        h, rem = divmod(elapsed, 3600)
        m, s = divmod(rem, 60)
        ts = f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"
        text.append(f"⏱  {ts}\n", style="bold cyan")

        if rain_active:
            text.append("🌧  Rain is falling!\n", style="bold blue")

        text.append("\n")

        return text

    def _render_population_section(self, entities: list[Entity]) -> Text:
        """Render population counters for plants and animals."""

        text = Text()

        seedlings = sum(1 for e in entities if e.entity_type == EntityType.SEEDLING)
        bushes = sum(1 for e in entities if e.entity_type == EntityType.BUSH)
        trees = sum(1 for e in entities if e.entity_type == EntityType.TREE)
        herbs = sum(1 for e in entities if isinstance(e, Herbivore))
        preds = sum(1 for e in entities if isinstance(e, Predator))

        text.append("Population\n", style="bold white")
        text.append(f"  , Seedlings  {seedlings:3d}\n", style="green")
        text.append(f"  ♣ Bushes     {bushes:3d}\n", style="bright_green")
        text.append(f"  ↑ Trees      {trees:3d}\n", style="bold green")
        text.append(f"  o Herbivores {herbs:3d}\n", style="yellow")
        text.append(f"  @ Predators  {preds:3d}\n", style="red")
        text.append("\n")

        return text

    def _render_notable_section(self, entities: list[Entity]) -> Text:
        """Render recently named animals."""

        text = Text()

        named = [e for e in entities if isinstance(e, Animal) and e.name]

        if named:
            text.append("Notable\n", style="bold white")

            for a in named[-3:]:
                sym, style = RENDER[a.entity_type]
                m2, s2 = divmod(a.age, 60)
                text.append(f"  {sym} {a.name} ({m2}m {s2}s)\n", style=style)

            text.append("\n")

        return text

    def _render_events_section(self, event_log: EventLog) -> Text:
        """Render recent event messages."""

        text = Text()

        text.append("Recent Events\n", style="bold white")
        events = event_log.recent(8)

        if events:
            for ev in events:
                msg = ev.message

                if len(msg) > 32:
                    msg = msg[:30] + "…"

                text.append(f"  {msg}\n", style=ev.color)
        else:
            text.append("  —\n", style="dim")

        text.append("\n")

        return text

    def _render_milestones_section(self, milestones: MilestoneTracker) -> Text:
        """Render achieved milestones."""

        text = Text()

        if milestones.achieved:
            text.append("Milestones\n", style="bold white")

            for key in milestones.achieved:
                name = MILESTONE_NAMES.get(key, key)
                text.append(f"  ✓ {name}\n", style="gold1")

            text.append("\n")

        return text

    def _render_legend_controls_section(self) -> Text:
        """Render the legend and controls sections."""

        text = Text()

        text.append("Legend\n", style="bold white")
        text.append("  ,  seedling  ♣  bush\n", style="dim")
        text.append("  ↑  tree      o  herb\n", style="dim")
        text.append("  @  predator  %  organic\n", style="dim")
        text.append("  ~  water     ·  soil\n", style="dim")
        text.append("\n")

        text.append("Controls\n", style="bold white")
        text.append("  [r] rain     [f] fertilize\n", style="dim")
        text.append("  [h] herbivore [p] predator\n", style="dim")
        text.append("  [q] quit\n", style="dim")

        return text

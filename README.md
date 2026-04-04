# Terrarium

![Python](https://img.shields.io/badge/python-3.11+-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Platform](https://img.shields.io/badge/platform-linux%20|%20macos%20|%20windows-lightgrey)

[![Conventional Commits](https://img.shields.io/badge/Conventional%20Commits-1.0.0-%23FE5196?logo=conventionalcommits&logoColor=white)](https://conventionalcommits.org)

A living ASCII ecosystem that runs in your terminal. Watch plants spread,
herbivores graze and predators hunt—all while you leave your terminal open.

```
┌─────────────────────────────────────────────────────── Terrarium ────┬─── Status ───┐
│ ··,·,·~~~~~·↑·↑··,·····,···,·o····↑····················,··,·,······ │ ⏱  04:22     │
│ ·,·♣·~~~~~·,·↑↑·,·····,·,·,····@·↑·····,·,·,···,···,·,·,·,·,····· │              │
│ ···,·~·~~~~··,↑·,·······,·····,·↑·,·,·,·,·,·····o··,·,·,·,·,···,· │ Population   │
│ ···,·········,·,·,·,·,·,···,·,·,·,·····,·,·,·,·,·,·,·,·,·,·,·,··· │ , Seedlings 8│
│ ·o·♣·,·,·♣·↑·,·♣·,·,·,·,·,·,·,·,·,·,·o·····,·,·,·♣·,·,·,·,·,·,· │ ♣ Bushes    4│
└──────────────────────────────────────────────────────────────────────┴──────────────┘
```

## Overview

Terrarium is an idle simulation game. The player watches—and occasionally nudges—
a self-sustaining world of plants, herbivores and predators. The core fantasy is:

> *"I grew something beautiful just by leaving my terminal open."*

## Requirements

- Python 3.11+
- [`rich`](https://github.com/Textualize/rich)
- A terminal at least **80 × 24** characters (120 × 30+ recommended)

## Installation

```bash
git clone https://github.com/minoangelo/terrarium
cd terrarium
pip install -r requirements.txt
python main.py
```

## Controls

| Key | Action |
|-----|--------|
| `r` | Drop rain: boosts all moisture for 20 seconds |
| `f` | Fertilize a random region: boosts nutrients |
| `h` | Introduce a new herbivore |
| `p` | Place a new predator (if below the cap) |
| `q` | Quit and save |

The game is designed to be satisfying to watch without touching the keyboard.

## How It Works

### The Grid

The world is a 2-D tile grid (up to 60 × 24, scaled to your terminal). Each tile
tracks **moisture** and **nutrients** (0–100) that slowly regenerate over time.
Static water tiles (~) boost nearby moisture. Dead organic matter (%) fertilises
the soil as it decays.

### Plants

| Symbol | Name | Behaviour |
|--------|------|-----------|
| `,` | Seedling | Grows into a bush after ~30 s if soil is fertile |
| `♣` | Bush | Grows into a tree after ~120 s; spreads seeds more aggressively |
| `↑` | Tree | Fully mature; highest seed-spread rate |

Plants die when soil nutrients reach zero, leaving organic matter behind.

### Animals

| Symbol | Name | Cap | Behaviour |
|--------|------|-----|-----------|
| `o` | Herbivore | 20 | Wanders and eats adjacent plants; reproduces when well-fed |
| `@` | Predator | 5 | Hunts the nearest herbivore within 5 tiles; second one unlocks at 2 min |

Both animals starve if hunger reaches 100—health then decays until death, leaving
organic matter.

### Milestones

| Milestone | Trigger |
|-----------|---------|
| First Tree Matured | A tree reaches full growth |
| Old Growth Forest | More than 10 trees exist simultaneously |
| Population Boom | Herbivore count exceeds 12 |
| Ecosystem Balanced | All three species co-exist for 60 consecutive seconds |
| Apex Predator | A predator survives 5+ minutes (it earns a name) |
| The Great Dying | All herbivores go extinct |

## Save Files

The game auto-saves every 30 seconds to `~/.terrarium/save.json`. On next launch
you will be asked whether to resume. Quitting with `q` always saves immediately.

## Project Structure

```
terrarium/
├── main.py          # Entry point, game loop, keyboard input
├── world.py         # Grid, Tile, and soil simulation
├── entities.py      # Entity classes and per-tick simulation logic
├── renderer.py      # Rich layout, viewport drawing, sidebar
├── events.py        # Event log and milestone tracking
├── persistence.py   # JSON save/load
└── requirements.txt
```

## Contributing

Contributions are welcome. This project currently uses a lightweight workflow.

### 1) Set up locally

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 2) Run and validate

```bash
# run the app
python main.py

# basic syntax/import check
python -m compileall .

# lint (primary)
pylint main.py entities.py events.py persistence.py renderer.py world.py

# optional fast lint
ruff check .
```

### 3) Tests

There is no committed test suite yet. If you add tests, use `pytest`.

```bash
# run all tests
pytest

# run a single test file
pytest tests/test_entities.py

# run a single test case
pytest tests/test_entities.py::test_predator_hunts_nearest

# run by expression
pytest -k "predator and not slow"
```

### 4) Commit and PR style

- Follow [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/)
  (for example: `feat: ...`, `fix: ...`, `docs: ...`).
- Keep changes focused and small when possible.
- In your PR description, include:
  - what changed,
  - why it changed,
  - which validation commands you ran.

### 5) Scope guidance

- Keep architecture boundaries intact:
  - `world.py` for terrain/soil rules,
  - `entities.py` for simulation behavior,
  - `renderer.py` for presentation,
  - `persistence.py` for save/load,
  - `main.py` for orchestration and input loop.
- Avoid blocking I/O in the main loop.
- Preserve save compatibility where practical.

## License

See [LICENSE.md](LICENSE.md).

## Contact

- Carmine (Mino) Siena, [dev@mino-siena.de](mailto:dev@mino-siena.de)

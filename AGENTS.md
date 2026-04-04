# AGENTS.md

This file is guidance for coding agents working in this repository.
It captures how to run, validate, and modify the Terrarium codebase safely.

## Project Snapshot

- Language: Python (3.11+)
- Runtime UI: terminal app using `rich`
- Entry point: `main.py`
- Core modules: `world.py`, `entities.py`, `renderer.py`, `events.py`, `persistence.py`
- Dependency management: `requirements.txt` only (no pyproject/setup.cfg at the moment)

## Environment Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Build / Run / Lint / Test Commands

There is no formal build system and no committed test suite yet.
Use the following commands when developing.

### Run the app

```bash
python main.py
```

### Basic validation (syntax/import check)

```bash
python -m compileall .
```

### Linting

The codebase contains inline `pylint` disables, so `pylint` is the primary implied linter.
`ruff` is also reasonable for quick static checks, but is not configured in-repo.

```bash
# if needed
pip install pylint ruff

# lint all project modules
pylint main.py entities.py events.py persistence.py renderer.py world.py

# optional fast lint pass
ruff check .
```

### Tests

Tests are present under `tests/`.
Use `pytest` and keep extending coverage as features and fixes are added.

```bash
# if needed
pip install pytest

# run all tests
pytest

# run a single test file
pytest tests/test_entities.py

# run a single test case
pytest tests/test_entities.py::test_predator_hunts_nearest

# run tests by expression
pytest -k "predator and not slow"
```

## Save/Runtime Notes

- Save file path: `~/.terrarium/save.json`
- App auto-saves every 30 seconds and on quit.
- Terminal size requirement is enforced in `main.py` (minimum 80x24).
- Rendering is time-based; avoid adding blocking I/O in the main loop.

## Repository-Specific Code Style

Follow existing style in current modules rather than introducing a new framework.

### Imports

- Use import groups in this order:
  1) standard library
  2) third-party (`rich`)
  3) local modules (`entities`, `world`, etc.)
- Prefer explicit imports over wildcard imports.
- Keep one import per line when practical.
- Use `TYPE_CHECKING` blocks for type-only imports that would otherwise cause cycles.
- Keep `from __future__ import annotations` at top where already used.

### Formatting and layout

- Follow PEP 8 conventions and current file style.
- Use 4 spaces for indentation.
- Keep functions focused; extract helpers for simulation sub-steps.
- Preserve section markers used in files (for example `# === Tick logic ===`).
- Prefer short, clear docstrings on classes/functions.
- Avoid adding comments unless logic is non-obvious.

### Types and data modeling

- Use type hints throughout (this codebase is already strongly typed).
- Prefer concrete types like `list[Entity]`, `dict[str, str]`, `set[tuple[int, int]]`.
- Use `X | None` instead of `Optional[X]`.
- Use dataclasses for simple state containers (`Tile`, `Event`, `TickState`).
- Keep enum-driven modeling (`EntityType`) for gameplay categories.

### Naming conventions

- `snake_case` for functions, methods, variables, and module-level helpers.
- `PascalCase` for classes.
- `UPPER_SNAKE_CASE` for constants.
- Prefix non-public helpers with `_`.
- Prefer descriptive names tied to simulation concepts (`tick_soil`, `reproduce_cooldown`).

### Error handling

- Use targeted exception handling, not bare `except`.
- For persistence/parsing, fail safely and return `None` on invalid/corrupt save data.
- Keep gameplay loop resilient: catch expected terminal/input failures and continue gracefully.
- Do not swallow exceptions silently unless there is a clear recovery path.

### Control flow and state updates

- Prefer guard clauses (`continue`/early return) to reduce nesting.
- Keep one-tick logic deterministic and partitioned by entity type.
- When mutating shared per-tick state, update occupancy sets consistently.
- Preserve existing atomic save behavior (`.tmp` write then replace).

### UI/rendering conventions

- Renderer should remain presentation-only; avoid game-rule mutations in `renderer.py`.
- Keep symbol/color mappings centralized in `entities.RENDER`.
- Truncate or bound sidebar content to avoid overflow.
- Ensure terminal compatibility for Unicode symbols already in use.

## Architecture Guardrails

- `world.py`: terrain grid, soil rules, neighborhood math.
- `entities.py`: entity models + simulation tick behavior.
- `events.py`: event ring buffer + milestone tracking.
- `renderer.py`: Rich layout and text generation only.
- `persistence.py`: JSON serialization/deserialization only.
- `main.py`: orchestration, input handling, autosave cadence, loop timing.

Keep responsibilities separated when adding features.

## Preferred Change Workflow for Agents

1. Read relevant module(s) fully before editing.
2. Make minimal, local changes consistent with current architecture.
3. Run `python -m compileall .` after edits.
4. Run lint/tests if tools are available for your environment.
5. In your final report, include:
   - files changed,
   - validation commands run,
   - any commands you could not run.

## Cursor / Copilot Rules Check

- `.cursorrules`: not found
- `.cursor/rules/`: not found
- `.github/copilot-instructions.md`: not found

No additional editor-specific instruction files are currently present.

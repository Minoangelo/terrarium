# AGENTS.md

Guidance for coding agents working in this repository.
Use this file to make safe, minimal, architecture-consistent changes.

## Repository Snapshot
- Project: Terrarium (terminal ecosystem simulation)
- Language: Python 3.11+
- UI/runtime: terminal app with `rich`
- Package management: `requirements.txt` (no `pyproject.toml`)
- Entry point: `main.py`
- Core modules: `world.py`, `entities.py`, `events.py`, `renderer.py`, `persistence.py`, `state.py`
- Test suite: `pytest` tests under `tests/`

## Editor Rule Files (Cursor / Copilot)
Checked paths and current status:
- `.cursorrules`: not found
- `.cursor/rules/`: not found
- `.github/copilot-instructions.md`: not found

If any of the files above are added later, treat them as higher-priority local guidance.

## Environment Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Build / Run / Lint / Test Commands
There is no formal build step. Use compile/lint/test as validation.

### Run app
```bash
python main.py
```

### Syntax/import sanity check
```bash
python -m compileall .
```

### Lint
Primary lint command (matches repo style and existing inline disables):
```bash
pylint main.py entities.py events.py persistence.py renderer.py state.py world.py
```

Lint tests when needed:
```bash
PYTHONPATH=. pylint tests/test_entities.py
```

Optional fast lint pass:
```bash
ruff check .
```

### Tests (pytest)
Run full suite:
```bash
pytest
```

Run a single test file:
```bash
pytest tests/test_entities.py
```

Run a single test function (recommended during iteration):
```bash
pytest tests/test_entities.py::test_predator_moves_toward_nearest_prey
```

Run tests by expression:
```bash
pytest -k "predator and not slow"
```

## Runtime and Persistence Notes
- Save path: `~/.terrarium/save.json`
- Auto-save cadence: every 30 seconds plus on quit
- Save writes are atomic (`.tmp` then replace)
- Minimum terminal size enforced in `main.py`: 80x24
- Avoid blocking I/O in the main loop

## Architecture Guardrails
- `world.py`: grid, tiles, neighborhood math, soil simulation
- `entities.py`: entity models and per-tick behavior rules
- `events.py`: event buffer and milestone logic
- `renderer.py`: presentation only (Rich layout/text)
- `persistence.py`: JSON serialization/deserialization only
- `state.py`: shared state dataclasses
- `main.py`: orchestration, input, autosave, loop timing

Keep responsibilities separated.
Do not move gameplay rules into `renderer.py`.

## Code Style Guidelines
Follow existing file-local style first; keep changes narrow and consistent.

### Imports
- Group imports as: standard library, third-party, local
- Keep imports explicit; avoid wildcard imports
- Keep `from __future__ import annotations` at the top where already present
- Use `TYPE_CHECKING` for type-only imports that may introduce cycles

### Formatting and layout
- Follow PEP 8 and existing spacing/line-break patterns
- Use 4-space indentation
- Prefer small focused helpers over deep nesting
- Preserve section markers like `# === Tick logic ===`
- Add comments only for non-obvious logic
- Keep docstrings concise and action-oriented

### Types and data modeling
- Keep type hints on all new or modified code
- Prefer built-in generics (`list[T]`, `dict[K, V]`, `set[T]`)
- Use `X | None` instead of `Optional[X]`
- Use dataclasses for simple state containers
- Keep enum-based modeling for entity categories (`EntityType`)

### Naming conventions
- `snake_case`: functions, methods, variables, module helpers
- `PascalCase`: classes
- `UPPER_SNAKE_CASE`: constants
- Prefix internal helpers with `_` when non-public
- Use simulation-domain names (`tick_soil`, `spread_cooldown`, `occupied`)

### Control flow and state updates
- Prefer guard clauses and early returns to reduce nesting
- Keep tick behavior deterministic and partitioned by entity type
- When mutating occupancy/collections during ticks, keep sets/lists in sync
- Avoid hidden cross-module side effects

### Error handling
- Catch specific exceptions; never use bare `except`
- For load/parse paths, fail safely and return `None` on invalid data
- Keep game loop resilient to expected terminal/input failures
- Do not silently ignore exceptions unless recovery behavior is explicit

### Testing conventions
- Add or update tests in `tests/` for behavior changes
- Prefer targeted test runs while iterating, then run full `pytest`
- For bug fixes, include at least one regression assertion

## Agent Workflow
1. Read relevant modules fully before editing.
2. Make minimal local changes that respect architecture boundaries.
3. Run `python -m compileall .` after edits.
4. Run targeted tests, then full `pytest` if feasible.
5. Run lint commands when available.
6. Report files changed, commands run, and any commands not run.

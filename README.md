# pnfl-profilewriter

Copies selected fields between Front Page Sports Football Pro '98 coaching profiles (`.prf`).

Sits on top of [`pnfl-profile`](../pnfl-profile) (PNFL rule layer over [`fbpro98-profile`](../fbpro98-profile)) and exposes the `pnfl copy-profile` umbrella subcommand. See [ARCHITECTURE.md](ARCHITECTURE.md) and [pnfl-docs/Design/profile-architecture.md](../pnfl-docs/Design/profile-architecture.md).

## Setup

```powershell
py -3.13 -m venv .venv
.venv\Scripts\activate
py -m pip install -e ..\fbpro98-profile
py -m pip install -e ..\pnfl-profile
py -m pip install -e ".[dev]"
```

## Usage

```powershell
pnfl copy-profile SOURCE.prf TARGET.prf [FLAGS]
```

Both profiles must be the same type (offense → offense, defense → defense). The target is updated in place. PNFL rule violations on the result are surfaced as `PnflRuleWarning`; the target is written regardless.

### Copy options

| Flag | Copies |
|---|---|
| `--stop-clock` | Stop-clock flag for every situation (2520 entries). |
| `--sub-percent` | Every position group's substitution percentages. |
| `--field-goal-range` | The field-goal range. |
| `--fourth-down` | Every 4th-down situation (stop_clock + category weights). |
| `--goal-line` | Every goal-line situation, inside DEF 5 or OFF 5 (stop_clock + category weights). |

At least one copy flag is required. Multiple may be combined.

## Testing

```powershell
pytest
```

## Building a Release

Ships these artifacts to the umbrella bundle:

- Python wheel (built by `pnfl/scripts/build_release.py`)

Distributed as part of the [`pnfl`](../pnfl) umbrella CLI.

# pnfl-profilewriter — Architecture

PNFL-aware CLI that copies selected fields from a source `.prf` into a target `.prf`. See [pnfl-docs/Design/profile-architecture.md](../pnfl-docs/Design/profile-architecture.md) for system context and [profile-validation.md](../pnfl-docs/Design/profile-validation.md) for validation ownership.

## Module layout

```
src/pnfl_profilewriter/
├── copy_cli.py        # argparse, main()
├── main.py            # copy_profile() orchestrator
└── profile_writer.py  # ProfileWriter, ProfileTypeMismatchError
```

## Flow

1. `copy_cli.main` installs `warnings.simplefilter("always", PnflRuleWarning)`, parses args.
2. `main.copy_profile` builds a `ProfileWriter(source, target)` and calls `apply(**copy_flags) -> PnflProfile`.
3. `ProfileWriter.apply` loads both via `PnflProfile.from_file`, checks `profile_type` match (else `ProfileTypeMismatchError`), and applies each requested copy operation to the target's `Profile` via `dataclasses.replace`.
4. CLI calls `pp.save(target_path)` — writes the file, emits one `PnflRuleWarning` per PNFL aggregate-rule violation, returns the violation tuple. PNFL violations **do not block the write**.

## Copy options

Each is independent and may be combined. All require matching `profile_type`.

| Flag | Copies | Scope |
|---|---|---|
| `--stop-clock` | `stop_clock` boolean | Every situation (2520). |
| `--sub-percent` | `SubstitutionSettings` | Whole profile (one record). |
| `--field-goal-range` | `field_goal_range` int | Whole profile (one value). |
| `--fourth-down` | `stop_clock` + `category_weights` | Situations where `down == Fourth`. |
| `--goal-line` | `stop_clock` + `category_weights` | Situations where `field_position ∈ {INSIDE_DEF_5, INSIDE_OFF_5}`. |

`--fourth-down` and `--goal-line` copy the **entire** affected situation. Overlapping with `--stop-clock` is harmless because all per-situation copies are idempotent at the byte level; the whole-situation copy supersedes the stop-clock-only copy on situations matching the whole-situation predicate.

## Errors

CLI-level (SystemExit): `source_path` and `target_path` required; at least one copy flag required.

`ProfileTypeMismatchError` (`ValueError` subclass): raised by `ProfileWriter.apply` before any field is copied; the target file is never written.

`OSError`, `InvalidProfileError`, `UnsupportedProfileError`: caught in `copy_cli.main`, printed as `{PROG}: {error}`, exit 1.

## Testing

- `tests/test_profile_writer.py` — `ProfileWriter.apply` per-flag copy semantics, combinations, and `ProfileTypeMismatchError` cases (offense + defense).
- `tests/test_copy_cli.py` — argparse, file dispatch, end-to-end copy verified by reloading the written `.prf`, mismatch / missing-file exit codes.

Test fixtures (`tests/data/TST-{OFF,DEF}{1,2}.prf`) are copies of the `fbpro98-profile` ground-truth profiles to keep this project self-contained.

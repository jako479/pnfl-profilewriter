# Changelog

- `pnfl copy-profile SOURCE TARGET` CLI: copies selected fields between same-side `.prf` profiles.
- `--stop-clock` flag: copy stop-clock for every situation.
- `--sub-percent` flag: copy every position group's substitution percentages.
- `--field-goal-range` flag: copy the field-goal range.
- `--fourth-down` flag: copy every 4th-down situation (stop_clock + category_weights).
- `--goal-line` flag: copy every goal-line situation (inside DEF 5 / OFF 5).
- Multiple flags may be combined; all independent.
- `ProfileWriter.apply(**copy_flags) -> PnflProfile`; library entry point.
- `ProfileTypeMismatchError` raised before any field is copied when sides differ.
- CLI installs `warnings.simplefilter("always", PnflRuleWarning)` at entry; PNFL violations warn but don't block the write.
- `pnfl.commands` entry point: `copy-profile = pnfl_profilewriter.copy_cli:main`.
- Rename `fbpro98-profilewriter` → `pnfl-profilewriter`.
- `pnfl-profile` is the sole runtime dependency.
- Initial project skeleton (pyproject.toml, README, LICENSE, package and tests scaffolding).

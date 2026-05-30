"""Copy selected fields from a source `.prf` into a target `.prf`.

Loads both profiles via `PnflProfile.from_file`, requires their `profile_type`
to match, applies each requested copy operation in turn, and returns a new
`PnflProfile` wrapping the resulting `Profile`. Nothing is written to disk;
callers persist via `pp.save(path)`.
"""

from __future__ import annotations

from dataclasses import replace
from os import PathLike
from pathlib import Path

from fbpro98_profile import Down, FieldPosition, Profile, ProfileType, Situation
from pnfl_profile import PNFL_RULES, PnflProfile, PnflRules

StrPath = str | PathLike[str]

GOAL_LINE_POSITIONS: frozenset[FieldPosition] = frozenset({FieldPosition.INSIDE_DEF_5, FieldPosition.INSIDE_OFF_5})


class ProfileTypeMismatchError(ValueError):
    """Raised when the source and target profile types differ."""

    def __init__(self, source_type: ProfileType, target_type: ProfileType) -> None:
        self.source_type = source_type
        self.target_type = target_type
        super().__init__(
            f"Profile type mismatch: source is {source_type.name}, target is {target_type.name}. "
            f"copy-profile only copies offense → offense or defense → defense."
        )


class ProfileWriter:
    """Loads source and target `.prf` files and copies selected fields between them."""

    def __init__(
        self,
        source_path: StrPath,
        target_path: StrPath,
        *,
        rules: PnflRules = PNFL_RULES,
    ) -> None:
        self.source_path = Path(source_path)
        self.target_path = Path(target_path)
        self.rules = rules

    def apply(
        self,
        *,
        copy_stop_clock: bool = False,
        copy_sub_percent: bool = False,
        copy_field_goal_range: bool = False,
        copy_fourth_down: bool = False,
        copy_goal_line: bool = False,
    ) -> PnflProfile:
        """Apply the requested copy operations and return the updated target as a `PnflProfile`.

        Loads source and target via `PnflProfile.from_file`. Requires
        `source.profile_type == target.profile_type`; otherwise raises
        `ProfileTypeMismatchError` before any field is copied. Each copy
        operation is independent and may be combined; passing no flags
        returns the target unchanged.

        `copy_fourth_down` and `copy_goal_line` copy the **entire** affected
        situation (stop_clock + category_weights) — overlapping with
        `copy_stop_clock` is harmless because both are idempotent. When both
        target multiple situation kinds, the per-situation copy applies if
        the situation matches any selected predicate.
        """
        source = PnflProfile.from_file(str(self.source_path), self.rules)
        target = PnflProfile.from_file(str(self.target_path), self.rules)
        if source.profile_type != target.profile_type:
            raise ProfileTypeMismatchError(source.profile_type, target.profile_type)
        profile = target.profile
        if copy_sub_percent:
            profile = replace(profile, substitutions=source.profile.substitutions)
        if copy_field_goal_range:
            profile = replace(profile, field_goal_range=source.profile.field_goal_range)
        if copy_stop_clock or copy_fourth_down or copy_goal_line:
            profile = _copy_situations(
                profile,
                source.profile,
                stop_clock=copy_stop_clock,
                fourth_down=copy_fourth_down,
                goal_line=copy_goal_line,
            )
        return PnflProfile(profile=profile, rules=target.rules)


def _copy_situations(
    target: Profile,
    source: Profile,
    *,
    stop_clock: bool,
    fourth_down: bool,
    goal_line: bool,
) -> Profile:
    """Return a new Profile with per-situation fields taken from `source`.

    `stop_clock` copies only the boolean across every situation.
    `fourth_down` / `goal_line` copy the whole situation (stop_clock +
    category_weights) for situations matching that predicate. When both
    fine-grained flags select the same situation, the whole-situation copy
    wins (it already includes stop_clock).
    """
    situations: list[Situation] = []
    for t, s in zip(target.situations, source.situations, strict=True):
        whole = (fourth_down and t.down == Down.Fourth) or (goal_line and t.field_position in GOAL_LINE_POSITIONS)
        if whole:
            situations.append(replace(t, stop_clock=s.stop_clock, category_weights=s.category_weights))
        elif stop_clock:
            situations.append(replace(t, stop_clock=s.stop_clock))
        else:
            situations.append(t)
    return replace(target, situations=tuple(situations))

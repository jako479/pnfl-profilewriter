from __future__ import annotations

import shutil
from dataclasses import replace
from pathlib import Path

import pytest
from conftest import DEFENSE_PRF, OFFENSE_PRF
from fbpro98_profile import (
    CategoryWeights,
    Down,
    FieldPosition,
    Profile,
    SubstitutionPair,
    SubstitutionSettings,
    read_profile,
    write_profile,
)
from pnfl_profile import PNFL_RULES, PnflProfile

from pnfl_profilewriter.profile_writer import (
    GOAL_LINE_POSITIONS,
    ProfileTypeMismatchError,
    ProfileWriter,
)

# ---------- helpers ----------


def _copy_prf(src: Path, tmp_path: Path, *, name: str | None = None) -> Path:
    dest = tmp_path / (name or src.name)
    shutil.copy2(src, dest)
    return dest


def _write_source(profile: Profile, tmp_path: Path, *, name: str = "source.prf") -> Path:
    dest = tmp_path / name
    write_profile(profile, str(dest))
    return dest


def _mutated_stop_clock_source(src: Path, tmp_path: Path, *, flip: tuple[int, ...]) -> Path:
    profile = read_profile(str(src))
    sits = list(profile.situations)
    for n in flip:
        sits[n - 1] = replace(sits[n - 1], stop_clock=not sits[n - 1].stop_clock)
    return _write_source(replace(profile, situations=tuple(sits)), tmp_path)


def _stop_clock_vector(path: Path) -> tuple[bool, ...]:
    return tuple(s.stop_clock for s in read_profile(str(path)).situations)


def _distinct_weights(base: CategoryWeights) -> CategoryWeights:
    """Return a CategoryWeights value distinct from `base` (within domain bounds)."""
    new_cat = (base.play_category1 + 1) % 0x1B  # 0x00..0x1A
    new_weight = (base.weight1 + 1) % 11  # 0..10
    return replace(base, play_category1=new_cat, weight1=new_weight)


def _stamp_situations_matching(profile: Profile, *, predicate, marker: CategoryWeights) -> Profile:
    """Return profile with every situation matching `predicate` replaced with `marker` weights + flipped stop_clock."""
    sits = tuple(
        replace(s, category_weights=marker, stop_clock=not s.stop_clock) if predicate(s) else s
        for s in profile.situations
    )
    return replace(profile, situations=sits)


# ---------- stop_clock copy ----------


def test_copy_stop_clock_replaces_every_situation(tmp_path: Path) -> None:
    source = _mutated_stop_clock_source(OFFENSE_PRF, tmp_path, flip=(1, 100, 2000, 2520))
    target = _copy_prf(OFFENSE_PRF, tmp_path, name="target.prf")

    result = ProfileWriter(source, target).apply(copy_stop_clock=True)

    assert _stop_clock_vector(source) == tuple(s.stop_clock for s in result.situations)


def test_copy_stop_clock_idempotent_when_source_equals_target(tmp_path: Path) -> None:
    target = _copy_prf(OFFENSE_PRF, tmp_path, name="target.prf")
    source = _copy_prf(OFFENSE_PRF, tmp_path, name="source.prf")
    original = _stop_clock_vector(target)

    result = ProfileWriter(source, target).apply(copy_stop_clock=True)

    assert tuple(s.stop_clock for s in result.situations) == original


def test_copy_no_flags_returns_target_unchanged(tmp_path: Path) -> None:
    source = _mutated_stop_clock_source(OFFENSE_PRF, tmp_path, flip=(1, 2, 3))
    target = _copy_prf(OFFENSE_PRF, tmp_path, name="target.prf")
    original = _stop_clock_vector(target)

    result = ProfileWriter(source, target).apply()

    assert tuple(s.stop_clock for s in result.situations) == original


def test_copy_stop_clock_works_on_defense(tmp_path: Path) -> None:
    source = _mutated_stop_clock_source(DEFENSE_PRF, tmp_path, flip=(50, 1500))
    target = _copy_prf(DEFENSE_PRF, tmp_path, name="target.prf")

    result = ProfileWriter(source, target).apply(copy_stop_clock=True)

    assert _stop_clock_vector(source) == tuple(s.stop_clock for s in result.situations)


def test_copy_stop_clock_preserves_category_weights(tmp_path: Path) -> None:
    source = _mutated_stop_clock_source(OFFENSE_PRF, tmp_path, flip=(1, 100))
    target = _copy_prf(OFFENSE_PRF, tmp_path, name="target.prf")
    original_target = PnflProfile.from_file(str(target), PNFL_RULES)

    result = ProfileWriter(source, target).apply(copy_stop_clock=True)

    for original, after in zip(original_target.situations, result.situations, strict=True):
        assert after.situation_number == original.situation_number
        assert after.category_weights == original.category_weights


# ---------- sub_percent copy ----------


def _custom_subs() -> SubstitutionSettings:
    return SubstitutionSettings(
        offensive_linemen=SubstitutionPair(10, 20),
        quarterbacks=SubstitutionPair(75, 80),
        running_backs=SubstitutionPair(30, 40),
        receivers=SubstitutionPair(35, 45),
        defensive_linemen=SubstitutionPair(50, 60),
        linebackers=SubstitutionPair(55, 65),
        defensive_backs=SubstitutionPair(60, 70),
        kickers=SubstitutionPair(65, 75),
    )


def test_copy_sub_percent_replaces_substitutions(tmp_path: Path) -> None:
    base = read_profile(str(OFFENSE_PRF))
    source = _write_source(replace(base, substitutions=_custom_subs()), tmp_path)
    target = _copy_prf(OFFENSE_PRF, tmp_path, name="target.prf")

    result = ProfileWriter(source, target).apply(copy_sub_percent=True)

    assert result.substitutions == _custom_subs()


def test_copy_sub_percent_leaves_other_fields_alone(tmp_path: Path) -> None:
    base = read_profile(str(OFFENSE_PRF))
    source = _write_source(replace(base, substitutions=_custom_subs()), tmp_path)
    target = _copy_prf(OFFENSE_PRF, tmp_path, name="target.prf")
    original = read_profile(str(target))

    result = ProfileWriter(source, target).apply(copy_sub_percent=True)

    assert tuple(s.stop_clock for s in result.situations) == tuple(s.stop_clock for s in original.situations)
    assert result.field_goal_range == original.field_goal_range


# ---------- field_goal_range copy ----------


def test_copy_field_goal_range_replaces_value(tmp_path: Path) -> None:
    base = read_profile(str(OFFENSE_PRF))
    new_range = base.field_goal_range + 1 if base.field_goal_range < 50 else base.field_goal_range - 1
    source = _write_source(replace(base, field_goal_range=new_range), tmp_path)
    target = _copy_prf(OFFENSE_PRF, tmp_path, name="target.prf")

    result = ProfileWriter(source, target).apply(copy_field_goal_range=True)

    assert result.field_goal_range == new_range


def test_copy_field_goal_range_leaves_situations_alone(tmp_path: Path) -> None:
    base = read_profile(str(OFFENSE_PRF))
    new_range = base.field_goal_range + 1 if base.field_goal_range < 50 else base.field_goal_range - 1
    source = _write_source(replace(base, field_goal_range=new_range), tmp_path)
    target = _copy_prf(OFFENSE_PRF, tmp_path, name="target.prf")
    original = read_profile(str(target))

    result = ProfileWriter(source, target).apply(copy_field_goal_range=True)

    assert tuple(s.stop_clock for s in result.situations) == tuple(s.stop_clock for s in original.situations)
    assert tuple(s.category_weights for s in result.situations) == tuple(
        s.category_weights for s in original.situations
    )


# ---------- fourth_down copy ----------


def test_copy_fourth_down_copies_only_fourth_down_situations(tmp_path: Path) -> None:
    base = read_profile(str(OFFENSE_PRF))
    marker = _distinct_weights(base.situations[0].category_weights)
    source = _write_source(
        _stamp_situations_matching(base, predicate=lambda s: s.down == Down.Fourth, marker=marker),
        tmp_path,
    )
    target = _copy_prf(OFFENSE_PRF, tmp_path, name="target.prf")
    original = read_profile(str(target))

    result = ProfileWriter(source, target).apply(copy_fourth_down=True)

    for original_sit, after in zip(original.situations, result.situations, strict=True):
        if original_sit.down == Down.Fourth:
            assert after.category_weights == marker
            assert after.stop_clock != original_sit.stop_clock
        else:
            assert after.category_weights == original_sit.category_weights
            assert after.stop_clock == original_sit.stop_clock


def test_copy_fourth_down_works_on_defense(tmp_path: Path) -> None:
    base = read_profile(str(DEFENSE_PRF))
    marker = _distinct_weights(base.situations[0].category_weights)
    source = _write_source(
        _stamp_situations_matching(base, predicate=lambda s: s.down == Down.Fourth, marker=marker),
        tmp_path,
    )
    target = _copy_prf(DEFENSE_PRF, tmp_path, name="target.prf")

    result = ProfileWriter(source, target).apply(copy_fourth_down=True)

    affected = [s for s in result.situations if s.down == Down.Fourth]
    assert affected, "fixture should contain 4th-down situations"
    assert all(s.category_weights == marker for s in affected)


# ---------- goal_line copy ----------


def test_copy_goal_line_copies_only_goal_line_situations(tmp_path: Path) -> None:
    base = read_profile(str(OFFENSE_PRF))
    marker = _distinct_weights(base.situations[0].category_weights)
    source = _write_source(
        _stamp_situations_matching(base, predicate=lambda s: s.field_position in GOAL_LINE_POSITIONS, marker=marker),
        tmp_path,
    )
    target = _copy_prf(OFFENSE_PRF, tmp_path, name="target.prf")
    original = read_profile(str(target))

    result = ProfileWriter(source, target).apply(copy_goal_line=True)

    for original_sit, after in zip(original.situations, result.situations, strict=True):
        if original_sit.field_position in GOAL_LINE_POSITIONS:
            assert after.category_weights == marker
        else:
            assert after.category_weights == original_sit.category_weights


def test_copy_goal_line_covers_both_inside_5_buckets(tmp_path: Path) -> None:
    base = read_profile(str(OFFENSE_PRF))
    marker = _distinct_weights(base.situations[0].category_weights)
    source = _write_source(
        _stamp_situations_matching(base, predicate=lambda s: s.field_position in GOAL_LINE_POSITIONS, marker=marker),
        tmp_path,
    )
    target = _copy_prf(OFFENSE_PRF, tmp_path, name="target.prf")

    result = ProfileWriter(source, target).apply(copy_goal_line=True)

    def_5 = [s for s in result.situations if s.field_position == FieldPosition.INSIDE_DEF_5]
    off_5 = [s for s in result.situations if s.field_position == FieldPosition.INSIDE_OFF_5]
    assert def_5 and off_5
    assert all(s.category_weights == marker for s in def_5)
    assert all(s.category_weights == marker for s in off_5)


# ---------- combinations ----------


def test_combined_flags_apply_each_independently(tmp_path: Path) -> None:
    base = read_profile(str(OFFENSE_PRF))
    new_range = base.field_goal_range + 1 if base.field_goal_range < 50 else base.field_goal_range - 1
    marker = _distinct_weights(base.situations[0].category_weights)
    stamped = _stamp_situations_matching(base, predicate=lambda s: s.down == Down.Fourth, marker=marker)
    source = _write_source(
        replace(
            stamped,
            substitutions=_custom_subs(),
            field_goal_range=new_range,
        ),
        tmp_path,
    )
    target = _copy_prf(OFFENSE_PRF, tmp_path, name="target.prf")
    original = read_profile(str(target))

    result = ProfileWriter(source, target).apply(
        copy_sub_percent=True,
        copy_field_goal_range=True,
        copy_fourth_down=True,
    )

    assert result.substitutions == _custom_subs()
    assert result.field_goal_range == new_range
    fourth = [s for s in result.situations if s.down == Down.Fourth]
    non_fourth_changed = [
        a
        for a, o in zip(result.situations, original.situations, strict=True)
        if a.down != Down.Fourth and a.category_weights != o.category_weights
    ]
    assert all(s.category_weights == marker for s in fourth)
    assert non_fourth_changed == []


def test_fourth_down_and_stop_clock_combine_cleanly(tmp_path: Path) -> None:
    base = read_profile(str(OFFENSE_PRF))
    marker = _distinct_weights(base.situations[0].category_weights)
    sits = list(base.situations)
    # Flip stop_clock everywhere; also stamp 4th-down with marker weights.
    sits = [replace(s, stop_clock=not s.stop_clock) for s in sits]
    sits = [replace(s, category_weights=marker) if s.down == Down.Fourth else s for s in sits]
    source = _write_source(replace(base, situations=tuple(sits)), tmp_path)
    target = _copy_prf(OFFENSE_PRF, tmp_path, name="target.prf")
    original = read_profile(str(target))

    result = ProfileWriter(source, target).apply(copy_stop_clock=True, copy_fourth_down=True)

    for original_sit, after in zip(original.situations, result.situations, strict=True):
        assert after.stop_clock != original_sit.stop_clock
        if original_sit.down == Down.Fourth:
            assert after.category_weights == marker
        else:
            assert after.category_weights == original_sit.category_weights


# ---------- mismatched types ----------


def test_offense_source_defense_target_raises(tmp_path: Path) -> None:
    source = _copy_prf(OFFENSE_PRF, tmp_path, name="source.prf")
    target = _copy_prf(DEFENSE_PRF, tmp_path, name="target.prf")

    with pytest.raises(ProfileTypeMismatchError):
        ProfileWriter(source, target).apply(copy_stop_clock=True)


def test_defense_source_offense_target_raises(tmp_path: Path) -> None:
    source = _copy_prf(DEFENSE_PRF, tmp_path, name="source.prf")
    target = _copy_prf(OFFENSE_PRF, tmp_path, name="target.prf")

    with pytest.raises(ProfileTypeMismatchError):
        ProfileWriter(source, target).apply(copy_stop_clock=True)


def test_mismatch_error_carries_both_types(tmp_path: Path) -> None:
    source = _copy_prf(OFFENSE_PRF, tmp_path, name="source.prf")
    target = _copy_prf(DEFENSE_PRF, tmp_path, name="target.prf")

    with pytest.raises(ProfileTypeMismatchError) as exc_info:
        ProfileWriter(source, target).apply(copy_stop_clock=True)
    assert exc_info.value.source_type.name == "OFFENSE"
    assert exc_info.value.target_type.name == "DEFENSE"


def test_mismatch_does_not_modify_target(tmp_path: Path) -> None:
    source = _copy_prf(OFFENSE_PRF, tmp_path, name="source.prf")
    target = _copy_prf(DEFENSE_PRF, tmp_path, name="target.prf")
    pre_bytes = target.read_bytes()

    with pytest.raises(ProfileTypeMismatchError):
        ProfileWriter(source, target).apply(copy_stop_clock=True)
    assert target.read_bytes() == pre_bytes


def test_mismatch_raises_for_any_flag(tmp_path: Path) -> None:
    source = _copy_prf(OFFENSE_PRF, tmp_path, name="source.prf")
    target = _copy_prf(DEFENSE_PRF, tmp_path, name="target.prf")

    with pytest.raises(ProfileTypeMismatchError):
        ProfileWriter(source, target).apply(copy_sub_percent=True)
    with pytest.raises(ProfileTypeMismatchError):
        ProfileWriter(source, target).apply(copy_field_goal_range=True)
    with pytest.raises(ProfileTypeMismatchError):
        ProfileWriter(source, target).apply(copy_fourth_down=True)
    with pytest.raises(ProfileTypeMismatchError):
        ProfileWriter(source, target).apply(copy_goal_line=True)

from __future__ import annotations

import shutil
from dataclasses import replace
from pathlib import Path

import pytest
from conftest import DEFENSE_PRF, OFFENSE_PRF
from fbpro98_profile import Down, SubstitutionPair, SubstitutionSettings, read_profile, write_profile

from pnfl_profilewriter.copy_cli import main, parse_args

# ---------- argparse ----------


def test_parse_args_requires_source() -> None:
    with pytest.raises(SystemExit):
        parse_args([])


def test_parse_args_requires_target() -> None:
    with pytest.raises(SystemExit):
        parse_args(["source.prf"])


def test_parse_args_requires_a_copy_flag() -> None:
    with pytest.raises(SystemExit):
        parse_args(["source.prf", "target.prf"])


def test_parse_args_accepts_stop_clock() -> None:
    args = parse_args(["source.prf", "target.prf", "--stop-clock"])
    assert args.copy_stop_clock is True
    assert args.copy_sub_percent is False
    assert args.copy_field_goal_range is False
    assert args.copy_fourth_down is False
    assert args.copy_goal_line is False


def test_parse_args_accepts_sub_percent() -> None:
    args = parse_args(["source.prf", "target.prf", "--sub-percent"])
    assert args.copy_sub_percent is True


def test_parse_args_accepts_field_goal_range() -> None:
    args = parse_args(["source.prf", "target.prf", "--field-goal-range"])
    assert args.copy_field_goal_range is True


def test_parse_args_accepts_fourth_down() -> None:
    args = parse_args(["source.prf", "target.prf", "--fourth-down"])
    assert args.copy_fourth_down is True


def test_parse_args_accepts_goal_line() -> None:
    args = parse_args(["source.prf", "target.prf", "--goal-line"])
    assert args.copy_goal_line is True


def test_parse_args_accepts_multiple_flags() -> None:
    args = parse_args(
        [
            "s.prf",
            "t.prf",
            "--stop-clock",
            "--sub-percent",
            "--field-goal-range",
            "--fourth-down",
            "--goal-line",
        ]
    )
    assert args.copy_stop_clock is True
    assert args.copy_sub_percent is True
    assert args.copy_field_goal_range is True
    assert args.copy_fourth_down is True
    assert args.copy_goal_line is True


# ---------- main: file flow ----------


def _copy_prf(src: Path, tmp_path: Path, *, name: str | None = None) -> Path:
    dest = tmp_path / (name or src.name)
    shutil.copy2(src, dest)
    return dest


def _mutated_source(src: Path, tmp_path: Path, *, flip: tuple[int, ...]) -> Path:
    profile = read_profile(str(src))
    sits = list(profile.situations)
    for n in flip:
        sits[n - 1] = replace(sits[n - 1], stop_clock=not sits[n - 1].stop_clock)
    dest = tmp_path / "source.prf"
    write_profile(replace(profile, situations=tuple(sits)), str(dest))
    return dest


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


def test_main_copies_stop_clock_between_offense_profiles(tmp_path: Path) -> None:
    source = _mutated_source(OFFENSE_PRF, tmp_path, flip=(1, 100, 2520))
    target = _copy_prf(OFFENSE_PRF, tmp_path, name="target.prf")

    rc = main([str(source), str(target), "--stop-clock"])

    assert rc == 0
    expected = tuple(s.stop_clock for s in read_profile(str(source)).situations)
    actual = tuple(s.stop_clock for s in read_profile(str(target)).situations)
    assert actual == expected


def test_main_copies_stop_clock_between_defense_profiles(tmp_path: Path) -> None:
    source = _mutated_source(DEFENSE_PRF, tmp_path, flip=(50, 1500))
    target = _copy_prf(DEFENSE_PRF, tmp_path, name="target.prf")

    rc = main([str(source), str(target), "--stop-clock"])

    assert rc == 0
    expected = tuple(s.stop_clock for s in read_profile(str(source)).situations)
    actual = tuple(s.stop_clock for s in read_profile(str(target)).situations)
    assert actual == expected


def test_main_copies_sub_percent(tmp_path: Path) -> None:
    base = read_profile(str(OFFENSE_PRF))
    source = tmp_path / "source.prf"
    write_profile(replace(base, substitutions=_custom_subs()), str(source))
    target = _copy_prf(OFFENSE_PRF, tmp_path, name="target.prf")

    rc = main([str(source), str(target), "--sub-percent"])

    assert rc == 0
    assert read_profile(str(target)).substitutions == _custom_subs()


def test_main_copies_field_goal_range(tmp_path: Path) -> None:
    base = read_profile(str(OFFENSE_PRF))
    new_range = base.field_goal_range + 1 if base.field_goal_range < 50 else base.field_goal_range - 1
    source = tmp_path / "source.prf"
    write_profile(replace(base, field_goal_range=new_range), str(source))
    target = _copy_prf(OFFENSE_PRF, tmp_path, name="target.prf")

    rc = main([str(source), str(target), "--field-goal-range"])

    assert rc == 0
    assert read_profile(str(target)).field_goal_range == new_range


def test_main_copies_fourth_down(tmp_path: Path) -> None:
    base = read_profile(str(OFFENSE_PRF))
    marker = replace(
        base.situations[0].category_weights, weight1=(base.situations[0].category_weights.weight1 + 1) % 11
    )
    sits = tuple(replace(s, category_weights=marker) if s.down == Down.Fourth else s for s in base.situations)
    source = tmp_path / "source.prf"
    write_profile(replace(base, situations=sits), str(source))
    target = _copy_prf(OFFENSE_PRF, tmp_path, name="target.prf")

    rc = main([str(source), str(target), "--fourth-down"])

    assert rc == 0
    result = read_profile(str(target))
    assert all(s.category_weights == marker for s in result.situations if s.down == Down.Fourth)


def test_main_copies_goal_line_and_stop_clock_combined(tmp_path: Path) -> None:
    source = _mutated_source(OFFENSE_PRF, tmp_path, flip=(1, 100, 2520))
    target = _copy_prf(OFFENSE_PRF, tmp_path, name="target.prf")

    rc = main([str(source), str(target), "--stop-clock", "--goal-line"])

    assert rc == 0
    expected = tuple(s.stop_clock for s in read_profile(str(source)).situations)
    actual = tuple(s.stop_clock for s in read_profile(str(target)).situations)
    assert actual == expected


def test_main_rejects_offense_to_defense(tmp_path: Path) -> None:
    source = _copy_prf(OFFENSE_PRF, tmp_path, name="source.prf")
    target = _copy_prf(DEFENSE_PRF, tmp_path, name="target.prf")
    pre_bytes = target.read_bytes()

    rc = main([str(source), str(target), "--stop-clock"])

    assert rc == 1
    assert target.read_bytes() == pre_bytes


def test_main_rejects_defense_to_offense(tmp_path: Path) -> None:
    source = _copy_prf(DEFENSE_PRF, tmp_path, name="source.prf")
    target = _copy_prf(OFFENSE_PRF, tmp_path, name="target.prf")
    pre_bytes = target.read_bytes()

    rc = main([str(source), str(target), "--stop-clock"])

    assert rc == 1
    assert target.read_bytes() == pre_bytes


def test_main_rejects_mismatch_for_any_flag(tmp_path: Path) -> None:
    source = _copy_prf(OFFENSE_PRF, tmp_path, name="source.prf")
    target = _copy_prf(DEFENSE_PRF, tmp_path, name="target.prf")

    for flag in ("--stop-clock", "--sub-percent", "--field-goal-range", "--fourth-down", "--goal-line"):
        target_copy = _copy_prf(DEFENSE_PRF, tmp_path, name=f"target_{flag.strip('-')}.prf")
        rc = main([str(source), str(target_copy), flag])
        assert rc == 1


def test_main_missing_source_returns_error(tmp_path: Path) -> None:
    target = _copy_prf(OFFENSE_PRF, tmp_path, name="target.prf")

    rc = main([str(tmp_path / "nope.prf"), str(target), "--stop-clock"])

    assert rc == 1


def test_main_missing_target_returns_error(tmp_path: Path) -> None:
    source = _copy_prf(OFFENSE_PRF, tmp_path, name="source.prf")

    rc = main([str(source), str(tmp_path / "nope.prf"), "--stop-clock"])

    assert rc == 1

"""Orchestrator: load source + target, copy selected fields, persist target."""

from __future__ import annotations

import logging
from pathlib import Path

from pnfl_profilewriter.profile_writer import ProfileWriter

logger = logging.getLogger(__name__)


def copy_profile(
    *,
    source_path: str | Path,
    target_path: str | Path,
    copy_stop_clock: bool = False,
    copy_sub_percent: bool = False,
    copy_field_goal_range: bool = False,
    copy_fourth_down: bool = False,
    copy_goal_line: bool = False,
) -> None:
    """Copy the requested fields from `source_path` into `target_path` and save.

    PNFL-rule violations on the resulting profile are surfaced as
    `PnflRuleWarning` from `PnflProfile.save()`; the target is written
    regardless. Raises `ProfileTypeMismatchError` when sides don't match.
    """
    writer = ProfileWriter(source_path, target_path)
    pp = writer.apply(
        copy_stop_clock=copy_stop_clock,
        copy_sub_percent=copy_sub_percent,
        copy_field_goal_range=copy_field_goal_range,
        copy_fourth_down=copy_fourth_down,
        copy_goal_line=copy_goal_line,
    )
    pp.save(str(target_path))
    parts = _summarize(
        copy_stop_clock=copy_stop_clock,
        copy_sub_percent=copy_sub_percent,
        copy_field_goal_range=copy_field_goal_range,
        copy_fourth_down=copy_fourth_down,
        copy_goal_line=copy_goal_line,
    )
    logger.info("Copied %s from '%s' to '%s'", parts, source_path, target_path)


def _summarize(
    *,
    copy_stop_clock: bool,
    copy_sub_percent: bool,
    copy_field_goal_range: bool,
    copy_fourth_down: bool,
    copy_goal_line: bool,
) -> str:
    flags = []
    if copy_stop_clock:
        flags.append("stop-clock")
    if copy_sub_percent:
        flags.append("sub-percent")
    if copy_field_goal_range:
        flags.append("field-goal-range")
    if copy_fourth_down:
        flags.append("fourth-down")
    if copy_goal_line:
        flags.append("goal-line")
    return ", ".join(flags) if flags else "nothing"

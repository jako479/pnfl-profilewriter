"""`pnfl copy-profile` — copy selected fields from one `.prf` into another.

At least one copy flag is required; without one the CLI exits with usage
error. Both profiles must be the same side (offense ↔ offense, defense ↔
defense). PNFL rule violations on the resulting target are logged at WARNING
by `PnflProfile.save()`; the target is written regardless.
"""

from __future__ import annotations

import argparse
import logging
from collections.abc import Sequence
from pathlib import Path

from pnfl_profile import InvalidProfileError, UnsupportedProfileError

from pnfl_profilewriter.main import copy_profile
from pnfl_profilewriter.profile_writer import ProfileTypeMismatchError

PROG = "pnfl copy-profile"
logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=PROG,
        description="Copy selected fields from a source .prf into a target .prf.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Copy options (at least one required, multiple may be combined):\n"
            "  --stop-clock          Copy the stop-clock flag for every situation.\n"
            "  --sub-percent         Copy every position group's substitution percentages.\n"
            "  --field-goal-range    Copy the field-goal range.\n"
            "  --fourth-down         Copy every 4th-down situation (stop_clock + weights).\n"
            "  --goal-line           Copy every goal-line situation (inside DEF 5 or OFF 5).\n"
            "\n"
            "Both profiles must be the same type (offense -> offense, defense -> defense).\n"
            "The target is updated in place.\n"
        ),
    )
    parser.add_argument(
        "source_path",
        help="Path to the source .prf profile to copy from",
    )
    parser.add_argument(
        "target_path",
        help="Path to the target .prf profile to update",
    )
    parser.add_argument(
        "--stop-clock",
        dest="copy_stop_clock",
        action="store_true",
        help="Copy stop-clock flag for every situation",
    )
    parser.add_argument(
        "--sub-percent",
        dest="copy_sub_percent",
        action="store_true",
        help="Copy every position group's substitution percentages",
    )
    parser.add_argument(
        "--field-goal-range",
        dest="copy_field_goal_range",
        action="store_true",
        help="Copy the field-goal range",
    )
    parser.add_argument(
        "--fourth-down",
        dest="copy_fourth_down",
        action="store_true",
        help="Copy every 4th-down situation (stop_clock + category_weights)",
    )
    parser.add_argument(
        "--goal-line",
        dest="copy_goal_line",
        action="store_true",
        help="Copy every goal-line situation (inside DEF 5 or OFF 5)",
    )
    return parser


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not _any_copy_flag(args):
        parser.error(
            "at least one copy option is required "
            "(--stop-clock, --sub-percent, --field-goal-range, --fourth-down, --goal-line)"
        )
    return args


def _any_copy_flag(args: argparse.Namespace) -> bool:
    return any(
        (
            args.copy_stop_clock,
            args.copy_sub_percent,
            args.copy_field_goal_range,
            args.copy_fourth_down,
            args.copy_goal_line,
        )
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
    )
    try:
        copy_profile(
            source_path=Path(args.source_path),
            target_path=Path(args.target_path),
            copy_stop_clock=args.copy_stop_clock,
            copy_sub_percent=args.copy_sub_percent,
            copy_field_goal_range=args.copy_field_goal_range,
            copy_fourth_down=args.copy_fourth_down,
            copy_goal_line=args.copy_goal_line,
        )
    except ProfileTypeMismatchError as error:
        logger.error("%s: %s", PROG, error)
        return 1
    except (InvalidProfileError, UnsupportedProfileError) as error:
        logger.error("%s: %s", PROG, error)
        return 1
    except OSError as error:
        logger.error("%s: %s", PROG, error)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

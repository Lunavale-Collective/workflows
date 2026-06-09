#!/usr/bin/env python3
"""Write a Shields endpoint JSON badge for workflow status dates."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
from zoneinfo import ZoneInfo


DEFAULT_TIMEZONE = ZoneInfo("America/New_York")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Write a workflow status badge JSON file.")
    parser.add_argument("--output", required=True, help="Badge JSON output path.")
    parser.add_argument("--label", required=True, help="Badge label.")
    parser.add_argument("--color", default="0969da", help="Badge color. Default: 0969da.")
    return parser.parse_args()


def current_badge_date() -> dt.date:
    raw_value = os.environ.get("BADGE_NOW")
    if not raw_value:
        return dt.datetime.now(DEFAULT_TIMEZONE).date()

    value = raw_value.strip()
    if len(value) == 10:
        return dt.date.fromisoformat(value)

    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    parsed = dt.datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=DEFAULT_TIMEZONE)
    return parsed.astimezone(DEFAULT_TIMEZONE).date()


def date_message(value: dt.date) -> str:
    return f"{value.strftime('%b')} {value.day}, {value.year}"


def write_badge(path: Path, *, label: str, message: str, color: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "label": label,
                "message": message,
                "color": color,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> int:
    args = parse_args()
    write_badge(
        Path(args.output),
        label=args.label,
        message=date_message(current_badge_date()),
        color=args.color,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

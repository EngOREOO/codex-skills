#!/usr/bin/env python3
"""Fail a production QA gate when the manual coverage ledger is incomplete."""

from __future__ import annotations

import csv
import sys
from collections import Counter
from pathlib import Path


REQUIRED_COLUMNS = (
    "id",
    "client",
    "platform",
    "device_or_browser",
    "role",
    "screen_or_route",
    "state",
    "control_or_action",
    "data_backed",
    "mutation",
    "expected_result",
    "observed_result",
    "status",
    "ui_evidence",
    "network_evidence",
    "backend_evidence",
    "persistence_evidence",
    "accessibility_evidence",
    "build_id",
    "tested_at",
    "tester",
)

ALLOWED_STATUSES = {"PASS", "FAIL", "BLOCKED", "UNTESTED"}
ALLOWED_BOOLEAN_VALUES = {"yes", "no"}
PLACEHOLDERS = {"", "n/a", "na", "none", "null", "todo", "tbd", "replace_me", "-"}


def missing(value: str | None) -> bool:
    return value is None or value.strip().lower() in PLACEHOLDERS


def validate_coverage(path: Path) -> tuple[list[str], set[str]]:
    errors: list[str] = []
    if not path.is_file():
        return [f"coverage matrix does not exist: {path}"], set()

    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        columns = reader.fieldnames or []
        missing_columns = [column for column in REQUIRED_COLUMNS if column not in columns]
        if missing_columns:
            return ["missing required columns: " + ", ".join(missing_columns)], set()
        rows = list(reader)

    if not rows:
        return ["coverage matrix contains no test rows"], set()

    ids = [row.get("id", "").strip() for row in rows]
    duplicates = sorted(item for item, count in Counter(ids).items() if item and count > 1)
    if duplicates:
        errors.append("duplicate coverage IDs: " + ", ".join(duplicates))

    for index, row in enumerate(rows, start=2):
        row_id = row.get("id", "").strip() or f"line {index}"
        status = row.get("status", "").strip().upper()
        data_backed = row.get("data_backed", "").strip().lower()
        mutation = row.get("mutation", "").strip().lower()

        for column in REQUIRED_COLUMNS:
            if column in {"network_evidence", "backend_evidence", "persistence_evidence"}:
                continue
            if missing(row.get(column)):
                errors.append(f"{row_id}: missing {column}")

        if status not in ALLOWED_STATUSES:
            errors.append(f"{row_id}: invalid status {status or '<empty>'}")
        elif status != "PASS":
            errors.append(f"{row_id}: release gate contains {status}")

        if status == "PASS" and missing(row.get("ui_evidence")):
            errors.append(f"{row_id}: PASS lacks UI/manual evidence")

        for column, value in (("data_backed", data_backed), ("mutation", mutation)):
            if value not in ALLOWED_BOOLEAN_VALUES:
                errors.append(f"{row_id}: {column} must be yes or no")
        if mutation == "yes" and data_backed != "yes":
            errors.append(f"{row_id}: mutation=yes requires data_backed=yes")

        if status == "PASS" and data_backed == "yes":
            for column in ("network_evidence", "backend_evidence"):
                if missing(row.get(column)):
                    errors.append(f"{row_id}: data-backed PASS lacks {column}")
        if status == "PASS" and mutation == "yes" and missing(row.get("persistence_evidence")):
            errors.append(f"{row_id}: mutation PASS lacks persistence_evidence")

        if any("replace_me" in (value or "").lower() for value in row.values()):
            errors.append(f"{row_id}: contains template placeholder REPLACE_ME")

    return errors, set(ids)


def validate_defects(path: Path, coverage_ids: set[str]) -> list[str]:
    required = {
        "defect_id",
        "severity",
        "title",
        "coverage_ids",
        "environment",
        "build_id",
        "steps",
        "expected_result",
        "observed_result",
        "evidence",
        "retest_coverage_ids",
        "status",
    }
    if not path.is_file():
        return [f"defect ledger does not exist: {path}"]

    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        columns = set(reader.fieldnames or [])
        missing_columns = sorted(required - columns)
        if missing_columns:
            return ["defect ledger missing required columns: " + ", ".join(missing_columns)]
        rows = list(reader)

    errors: list[str] = []
    defect_ids = [row.get("defect_id", "").strip() for row in rows]
    duplicates = sorted(item for item, count in Counter(defect_ids).items() if item and count > 1)
    if duplicates:
        errors.append("duplicate defect IDs: " + ", ".join(duplicates))

    for index, row in enumerate(rows, start=2):
        defect_id = row.get("defect_id", "").strip() or f"defect line {index}"
        for column in required - {"retest_coverage_ids"}:
            if missing(row.get(column)):
                errors.append(f"{defect_id}: missing {column}")
        status = row.get("status", "").strip().upper()
        if status != "CLOSED":
            errors.append(f"{defect_id}: defect status is {status or '<empty>'}, not CLOSED")
        retest_ids = {
            item.strip()
            for item in row.get("retest_coverage_ids", "").replace(";", ",").split(",")
            if item.strip()
        }
        if not retest_ids:
            errors.append(f"{defect_id}: CLOSED defect lacks retest_coverage_ids")
        unknown = sorted(retest_ids - coverage_ids)
        if unknown:
            errors.append(f"{defect_id}: unknown retest coverage IDs: {', '.join(unknown)}")
        if any("replace_me" in (value or "").lower() for value in row.values()):
            errors.append(f"{defect_id}: contains template placeholder REPLACE_ME")
    return errors


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "usage: validate_qa_evidence.py COVERAGE_MATRIX.csv DEFECTS.csv",
            file=sys.stderr,
        )
        return 2

    coverage_path = Path(sys.argv[1]).expanduser().resolve()
    defects_path = Path(sys.argv[2]).expanduser().resolve()
    coverage_errors, coverage_ids = validate_coverage(coverage_path)
    errors = coverage_errors + validate_defects(defects_path, coverage_ids)
    if errors:
        print(f"NOT PRODUCTION READY: {len(errors)} gate violation(s)")
        for error in errors:
            print(f"- {error}")
        return 1

    with coverage_path.open(newline="", encoding="utf-8-sig") as handle:
        count = sum(1 for _ in csv.DictReader(handle))
    print(f"QA evidence gate passed: {count} manual coverage row(s), all PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

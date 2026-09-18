"""UCI water-treatment dataset reader for the four-feature research model."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path


FEATURES = ("PH-E", "COND-E", "SS-E", "DQO-E")
TARGET = "RD-SS-P"

# The raw file has a date identifier followed by the 38 documented attributes.
_COLUMN_INDEX = {"PH-E": 3, "DQO-E": 5, "SS-E": 6, "COND-E": 9, "RD-SS-P": 31}


@dataclass(frozen=True)
class TreatmentRow:
    date: date
    features: dict[str, float | None]
    target: float | None


@dataclass(frozen=True)
class Dataset:
    rows: list[TreatmentRow]
    report: dict[str, int]


def _number(value: str) -> float | None:
    value = value.strip()
    return None if value in {"", "?"} else float(value)


def _date(value: str) -> date:
    cleaned = value.strip()
    if not cleaned.startswith("D-"):
        raise ValueError(f"unsupported date value: {value}")
    return datetime.strptime(cleaned[2:], "%d/%m/%y").date()


def parse_row(line: str) -> TreatmentRow:
    fields = [field.strip() for field in line.strip().split(",")]
    if len(fields) != 39:
        raise ValueError(f"expected 39 columns, received {len(fields)}")
    features = {name: _number(fields[_COLUMN_INDEX[name]]) for name in FEATURES}
    return TreatmentRow(
        date=_date(fields[0]),
        features=features,
        target=_number(fields[_COLUMN_INDEX[TARGET]]),
    )


def load_dataset(path: str | Path) -> Dataset:
    source = Path(path)
    parsed = [parse_row(line) for line in source.read_text(encoding="utf-8").splitlines() if line.strip()]
    rows = sorted((row for row in parsed if row.target is not None), key=lambda row: row.date)
    return Dataset(
        rows=rows,
        report={
            "raw_rows": len(parsed),
            "usable_rows": len(rows),
            "missing_target_rows": sum(row.target is None for row in parsed),
            "rows_with_missing_features": sum(
                any(value is None for value in row.features.values()) for row in rows
            ),
        },
    )

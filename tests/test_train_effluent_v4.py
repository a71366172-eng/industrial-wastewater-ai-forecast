import math

import pytest

from train_effluent_v4 import COLUMNS, FEATURES, load_rows, parse_number, train_target


def test_parse_number_handles_uci_missing_and_decimal_comma():
    assert math.isnan(parse_number("?"))
    assert parse_number("7,25") == 7.25


def test_load_rows_rejects_wrong_column_count(tmp_path):
    source = tmp_path / "bad.data"
    source.write_text("01-DIC-1990,1,2\n", encoding="utf-8")
    with pytest.raises(ValueError, match="欄位數"):
        load_rows(source)


def test_training_artifact_uses_time_order_and_baseline():
    rows = []
    for i in range(50):
        row = {column: 0.0 for column in COLUMNS}
        row["DATE"] = f"day-{i:02d}"
        for j, feature in enumerate(FEATURES, 1):
            row[feature] = float(i + j)
        row["SS-S"] = float(2 * i + 3)
        row["DQO-S"] = float(3 * i + 5)
        rows.append(row)
    result = train_target(rows, "SS-S")
    assert result["rows"] == {"total": 50, "train": 40, "test": 10}
    assert result["dateRange"] == {"first": "day-00", "last": "day-49"}
    assert "medianBaselineMae" in result["metrics"]
    assert result["metrics"]["mae"] < result["metrics"]["medianBaselineMae"]


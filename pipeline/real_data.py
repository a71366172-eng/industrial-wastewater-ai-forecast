"""實廠與環境部申報資料的正規化及品質檢查。"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterable


REQUIRED_PLANT_COLUMNS = {
    "timestamp", "plant_id", "influent_ph", "influent_conductivity_us_cm",
    "influent_ss_mg_l", "influent_cod_mg_l", "effluent_ph",
    "effluent_ss_mg_l", "effluent_cod_mg_l", "quality_flag",
}
OPTIONAL_OPERATION_COLUMNS = {
    "influent_flow_m3_h", "coagulant_dose_mg_l", "polymer_dose_mg_l",
    "aeration_do_mg_l", "sludge_concentration_mg_l", "discharge_point", "sample_type",
}
MOENV_REQUIRED_COLUMNS = {
    "EMS_NO", "PER_NO", "LET", "LET_WATERTYPE", "EMI_SDATE", "EMI_EDATE",
    "EMI_WATER", "EMI_ITEM", "EMI_VALUE", "EMI_UNITS",
}


@dataclass
class ValidationReport:
    rows: int = 0
    accepted: int = 0
    rejected: int = 0
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return not self.errors and self.accepted > 0


def _number(value: str | None) -> float | None:
    if value is None or not value.strip() or value.strip() in {"?", "NA", "N/A", "null"}:
        return None
    return float(value.strip().replace(",", "."))


def _timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.strip().replace("Z", "+00:00"))


def validate_plant_csv(path: Path) -> ValidationReport:
    report = ValidationReport()
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        columns = set(reader.fieldnames or [])
        missing = sorted(REQUIRED_PLANT_COLUMNS - columns)
        if missing:
            report.errors.append("缺少必要欄位：" + ", ".join(missing))
            return report
        previous_by_plant: dict[str, datetime] = {}
        for line, row in enumerate(reader, 2):
            report.rows += 1
            try:
                when = _timestamp(row["timestamp"])
                plant = row["plant_id"].strip()
                if not plant:
                    raise ValueError("plant_id 空白")
                if row["quality_flag"].strip().lower() not in {"valid", "review"}:
                    report.rejected += 1
                    continue
                values = {name: _number(row.get(name)) for name in REQUIRED_PLANT_COLUMNS if name not in {"timestamp", "plant_id", "quality_flag"}}
                if values["influent_ph"] is not None and not 0 <= values["influent_ph"] <= 14:
                    raise ValueError("influent_ph 超出 0–14")
                if values["effluent_ph"] is not None and not 0 <= values["effluent_ph"] <= 14:
                    raise ValueError("effluent_ph 超出 0–14")
                nonnegative = [v for key, v in values.items() if key not in {"influent_ph", "effluent_ph"}]
                if any(v is not None and v < 0 for v in nonnegative):
                    raise ValueError("濃度或導電度不可為負值")
                if plant in previous_by_plant and when < previous_by_plant[plant]:
                    report.warnings.append(f"第 {line} 列時間早於同廠前一筆，訓練前將按時間排序")
                previous_by_plant[plant] = when
                report.accepted += 1
            except (ValueError, TypeError) as exc:
                report.rejected += 1
                report.errors.append(f"第 {line} 列：{exc}")
    if report.rows and report.accepted / report.rows < 0.8:
        report.warnings.append("有效資料低於 80%，暫不建議啟動模型訓練")
    missing_optional = sorted(OPTIONAL_OPERATION_COLUMNS - columns)
    if missing_optional:
        report.warnings.append("缺少部分操作特徵，可能降低提前預報能力：" + ", ".join(missing_optional))
    return report


def normalize_moenv_rows(rows: Iterable[dict[str, str]]) -> tuple[list[dict], ValidationReport]:
    """將下載後的 EMS_S_03 CSV 列轉為長表；不把它誤當逐時感測資料。"""
    rows = list(rows)
    report = ValidationReport(rows=len(rows))
    if not rows:
        report.errors.append("官方申報資料為空")
        return [], report
    missing = sorted(MOENV_REQUIRED_COLUMNS - set(rows[0]))
    if missing:
        report.errors.append("EMS_S_03 缺少欄位：" + ", ".join(missing))
        return [], report
    normalized: list[dict] = []
    for index, row in enumerate(rows, 2):
        try:
            value = _number(row.get("EMI_VALUE"))
            if value is None:
                report.rejected += 1
                continue
            normalized.append({
                "plant_id": row["EMS_NO"].strip(),
                "permit_id": row["PER_NO"].strip(),
                "discharge_point": row["LET"].strip(),
                "receiving_water": row["LET_WATERTYPE"].strip(),
                "period_start": row["EMI_SDATE"].strip(),
                "period_end": row["EMI_EDATE"].strip(),
                "discharge_volume": _number(row.get("EMI_WATER")),
                "parameter": row["EMI_ITEM"].strip(),
                "value": value,
                "unit": row["EMI_UNITS"].strip(),
                "source": "MOENV EMS_S_03",
                "temporal_resolution": "reporting_period",
            })
            report.accepted += 1
        except (ValueError, TypeError) as exc:
            report.rejected += 1
            report.errors.append(f"第 {index} 列：{exc}")
    return normalized, report


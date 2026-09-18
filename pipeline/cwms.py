"""環境部 CWMS 公開資料的安全驗證與正規化函式。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import re
from typing import Any, Iterable
from urllib.parse import urlencode


API_BASE = "https://data.moenv.gov.tw/api/v2"
REQUIRED_COLUMNS = (
    "cno", "abbr", "dp_no", "desp", "m_date", "m_time", "m_val",
    "status", "unit", "std1", "std2", "std_s", "twd97x", "twd97y",
    "wgs84x", "wgs84y",
)
_DATA_KEYS = ("data", "records", "result")
_DATASET_RE = re.compile(r"^[a-z0-9_]+$")


class MetricMappingError(ValueError):
    """資料沒有已確認的測項對照時，不允許輸出觀測快照。"""


@dataclass(frozen=True)
class ValidationReport:
    row_count: int
    missing_columns: tuple[str, ...]
    invalid_value_rows: tuple[int, ...]
    invalid_timestamp_rows: tuple[int, ...]
    units: tuple[str, ...]
    statuses: tuple[str, ...]
    metric_mapping_status: str
    errors: tuple[str, ...]

    @property
    def can_publish(self) -> bool:
        return not self.errors and self.row_count > 0


def build_api_url(dataset_code: str, api_key: str, limit: int = 1000, sort: str = "ImportDate desc") -> str:
    """組合環境部 API URL；金鑰由呼叫端提供，不在此儲存。"""

    if not api_key:
        raise ValueError("MOENV_API_KEY is required")
    if not _DATASET_RE.fullmatch(dataset_code):
        raise ValueError("dataset_code must contain lowercase letters, digits, or underscores")
    if limit < 1 or limit > 1000:
        raise ValueError("limit must be between 1 and 1000")
    query = urlencode({
        "format": "JSON",
        "limit": str(limit),
        "sort": sort,
        "api_key": api_key,
    })
    return f"{API_BASE}/{dataset_code}?{query}"


def extract_rows(payload: Any) -> list[dict[str, Any]]:
    """從已解析的 JSON 取出資料列，拒絕未知回應形狀。"""

    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict):
        rows = next((payload[key] for key in _DATA_KEYS if isinstance(payload.get(key), list)), None)
        if rows is None:
            raise ValueError("unsupported API response shape")
    else:
        raise ValueError("API response must be a JSON list or object")
    if not all(isinstance(row, dict) for row in rows):
        raise ValueError("API rows must be JSON objects")
    return [dict(row) for row in rows]


def _lower_keys(row: dict[str, Any]) -> dict[str, Any]:
    return {str(key).lower(): value for key, value in row.items()}


def _parse_number(value: Any) -> float:
    if value is None or str(value).strip() == "":
        raise ValueError("empty numeric value")
    return float(str(value).strip().replace(",", ""))


def _parse_timestamp(date_value: Any, time_value: Any) -> str:
    date_text = str(date_value or "").strip().replace("/", "-")
    time_text = str(time_value or "").strip()
    if not date_text or not time_text:
        raise ValueError("date and time are required")
    value = datetime.fromisoformat(f"{date_text}T{time_text}")
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone(timedelta(hours=8)))
    return value.isoformat()


def _mapping_status(metric_mapping: dict[str, str] | None) -> str:
    if not metric_mapping:
        return "unresolved"
    if not metric_mapping.get("metric_id") or not metric_mapping.get("metric_name"):
        return "unresolved"
    return "confirmed"


def validate_rows(rows: Iterable[dict[str, Any]], metric_mapping: dict[str, str] | None = None) -> ValidationReport:
    """檢查欄位、數值、時間與測項對照；不猜測 m_val 的物理意義。"""

    rows = list(rows)
    errors: list[str] = []
    missing: set[str] = set()
    invalid_values: list[int] = []
    invalid_timestamps: list[int] = []
    units: set[str] = set()
    statuses: set[str] = set()

    for index, original in enumerate(rows):
        row = _lower_keys(original)
        missing.update(set(REQUIRED_COLUMNS).difference(row.keys()))
        if "m_val" in row:
            try:
                _parse_number(row["m_val"])
            except (TypeError, ValueError):
                invalid_values.append(index)
        if "m_date" in row and "m_time" in row:
            try:
                _parse_timestamp(row["m_date"], row["m_time"])
            except (TypeError, ValueError):
                invalid_timestamps.append(index)
        if row.get("unit") not in (None, ""):
            units.add(str(row["unit"]))
        if row.get("status") not in (None, ""):
            statuses.add(str(row["status"]))

    if not rows:
        errors.append("no rows")
    if missing:
        errors.append(f"missing columns: {', '.join(sorted(missing))}")
    if invalid_values:
        errors.append(f"invalid m_val rows: {', '.join(map(str, invalid_values))}")
    if invalid_timestamps:
        errors.append(f"invalid timestamp rows: {', '.join(map(str, invalid_timestamps))}")
    mapping_status = _mapping_status(metric_mapping)
    if mapping_status != "confirmed":
        errors.append("metric mapping is unresolved")

    return ValidationReport(
        row_count=len(rows),
        missing_columns=tuple(sorted(missing)),
        invalid_value_rows=tuple(invalid_values),
        invalid_timestamp_rows=tuple(invalid_timestamps),
        units=tuple(sorted(units)),
        statuses=tuple(sorted(statuses)),
        metric_mapping_status=mapping_status,
        errors=tuple(errors),
    )


def normalize_row(row: dict[str, Any], metric_mapping: dict[str, str] | None) -> dict[str, Any]:
    """在測項對照已確認後，輸出前端 observations.json 的一筆資料。"""

    if _mapping_status(metric_mapping) != "confirmed":
        raise MetricMappingError("metric mapping is unresolved")
    lowered = _lower_keys(row)
    try:
        value = _parse_number(lowered["m_val"])
        observed_at = _parse_timestamp(lowered["m_date"], lowered["m_time"])
    except KeyError as exc:
        raise ValueError(f"missing field: {exc.args[0]}") from exc
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid row: {exc}") from exc
    return {
        "observed_at": observed_at,
        "value": value,
        "unit": str(lowered.get("unit") or ""),
        "quality_status": str(lowered.get("status") or "unknown"),
        "metric_id": metric_mapping["metric_id"],
        "metric_name": metric_mapping["metric_name"],
        "source_object_id": str(lowered.get("cno") or ""),
        "source_position_id": str(lowered.get("dp_no") or ""),
    }

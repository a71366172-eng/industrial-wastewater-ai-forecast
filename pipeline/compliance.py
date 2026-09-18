"""法規限值判讀核心。

本模組只比較數值與已選定的設定檔，不推定工廠適用哪一套法規。
AI 預測結果回傳 forecast_* 狀態，避免與正式實測合規判定混淆。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


AssessmentStatus = Literal[
    "unassessed",
    "forecast_below_limit",
    "forecast_near_limit",
    "forecast_exceeds_limit",
]


@dataclass(frozen=True)
class Assessment:
    pollutant: str
    predicted_value: float | None
    status: AssessmentStatus
    margin: float | None
    utilization: float | None
    message: str


def assess_maximum(
    pollutant: str,
    predicted_value: float | None,
    maximum: float | None,
    *,
    warning_ratio: float = 0.8,
) -> Assessment:
    """比較最大限值；margin 為限值減預測值。"""
    if predicted_value is None or maximum is None or maximum <= 0:
        return Assessment(pollutant, predicted_value, "unassessed", None, None, "缺少預測值或適用限值")
    utilization = predicted_value / maximum
    margin = maximum - predicted_value
    if predicted_value > maximum:
        status, message = "forecast_exceeds_limit", "預測值超出所選限值"
    elif utilization >= warning_ratio:
        status, message = "forecast_near_limit", "預測值接近所選限值"
    else:
        status, message = "forecast_below_limit", "預測值低於所選限值"
    return Assessment(pollutant, predicted_value, status, margin, utilization, message)


def assess_range(
    pollutant: str,
    predicted_value: float | None,
    minimum: float | None,
    maximum: float | None,
    *,
    warning_fraction: float = 0.1,
) -> Assessment:
    """比較上下限；margin 為預測值距離最近界限的距離。"""
    if predicted_value is None or minimum is None or maximum is None or minimum >= maximum:
        return Assessment(pollutant, predicted_value, "unassessed", None, None, "缺少預測值或有效範圍")
    span = maximum - minimum
    margin = min(predicted_value - minimum, maximum - predicted_value)
    if predicted_value < minimum or predicted_value > maximum:
        return Assessment(pollutant, predicted_value, "forecast_exceeds_limit", margin, 1.0, "預測值超出所選範圍")
    edge_fraction = margin / span
    if edge_fraction <= warning_fraction:
        return Assessment(pollutant, predicted_value, "forecast_near_limit", margin, 1.0 - edge_fraction, "預測值接近所選範圍界限")
    return Assessment(pollutant, predicted_value, "forecast_below_limit", margin, 1.0 - edge_fraction, "預測值位於所選範圍內")


def profile_is_applicable(profile: dict, plant: dict) -> tuple[bool, list[str]]:
    """檢查明示條件是否相符；不嘗試解釋未提供的許可或地方規則。"""
    missing = [key for key in ("industry", "dischargeRoute", "jurisdiction") if not plant.get(key)]
    if missing:
        return False, [f"缺少 {key}" for key in missing]
    reasons: list[str] = []
    for key in ("industry", "dischargeRoute", "jurisdiction"):
        if profile.get(key) != plant.get(key):
            reasons.append(f"{key} 不符合設定檔")
    if plant.get("stricterRequirementExists"):
        reasons.append("存在較嚴個案條件，必須使用覆寫後設定檔")
    return not reasons, reasons


"""訓練 UCI 放流水 SS-S / DQO-S 原型模型。

用途僅限方法驗證。UCI Water Treatment Plant 是西班牙都市污水資料，
不可用來宣稱符合臺灣化工業放流水標準。
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


COLUMNS = [
    "DATE", "Q-E", "ZN-E", "PH-E", "DBO-E", "DQO-E", "SS-E", "SSV-E", "SED-E", "COND-E",
    "PH-P", "DBO-P", "SS-P", "SSV-P", "SED-P", "COND-P", "PH-D", "DBO-D", "DQO-D", "SS-D",
    "SSV-D", "SED-D", "COND-D", "PH-S", "DBO-S", "DQO-S", "SS-S", "SSV-S", "SED-S", "COND-S",
    "RD-DBO-P", "RD-SS-P", "RD-SED-P", "RD-DBO-S", "RD-DQO-S", "RD-DBO-G", "RD-DQO-G", "RD-SS-G", "RD-SED-G",
]
FEATURES = ["PH-E", "COND-E", "SS-E", "DQO-E"]
TARGETS = ["SS-S", "DQO-S"]


def parse_number(raw: str) -> float:
    raw = raw.strip()
    if not raw or raw == "?":
        return np.nan
    return float(raw.replace(",", "."))


def parse_date(raw: str) -> datetime:
    cleaned = raw.strip()
    if not cleaned.startswith("D-"):
        raise ValueError(f"不支援的日期：{raw}")
    return datetime.strptime(cleaned[2:], "%d/%m/%y")


def load_rows(path: Path) -> list[dict[str, float | str]]:
    rows: list[dict[str, float | str]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        if not line.strip():
            continue
        parts = [item.strip() for item in line.split(",")]
        if len(parts) != len(COLUMNS):
            raise ValueError(f"第 {line_number} 列欄位數為 {len(parts)}，預期 {len(COLUMNS)}")
        row: dict[str, float | str] = {"DATE": parts[0]}
        row.update({name: parse_number(value) for name, value in zip(COLUMNS[1:], parts[1:])})
        rows.append(row)
    if not rows:
        raise ValueError("資料檔沒有可用列")
    return sorted(rows, key=lambda row: parse_date(str(row["DATE"])))


def _metrics(actual: np.ndarray, predicted: np.ndarray, baseline: np.ndarray) -> dict:
    mae = float(np.mean(np.abs(actual - predicted)))
    baseline_mae = float(np.mean(np.abs(actual - baseline)))
    rmse = float(np.sqrt(np.mean((actual - predicted) ** 2)))
    denominator = float(np.sum((actual - actual.mean()) ** 2))
    r2 = 1.0 - float(np.sum((actual - predicted) ** 2)) / denominator if denominator else 0.0
    return {
        "mae": mae,
        "rmse": rmse,
        "r2": r2,
        "medianBaselineMae": baseline_mae,
        "beatsBaseline": mae < baseline_mae,
        "improvementPercent": ((baseline_mae - mae) / baseline_mae * 100.0) if baseline_mae else 0.0,
    }


def train_target(rows: list[dict[str, float | str]], target: str, alpha: float = 1.0) -> dict:
    usable = [row for row in rows if not np.isnan(float(row[target]))]
    if len(usable) < 30:
        raise ValueError(f"{target} 可用資料不足：{len(usable)}")
    split = int(len(usable) * 0.8)
    train, test = usable[:split], usable[split:]
    x_train = np.array([[float(row[name]) for name in FEATURES] for row in train], dtype=float)
    x_test = np.array([[float(row[name]) for name in FEATURES] for row in test], dtype=float)
    y_train = np.array([float(row[target]) for row in train], dtype=float)
    y_test = np.array([float(row[target]) for row in test], dtype=float)

    medians = np.nanmedian(x_train, axis=0)
    x_train = np.where(np.isnan(x_train), medians, x_train)
    x_test = np.where(np.isnan(x_test), medians, x_test)
    means = x_train.mean(axis=0)
    scales = x_train.std(axis=0)
    scales[scales == 0] = 1.0
    standardized_train = (x_train - means) / scales
    standardized_test = (x_test - means) / scales
    target_mean = float(y_train.mean())
    penalty = max(float(alpha), 0.0) * np.eye(len(FEATURES))
    coefficients = np.linalg.solve(
        standardized_train.T @ standardized_train + penalty,
        standardized_train.T @ (y_train - target_mean),
    )
    predicted = target_mean + standardized_test @ coefficients
    baseline_value = float(np.median(y_train))
    metrics = _metrics(y_test, predicted, np.full_like(y_test, baseline_value))
    residuals = np.sort(y_test - predicted)

    return {
        "target": target,
        "features": FEATURES,
        "rows": {"total": len(usable), "train": len(train), "test": len(test)},
        "dateRange": {"first": usable[0]["DATE"], "last": usable[-1]["DATE"]},
        "split": "chronological first 80% train / last 20% test",
        "metrics": metrics,
        "uncertainty": {
            "method": "held-out empirical residual distribution",
            "interval": "central 80 percent",
            "testResiduals": residuals.tolist(),
            "sampleCount": len(residuals),
            "limitations": "Research estimate; not a calibrated regulatory exceedance probability",
        },
        "parameters": {
            "featureMedians": medians.tolist(),
            "featureMeans": means.tolist(),
            "featureScales": scales.tolist(),
            "coefficients": coefficients.tolist(),
            "intercept": target_mean,
            "alpha": float(alpha),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("data/public/water-treatment.data"))
    parser.add_argument("--output", type=Path, default=Path("frontend/public/data/effluent-model-v4.json"))
    args = parser.parse_args()
    rows = load_rows(args.input)
    artifact = {
        "schemaVersion": "1.1.0",
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "modelType": "numpy-ridge-regression-prototype",
        "deploymentStatus": "research_only",
        "sourceDataset": "UCI Water Treatment Plant",
        "limitations": [
            "西班牙都市污水歷史資料，不代表臺灣化工業製程",
            "僅使用四個進流水特徵，未含流量、加藥、曝氣與水力停留時間",
            "模型輸出不可作為正式法規合規證明",
        ],
        "models": {target: train_target(rows, target) for target in TARGETS},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    for target, result in artifact["models"].items():
        metrics = result["metrics"]
        print(f"{target}: MAE={metrics['mae']:.3f}, baseline={metrics['medianBaselineMae']:.3f}, beats={metrics['beatsBaseline']}")
    print(args.output)


if __name__ == "__main__":
    main()

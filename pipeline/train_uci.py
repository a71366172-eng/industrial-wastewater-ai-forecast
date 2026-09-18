"""Train the four-input UCI prototype and export a browser-readable artifact."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from pipeline.modeling import evaluate, fit_ridge, split_chronologically
from pipeline.uci import FEATURES, TARGET, TreatmentRow, load_dataset


FEATURE_META = {
    "PH-E": {"label": "進水 pH", "unit": "pH"},
    "COND-E": {"label": "進水導電度", "unit": "µS/cm"},
    "SS-E": {"label": "進水懸浮固體（SS）", "unit": "mg/L"},
    "DQO-E": {"label": "進水化學需氧量（COD）", "unit": "mg/L"},
}


def _choose_alpha(training, validation):
    candidates = []
    for alpha in (0.01, 0.1, 1.0, 10.0, 100.0):
        model = fit_ridge(training, alpha)
        metrics = evaluate(model, training, validation)
        candidates.append((metrics["model_mae"], alpha))
    return min(candidates)[1]


def _range(rows: list[TreatmentRow], name: str) -> tuple[float, float]:
    values = [float(row.features[name]) for row in rows if row.features[name] is not None]
    return min(values), max(values)


def build_artifact(rows: list[TreatmentRow], data_report: dict) -> dict:
    training, validation, test = split_chronologically(rows)
    if min(len(training), len(validation), len(test)) < 1:
        raise ValueError("at least five dated usable rows are required")
    alpha = _choose_alpha(training, validation)
    development = training + validation
    model = fit_ridge(development, alpha)
    metrics = evaluate(model, development, test)
    feature_meta = []
    for name in FEATURES:
        lower, upper = _range(development, name)
        feature_meta.append({"field": name, **FEATURE_META[name], "min": lower, "max": upper})
    test_cases = [
        {
            "date": row.date.isoformat(),
            "inputs": row.features,
            "actual": row.target,
            "predicted": model.predict(row.features),
        }
        for row in test
    ]
    return {
        "schema_version": "2.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "historical-research",
        "source": {
            "name": "UCI Water Treatment Plant",
            "url": "https://archive.ics.uci.edu/dataset/106/water+treatment+plant",
            "scope": "1990–1991 urban wastewater daily measurements",
        },
        "features": feature_meta,
        "target": {
            "field": TARGET,
            "label": "初沉池 SS 去除效率",
            "unit": "%",
            "warning_threshold": 50,
            "threshold_kind": "research",
        },
        "split": {"train": len(training), "validation": len(validation), "test": len(test)},
        "data_report": data_report,
        "model": {
            "type": "ridge-regression",
            "alpha": model.alpha,
            "intercept": model.intercept,
            "medians": model.medians,
            "means": model.means,
            "scales": model.scales,
            "coefficients": model.coefficients,
        },
        "metrics": metrics,
        "test_cases": test_cases,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    dataset = load_dataset(args.input)
    artifact = build_artifact(dataset.rows, dataset.report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "metrics": artifact["metrics"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

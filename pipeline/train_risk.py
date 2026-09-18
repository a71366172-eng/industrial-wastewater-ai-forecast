"""Add a research risk classifier to the exported efficiency artifact."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pipeline.classification import evaluate_classifier, fit_logistic, label_efficiency
from pipeline.modeling import split_chronologically
from pipeline.uci import load_dataset


def augment_artifact(artifact: dict, rows: list, threshold: float = 50.0) -> dict:
    training, validation, test = split_chronologically(rows)
    model = fit_logistic(training + validation, threshold=threshold)
    metrics = evaluate_classifier(model, test)
    artifact["risk"] = {
        "target": "RD-SS-P below research threshold",
        "threshold": threshold,
        "cutoff": 0.5,
        "metrics": metrics,
        "model": {
            "type": "logistic-regression",
            "intercept": model.intercept,
            "prior": model.prior,
            "medians": model.medians,
            "means": model.means,
            "scales": model.scales,
            "coefficients": model.coefficients,
        },
    }
    test_by_date = {row.date.isoformat(): row for row in test}
    for case in artifact["test_cases"]:
        row = test_by_date.get(case["date"])
        if row is None:
            continue
        probability = model.predict_proba(row.features)
        case["risk_probability"] = probability
        case["risk_actual"] = label_efficiency(row.target, threshold)
    return artifact


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--artifact", required=True, type=Path)
    args = parser.parse_args()
    dataset = load_dataset(args.input)
    artifact = json.loads(args.artifact.read_text(encoding="utf-8"))
    artifact = augment_artifact(artifact, dataset.rows)
    args.artifact.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(artifact["risk"]["metrics"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

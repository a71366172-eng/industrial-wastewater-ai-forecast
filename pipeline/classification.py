"""Research risk classifier built from the same four influent features."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import median
from typing import Iterable

import numpy as np

from pipeline.uci import FEATURES, TreatmentRow


def label_efficiency(value: float, threshold: float) -> int:
    return int(float(value) < float(threshold))


@dataclass(frozen=True)
class LogisticModel:
    feature_names: tuple[str, ...]
    medians: dict[str, float]
    means: dict[str, float]
    scales: dict[str, float]
    coefficients: dict[str, float]
    intercept: float
    threshold: float
    prior: float

    def predict_proba(self, features: dict[str, float | None]) -> float:
        score = self.intercept
        for name in self.feature_names:
            raw = features.get(name)
            value = self.medians[name] if raw is None else float(raw)
            score += self.coefficients[name] * ((value - self.means[name]) / self.scales[name])
        score = max(min(score, 35.0), -35.0)
        return float(1.0 / (1.0 + np.exp(-score)))


def fit_logistic(rows: Iterable[TreatmentRow], threshold: float = 50.0, learning_rate: float = 0.08, steps: int = 2500) -> LogisticModel:
    training = list(rows)
    if not training:
        raise ValueError("training rows are required")
    medians = {
        name: float(median(value for row in training if (value := row.features[name]) is not None))
        for name in FEATURES
    }
    matrix = np.array(
        [[medians[name] if row.features[name] is None else row.features[name] for name in FEATURES] for row in training], dtype=float
    )
    labels = np.array([label_efficiency(row.target, threshold) for row in training], dtype=float)
    means = matrix.mean(axis=0)
    scales = matrix.std(axis=0)
    scales[scales == 0] = 1.0
    x = (matrix - means) / scales
    weights = np.zeros(len(FEATURES), dtype=float)
    intercept = float(np.log((labels.mean() + 1e-6) / (1 - labels.mean() + 1e-6)))
    for _ in range(steps):
        scores = np.clip(intercept + x @ weights, -35, 35)
        probabilities = 1 / (1 + np.exp(-scores))
        error = probabilities - labels
        weights -= learning_rate * (x.T @ error / len(labels))
        intercept -= learning_rate * float(error.mean())
    return LogisticModel(
        feature_names=FEATURES,
        medians=medians,
        means=dict(zip(FEATURES, means.tolist())),
        scales=dict(zip(FEATURES, scales.tolist())),
        coefficients=dict(zip(FEATURES, weights.tolist())),
        intercept=intercept,
        threshold=float(threshold),
        prior=float(labels.mean()),
    )


def evaluate_classifier(model: LogisticModel, rows: Iterable[TreatmentRow], cutoff: float = 0.5) -> dict[str, float | int]:
    test = list(rows)
    actual = [label_efficiency(row.target, model.threshold) for row in test]
    predicted = [int(model.predict_proba(row.features) >= cutoff) for row in test]
    true_positive = sum(a == p == 1 for a, p in zip(actual, predicted))
    false_positive = sum(a == 0 and p == 1 for a, p in zip(actual, predicted))
    false_negative = sum(a == 1 and p == 0 for a, p in zip(actual, predicted))
    events = sum(actual)
    return {
        "test_rows": len(test),
        "test_events": events,
        "predicted_events": sum(predicted),
        "recall": true_positive / events if events else 0.0,
        "precision": true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0,
        "true_positive": true_positive,
        "false_negative": false_negative,
    }

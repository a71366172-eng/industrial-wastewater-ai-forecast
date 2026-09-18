"""Small, reproducible regression helpers for the public UCI prototype."""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from statistics import median
from typing import Iterable

import numpy as np

from pipeline.uci import FEATURES, TreatmentRow


@dataclass(frozen=True)
class RidgeModel:
    feature_names: tuple[str, ...]
    medians: dict[str, float]
    means: dict[str, float]
    scales: dict[str, float]
    coefficients: dict[str, float]
    intercept: float
    alpha: float

    def predict(self, features: dict[str, float | None]) -> float:
        total = self.intercept
        for name in self.feature_names:
            raw_value = features.get(name)
            value = self.medians[name] if raw_value is None else float(raw_value)
            total += self.coefficients[name] * ((value - self.means[name]) / self.scales[name])
        return float(total)


def split_chronologically(rows: Iterable[TreatmentRow]):
    ordered = sorted(rows, key=lambda row: row.date)
    first = int(len(ordered) * 0.6)
    second = int(len(ordered) * 0.8)
    return ordered[:first], ordered[first:second], ordered[second:]


def fit_ridge(rows: Iterable[TreatmentRow], alpha: float = 1.0) -> RidgeModel:
    training = list(rows)
    if not training:
        raise ValueError("training rows are required")
    medians = {
        name: float(median(value for row in training if (value := row.features[name]) is not None))
        for name in FEATURES
    }
    matrix = np.array(
        [[medians[name] if row.features[name] is None else row.features[name] for name in FEATURES] for row in training],
        dtype=float,
    )
    targets = np.array([row.target for row in training], dtype=float)
    means = matrix.mean(axis=0)
    scales = matrix.std(axis=0)
    scales[scales == 0] = 1.0
    standardized = (matrix - means) / scales
    centered_target = targets - targets.mean()
    penalty = max(float(alpha), 0.0) * np.eye(len(FEATURES))
    coefficients = np.linalg.solve(standardized.T @ standardized + penalty, standardized.T @ centered_target)
    return RidgeModel(
        feature_names=FEATURES,
        medians=dict(zip(FEATURES, medians.values())),
        means=dict(zip(FEATURES, means.tolist())),
        scales=dict(zip(FEATURES, scales.tolist())),
        coefficients=dict(zip(FEATURES, coefficients.tolist())),
        intercept=float(targets.mean()),
        alpha=float(alpha),
    )


def _mae(actual: list[float], predicted: list[float]) -> float:
    return sum(abs(left - right) for left, right in zip(actual, predicted)) / len(actual)


def evaluate(model: RidgeModel, training: Iterable[TreatmentRow], test: Iterable[TreatmentRow]) -> dict[str, float | int]:
    training_rows = list(training)
    test_rows = list(test)
    if not training_rows or not test_rows:
        raise ValueError("training and test rows are required")
    actual = [float(row.target) for row in test_rows]
    predicted = [model.predict(row.features) for row in test_rows]
    baseline_value = float(median(row.target for row in training_rows))
    model_mae = _mae(actual, predicted)
    baseline_mae = _mae(actual, [baseline_value] * len(actual))
    rmse = sqrt(sum((left - right) ** 2 for left, right in zip(actual, predicted)) / len(actual))
    average = sum(actual) / len(actual)
    denominator = sum((value - average) ** 2 for value in actual)
    r2 = 1 - sum((left - right) ** 2 for left, right in zip(actual, predicted)) / denominator if denominator else 0.0
    return {
        "test_rows": len(test_rows),
        "model_mae": model_mae,
        "baseline_mae": baseline_mae,
        "rmse": rmse,
        "r2": r2,
        "baseline_value": baseline_value,
        "improvement_percent": ((baseline_mae - model_mae) / baseline_mae * 100) if baseline_mae else 0.0,
    }

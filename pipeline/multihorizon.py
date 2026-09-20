"""Leakage-safe 1/3/6-hour effluent exceedance probability models."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable
import numpy as np

BASE_FIELDS = ('influent_ph', 'influent_conductivity', 'influent_ss', 'influent_cod')

@dataclass(frozen=True)
class HourlyRow:
    timestamp: datetime
    plant_id: str
    influent_ph: float
    influent_conductivity: float
    influent_ss: float
    influent_cod: float
    effluent_ss: float
    effluent_cod: float

@dataclass(frozen=True)
class HorizonExample:
    timestamp: datetime
    plant_id: str
    features: dict[str, float]
    labels: dict[int, int]

@dataclass(frozen=True)
class HorizonModel:
    horizon: int
    feature_names: tuple[str, ...]
    means: dict[str, float]
    scales: dict[str, float]
    coefficients: dict[str, float]
    intercept: float
    prior: float

    def predict_proba(self, features: dict[str, float]) -> float:
        score = self.intercept
        for name in self.feature_names:
            score += self.coefficients[name] * ((float(features[name]) - self.means[name]) / self.scales[name])
        score = max(-35.0, min(35.0, score))
        return float(1 / (1 + np.exp(-score)))


def _features(history: list[HourlyRow]) -> dict[str, float]:
    current = history[-1]
    previous = history[-2] if len(history) > 1 else current
    window = history[-6:]
    result: dict[str, float] = {}
    for name in BASE_FIELDS:
        value = float(getattr(current, name))
        result[name] = value
        result[f'{name}_delta_1h'] = value - float(getattr(previous, name))
        result[f'{name}_mean_6h'] = float(np.mean([getattr(item, name) for item in window]))
    return result


def build_examples(rows: Iterable[HourlyRow], horizons=(1, 3, 6), cod_limit=100.0, ss_limit=30.0) -> list[HorizonExample]:
    horizons = tuple(sorted(set(int(value) for value in horizons)))
    if not horizons or horizons[0] < 1:
        raise ValueError('horizons must be positive hours')
    by_plant: dict[str, list[HourlyRow]] = {}
    for item in rows:
        by_plant.setdefault(item.plant_id, []).append(item)
    examples: list[HorizonExample] = []
    for plant_id, plant_rows in by_plant.items():
        ordered = sorted(plant_rows, key=lambda item: item.timestamp)
        for index, current in enumerate(ordered):
            max_end = current.timestamp + timedelta(hours=max(horizons))
            future_all = [item for item in ordered[index + 1:] if item.timestamp <= max_end]
            if not future_all or future_all[-1].timestamp < max_end:
                continue
            labels = {}
            for horizon in horizons:
                end = current.timestamp + timedelta(hours=horizon)
                future = [item for item in future_all if item.timestamp <= end]
                labels[horizon] = int(any(item.effluent_cod > cod_limit or item.effluent_ss > ss_limit for item in future))
            examples.append(HorizonExample(current.timestamp, plant_id, _features(ordered[:index + 1]), labels))
    return sorted(examples, key=lambda item: item.timestamp)


def split_examples(examples: Iterable[HorizonExample]):
    ordered = sorted(examples, key=lambda item: item.timestamp)
    if len(ordered) < 10:
        raise ValueError('at least 10 hourly examples are required')
    train_end = max(1, int(len(ordered) * 0.6))
    validation_end = max(train_end + 1, int(len(ordered) * 0.8))
    return ordered[:train_end], ordered[train_end:validation_end], ordered[validation_end:]


def fit_horizon_model(examples: Iterable[HorizonExample], horizon: int, learning_rate=0.05, steps=2000) -> HorizonModel:
    training = list(examples)
    if not training:
        raise ValueError('training examples are required')
    feature_names = tuple(training[0].features)
    matrix = np.array([[item.features[name] for name in feature_names] for item in training], dtype=float)
    labels = np.array([item.labels[horizon] for item in training], dtype=float)
    means = matrix.mean(axis=0)
    scales = matrix.std(axis=0)
    scales[scales == 0] = 1.0
    x = (matrix - means) / scales
    weights = np.zeros(len(feature_names))
    prior = float(labels.mean())
    intercept = float(np.log((prior + 1e-6) / (1 - prior + 1e-6)))
    for _ in range(steps):
        probabilities = 1 / (1 + np.exp(-np.clip(intercept + x @ weights, -35, 35)))
        error = probabilities - labels
        weights -= learning_rate * (x.T @ error / len(labels))
        intercept -= learning_rate * float(error.mean())
    return HorizonModel(horizon, feature_names, dict(zip(feature_names, means)), dict(zip(feature_names, scales)), dict(zip(feature_names, weights)), intercept, prior)


def evaluate_horizon(model: HorizonModel, examples: Iterable[HorizonExample], cutoff=0.5) -> dict:
    test = list(examples)
    labels = np.array([item.labels[model.horizon] for item in test], dtype=float)
    probabilities = np.array([model.predict_proba(item.features) for item in test])
    predictions = probabilities >= cutoff
    events = int(labels.sum())
    true_positive = int(((predictions == 1) & (labels == 1)).sum())
    false_positive = int(((predictions == 1) & (labels == 0)).sum())
    return {
        'rows': len(test), 'events': events,
        'brier_score': float(np.mean((probabilities - labels) ** 2)) if len(test) else None,
        'recall': true_positive / events if events else 0.0,
        'precision': true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0,
        'baseline_brier_score': float(np.mean((model.prior - labels) ** 2)) if len(test) else None,
    }

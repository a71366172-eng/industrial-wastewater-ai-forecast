"""Train 1/3/6-hour exceedance probability baselines from plant hourly CSV."""
from __future__ import annotations
import argparse, csv, json
from datetime import datetime, timezone
from pathlib import Path
from pipeline.multihorizon import HourlyRow, build_examples, evaluate_horizon, fit_horizon_model, split_examples


def load_rows(path: Path) -> list[HourlyRow]:
    rows = []
    with path.open('r', encoding='utf-8-sig', newline='') as stream:
        for item in csv.DictReader(stream):
            if item.get('quality_flag', '').lower() not in {'valid', 'review'}:
                continue
            rows.append(HourlyRow(
                timestamp=datetime.fromisoformat(item['timestamp'].replace('Z', '+00:00')),
                plant_id=item['plant_id'], influent_ph=float(item['influent_ph']),
                influent_conductivity=float(item['influent_conductivity_us_cm']),
                influent_ss=float(item['influent_ss_mg_l']), influent_cod=float(item['influent_cod_mg_l']),
                effluent_ss=float(item['effluent_ss_mg_l']), effluent_cod=float(item['effluent_cod_mg_l']),
            ))
    return rows


def export_model(model):
    return {'horizonHours': model.horizon, 'featureNames': model.feature_names, 'means': model.means, 'scales': model.scales, 'coefficients': model.coefficients, 'intercept': model.intercept, 'prior': model.prior}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('csv', type=Path)
    parser.add_argument('--output', type=Path, default=Path('frontend/public/data/multihorizon-model.json'))
    args = parser.parse_args()
    rows = load_rows(args.csv)
    examples = build_examples(rows)
    minimum_rows = 2160
    event_counts = {str(horizon): sum(item.labels[horizon] for item in examples) for horizon in (1, 3, 6)}
    if len(examples) < minimum_rows or any(count < 30 for count in event_counts.values()):
        print(json.dumps({'status': 'insufficient_data', 'examples': len(examples), 'requiredExamples': minimum_rows, 'events': event_counts, 'requiredEventsPerHorizon': 30}, ensure_ascii=False))
        return 2
    train, validation, test = split_examples(examples)
    models = {}
    for horizon in (1, 3, 6):
        model = fit_horizon_model(train, horizon)
        models[str(horizon)] = {**export_model(model), 'validation': evaluate_horizon(model, validation), 'test': evaluate_horizon(model, test)}
    artifact = {'schemaVersion': '1.0.0', 'createdAt': datetime.now(timezone.utc).isoformat(), 'status': 'research_only', 'target': 'future_any_COD_or_SS_reference_exceedance', 'split': {'train': len(train), 'validation': len(validation), 'test': len(test)}, 'models': models, 'reinforcementLearning': 'deferred_until_safe_simulator_or_offline_policy_evaluation'}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'output': str(args.output), 'examples': len(examples)}, ensure_ascii=False))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())

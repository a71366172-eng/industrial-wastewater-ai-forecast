"""Verify the v4 effluent model and Taiwan chemical legal profile before release."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from train_effluent_v4 import TARGETS, load_rows, train_target


def _compare(expected: Any, actual: Any, path: str, errors: list[str]) -> None:
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            errors.append(f'{path} 型態不符')
            return
        for key, value in expected.items():
            if key not in actual:
                errors.append(f'{path}.{key} 缺少')
            else:
                _compare(value, actual[key], f'{path}.{key}', errors)
    elif isinstance(expected, list):
        if not isinstance(actual, list) or len(expected) != len(actual):
            errors.append(f'{path} 陣列長度不符')
            return
        for index, value in enumerate(expected):
            _compare(value, actual[index], f'{path}[{index}]', errors)
    elif isinstance(expected, float):
        if not isinstance(actual, (int, float)) or abs(expected - float(actual)) > 1e-8:
            errors.append(f'{path} 數值不符')
    elif expected != actual:
        errors.append(f'{path} 不符')


def verify_artifacts(data_path: Path, model_path: Path, profile_path: Path) -> dict:
    errors: list[str] = []
    try:
        artifact = json.loads(model_path.read_text(encoding='utf-8'))
        profiles = json.loads(profile_path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as exc:
        return {'ok': False, 'errors': [str(exc)]}

    if artifact.get('deploymentStatus') != 'research_only':
        errors.append('v4 模型部署狀態必須維持 research_only')
    if artifact.get('sourceDataset') != 'UCI Water Treatment Plant':
        errors.append('v4 模型資料來源不符')
    if set(artifact.get('models', {})) != set(TARGETS):
        errors.append('v4 模型必須同時包含 SS-S 與 DQO-S')
    else:
        rows = load_rows(data_path)
        for target in TARGETS:
            regenerated = train_target(rows, target)
            _compare(regenerated, artifact['models'][target], f'models.{target}', errors)

    profile_list = profiles.get('profiles', [])
    if len(profile_list) != 1:
        errors.append('目前必須且只能有一個已核對的化工業中央設定檔')
    else:
        profile = profile_list[0]
        if profile.get('industry') != '化工業':
            errors.append('預設法規設定檔必須為化工業')
        if profile.get('dischargeRoute') != 'surface_water':
            errors.append('預設法規情境必須為直接排放至地面水體')
        limits = profile.get('limits', {})
        if limits.get('ss', {}).get('max') != 30:
            errors.append('SS 中央基準必須為 30 mg/L')
        if limits.get('cod', {}).get('max') != 100:
            errors.append('COD 中央基準必須為 100 mg/L')
        if (limits.get('ph', {}).get('min'), limits.get('ph', {}).get('max')) != (6.0, 9.0):
            errors.append('pH 中央基準必須為 6.0–9.0')
        if not profile.get('source', {}).get('attachmentUrl'):
            errors.append('法規設定檔缺少官方附表來源')
        if not profile.get('caveat'):
            errors.append('法規設定檔缺少個案加嚴警語')

    return {'ok': not errors, 'errors': errors}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, default=Path('data/public/water-treatment.data'))
    parser.add_argument('--model', type=Path, default=Path('frontend/public/data/effluent-model-v4.json'))
    parser.add_argument('--profiles', type=Path, default=Path('frontend/public/data/legal-profiles.json'))
    args = parser.parse_args()
    report = verify_artifacts(args.input, args.model, args.profiles)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report['ok'] else 1)


if __name__ == '__main__':
    main()

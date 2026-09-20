"""Import a manually downloaded MOENV EMS_S_03 CSV and create a safe summary."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from pipeline.moenv_ems import aggregate_public_summary, load_csv_records


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('csv', type=Path)
    parser.add_argument('--raw-output', type=Path, default=Path('data/raw/moenv/ems_s_03-normalized.json'))
    parser.add_argument('--public-output', type=Path, default=Path('frontend/public/data/moenv-ems-summary.json'))
    args = parser.parse_args()

    records = load_csv_records(args.csv)
    args.raw_output.parent.mkdir(parents=True, exist_ok=True)
    args.raw_output.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding='utf-8')

    summary = aggregate_public_summary(records)
    summary['generated_at'] = datetime.now(timezone.utc).isoformat()
    summary['record_count'] = len(records)
    summary['input_mode'] = 'manual_official_csv'
    args.public_output.parent.mkdir(parents=True, exist_ok=True)
    args.public_output.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')

    print(json.dumps({
        'records': len(records),
        'raw_output': str(args.raw_output),
        'public_output': str(args.public_output),
        'parameters': sorted(summary['parameters']),
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

"""Download and sanitize MOENV EMS_S_03 data.

The API key is read only from MOENV_API_KEY and is never written to output.
Raw normalized records stay under data/raw, which is excluded from Git.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from pipeline.moenv_ems import (
    aggregate_public_summary,
    download_public_preview_records,
    download_records,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--raw-output', type=Path, default=Path('data/raw/moenv/ems_s_03-normalized.json'))
    parser.add_argument('--public-output', type=Path, default=Path('frontend/public/data/moenv-ems-summary.json'))
    parser.add_argument('--page-size', type=int, default=1000)
    parser.add_argument('--max-pages', type=int, default=10)
    parser.add_argument('--mode', choices=('auto', 'api-key', 'public-preview'), default='auto')
    args = parser.parse_args()

    api_key = os.environ.get('MOENV_API_KEY', '').strip()
    use_api_key = args.mode == 'api-key' or (args.mode == 'auto' and bool(api_key))
    if use_api_key and not api_key:
        print('MOENV_API_KEY is required in api-key mode; register at https://data.moenv.gov.tw/api_term')
        return 2

    if use_api_key:
        records = download_records(api_key, page_size=args.page_size, max_pages=args.max_pages)
        input_mode = 'member_api'
    else:
        records = download_public_preview_records(page_size=args.page_size, max_pages=args.max_pages)
        input_mode = 'public_preview'
    args.raw_output.parent.mkdir(parents=True, exist_ok=True)
    args.raw_output.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding='utf-8')

    summary = aggregate_public_summary(records)
    summary['generated_at'] = datetime.now(timezone.utc).isoformat()
    summary['record_count'] = len(records)
    summary['input_mode'] = input_mode
    summary['sampling_note'] = '依官方資料預覽排序擷取最新批次；非全資料母體統計' if input_mode == 'public_preview' else '會員 API 分頁批次'
    args.public_output.parent.mkdir(parents=True, exist_ok=True)
    args.public_output.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')

    print(json.dumps({
        'records': len(records),
        'raw_output': str(args.raw_output),
        'public_output': str(args.public_output),
        'parameters': sorted(summary['parameters']),
        'input_mode': input_mode,
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

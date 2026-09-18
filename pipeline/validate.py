"""本機資料驗證命令列工具。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

from .cwms import extract_rows, validate_rows


def _report_dict(report: Any, source_name: str) -> dict[str, Any]:
    return {
        "source_file": source_name,
        "can_publish": report.can_publish,
        "row_count": report.row_count,
        "missing_columns": list(report.missing_columns),
        "invalid_value_rows": list(report.invalid_value_rows),
        "invalid_timestamp_rows": list(report.invalid_timestamp_rows),
        "units": list(report.units),
        "statuses": list(report.statuses),
        "metric_mapping_status": report.metric_mapping_status,
        "errors": list(report.errors),
    }


def validate_file(input_path: Path, output_path: Path, metric_mapping: dict[str, str] | None = None) -> dict[str, Any]:
    """驗證本機 JSON，寫入不含原始值的報告並回傳報告內容。"""

    payload = json.loads(input_path.read_text(encoding="utf-8"))
    rows = extract_rows(payload)
    report = validate_rows(rows, metric_mapping=metric_mapping)
    result = _report_dict(report, input_path.name)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="驗證環境部 CWMS JSON 資料，不直接產生前端快照")
    parser.add_argument("--input", required=True, type=Path, help="本機 JSON 檔案")
    parser.add_argument("--output", required=True, type=Path, help="驗證報告 JSON 路徑")
    parser.add_argument("--metric-id", help="已由人工或官方文件確認的測項 ID")
    parser.add_argument("--metric-name", help="已確認的測項顯示名稱")
    args = parser.parse_args(argv)

    mapping = None
    if args.metric_id or args.metric_name:
        if not args.metric_id or not args.metric_name:
            parser.error("--metric-id and --metric-name must be provided together")
        mapping = {"metric_id": args.metric_id, "metric_name": args.metric_name}

    try:
        result = validate_file(args.input, args.output, metric_mapping=mapping)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"validation failed: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["can_publish"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pipeline.real_data import validate_plant_csv


def main() -> None:
    parser = argparse.ArgumentParser(description="檢查化工廠訓練資料，不會修改原檔")
    parser.add_argument("csv", type=Path)
    args = parser.parse_args()
    report = validate_plant_csv(args.csv)
    print(json.dumps(report.__dict__ | {"valid": report.valid}, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report.valid else 1)


if __name__ == "__main__":
    main()


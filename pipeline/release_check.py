"""Static release guard for the GitHub Pages artifact."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def check_release(root: str | Path) -> dict[str, object]:
    root = Path(root)
    errors: list[str] = []
    entry = root / "frontend" / "index.html"
    model_path = root / "frontend" / "public" / "data" / "uci-model.json"
    if not entry.exists() or "src/app-v3.js" not in entry.read_text(encoding="utf-8"):
        errors.append("v3 entry is missing")
    if not model_path.exists():
        errors.append("model artifact is missing")
    else:
        try:
            model = json.loads(model_path.read_text(encoding="utf-8"))
            if model.get("schema_version") != "2.0":
                errors.append("model schema must be 2.0")
            if not model.get("risk", {}).get("metrics"):
                errors.append("risk metrics are missing")
        except json.JSONDecodeError:
            errors.append("model artifact is invalid JSON")
    return {"ok": not errors, "errors": errors}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()
    result = check_release(args.root)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())


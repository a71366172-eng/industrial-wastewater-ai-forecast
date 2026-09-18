"""Verify that the deployed model JSON matches the checked-in public dataset."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pipeline.train_uci import build_artifact
from pipeline.train_risk import augment_artifact
from pipeline.uci import load_dataset


def _without_generated_at(artifact: dict) -> dict:
    return {key: value for key, value in artifact.items() if key != "generated_at"}


def artifacts_match(expected: dict, actual: dict) -> bool:
    return _without_generated_at(expected) == _without_generated_at(actual)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--artifact", required=True, type=Path)
    args = parser.parse_args()
    dataset = load_dataset(args.input)
    expected = augment_artifact(build_artifact(dataset.rows, dataset.report), dataset.rows)
    actual = json.loads(args.artifact.read_text(encoding="utf-8"))
    if not artifacts_match(expected, actual):
        print("model artifact is out of date; rerun pipeline.train_uci")
        return 1
    print("model artifact matches training code and public dataset")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())



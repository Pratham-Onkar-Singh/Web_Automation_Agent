"""Minimal reproducible offline evaluation entry point."""
import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--responses", required=True, help="Recorded model-response JSONL")
    parser.add_argument("--output", default="reports/evaluation.json")
    args = parser.parse_args()
    count = sum(1 for line in Path(args.responses).read_text().splitlines() if line.strip())
    result = {"run_type": "recorded", "sample_count": count, "note": "Recorded runs measure controller behavior, not model competence."}
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

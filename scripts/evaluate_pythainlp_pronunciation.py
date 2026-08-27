"""Compare current PyThaiNLP W2P output with the candidate pronunciation data."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from pythainlp.transliterate import pronunciate


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_PATH = ROOT / "data" / "thai_one_syllable_test_candidates.json"


def evaluate(data_path: Path) -> tuple[list[dict[str, str]], int]:
    payload = json.loads(data_path.read_text(encoding="utf-8"))
    cases = payload.get("cases", [])
    if not isinstance(cases, list):
        raise ValueError('The data file must contain a "cases" list.')

    results = []
    for case in cases:
        if not isinstance(case, dict):
            continue

        word = case.get("word")
        expected = case.get("pythainlp_pronunciation")
        if not isinstance(word, str) or not isinstance(expected, str):
            continue

        actual = pronunciate(word)
        results.append(
            {
                "word": word,
                "expected": expected,
                "actual": actual,
                "category": str(case.get("category", "uncategorized")),
                "status": "correct" if actual == expected else "incorrect",
            }
        )

    return results, len(cases)


def print_report(results: list[dict[str, str]], total_cases: int, data_path: Path) -> None:
    correct = sum(result["status"] == "correct" for result in results)
    incorrect = len(results) - correct
    skipped = total_cases - len(results)
    percentage = (correct / len(results) * 100) if results else 0

    print("PyThaiNLP W2P pronunciation evaluation")
    print(f"Data: {data_path}")
    print(f"Correct: {correct}/{len(results)} ({percentage:.1f}%)")
    print(f"Incorrect: {incorrect}")
    if skipped:
        print(f"Skipped invalid cases: {skipped}")

    category_counts = Counter(
        result["category"] for result in results if result["status"] == "incorrect"
    )
    if category_counts:
        print("\nIncorrect by category:")
        for category, count in sorted(category_counts.items()):
            print(f"  {category}: {count}")

    failures = [result for result in results if result["status"] == "incorrect"]
    if failures:
        print("\nIncorrect pronunciations:")
        for result in failures:
            print(
                f"  {result['word']}: expected {result['expected']}, "
                f"got {result['actual']}"
            )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate PyThaiNLP W2P pronunciation against the candidate data."
    )
    parser.add_argument(
        "--data",
        type=Path,
        default=DEFAULT_DATA_PATH,
        help="Path to the Thai one-syllable candidate JSON file.",
    )
    args = parser.parse_args()

    results, total_cases = evaluate(args.data)
    print_report(results, total_cases, args.data)


if __name__ == "__main__":
    main()

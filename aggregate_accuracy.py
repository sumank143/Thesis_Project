"""
Step 1 of Results generation: build one clean accuracy summary from the
6 results CSVs -- correct counts by model, prompting condition, and
complexity level. This is the base table almost every Results chart
and the RQ1 narrative will draw from.

Usage:
    python aggregate_accuracy.py
"""
import csv
from collections import defaultdict

RESULT_FILES = [
    "results_gpt.csv", "results_gpt_zeroshot.csv",
    "results_claude.csv", "results_claude_zeroshot.csv",
    "results_gemini.csv", "results_gemini_zeroshot.csv",
]

def split_model_condition(model_field):
    if model_field.endswith("-zeroshot"):
        return model_field[: -len("-zeroshot")], "zero-shot"
    return model_field, "schema-aware"

def main():
    # (model, condition) -> {"ran_ok": n, "correct": n, "total": n}
    overall = defaultdict(lambda: {"ran_ok": 0, "correct": 0, "total": 0})
    # (model, condition, level) -> {"correct": n, "total": n}
    by_level = defaultdict(lambda: {"correct": 0, "total": 0})

    for filename in RESULT_FILES:
        with open(filename, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                model, condition = split_model_condition(row["model"])
                key = (model, condition)
                overall[key]["total"] += 1
                if row["ran_ok"] == "True":
                    overall[key]["ran_ok"] += 1
                if row["correct"] == "True":
                    overall[key]["correct"] += 1

                lkey = (model, condition, row["level"])
                by_level[lkey]["total"] += 1
                if row["correct"] == "True":
                    by_level[lkey]["correct"] += 1

    print("=" * 70)
    print("OVERALL ACCURACY (correct / 50)")
    print("=" * 70)
    print(f"{'model':20s}{'condition':14s}{'ran_ok':>8s}{'correct':>9s}{'total':>7s}")
    with open("accuracy_summary.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["model", "condition", "ran_ok", "correct", "total"])
        for (model, condition), d in sorted(overall.items()):
            print(f"{model:20s}{condition:14s}{d['ran_ok']:>8d}{d['correct']:>9d}{d['total']:>7d}")
            w.writerow([model, condition, d["ran_ok"], d["correct"], d["total"]])

    print()
    print("=" * 70)
    print("ACCURACY BY COMPLEXITY LEVEL (correct / total)")
    print("=" * 70)
    print(f"{'model':20s}{'condition':14s}{'level':>6s}{'correct':>9s}{'total':>7s}")
    with open("accuracy_by_level.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["model", "condition", "level", "correct", "total"])
        for (model, condition, level), d in sorted(by_level.items(), key=lambda x: (x[0][0], x[0][1], int(x[0][2]))):
            print(f"{model:20s}{condition:14s}{level:>6s}{d['correct']:>9d}{d['total']:>7d}")
            w.writerow([model, condition, level, d["correct"], d["total"]])

    print()
    print("Saved: accuracy_summary.csv, accuracy_by_level.csv")

if __name__ == "__main__":
    main()

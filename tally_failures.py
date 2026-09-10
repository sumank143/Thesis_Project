"""
Step 3 of failure-pattern classification (thesis section 3.4/RQ2).

Reads failures_with_suggestions.csv (82 tagged rows) and produces the RQ2
results table: failure category counts broken down by model, by prompting
condition, and by complexity level.

Uses the 'category' column if you've filled it in by hand for a given row
(i.e. you corrected the suggestion), otherwise falls back to
'suggested_category' -- so you don't have to retype all 82 to use this.

Usage:
    python tally_failures.py
"""
import csv
from collections import Counter, defaultdict

INPUT_FILE = "failures_with_suggestions.csv"

def final_category(row):
    return row["category"].strip() if row["category"].strip() else row["suggested_category"]

def split_model_condition(model_field):
    if model_field.endswith("-zeroshot"):
        return model_field[: -len("-zeroshot")], "zero-shot"
    return model_field, "schema-aware"

def main():
    with open(INPUT_FILE, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    by_model_condition = defaultdict(Counter)
    by_level = defaultdict(Counter)
    overall = Counter()

    for row in rows:
        cat = final_category(row)
        base_model, condition = split_model_condition(row["model"])
        by_model_condition[(base_model, condition)][cat] += 1
        by_level[row["level"]][cat] += 1
        overall[cat] += 1

    categories = ["hallucinated_schema", "wrong_join_path", "wrong_aggregation", "wrong_filter", "syntax_error"]
    # include any category actually present that isn't in the standard list (safety net)
    for cat in overall:
        if cat not in categories:
            categories.append(cat)

    print("=" * 70)
    print("OVERALL (all 82 failures)")
    print("=" * 70)
    for cat in categories:
        n = overall.get(cat, 0)
        if n:
            print(f"  {cat:22s} {n:3d}  ({n/len(rows)*100:.0f}%)")
    print(f"  {'TOTAL':22s} {len(rows):3d}")

    print()
    print("=" * 70)
    print("BY MODEL AND PROMPTING CONDITION")
    print("=" * 70)
    header = "model".ljust(20) + "condition".ljust(14) + "".join(c[:12].ljust(13) for c in categories) + "total"
    print(header)
    for (model, condition), counts in sorted(by_model_condition.items()):
        total = sum(counts.values())
        line = model.ljust(20) + condition.ljust(14)
        line += "".join(str(counts.get(c, 0)).ljust(13) for c in categories)
        line += str(total)
        print(line)

    print()
    print("=" * 70)
    print("BY COMPLEXITY LEVEL")
    print("=" * 70)
    header = "level".ljust(8) + "".join(c[:12].ljust(13) for c in categories) + "total"
    print(header)
    for level in sorted(by_level.keys(), key=lambda x: int(x)):
        counts = by_level[level]
        total = sum(counts.values())
        line = str(level).ljust(8)
        line += "".join(str(counts.get(c, 0)).ljust(13) for c in categories)
        line += str(total)
        print(line)

    # also write a CSV version for direct use in the thesis table
    with open("rq2_failure_summary.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["model", "condition"] + categories + ["total"])
        for (model, condition), counts in sorted(by_model_condition.items()):
            w.writerow([model, condition] + [counts.get(c, 0) for c in categories] + [sum(counts.values())])
        w.writerow([])
        w.writerow(["level", ""] + categories + ["total"])
        for level in sorted(by_level.keys(), key=lambda x: int(x)):
            counts = by_level[level]
            w.writerow([f"Level {level}", ""] + [counts.get(c, 0) for c in categories] + [sum(counts.values())])

    print()
    print("Saved: rq2_failure_summary.csv")

if __name__ == "__main__":
    main()

import csv
from collections import defaultdict

RESULT_FILES = [
    "extended_conditions/results_condition1_unaware_gpt.csv",
    "extended_conditions/results_condition1_unaware_gemini.csv",
    "extended_conditions/results_condition2_aware_no_hints_gpt.csv",
    "extended_conditions/results_condition2_aware_no_hints_gemini.csv",
    "extended_conditions/results_condition3_fewshot_gpt.csv",
    "extended_conditions/results_condition3_fewshot_gemini.csv",
]

rows = []
for path in RESULT_FILES:
    with open(path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

print(f"Loaded {len(rows)} result rows from {len(RESULT_FILES)} files")

def to_bool(s):
    return str(s).strip().lower() == "true"

overall = defaultdict(lambda: {"ran_ok": 0, "correct": 0, "total": 0})
by_level = defaultdict(lambda: {"ran_ok": 0, "correct": 0, "total": 0})

for row in rows:
    condition = row["condition"]
    model = row["model"]
    level = row["level"]
    ran_ok = to_bool(row["ran_ok"])
    correct = to_bool(row["correct"])

    key_overall = (condition, model)
    overall[key_overall]["total"] += 1
    overall[key_overall]["ran_ok"] += int(ran_ok)
    overall[key_overall]["correct"] += int(correct)

    key_level = (condition, model, level)
    by_level[key_level]["total"] += 1
    by_level[key_level]["ran_ok"] += int(ran_ok)
    by_level[key_level]["correct"] += int(correct)

with open("extended_conditions/extended_summary.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["condition", "model", "level", "ran_ok", "correct", "total", "accuracy_pct"])

    for (condition, model), stats in sorted(overall.items()):
        acc = round(100 * stats["correct"] / stats["total"], 1) if stats["total"] else 0.0
        writer.writerow([condition, model, "ALL", stats["ran_ok"], stats["correct"], stats["total"], acc])

    for (condition, model, level), stats in sorted(by_level.items()):
        acc = round(100 * stats["correct"] / stats["total"], 1) if stats["total"] else 0.0
        writer.writerow([condition, model, level, stats["ran_ok"], stats["correct"], stats["total"], acc])

print("Done. Summary saved to extended_conditions/extended_summary.csv")

print("\n=== Overall accuracy by condition/model ===")
for (condition, model), stats in sorted(overall.items()):
    acc = round(100 * stats["correct"] / stats["total"], 1) if stats["total"] else 0.0
    print(f"{condition:28s} {model:24s} correct={stats['correct']:3d}/{stats['total']:3d} ({acc}%)  ran_ok={stats['ran_ok']}")

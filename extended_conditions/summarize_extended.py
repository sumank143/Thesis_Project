"""
Aggregation for the extended prompting-condition study (Sections 3.5 / 4.5),
covering all FOUR conditions (C1-C4). Supersedes the old
analyze_extended_results.py / analyze_and_chart.py, which only covered
Conditions 1-3 and were removed once Condition 4 was added.

Writes extended_conditions/extended_summary.csv (overall + by-level
accuracy per condition/model) and extended_conditions/final_summary.csv
(the same overall_summary + by_level sections, plus a
condition3_to_condition4_delta section showing each Condition-3 query's
correctness before/after the Condition-4 rewording, per model).

Run from the thesis-nl2sql/ folder root:
    python extended_conditions/summarize_extended.py
"""
import csv
import os
from collections import defaultdict

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXT = os.path.join(BASE, "extended_conditions")

MODEL_ORDER = ["gpt-4.1-mini", "gemini-3.5-flash-lite"]

CONDITION_ORDER = [
    "condition1_unaware",
    "condition2_aware_no_hints",
    "condition3_fewshot",
    "condition4_precise_wording",
]

RESULT_FILES = {
    ("condition1_unaware", "gpt-4.1-mini"): os.path.join(EXT, "results_condition1_unaware_gpt.csv"),
    ("condition1_unaware", "gemini-3.5-flash-lite"): os.path.join(EXT, "results_condition1_unaware_gemini.csv"),
    ("condition2_aware_no_hints", "gpt-4.1-mini"): os.path.join(EXT, "results_condition2_aware_no_hints_gpt.csv"),
    ("condition2_aware_no_hints", "gemini-3.5-flash-lite"): os.path.join(EXT, "results_condition2_aware_no_hints_gemini.csv"),
    ("condition3_fewshot", "gpt-4.1-mini"): os.path.join(EXT, "results_condition3_fewshot_gpt.csv"),
    ("condition3_fewshot", "gemini-3.5-flash-lite"): os.path.join(EXT, "results_condition3_fewshot_gemini.csv"),
    ("condition4_precise_wording", "gpt-4.1-mini"): os.path.join(EXT, "results_condition4_precise_wording_gpt.csv"),
    ("condition4_precise_wording", "gemini-3.5-flash-lite"): os.path.join(EXT, "results_condition4_precise_wording_gemini.csv"),
}

def to_bool(s):
    return str(s).strip().lower() == "true"

def load_rows(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def main():
    all_data = {key: load_rows(path) for key, path in RESULT_FILES.items()}

    overall = {}
    by_level = defaultdict(lambda: {"ran_ok": 0, "correct": 0, "total": 0})
    for (cond, model), rows in all_data.items():
        total = len(rows)
        correct = sum(1 for r in rows if to_bool(r["correct"]))
        ran_ok = sum(1 for r in rows if to_bool(r["ran_ok"]))
        exec_fail_count = sum(1 for r in rows if not to_bool(r["ran_ok"]))
        ran_but_wrong_count = sum(1 for r in rows if to_bool(r["ran_ok"]) and not to_bool(r["correct"]))
        accuracy_pct = round(100 * correct / total, 1) if total else 0.0
        overall[(cond, model)] = {
            "total": total, "correct": correct, "accuracy_pct": accuracy_pct,
            "ran_ok": ran_ok, "exec_fail_count": exec_fail_count,
            "ran_but_wrong_count": ran_but_wrong_count,
        }
        for r in rows:
            key = (cond, model, r["level"])
            by_level[key]["total"] += 1
            by_level[key]["ran_ok"] += int(to_bool(r["ran_ok"]))
            by_level[key]["correct"] += int(to_bool(r["correct"]))

    # --- extended_summary.csv (flat, single-section) ---
    ext_path = os.path.join(EXT, "extended_summary.csv")
    with open(ext_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["condition", "model", "level", "ran_ok", "correct", "total", "accuracy_pct"])
        for cond in CONDITION_ORDER:
            for model in MODEL_ORDER:
                s = overall[(cond, model)]
                w.writerow([cond, model, "ALL", s["ran_ok"], s["correct"], s["total"], s["accuracy_pct"]])
        for cond in CONDITION_ORDER:
            for model in MODEL_ORDER:
                levels = sorted({lvl for (c, m, lvl) in by_level if c == cond and m == model})
                for lvl in levels:
                    s = by_level[(cond, model, lvl)]
                    acc = round(100 * s["correct"] / s["total"], 1) if s["total"] else 0.0
                    w.writerow([cond, model, lvl, s["ran_ok"], s["correct"], s["total"], acc])
    print("Wrote", ext_path)

    # --- condition3_to_condition4_delta (per-query flip/regress) ---
    delta_rows = []
    for model in MODEL_ORDER:
        c3 = {r["id"]: to_bool(r["correct"]) for r in all_data[("condition3_fewshot", model)]}
        c4 = {r["id"]: to_bool(r["correct"]) for r in all_data[("condition4_precise_wording", model)]}
        for qid in sorted(set(c3) & set(c4)):
            c3_ok, c4_ok = c3[qid], c4[qid]
            delta_rows.append({
                "model": model, "query_id": qid,
                "c3_correct": c3_ok, "c4_correct": c4_ok,
                "flipped_wrong_to_correct": (not c3_ok) and c4_ok,
                "regressed_correct_to_wrong": c3_ok and (not c4_ok),
            })

    # --- final_summary.csv (multi-section, same convention as rq2_failure_summary.csv) ---
    final_path = os.path.join(EXT, "final_summary.csv")
    with open(final_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)

        w.writerow(["# SECTION: overall_summary"])
        w.writerow(["condition", "model", "total", "correct", "accuracy_pct", "ran_ok", "exec_fail_count", "ran_but_wrong_count"])
        for cond in CONDITION_ORDER:
            for model in MODEL_ORDER:
                s = overall[(cond, model)]
                w.writerow([cond, model, s["total"], s["correct"], s["accuracy_pct"],
                            s["ran_ok"], s["exec_fail_count"], s["ran_but_wrong_count"]])
        w.writerow([])

        w.writerow(["# SECTION: by_level"])
        w.writerow(["condition", "model", "level", "correct", "total", "accuracy_pct"])
        for cond in CONDITION_ORDER:
            for model in MODEL_ORDER:
                levels = sorted({lvl for (c, m, lvl) in by_level if c == cond and m == model})
                for lvl in levels:
                    s = by_level[(cond, model, lvl)]
                    acc = round(100 * s["correct"] / s["total"], 1) if s["total"] else 0.0
                    w.writerow([cond, model, lvl, s["correct"], s["total"], acc])
        w.writerow([])

        w.writerow(["# SECTION: condition3_to_condition4_delta"])
        w.writerow(["model", "query_id", "c3_correct", "c4_correct", "flipped_wrong_to_correct", "regressed_correct_to_wrong"])
        for r in delta_rows:
            w.writerow([r["model"], r["query_id"], r["c3_correct"], r["c4_correct"],
                        r["flipped_wrong_to_correct"], r["regressed_correct_to_wrong"]])
    print("Wrote", final_path)

if __name__ == "__main__":
    main()

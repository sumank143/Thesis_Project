"""
Step 2 of failure-pattern classification (thesis section 3.4, dimension 5).
v2 -- adds detection for LEFT JOIN vs INNER JOIN mismatches and LIMIT
mismatches, after spot-checking the v1 "unclear" rows by eye and finding
these were the dominant missed pattern.

Categories (from thesis section 3.4):
  a) hallucinated_schema   - model invented a table/column name that doesn't exist
  b) wrong_join_path       - join structure differs from ground truth
                             (different number of joins, different join TYPE
                             i.e. LEFT vs INNER, or joins the wrong table)
  c) wrong_aggregation     - aggregate/GROUP BY/HAVING logic differs
  d) wrong_filter          - WHERE-clause or LIMIT logic differs
  e) syntax_error          - SQL is malformed (MySQL syntax error)
  f) unclear               - doesn't fit the above cleanly; needs a human look

Usage:
    python classify_failures.py
"""
import csv
import json
import re

RESULT_FILES = [
    "results_gpt.csv", "results_gpt_zeroshot.csv",
    "results_claude.csv", "results_claude_zeroshot.csv",
    "results_gemini.csv", "results_gemini_zeroshot.csv",
]
OUTPUT_FILE = "failures_with_suggestions.csv"

def is_failure(row):
    return row["ran_ok"] != "True" or row["correct"] != "True"

def load_ground_truth():
    with open("queries.json", encoding="utf-8") as f:
        qs = json.load(f)
    return {q["id"]: q for q in qs}

def join_signature(sql):
    """Returns (count of LEFT JOIN, count of INNER/plain JOIN)."""
    left = len(re.findall(r"\bleft\s+join\b", sql))
    total = len(re.findall(r"\bjoin\b", sql))
    inner = total - left
    return left, inner

def suggest_category(row, gt):
    sql = (row.get("model_sql") or "").lower()
    err = (row.get("error") or "").lower()
    ran_ok = row["ran_ok"] == "True"
    truth_sql = (gt.get("ground_truth_sql") or "").lower()

    if not ran_ok:
        if "1146" in err or ("doesn't exist" in err and "table" in err):
            return "hallucinated_schema"
        if "1054" in err or "unknown column" in err:
            return "hallucinated_schema"
        if "1064" in err or "syntax" in err:
            return "syntax_error"
        return "unclear"

    model_left, model_inner = join_signature(sql)
    truth_left, truth_inner = join_signature(truth_sql)

    # different join TYPE mix (e.g. model used LEFT JOIN where truth used INNER JOIN)
    if (model_left, model_inner) != (truth_left, truth_inner):
        return "wrong_join_path"

    model_agg = bool(re.search(r"\b(count|sum|avg|min|max)\s*\(", sql))
    truth_agg = bool(re.search(r"\b(count|sum|avg|min|max)\s*\(", truth_sql))
    model_group = "group by" in sql
    truth_group = "group by" in truth_sql
    if model_agg != truth_agg or model_group != truth_group:
        return "wrong_aggregation"

    model_where = "where" in sql
    truth_where = "where" in truth_sql
    model_limit = "limit" in sql
    truth_limit = "limit" in truth_sql
    if model_where != truth_where or model_limit != truth_limit:
        return "wrong_filter"

    return "unclear"

def main():
    gt_map = load_ground_truth()
    all_failures = []
    for filename in RESULT_FILES:
        with open(filename, newline="", encoding="utf-8") as f:
            rows = [r for r in csv.DictReader(f) if is_failure(r)]
            all_failures.extend(rows)

    fieldnames = [
        "id", "level", "model", "ran_ok", "correct",
        "model_rows", "truth_rows", "question", "ground_truth_sql",
        "model_sql", "error", "suggested_category", "category",
    ]
    counts = {}
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in all_failures:
            gt = gt_map.get(row["id"], {})
            suggestion = suggest_category(row, gt)
            counts[suggestion] = counts.get(suggestion, 0) + 1
            writer.writerow({
                "id": row["id"], "level": row["level"], "model": row["model"],
                "ran_ok": row["ran_ok"], "correct": row["correct"],
                "model_rows": row.get("model_rows", ""), "truth_rows": row.get("truth_rows", ""),
                "question": gt.get("question", ""), "ground_truth_sql": gt.get("ground_truth_sql", ""),
                "model_sql": row["model_sql"], "error": row["error"],
                "suggested_category": suggestion, "category": "",
            })

    print(f"Total failing rows: {len(all_failures)}")
    print(f"Written to {OUTPUT_FILE}\n")
    print("Suggested category breakdown (still needs your review):")
    for cat, n in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {n}")

if __name__ == "__main__":
    main()

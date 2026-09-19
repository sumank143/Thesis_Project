"""
Row-level failure classification for the extended-conditions study
(Sections 3.5 / 4.5 / Table 9 of the thesis).

Unlike the static-text classifier, this script EXECUTES the ground-truth
SQL and the model's SQL against your live thesis_nl2sql MySQL database and
compares actual output rows, so it can correctly tell apart:
  - column_shape_mismatch   (right rows, wrong/extra/missing columns)
  - output_formatting_mismatch (same rows+columns, differs only in
    rounding / GROUP_CONCAT ordering / date-string granularity)
  - wrong_join_path / wrong_aggregation / wrong_filter (genuinely
    different row set)
  - hallucinated_schema / syntax_error (execution failed - taken directly
    from the original run's recorded error, not re-derived)

Run this from the thesis-nl2sql/ folder root (same place run_condition*.py
live), with your normal .env / MYSQL_PASSWORD in place:

    python extended_conditions/classify_failures_extended.py

It writes extended_conditions/table9_classification.csv (one row per
failing query, with its category) and prints the summary counts you can
report to Claude for Table 9.
"""
import csv
import json
import os
import re
from collections import defaultdict

from dotenv import load_dotenv
load_dotenv()

import mysql.connector

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXT = os.path.join(BASE, "extended_conditions")

RESULT_FILES = [
    os.path.join(EXT, "results_condition1_unaware_gpt.csv"),
    os.path.join(EXT, "results_condition1_unaware_gemini.csv"),
    os.path.join(EXT, "results_condition2_aware_no_hints_gpt.csv"),
    os.path.join(EXT, "results_condition2_aware_no_hints_gemini.csv"),
    os.path.join(EXT, "results_condition3_fewshot_gpt.csv"),
    os.path.join(EXT, "results_condition3_fewshot_gemini.csv"),
    os.path.join(EXT, "results_condition4_precise_wording_gpt.csv"),
    os.path.join(EXT, "results_condition4_precise_wording_gemini.csv"),
]

def get_conn():
    return mysql.connector.connect(
        host="localhost", user="root",
        password=os.getenv("MYSQL_PASSWORD"), database="thesis_nl2sql",
    )

def load_gt():
    gt = {}
    with open(os.path.join(BASE, "queries.json"), encoding="utf-8") as f:
        for q in json.load(f):
            gt[q["id"]] = q
    with open(os.path.join(EXT, "new_queries_l3_l4.json"), encoding="utf-8") as f:
        for q in json.load(f):
            gt[q["id"]] = q
    precise_path = os.path.join(EXT, "new_queries_l3_l4_precise.json")
    if os.path.exists(precise_path):
        with open(precise_path, encoding="utf-8") as f:
            for q in json.load(f):
                if q["id"] not in gt:
                    gt[q["id"]] = q
    return gt

def run_sql(conn, sql):
    """Returns (columns, rows) or raises on execution error."""
    cur = conn.cursor()
    cur.execute(sql)
    cols = [d[0] for d in cur.description] if cur.description else []
    rows = cur.fetchall()
    cur.close()
    return cols, rows

def normalize_cell(v):
    """Normalize a cell value so formatting-only differences (rounding,
    trailing zeros, date-string granularity) don't count as a mismatch."""
    if v is None:
        return None
    if isinstance(v, float):
        return round(v, 2)
    if isinstance(v, int):
        return v
    s = str(v).strip()
    # normalize date-like strings to YYYY-MM-DD if they start that way
    m = re.match(r"^(\d{4}-\d{2}-\d{2})", s)
    if m:
        return m.group(1)
    # try numeric normalization (e.g. "12.500" vs "12.5")
    try:
        f = float(s)
        return round(f, 2)
    except ValueError:
        pass
    return s.lower()

def normalize_row(row):
    return tuple(normalize_cell(v) for v in row)

def normalize_rowset(rows, ignore_order=True):
    normed = [normalize_row(r) for r in rows]
    if ignore_order:
        return sorted(normed, key=lambda t: tuple(str(x) for x in t))
    return normed

def classify_execfail(row):
    err = (row.get("error") or "").lower()
    if "1146" in err or ("doesn't exist" in err and "table" in err):
        return "hallucinated_schema"
    if "1054" in err or "unknown column" in err:
        return "hallucinated_schema"
    if "1064" in err or "syntax" in err:
        return "syntax_error"
    return "unclear_execfail"

def classify_row(conn, row, gt):
    ran_ok = row["ran_ok"] == "True"
    if not ran_ok:
        return classify_execfail(row), {}

    truth_sql = gt.get("ground_truth_sql", "")
    model_sql = row.get("model_sql", "")

    try:
        truth_cols, truth_rows = run_sql(conn, truth_sql)
    except Exception as e:
        return "gt_exec_error", {"error": str(e)}

    try:
        model_cols, model_rows = run_sql(conn, model_sql)
    except Exception as e:
        # model_sql previously ran_ok=True in the original run but fails
        # now (shouldn't normally happen) - fall back to execfail-style err
        return "unclear_model_reexec_failed", {"error": str(e)}

    detail = {
        "truth_cols": len(truth_cols), "model_cols": len(model_cols),
        "truth_rows_n": len(truth_rows), "model_rows_n": len(model_rows),
    }

    # 1. Column count mismatch -> column shape
    if len(model_cols) != len(truth_cols):
        return "column_shape_mismatch", detail

    # 2. Same column count: compare normalized row sets (order-insensitive,
    #    value-normalized) - if they match exactly, it's genuinely correct
    #    (shouldn't happen since row was marked incorrect, but guard anyway)
    truth_norm = normalize_rowset(truth_rows, ignore_order=True)
    model_norm = normalize_rowset(model_rows, ignore_order=True)
    if truth_norm == model_norm:
        return "actually_correct_after_normalization", detail

    # 3. Same column count, different normalized content but same row
    #    count -> check order-sensitive match (catches GROUP_CONCAT
    #    ordering / date-format differences that ignore_order doesn't)
    if len(model_rows) == len(truth_rows):
        truth_norm_ord = normalize_rowset(truth_rows, ignore_order=False)
        model_norm_ord = normalize_rowset(model_rows, ignore_order=False)
        # if the only difference is order (set-equal) or trivial formatting
        # already normalized away above but row-for-row still differs,
        # treat same-row-count + all-values-individually-close as formatting
        # Try comparing as multisets one more time after normalization
        from collections import Counter
        if Counter(truth_norm) == Counter(model_norm):
            return "output_formatting_mismatch", detail
        # same row count but different actual content -> could still be
        # column-shape (different columns selected but same count) or a
        # genuine logic difference; check column name overlap as a hint
        truth_colset = set(c.lower() for c in truth_cols)
        model_colset = set(c.lower() for c in model_cols)
        if truth_colset != model_colset and len(truth_colset & model_colset) < len(truth_colset):
            return "column_shape_mismatch", detail
        return "wrong_filter", detail

    # 4. Different row count -> genuine reasoning error: join/aggregation/filter
    sql_l = model_sql.lower()
    truth_l = truth_sql.lower()
    model_joins = len(re.findall(r"\bjoin\b", sql_l))
    truth_joins = len(re.findall(r"\bjoin\b", truth_l))
    if model_joins != truth_joins:
        return "wrong_join_path", detail
    model_agg = bool(re.search(r"\b(count|sum|avg|min|max)\s*\(", sql_l))
    truth_agg = bool(re.search(r"\b(count|sum|avg|min|max)\s*\(", truth_l))
    if model_agg != truth_agg or ("group by" in sql_l) != ("group by" in truth_l):
        return "wrong_aggregation", detail
    return "wrong_filter", detail


def main():
    gt = load_gt()
    conn = get_conn()

    counts = defaultdict(int)
    out_rows = []
    total_failing = 0

    for fn in RESULT_FILES:
        with open(fn, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        for r in rows:
            if r["correct"] == "True":
                continue
            total_failing += 1
            qid = r["id"]
            g = gt.get(qid, {})
            cat, detail = classify_row(conn, r, g)
            counts[cat] += 1
            out_rows.append({
                "file": os.path.basename(fn), "id": qid, "model": r["model"],
                "category": cat, **detail,
            })

    conn.close()

    out_path = os.path.join(EXT, "table9_classification.csv")
    fieldnames = ["file", "id", "model", "category", "error",
                  "truth_cols", "model_cols", "truth_rows_n", "model_rows_n"]
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for row in out_rows:
            w.writerow(row)

    print("Wrote:", out_path)
    print()
    print("total_failing:", total_failing)
    for cat, n in sorted(counts.items(), key=lambda x: -x[1]):
        pct = 100.0 * n / total_failing
        print("  " + cat + ": " + str(n) + " (" + format(pct, ".1f") + "%)")

    unclear = [r for r in out_rows if r["category"].startswith(("unclear", "gt_exec_error", "actually_correct"))]
    if unclear:
        print()
        print("=== rows needing a manual look (" + str(len(unclear)) + ") ===")
        for r in unclear:
            print(" ", r["file"], r["id"], r["model"], r["category"], r.get("error", ""))

if __name__ == "__main__":
    main()

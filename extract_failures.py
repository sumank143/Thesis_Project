"""
Step 1 of failure-pattern classification (thesis section 3.4, dimension 5).

Reads all 6 results CSVs (3 models x 2 prompting conditions), pulls out every
row that either failed to execute (ran_ok = False) or executed but returned
the wrong answer (correct = False), and writes them to one combined CSV with
an empty 'category' column ready for hand-tagging.

Usage:
    python extract_failures.py
"""
import csv

RESULT_FILES = [
    "results_gpt.csv",
    "results_gpt_zeroshot.csv",
    "results_claude.csv",
    "results_claude_zeroshot.csv",
    "results_gemini.csv",
    "results_gemini_zeroshot.csv",
]

OUTPUT_FILE = "failures_to_classify.csv"

def is_failure(row):
    return row["ran_ok"] != "True" or row["correct"] != "True"

def main():
    all_failures = []
    for filename in RESULT_FILES:
        with open(filename, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            failures = [r for r in rows if is_failure(r)]
            print(f"{filename}: {len(failures)} failing rows out of {len(rows)}")
            all_failures.extend(failures)

    fieldnames = ["id", "level", "model", "ran_ok", "correct", "model_sql", "error", "category"]
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in all_failures:
            writer.writerow({
                "id": row["id"],
                "level": row["level"],
                "model": row["model"],
                "ran_ok": row["ran_ok"],
                "correct": row["correct"],
                "model_sql": row["model_sql"],
                "error": row["error"],
                "category": "",  # you fill this in by hand
            })

    print(f"\nTotal failing rows written to {OUTPUT_FILE}: {len(all_failures)}")

if __name__ == "__main__":
    main()

import os, csv, json
from dotenv import load_dotenv
import mysql.connector

load_dotenv()

def get_conn():
    return mysql.connector.connect(host="localhost", user="root",
        password=os.getenv("MYSQL_PASSWORD"), database="thesis_nl2sql")

# --- run EXPLAIN and pull two simple efficiency numbers ---
def explain_stats(sql):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("EXPLAIN " + sql.rstrip(";"))
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]
    cur.close(); conn.close()

    type_idx = cols.index("type")
    rows_idx = cols.index("rows")

    full_scans = 0
    total_rows = 0
    for r in rows:
        if r[type_idx] == "ALL":       # full table scan
            full_scans += 1
        if r[rows_idx] is not None:
            total_rows += int(r[rows_idx])
    return full_scans, total_rows

# --- load ground-truth SQL keyed by id ---
with open("queries.json", encoding="utf-8") as f:
    truth = {q["id"]: q["ground_truth_sql"] for q in json.load(f)}

# --- read the model results, keep only CORRECT ones ---
correct_rows = []
with open("results_claude.csv", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row["correct"] == "True":
            correct_rows.append(row)

print(f"Measuring efficiency on {len(correct_rows)} correct queries\n")

out = []
same = less = more = 0
for row in correct_rows:
    qid = row["id"]
    model_sql = row["model_sql"]
    truth_sql = truth[qid]
    try:
        m_scans, m_rows = explain_stats(model_sql)
        t_scans, t_rows = explain_stats(truth_sql)
    except Exception as e:
        print(f"{qid}: EXPLAIN failed - {str(e)[:60]}")
        continue

    # simple verdict: compare (scans, rows examined)
    if (m_scans, m_rows) == (t_scans, t_rows):
        verdict = "same"; same += 1
    elif (m_scans, m_rows) > (t_scans, t_rows):
        verdict = "model_less_efficient"; less += 1
    else:
        verdict = "model_more_efficient"; more += 1

    out.append([qid, row["level"], m_scans, m_rows, t_scans, t_rows, verdict])
    print(f"{qid}: model({m_scans} scans, {m_rows} rows) vs truth({t_scans} scans, {t_rows} rows) -> {verdict}")

# --- save comparison ---
with open("efficiency_claude.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["id","level","model_scans","model_rows","truth_scans","truth_rows","verdict"])
    w.writerows(out)

print(f"\n=== SUMMARY (of {len(out)} correct queries) ===")
print(f"Same efficiency:        {same}")
print(f"Model LESS efficient:   {less}")
print(f"Model MORE efficient:   {more}")
print("Saved to efficiency.csv")
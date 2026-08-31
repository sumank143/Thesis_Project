import os, csv, time, json
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
import mysql.connector

load_dotenv()

# --- pick which model to test (swap these 4 lines per model) ---
from langchain_google_genai import ChatGoogleGenerativeAI
MODEL_NAME = "gemini-3.5-flash-lite"
llm = ChatGoogleGenerativeAI(model="gemini-3.5-flash-lite", api_key=os.getenv("GOOGLE_API_KEY"))
DELAY_SECONDS = 8
DELAY_SECONDS = 3
REPEATS = 5

# representative subset: mix of levels, weighted to complex
SUBSET_IDS = ["L1-01", "L2-04", "L2-08", "L3-05", "L3-06", "L3-11", "L4-02", "L4-06", "L4-08", "L4-10"]

schema = """
Database schema (MySQL):
customers(customer_id PK, first_name, last_name, email, city, country, created_at)
products(product_id PK, product_name, category_id FK, price, stock_qty)
categories(category_id PK, category_name, parent_category_id FK, description, is_active, created_at)
orders(order_id PK, customer_id FK, handled_by FK->employees, order_date, status)
order_items(order_item_id PK, order_id FK, product_id FK, quantity, unit_price)
warehouses(warehouse_id PK, warehouse_name, city, country, is_active, created_at)
inventory(inventory_id PK, product_id FK, warehouse_id FK, quantity, last_restocked, created_at)
employees(employee_id PK, first_name, last_name, email, department_id FK, manager_id FK->employees, hire_date, created_at)
departments(department_id PK, department_name, location, created_at)
"""

with open("queries.json", "r", encoding="utf-8") as f:
    all_queries = json.load(f)
queries = [q for q in all_queries if q["id"] in SUBSET_IDS]
print(f"Testing {len(queries)} queries x {REPEATS} repeats for {MODEL_NAME}")

def run_sql(sql):
    conn = mysql.connector.connect(host="localhost", user="root",
        password=os.getenv("MYSQL_PASSWORD"), database="thesis_nl2sql")
    cur = conn.cursor(); cur.execute(sql); rows = cur.fetchall()
    cur.close(); conn.close()
    return rows

def extract_text(response):
    raw = response.content
    if isinstance(raw, list):
        parts = [i["text"] for i in raw if isinstance(i, dict) and "text" in i]
        return "".join(parts).strip()
    return str(raw).strip()

def clean_sql(text):
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1] if "```" in text else text
        if text.lower().startswith("sql"):
            text = text[3:]
    return text.strip().rstrip("`").strip()

def get_model_sql(question, expected_columns):
    prompt = f"""{schema}

Given the schema above, write a single MySQL query to answer this question:
"{question}"

Return exactly these columns in the SELECT: {expected_columns}
Return ONLY the SQL query, no explanation, no markdown, no code fences."""
    response = llm.invoke(prompt)
    return clean_sql(extract_text(response))

outfile = f"consistency_{MODEL_NAME}.csv"
with open(outfile, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["id","level","model","run_num","result_signature","sql"])

    summary = []
    for q in queries:
        signatures = []
        for r in range(1, REPEATS + 1):
            try:
                sql = get_model_sql(q["question"], q["expected_columns"])
                rows = run_sql(sql)
                # signature = sorted set of rows as a string (order-independent)
                sig = str(sorted([tuple(str(x) for x in row) for row in rows]))
            except Exception as e:
                sql = ""; sig = "ERROR:" + str(e)[:40]
            signatures.append(sig)
            writer.writerow([q["id"], q["level"], MODEL_NAME, r, hash(sig), sql])
            f.flush()
            time.sleep(DELAY_SECONDS)

        # consistency = how many distinct result-signatures across the repeats
        distinct = len(set(signatures))
        consistent = (distinct == 1)
        summary.append((q["id"], q["level"], distinct, consistent))
        print(f"{q['id']} (L{q['level']}): {distinct} distinct result(s) across {REPEATS} runs -> {'CONSISTENT' if consistent else 'VARIES'}")

    print(f"\n=== SUMMARY ({MODEL_NAME}) ===")
    fully = sum(1 for _,_,_,c in summary if c)
    print(f"Fully consistent: {fully}/{len(summary)} queries")
    print(f"Saved to {outfile}")
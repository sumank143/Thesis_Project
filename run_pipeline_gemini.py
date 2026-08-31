import os, csv, time, json
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
import mysql.connector

load_dotenv()
MODEL_NAME = "gemini-3.5-flash-lite"
DELAY_SECONDS = 8         # <-- bigger delay

llm = ChatGoogleGenerativeAI(model=MODEL_NAME, api_key=os.getenv("GOOGLE_API_KEY"))

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
    queries = json.load(f)
print(f"Loaded {len(queries)} queries")

def run_sql(sql):
    conn = mysql.connector.connect(host="localhost", user="root",
        password=os.getenv("MYSQL_PASSWORD"), database="thesis_nl2sql")
    cur = conn.cursor(); cur.execute(sql); rows = cur.fetchall()
    cur.close(); conn.close()
    return rows

def get_model_sql(question, expected_columns, max_retries=4):
    prompt = f"""{schema}

Given the schema above, write a single MySQL query to answer this question:
"{question}"

Return exactly these columns in the SELECT: {expected_columns}
Return ONLY the SQL query, no explanation, no markdown, no code fences."""
    for attempt in range(max_retries):
        try:
            response = llm.invoke(prompt)
            raw = response.content
            return (raw[0]["text"] if isinstance(raw, list) else raw).strip()
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                wait = 30 * (attempt + 1)
                print(f"   rate limit hit, waiting {wait}s...")
                time.sleep(wait)
            else:
                raise
    raise Exception("Max retries exceeded")

outfile = "results_gemini.csv"
with open(outfile, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["id","level","model","ran_ok","correct","model_rows","truth_rows","model_sql","error"])

    for i, q in enumerate(queries, 1):
        error = ""
        try:
            model_sql = get_model_sql(q["question"], q["expected_columns"])
        except Exception as e:
            model_sql = ""; error = "GEN_FAIL: " + str(e)[:80]

        try:
            truth_rows = run_sql(q["ground_truth_sql"])
        except Exception as e:
            truth_rows = []; error += " TRUTH_FAIL: " + str(e)[:80]

        if model_sql:
            try:
                model_rows = run_sql(model_sql)
                ran_ok = True
                correct = (set(model_rows) == set(truth_rows))
            except Exception as e:
                model_rows = []; ran_ok = False; correct = False
                error = "EXEC_FAIL: " + str(e)[:80]
        else:
            model_rows = []; ran_ok = False; correct = False

        writer.writerow([q["id"], q["level"], MODEL_NAME, ran_ok, correct,
                         len(model_rows), len(truth_rows), model_sql, error])
        f.flush()
        print(f"[{i}/{len(queries)}] {q['id']} (L{q['level']}): ran={ran_ok} correct={correct}")

        if i < len(queries):
            time.sleep(DELAY_SECONDS)

print(f"\nDone. Results saved to {outfile}")
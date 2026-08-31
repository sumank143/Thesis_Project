import os, csv, time, json
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
import mysql.connector

load_dotenv()
MODEL_NAME = "gpt-4.1-mini"
DELAY_SECONDS = 3          # Azure limits are generous; small delay is fine

llm = ChatOpenAI(
    model="gpt-4.1-mini",
    api_key=os.getenv("AZURE_OPENAI_KEY"),
    base_url=os.getenv("AZURE_OPENAI_ENDPOINT"),
)

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
print(f"Loaded {len(queries)} queries for model {MODEL_NAME}")

def run_sql(sql):
    conn = mysql.connector.connect(host="localhost", user="root",
        password=os.getenv("MYSQL_PASSWORD"), database="thesis_nl2sql")
    cur = conn.cursor(); cur.execute(sql); rows = cur.fetchall()
    cur.close(); conn.close()
    return rows

def extract_text(response):
    raw = response.content
    if isinstance(raw, list):
        parts = []
        for item in raw:
            if isinstance(item, dict) and "text" in item:
                parts.append(item["text"])
            elif isinstance(item, str):
                parts.append(item)
        return "".join(parts).strip()
    return str(raw).strip()

def clean_sql(text):
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1] if "```" in text else text
        if text.lower().startswith("sql"):
            text = text[3:]
    return text.strip().rstrip("`").strip()

def get_model_sql(question, expected_columns, max_retries=4):
    prompt = f"""{schema}

Given the schema above, write a single MySQL query to answer this question:
"{question}"

Return exactly these columns in the SELECT: {expected_columns}
Return ONLY the SQL query, no explanation, no markdown, no code fences."""
    for attempt in range(max_retries):
        try:
            response = llm.invoke(prompt)
            return clean_sql(extract_text(response))
        except Exception as e:
            if "429" in str(e) or "rate" in str(e).lower():
                wait = 20 * (attempt + 1)
                print(f"   rate limit, waiting {wait}s...")
                time.sleep(wait)
            else:
                raise
    raise Exception("Max retries exceeded")

outfile = "results_gpt.csv"
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
            truth_rows = []; error += " TRUTH_FAIL: " + str(e)[:60]

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
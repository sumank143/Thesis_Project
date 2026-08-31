import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
import mysql.connector

load_dotenv()
llm = ChatGoogleGenerativeAI(model="gemini-3.6-flash", api_key=os.getenv("GOOGLE_API_KEY"))

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

# 4 test queries — one per level. Each: id, question, expected_columns, ground_truth_sql
test_queries = [
    {
        "id": "L1-09",
        "question": "Which customers are from Hamburg?",
        "expected_columns": "first_name, last_name, city",
        "ground_truth_sql": "SELECT first_name, last_name, city FROM customers WHERE city = 'Hamburg';"
    },
    {
        "id": "L2-01",
        "question": "Which products are in the Laptops category?",
        "expected_columns": "product_name, category_name",
        "ground_truth_sql": "SELECT p.product_name, c.category_name FROM products p JOIN categories c ON p.category_id = c.category_id WHERE c.category_name = 'Laptops';"
    },
    {
        "id": "L3-05",
        "question": "What is the total revenue per product category?",
        "expected_columns": "category_name, revenue",
        "ground_truth_sql": "SELECT c.category_name, SUM(oi.quantity * oi.unit_price) AS revenue FROM order_items oi JOIN products p ON oi.product_id = p.product_id JOIN categories c ON p.category_id = c.category_id GROUP BY c.category_name ORDER BY revenue DESC;"
    },
    {
        "id": "L4-05",
        "question": "Which products have never been ordered?",
        "expected_columns": "product_name",
        "ground_truth_sql": "SELECT product_name FROM products WHERE product_id NOT IN (SELECT DISTINCT product_id FROM order_items);"
    },
]

def run_sql(sql):
    conn = mysql.connector.connect(host="localhost", user="root",
        password=os.getenv("MYSQL_PASSWORD"), database="thesis_nl2sql")
    cur = conn.cursor(); cur.execute(sql); rows = cur.fetchall()
    cur.close(); conn.close()
    return rows

def get_model_sql(question, expected_columns):
    prompt = f"""{schema}

Given the schema above, write a single MySQL query to answer this question:
"{question}"

Return exactly these columns in the SELECT: {expected_columns}
Return ONLY the SQL query, no explanation, no markdown, no code fences."""
    response = llm.invoke(prompt)
    raw = response.content
    return (raw[0]["text"] if isinstance(raw, list) else raw).strip()

# --- THE LOOP ---
print(f"{'ID':<7} {'RAN':<5} {'CORRECT':<8} {'ROWS(m/t)':<10}")
print("-" * 40)

results = []
for q in test_queries:
    model_sql = get_model_sql(q["question"], q["expected_columns"])
    truth_rows = run_sql(q["ground_truth_sql"])
    try:
        model_rows = run_sql(model_sql)
        ran = True
        correct = (set(model_rows) == set(truth_rows))
    except Exception as e:
        model_rows = []; ran = False; correct = False
        err = str(e)[:50]

    results.append({"id": q["id"], "ran": ran, "correct": correct, "sql": model_sql})
    print(f"{q['id']:<7} {str(ran):<5} {str(correct):<8} {len(model_rows)}/{len(truth_rows)}")

# --- SUMMARY ---
total = len(results)
ran_ok = sum(1 for r in results if r["ran"])
correct_ok = sum(1 for r in results if r["correct"])
print("-" * 40)
print(f"Ran without error: {ran_ok}/{total}")
print(f"Correct (execution accuracy): {correct_ok}/{total}")

# Show any that failed, for inspection
for r in results:
    if not r["correct"]:
        print(f"\n[{r['id']}] not correct. Model SQL was:\n{r['sql']}")
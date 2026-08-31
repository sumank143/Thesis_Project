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

question = "Which customers are from Hamburg?"
expected_columns = "first_name, last_name, city"   # NEW: tells model what to return
ground_truth_sql = "SELECT first_name, last_name, city FROM customers WHERE city = 'Hamburg';"

def run_sql(sql):
    conn = mysql.connector.connect(host="localhost", user="root",
        password=os.getenv("MYSQL_PASSWORD"), database="thesis_nl2sql")
    cur = conn.cursor(); cur.execute(sql); rows = cur.fetchall()
    cur.close(); conn.close()
    return rows

prompt = f"""{schema}

Given the schema above, write a single MySQL query to answer this question:
"{question}"

Return exactly these columns in the SELECT: {expected_columns}
Return ONLY the SQL query, no explanation, no markdown, no code fences."""

response = llm.invoke(prompt)
raw = response.content
model_sql = (raw[0]["text"] if isinstance(raw, list) else raw).strip()
print("=== MODEL SQL ===\n", model_sql)

try:
    model_rows = run_sql(model_sql); model_ran = True
except Exception as e:
    model_rows = []; model_ran = False; print("MODEL SQL FAILED:", e)

truth_rows = run_sql(ground_truth_sql)
exact_match = (set(model_rows) == set(truth_rows))

print("\n=== RESULTS ===")
print(f"Model ran OK: {model_ran}")
print(f"Model rows: {len(model_rows)}, truth rows: {len(truth_rows)}")
print(f"CORRECT (exact result match): {exact_match}")
import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
import mysql.connector

load_dotenv()

# --- 1. Set up the model ---
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

prompt = f"""{schema}

Given the schema above, write a single MySQL query to answer this question:
"{question}"

Return ONLY the SQL query, with no explanation, no markdown formatting, and no code fences.
"""

# --- 2. Get SQL from the model ---
response = llm.invoke(prompt)
raw = response.content
sql = raw[0]["text"] if isinstance(raw, list) else raw
sql = sql.strip()
print("=== GENERATED SQL ===")
print(sql)

# --- 3. Run it against the database ---
print("\n=== RUNNING AGAINST DATABASE ===")
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password=os.getenv("MYSQL_PASSWORD"),
    database="thesis_nl2sql"
)
cursor = conn.cursor()
cursor.execute(sql)
rows = cursor.fetchall()

print(f"Returned {len(rows)} rows:")
for row in rows:
    print(row)

cursor.close()
conn.close()
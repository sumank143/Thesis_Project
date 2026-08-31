import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

llm = ChatGoogleGenerativeAI(model="gemini-3.6-flash", api_key=os.getenv("GOOGLE_API_KEY"))

# Your schema, described for the model
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

# One question from your benchmark (L1-09)
question = "Which customers are from Hamburg?"

# Build the prompt: schema + question + clear instruction
prompt = f"""{schema}

Given the schema above, write a single MySQL query to answer this question:
"{question}"

Return ONLY the SQL query, with no explanation, no markdown formatting, and no code fences.
"""

# Call the model
response = llm.invoke(prompt)

# Extract the text (this newer Gemini returns a list, so reach into it)
raw = response.content
if isinstance(raw, list):
    sql = raw[0]["text"]
else:
    sql = raw

print("=== GENERATED SQL ===")
print(sql)
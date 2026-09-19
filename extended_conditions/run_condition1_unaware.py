import os, csv, time, json
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
import mysql.connector

load_dotenv()
CONDITION = "condition1_unaware"

MODELS = {
    "gpt-4.1-mini": {
        "llm": ChatOpenAI(
            model="gpt-4.1-mini",
            api_key=os.getenv("AZURE_OPENAI_KEY"),
            base_url=os.getenv("AZURE_OPENAI_ENDPOINT"),
        ),
        "delay": 3,
        "outfile": "extended_conditions/results_condition1_unaware_gpt.csv",
        "rate_markers": ["429", "rate"],
        "rate_base_wait": 20,
    },
    "gemini-3.5-flash-lite": {
        "llm": ChatGoogleGenerativeAI(model="gemini-3.5-flash-lite", api_key=os.getenv("GOOGLE_API_KEY")),
        "delay": 8,
        "outfile": "extended_conditions/results_condition1_unaware_gemini.csv",
        "rate_markers": ["429", "resource_exhausted", "rate"],
        "rate_base_wait": 30,
    },
}

with open("queries.json", "r", encoding="utf-8") as f:
    queries = json.load(f)
print(f"Loaded {len(queries)} queries")

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

def get_model_sql(llm, question, rate_markers, rate_base_wait, max_retries=4):
    prompt = f"""Write a single MySQL query to answer this question:
"{question}"

Return ONLY the SQL query, no explanation, no markdown, no code fences."""
    for attempt in range(max_retries):
        try:
            response = llm.invoke(prompt)
            return clean_sql(extract_text(response))
        except Exception as e:
            msg = str(e).lower()
            if any(marker.lower() in msg for marker in rate_markers):
                wait = rate_base_wait * (attempt + 1)
                print(f"   rate limit, waiting {wait}s...")
                time.sleep(wait)
            else:
                raise
    raise Exception("Max retries exceeded")

for model_name, cfg in MODELS.items():
    print(f"\n=== Running {CONDITION} for {model_name} ===")
    outfile = cfg["outfile"]
    with open(outfile, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["id","level","model","ran_ok","correct","model_rows","truth_rows","model_sql","error","condition"])
        for i, q in enumerate(queries, 1):
            error = ""
            try:
                model_sql = get_model_sql(cfg["llm"], q["question"], cfg["rate_markers"], cfg["rate_base_wait"])
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
            writer.writerow([q["id"], q["level"], model_name, ran_ok, correct,
                             len(model_rows), len(truth_rows), model_sql, error, CONDITION])
            f.flush()
            print(f"[{i}/{len(queries)}] {q['id']} ({q['level']}): ran={ran_ok} correct={correct}")
            if i < len(queries):
                time.sleep(cfg["delay"])
    print(f"Done. Results saved to {outfile}")

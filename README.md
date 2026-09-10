# Thesis: Natural Language to SQL — Benchmarking LLMs

Empirical evaluation of three LLMs (GPT-4.1-mini, Claude Haiku 4.5, Gemini
3.5 Flash-Lite) translating natural-language questions into MySQL queries
against a synthetic enterprise database. Measures semantic accuracy,
prompting-condition sensitivity (schema-aware vs. zero-shot), failure
patterns, output consistency, and query efficiency relative to hand-written
ground truth.

## Research questions

- **RQ1 — Accuracy**: How accurate is each model at each query complexity
  level, and how much does providing the schema in the prompt matter?
- **RQ2 — Failure modes**: When a model gets it wrong, why — hallucinated
  schema, wrong join path, wrong aggregation, wrong filter, or a syntax
  error?
- **RQ3 — Consistency & efficiency**: How repeatable are a model's answers
  across repeated runs of the same question, and how do its query plans
  compare to the ground-truth query (full scans, rows examined)?

## Database

A 9-table MySQL schema (`thesis_nl2sql`) modeling a small e-commerce/
warehouse business: `customers`, `products`, `categories`, `orders`,
`order_items`, `warehouses`, `inventory`, `employees`, `departments`. See
[ER-Diagram.svg](ER-Diagram.svg) / [erd.png](erd.png) for the full entity
relationship diagram, and [seed_data.sql](seed_data.sql) for a
deterministic, re-runnable seed of the transactional tables.

## Benchmark

[queries.json](queries.json) holds 50 hand-written natural-language
questions, each with the expected result columns and a ground-truth SQL
query, split across four complexity levels:

| Level | Description | Count |
|-------|--------------------------------------------|-------|
| L1    | Single-table filters/sorts/aggregates       | 10    |
| L2    | Simple joins                                | 15    |
| L3    | Multi-table joins, grouping                 | 15    |
| L4    | Nested queries, complex aggregation/logic   | 10    |

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

Create a `.env` file (not committed) with:

```
GOOGLE_API_KEY=...          # Gemini
OPENROUTER_API_KEY=...      # Claude, via OpenRouter
AZURE_OPENAI_KEY=...        # GPT, via Azure OpenAI
AZURE_OPENAI_ENDPOINT=...
AZURE_DEPLOYMENT=...
MYSQL_PASSWORD=...          # local MySQL root password
```

A local MySQL server with the `thesis_nl2sql` database (schema + seed data
loaded) must be running on `localhost`.

## Pipeline

1. **Generate SQL and score accuracy** — one script per model, per
   prompting condition. Each sends every question to the model, runs both
   the model's SQL and the ground-truth SQL, and compares result sets:
   - `run_pipeline_gpt.py`, `run_pipeline_gpt_zeroshot.py`
   - `run_pipeline_claude.py`, `run_pipeline_claude_zeroshot.py`
   - `run_pipeline_gemini.py`, `run_pipeline_gemini_zeroshot.py`

   Each writes a `results_<model>[_zeroshot].csv` with per-query
   `ran_ok`/`correct` outcomes.

2. **Aggregate accuracy** — `aggregate_accuracy.py` rolls the six results
   CSVs into `accuracy_summary.csv` (overall) and `accuracy_by_level.csv`
   (by complexity level).

3. **Classify failures (RQ2)** — three-step pipeline over the results CSVs:
   - `extract_failures.py` → pulls every failing row into
     `failures_to_classify.csv`
   - `classify_failures.py` → auto-suggests a failure category
     (hallucinated schema, wrong join path, wrong aggregation, wrong
     filter, syntax error, unclear) into `failures_with_suggestions.csv`
   - `tally_failures.py` → tallies corrected/suggested categories by
     model, condition, and level into `rq2_failure_summary.csv`

4. **Measure consistency (RQ3)** — `measure_consistency.py` re-runs a
   representative subset of questions 5x per model and records whether the
   result set is identical across repeats (`consistency_<model>.csv`).

5. **Measure efficiency (RQ3)** — `measure_efficiency.py` runs `EXPLAIN` on
   each correct model query and its ground-truth counterpart, comparing
   full table scans and rows examined (`efficiency_<model>.csv`).

6. **Generate charts** — `generate_charts.py` builds the five Results
   charts into [charts/](charts/) from the aggregated CSVs above.

Run the full pipeline for one model with, e.g.:

```bash
python run_pipeline_claude.py
python run_pipeline_claude_zeroshot.py
python aggregate_accuracy.py
python extract_failures.py && python classify_failures.py && python tally_failures.py
python measure_consistency.py
python measure_efficiency.py
python generate_charts.py
```

`list_models.py` is a small utility to list available Gemini models.
`test_*.py` are exploratory scripts used during development to sanity-check
model calls, SQL execution, and scoring logic against a single query.

## Results snapshot

Overall accuracy (correct / 50):

| Model                   | Schema-aware | Zero-shot |
|--------------------------|:-----------:|:---------:|
| GPT-4.1-mini              | 45          | 29        |
| Claude Haiku 4.5          | 45          | 31        |
| Gemini 3.5 Flash-Lite     | 40          | 28        |

Providing the schema roughly doubles the rate of hallucinated-schema
failures avoided; see [accuracy_summary.csv](accuracy_summary.csv),
[rq2_failure_summary.csv](rq2_failure_summary.csv), and
[charts/](charts/) for the full breakdown.

## Repository layout

```
queries.json                 50-question benchmark (question, expected columns, ground-truth SQL)
seed_data.sql                Deterministic seed for the thesis_nl2sql database
ER-Diagram.svg / erd.png     Entity-relationship diagram
run_pipeline_*.py            Per-model, per-condition SQL generation + scoring
aggregate_accuracy.py        RQ1: accuracy aggregation
extract_failures.py          RQ2: pull failing rows
classify_failures.py         RQ2: auto-suggest failure category
tally_failures.py            RQ2: tally by model/condition/level
measure_consistency.py       RQ3: repeat-run consistency
measure_efficiency.py        RQ3: EXPLAIN-based efficiency comparison
generate_charts.py           Builds charts/ from the aggregated CSVs
results_*.csv                Raw per-query results per model/condition
accuracy_*.csv               Aggregated accuracy (RQ1)
failures_*.csv, rq2_*.csv    Failure classification (RQ2)
consistency_*.csv            Consistency results (RQ3)
efficiency_*.csv             Efficiency results (RQ3)
charts/                      Generated PNG charts for the Results chapter
list_models.py, test_*.py    Utility / exploratory scripts
```

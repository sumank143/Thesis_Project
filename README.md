# Thesis: Natural Language to SQL — Benchmarking LLMs

Empirical evaluation of three LLMs (GPT-4.1-mini, Claude Haiku 4.5, Gemini
3.5 Flash-Lite) translating natural-language questions into MySQL queries
against a synthetic enterprise database. Measures semantic accuracy,
prompting-condition sensitivity (schema-aware vs. zero-shot), failure
patterns, output consistency, and query efficiency relative to hand-written
ground truth.

## Research questions

As defined in the thesis (Section 1.3):

- **RQ1 — Accuracy**: At what degree of accuracy can GPT-4.1-mini, Claude
  Haiku 4.5, and Gemini 3.5 Flash-Lite produce correct SQL against an
  enterprise MySQL schema, across the four query complexity levels?
- **RQ2 — Failure patterns**: What types of errors does each LLM most
  commonly produce, and how does the error mix change with query
  complexity?
- **RQ3 — Enterprise suitability**: Which LLM is best suited for
  production use, judged on query efficiency (execution plan vs. ground
  truth) and output consistency (same question, repeated)?
- **RQ4 — Prompting effectiveness**: How much does schema-aware
  (engineered) prompting improve SQL-generation accuracy over zero-shot
  (unengineered) prompting?

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
   CSVs into `accuracy_by_level.csv` (RQ1: accuracy per complexity level)
   and `accuracy_summary.csv` (RQ4: overall accuracy, schema-aware vs.
   zero-shot).

3. **Classify failures (RQ2)** — three-step pipeline over the results CSVs:
   - `extract_failures.py` → pulls every failing row into
     `failures_to_classify.csv`
   - `classify_failures.py` → auto-suggests a failure category
     (hallucinated schema, wrong join path, wrong aggregation, wrong
     filter, syntax error, unclear) into `failures_with_suggestions.csv`
   - `tally_failures.py` → tallies corrected/suggested categories by
     model, condition, and level into `rq2_failure_summary.csv`

   `failures_reviewed_final.csv` is the manually reviewed version of the
   auto-suggested categories, with a `review_note` explaining the
   corrected category for each failing query.

4. **Measure consistency (RQ3)** — `measure_consistency.py` re-runs a
   representative subset of 10 questions 5x per model and records whether
   the result set is identical across all repeats
   (`consistency_<model>.csv`).

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

## Results snapshot

Overall accuracy (correct / 50), from `accuracy_summary.csv`:

| Model                   | Schema-aware | Zero-shot |
|--------------------------|:-----------:|:---------:|
| GPT-4.1-mini              | 45 (90%)    | 29 (58%)  |
| Claude Haiku 4.5          | 45 (90%)    | 31 (62%)  |
| Gemini 3.5 Flash-Lite     | 40 (80%)    | 28 (56%)  |

Key findings (thesis Chapter 4):

- **RQ1**: Every model solves all 10 Level-1 (single-table) queries
  regardless of prompting condition. Zero-shot accuracy then collapses as
  soon as a query needs more than one table (Level 2+); schema-aware
  accuracy stays at 80%+ for GPT-4.1-mini and Claude Haiku 4.5 across all
  levels, and 60%+ for Gemini 3.5 Flash-Lite.
- **RQ2**: Of 82 total failures, 56 (68%) are hallucinated-schema errors —
  almost all zero-shot. Once the schema is provided, hallucinated-schema
  errors disappear entirely and wrong-join-path becomes the dominant
  failure (21 of 82 overall); wrong-aggregation and wrong-filter errors
  appear only at Level 4.
- **RQ3**: On correct queries, each model's execution plan matches the
  ground truth's about 9 times out of 10 (Claude 41/45, GPT 40/45, Gemini
  35/40). Output consistency (5 repeats x 10 questions) is 10/10 for
  GPT-4.1-mini, 9/10 for Claude Haiku 4.5, 8/10 for Gemini
  3.5 Flash-Lite — with the inconsistent queries concentrated at Levels 3–4.
- **RQ4**: Schema-aware prompting lifts accuracy for every model
  (GPT-4.1-mini +32pp, Claude Haiku 4.5 +28pp, Gemini 3.5 Flash-Lite
  +24pp) and eliminates hallucinated-schema errors outright — but it does
  not fix the harder reasoning failures (wrong joins/aggregation/filters),
  which persist and grow with query complexity even with the schema in
  hand.

See [accuracy_summary.csv](accuracy_summary.csv),
[accuracy_by_level.csv](accuracy_by_level.csv),
[rq2_failure_summary.csv](rq2_failure_summary.csv), the `consistency_*.csv`
/ `efficiency_*.csv` files, and [charts/](charts/) for the full breakdown.

## Extended prompting-condition study

[extended_conditions/](extended_conditions/) is a follow-up study (GPT-4.1-mini
and Gemini 3.5 Flash-Lite only) that breaks the schema-aware/zero-shot split
above into four finer-grained prompting conditions, to isolate exactly which
ingredient of "engineered" prompting drives the RQ4 accuracy gain:

| Condition | Prompt | Test set |
|-----------|--------|----------|
| 1 — unaware   | Question only, no schema                          | Full 50-query benchmark |
| 2 — aware, no hints | Schema + question, no examples              | Full 50-query benchmark |
| 3 — few-shot  | Schema + all 50 benchmark Q/SQL pairs as examples  | 20 new, harder L3/L4 queries ([new_queries_l3_l4.json](extended_conditions/new_queries_l3_l4.json)) |
| 4 — precise wording | Same as condition 3, but the 20 new questions are reworded to remove ambiguity ([new_queries_l3_l4_precise.json](extended_conditions/new_queries_l3_l4_precise.json)) | Same 20 queries, precisely worded |

Conditions 3→4 test whether failures on harder queries are a reasoning
limitation or a question-ambiguity artifact: `final_summary.csv` shows
accuracy jumping from 20% (both models, condition 3) to 70% (GPT-4.1-mini)
and 60% (Gemini 3.5 Flash-Lite) once the same questions are reworded
precisely (condition 4), with the per-query before/after flips recorded in
its `condition3_to_condition4_delta` section.

Run with:

```bash
python extended_conditions/run_condition1_unaware.py
python extended_conditions/run_condition2_aware_no_hints.py
python extended_conditions/run_condition3_fewshot.py
python extended_conditions/run_condition4_precise_wording.py
python extended_conditions/summarize_extended.py
python extended_conditions/classify_failures_extended.py
python extended_conditions/generate_charts_full.py
```

Outputs stay self-contained inside the folder: `results_condition*_<model>.csv`
(raw per-query results), `extended_summary.csv` / `final_summary.csv`
(aggregated accuracy, by-level breakdown, and the condition 3→4 delta,
produced by `summarize_extended.py`), `table9_classification.csv`
(row-level failure category, produced by `classify_failures_extended.py`
by executing each query's SQL against the live database — requires
`MYSQL_PASSWORD` in `.env`), and
[extended_conditions/charts/](extended_conditions/charts/) (Figures 7-8,
produced by `generate_charts_full.py`).

Figure 8 and Table 9's final counts additionally require a manual review
pass: `classify_failures_extended.py` flags rows needing a manual look
(execution errors it can't categorize, or rows found "correct after
normalization") in its console output; save the reviewed copy as
`table9_classification_final.csv` with a `category_final` column
(defaulting unreviewed rows' `category_final` to their `category`) before
running `generate_charts_full.py`.

## Repository layout

```
queries.json                 50-question benchmark (question, expected columns, ground-truth SQL)
seed_data.sql                Deterministic seed for the thesis_nl2sql database
ER-Diagram.svg / erd.png     Entity-relationship diagram
run_pipeline_*.py            Per-model, per-condition SQL generation + scoring
aggregate_accuracy.py        RQ1 (by level) + RQ4 (schema-aware vs zero-shot) accuracy aggregation
extract_failures.py          RQ2: pull failing rows
classify_failures.py         RQ2: auto-suggest failure category
tally_failures.py            RQ2: tally by model/condition/level
measure_consistency.py       RQ3: repeat-run consistency
measure_efficiency.py        RQ3: EXPLAIN-based efficiency comparison
generate_charts.py           Builds charts/ from the aggregated CSVs
results_*.csv                Raw per-query results per model/condition
accuracy_by_level.csv        Aggregated accuracy by complexity level (RQ1)
accuracy_summary.csv         Aggregated overall accuracy by condition (RQ4)
failures_*.csv, rq2_*.csv    Failure classification (RQ2)
failures_reviewed_final.csv  Manually reviewed failure categories with review notes
consistency_*.csv            Consistency results (RQ3)
efficiency_*.csv             Efficiency results (RQ3)
charts/                      Generated PNG charts for the Results chapter
list_models.py               Utility to list available Gemini models
extended_conditions/         Follow-up study: 4 finer-grained prompting conditions (GPT + Gemini)
```

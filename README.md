# Evaluating Large Language Models for Natural Language to SQL Query Generation in Enterprise Applications

This repository contains the code accompanying a thesis investigating how well
large language models (LLMs) translate natural-language questions into SQL
queries against enterprise-style relational schemas, and how their outputs
compare using exact-match and execution-accuracy metrics.

## Overview

The pipeline:

1. Loads a natural-language-question / gold-SQL benchmark
   (`data/sample_queries.jsonl`) defined against a sample enterprise database
   schema (`data/schema.sql`).
2. Prompts one or more configured LLMs (OpenAI, Anthropic) to generate a SQL
   query for each question.
3. Executes both the generated and gold queries against an in-memory SQLite
   database built from the schema.
4. Scores each prediction with:
   - **Exact match** — normalized string equality with the gold query.
   - **Execution accuracy** — whether the predicted query returns the same
     result set as the gold query.
5. Aggregates per-model results into a summary table and writes results to
   `results/`.

## Project structure

```
configs/            Evaluation run configuration (models, dataset, output paths)
data/                Sample enterprise schema and NL-to-SQL benchmark examples
src/nl2sql_eval/     Evaluation pipeline package
  config.py          YAML config loading
  datasets.py        Benchmark loading
  db.py              SQLite database construction and query execution
  models.py          LLM client wrappers (OpenAI, Anthropic) and prompt building
  metrics.py         Exact-match and execution-accuracy scoring
  evaluate.py        CLI entry point that runs the full evaluation
scripts/             Convenience entry point script
tests/               Unit tests for metrics and database execution
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Set API keys for whichever providers are configured in `configs/default.yaml`:

```bash
export OPENAI_API_KEY=...
export ANTHROPIC_API_KEY=...
```

## Running the evaluation

```bash
python scripts/run_evaluation.py --config configs/default.yaml
```

This prints a summary table and writes `results/summary.csv` and
`results/results.json` with per-question predictions and scores.

## Running tests

```bash
pytest
```

## Extending the benchmark

Add new examples to `data/sample_queries.jsonl`, one JSON object per line:

```json
{"question": "...", "db_id": "enterprise", "gold_sql": "SELECT ..."}
```

Extend `data/schema.sql` to add tables or seed data referenced by new
questions. Add new model providers by implementing `LLMClient` in
`src/nl2sql_eval/models.py` and registering it in `create_client`.

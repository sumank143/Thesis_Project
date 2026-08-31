import argparse
import json
from pathlib import Path

import pandas as pd

from .config import load_config
from .datasets import load_dataset
from .db import build_database, execute_query
from .metrics import exact_match, execution_accuracy
from .models import create_client


def evaluate_model(client, examples: list[dict], conn, schema_text: str) -> list[dict]:
    rows = []
    for example in examples:
        predicted_sql = client.generate_sql(example["question"], schema_text)
        predicted_rows = execute_query(conn, predicted_sql)
        gold_rows = execute_query(conn, example["gold_sql"])
        rows.append(
            {
                "question": example["question"],
                "gold_sql": example["gold_sql"],
                "predicted_sql": predicted_sql,
                "exact_match": exact_match(predicted_sql, example["gold_sql"]),
                "execution_accuracy": execution_accuracy(predicted_rows, gold_rows),
            }
        )
    return rows


def summarize(rows: list[dict]) -> dict:
    total = len(rows)
    if total == 0:
        return {"count": 0, "exact_match_rate": 0.0, "execution_accuracy_rate": 0.0}
    return {
        "count": total,
        "exact_match_rate": sum(r["exact_match"] for r in rows) / total,
        "execution_accuracy_rate": sum(r["execution_accuracy"] for r in rows) / total,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate LLMs on NL-to-SQL generation.")
    parser.add_argument("--config", default="configs/default.yaml")
    args = parser.parse_args()

    cfg = load_config(args.config)
    examples = load_dataset(cfg["dataset_path"])
    schema_text = Path(cfg["schema_path"]).read_text()
    conn = build_database(cfg["schema_path"])

    output_dir = Path(cfg.get("output_dir", "results"))
    output_dir.mkdir(parents=True, exist_ok=True)

    summary_table = []
    all_results = {}
    for model_cfg in cfg["models"]:
        client = create_client(model_cfg)
        rows = evaluate_model(client, examples, conn, schema_text)
        summary = summarize(rows)
        summary["model"] = model_cfg["name"]
        summary_table.append(summary)
        all_results[model_cfg["name"]] = rows

    with open(output_dir / "results.json", "w") as f:
        json.dump(all_results, f, indent=2)

    df = pd.DataFrame(summary_table).set_index("model")
    print(df)
    df.to_csv(output_dir / "summary.csv")


if __name__ == "__main__":
    main()

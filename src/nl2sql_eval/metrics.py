def normalize_sql(sql: str) -> str:
    return " ".join(sql.strip().rstrip(";").split()).lower()


def exact_match(predicted_sql: str, gold_sql: str) -> bool:
    return normalize_sql(predicted_sql) == normalize_sql(gold_sql)


def execution_accuracy(predicted_rows: list[tuple] | None, gold_rows: list[tuple] | None) -> bool:
    if predicted_rows is None or gold_rows is None:
        return False
    return set(predicted_rows) == set(gold_rows)

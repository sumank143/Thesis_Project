from nl2sql_eval.metrics import exact_match, execution_accuracy, normalize_sql


def test_normalize_sql_collapses_whitespace_and_case():
    assert normalize_sql("SELECT  *  FROM Foo;") == "select * from foo"


def test_exact_match_true_for_equivalent_formatting():
    assert exact_match("select * from foo", "SELECT * FROM foo;")


def test_exact_match_false_for_different_queries():
    assert not exact_match("SELECT * FROM foo", "SELECT * FROM bar")


def test_execution_accuracy_ignores_row_order():
    predicted = [(1, "a"), (2, "b")]
    gold = [(2, "b"), (1, "a")]
    assert execution_accuracy(predicted, gold)


def test_execution_accuracy_false_when_predicted_failed():
    assert not execution_accuracy(None, [(1, "a")])

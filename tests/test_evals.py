import pandas as pd
from evals.run_evals import compare_dataframes
from src.db import execute_query

def test_dataframe_exact_match():
    df1 = pd.DataFrame({"col_a": [1, 2, 3], "col_b": ["x", "y", "z"]})
    df2 = pd.DataFrame({"col_a": [1, 2, 3], "col_b": ["x", "y", "z"]})
    match, err = compare_dataframes(df1, df2)
    assert match is True
    assert err == ""

def test_dataframe_sorted_match():
    df1 = pd.DataFrame({"val": [10.0, 20.0]})
    df2 = pd.DataFrame({"val": [20.0, 10.0]})
    match, err = compare_dataframes(df1, df2)
    assert match is True
    assert err == ""

def test_dataframe_shape_mismatch():
    df1 = pd.DataFrame({"val": [1, 2]})
    df2 = pd.DataFrame({"val": [1, 2, 3]})
    match, err = compare_dataframes(df1, df2)
    assert match is False
    assert "Shape mismatch" in err

def test_dataframe_value_mismatch():
    df1 = pd.DataFrame({"val": [100.0]})
    df2 = pd.DataFrame({"val": [999.0]})
    match, err = compare_dataframes(df1, df2)
    assert match is False
    assert "mismatch" in err.lower()

def test_eval_questions_csv_integrity():
    df_questions = pd.read_csv("evals/questions.csv")
    assert len(df_questions) == 30
    assert "question" in df_questions.columns
    assert "gold_sql" in df_questions.columns

    for idx, row in df_questions.iterrows():
        df_res, err = execute_query(row["gold_sql"], "olist.db")
        assert err is None, f"Query {idx+1} failed: {err}"
        assert df_res is not None
        assert len(df_res) > 0, f"Query {idx+1} returned 0 rows"

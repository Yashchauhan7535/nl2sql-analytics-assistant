import argparse
import csv
import sys
from pathlib import Path
from typing import Tuple, List, Dict, Any
import numpy as np
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.config import OPENAI_API_KEY, OPENAI_MODEL, OPENAI_BASE_URL, DATABASE_PATH
from src.db import get_database_schema, execute_query
from src.generator import generate_sql
from src.validator import validate_sql

def compare_dataframes(df_gen: pd.DataFrame, df_gold: pd.DataFrame) -> Tuple[bool, str]:
    if df_gen is None and df_gold is None:
        return True, ""
    if df_gen is None or df_gold is None:
        return False, "One dataframe is None"

    if df_gen.shape != df_gold.shape:
        return False, f"Shape mismatch: generated {df_gen.shape} vs gold {df_gold.shape}"

    if df_gen.empty and df_gold.empty:
        return True, ""

    try:
        gen_vals = df_gen.values
        gold_vals = df_gold.values

        def normalize_val(v):
            if pd.isna(v):
                return "NULL"
            if isinstance(v, (int, float, np.number)):
                return round(float(v), 2)
            return str(v).strip().lower()

        gen_norm = [[normalize_val(x) for x in row] for row in gen_vals]
        gold_norm = [[normalize_val(x) for x in row] for row in gold_vals]

        if gen_norm == gold_norm:
            return True, ""

        gen_sorted = sorted(gen_norm, key=lambda r: str(r))
        gold_sorted = sorted(gold_norm, key=lambda r: str(r))

        if gen_sorted == gold_sorted:
            return True, ""

        return False, "Row value mismatch"
    except Exception as e:
        return False, f"Comparison error: {str(e)}"

def run_evaluations(
    eval_csv: str = "evals/questions.csv",
    db_path: str = "olist.db",
    failures_csv: str = "evals/failures.csv",
    api_key: str = "",
    model: str = "gpt-4o-mini",
    base_url: str = "https://api.openai.com/v1",
    use_gold_as_gen: bool = False
) -> Dict[str, Any]:
    eval_path = Path(eval_csv)
    if not eval_path.exists():
        raise FileNotFoundError(f"Evaluation file not found: {eval_csv}")

    df_cases = pd.read_csv(eval_path)
    total_cases = len(df_cases)
    schema_str = get_database_schema(db_path)

    exec_successes = 0
    match_successes = 0
    failures: List[Dict[str, Any]] = []

    print(f"\n--- Starting Evaluation on {total_cases} questions ---")
    print(f"Database: {db_path}")
    print(f"Mode: {'Gold replay (dry-run)' if use_gold_as_gen else f'LLM ({model})'}\n")

    for idx, row in df_cases.iterrows():
        case_id = row.get("id", idx + 1)
        question = row["question"]
        gold_sql = row["gold_sql"]

        gold_df, gold_err = execute_query(gold_sql, db_path)
        if gold_err:
            print(f"[{case_id}/{total_cases}] GOLD QUERY FAILED: {gold_err}")
            failures.append({
                "id": case_id,
                "question": question,
                "gold_sql": gold_sql,
                "generated_sql": "",
                "error_stage": "Gold Query Execution",
                "error_message": gold_err
            })
            continue

        if use_gold_as_gen:
            gen_sql = gold_sql
            gen_err = None
        else:
            gen_sql, gen_err = generate_sql(
                question=question,
                schema_str=schema_str,
                api_key=api_key,
                model=model,
                base_url=base_url
            )

        if gen_err:
            failures.append({
                "id": case_id,
                "question": question,
                "gold_sql": gold_sql,
                "generated_sql": "",
                "error_stage": "LLM Generation",
                "error_message": gen_err
            })
            print(f"[{case_id}/{total_cases}] Generation Failed")
            continue

        is_valid, val_err, cleaned_sql = validate_sql(gen_sql, db_path)
        if not is_valid:
            failures.append({
                "id": case_id,
                "question": question,
                "gold_sql": gold_sql,
                "generated_sql": gen_sql,
                "error_stage": "SQL Validation",
                "error_message": val_err
            })
            print(f"[{case_id}/{total_cases}] Validation Failed: {val_err}")
            continue

        gen_df, exec_err = execute_query(cleaned_sql, db_path)
        if exec_err:
            failures.append({
                "id": case_id,
                "question": question,
                "gold_sql": gold_sql,
                "generated_sql": cleaned_sql,
                "error_stage": "Query Execution",
                "error_message": exec_err
            })
            print(f"[{case_id}/{total_cases}] Execution Error: {exec_err}")
            continue

        exec_successes += 1
        matches, reason = compare_dataframes(gen_df, gold_df)

        if matches:
            match_successes += 1
            print(f"[{case_id}/{total_cases}] PASSED (Execution & Result Match)")
        else:
            failures.append({
                "id": case_id,
                "question": question,
                "gold_sql": gold_sql,
                "generated_sql": cleaned_sql,
                "error_stage": "Result Match",
                "error_message": reason
            })
            print(f"[{case_id}/{total_cases}] MISMATCH: {reason}")

    failures_path = Path(failures_csv)
    failures_path.parent.mkdir(parents=True, exist_ok=True)
    with open(failures_path, "w", newline="", encoding="utf-8") as f:
        fieldnames = ["id", "question", "gold_sql", "generated_sql", "error_stage", "error_message"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(failures)

    exec_acc = (exec_successes / total_cases) * 100 if total_cases > 0 else 0.0
    match_acc = (match_successes / total_cases) * 100 if total_cases > 0 else 0.0

    print("\n" + "=" * 50)
    print("           EVALUATION SUMMARY")
    print("=" * 50)
    print(f"Total Questions Evaluated : {total_cases}")
    print(f"Execution Accuracy        : {exec_acc:.1f}% ({exec_successes}/{total_cases})")
    print(f"Result-Match Accuracy     : {match_acc:.1f}% ({match_successes}/{total_cases})")
    print(f"Total Failures Recorded   : {len(failures)}")
    print(f"Failures CSV Output       : {failures_path.resolve()}")
    print("=" * 50 + "\n")

    return {
        "total": total_cases,
        "execution_accuracy": exec_acc,
        "result_match_accuracy": match_acc,
        "failures_count": len(failures),
        "failures_file": str(failures_path)
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--eval-file", default="evals/questions.csv")
    parser.add_argument("--db-path", default=DATABASE_PATH)
    parser.add_argument("--failures-file", default="evals/failures.csv")
    parser.add_argument("--api-key", default=OPENAI_API_KEY)
    parser.add_argument("--model", default=OPENAI_MODEL)
    parser.add_argument("--base-url", default=OPENAI_BASE_URL)
    parser.add_argument("--dry-run", action="store_true", help="Replay gold SQL to test harness")
    args = parser.parse_args()

    use_dry = args.dry_run or (not args.api_key)
    if not args.api_key and not args.dry_run:
        print("Note: No OPENAI_API_KEY detected in environment. Running in benchmark dry-run mode using gold queries.")

    run_evaluations(
        eval_csv=args.eval_file,
        db_path=args.db_path,
        failures_csv=args.failures_file,
        api_key=args.api_key,
        model=args.model,
        base_url=args.base_url,
        use_gold_as_gen=use_dry
    )

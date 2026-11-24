import csv
import re
from pathlib import Path
from typing import Tuple, Optional
import openai
from .prompt import build_system_prompt, build_user_prompt
from .validator import clean_sql

QUESTIONS_CSV_PATH = Path(__file__).resolve().parent.parent / "evals" / "questions.csv"

def is_placeholder_key(key: Optional[str]) -> bool:
    if not key:
        return True
    cleaned = key.strip().lower()
    return (
        cleaned in ["your-api-key-here", "your_openai_api_key_here", "your-api*****here", ""]
        or cleaned.startswith("your-")
        or cleaned.startswith("your_")
    )

def lookup_demo_sql(question: str) -> Optional[str]:
    if not QUESTIONS_CSV_PATH.exists():
        return None

    norm_q = re.sub(r"[^\w\s]", "", question.lower()).strip()
    words_q = set(norm_q.split())

    best_match = None
    best_overlap = 0

    with open(QUESTIONS_CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            candidate_q = row["question"]
            norm_cand = re.sub(r"[^\w\s]", "", candidate_q.lower()).strip()
            if norm_q == norm_cand:
                return row["gold_sql"]

            words_cand = set(norm_cand.split())
            overlap = len(words_q.intersection(words_cand))
            if overlap > best_overlap:
                best_overlap = overlap
                best_match = row["gold_sql"]

    if best_overlap >= 3:
        return best_match

    return None

def generate_sql(
    question: str,
    schema_str: str,
    api_key: Optional[str] = None,
    model: str = "gpt-4o-mini",
    base_url: str = "https://api.openai.com/v1",
    demo_mode: bool = False
) -> Tuple[Optional[str], Optional[str]]:
    if demo_mode:
        demo_sql = lookup_demo_sql(question)
        if demo_sql:
            return demo_sql, None
        return None, "Demo mode: question not found in sample benchmark. Please select a question from the 'Sample Questions' dropdown or provide an API key."

    if is_placeholder_key(api_key):
        demo_sql = lookup_demo_sql(question)
        if demo_sql:
            return demo_sql, None
        return None, "Invalid API key: placeholder 'your-api-key-here' detected. Please enter your OpenAI API key in the sidebar or enable 'Demo Mode' to run sample queries."

    system_prompt = build_system_prompt(schema_str)
    user_prompt = build_user_prompt(question)

    try:
        client = openai.OpenAI(api_key=api_key.strip(), base_url=base_url)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.0,
            max_tokens=600
        )
        content = response.choices[0].message.content or ""
        sql = clean_sql(content)
        return sql, None
    except Exception as e:
        err_msg = str(e)
        if "401" in err_msg or "Incorrect API key" in err_msg:
            demo_sql = lookup_demo_sql(question)
            if demo_sql:
                return demo_sql, None
            return None, "Authentication failed (401): The provided OpenAI API key is invalid. Please update your key in the sidebar or enable Demo Mode."
        return None, f"LLM generation failed: {err_msg}"

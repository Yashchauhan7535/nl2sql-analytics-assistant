from typing import Tuple, Optional
import openai
from .prompt import build_system_prompt, build_user_prompt
from .validator import clean_sql

def generate_sql(
    question: str,
    schema_str: str,
    api_key: Optional[str] = None,
    model: str = "gpt-4o-mini",
    base_url: str = "https://api.openai.com/v1"
) -> Tuple[Optional[str], Optional[str]]:
    if not api_key:
        return None, "API key is missing. Please set OPENAI_API_KEY in your .env file."

    system_prompt = build_system_prompt(schema_str)
    user_prompt = build_user_prompt(question)

    try:
        client = openai.OpenAI(api_key=api_key, base_url=base_url)
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
        return None, f"LLM generation failed: {str(e)}"

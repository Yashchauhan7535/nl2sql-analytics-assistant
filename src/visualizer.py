import re
from typing import Optional, Tuple
import pandas as pd
import altair as alt

def is_date_or_time_col(col_name: str, series: pd.Series) -> bool:
    name_lower = col_name.lower()
    if any(keyword in name_lower for keyword in ["date", "time", "month", "year", "day", "week", "period", "quarter"]):
        return True
    if pd.api.types.is_datetime64_any_dtype(series):
        return True
    if series.dtype == object and len(series) > 0:
        first_val = str(series.dropna().iloc[0]) if not series.dropna().empty else ""
        if re.match(r"^\d{4}-\d{2}(-\d{2})?", first_val):
            return True
    return False

def recommend_chart(df: pd.DataFrame) -> Tuple[Optional[str], Optional[alt.Chart]]:
    if df is None or df.empty:
        return None, None

    cols = list(df.columns)
    num_rows = len(df)
    if num_rows <= 1 and len(cols) == 1:
        return None, None

    numeric_cols = [c for c in cols if pd.api.types.is_numeric_dtype(df[c])]
    non_numeric_cols = [c for c in cols if c not in numeric_cols]

    if not numeric_cols:
        return None, None

    date_col = next((c for c in non_numeric_cols if is_date_or_time_col(c, df[c])), None)
    cat_col = next((c for c in non_numeric_cols if c != date_col), None)

    if date_col and numeric_cols:
        val_col = numeric_cols[0]
        chart_data = df.copy()
        if cat_col and len(df[cat_col].unique()) <= 7:
            chart = (
                alt.Chart(chart_data)
                .mark_line(point=True)
                .encode(
                    x=alt.X(f"{date_col}:O", title=date_col),
                    y=alt.Y(f"{val_col}:Q", title=val_col),
                    color=alt.Color(f"{cat_col}:N", title=cat_col),
                    tooltip=[date_col, cat_col, val_col]
                )
                .properties(width="container", height=350)
                .interactive()
            )
            return "line", chart
        else:
            chart = (
                alt.Chart(chart_data)
                .mark_line(point=True, color="#4F46E5")
                .encode(
                    x=alt.X(f"{date_col}:O", title=date_col),
                    y=alt.Y(f"{val_col}:Q", title=val_col),
                    tooltip=[date_col, val_col]
                )
                .properties(width="container", height=350)
                .interactive()
            )
            return "line", chart

    if cat_col and numeric_cols:
        val_col = numeric_cols[0]
        chart_data = df.head(20).copy()
        chart = (
            alt.Chart(chart_data)
            .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
            .encode(
                x=alt.X(f"{cat_col}:N", sort="-y", title=cat_col),
                y=alt.Y(f"{val_col}:Q", title=val_col),
                color=alt.Color(f"{val_col}:Q", scale=alt.Scale(scheme="blues"), legend=None),
                tooltip=[cat_col, val_col]
            )
            .properties(width="container", height=360)
        )
        return "bar", chart

    if len(numeric_cols) >= 2:
        x_col = numeric_cols[0]
        y_col = numeric_cols[1]
        chart = (
            alt.Chart(df)
            .mark_circle(size=70, opacity=0.7, color="#0EA5E9")
            .encode(
                x=alt.X(f"{x_col}:Q", title=x_col),
                y=alt.Y(f"{y_col}:Q", title=y_col),
                tooltip=[c for c in cols[:5]]
            )
            .properties(width="container", height=350)
            .interactive()
        )
        return "scatter", chart

    if len(numeric_cols) == 1 and non_numeric_cols:
        first_col = non_numeric_cols[0]
        val_col = numeric_cols[0]
        chart_data = df.head(15).copy()
        chart = (
            alt.Chart(chart_data)
            .mark_bar()
            .encode(
                y=alt.Y(f"{first_col}:N", sort="-x", title=first_col),
                x=alt.X(f"{val_col}:Q", title=val_col),
                color=alt.Color(f"{val_col}:Q", scale=alt.Scale(scheme="tealblues"), legend=None),
                tooltip=[first_col, val_col]
            )
            .properties(width="container", height=360)
        )
        return "bar", chart

    return None, None

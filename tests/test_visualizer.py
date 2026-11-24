import pandas as pd
from src.visualizer import recommend_chart

def test_recommend_line_chart_for_time_series():
    df = pd.DataFrame({
        "order_month": ["2017-01", "2017-02", "2017-03"],
        "total_revenue": [12500.50, 18300.00, 21450.75]
    })
    chart_type, chart = recommend_chart(df)
    assert chart_type == "line"
    assert chart is not None

def test_recommend_bar_chart_for_categories():
    df = pd.DataFrame({
        "category": ["health_beauty", "computers_accessories", "watches_gifts"],
        "total_sales": [50000.0, 42000.0, 38000.0]
    })
    chart_type, chart = recommend_chart(df)
    assert chart_type == "bar"
    assert chart is not None

def test_recommend_scatter_chart_for_numeric_pairs():
    df = pd.DataFrame({
        "product_weight_g": [250.0, 500.0, 1200.0, 3400.0],
        "freight_value": [12.5, 18.0, 24.5, 55.0]
    })
    chart_type, chart = recommend_chart(df)
    assert chart_type == "scatter"
    assert chart is not None

def test_no_chart_for_single_scalar():
    df = pd.DataFrame({"total_orders": [850]})
    chart_type, chart = recommend_chart(df)
    assert chart_type is None
    assert chart is None

def test_no_chart_for_empty_dataframe():
    chart_type, chart = recommend_chart(pd.DataFrame())
    assert chart_type is None
    assert chart is None

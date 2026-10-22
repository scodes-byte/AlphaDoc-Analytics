import os
import sys
import math

import numpy as np
import pytest
from scipy import stats

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "backend"))
os.environ["GEMINI_API_KEY"] = ""  # tests always run offline

from pipeline.analytics import AnalyticsEngine
from pipeline.table_parser import extract_kpi_table, parse_number, merge_kpi_histories, normalize_period
from pipeline.narrative import score_sentiment
from pipeline.llm_extractor import LLMExtractor

SAMPLE_TABLE = """
F I N A N C I A L   S U M M A R Y
($ in millions, except percentages and per share data) Q4-2023 Q1-2024 Q2-2024 Q3-2024 Q4-2024 YoY
Total automotive revenues 21,563 17,378 19,878 20,016 19,798 -8%
Total revenues 25,167 21,301 25,500 25,182 25,707 2%
Income from operations 2,064 1,171 1,605 2,717 1,583 -23%
Operating margin 8.2% 5.5% 6.3% 10.8% 6.2% -204 bp
Net income attributable to common stockholders (GAAP) 7,928 1,129 1,478 2,167 2,317 -71%
Net income attributable to common stockholders (non-GAAP) 2,485 1,536 1,812 2,505 2,566 3%
EPS attributable to common stockholders, diluted (GAAP) 2.27 0.34 0.42 0.62 0.66 -71%
Free cash flow 2,064 (2,531) 1,342 2,742 2,031 -2%
"""


# ---------- table parser ----------

def test_parse_number_handles_financial_formats():
    assert parse_number("1,234") == 1234
    assert parse_number("5.5%") == 5.5
    assert parse_number("(2,531)") == -2531
    assert parse_number("abc") is None


def test_normalize_period():
    assert normalize_period("4", "24") == "Q4 2024"
    assert normalize_period("1", "2025") == "Q1 2025"


def test_extracts_gaap_rows_and_ignores_yoy_column():
    kpis = extract_kpi_table(SAMPLE_TABLE)
    assert [k["period"] for k in kpis] == ["Q4 2023", "Q1 2024", "Q2 2024", "Q3 2024", "Q4 2024"]
    assert kpis[-1] == {"period": "Q4 2024", "revenue": 25707, "operating_margin": 6.2, "net_income": 2317, "eps": 0.66}
    # Must pick the GAAP row, not the non-GAAP one, and total (not automotive) revenue
    assert kpis[0]["net_income"] == 7928
    assert kpis[0]["revenue"] == 25167


def test_operating_margin_is_derived_when_missing():
    text = "Metric Q1 2024 Q2 2024 Q3 2024\nTotal revenues 100 200 400\nOperating income 10 30 40\n"
    kpis = extract_kpi_table(text)
    assert [k["operating_margin"] for k in kpis] == [10.0, 15.0, 10.0]


def test_no_table_returns_empty():
    assert extract_kpi_table("Just some prose about a company with no numbers.") == []


def test_merge_prefers_later_reports_and_sorts():
    old = [{"period": "Q2 2024", "revenue": 1.0}, {"period": "Q1 2024", "revenue": 1.0}]
    new = [{"period": "Q2 2024", "revenue": 2.0}, {"period": "Q3 2024", "revenue": 3.0}]
    merged = merge_kpi_histories([old, new])
    assert [r["period"] for r in merged] == ["Q1 2024", "Q2 2024", "Q3 2024"]
    assert merged[1]["revenue"] == 2.0


# ---------- analytics ----------

def test_ols_prediction_interval_matches_textbook_formula():
    x = np.arange(5)
    y = np.array([10.0, 12.0, 13.0, 15.0, 18.0])
    result = AnalyticsEngine.ols_forecast(x, y, x_new=5)

    slope, intercept = np.polyfit(x, y, 1)
    resid = y - (intercept + slope * x)
    s = math.sqrt(np.sum(resid ** 2) / 3)
    se = s * math.sqrt(1 + 1 / 5 + (5 - 2) ** 2 / 10)
    t = stats.t.ppf(0.975, 3)
    expected = intercept + slope * 5

    assert result["predicted"] == pytest.approx(expected, abs=0.01)
    assert result["lower_95"] == pytest.approx(expected - t * se, abs=0.01)
    assert result["upper_95"] == pytest.approx(expected + t * se, abs=0.01)
    assert result["trend_slope"] == pytest.approx(slope, abs=0.01)


def test_perfect_line_has_zero_width_interval():
    result = AnalyticsEngine.ols_forecast(np.arange(4), np.array([1.0, 2.0, 3.0, 4.0]), x_new=4)
    assert result["predicted"] == 5.0
    assert result["lower_95"] == result["upper_95"] == 5.0
    assert result["r_squared"] == 1.0


def test_forecast_sorts_and_handles_strings_and_missing_values():
    kpis = [
        {"period": "Q3 2024", "revenue": "300", "net_income": None},
        {"period": "Q1 2024", "revenue": "1,00", "net_income": 10},
        {"period": "Q2 2024", "revenue": 200.0, "net_income": "(5)"},
    ]
    result = AnalyticsEngine.forecast_next_period(kpis)
    assert [r["period"] for r in result["historical"]] == ["Q1 2024", "Q2 2024", "Q3 2024"]
    assert result["next_period"] == "Q4 2024"
    assert result["forecasts"]["revenue"]["predicted"] == pytest.approx(400.0)
    # Net income has only 2 usable points, so no forecast is produced for it
    assert "net_income" not in result["forecasts"]
    # Loss-to-profit growth uses abs(previous) and stays finite
    assert result["historical"][1]["net_income_growth_qoq"] == -150.0


def test_growth_is_none_when_previous_value_is_zero():
    rows = AnalyticsEngine.calculate_growth_rates([
        {"period": "Q1 2024", "revenue": 0.0, "net_income": 0.0},
        {"period": "Q2 2024", "revenue": 10.0, "net_income": 5.0},
    ])
    assert rows[1]["revenue_growth_qoq"] is None


def test_forecast_requires_three_periods():
    with pytest.raises(ValueError):
        AnalyticsEngine.forecast_next_period([{"period": "Q1 2024", "revenue": 1}, {"period": "Q2 2024", "revenue": 2}])


def test_quarter_rollover():
    assert AnalyticsEngine._increment_quarter("Q4 2025") == "Q1 2026"
    assert AnalyticsEngine._increment_quarter("FY2025") == "Next Period"


def test_backtest_beats_naive_on_linear_trend():
    result = AnalyticsEngine.backtest([10, 20, 30, 40, 50, 60])
    assert result["ols_mape"] == 0.0
    assert result["naive_mape"] > 0


# ---------- narrative & extractor ----------

def test_sentiment_lexicon_direction():
    assert score_sentiment("Record growth and strong, improved profitability.")["score"] > 0
    assert score_sentiment("Revenue declined amid headwinds, uncertainty and losses.")["score"] < 0


def test_offline_extractor_uses_table_parser_and_grounding():
    result = LLMExtractor().analyze_document(SAMPLE_TABLE, "report.pdf", document_type="pdf")
    assert result["extraction_mode"]["kpis"] == "rule_based_table_parser"
    assert result["extraction_mode"]["kpi_values_found_in_source_text"] == 1.0
    assert len(result["kpis"]) == 5


def test_offline_extractor_refuses_to_invent_data():
    with pytest.raises(ValueError):
        LLMExtractor().analyze_document("No tables here at all.", "empty.pdf", document_type="pdf")
    with pytest.raises(ValueError):
        LLMExtractor().analyze_document("[image]", "chart.png", document_type="image", image_b64="aGVsbG8=")

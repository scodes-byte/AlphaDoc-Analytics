"""
Reproducible evaluation on the bundled Tesla 2024 quarterly update PDFs.

1. Extraction accuracy: compares the rule-based parser output for each report with
   hand-checked values from the reports' "Financial Summary" tables.
2. Cross-report consistency: the same quarter appears in up to five reports; the
   extracted values must agree.
3. Forecast backtest: walk-forward one-step-ahead forecasts over the merged 8-quarter
   revenue series, OLS trend vs. a naive last-value baseline.

Run from the project root:  python backend/evaluate.py
"""
import os
import sys
import glob

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pipeline.document_processor import DocumentProcessor
from pipeline.table_parser import extract_kpi_table, merge_kpi_histories
from pipeline.analytics import AnalyticsEngine

# Hand-checked from the Financial Summary tables (page 4) of Tesla's 2024 quarterly updates.
# revenue/net income in $M (GAAP net income attributable to common stockholders), margin in %, diluted GAAP EPS.
GROUND_TRUTH = {
    "Q1 2023": (23329, 11.4, 2513, 0.73),
    "Q2 2023": (24927, 9.6, 2703, 0.78),
    "Q3 2023": (23350, 7.6, 1853, 0.53),
    "Q4 2023": (25167, 8.2, 7928, 2.27),
    "Q1 2024": (21301, 5.5, 1129, 0.34),
    "Q2 2024": (25500, 6.3, 1478, 0.42),
    "Q3 2024": (25182, 10.8, 2167, 0.62),
    "Q4 2024": (25707, 6.2, 2317, 0.66),
}
FIELDS = ("revenue", "operating_margin", "net_income", "eps")


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pdfs = sorted(glob.glob(os.path.join(root, "real_datasets", "*.pdf")))
    histories = []
    checked = correct = 0

    print("1) Extraction accuracy per report")
    for path in pdfs:
        kpis = extract_kpi_table(DocumentProcessor.process_file(path)["text_content"])
        histories.append(kpis)
        report_ok = 0
        for record in kpis:
            truth = GROUND_TRUTH.get(record["period"])
            if truth is None:
                continue
            for field, expected in zip(FIELDS, truth):
                checked += 1
                if record[field] is not None and abs(record[field] - expected) < 1e-6:
                    correct += 1
                    report_ok += 1
        print(f"   {os.path.basename(path)}: {len(kpis)} quarters, {report_ok}/{len(kpis) * 4} fields correct")
    print(f"   Field-level accuracy: {correct}/{checked} = {correct / checked:.1%}\n")

    print("2) Cross-report consistency")
    seen = {}
    conflicts = 0
    for kpis in histories:
        for record in kpis:
            values = tuple(record[f] for f in FIELDS)
            if record["period"] in seen and seen[record["period"]] != values:
                conflicts += 1
            seen[record["period"]] = values
    print(f"   Overlapping quarters with conflicting values: {conflicts}\n")

    merged = merge_kpi_histories(histories)
    print(f"3) Walk-forward backtest on {len(merged)} merged quarters ({merged[0]['period']} to {merged[-1]['period']})")
    for field in ("revenue", "net_income"):
        series = [r[field] for r in merged]
        result = AnalyticsEngine.backtest(series)
        print(f"   {field}: OLS MAPE {result['ols_mape']}% | naive MAPE {result['naive_mape']}% | "
              f"95% interval coverage {result['interval_coverage']:.0%} over {len(result['steps'])} forecasts")
        for step in result["steps"]:
            print(f"      predict {merged[step['step']]['period']}: actual {step['actual']:,.0f} | "
                  f"OLS {step['ols']:,.0f} | naive {step['naive']:,.0f} | in interval: {step['inside_interval']}")


if __name__ == "__main__":
    main()

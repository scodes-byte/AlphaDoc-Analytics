import re
import numpy as np
from typing import Dict, Any, List, Optional
from scipy import stats
from sklearn.linear_model import LinearRegression

from pipeline.table_parser import period_sort_key

TARGET_VARIABLES = ["revenue", "operating_margin", "net_income", "eps"]
MIN_PERIODS = 3  # OLS with an intercept and slope needs n - 2 >= 1 residual degrees of freedom


class AnalyticsEngine:
    """
    Data Science Analytics Engine: cleans the extracted quarterly series, computes
    quarter-over-quarter growth, and fits an OLS linear trend per KPI to forecast the
    next quarter with a 95% prediction interval.
    """

    @staticmethod
    def prepare_series(kpis: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Coerces values to floats, drops rows without a period or revenue, de-duplicates and sorts chronologically."""
        by_period: Dict[str, Dict[str, Any]] = {}
        for item in kpis:
            period = str(item.get("period") or "").strip()
            if not period:
                continue
            record = {"period": period}
            for var in TARGET_VARIABLES:
                record[var] = _to_float(item.get(var))
            if record["revenue"] is None:
                continue
            by_period[period] = record
        return sorted(by_period.values(), key=lambda r: period_sort_key(r["period"]))

    @staticmethod
    def calculate_growth_rates(kpis: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Adds QoQ growth (%) for revenue and net income. The denominator uses the absolute
        previous value so growth from a loss to a smaller loss is reported as positive.
        Growth is None for the first period or when the previous value is 0 or missing.
        """
        enriched = []
        for idx, item in enumerate(kpis):
            record = dict(item)
            for var in ("revenue", "net_income"):
                prev = kpis[idx - 1].get(var) if idx > 0 else None
                cur = item.get(var)
                if prev in (None, 0) or cur is None:
                    record[f"{var}_growth_qoq"] = None
                else:
                    record[f"{var}_growth_qoq"] = round((cur - prev) / abs(prev) * 100, 2)
            enriched.append(record)
        return enriched

    @staticmethod
    def ols_forecast(x: np.ndarray, y: np.ndarray, x_new: float, confidence: float = 0.95) -> Dict[str, Any]:
        """
        Fits y = b0 + b1 * t by OLS and returns the forecast at x_new with a prediction interval:

            s       = sqrt(SSE / (n - 2))                       residual standard error
            se_pred = s * sqrt(1 + 1/n + (x_new - x_bar)^2 / Sxx)
            PI      = y_hat +/- t_{(1+confidence)/2, n-2} * se_pred

        The t-distribution (not z = 1.96) is used because n is small and sigma is estimated.
        The "1 +" term makes it a prediction interval for a single new quarter rather than a
        confidence interval for the mean trend line, which would be much too narrow.
        """
        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float)
        n = len(x)
        model = LinearRegression().fit(x.reshape(-1, 1), y)
        fitted = model.predict(x.reshape(-1, 1))
        predicted = float(model.predict(np.array([[x_new]]))[0])

        dof = n - 2
        sse = float(np.sum((y - fitted) ** 2))
        s = np.sqrt(sse / dof)
        sxx = float(np.sum((x - x.mean()) ** 2))
        se_pred = s * np.sqrt(1 + 1 / n + (x_new - x.mean()) ** 2 / sxx)
        t_crit = stats.t.ppf((1 + confidence) / 2, dof)
        margin = t_crit * se_pred

        sst = float(np.sum((y - y.mean()) ** 2))
        r_squared = 1 - sse / sst if sst > 0 else 1.0

        return {
            "predicted": round(predicted, 2),
            "lower_95": round(predicted - margin, 2),
            "upper_95": round(predicted + margin, 2),
            "trend_slope": round(float(model.coef_[0]), 2),
            "r_squared": round(r_squared, 3),
            "n_obs": n,
        }

    @classmethod
    def forecast_next_period(cls, kpis: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Forecasts every KPI for the quarter after the last observed one.

        Raises:
            ValueError: if fewer than MIN_PERIODS quarters with revenue are available.
        """
        series = cls.prepare_series(kpis)
        if len(series) < MIN_PERIODS:
            raise ValueError(
                f"At least {MIN_PERIODS} quarters of data are needed to fit a trend; found {len(series)}."
            )

        enriched = cls.calculate_growth_rates(series)
        n_periods = len(enriched)

        forecasts = {}
        for var in TARGET_VARIABLES:
            points = [(i, r[var]) for i, r in enumerate(enriched) if r[var] is not None]
            if len(points) < MIN_PERIODS:
                continue
            x, y = zip(*points)
            fc = cls.ols_forecast(np.array(x), np.array(y), x_new=n_periods)
            if var == "revenue":
                fc["lower_95"] = max(0.0, fc["lower_95"])  # revenue cannot be negative
            forecasts[var] = fc

        return {
            "historical": enriched,
            "next_period": cls._increment_quarter(enriched[-1]["period"]),
            "forecasts": forecasts,
            "model": "OLS linear trend on quarter index, 95% prediction interval (t-distribution)",
        }

    @classmethod
    def backtest(cls, values: List[float], min_train: int = MIN_PERIODS) -> Dict[str, Any]:
        """
        Walk-forward evaluation: for each step t >= min_train, train on values[:t] and predict values[t].
        Compares the OLS trend with a naive "next quarter = last quarter" baseline, and reports how often
        the actual value fell inside the 95% prediction interval (empirical coverage).
        """
        y = np.asarray(values, dtype=float)
        rows = []
        for t in range(min_train, len(y)):
            fc = cls.ols_forecast(np.arange(t), y[:t], x_new=t)
            rows.append({
                "step": t,
                "actual": float(y[t]),
                "ols": fc["predicted"],
                "naive": float(y[t - 1]),
                "inside_interval": fc["lower_95"] <= y[t] <= fc["upper_95"],
            })
        if not rows:
            return {"steps": [], "ols_mape": None, "naive_mape": None, "interval_coverage": None}

        def mape(key):
            return round(float(np.mean([abs(r[key] - r["actual"]) / abs(r["actual"]) for r in rows])) * 100, 2)

        return {
            "steps": rows,
            "ols_mape": mape("ols"),
            "naive_mape": mape("naive"),
            "interval_coverage": round(sum(r["inside_interval"] for r in rows) / len(rows), 2),
        }

    @staticmethod
    def _increment_quarter(quarter_str: str) -> str:
        """Increments a quarter label, e.g. 'Q4 2025' -> 'Q1 2026'."""
        match = re.match(r"Q([1-4])\s+(\d{4})", quarter_str.strip())
        if not match:
            return "Next Period"
        q_num, year = int(match.group(1)), int(match.group(2))
        return f"Q1 {year + 1}" if q_num == 4 else f"Q{q_num + 1} {year}"


def _to_float(value: Any) -> Optional[float]:
    """Accepts numbers or strings such as '1,234.5', '5.5%' or '(2,531)'."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value) if np.isfinite(value) else None
    text = str(value).strip().replace(",", "").replace("$", "").replace("%", "")
    negative = text.startswith("(") and text.endswith(")")
    try:
        number = float(text.strip("()"))
    except ValueError:
        return None
    return -number if negative else number


if __name__ == "__main__":
    test_data = [
        {"period": "Q1 2025", "revenue": 100.0, "operating_margin": 10.0, "net_income": 10.0, "eps": 0.50},
        {"period": "Q2 2025", "revenue": 110.0, "operating_margin": 11.0, "net_income": 11.5, "eps": 0.55},
        {"period": "Q3 2025", "revenue": 120.0, "operating_margin": 10.5, "net_income": 13.0, "eps": 0.62},
        {"period": "Q4 2025", "revenue": 135.0, "operating_margin": 12.0, "net_income": 15.5, "eps": 0.70},
    ]
    results = AnalyticsEngine.forecast_next_period(test_data)
    print("Next Period:", results["next_period"])
    print("Revenue Forecast:", results["forecasts"]["revenue"])

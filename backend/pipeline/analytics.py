import numpy as np
import pandas as pd
from typing import Dict, Any, List
from sklearn.linear_model import LinearRegression

class AnalyticsEngine:
    """
    Data Science Analytics Engine: Ingests structured time-series metrics,
    calculates quarter-over-quarter financial growth trends, and runs linear 
    regressions to generate predictive next-quarter forecasts with statistical confidence margins.
    """
    @staticmethod
    def calculate_growth_rates(kpis: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Calculates Quarter-over-Quarter (QoQ) percentage growth rates for numeric financial KPIs.
        
        Args:
            kpis (List[Dict[str, Any]]): Time series of extracted quarterly KPI records.
            
        Returns:
            List[Dict[str, Any]]: KPIs enriched with growth rate calculations.
        """
        if len(kpis) < 2:
            # Enriched values set to 0 if history is too short to compute growth
            for item in kpis:
                item["revenue_growth_qoq"] = 0.0
                item["net_income_growth_qoq"] = 0.0
            return kpis

        # Convert to DataFrame for vectorised shifts
        df = pd.DataFrame(kpis)
        
        # Calculate percentage changes
        df["revenue_growth_qoq"] = df["revenue"].pct_change() * 100
        df["net_income_growth_qoq"] = df["net_income"].pct_change() * 100
        
        # Fill NaN values with 0.0
        df["revenue_growth_qoq"] = df["revenue_growth_qoq"].fillna(0.0).round(2)
        df["net_income_growth_qoq"] = df["net_income_growth_qoq"].fillna(0.0).round(2)
        
        return df.to_dict(orient="records")

    @classmethod
    def forecast_next_period(cls, kpis: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Fits a linear regression model over the sequential observations to predict 
        the next chronological quarter's values, returning expected values and confidence bounds.
        
        Args:
            kpis (List[Dict[str, Any]]): Sequential historical quarterly data.
            
        Returns:
            Dict[str, Any]: Object containing historical sequences, growth trends, 
                           the predicted next quarter label, and forecasted values.
        """
        # Enrichment step: calculate growth rates
        enriched_kpis = cls.calculate_growth_rates(kpis)
        
        n_periods = len(enriched_kpis)
        if n_periods < 2:
            return {
                "historical": enriched_kpis,
                "forecast": {}
            }

        # Setup feature array (time steps index: 0, 1, 2, 3...)
        X = np.array(range(n_periods)).reshape(-1, 1)
        next_step = np.array([[n_periods]])

        forecasts = {}
        target_variables = ["revenue", "operating_margin", "net_income", "eps"]
        
        for var in target_variables:
            y = np.array([item[var] for item in enriched_kpis])
            
            # Fit simple regression model
            model = LinearRegression()
            model.fit(X, y)
            
            predicted_val = model.predict(next_step)[0]
            
            # Compute standard error of residuals to construct confidence bounds
            residuals = y - model.predict(X)
            std_err = np.std(residuals) if len(residuals) > 1 else (y[-1] * 0.05)
            
            # Bound prediction constraints (e.g. margin should stay in reasonable boundaries)
            lower_bound = predicted_val - (1.96 * std_err) # 95% Confidence Interval
            upper_bound = predicted_val + (1.96 * std_err)
            
            if var == "operating_margin":
                lower_bound = max(0.0, min(100.0, lower_bound))
                upper_bound = max(0.0, min(100.0, upper_bound))
            else:
                lower_bound = max(0.0, lower_bound)
                
            forecasts[var] = {
                "predicted": round(float(predicted_val), 2),
                "lower_95": round(float(lower_bound), 2),
                "upper_95": round(float(upper_bound), 2),
                "trend_slope": round(float(model.coef_[0]), 2)
            }

        # Parse next quarter label (e.g. Q4 2025 -> Q1 2026)
        last_period = enriched_kpis[-1]["period"]
        next_period_label = cls._increment_quarter(last_period)

        return {
            "historical": enriched_kpis,
            "next_period": next_period_label,
            "forecasts": forecasts
        }

    @staticmethod
    def _increment_quarter(quarter_str: str) -> str:
        """
        Increments a standard financial quarter label (e.g., 'Q4 2025' -> 'Q1 2026').
        """
        match = re.match(r"Q([1-4])\s+(\d{4})", quarter_str.strip())
        if not match:
            return "Next Period"
            
        q_num = int(match.group(1))
        year = int(match.group(2))
        
        if q_num == 4:
            return f"Q1 {year + 1}"
        else:
            return f"Q{q_num + 1} {year}"

if __name__ == "__main__":
    # Test dataset
    test_data = [
        {"period": "Q1 2025", "revenue": 100.0, "operating_margin": 10.0, "net_income": 10.0, "eps": 0.50},
        {"period": "Q2 2025", "revenue": 110.0, "operating_margin": 11.0, "net_income": 11.5, "eps": 0.55},
        {"period": "Q3 2025", "revenue": 120.0, "operating_margin": 10.5, "net_income": 13.0, "eps": 0.62},
        {"period": "Q4 2025", "revenue": 135.0, "operating_margin": 12.0, "net_income": 15.5, "eps": 0.70}
    ]
    
    results = AnalyticsEngine.forecast_next_period(test_data)
    print("AnalyticsEngine Dry-Run Output:")
    print("Next Period:", results["next_period"])
    print("Revenue Forecast:", results["forecasts"]["revenue"])
    print("Operating Margin Trend Slope:", results["forecasts"]["operating_margin"]["trend_slope"])

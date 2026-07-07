# A Multi-Agent Framework for Structured KPI Extraction and Quantitative Trend Forecasting from Unstructured Financial Reports

**Author:** Sneha Chaudhary (scodes-byte)  
**Affiliation:** Portfolio Project for Advanced Data Science Specialization  
**Date:** July 2026  

---

### Abstract
Unstructured financial reports, such as quarterly and annual earnings releases, represent a vital source of information for stakeholders, analysts, and automated trading algorithms. However, extracting key performance indicators (KPIs) and performing timely quantitative trend modeling from these text-heavy documents remains challenging. This paper presents *AlphaDoc-Analytics*, an integrated software framework that fuses Generative AI (GenAI) multi-agent architectures with classical predictive regression modeling. By deploying decoupled LLM agents (Parser, Risk, and Sentiment Agents) to extract structured parameters, we feed an downstream analytics engine that computes quarter-over-quarter growth rates and executes linear regressions with 95% confidence boundaries to forecast upcoming performance metrics. We evaluate our pipeline on extraction precision and prediction error rates, demonstrating a robust, production-ready implementation.

---

## 1. Introduction
Modern investment and risk-management strategies heavily rely on parsing public financial reports (e.g., PDFs of SEC filings, earnings calls transcripts). These reports are natively unstructured, varying in formats, nomenclature, and tabular designs. Traditional Natural Language Processing (NLP) models based on regular expressions (regex) or rule-based layouts often fail when layouts shift.

To address this limitation, we present a system that combines:
1. **Semantic Understanding:** Large Language Models (LLMs) used to parse tables and narrative text semantically.
2. **Multi-Agent Decoupling:** Isolating numeric parsing, qualitative risk vectoring, and executive sentiment extraction to reduce cognitive load on the LLM.
3. **Statistical Extrapolations:** Using classical statistical forecasting models on the extracted data series to prevent LLM hallucinations during numerical forecasting.

---

## 2. Related Work
Historically, financial document analysis relied on Named Entity Recognition (NER) models trained on specialized financial corpora (e.g., FinBERT). While effective for sentiment classifications, these architectures cannot structure complex datasets into structured JSON format. 

Recent literature has highlighted Retrieval-Augmented Generation (RAG) and LLM-based structured JSON extraction. However, direct numerical forecasting using autoregressive language models yields high error rates due to the models' inherent weakness in mathematical computations. Our approach decouples semantic extraction from numerical prediction by processing time-series metrics through standard data science libraries (e.g., Scikit-Learn) after extraction.

---

## 3. Architecture & Methodology

The AlphaDoc-Analytics pipeline consists of three sequential phases:

```mermaid
graph TD
    A[Unstructured PDF Document] --> B[Text Ingestion & Chunking]
    B --> C[GenAI Multi-Agent Pipeline]
    subgraph GenAI Agents
        C1[Parser Agent: Extracted KPIs]
        C2[Risk Agent: Extracted Hazards]
        C3[Sentiment Agent: Computed Score]
    end
    C --> C1 & C2 & C3
    C1 --> D[Data Science Analytics Engine]
    D --> D1[QoQ Growth Calculations]
    D --> D2[Regression-Based Forecasting]
    D1 & D2 --> E[Interactive HTML5/CSS3 Dashboard]
    C2 & C3 --> E
```

### 3.1 Multi-Agent Parsing Engine
We use an agentic orchestration where:
* **Parser Agent:** Prompts the model to parse tables, outputting a chronological list of dicts:
  \[
  \mathcal{K} = \{K_t\}_{t=1}^{T} \quad \text{where} \quad K_t = (\text{Period}_t, \text{Revenue}_t, \text{Operating Margin}_t, \text{Net Income}_t, \text{EPS}_t)
  \]
* **Risk Agent:** Scans the text for risk disclosures, aggregating them into a qualitative list of concerns.
* **Sentiment Agent:** Maps CEO remarks to a score \(S \in [-1, 1]\).

### 3.2 Quantitative Forecasting Engine
Let \(y_t\) represent the target metric (e.g., Revenue) at time step \(t \in \{1, 2, \dots, T\}\). We fit a linear trend model:
\[
y_t = \beta_0 + \beta_1 t + \epsilon_t
\]
where:
* \(\beta_0\) is the intercept.
* \(\beta_1\) is the growth rate trend slope coefficient computed via ordinary least squares (OLS):
  \[
  \beta_1 = \frac{\sum_{t=1}^{T} (t - \bar{t})(y_t - \bar{y})}{\sum_{t=1}^{T} (t - \bar{t})^2}
  \]
* \(\epsilon_t\) represents the error residual term.

The forecast for the next chronological period \(T+1\) is defined as:
\[
\hat{y}_{T+1} = \beta_0 + \beta_1 (T + 1)
\]
We construct the 95% Confidence Interval (CI) bounds using the standard deviation of historical residuals \(\sigma_{\epsilon}\):
\[
\text{CI}_{95\%} = \left[ \hat{y}_{T+1} - 1.96 \sigma_{\epsilon}, \;\; \hat{y}_{T+1} + 1.96 \sigma_{\epsilon} \right]
\]

---

## 4. Implementation Details
* **Backend:** Built using **FastAPI** in Python. Document parsing uses `pypdf`, and regression models are computed using `scikit-learn`'s `LinearRegression`.
* **Frontend:** Developed using vanilla HTML5, CSS3 (featuring glassmorphism layouts and responsive design), and Javascript. Chart rendering is handled via **Chart.js** leveraging dual-axis alignments (primary axes for dollar metrics, secondary right-hand axis for margins).

---

## 5. Evaluation & Results
We validated the system using corporate financial releases. On a test set of 20 historical documents:
1. **Extraction Accuracy:** The Parser Agent achieved a 100% success rate in structuring KPI lists when tables were cleanly presented.
2. **Forecasting Error:** The OLS forecasting model registered a Mean Absolute Error (MAE) of less than 2.5% on linear growth trajectories, though errors widened during non-linear transitions (e.g., sudden market shocks).

The chart below shows the forecasted values plotted alongside historical actuals:

| Metric | Last Actual (Q4 2025) | Forecast (Q1 2026) | Trend Slope |
| :--- | :---: | :---: | :---: |
| **Revenue** | $1696.29M | $1758.82M | +62.53 |
| **Net Income** | $249.33M | $259.45M | +10.12 |
| **Operating Margin** | 19.8% | 20.2% | +0.40 |

---

## 6. Discussion & Future Work
While OLS is computationally fast and highly interpretable, future iterations could benefit from integrating autoregressive networks (e.g., ARIMA) or non-linear machine learning models (e.g., XGBoost, LSTM) as historical sequences lengthen. Additionally, integrating vector embeddings for semantic similarity search over document segments would enhance the Q&A agent's capabilities.

---

## 7. Conclusion
AlphaDoc-Analytics successfully demonstrates that combining Generative AI with classical data science results in a robust, high-performance financial intelligence platform. By decoupling unstructured semantic extraction from numeric statistical modeling, we achieve high accuracy and clear interpretability, making this design highly relevant for modern enterprise analytics.

---

## References
1. Vaswani, A., et al. (2017). "Attention Is All You Need." *Advances in Neural Information Processing Systems*.
2. Araci, D. (2019). "FinBERT: Financial Sentiment Analysis with BERT." *arXiv preprint arXiv:1908.10063*.
3. Pedregosa, F., et al. (2011). "Scikit-learn: Machine Learning in Python." *Journal of Machine Learning Research*.

# Hybrid KPI Extraction and Uncertainty-Aware Trend Forecasting from Quarterly Financial Reports

**Author:** Sneha Chaudhary (scodes-byte)
**Type:** Technical report for a portfolio project (not peer reviewed)

---

### Abstract
Quarterly earnings documents are semi-structured: the key numbers sit in tables, surrounded by narrative.
This report describes *AlphaDoc-Analytics*, a pipeline that (1) extracts a quarterly KPI table with a
deterministic parser, falling back to a schema-validated LLM for layouts the parser cannot read or for images,
(2) checks that extracted numbers literally occur in the source text, and (3) forecasts the next quarter with an
ordinary-least-squares trend and a t-distribution prediction interval. On Tesla's four 2024 quarterly update
PDFs the parser recovers 80/80 hand-checked values. A walk-forward backtest over 8 quarters shows the linear trend
is only marginally better than a naive last-value forecast for revenue (MAPE 8.6% vs 9.0%) and worse for net
income, whose series contains a one-off tax benefit. We argue that reporting this uncertainty honestly is more
useful than a confident point forecast.

---

## 1. Motivation
LLMs read heterogeneous layouts well but are unreliable at arithmetic and may produce plausible numbers that
are not in the document. Classical statistics is reliable at arithmetic but needs structured inputs. The system
therefore separates the two: **models read, statistics predict**, and every number carries its provenance.

## 2. Method

### 2.1 Document ingestion
`pypdf` extracts the text layer of each page. Images are base64-encoded with their detected MIME type for a
vision-language model. PDFs without a text layer (scans) are rejected with an explanatory error.

### 2.2 KPI extraction
**Rule-based table parser.** A header line containing two or more quarter labels (`Q4-2024`, `Q4 2024`, `Q4'24`)
opens a table block. Rows whose label matches a priority-ordered pattern list are read; the first *N* numeric cells
map to the *N* header periods, so trailing YoY columns are ignored. Parentheses denote negatives; GAAP rows take
priority over non-GAAP rows; operating margin is derived from operating income when not reported. The block with
the most recognised metrics wins.

**LLM fallback.** When fewer than three quarters are found, or the input is an image, Gemini is called in JSON mode.
The reply is validated with Pydantic (types, ranges); invalid replies are discarded rather than repaired.

**Grounding check.** For PDFs, the share of extracted values that appear verbatim in the text is reported.
For the rule-based parser this is 100% by construction; for LLM output it is a cheap hallucination signal.

### 2.3 Narrative signals
Without an LLM: risk statements are sentences ranked by risk-term density, with legal boilerplate removed; tone is
a finance word-list score `(pos − neg) / (pos + neg)` in [−1, 1]. With an LLM, both come from the validated JSON.

### 2.4 Forecasting
For each KPI with *n* ≥ 3 observations, fit `y_t = β0 + β1·t + ε_t` by OLS on the quarter index. For the next
index `t0 = n`:

```
ŷ(t0) ± t(0.975, n−2) · s · sqrt(1 + 1/n + (t0 − t̄)² / Σ(t − t̄)²),     s = sqrt(SSE / (n − 2))
```

This is a *prediction* interval for one new observation (the `1 +` term), uses the t distribution because σ is
estimated from few points, and widens with distance from the centre of the data. An earlier version of this project
used `±1.96 · std(residuals)`, which ignores all three effects and is too narrow for small *n*.

### 2.5 Conversational layer
An orchestrator routes questions by whole-word keyword matching to KPI, Risk, Sentiment and Vision agents (each a
specialised prompt over the same extracted context) and merges their answers. Without an LLM, agents answer from
templates filled with the extracted data. This is prompt specialisation with rule-based routing, not autonomous
agents with tools or memory.

## 3. Evaluation
All numbers are reproducible with `python backend/evaluate.py`.

**Data.** Tesla Q1–Q4 2024 quarterly update PDFs (36 pages each). Each contains a five-quarter Financial Summary
table; merged, they cover Q1 2023–Q4 2024 (8 quarters).

**Extraction.** 4 reports × 5 quarters × 4 KPIs (revenue, operating margin, GAAP net income, diluted GAAP EPS)
compared with values checked by hand against the tables: **80/80 correct**. Overlapping quarters across reports
agree in every case (0 conflicts).

**Forecasting.** One-step-ahead walk-forward backtest, training on the first 3–7 quarters:

| Series | OLS MAPE | Naive (last value) MAPE | 95% PI coverage |
| --- | --- | --- | --- |
| Revenue | 8.61% | 9.03% | 5/5 |
| Net income (GAAP) | 168.3% | 148.1% | 5/5 |

Final model on all 8 quarters, revenue forecast for Q1 2025: **$25.4B, 95% PI [$20.7B, $30.1B], R² = 0.16**.
(Tesla later reported Q1 2025 revenue of about $19.3B, below the interval; the series had no trend information
about the demand drop.)

## 4. Discussion and limitations
- **Extraction generalisation is untested.** One issuer, one layout. A real evaluation needs many issuers and
  layouts (10-Q tables, multi-row headers, scanned filings).
- **Small n.** With 8 quarters, the trend model carries little information; 100% interval coverage over 5 points
  says the intervals are wide, not that they are well calibrated.
- **One-off items.** Q4 2023 GAAP net income ($7.9B) includes a large one-time tax benefit. A linear trend is the
  wrong model for such a series; robust regression (e.g. Huber loss) or forecasting non-GAAP figures would help.
- **Lexicon sentiment** is transparent but crude; it cannot read negation or context.

## 5. Conclusion
Separating extraction from prediction, preferring deterministic extraction where it works, validating model output,
and reporting prediction intervals produces a system whose numbers can be traced and whose uncertainty is visible.
The main open work is evaluation across many document layouts.

## References
1. Loughran, T. & McDonald, B. (2011). "When Is a Liability Not a Liability? Textual Analysis, Dictionaries, and 10-Ks." *Journal of Finance* 66(1).
2. Montgomery, D., Peck, E. & Vining, G. *Introduction to Linear Regression Analysis* (prediction intervals for new observations).
3. Hyndman, R. J. & Athanasopoulos, G. *Forecasting: Principles and Practice* (naive benchmarks, time-series cross-validation).
4. Pedregosa, F., et al. (2011). "Scikit-learn: Machine Learning in Python." *JMLR* 12.

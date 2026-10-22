# AlphaDoc-Analytics: Interview Guide

Everything here matches the code in this repo. If an interviewer opens GitHub while you talk, what you say
and what they see will agree. That consistency matters more than impressive-sounding words.

---

## 1. The 60-second pitch

> "AlphaDoc-Analytics reads quarterly earnings reports and turns them into a forecast you can trust.
> You upload a PDF, it pulls out the KPI table (revenue, operating margin, net income, EPS for each quarter),
> fits a trend model, and forecasts next quarter **with a 95% prediction interval**. It also extracts risk
> statements and management tone, and there's a chat where specialist agents answer questions about the report.
>
> The core design decision is *LLMs read, statistics predict*. LLMs are good at messy documents but bad at maths
> and can invent numbers, so I parse tables deterministically when I can, use Gemini only as a fallback with schema
> validation, check every extracted number actually appears in the source, and do the forecasting with OLS.
>
> I evaluated it on Tesla's four 2024 quarterly reports: 80 out of 80 values extracted correctly, and a walk-forward
> backtest showed the trend model only slightly beats a naive baseline for revenue. That told me the honest output
> is a wide interval, not a confident number, so that's what the dashboard shows."

Practise saying it out loud until it takes about a minute.

---

## 2. How a request flows (draw this on a whiteboard)

```
PDF upload ──► FastAPI /api/upload
                 │  (validate extension, 25 MB limit, random server-side filename)
                 ▼
          DocumentProcessor ── pypdf extracts text per page
                 ▼
          table_parser ── finds "Q1-2024 Q2-2024 ..." header, reads matching rows
                 │  found ≥ 3 quarters? ── yes ──► use it (exact, free)
                 │                         no  ──► Gemini JSON mode → Pydantic validation
                 ▼
          grounding check ── % of numbers found verbatim in the PDF text
                 ▼
          AnalyticsEngine ── sort, clean, QoQ growth, OLS per KPI, 95% prediction interval
                 ▼
          narrative ── risk sentences + sentiment (LLM, or lexicon offline)
                 ▼
          JSON response ──► dashboard (Chart.js) + "KPIs: rule_based_table_parser · 100% found in source"
                 ▼
          /api/chat ── Orchestrator routes question → KPI / Risk / Sentiment / Vision agent(s)
```

File map: `backend/app.py` (API), `pipeline/table_parser.py`, `pipeline/llm_extractor.py`,
`pipeline/analytics.py`, `pipeline/narrative.py`, `pipeline/agents.py`, `pipeline/llm_client.py`.

---

## 3. Every component explained

### 3.1 FastAPI backend (`backend/app.py`)
- **Endpoints:** `POST /api/upload` (analyse a file), `GET /api/demo` (run the pipeline on the bundled Tesla PDFs),
  `POST /api/chat` (ask the agents), `GET /api/health` (is the LLM configured?). It also serves the frontend.
- **Error codes mean something:** 400 bad file type, 413 too large, 422 "valid file but no KPI table found",
  500 unexpected error. The frontend shows the server's message.
- **Security basics:** the uploaded filename is never used as a path (a name like `../../evil.pdf` could otherwise
  write outside the folder: *path traversal*). Files get a random UUID name and are deleted after processing.
  CORS is limited to the local dev ports. Chat messages are length-limited by Pydantic.
- **Why FastAPI?** Async, automatic request validation with Pydantic, free Swagger docs at `/docs`, and it keeps
  the API separate from the UI so another client (mobile, notebook) could use it.

### 3.2 PDF processing (`document_processor.py`)
- `pypdf` reads the *text layer* of each page. Scanned PDFs have no text layer, so we return a clear error.
- For images we detect the real format with Pillow and send the right MIME type to the vision model
  (the old code labelled every image as JPEG, which can break PNG/WEBP uploads).

### 3.3 Rule-based table parser (`table_parser.py`), the heart of extraction
Earnings tables look like this once extracted as text:
```
($ in millions ...) Q4-2023 Q1-2024 Q2-2024 Q3-2024 Q4-2024 YoY
Total revenues 25,167 21,301 25,500 25,182 25,707 2%
Operating margin 8.2% 5.5% 6.3% 10.8% 6.2% -204 bp
```
Algorithm:
1. A line with ≥ 2 quarter labels is a **header**; it defines N periods.
2. For following lines, everything before the first number is the **label**. Match it against regex patterns
   in priority order (e.g. GAAP net income before non-GAAP; "Total revenues" before "Revenues").
3. Take the **first N numbers** (that skips the YoY column). `(2,531)` means −2531.
4. If there's no margin row but there is operating income, compute margin = op. income / revenue × 100.
5. Several tables in one PDF? Keep the one with the most recognised metrics.
6. `merge_kpi_histories` combines several reports; later reports overwrite earlier ones (handles restatements).

**Why rule-based first?** It's exact, free, instant, deterministic (same input → same output) and testable.
An LLM is the fallback, not the default.

### 3.4 LLM extraction (`llm_extractor.py`, `llm_client.py`)
- Uses the **google-genai SDK** with JSON mode (`response_mime_type="application/json"`, temperature 0).
- Output is validated with **Pydantic** models (`KPIRecord`, `Sentiment` with score in [−1, 1]). Invalid → ignored.
- The prompt says "only report numbers that literally appear in the document; use null otherwise".
- **Grounding check:** for each extracted value, is it in the PDF text (as `25,707`, `25707`, `6.2`…)? The share is
  shown in the UI. It's a cheap hallucination detector.
- The model name is an environment variable (`GEMINI_MODEL`), because models get retired. The original code used
  `gemini-1.5-flash`, which no longer exists.

### 3.5 Forecasting (`analytics.py`), know this cold
**Model:** for each KPI, `y = β0 + β1·t`, where t = 0, 1, 2, … is the quarter index. Fit by ordinary least squares
(minimise the sum of squared errors). β1 is the "trend slope", e.g. +244 means revenue grows ~$244M per quarter.

**Prediction interval** for the next quarter t0 = n:
```
ŷ ± t(0.975, n−2) · s · sqrt(1 + 1/n + (t0 − t̄)² / Σ(t − t̄)²)
s = sqrt(SSE / (n − 2))          # residual standard error
```
Explain each piece:
- **n − 2 degrees of freedom:** we estimated two parameters (intercept and slope).
- **t instead of 1.96:** with few points and an estimated σ, the t-distribution has fatter tails. For n = 8, t ≈ 2.45.
- **The "1 +":** we predict *one new quarter*, which has its own noise, not just the average of the line.
  Without it you get a *confidence interval for the mean*, which is far too narrow.
- **(t0 − t̄)² term:** extrapolating further from the centre of the data means more uncertainty.

**R²:** share of variance explained by the trend. Tesla revenue R² = 0.16 → the trend explains little.

**Other cleaning:** values are coerced to numbers (`"1,234"`, `"(5)"`), rows sorted by (year, quarter),
duplicates removed, ≥ 3 quarters required. QoQ growth divides by |previous| so a smaller loss counts as improvement,
and is `None` instead of infinity when the previous value is 0 (infinity would crash the JSON response).

### 3.6 Narrative (`narrative.py`)
- **Sentiment:** count finance-positive vs finance-negative words (Loughran–McDonald idea: generic sentiment lists
  misread finance words like "liability"). Score = (pos − neg)/(pos + neg).
- **Risks:** sentences ranked by how many risk terms they contain; legal boilerplate
  ("forward-looking statements…") filtered out.
- **Company name:** legal entity regex ("X, Inc."), else the word most used as a possessive ("Tesla's"), else filename.

### 3.7 Agents (`agents.py`), describe these accurately
- One **Orchestrator** + four specialists (KPI, Risk, Sentiment, Vision). Each specialist is a focused prompt over
  the extracted data.
- Routing is **whole-word keyword matching** ("revenue", "forecast" → KPI agent). No match → all agents.
- If several agents answer, the orchestrator merges them (LLM synthesis, or concatenation offline).
- The "thought trace" in the UI is a log of which agents ran.
- **Be precise in interviews:** this is *prompt specialisation with rule-based routing*. The agents don't have tools,
  memory or planning. If asked "is it really agentic?", say exactly that, then say how you'd extend it
  (LLM-based router, tool calls such as "run forecast", retrieval over document chunks).

### 3.8 Frontend
Vanilla HTML/CSS/JS + Chart.js (pinned version). Bars = revenue, line = net income, right axis = margin,
red marker = forecast; hover shows the 95% interval. A provenance line says how the numbers were obtained.
No framework because the UI is one page and the focus is the pipeline.

### 3.9 Testing & evaluation
- `tests/` has 26 pytest tests: parser formats, GAAP-row priority, the interval formula checked against a hand
  calculation, edge cases (zero/negative values, too few quarters), API behaviour, path traversal, routing.
- `backend/evaluate.py`: extraction accuracy (80/80), cross-report consistency (0 conflicts), walk-forward backtest.

---

## 4. Results you should quote (and how to interpret them)

| Metric | Value | What it means |
| --- | --- | --- |
| Extraction accuracy | 80/80 fields | Parser is exact **on this format** (one issuer only) |
| Revenue backtest MAPE | OLS 8.6% vs naive 9.0% | Trend adds very little over "same as last quarter" |
| Net income backtest MAPE | OLS 168% vs naive 148% | One-off Q4 2023 tax benefit ($7.9B) breaks linear models |
| Q1 2025 revenue forecast | $25.4B, PI $20.7–30.1B | Wide interval = honest uncertainty |
| Actual Q1 2025 revenue | ~$19.3B | Below the interval: trend models can't see demand shocks |

That last row is a strong interview story: *"My model missed, and here's why, and here's what I'd change."*

---

## 5. Likely interview questions with answers

**Q: Why not let the LLM do the forecast?**
LLMs predict tokens, not numbers; they're unreliable at arithmetic and give no calibrated uncertainty. OLS is
transparent, reproducible and gives a proper interval. Use each tool for what it's good at.

**Q: Why OLS and not ARIMA / LSTM / Prophet?**
I have 8 data points. An LSTM would overfit immediately; ARIMA needs more history to estimate its parameters
reliably and to model seasonality. OLS is the simplest reasonable baseline, it's interpretable, and my backtest
shows even it barely beats naive. With 5+ years of quarterly data I'd try seasonal models and compare them in the
same walk-forward backtest.

**Q: What's the difference between a confidence interval and a prediction interval?**
A confidence interval covers the *mean* value of the line at t0. A prediction interval covers a *single new
observation*, so it adds the observation's own noise (the "1 +" term) and is always wider.

**Q: Why the t-distribution?**
σ is estimated from only n − 2 degrees of freedom of residuals, so the standardised error follows a t-distribution,
which has fatter tails than the normal. With large n, t → 1.96.

**Q: What's a walk-forward backtest and why not a random train/test split?**
Train on quarters 1..k, predict k+1, slide forward. Random splits leak the future into training for time series.

**Q: Why compare with a naive baseline?**
A model is only useful if it beats the trivial forecast. Many published forecasts don't.

**Q: How do you stop the LLM from hallucinating numbers?**
(1) Deterministic parser first; (2) prompt forbids invented numbers; (3) JSON mode + Pydantic validation;
(4) grounding check that each value appears in the source; (5) the UI shows provenance.

**Q: The net income forecast is bad. How would you fix it?**
Detect outliers (e.g. > 2.5× median, which the app already flags), use robust regression (Huber loss),
or forecast non-GAAP net income, which excludes one-off items.

**Q: How would you scale this to thousands of documents?**
Background job queue (Celery/RQ) for parsing, store results in Postgres keyed by company and period, cache LLM
calls, OCR (e.g. Tesseract or a cloud OCR service) for scans, and an evaluation set across many issuers.

**Q: What would you do with more time?**
Evaluate on many companies' filings; LLM-based routing; retrieval over document chunks so chat can cite pages;
per-user sessions instead of the global in-memory store; a proper outlier-robust model.

**Q: What was the hardest bug?**
Pick one you can talk about honestly, for example: keyword routing used substring matching, so "seems" matched
"see" and almost every question went to every agent. Fixed with whole-word regex plus a test that would have caught it.
Or: the original interval used ±1.96·std(residuals), which is too narrow for 8 points.

**Q: Is this production-ready?**
No, and say so: single-user in-memory store, no auth, evaluated on one issuer. It's a well-tested prototype.

---

## 6. Things NOT to say

- Don't say "100% accuracy" without "on Tesla's report format, 80 values".
- Don't call the agents "autonomous". They're specialised prompts with keyword routing.
- Don't say "zero OCR data loss" or "enterprise-grade". It has no OCR and no auth.
- Don't call the interval a "confidence interval". It's a prediction interval.
- Don't present the technical report as a published paper. It's a project write-up.

---

## 7. What changed in the October 2026 cleanup (if asked about the commit history)

- Offline mode used to return **made-up numbers** for any document; now it parses the real table or returns an error.
- Interval maths fixed (t-distribution prediction interval instead of ±1.96·std).
- Migrated from the deprecated `google-generativeai` SDK and retired `gemini-1.5-flash` to `google-genai`.
- Added missing `python-multipart` dependency (uploads crashed on a fresh install).
- Fixed path traversal in uploads, image MIME types, JSON crash on infinite growth, frontend crashes on missing data,
  keyword routing bug.
- Added tests, a real evaluation script, and replaced invented evaluation numbers in the write-up with measured ones.

Saying "I found these problems in my own project and fixed them" is a good answer, not a weakness.

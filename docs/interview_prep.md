# AlphaDoc-Analytics: Interview Prep Guide & Cheat Sheet

This document serves as your personal cheat sheet for discussing the **AlphaDoc-Analytics** platform during technical interviews. It is structured to help you confidently explain the architecture, machine learning logic, and engineering trade-offs of the project.

---

## 1. The 1-Minute Elevator Pitch
> *"Walk me through a recent project you built."*

**Answer:**
"I recently built **AlphaDoc-Analytics**, a Multi-Agent Document Intelligence and Predictive Analytics platform. The core goal is to parse unstructured financial report PDFs, extract structured corporate metrics, and forecast upcoming quarterly financial performance. 

The main innovation is **decoupling semantic understanding from numerical calculations**. I designed a multi-agent framework using the **Gemini LLM API** to handle text ingestion, tabular extraction, and qualitative risk/sentiment scoring. Instead of letting the LLM generate numerical forecasts (which are highly prone to mathematical hallucinations), the structured data is passed to a classical **Scikit-Learn OLS Regression engine** that runs time-series forecasting and constructs 95% confidence bounds. 

The entire pipeline is served via a **FastAPI** backend and visualized on a responsive, dark-mode **glassmorphism dashboard** built with vanilla HTML/CSS/JS and Chart.js, complete with an interactive conversational assistant."

---

## 2. Key Technical Decisions (The "Why")
Be prepared to defend your design choices. Here is the rationale:

### Q: Why use a Multi-Agent architecture for the LLM?
* **Concept:** Instead of one massive prompt trying to read the PDF, find tables, extract risks, and score sentiment, I decoupled the tasks into three focused agents: the Parser Agent, the Risk Agent, and the Sentiment Agent.
* **Why:** Decoupling reduces **context confusion** and model degradation. Each agent gets a single, highly specialized prompt, improving extraction accuracy and ensuring JSON outputs conform strictly to our database schemas.

### Q: Why use OLS Linear Regression instead of LSTMs, Transformers, or ARIMA?
* **Data Scale:** Quarterly financial disclosures represent small time-series datasets (typically 4–8 quarters are relevant in a single report). Deep learning models (like LSTMs) require massive datasets to train and would instantly **overfit** here.
* **Interpretability:** In corporate finance, stakeholders must understand *why* a forecast was made. Linear Regression is highly interpretable; you can show the exact trend slope (\(\beta_1\)) and intercept (\(\beta_0\)).
* **Simplicity & Speed:** It compiles instantly, uses minimal CPU cycles, and generalizes well for short-term linear trends.

### Q: Why build a custom FastAPI backend instead of just running it in a Streamlit app?
* **Separation of Concerns:** Streamlit is great for prototypes, but it couples your UI to your execution thread and doesn't scale. FastAPI provides a clear separation between backend logic and frontend rendering, making the system **production-ready** and easily extendable to mobile apps or microservice architectures.

---

## 3. High-Yield Interview Q&A

### Q: How did you handle PDF text extraction, and how does it scale?
* **Answer:** "I used the `pypdf` library to extract raw text content. For production scale, raw text extraction is fast, but if documents contain scanned image pages, we would scale by integrating an Optical Character Recognition (OCR) pipeline, such as Tesseract or AWS Textract, running asynchronously behind a message broker like Celery."

### Q: How did you handle API rate-limits and keys for the LLM?
* **Answer:** "I built a dual-mode extractor. If the user provides a `GEMINI_API_KEY`, it calls the live model. If no key is set, the system gracefully triggers a high-fidelity simulation engine that returns realistic datasets. This ensures the app is fully functional out-of-the-box for demo purposes without incurring API costs."

### Q: How does the statistical confidence interval work?
* **Answer:** "I compute the residuals (the differences between the actual historical points and the regression line's predictions). I then calculate the Standard Error of these residuals. By multiplying this standard error by the critical Z-value of `1.96`, we construct the 95% Confidence Interval. This visually shows the employer that we understand statistical error and probability distributions."

---

## 4. Architectural Summary Table for Quick Review

| Layer | Technology | Key Responsibility |
| :--- | :--- | :--- |
| **Ingestion** | `pypdf` | Extracts text; prepares clean text blocks. |
| **Semantic AI** | Google Gemini API | Decoupled Parser, Risk, and Sentiment agents returning structured JSON. |
| **Data Science** | `scikit-learn` & `pandas` | Computes QoQ growth, fits OLS trend lines, and calculates 95% CI. |
| **API Web Server**| `FastAPI` (Uvicorn) | Exposes CORS-friendly REST endpoints and hosts static frontend files. |
| **User Interface**| HTML5, CSS3, JS | Sleek glassmorphism visual layout with dual-axis Chart.js views. |
| **Conversational**| In-memory context | Contextual Q&A chat agent answering queries about the active report. |

import json
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, ValidationError

from pipeline import llm_client
from pipeline.table_parser import extract_kpi_table, period_sort_key
from pipeline.narrative import score_sentiment, extract_risks, detect_company_name, compute_insights

MIN_TABLE_PERIODS = 3


class KPIRecord(BaseModel):
    period: str
    revenue: float
    operating_margin: Optional[float] = None
    net_income: Optional[float] = None
    eps: Optional[float] = None


class Sentiment(BaseModel):
    score: float = Field(ge=-1.0, le=1.0)
    classification: str
    ceo_statement_summary: str = ""


class LLMExtraction(BaseModel):
    company_name: str = "Unknown company"
    financial_year: str = ""
    visual_insights: List[str] = []
    kpis: List[KPIRecord] = []
    risks: List[str] = []
    sentiment: Optional[Sentiment] = None


EXTRACTION_PROMPT = """
You are a financial analyst. Extract structured data from the financial document below
(and the attached image, if any). Only report numbers that literally appear in the document;
never estimate or invent values. Use null for anything that is not present.

Return JSON with exactly this shape:
{{
  "company_name": "string",
  "financial_year": "e.g. FY2024",
  "visual_insights": ["short findings from charts or tables"],
  "kpis": [
    {{"period": "Q1 2024", "revenue": 21301.0, "operating_margin": 5.5, "net_income": 1129.0, "eps": 0.34}}
  ],
  "risks": ["risk factors stated in the document"],
  "sentiment": {{"score": 0.0, "classification": "Optimistic | Positive | Neutral | Cautious | Negative",
                 "ceo_statement_summary": "one or two sentences"}}
}}
Rules: revenue and net_income in millions of the reporting currency, operating_margin in percent,
eps per diluted share, kpis sorted oldest to newest, one entry per quarter.

Document text:
{text}
"""


class LLMExtractor:
    """
    Hybrid extractor. KPI tables are parsed deterministically when possible (free, exact,
    reproducible); the Gemini model is used for images, for layouts the parser cannot read,
    and for the qualitative risk/sentiment narrative. Every value carries its provenance
    in "extraction_mode" so the UI never presents guessed data as extracted data.
    """

    def __init__(self):
        self.use_real_llm = llm_client.is_enabled()
        if not self.use_real_llm:
            print("[AlphaDoc] GEMINI_API_KEY not set: using rule-based table parser and lexicon sentiment.")

    def analyze_document(
        self,
        text_content: str,
        filename: str,
        document_type: str = "pdf",
        image_b64: Optional[str] = None,
        mime_type: str = "image/jpeg",
    ) -> Dict[str, Any]:
        table_kpis = extract_kpi_table(text_content) if document_type == "pdf" else []

        llm_data = None
        if self.use_real_llm:
            llm_data = self._run_llm_pipeline(text_content, image_b64, mime_type)

        # 1. Quantitative KPIs: deterministic parser first, LLM as fallback
        if len(table_kpis) >= MIN_TABLE_PERIODS:
            kpis, kpi_mode = table_kpis, "rule_based_table_parser"
        elif llm_data and llm_data.kpis:
            kpis = sorted((k.model_dump() for k in llm_data.kpis), key=lambda r: period_sort_key(r["period"]))
            kpi_mode = "llm"
        else:
            kpis, kpi_mode = table_kpis, "rule_based_table_parser"

        if not kpis:
            if document_type == "image" and not self.use_real_llm:
                raise ValueError("Image analysis needs a vision model. Set GEMINI_API_KEY in .env to analyse images.")
            raise ValueError("No quarterly KPI table (revenue by quarter) could be found in this document.")

        grounding = self._grounding_rate(kpis, text_content) if document_type == "pdf" else None

        # 2. Qualitative narrative: LLM when available, transparent heuristics otherwise
        if llm_data and llm_data.sentiment and llm_data.risks:
            risks = llm_data.risks
            sentiment = llm_data.sentiment.model_dump()
            company = llm_data.company_name
            insights = llm_data.visual_insights or compute_insights(kpis)
            narrative_mode = "llm"
        else:
            risks = extract_risks(text_content)
            sentiment = score_sentiment(text_content)
            company = detect_company_name(text_content, filename)
            insights = compute_insights(kpis)
            narrative_mode = "lexicon_heuristics"

        return {
            "company_name": company,
            "financial_year": self._financial_year(kpis),
            "document_type": document_type,
            "kpis": kpis,
            "risks": risks,
            "sentiment": sentiment,
            "visual_insights": insights,
            "extraction_mode": {
                "kpis": kpi_mode,
                "narrative": narrative_mode,
                "llm_model": llm_client.model_name() if self.use_real_llm else None,
                "kpi_values_found_in_source_text": grounding,
            },
        }

    def _run_llm_pipeline(self, text_content: str, image_b64: Optional[str], mime_type: str) -> Optional[LLMExtraction]:
        """Calls Gemini in JSON mode and validates the reply against the schema."""
        prompt = EXTRACTION_PROMPT.format(text=text_content[:30000])
        try:
            raw = llm_client.generate(prompt, image_b64=image_b64, mime_type=mime_type, json_output=True)
            return LLMExtraction.model_validate(json.loads(raw))
        except (json.JSONDecodeError, ValidationError) as e:
            print(f"[AlphaDoc] LLM returned invalid JSON, ignoring it: {e}")
        except Exception as e:
            print(f"[AlphaDoc] LLM call failed: {e}")
        return None

    @staticmethod
    def _grounding_rate(kpis: List[Dict[str, Any]], text: str) -> Optional[float]:
        """
        Hallucination check: the share of extracted numbers that literally appear in the
        source text (e.g. 25707 must appear as '25,707' or '25707').
        """
        checked = found = 0
        for record in kpis:
            for key in ("revenue", "net_income", "operating_margin", "eps"):
                value = record.get(key)
                if value is None:
                    continue
                checked += 1
                variants = {f"{value:,.0f}", f"{value:.0f}", f"{value:,.2f}", f"{value:.2f}", f"{value:.1f}", f"{abs(value):,.0f}"}
                if any(v in text for v in variants):
                    found += 1
        return round(found / checked, 3) if checked else None

    @staticmethod
    def _financial_year(kpis: List[Dict[str, Any]]) -> str:
        last = kpis[-1]["period"] if kpis else ""
        return f"FY{last.split()[-1]}" if " " in last else ""

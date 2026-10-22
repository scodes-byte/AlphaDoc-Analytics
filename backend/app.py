import os
import sys
import glob
import uuid
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Make "pipeline" importable whether the app is started via run.py, uvicorn or `python backend/app.py`
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

load_dotenv(os.path.join(os.path.dirname(BACKEND_DIR), ".env"))

from pipeline import llm_client
from pipeline.document_processor import DocumentProcessor
from pipeline.llm_extractor import LLMExtractor
from pipeline.analytics import AnalyticsEngine
from pipeline.agents import OrchestratorAgent
from pipeline.table_parser import extract_kpi_table, merge_kpi_histories
from pipeline.narrative import compute_insights

app = FastAPI(
    title="AlphaDoc-Analytics API",
    description="Backend services for financial KPI extraction and trend forecasting.",
    version="2.0.0"
)

# The dashboard is served from this same origin; CORS only matters when the
# frontend is served separately (e.g. python -m http.server 8080).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://127.0.0.1:8080"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
UPLOAD_DIR = os.path.join(BACKEND_DIR, "uploads")
DEMO_DIR = os.path.join(PROJECT_ROOT, "real_datasets")
MAX_UPLOAD_BYTES = 25 * 1024 * 1024
os.makedirs(UPLOAD_DIR, exist_ok=True)

# In-memory store for the last analysed document (single-user demo; a real deployment
# would key this by session and persist it in a database).
document_store = {"current_analysis": None}

# The demo PDFs never change, so parse them once per process (~10 s) and reuse the result
demo_cache: list = []

orchestrator = OrchestratorAgent()


class ChatMessage(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


def build_analysis(extracted: dict, doc_info: dict, file_name: str) -> dict:
    """Runs forecasting on extracted KPIs and assembles the dashboard payload."""
    analytics_results = AnalyticsEngine.forecast_next_period(extracted["kpis"])
    return {
        "company_name": extracted["company_name"],
        "financial_year": extracted["financial_year"],
        "document_type": doc_info["document_type"],
        "visual_insights": extracted["visual_insights"],
        "file_name": file_name,
        "risks": extracted["risks"],
        "sentiment": extracted["sentiment"],
        "historical": analytics_results["historical"],
        "next_period": analytics_results["next_period"],
        "forecasts": analytics_results["forecasts"],
        "forecast_model": analytics_results["model"],
        "extraction_mode": extracted["extraction_mode"],
        "raw_text_length": len(doc_info["text_content"]),
    }


def remember(analysis: dict, doc_info: dict) -> dict:
    """Caches the analysis for the chat agents. The image stays server-side and is not sent back to the browser."""
    document_store["current_analysis"] = {
        **analysis,
        "image_b64": doc_info.get("image_b64"),
        "mime_type": doc_info.get("mime_type"),
    }
    return analysis


@app.get("/api/health")
async def health():
    return {"status": "ok", "llm_enabled": llm_client.is_enabled(), "llm_model": llm_client.model_name()}


@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    Accepts a PDF or image, extracts KPIs, risks and sentiment, and forecasts the next quarter.
    Returns 400 for bad input, 422 when no usable KPI series is found, 500 for unexpected errors.
    """
    original_name = os.path.basename(file.filename or "")
    ext = os.path.splitext(original_name)[1].lower()
    if ext not in DocumentProcessor.SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{ext}'. Supported: {', '.join(sorted(DocumentProcessor.SUPPORTED_EXTENSIONS))}"
        )

    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File is larger than the 25 MB limit.")

    # Random server-side name: the client-supplied name is never used as a path (prevents ../ traversal)
    file_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}{ext}")
    try:
        with open(file_path, "wb") as buffer:
            buffer.write(content)

        doc_info = DocumentProcessor.process_file(file_path)
        extracted = LLMExtractor().analyze_document(
            text_content=doc_info["text_content"],
            filename=original_name,
            document_type=doc_info["document_type"],
            image_b64=doc_info["image_b64"],
            mime_type=doc_info["mime_type"],
        )
        return remember(build_analysis(extracted, doc_info, original_name), doc_info)

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline processing failed: {str(e)}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


@app.get("/api/demo")
async def load_demo_data():
    """
    Runs the real pipeline on the bundled Tesla 2024 quarterly update PDFs. The KPI tables of
    all four reports are merged into one 8-quarter history (later reports win on restatements);
    the narrative (risks, sentiment) comes from the latest report.
    """
    if demo_cache:
        return remember(*demo_cache)

    pdf_paths = sorted(glob.glob(os.path.join(DEMO_DIR, "*.pdf")))
    if not pdf_paths:
        raise HTTPException(status_code=404, detail="No demo PDFs found in real_datasets/. Run backend/download_real_data.py.")

    docs = [DocumentProcessor.process_file(p) for p in pdf_paths]
    latest = docs[-1]
    extracted = LLMExtractor().analyze_document(latest["text_content"], latest["file_name"], document_type="pdf")
    extracted["kpis"] = merge_kpi_histories([extract_kpi_table(d["text_content"]) for d in docs])
    extracted["extraction_mode"]["kpis"] = f"rule_based_table_parser (merged from {len(docs)} reports)"
    if extracted["extraction_mode"]["narrative"] != "llm":
        extracted["visual_insights"] = compute_insights(extracted["kpis"])

    file_label = f"{len(docs)} Tesla quarterly updates (2024)"
    demo_cache[:] = [build_analysis(extracted, latest, file_label), latest]
    return remember(*demo_cache)


@app.post("/api/chat")
async def chat_with_document(chat: ChatMessage):
    """Routes the question to the relevant specialist agents and returns the answer plus the agents' trace."""
    analysis = document_store["current_analysis"]
    if not analysis:
        return {
            "response": "Please upload a financial document or click 'Load Demo Analysis' before starting the chat.",
            "thought_log": []
        }

    try:
        response, thought_log = orchestrator.coordinate(chat.message, analysis)
        return {"response": response, "thought_log": thought_log}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Multi-agent reasoning failed: {str(e)}")


frontend_dir = os.path.join(PROJECT_ROOT, "frontend")

# Serve the dashboard UI at / (API routes above take precedence)
app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=int(os.getenv("PORT", "8000")))

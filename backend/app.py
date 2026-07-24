import os
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

from pipeline.document_processor import DocumentProcessor
from pipeline.llm_extractor import LLMExtractor
from pipeline.analytics import AnalyticsEngine
from pipeline.agents import OrchestratorAgent

load_dotenv()

app = FastAPI(
    title="AlphaDoc-Analytics API",
    description="Backend services for Generative AI KPI Extraction and Predictive Analytics.",
    version="1.0.0"
)

# CORS Policy configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Permits dashboard access from any client host/port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Shared in-memory cache to store the last analyzed document results for the chat agent
document_store = {
    "current_analysis": None
}

class ChatMessage(BaseModel):
    message: str

# Instantiate Multi-Agent Orchestrator
orchestrator = OrchestratorAgent()

@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    Saves an uploaded PDF document or Image (PNG/JPG/WEBP), extracts text and visual features,
    and processes it through the Multimodal GenAI and Analytics pipeline.
    """
    ext = os.path.splitext(file.filename)[1].lower()
    allowed_exts = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".bmp"}
    if ext not in allowed_exts:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file format '{ext}'. Supported formats: {', '.join(allowed_exts)}"
        )
        
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # 1. Process Document or Image
        doc_info = DocumentProcessor.process_file(file_path)
        
        # 2. Extract structured fields using Multimodal LLM Extractor
        extractor = LLMExtractor()
        extracted_data = extractor.analyze_document(
            text_content=doc_info["text_content"],
            filename=file.filename,
            document_type=doc_info["document_type"],
            image_b64=doc_info["image_b64"]
        )
        
        # 3. Perform Data Science Forecasting
        kpi_series = extracted_data.get("kpis", [])
        if not kpi_series:
            raise ValueError("No financial KPI time-series metrics could be extracted from this document/image.")
            
        analytics_results = AnalyticsEngine.forecast_next_period(kpi_series)
        
        # Merge structured results
        full_analysis = {
            "company_name": extracted_data.get("company_name", "GlobalCorp Technologies"),
            "financial_year": extracted_data.get("financial_year", "FY2025"),
            "document_type": doc_info["document_type"],
            "visual_insights": extracted_data.get("visual_insights", []),
            "image_b64": doc_info["image_b64"],
            "file_name": file.filename,
            "risks": extracted_data.get("risks", []),
            "sentiment": extracted_data.get("sentiment", {}),
            "historical": analytics_results.get("historical", []),
            "next_period": analytics_results.get("next_period", "Next Period"),
            "forecasts": analytics_results.get("forecasts", {}),
            "raw_text_length": len(doc_info["text_content"])
        }
        
        # Cache results in-memory for Q&A sessions
        document_store["current_analysis"] = full_analysis
        return full_analysis
        
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"Multimodal pipeline processing failed: {str(e)}")

@app.get("/api/demo")
async def load_demo_data():
    """
    Loads pre-calculated high-fidelity multimodal analysis (text + visual chart) 
    to enable immediate testing of the dashboard components without requiring a upload.
    """
    extractor = LLMExtractor()
    extracted_data = extractor.analyze_document("", "demo_report.pdf", document_type="pdf")
    analytics_results = AnalyticsEngine.forecast_next_period(extracted_data["kpis"])
    
    demo_analysis = {
        "company_name": extracted_data["company_name"],
        "financial_year": extracted_data["financial_year"],
        "document_type": "pdf",
        "visual_insights": extracted_data.get("visual_insights", [
            "Multimodal Vision Agent parsed quarterly revenue bar charts and confirmed upward trend.",
            "Operating margin progression exhibits +1.6% net expansion despite capital expenditure.",
            "Infographic balance sheet table confirms strong liquidity ratio and robust cash reserves."
        ]),
        "image_b64": None,
        "file_name": "demo_report.pdf",
        "risks": extracted_data["risks"],
        "sentiment": extracted_data["sentiment"],
        "historical": analytics_results["historical"],
        "next_period": analytics_results["next_period"],
        "forecasts": analytics_results["forecasts"],
        "raw_text_length": 45120
    }
    
    document_store["current_analysis"] = demo_analysis
    return demo_analysis

@app.post("/api/chat")
async def chat_with_document(chat: ChatMessage):
    """
    Coordinates specialized financial agents (Orchestrator, KPI, Risk, Sentiment)
    to perform multi-agent analysis and return the synthesized response alongside thought traces.
    """
    analysis = document_store["current_analysis"]
    if not analysis:
        return {
            "response": "Please upload a financial document or click 'Load Demo Data' before starting the chat.",
            "thought_log": []
        }
        
    try:
        response, thought_log = orchestrator.coordinate(chat.message, analysis)
        return {"response": response, "thought_log": thought_log}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Multi-agent reasoning failed: {str(e)}")

frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")

# Compatibility routes for legacy static paths
@app.get("/static/css/style.css")
@app.get("/static/css/styles.css")
@app.get("/style.css")
@app.get("/styles.css")
async def get_styles():
    from fastapi.responses import FileResponse
    return FileResponse(os.path.join(frontend_dir, "styles.css"), media_type="text/css")

@app.get("/static/js/app.js")
@app.get("/app.js")
async def get_script():
    from fastapi.responses import FileResponse
    return FileResponse(os.path.join(frontend_dir, "app.js"), media_type="application/javascript")

# Mount frontend files to serve the dashboard UI at the root path /
app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    # Serves API and UI locally on port 8000 when executed directly
    uvicorn.run(app, host="127.0.0.1", port=8000)

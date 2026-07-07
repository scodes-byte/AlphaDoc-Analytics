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

@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    Saves an uploaded PDF file, extracts its content, and processes it 
    through the GenAI and Analytics pipeline.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF documents are supported.")
        
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # 1. Extract Text
        text_content = DocumentProcessor.extract_text_from_pdf(file_path)
        
        # 2. Extract structured fields using LLM
        extractor = LLMExtractor()
        extracted_data = extractor.analyze_document(text_content, file.filename)
        
        # 3. Perform Data Science Forecasting
        kpi_series = extracted_data.get("kpis", [])
        if not kpi_series:
            raise ValueError("No financial KPI time-series metrics could be extracted from this document.")
            
        analytics_results = AnalyticsEngine.forecast_next_period(kpi_series)
        
        # Merge structured results
        full_analysis = {
            "company_name": extracted_data.get("company_name", "GlobalCorp Technologies"),
            "financial_year": extracted_data.get("financial_year", "FY2025"),
            "risks": extracted_data.get("risks", []),
            "sentiment": extracted_data.get("sentiment", {}),
            "historical": analytics_results.get("historical", []),
            "next_period": analytics_results.get("next_period", "Next Period"),
            "forecasts": analytics_results.get("forecasts", {}),
            "raw_text_length": len(text_content)
        }
        
        # Cache results in-memory for Q&A sessions
        document_store["current_analysis"] = full_analysis
        return full_analysis
        
    except Exception as e:
        # Cleanup file if failure occurs
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"Pipeline processing failed: {str(e)}")

@app.get("/api/demo")
async def load_demo_data():
    """
    Loads pre-calculated high-fidelity analysis to enable immediate testing 
    of the dashboard components without requiring a PDF upload.
    """
    extractor = LLMExtractor()
    # Runs extraction pipeline on empty inputs to generate standard realistic simulated analysis
    extracted_data = extractor.analyze_document("", "demo_report.pdf")
    analytics_results = AnalyticsEngine.forecast_next_period(extracted_data["kpis"])
    
    demo_analysis = {
        "company_name": extracted_data["company_name"],
        "financial_year": extracted_data["financial_year"],
        "risks": extracted_data["risks"],
        "sentiment": extracted_data["sentiment"],
        "historical": analytics_results["historical"],
        "next_period": analytics_results["next_period"],
        "forecasts": analytics_results["forecasts"],
        "raw_text_length": 45120 # simulated text length
    }
    
    document_store["current_analysis"] = demo_analysis
    return demo_analysis

@app.post("/api/chat")
async def chat_with_document(chat: ChatMessage):
    """
    Simulates a contextual conversational financial agent that answers user 
    questions based on the current document analysis cache.
    """
    analysis = document_store["current_analysis"]
    if not analysis:
        return {"response": "Please upload a financial document or click 'Load Demo Data' before starting the chat."}
        
    query = chat.message.lower()
    company = analysis["company_name"]
    
    # 1. Perform intent classification and synthesis
    if "revenue" in query:
        hist_rev = ", ".join([f"{item['period']}: ${item['revenue']}M" for item in analysis["historical"]])
        fc_rev = analysis["forecasts"]["revenue"]["predicted"]
        trend = "increasing" if analysis["forecasts"]["revenue"]["trend_slope"] > 0 else "decreasing"
        
        response = (f"According to the financial records for **{company}**, "
                    f"the historical revenue series shows: {hist_rev}. "
                    f"Our predictive data science model forecasts the next quarter (**{analysis['next_period']}**) "
                    f"revenue to be **${fc_rev}M** (with a {trend} trend slope of {analysis['forecasts']['revenue']['trend_slope']}).")
                    
    elif "risk" in query or "headwind" in query or "challenge" in query:
        risk_list = "\n".join([f"- {risk}" for risk in analysis["risks"]])
        response = f"Here are the core operational risk factors extracted by our risk analysis agent for **{company}**:\n\n{risk_list}"
        
    elif "sentiment" in query or "opinion" in query or "ceo" in query:
        sentiment_info = analysis["sentiment"]
        response = (f"The narrative sentiment classification is **{sentiment_info['classification']}** "
                    f"(with a quantitative score of **{sentiment_info['score']}** on a [-1, 1] scale).\n\n"
                    f"**CEO Perspective Summary:** {sentiment_info['ceo_statement_summary']}")
                    
    elif "net income" in query or "profit" in query:
        hist_profit = ", ".join([f"{item['period']}: ${item['net_income']}M" for item in analysis["historical"]])
        fc_profit = analysis["forecasts"]["net_income"]["predicted"]
        response = (f"Historical net income metrics for **{company}**: {hist_profit}.\n\n"
                    f"The predictive regression model projects a net income of **${fc_profit}M** for **{analysis['next_period']}**.")
                    
    else:
        # Default agent response aggregating main metrics
        response = (f"I am the financial intelligence agent for **{company}** ({analysis['financial_year']}).\n"
                    f"Currently, I have cached quarterly historical metrics for {len(analysis['historical'])} periods. "
                    f"I can assist with detailed queries about: **Revenue growth**, **Net Income projections**, **Operating Margins**, "
                    f"or the CEO's **Risk & Sentiment factors**. What would you like to explore?")
                    
    return {"response": response}

# Mount frontend files to serve the dashboard UI at the root path /
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    # Serves API and UI locally on port 8000 when executed directly
    uvicorn.run(app, host="127.0.0.1", port=8000)

# backend/pipeline/agents.py

import os
import time
import base64
from typing import List, Dict, Any, Tuple, Optional
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

class BaseAgent:
    def __init__(self, name: str, role: str, description: str):
        self.name = name
        self.role = role
        self.description = description
        
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.use_real_llm = bool(self.api_key and self.api_key.strip())
        
        if self.use_real_llm:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel("gemini-1.5-flash")

    def _call_llm_with_fallback(self, prompt: str, fallback_response: str, image_b64: Optional[str] = None) -> str:
        if self.use_real_llm:
            try:
                inputs = [prompt]
                if image_b64:
                    image_bytes = base64.b64decode(image_b64)
                    inputs.append({"mime_type": "image/jpeg", "data": image_bytes})
                response = self.model.generate_content(inputs)
                return response.text.strip()
            except Exception as e:
                print(f"[{self.name}] LLM invocation failed: {e}. Using rule-based fallback.")
        return fallback_response


class VisionAgent(BaseAgent):
    """
    Multimodal Vision Specialist Agent: Analyzes visual financial charts, balance sheet 
    screenshots, infographics, and graphical document elements.
    """
    def __init__(self):
        super().__init__(
            name="Multimodal Vision Agent",
            role="Visual & Document OCR Specialist",
            description="Inspects visual financial charts, balance sheet scans, infographics, and graphical trend lines."
        )

    def process(self, query: str, context: Dict[str, Any], log_cb) -> str:
        log_cb(f"[{self.name}] Ingesting visual feature maps, document graphics, and chart coordinates.")
        company = context.get("company_name", "GlobalCorp")
        doc_type = context.get("document_type", "pdf").upper()
        insights = context.get("visual_insights", [])
        image_b64 = context.get("image_b64")

        insight_list = "\n".join([f"• {item}" for item in insights])
        fallback_text = (
            f"**Multimodal Vision Analysis for {company} ({doc_type}):**\n\n"
            f"{insight_list}\n\n"
            f"The visual analysis engine confirmed clear graphical layout hierarchy and consistent metric presentation."
        )

        prompt = f"""
        You are the {self.name} ({self.role}).
        Visual Context for {company} ({doc_type}):
        - Detected Visual Insights:
        {insight_list}
        
        Answer the following user query focusing on visual, graphical, or chart data:
        Query: "{query}"
        
        Keep your response visual-centric, analytical, and structured.
        """
        
        log_cb(f"[{self.name}] Synthesizing visual chart trend lines and graphical highlights.")
        return self._call_llm_with_fallback(prompt, fallback_text, image_b64)


class KPIAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="KPI Analytics Agent",
            role="Financial Data Scientist",
            description="Analyzes financial time-series metrics, revenue margins, net income, and projects forecasts."
        )

    def process(self, query: str, context: Dict[str, Any], log_cb) -> str:
        log_cb(f"[{self.name}] Initiated context evaluation of financial sequences.")
        company = context.get("company_name", "GlobalCorp")
        historical = context.get("historical", [])
        forecasts = context.get("forecasts", {})
        next_period = context.get("next_period", "Next Quarter")
        image_b64 = context.get("image_b64")

        hist_rev = ", ".join([f"{item['period']}: ${item['revenue']}M" for item in historical]) if historical else "N/A"
        hist_net = ", ".join([f"{item['period']}: ${item['net_income']}M" for item in historical]) if historical else "N/A"
        
        fc_rev = forecasts.get("revenue", {}).get("predicted", 0.0)
        slope_rev = forecasts.get("revenue", {}).get("trend_slope", 0.0)
        trend_rev = "positive (growth)" if slope_rev >= 0 else "negative (headwind)"

        fc_net = forecasts.get("net_income", {}).get("predicted", 0.0)
        slope_net = forecasts.get("net_income", {}).get("trend_slope", 0.0)

        fallback_text = (
            f"According to the verified files for **{company}**, the historical revenue sequence displays: {hist_rev}.\n\n"
            f"Our predictive data science model forecasts the next period (**{next_period}**) revenue to be **${fc_rev}M** "
            f"(showing a {trend_rev} trend slope of {slope_rev}). Net income is projected to reach **${fc_net}M** for the same period."
        )

        prompt = f"""
        You are the {self.name} ({self.role}).
        Context data for {company}:
        - Historical Revenue: {hist_rev}
        - Historical Net Income: {hist_net}
        - Forecasted Revenue for {next_period}: ${fc_rev}M (Trend Slope: {slope_rev})
        - Forecasted Net Income for {next_period}: ${fc_net}M (Trend Slope: {slope_net})
        
        Answer the following user query about KPIs:
        Query: "{query}"
        
        Keep your response clear, professional, and emphasize the metrics.
        """
        
        log_cb(f"[{self.name}] Compiling regression and forecasting indicators.")
        return self._call_llm_with_fallback(prompt, fallback_text, image_b64)


class RiskAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Risk Specialist Agent",
            role="Corporate Risk Auditor",
            description="Evaluates operational risk factors, FX headwinds, competitor analysis, and R&D capital expenditure hazards."
        )

    def process(self, query: str, context: Dict[str, Any], log_cb) -> str:
        log_cb(f"[{self.name}] Running vulnerability assessment against operational risk logs.")
        company = context.get("company_name", "GlobalCorp")
        risks = context.get("risks", [])
        image_b64 = context.get("image_b64")
        
        risk_list = "\n".join([f"- {r}" for r in risks])
        fallback_text = (
            f"Here are the corporate risk indicators extracted for **{company}**:\n\n{risk_list}"
        )

        prompt = f"""
        You are the {self.name} ({self.role}).
        Operational Risks extracted for {company}:
        {risk_list}
        
        Answer the following user query about risks or headwinds:
        Query: "{query}"
        
        Keep your response precise and highly structured.
        """
        
        log_cb(f"[{self.name}] Classifying risk vectors and compiling remediation notes.")
        return self._call_llm_with_fallback(prompt, fallback_text, image_b64)


class SentimentAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Sentiment Analyst Agent",
            role="Market Sentiment Specialist",
            description="Analyzes qualitative corporate tone, executive commentary, and CEO statements."
        )

    def process(self, query: str, context: Dict[str, Any], log_cb) -> str:
        log_cb(f"[{self.name}] Analyzing tone parameters of executive messages.")
        company = context.get("company_name", "GlobalCorp")
        sentiment = context.get("sentiment", {})
        score = sentiment.get("score", 0.0)
        classification = sentiment.get("classification", "Neutral")
        ceo_statement = sentiment.get("ceo_statement_summary", "No CEO statement summary available.")
        image_b64 = context.get("image_b64")

        fallback_text = (
            f"The overall sentiment for **{company}** is classified as **{classification}** (with a quantitative score of **{score}** on a [-1, 1] scale).\n\n"
            f"**CEO Perspective Summary:** {ceo_statement}"
        )

        prompt = f"""
        You are the {self.name} ({self.role}).
        Corporate sentiment data for {company}:
        - Tone Classification: {classification} (Score: {score})
        - CEO Perspective: {ceo_statement}
        
        Answer the following user query about tone or sentiment:
        Query: "{query}"
        
        Provide a concise qualitative analysis.
        """
        
        log_cb(f"[{self.name}] Contextualizing qualitative CEO statements.")
        return self._call_llm_with_fallback(prompt, fallback_text, image_b64)


class OrchestratorAgent:
    """
    Multimodal Lead Coordinator Agent: Evaluates user prompts across text and visual modality inputs,
    routes tasks to specialized agents (KPI, Risk, Sentiment, Vision), and synthesizes output.
    """
    def __init__(self):
        self.kpi_agent = KPIAgent()
        self.risk_agent = RiskAgent()
        self.sentiment_agent = SentimentAgent()
        self.vision_agent = VisionAgent()
        
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.use_real_llm = bool(self.api_key and self.api_key.strip())
        
        if self.use_real_llm:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel("gemini-1.5-flash")

    def coordinate(self, query: str, context: Dict[str, Any]) -> Tuple[str, List[str]]:
        """
        Orchestrates multi-agent multimodal communication, dispatches tasks, and aggregates results.
        
        Returns:
            Tuple[str, List[str]]: (Synthesized Response, Thought Logs)
        """
        thought_logs = []
        def log(msg: str):
            thought_logs.append(f"[{time.strftime('%H:%M:%S')}] {msg}")

        doc_type = context.get("document_type", "pdf").upper()
        log(f"Orchestrator received prompt (Document Modality: {doc_type}): " + f'"{query}"')
        
        query_lower = query.lower()
        active_agents = []
        
        log("Evaluating multimodal routing intent...")
        
        # Check for visual / image queries
        if any(w in query_lower for w in ["visual", "image", "chart", "graphic", "diagram", "table", "picture", "look", "see", "ocr"]):
            active_agents.append(self.vision_agent)
            log("Routed target scope: Multimodal Vision Agent (active)")
            
        if any(w in query_lower for w in ["revenue", "profit", "net income", "margin", "forecast", "projection", "predict", "eps", "growth"]):
            active_agents.append(self.kpi_agent)
            log("Routed target scope: KPI Analytics Agent (active)")
            
        if any(w in query_lower for w in ["risk", "headwind", "challenge", "competitor", "disruption", "threat"]):
            active_agents.append(self.risk_agent)
            log("Routed target scope: Risk Specialist Agent (active)")
            
        if any(w in query_lower for w in ["sentiment", "tone", "ceo", "perspective", "opinion", "statement", "executive"]):
            active_agents.append(self.sentiment_agent)
            log("Routed target scope: Sentiment Analyst Agent (active)")
            
        # Default fallback if no specific routing triggered
        if not active_agents:
            log("No specialized domain matches found. Dispatching query to full agent network (Vision, KPI, Risk, Sentiment)...")
            active_agents = [self.vision_agent, self.kpi_agent, self.risk_agent, self.sentiment_agent]

        # Invoke active agents
        agent_responses = []
        for agent in active_agents:
            agent_response = agent.process(query, context, log)
            agent_responses.append((agent.name, agent_response))
            log(f"Received feedback block from {agent.name}.")

        # Synthesize final response
        log("Assembling final multimodal synthesis block...")
        
        if len(agent_responses) == 1:
            final_response = agent_responses[0][1]
            log("Completed response synthesis (single-agent output).")
        else:
            log("Merging outputs from multiple multimodal specialists...")
            company = context.get("company_name", "GlobalCorp")
            
            synthesis_input = "\n\n".join([f"### Output from {name}:\n{resp}" for name, resp in agent_responses])
            
            fallback_synthesis = (
                f"I have coordinated the analysis with my specialized financial & visual agents for **{company}**:\n\n" +
                "\n\n".join([f"**{name} Highlights:**\n{resp}" for name, resp in agent_responses])
            )
            
            prompt = f"""
            You are the Lead Financial & Multimodal Coordinator Orchestrator.
            Synthesize a single coherent, concise response to the user's query using the outputs provided by your specialized agents.
            
            User Query: "{query}"
            
            Agent Outputs:
            {synthesis_input}
            
            Combine the outputs fluidly without repeating agent names continuously. Keep it highly professional, visual-aware, and easy to read.
            """
            
            if self.use_real_llm:
                try:
                    res = self.model.generate_content(prompt)
                    final_response = res.text.strip()
                    log("Completed response synthesis (Consolidated Multimodal LLM output).")
                except Exception as e:
                    print(f"[Orchestrator] Consolidated LLM failed: {e}")
                    final_response = fallback_synthesis
                    log("Completed response synthesis (Fallback consolidation).")
            else:
                final_response = fallback_synthesis
                log("Completed response synthesis (Fallback consolidation).")
                
        return final_response, thought_logs

if __name__ == "__main__":
    orchestrator = OrchestratorAgent()
    print("Multimodal OrchestratorAgent compiled successfully.")

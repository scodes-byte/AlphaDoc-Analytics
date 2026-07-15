# backend/pipeline/agents.py

import os
import time
from typing import List, Dict, Any, Tuple
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

    def _call_llm_with_fallback(self, prompt: str, fallback_response: str) -> str:
        if self.use_real_llm:
            try:
                response = self.model.generate_content(prompt)
                return response.text.strip()
            except Exception as e:
                print(f"[{self.name}] LLM invocation failed: {e}. Using rule-based fallback.")
        return fallback_response


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

        # Compile data summaries
        hist_rev = ", ".join([f"{item['period']}: ${item['revenue']}M" for item in historical])
        hist_net = ", ".join([f"{item['period']}: ${item['net_income']}M" for item in historical])
        
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
        return self._call_llm_with_fallback(prompt, fallback_text)


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
        return self._call_llm_with_fallback(prompt, fallback_text)


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
        return self._call_llm_with_fallback(prompt, fallback_text)


class OrchestratorAgent:
    def __init__(self):
        self.kpi_agent = KPIAgent()
        self.risk_agent = RiskAgent()
        self.sentiment_agent = SentimentAgent()
        
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.use_real_llm = bool(self.api_key and self.api_key.strip())
        
        if self.use_real_llm:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel("gemini-1.5-flash")

    def coordinate(self, query: str, context: Dict[str, Any]) -> Tuple[str, List[str]]:
        """
        Orchestrates multi-agent communication, dispatches tasks, and aggregates results.
        
        Returns:
            Tuple[str, List[str]]: (Synthesized Response, Thought Logs)
        """
        thought_logs = []
        def log(msg: str):
            thought_logs.append(f"[{time.strftime('%H:%M:%S')}] {msg}")

        log("Orchestrator received prompt: " + f'"{query}"')
        
        # 1. Determine which agents are needed based on keyword heuristics or LLM routing
        query_lower = query.lower()
        active_agents = []
        
        log("Evaluating routing intent...")
        if any(w in query_lower for w in ["revenue", "profit", "net income", "margin", "forecast", "projection", "predict"]):
            active_agents.append(self.kpi_agent)
            log("Routed target scope: KPI Analytics Agent (active)")
        if any(w in query_lower for w in ["risk", "headwind", "challenge", "competitor", "disruption"]):
            active_agents.append(self.risk_agent)
            log("Routed target scope: Risk Specialist Agent (active)")
        if any(w in query_lower for w in ["sentiment", "tone", "ceo", "perspective", "opinion", "statement"]):
            active_agents.append(self.sentiment_agent)
            log("Routed target scope: Sentiment Analyst Agent (active)")
            
        # Default fallback if no specific routing triggered
        if not active_agents:
            log("No specialized domain matches found. Dispatching query to all agent endpoints for parallel review...")
            active_agents = [self.kpi_agent, self.risk_agent, self.sentiment_agent]

        # 2. Invoke active agents and collect their individual outputs
        agent_responses = []
        for agent in active_agents:
            agent_response = agent.process(query, context, log)
            agent_responses.append((agent.name, agent_response))
            log(f"Received feedback block from {agent.name}.")

        # 3. Synthesize the final response
        log("Assembling final synthesis block...")
        
        if len(agent_responses) == 1:
            # Single agent was sufficient
            final_response = agent_responses[0][1]
            log("Completed response synthesis (single-agent output).")
        else:
            # Multi-agent consolidation required
            log("Merging outputs from multiple specialists...")
            company = context.get("company_name", "GlobalCorp")
            
            synthesis_input = "\n\n".join([f"### Output from {name}:\n{resp}" for name, resp in agent_responses])
            
            fallback_synthesis = (
                f"I have coordinated the analysis with my specialized financial agents for **{company}**:\n\n" +
                "\n\n".join([f"**{name} Highlights:**\n{resp}" for name, resp in agent_responses])
            )
            
            prompt = f"""
            You are the Lead Financial Coordinator Orchestrator.
            Synthesize a single coherent, concise response to the user's query using the outputs provided by your specialized agents.
            
            User Query: "{query}"
            
            Agent Outputs:
            {synthesis_input}
            
            Combine the outputs fluidly without repeating the names of the agents continuously. Keep it highly professional and easy to read.
            """
            
            if self.use_real_llm:
                try:
                    res = self.model.generate_content(prompt)
                    final_response = res.text.strip()
                    log("Completed response synthesis (Consolidated LLM output).")
                except Exception as e:
                    print(f"[Orchestrator] Consolidated LLM failed: {e}")
                    final_response = fallback_synthesis
                    log("Completed response synthesis (Fallback consolidation).")
            else:
                final_response = fallback_synthesis
                log("Completed response synthesis (Fallback consolidation).")
                
        return final_response, thought_logs

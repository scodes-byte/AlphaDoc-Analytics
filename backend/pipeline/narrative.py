import re
from collections import Counter
from typing import Dict, Any, List

# Small finance-oriented word lists in the spirit of the Loughran-McDonald
# sentiment dictionary (general-purpose lexicons misread words like "liability").
POSITIVE_WORDS = {
    "record", "growth", "grew", "increase", "increased", "improve", "improved", "improvement",
    "strong", "stronger", "highest", "gain", "gains", "expand", "expanded", "expansion",
    "achieve", "achieved", "success", "successful", "profitable", "profitability", "efficient",
    "efficiency", "launch", "launched", "progress", "opportunity", "opportunities", "robust",
    "exceed", "exceeded", "momentum", "lowest-ever", "best-selling",
}
NEGATIVE_WORDS = {
    "decline", "declined", "decrease", "decreased", "loss", "losses", "weak", "weaker",
    "headwind", "headwinds", "risk", "risks", "uncertain", "uncertainty", "pressure",
    "pressures", "challenge", "challenges", "challenging", "lower", "reduced", "reduction",
    "difficult", "volatility", "volatile", "tariff", "tariffs", "disruption", "disruptions",
    "impairment", "slowdown", "negative", "adverse", "adversely", "shortage", "recall",
}
RISK_TERMS = re.compile(
    r"\b(risk|headwind|uncertain|pressure|challeng|tariff|disruption|declin|volatil|"
    r"competition|competitive|regulat|interest rate|inflation|macroeconomic|shortage|recall)\w*",
    re.IGNORECASE,
)
TOKEN_RE = re.compile(r"[a-z][a-z\-]+")
# Legal disclaimers mention "risks" constantly but say nothing about the business
BOILERPLATE_RE = re.compile(
    r"forward-looking|securities and exchange commission|form 10-[kq]|risk factors|not guarantees|"
    r"undertakes no obligation|safe harbor",
    re.IGNORECASE,
)


def split_sentences(text: str) -> List[str]:
    """Rejoins PDF-wrapped lines and splits the text into sentences."""
    flat = re.sub(r"\s+", " ", text.replace("-\n", ""))
    sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z])", flat)
    # Keep prose only: drop table rows and very short fragments
    return [s.strip() for s in sentences if 40 <= len(s) <= 400 and sum(c.isdigit() for c in s) < len(s) * 0.15]


def score_sentiment(text: str) -> Dict[str, Any]:
    """
    Lexicon-based tone score in [-1, 1]: (positive - negative) / (positive + negative).
    Transparent and reproducible, used when no LLM is configured.
    """
    tokens = TOKEN_RE.findall(text.lower())
    pos = sum(1 for t in tokens if t in POSITIVE_WORDS)
    neg = sum(1 for t in tokens if t in NEGATIVE_WORDS)
    score = round((pos - neg) / (pos + neg), 2) if (pos + neg) else 0.0

    if score >= 0.35:
        classification = "Optimistic"
    elif score >= 0.1:
        classification = "Positive"
    elif score > -0.1:
        classification = "Neutral"
    elif score > -0.35:
        classification = "Cautious"
    else:
        classification = "Negative"

    # Extractive summary: the most opinionated sentences in the document
    scored = []
    for sentence in split_sentences(text):
        words = TOKEN_RE.findall(sentence.lower())
        weight = sum(1 for w in words if w in POSITIVE_WORDS or w in NEGATIVE_WORDS)
        if weight:
            scored.append((weight, sentence))
    scored.sort(key=lambda item: item[0], reverse=True)
    summary = " ".join(s for _, s in scored[:2]) or "No management commentary found in the text."

    return {
        "score": score,
        "classification": classification,
        "ceo_statement_summary": summary,
        "method": f"lexicon ({pos} positive / {neg} negative terms)",
    }


def extract_risks(text: str, limit: int = 5) -> List[str]:
    """Returns the sentences that mention the most risk-related terms."""
    candidates = []
    seen = set()
    for sentence in split_sentences(text):
        if BOILERPLATE_RE.search(sentence):
            continue
        hits = len(RISK_TERMS.findall(sentence))
        key = sentence[:60].lower()
        if hits and key not in seen:
            seen.add(key)
            candidates.append((hits, sentence))
    candidates.sort(key=lambda item: item[0], reverse=True)
    return [s for _, s in candidates[:limit]]


def detect_company_name(text: str, filename: str) -> str:
    """
    Finds the company name: first a legal entity such as 'Tesla, Inc.', then the capitalised
    word most often used in possessive form ("Tesla's"), finally the file name.
    """
    match = re.search(
        r"\b([A-Z][A-Za-z0-9&.\-]+(?: [A-Z][A-Za-z0-9&.\-]+){0,3}),? (?:Inc|Corp|Corporation|Ltd|Limited|plc|N\.V|AG|SE)\b\.?",
        text[:20000],
    )
    if match:
        return match.group(1)
    possessives = Counter(re.findall(r"\b([A-Z][a-zA-Z]{2,})(?:'|’|�)s\b", text))
    if possessives:
        name, count = possessives.most_common(1)[0]
        if count >= 3:
            return name
    stem = re.split(r"[_\-\s.]", filename)[0]
    return stem.capitalize() if stem else "Unknown company"


def compute_insights(kpis: List[Dict[str, Any]]) -> List[str]:
    """Plain-language facts computed directly from the extracted KPI table."""
    if len(kpis) < 2:
        return []
    first, last, prev = kpis[0], kpis[-1], kpis[-2]
    insights = []

    if prev.get("revenue"):
        qoq = (last["revenue"] - prev["revenue"]) / abs(prev["revenue"]) * 100
        insights.append(f"Revenue moved {qoq:+.1f}% QoQ to ${last['revenue']:,.0f}M in {last['period']}.")
    if first.get("revenue"):
        span = (last["revenue"] - first["revenue"]) / abs(first["revenue"]) * 100
        insights.append(f"Revenue changed {span:+.1f}% from {first['period']} to {last['period']}.")
    if last.get("operating_margin") is not None and first.get("operating_margin") is not None:
        delta = last["operating_margin"] - first["operating_margin"]
        insights.append(
            f"Operating margin went from {first['operating_margin']}% to {last['operating_margin']}% "
            f"({delta:+.1f} pts) over the period."
        )
    net_values = [k["net_income"] for k in kpis if k.get("net_income") is not None]
    if len(net_values) >= 3:
        median = sorted(net_values)[len(net_values) // 2]
        outliers = [k["period"] for k in kpis if k.get("net_income") and median and k["net_income"] > 2.5 * median]
        if outliers:
            insights.append(
                f"Net income in {', '.join(outliers)} is far above the median quarter; likely a one-off item "
                f"that distorts the linear trend."
            )
    return insights

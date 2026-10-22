import re
from typing import Dict, Any, List, Optional

# Matches quarter labels such as "Q4-2024", "Q4 2024", "Q4'24" or "Q4 FY2024".
PERIOD_RE = re.compile(r"\bQ([1-4])\s*[-–'’ ]?\s*(?:FY)?\s*(\d{4}|\d{2})\b", re.IGNORECASE)

# A numeric cell: 1,234 | 5.5% | (2,531) | -0.34 | $1.2
NUMBER_RE = re.compile(r"\(?-?\$?\d[\d,]*\.?\d*%?\)?")

# Row labels to look for, in priority order. GAAP rows win over non-GAAP rows.
METRIC_PATTERNS = {
    "revenue": [
        r"^total revenues?\b",
        r"^total net revenues?\b",
        r"^net revenues?\b",
        r"^total net sales\b",
        r"^net sales\b",
        r"^revenues?\b",
    ],
    "operating_income": [
        r"^income from operations\b",
        r"^operating income\b",
    ],
    "operating_margin": [
        r"^operating margin\b",
    ],
    "net_income": [
        r"^net income attributable to common stockholders \(gaap\)",
        r"^net income attributable to (?!.*non-gaap)",
        r"^net income\b(?!.*non-gaap)",
    ],
    "eps": [
        r"^eps attributable to common stockholders, diluted \(gaap\)",
        r"^diluted (?:eps|earnings per share)\b(?!.*non-gaap)",
        r"^(?:eps|earnings per share)\b.*diluted(?!.*non-gaap)",
    ],
}


def normalize_period(quarter: str, year: str) -> str:
    """Normalises ('4', '24') or ('4', '2024') to 'Q4 2024'."""
    year_int = int(year)
    if year_int < 100:
        year_int += 2000
    return f"Q{int(quarter)} {year_int}"


def parse_number(token: str) -> Optional[float]:
    """Parses a financial table cell. Parentheses mean a negative value."""
    token = token.strip()
    negative = token.startswith("(") and token.endswith(")")
    cleaned = token.strip("()").replace("$", "").replace(",", "").replace("%", "")
    try:
        value = float(cleaned)
    except ValueError:
        return None
    return -abs(value) if negative else value


def _unit_multiplier(header_line: str) -> float:
    """Converts table values to millions based on the unit note in the header."""
    lower = header_line.lower()
    if "in thousands" in lower:
        return 0.001
    if "in billions" in lower:
        return 1000.0
    return 1.0


def _match_metric(label_text: str) -> Optional[tuple]:
    """Returns (metric, priority) for a table row label, or None."""
    lower = label_text.lower().strip()
    for metric, patterns in METRIC_PATTERNS.items():
        for priority, pattern in enumerate(patterns):
            if re.search(pattern, lower):
                return metric, priority
    return None


def extract_kpi_table(text: str) -> List[Dict[str, Any]]:
    """
    Deterministic (non-LLM) extraction of a quarterly KPI table from PDF text.

    Strategy: find a header line containing two or more quarter labels, then read
    the rows below it whose label matches a known metric. The first N numeric cells
    of each row map to the N periods in the header (trailing YoY columns are ignored).
    The header block with the most metrics wins.

    Returns a chronologically ordered list of KPI dicts, or [] if no table is found.
    """
    best_block: Dict[str, Any] = {}
    block: Optional[Dict[str, Any]] = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        periods = PERIOD_RE.findall(line)
        if len(periods) >= 2:
            if block and len(block["rows"]) > len(best_block.get("rows", {})):
                best_block = block
            block = {
                "periods": [normalize_period(q, y) for q, y in periods],
                "multiplier": _unit_multiplier(line),
                "rows": {},
            }
            continue
        if block is None:
            continue

        first_number = NUMBER_RE.search(line)
        if not first_number or first_number.start() == 0:
            continue
        label = line[: first_number.start()]
        matched = _match_metric(label)
        if not matched:
            continue
        metric, priority = matched
        existing = block["rows"].get(metric)
        if existing and existing["priority"] <= priority:
            continue

        cells = [parse_number(tok) for tok in NUMBER_RE.findall(line[first_number.start():])]
        n_periods = len(block["periods"])
        if len(cells) < n_periods:
            continue
        block["rows"][metric] = {"priority": priority, "values": cells[:n_periods]}

    if block and len(block["rows"]) > len(best_block.get("rows", {})):
        best_block = block

    rows = best_block.get("rows", {})
    if "revenue" not in rows:
        return []

    multiplier = best_block["multiplier"]
    kpis = []
    for idx, period in enumerate(best_block["periods"]):
        revenue = rows["revenue"]["values"][idx]
        record = {"period": period, "revenue": _scale(revenue, multiplier)}

        if "operating_margin" in rows:
            record["operating_margin"] = rows["operating_margin"]["values"][idx]
        elif "operating_income" in rows and revenue:
            # Derive margin when the table only reports operating income
            record["operating_margin"] = round(rows["operating_income"]["values"][idx] / revenue * 100, 2)
        else:
            record["operating_margin"] = None

        record["net_income"] = _scale(rows["net_income"]["values"][idx], multiplier) if "net_income" in rows else None
        record["eps"] = rows["eps"]["values"][idx] if "eps" in rows else None
        kpis.append(record)
    return kpis


def _scale(value: Optional[float], multiplier: float) -> Optional[float]:
    return None if value is None else round(value * multiplier, 2)


def merge_kpi_histories(histories: List[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """
    Merges KPI series from several reports into one de-duplicated history.
    Later reports overwrite earlier ones, so restated figures take precedence.
    """
    merged: Dict[str, Dict[str, Any]] = {}
    for history in histories:
        for record in history:
            merged[record["period"]] = record
    return sorted(merged.values(), key=lambda r: period_sort_key(r["period"]))


def period_sort_key(period: str) -> tuple:
    match = PERIOD_RE.search(period or "")
    if not match:
        return (9999, 9)
    normalized = normalize_period(*match.groups())
    quarter, year = normalized[1], normalized.split()[1]
    return (int(year), int(quarter))

"""
Shared query parsing module for Stock Search Assistant.

This module contains all the common query parsing logic that converts
natural language user input into structured search specifications.
It's shared across app.py, app_sdk.py, and streamlit_app.py to avoid code duplication.
"""

import re
from typing import Dict, Any, Optional

# ============================================================
# Configuration: Metrics, Indices, Sectors, Comparators
# ============================================================

METRIC_ALIASES = {
    "pe": "PE",
    "p/e": "PE",
    "p e": "PE",
    "pb": "PB",
    "p/b": "PB",
    "p b": "PB",
    "price to book": "PB",
    "price": "PRICE",  # assume dynamic source outside Azure Search
    "share price": "PRICE",
    "market price": "PRICE",
    "market cap": "MarketCapCr",
    "marketcap": "MarketCapCr",
    "market capitalization": "MarketCapCr",
    "eps": "EPS",
    "earnings per share": "EPS",
    "dividend": "DividendYieldPct",
    "dividend yield": "DividendYieldPct",
    "sector": "Sector",
}

SECTOR_ALIASES = {
    # Energy
    "energy": "Energy",
    "oil": "Energy",
    "gas": "Energy",
    "petroleum": "Energy",
    "oil and gas": "Energy",
    "oil & gas": "Energy",
    
    # Information Technology
    "information technology": "Information Technology",
    "it": "Information Technology",
    "tech": "Information Technology",
    "technology": "Information Technology",
    "software": "Information Technology",
    "infotech": "Information Technology",
    
    # Financials
    "financials": "Financials",
    "financial": "Financials",
    "finance": "Financials",
    "banking": "Financials",
    "bank": "Financials",
    "banks": "Financials",
    "nbfc": "Financials",
    "insurance": "Financials",
    "financial services": "Financials",
    
    # Automobile
    "automobile": "Automobile",
    "auto": "Automobile",
    "automotive": "Automobile",
    "cars": "Automobile",
    "vehicles": "Automobile",
    "automobiles": "Automobile",
    
    # Consumer Staples
    "consumer staples": "Consumer Staples",
    "fmcg": "Consumer Staples",
    "consumer goods": "Consumer Staples",
    "staples": "Consumer Staples",
    "fast moving consumer goods": "Consumer Staples",
    
    # Consumer Discretionary
    "consumer discretionary": "Consumer Discretionary",
    "discretionary": "Consumer Discretionary",
    "retail": "Consumer Discretionary",
    "consumer durables": "Consumer Discretionary",
    
    # Healthcare
    "healthcare": "Healthcare",
    "health": "Healthcare",
    "pharma": "Healthcare",
    "pharmaceutical": "Healthcare",
    "pharmaceuticals": "Healthcare",
    "hospitals": "Healthcare",
    "health care": "Healthcare",
    
    # Materials
    "materials": "Materials",
    "material": "Materials",
    "metals": "Materials",
    "metal": "Materials",
    "mining": "Materials",
    "steel": "Materials",
    "cement": "Materials",
    "chemicals": "Materials",
    "metals and mining": "Materials",
    
    # Industrials
    "industrials": "Industrials",
    "industrial": "Industrials",
    "manufacturing": "Industrials",
    "engineering": "Industrials",
    "construction": "Industrials",
    "infrastructure": "Industrials",
    
    # Utilities
    "utilities": "Utilities",
    "utility": "Utilities",
    "power": "Utilities",
    "electricity": "Utilities",
    "electric": "Utilities",
    
    # Communication Services
    "communication services": "Communication Services",
    "telecom": "Communication Services",
    "communication": "Communication Services",
    "telco": "Communication Services",
    "telecommunications": "Communication Services",
    
    # Conglomerate
    "conglomerate": "Conglomerate",
    "diversified": "Conglomerate",
    "conglomerates": "Conglomerate",
    
    # Real Estate
    "real estate": "Real Estate",
    "realty": "Real Estate",
    "property": "Real Estate",
    "real-estate": "Real Estate",
}

INDEX_ALIASES = {
    # NIFTY 50
    "nifty 50": "NIFTY50",
    "nifty50": "NIFTY50",
    "nifty fifty": "NIFTY50",
    "niftyfifty": "NIFTY50",
    "nifty-50": "NIFTY50",
    
    # NIFTY 100
    "nifty 100": "NIFTY100",
    "nifty100": "NIFTY100",
    "nifty hundred": "NIFTY100",
    "nifty-100": "NIFTY100",

    # NIFTY IT
    "nifty it": "NIFTYIT",
    "niftyit": "NIFTYIT",
    "nifty-it": "NIFTYIT",
    "nifty information technology": "NIFTYIT",
    "nifty tech": "NIFTYIT",

    # NIFTY BANK
    "nifty bank": "NIFTYBANK",
    "niftybank": "NIFTYBANK",
    "nifty-bank": "NIFTYBANK",
    "nifty banking": "NIFTYBANK",

    # NIFTY FMCG
    "nifty fmcg": "NIFTYFMCG",
    "niftyfmcg": "NIFTYFMCG",
    "nifty-fmcg": "NIFTYFMCG",
    "nifty consumer staples": "NIFTYFMCG",
    
    # NIFTY ENERGY
    "nifty energy": "NIFTYENERGY",
    "niftyenergy": "NIFTYENERGY",
    "nifty-energy": "NIFTYENERGY",
    "nifty oil gas": "NIFTYENERGY",
    
    # NIFTY AUTO
    "nifty auto": "NIFTYAUTO",
    "niftyauto": "NIFTYAUTO",
    "nifty-auto": "NIFTYAUTO",
    "nifty automobile": "NIFTYAUTO",
    
    # NIFTY PHARMA
    "nifty pharma": "NIFTYPHARMA",
    "niftypharma": "NIFTYPHARMA",
    "nifty-pharma": "NIFTYPHARMA",
    "nifty pharmaceutical": "NIFTYPHARMA",
    "nifty healthcare": "NIFTYPHARMA",
    
    # NIFTY METAL
    "nifty metal": "NIFTYMETAL",
    "niftymetal": "NIFTYMETAL",
    "nifty-metal": "NIFTYMETAL",
    "nifty metals": "NIFTYMETAL",
    
    # NIFTY REALTY
    "nifty realty": "NIFTYREALTY",
    "niftyrealty": "NIFTYREALTY",
    "nifty-realty": "NIFTYREALTY",
    "nifty real estate": "NIFTYREALTY",
}

COMPARATOR_ALIASES = {
    ">": "gt",
    "greater than": "gt",
    "higher than": "gt",
    "more than": "gt",
    "above": "gt",
    "over": "gt",

    "<": "lt",
    "less than": "lt",
    "lower than": "lt",
    "under": "lt",
    "below": "lt",

    ">=": "ge",
    "at least": "ge",
    "<=": "le",
    "at most": "le",
}

STOPWORDS_FOR_STOCK = {
    "what", "is", "the", "of", "for", "give", "me", "show",
    "tell", "stock", "stocks", "share", "shares",
    "price", "pe", "p/e", "eps",
    "dividend", "yield", "market", "cap", "in", "on", "all",
    # Add explicit sector modifiers that indicate sector queries, not stock names
    "sector", "sectors", "industry"
}


def normalize(text: str) -> str:
    """Normalize text by lowercasing and removing extra whitespace."""
    return " ".join(text.lower().strip().split())


# ============================================================
# Detection helpers - identify key components from user query
# ============================================================

def detect_metric(text_lower: str) -> Optional[Dict[str, Any]]:
    """
    Detect financial metric from user input using longest-match strategy.
    
    Args:
        text_lower: Lowercase normalized user query text
        
    Returns:
        Dictionary with:
            - "phrase": The matched phrase from METRIC_ALIASES
            - "column": The corresponding index column name
        Returns None if no metric detected
        
    Examples:
        "pe ratio" -> {"phrase": "pe ratio", "column": "PE_Ratio"}
        "market cap" -> {"phrase": "market cap", "column": "Market_Cap"}
    """
    best = None
    for phrase, col in METRIC_ALIASES.items():
        if phrase in text_lower:
            if best is None or len(phrase) > len(best["phrase"]):
                best = {"phrase": phrase, "column": col}
    return best


def detect_index_code(text_lower: str) -> Optional[str]:
    """
    Detect stock index from user input using longest-match strategy.
    
    Args:
        text_lower: Lowercase normalized user query text
        
    Returns:
        Index code string (e.g., "SENSEX", "NIFTY 50", "NIFTY BANK")
        Returns None if no index detected
        
    Examples:
        "sensex stocks" -> "SENSEX"
        "nifty bank" -> "NIFTY BANK"
    """
    best = None
    for phrase, code in INDEX_ALIASES.items():
        if phrase in text_lower:
            if best is None or len(phrase) > len(best["phrase"]):
                best = {"phrase": phrase, "code": code}
    return best["code"] if best else None


def detect_sector(text_lower: str, original_text: str) -> Optional[str]:
    """
    Detect sector from user input with company-name protection.
    
    Avoids matching if sector keyword appears to be part of a company name.
    For example: 'axis bank' or 'bajaj auto' should not trigger sector detection.
    
    Args:
        text_lower: Lowercase normalized user query
        original_text: Original user query (preserves capitalization)
        
    Returns:
        Sector name string (e.g., "Banking", "IT", "Automobile")
        Returns None if no sector detected or likely company name
        
    Examples:
        "banking stocks" -> "Banking" (sector filter)
        "axis bank" -> None (company name, not sector)
    """
    
    # Words that indicate a sector/listing query rather than a company name
    sector_modifiers = {
        "all", "top", "best", "good", "leading", "major", "large", "small",
        "sector", "stocks", "companies", "list", "show", "get", "find"
    }

    best = None
    for phrase, sector in SECTOR_ALIASES.items():
        if phrase in text_lower:
            if best is None or len(phrase) > len(best["phrase"]):
                best = {"phrase": phrase, "sector": sector}
    
    if best is None:
        return None
    
    # Check if it's likely a company name vs sector query
    phrase = best["phrase"]
    words_in_query = text_lower.split()
    
    # If query has sector modifiers, it's definitely a sector query
    if any(mod in words_in_query for mod in sector_modifiers):
        return best["sector"]
    
    # If query is very short (1-2 words) without modifiers, likely a company name
    # Examples: "bajaj auto", "axis bank", "reliance" (company names)
    # vs "banking stocks", "sector materials" (sector queries with modifiers)
    if len(words_in_query) <= 2:
        # Check if the sector keyword is the entire query or preceded by another word
        # If it's just the sector word alone (e.g., "banking"), it's likely a sector query
        # If it's part of a 2-word phrase (e.g., "bajaj auto", "axis bank"), likely company name
        if len(words_in_query) == 2:
            # Two-word query without modifiers = likely company name
            return None
        elif len(words_in_query) == 1:
            # Single word that matches sector could be sector query
            # unless it's a very specific match (keep sector detection)
            pass
    
    return best["sector"]


def detect_metric_filter(text_lower: str) -> Optional[Dict[str, Any]]:
    """
    Detect metric filter patterns like 'pe more than 10' or 'market cap > 1000'.
    
    Returns:
        Dictionary with metric, operator, value, and raw phrases, or None
    """
    metric_pattern = r"(market cap|marketcap|pb|p/b|pe|p/e|eps|dividend yield|dividend|price|share price|market price)"
    comp_pattern = r"(>=|<=|>|<|greater than|more than|above|over|less than|under|below|at least|at most)"
    regex = re.compile(metric_pattern + r".*?" + comp_pattern + r"\s*([\d\.]+)")

    m = regex.search(text_lower)
    if not m:
        return None

    metric_phrase = m.group(1)
    comp_phrase = m.group(2)
    value_str = m.group(3)

    metric_col = METRIC_ALIASES.get(metric_phrase)
    if not metric_col:
        return None

    op = COMPARATOR_ALIASES.get(comp_phrase)
    if not op:
        return None

    try:
        value = float(value_str)
    except ValueError:
        return None

    return {
        "metric": metric_col,
        "op": op,
        "value": value,
        "raw_metric_phrase": metric_phrase,
        "raw_comp_phrase": comp_phrase,
    }


def extract_stock_query(original: str, text_lower: str, metric_info: Optional[Dict[str, Any]]) -> Optional[str]:
    """
    Extract stock name from query by removing metric phrases and stopwords.
    
    Preserves company names even if they contain sector keywords (e.g., 'axis bank', 'bajaj auto').
    """
    tokens = re.findall(r"[a-zA-Z0-9&.\-]+", text_lower)
    if metric_info:
        metric_tokens = metric_info["phrase"].split()
    else:
        metric_tokens = []

    filtered = []
    for tok in tokens:
        if tok in STOPWORDS_FOR_STOCK:
            continue
        if tok in metric_tokens:
            continue
        filtered.append(tok)

    if not filtered:
        return None
    return " ".join(filtered)


# ============================================================
# Main query parsing: user text -> spec
# ============================================================

def parse_user_query(user_input: str) -> Dict[str, Any]:
    """
    Core router: Analyze user input and determine query mode with parameters.
    
    This is the most important function - it interprets natural language queries
    and converts them into structured search specifications.
    
    Args:
        user_input: Raw user query string (e.g., "pe of infy", "nifty 50 banking stocks")
        
    Returns:
        Dictionary with query specification containing:
            - "mode": Query type (single_stock_metric, list_by_index, etc.)
            - Other fields depend on mode (stock_query, metric, index_code, sector, metric_filter)
    
    Query Modes:
        1. single_stock_metric: Get specific metric for one company
           Example: "pe of reliance" -> {mode: "single_stock_metric", stock_query: "reliance", metric: "PE_Ratio"}
           
        2. single_stock_overview: Get all info for one company
           Example: "infosys" -> {mode: "single_stock_overview", stock_query: "infosys"}
           
        3. list_by_index: List all stocks in an index
           Example: "nifty 50" -> {mode: "list_by_index", index_code: "NIFTY 50"}
           
        4. list_by_metric_filter: Filter stocks by metric range
           Example: "stocks with pe less than 20" -> {mode: "list_by_metric_filter", metric_filter: {...}}
           
        5. list_by_sector: Filter stocks by sector
           Example: "banking stocks" -> {mode: "list_by_sector", sector: "Banking"}
    
    Priority Logic:
        More specific queries match first to avoid false positives:
        - "nifty bank high pe" -> Index + Sector + Metric (most specific)
        - "axis bank" -> Single stock (company name, not sector)
        - "banking" -> Sector filter (no other context)
        
    Note:
        The priority order in this function is CRITICAL for correct interpretation.
        Do not reorder the if-elif blocks without careful testing.
    """
    original = user_input
    text_lower = normalize(user_input)

    metric_info = detect_metric(text_lower)
    index_code = detect_index_code(text_lower)
    sector = detect_sector(text_lower, original)
    metric_filter = detect_metric_filter(text_lower)

    # 1) Index + Metric filter combination (e.g., "nifty 50 stocks with pe less than 50")
    if index_code is not None and metric_filter is not None:
        return {
            "mode": "list_by_metric_filter",
            "index_code": index_code,
            "metric_filter": {
                "metric": metric_filter["metric"],
                "op": metric_filter["op"],
                "value": metric_filter["value"]
            },
            "raw": {
                "input": original,
                "metric_phrase": metric_filter["raw_metric_phrase"],
                "comp_phrase": metric_filter["raw_comp_phrase"]
            }
        }

    # 2) Index + Sector (e.g., "nifty 50 banking stocks")
    if index_code is not None and sector is not None:
        return {
            "mode": "list_by_index_and_sector",
            "index_code": index_code,
            "sector": sector,
            "raw": {"input": original}
        }

    # 3) Sector + Metric filter (e.g., "it stocks with pe more than 40")
    if sector is not None and metric_filter is not None:
        return {
            "mode": "list_by_sector_and_metric_filter",
            "sector": sector,
            "metric_filter": {
                "metric": metric_filter["metric"],
                "op": metric_filter["op"],
                "value": metric_filter["value"]
            },
            "raw": {
                "input": original,
                "metric_phrase": metric_filter["raw_metric_phrase"],
                "comp_phrase": metric_filter["raw_comp_phrase"]
            }
        }

    # 4) Single stock metric (e.g., "pe of reliance", "axis bank pe")
    # CHECK THIS BEFORE SECTOR to handle cases like "axis bank pe" correctly
    # If user asks for a metric, it's likely a stock query, not a sector query
    if metric_info:
        stock_query = extract_stock_query(original, text_lower, metric_info)
        if stock_query:
            # Only return single_stock_metric if the query doesn't have explicit sector modifiers
            # like "sector banking pe" which would be weird but possible
            has_sector_modifier = any(word in text_lower.split() for word in ["sector", "sectors", "industry"])
            if not has_sector_modifier:
                return {
                    "mode": "single_stock_metric",
                    "stock_query": stock_query,
                    "metric": metric_info["column"],
                    "raw": {
                        "input": original,
                        "metric_phrase": metric_info["phrase"]
                    }
                }

    # 5) Index only (e.g., "nifty 50")
    if index_code is not None:
        return {
            "mode": "list_by_index",
            "index_code": index_code,
            "metric_filter": None,
            "raw": {"input": original}
        }

    # 6) Sector only (e.g., "banking stocks", "sector materials")
    # This is checked AFTER single_stock_metric to avoid false positives
    # like "axis bank pe" being interpreted as sector query
    # But we detect it if there's explicit sector modifier or no metric present
    if sector is not None:
        return {
            "mode": "list_by_sector",
            "sector": sector,
            "raw": {"input": original}
        }

    # 7) Metric filter without index/sector (e.g., "stocks with pe less than 20")
    if metric_filter is not None:
        return {
            "mode": "list_by_metric_filter",
            "metric_filter": {
                "metric": metric_filter["metric"],
                "op": metric_filter["op"],
                "value": metric_filter["value"]
            },
            "raw": {
                "input": original,
                "metric_phrase": metric_filter["raw_metric_phrase"],
                "comp_phrase": metric_filter["raw_comp_phrase"]
            }
        }

    # 8) Fallback: Single stock overview (e.g., "infosys")
    stock_query = extract_stock_query(original, text_lower, None)
    if stock_query:
        return {
            "mode": "single_stock_overview",
            "stock_query": stock_query,
            "raw": {"input": original}
        }

    # 9) No meaningful parse
    return {
        "mode": "unknown",
        "raw": {"input": original},
        "error": "Could not parse query. Try patterns like 'nifty 50', 'pe of reliance', 'banking stocks'."
    }

import re
from typing import Dict, Any, Optional
import time
import os
from dotenv import load_dotenv

import requests  # add at the top of the file if not already present
import json

# Load environment variables from .env file
load_dotenv()

# ============================================================
# HTTP Connection Pooling for Performance
# ============================================================
# Create a global session for connection pooling (reuse connections)
# This significantly improves performance by avoiding connection overhead
# 
# Performance Impact:
#   - First request: ~700-800ms (includes SSL handshake, DNS lookup)
#   - Subsequent requests: ~160-350ms (80% faster via connection reuse)
# 
# Without session: Each request creates new TCP connection = +400-500ms overhead
# With session: TCP connection reused across requests = minimal overhead
_http_session = requests.Session()

def execute_search_request(req: dict) -> dict:
    """
    Execute Azure Search API request using connection-pooled HTTP session.
    
    This function performs the actual HTTP POST to Azure Search, using a 
    persistent session for connection reuse across multiple requests.
    
    Args:
        req: Dictionary containing:
            - "spec": Search specification with parameters
            - "method": HTTP method (POST)
            - "url": Full Azure Search API endpoint
            - "headers": HTTP headers including api-key
            - "json": Request body with search, filter, select, etc.
        
    Returns:
        Dictionary with search results from Azure Search API response
        
    Performance:
        - Uses _http_session for connection pooling
        - First call: ~700-800ms (establishes connection)
        - Subsequent calls: ~160-350ms (reuses connection)
        
    Note:
        Connection pooling reduces overhead from 1400ms to 160-350ms
        by reusing TCP connections and avoiding SSL handshake each time.
    """
    response = _http_session.post(
        req["url"],
        headers=req["headers"],
        json=req["json"],
        timeout=10
    )
    try:
        data = response.json()
    except ValueError:
        # In case Azure returns non-JSON error
        data = {"raw_text": response.text}

    return {
        "status_code": response.status_code,
        "spec": req["spec"],
        "request_payload": req["json"],
        "response": data
    }


# ============================================================
# Config: metrics, indices, comparators
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
    "dividend", "yield", "market", "cap", "in", "on", "all"
}


def normalize(text: str) -> str:
    return " ".join(text.lower().strip().split())


# ============================================================
# Detection helpers - identify key components from user query
# ============================================================
# These functions parse user input to detect:
#   - Metrics (PE ratio, market cap, dividend yield, etc.)
#   - Index codes (SENSEX, NIFTY50, BANKNIFTY)
#   - Sectors (Banking, IT, Auto, etc.)
# 
# Priority is important: Specific matches (longer phrases) override generic ones
# This prevents false positives like "axis bank" triggering "bank" sector filter
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
        
    Note:
        Uses longest match to prioritize specific phrases over generic ones.
        Example: "market cap" (9 chars) wins over "market" (6 chars)
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
        "bank nifty" -> "NIFTY BANK"
        
    Note:
        Uses longest match to avoid false positives.
        Example: "nifty bank" (10 chars) wins over "nifty" (5 chars)
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
    
    Logic: If there's a specific word (non-article, non-modifier) before the sector keyword
    in a short query, it's likely a company name.
    
    Args:
        text_lower: Lowercase normalized user query
        original_text: Original user query (preserves capitalization)
        
    Returns:
        Sector name string (e.g., "Banking", "IT", "Automobile")
        Returns None if no sector detected or likely company name
        
    Examples:
        "banking stocks" -> "Banking" (sector filter)
        "axis bank" -> None (company name, not sector)
        "it sector high pe" -> "IT" (sector filter)
        "bajaj auto" -> None (company name, not sector)
        
    Note:
        Uses context analysis to distinguish sector filters from company names.
        Short queries with specific words before sector keywords are treated as company searches.
    """
    
    # Words that indicate a sector/listing query rather than a company name
    sector_modifiers = {
        "all", "top", "best", "good", "leading", "major", "large", "small",
        "show", "list", "give", "find", "get", "see", "view",
        "sector", "industry", "companies", "stocks", "shares",
        "nifty", "index"
    }
    
    tokens = text_lower.split()
    listing_keywords = ["stocks", "companies", "list", "show", "sector", "all", "in", "please", "me"]
    has_listing_context = any(kw in text_lower for kw in listing_keywords)
    
    # For short queries (2-3 words) without listing context
    if len(tokens) <= 3 and not has_listing_context:
        # Check if there's a word before the sector keyword
        for phrase, sector in SECTOR_ALIASES.items():
            if phrase in text_lower:
                phrase_words = phrase.split()
                sector_keyword = phrase_words[-1]  # e.g., "bank", "auto", "energy"
                
                # Find the position of sector keyword in the tokens
                try:
                    keyword_index = tokens.index(sector_keyword)
                    # If there's a preceding word that's not a modifier
                    if keyword_index > 0:
                        preceding_word = tokens[keyword_index - 1]
                        # If preceding word is not a sector modifier, it's likely a company name
                        if preceding_word not in sector_modifiers and len(preceding_word) > 2:
                            return None
                except ValueError:
                    # Sector keyword not found as separate token, continue
                    pass
    
    best = None
    for phrase, sector in SECTOR_ALIASES.items():
        if phrase in text_lower:
            if best is None or len(phrase) > len(best["phrase"]):
                best = {"phrase": phrase, "sector": sector}
    return best["sector"] if best else None


def detect_metric_filter(text_lower: str) -> Optional[Dict[str, Any]]:
    """
    Detect patterns like:
      'pe more than 10'
      'pe > 10'
      'dividend yield under 2'
    Return dict with {metric, op, value} or None.
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

    metric_phrase_norm = metric_phrase.strip().replace("  ", " ")
    metric_col = METRIC_ALIASES.get(metric_phrase_norm)
    if not metric_col:
        return None

    comp_norm = comp_phrase.strip()
    op = COMPARATOR_ALIASES.get(comp_norm)
    if not op:
        if comp_norm in (">", "<", ">=", "<="):
            op_map = {">": "gt", "<": "lt", ">=": "ge", "<=": "le"}
            op = op_map[comp_norm]
        else:
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
    Heuristic: remove metric phrase + stopwords, treat remaining text as stock query.
    Preserves company names even if they contain sector keywords (e.g., 'axis bank', 'bajaj auto').
    """
    tokens = re.findall(r"[a-zA-Z0-9&.\-]+", text_lower)
    if metric_info:
        metric_tokens = metric_info["phrase"].split()
    else:
        metric_tokens = []

    # Extended stopwords - but don't remove sector words if they're part of a stock name
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
# This is the CORE ROUTING LOGIC that determines query mode and parameters.
# 
# PRIORITY ORDER (CRITICAL - DO NOT CHANGE):
#   1. Index + Metric filter (e.g., "nifty 50 stocks with pe less than 50")
#   2. Index + Sector (e.g., "sensex banking stocks")
#   3. Sector + Metric filter (e.g., "it stocks with pe more than 40")
#   4. Index only (e.g., "nifty 50")
#   5. Sector only (e.g., "banking stocks")
#   6. Single stock metric (e.g., "pe of reliance")
#   7. Single stock overview (e.g., "infosys")
# 
# The order matters because more specific queries should match before generic ones.
# For example: "nifty bank stocks with high pe" should trigger mode #1 (index + metric)
# not mode #6 (single stock) even though "bank" could be a company name.
# ============================================================

def parse_user_query(user_input: str) -> Dict[str, Any]:
    """
    Core router: Analyze user input and determine query mode with parameters.
    
    This is the most important function in the application - it interprets natural
    language queries and converts them into structured search specifications.
    
    Args:
        user_input: Raw user query string (e.g., "pe of infy", "nifty 50 banking stocks")
        
    Returns:
        Dictionary with query specification containing:
            - "mode": Query type (single_stock_metric, list_by_index, etc.)
            - Other fields depend on mode:
                * stock_query: Company name for single stock queries
                * metric: Column name for metric queries
                * index_code: Index filter (SENSEX, NIFTY 50, etc.)
                * sector: Sector filter (Banking, IT, etc.)
                * metric_filter: Range filter {metric, op, value}
    
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
    sector = detect_sector(text_lower, original)  # Pass original text for capitalization check
    metric_filter = detect_metric_filter(text_lower)

    # 1) Index + Metric filter combination (e.g., "nifty 50 stocks with pe less than 50")
    # Check index first as it takes priority over sector
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

    # 2) Sector + Metric filter combination (e.g., "healthcare stocks with pe less than 50")
    if sector is not None and metric_filter is not None:
        listing_keywords = ["stocks", "companies", "list", "show", "all", "in"]
        has_listing_context = any(kw in text_lower for kw in listing_keywords) or "sector" in text_lower
        
        potential_stock = extract_stock_query(original, text_lower, metric_info)
        is_likely_sector_query = has_listing_context or not potential_stock or len(text_lower.split()) <= 3
        
        if is_likely_sector_query:
            return {
                "mode": "list_by_sector_with_filter",
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

    # 3) No metric filter but an index detected => list_by_index
    # Check index BEFORE sector to give index priority
    if index_code and metric_info is None:
        return {
            "mode": "list_by_index",
            "index_code": index_code,
            "metric_filter": None,
            "raw": {"input": original}
        }

    # 4) Sector-based listing without filter (e.g., "Healthcare companies")
    if sector is not None:
        listing_keywords = ["stocks", "companies", "list", "show", "all", "in"]
        has_listing_context = any(kw in text_lower for kw in listing_keywords) or "sector" in text_lower
        
        potential_stock = extract_stock_query(original, text_lower, metric_info)
        is_likely_sector_query = has_listing_context or not potential_stock or len(text_lower.split()) <= 3
        
        if is_likely_sector_query:
            return {
                "mode": "list_by_sector",
                "sector": sector,
                "raw": {"input": original}
            }

    # 5) Metric filter for many stocks
    if metric_filter is not None:
        return {
            "mode": "list_by_metric_filter",
            "index_code": index_code,  # can be None
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

    # 6) Stock + metric => single_stock_metric
    if metric_info is not None:
        stock_query = extract_stock_query(original, text_lower, metric_info)
        if stock_query:
            return {
                "mode": "single_stock_metric",
                "stock_query": stock_query,
                "metric": metric_info["column"],
                "metric_phrase": metric_info["phrase"],
                "raw": {"input": original}
            }
        # metric but no clear stock: treat as metric filter across universe
        return {
            "mode": "list_by_metric_filter",
            "index_code": index_code,
            "metric_filter": {
                "metric": metric_info["column"],
                "op": None,
                "value": None
            },
            "raw": {"input": original}
        }

    # 7) No metric, no index => assume single stock overview
    stock_query = extract_stock_query(original, text_lower, None)
    return {
        "mode": "single_stock_overview",
        "stock_query": stock_query or original,
        "raw": {"input": original}
    }


# ============================================================
# Azure AI Search: spec -> HTTP request
# ============================================================

def _build_metric_filter_odata(metric_filter: Dict[str, Any]) -> Optional[str]:
    """
    Convert {"metric": "PE", "op": "lt", "value": 20.0}
    into OData: "PE lt 20"
    """
    if not metric_filter:
        return None
    metric = metric_filter.get("metric")
    op = metric_filter.get("op")
    value = metric_filter.get("value")
    if not metric or not op or value is None:
        return None

    # op already mapped to lt/gt/le/ge
    if op not in ("lt", "gt", "le", "ge"):
        return None

    return f"{metric} {op} {value}"


def build_search_payload_from_spec(spec: Dict[str, Any]) -> Dict[str, Any]:
    """
    From the parsed spec, build the JSON body for the Search REST API.
    Does NOT include URL or headers.
    """
    mode = spec["mode"]

    # Common baseline select set for overviews
    overview_select = "Symbol,SymbolRaw,Name,Sector,MarketCapCr,PE,PB,EPS,DividendYieldPct,AllIndices"

    if mode == "single_stock_metric":
        metric = spec["metric"]
        # Build minimal select: essential fields + requested metric
        essential_fields = ["SymbolRaw", "Name", "Symbol"]
        if metric not in essential_fields:
            essential_fields.append(metric)
        select_fields = ",".join(essential_fields)
        
        payload = {
            "search": spec["stock_query"],
            "searchFields": "SymbolRaw,Name,Symbol",
            "top": 1,
            "select": select_fields
        }
        return payload

    if mode == "single_stock_overview":
        payload = {
            "search": spec["stock_query"],
            "searchFields": "SymbolRaw,Name,Symbol",
            "top": 1,
            "select": overview_select
        }
        return payload

    if mode == "list_by_index":
        index_code = spec.get("index_code")
        filter_clauses = []
        if index_code:
            filter_clauses.append(f"AllIndices/any(i: i eq '{index_code}')")
        filter_str = " and ".join(filter_clauses) if filter_clauses else None

        payload: Dict[str, Any] = {
            "search": "*",
            "top": 50,
            "select": overview_select,
            "count": True
        }
        if filter_str:
            payload["filter"] = filter_str
        return payload

    if mode == "list_by_sector":
        sector = spec.get("sector")
        filter_str = f"Sector eq '{sector}'" if sector else None

        payload: Dict[str, Any] = {
            "search": "*",
            "top": 50,
            "select": overview_select,
            "count": True
        }
        if filter_str:
            payload["filter"] = filter_str
        return payload

    if mode == "list_by_sector_with_filter":
        sector = spec.get("sector")
        metric_filter = spec.get("metric_filter")
        
        filter_clauses = []
        if sector:
            filter_clauses.append(f"Sector eq '{sector}'")
        
        metric_odata = _build_metric_filter_odata(metric_filter)
        if metric_odata:
            filter_clauses.append(metric_odata)
        
        filter_str = " and ".join(filter_clauses) if filter_clauses else None
        
        # Build select clause with essential fields + filtered metric
        select_fields = ["SymbolRaw", "Name", "Symbol", "Sector"]
        if metric_filter and metric_filter.get("metric"):
            metric_name = metric_filter["metric"]
            if metric_name not in select_fields:
                select_fields.append(metric_name)
        sel = ",".join(select_fields)
        
        payload: Dict[str, Any] = {
            "search": "*",
            "top": 50,
            "select": sel,
            "count": True
        }
        if filter_str:
            payload["filter"] = filter_str
        return payload

    if mode == "list_by_metric_filter":
        index_code = spec.get("index_code")
        metric_filter = spec.get("metric_filter")

        filter_clauses = []

        if index_code:
            filter_clauses.append(f"AllIndices/any(i: i eq '{index_code}')")

        metric_odata = _build_metric_filter_odata(metric_filter)
        if metric_odata:
            filter_clauses.append(metric_odata)

        filter_str = " and ".join(filter_clauses) if filter_clauses else None

        # Build select clause with essential fields + filtered metric
        select_fields = ["SymbolRaw", "Name", "Symbol", "Sector"]
        if metric_filter and metric_filter.get("metric"):
            metric_name = metric_filter["metric"]
            if metric_name not in select_fields:
                select_fields.append(metric_name)
        if index_code:
            select_fields.append("AllIndices")
        sel = ",".join(select_fields)
        
        payload: Dict[str, Any] = {
            "search": "*",
            "top": 50,
            "select": sel,
            "count": True
        }
        if filter_str:
            payload["filter"] = filter_str
        return payload

    # Fallback: treat as overview search
    return {
        "search": spec.get("stock_query") or spec["raw"]["input"],
        "searchFields": "SymbolRaw,Name,Symbol",
        "top": 1,
        "select": overview_select
    }


def build_search_request_from_user_input(
    user_input: str,
    service_endpoint: str,
    index_name: str,
    api_key: str,
    api_version: str = "2025-09-01"
) -> Dict[str, Any]:
    """
    End-to-end helper:
    - parses user input -> spec
    - builds HTTP method, URL, headers, JSON payload

    Returns dict:
    {
      "spec": {...},
      "method": "POST",
      "url": "...",
      "headers": {...},
      "json": {...}
    }
    """
    spec = parse_user_query(user_input)
    payload = build_search_payload_from_spec(spec)

    # Ensure no trailing slash duplication
    service_endpoint = service_endpoint.rstrip("/")
    url = f"{service_endpoint}/indexes/{index_name}/docs/search?api-version={api_version}"

    headers = {
        "Content-Type": "application/json",
        "api-key": api_key
    }

    return {
        "spec": spec,
        "method": "POST",
        "url": url,
        "headers": headers,
        "json": payload
    }


# ============================================================
# Small demo / examples
# ============================================================

if __name__ == "__main__":
    # Load configuration from environment variables
    SERVICE_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
    INDEX_NAME = os.getenv("AZURE_SEARCH_INDEX_NAME")
    API_KEY = os.getenv("AZURE_SEARCH_API_KEY")

    # Validate required environment variables
    if not SERVICE_ENDPOINT or not INDEX_NAME or not API_KEY:
        print("❌ Error: Missing required environment variables")
        print("Please ensure the following are set in your .env file:")
        print("  - AZURE_SEARCH_ENDPOINT")
        print("  - AZURE_SEARCH_INDEX_NAME")
        print("  - AZURE_SEARCH_API_KEY")
        exit(1)

    print("=== Azure AI Search Stock Query Interface ===")
    print("Type your query or 'exit' to quit\n")
    
    
    # test_queries = [
    #     "Infy PE",
    #     "PE of M&M",
    #     "Show HDFC Bank",
    #     "Nifty 50 stocks",
    #     "IT stocks with PE under 20",
    #     "NIFTYBANK constituents",
    #     "All stocks with PE more than 10"
    # ]

    while True:
        # Get user input
        try:
            user_query = input("Enter your query: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\nExiting...")
            break

        # Check for exit command
        if user_query.lower() in ['exit', 'quit', 'q']:
            print("Exiting...")
            break

        # Skip empty queries
        if not user_query:
            continue

        print("\n==============================")
        print("User query:", user_query)

        # Timestamp 1: Input received
        t1_input_received = time.time()
        print(f"[TIMESTAMP] Input received at: {t1_input_received:.6f}")

        try:
            req = build_search_request_from_user_input(
                user_query,
                service_endpoint=SERVICE_ENDPOINT,
                index_name=INDEX_NAME,
                api_key=API_KEY
            )

            # Log what we're sending
            print("Spec:", req["spec"])
            print("HTTP method:", req["method"])
            print("URL:", req["url"])
            print("Payload JSON:", json.dumps(req["json"], indent=2))

            # Timestamp 2: Before Azure AI Search call
            t2_before_search = time.time()
            print(f"[TIMESTAMP] Calling Azure AI Search at: {t2_before_search:.6f}")

            # 🔹 Call Azure AI Search
            result = execute_search_request(req)

            # Timestamp 3: After receiving response
            t3_response_received = time.time()
            print(f"[TIMESTAMP] Response received at: {t3_response_received:.6f}")

            print("Status code:", result["status_code"])
            print("Response JSON:")
            print(json.dumps(result["response"], indent=2))

            # Calculate time breakdowns in milliseconds
            time_parsing_ms = (t2_before_search - t1_input_received) * 1000
            time_search_ms = (t3_response_received - t2_before_search) * 1000
            time_total_ms = (t3_response_received - t1_input_received) * 1000

            print("\n[PERFORMANCE BREAKDOWN]")
            print(f"  1. Input processing & request building: {time_parsing_ms:.2f} ms")
            print(f"  2. Azure AI Search call (network + processing): {time_search_ms:.2f} ms")
            print(f"  3. Total time: {time_total_ms:.2f} ms")
            print("\n")

        except Exception as e:
            print(f"\n❌ Error processing query: {e}")
            print("Please try again.\n")
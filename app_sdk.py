import re
from typing import Dict, Any, Optional, List
import time
import os
from dotenv import load_dotenv

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import QueryType
import json

# Load environment variables from .env file
load_dotenv()

# ============================================================
# Azure Search SDK Client - Singleton Pattern
# ============================================================
# The SDK automatically handles connection pooling internally,
# so we use a singleton pattern to reuse the same SearchClient
# instance across all requests.
# 
# Performance Benefits:
#   - Automatic connection pooling (managed by SDK)
#   - No manual session management needed
#   - Similar performance to REST API with requests.Session()
# 
# Advantages over REST API:
#   - Type-safe: IntelliSense and compile-time validation
#   - Pythonic: Idiomatic Python patterns and error handling
#   - Auto-retry: Built-in retry logic for transient failures
#   - Maintained: Official SDK updated by Microsoft
# ============================================================

SERVICE_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
INDEX_NAME = os.getenv("AZURE_SEARCH_INDEX_NAME")
API_KEY = os.getenv("AZURE_SEARCH_API_KEY")

_search_client = None

def get_search_client() -> SearchClient:
    """
    Get or create the Azure Search client (singleton pattern).
    
    This function ensures only one SearchClient instance is created and reused
    across all search operations. The SDK manages connection pooling internally.
    
    Returns:
        SearchClient: Configured Azure Search client for the specified index
        
    Note:
        The client is created lazily on first call and cached for subsequent calls.
        This pattern provides automatic connection pooling without manual session management.
    """
    global _search_client
    if _search_client is None:
        credential = AzureKeyCredential(API_KEY)
        _search_client = SearchClient(
            endpoint=SERVICE_ENDPOINT,
            index_name=INDEX_NAME,
            credential=credential
        )
    return _search_client


def execute_search_request_sdk(spec: dict, search_text: str = "*", 
                                filter_expr: Optional[str] = None,
                                select_fields: Optional[List[str]] = None,
                                top: int = 50,
                                include_total_count: bool = True) -> dict:
    """
    Execute Azure Search query using Python SDK with automatic connection pooling.
    
    This is the SDK equivalent of app.py's execute_search_request() function.
    It provides a Pythonic interface with type safety and built-in error handling.
    
    Args:
        spec: Query specification dict (for context/debugging, not used in SDK call)
        search_text: Search query text (default "*" for match-all)
        filter_expr: OData filter expression (e.g., "Index_Code eq 'NIFTY 50'")
        select_fields: List of field names to return (e.g., ["Stock_Name", "PE_Ratio"])
        top: Maximum number of results to return (default 50)
        include_total_count: Whether to include @odata.count in response (default True)
    
    Returns:
        Dictionary with search results in REST API-compatible format:
        {
            "@odata.count": <total_count>,
            "value": [
                {"Stock_Name": "...", "PE_Ratio": ..., ...},
                ...
            ]
        }
        
    SDK Advantages:
        - Type-safe: IntelliSense support and compile-time checks
        - Pythonic: Native Python objects instead of raw JSON dicts
        - Auto-retry: Built-in retry logic for transient network failures
        - Connection pooling: Automatically managed by SDK (no manual session)
        
    Performance:
        Similar to REST API with requests.Session() due to SDK's internal connection pooling.
        First request: ~700-800ms (connection setup)
        Subsequent: ~160-350ms (connection reuse)
        
    Note:
        Results are converted from SDK's SearchItemPaged iterator to REST API format
        for compatibility with existing UI code (streamlit_app.py).
    """
    client = get_search_client()
    
    try:
        # Execute search
        results = client.search(
            search_text=search_text,
            filter=filter_expr,
            select=select_fields,
            top=top,
            include_total_count=include_total_count
        )
        
        # Convert results to list and extract total count
        results_list = list(results)
        total_count = results.get_count() if include_total_count else None
        
        # Format response to match REST API structure
        response_data = {
            "@odata.context": f"{SERVICE_ENDPOINT}/indexes('{INDEX_NAME}')/$metadata#docs(*)",
            "value": results_list
        }
        
        if total_count is not None:
            response_data["@odata.count"] = total_count
        
        return {
            "status_code": 200,
            "spec": spec,
            "request_payload": {
                "search": search_text,
                "filter": filter_expr,
                "select": ",".join(select_fields) if select_fields else None,
                "top": top,
                "count": include_total_count
            },
            "response": response_data
        }
        
    except Exception as e:
        return {
            "status_code": 500,
            "spec": spec,
            "request_payload": {},
            "response": {
                "error": {
                    "message": str(e)
                }
            }
        }


# ============================================================
# Config: metrics, indices, comparators (same as app.py)
# ============================================================

METRIC_ALIASES = {
    "pe": "PE",
    "p/e": "PE",
    "p e": "PE",
    "pb": "PB",
    "p/b": "PB",
    "p b": "PB",
    "price to book": "PB",
    "price": "PRICE",
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
# Detection helpers (same as app.py)
# ============================================================

def detect_metric(text_lower: str) -> Optional[Dict[str, Any]]:
    """Return dict with metric_name & matched_phrase, or None."""
    best = None
    for phrase, col in METRIC_ALIASES.items():
        if phrase in text_lower:
            if best is None or len(phrase) > len(best["phrase"]):
                best = {"phrase": phrase, "column": col}
    return best


def detect_index_code(text_lower: str) -> Optional[str]:
    """Detect index from user input. Use longest match to avoid false positives."""
    best = None
    for phrase, code in INDEX_ALIASES.items():
        if phrase in text_lower:
            if best is None or len(phrase) > len(best["phrase"]):
                best = {"phrase": phrase, "code": code}
    return best["code"] if best else None


def detect_sector(text_lower: str, original_text: str) -> Optional[str]:
    """Detect sector from user input. Return sector name or None."""
    
    sector_modifiers = {
        "all", "top", "best", "good", "leading", "major", "large", "small",
        "show", "list", "give", "find", "get", "see", "view",
        "sector", "industry", "companies", "stocks", "shares",
        "nifty", "index"
    }
    
    tokens = text_lower.split()
    listing_keywords = ["stocks", "companies", "list", "show", "sector", "all", "in", "please", "me"]
    has_listing_context = any(kw in text_lower for kw in listing_keywords)
    
    if len(tokens) <= 3 and not has_listing_context:
        for phrase, sector in SECTOR_ALIASES.items():
            if phrase in text_lower:
                phrase_words = phrase.split()
                sector_keyword = phrase_words[-1]
                
                try:
                    keyword_index = tokens.index(sector_keyword)
                    if keyword_index > 0:
                        preceding_word = tokens[keyword_index - 1]
                        if preceding_word not in sector_modifiers and len(preceding_word) > 2:
                            return None
                except ValueError:
                    pass
    
    best = None
    for phrase, sector in SECTOR_ALIASES.items():
        if phrase in text_lower:
            if best is None or len(phrase) > len(best["phrase"]):
                best = {"phrase": phrase, "sector": sector}
    return best["sector"] if best else None


def detect_metric_filter(text_lower: str) -> Optional[Dict[str, Any]]:
    """Detect patterns like 'pe more than 10', 'pe > 10', etc."""
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
    """Extract stock query from user input."""
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
# Main query parsing: same as app.py
# ============================================================

def parse_user_query(user_input: str) -> Dict[str, Any]:
    """Parse user input into query specification."""
    original = user_input
    text_lower = normalize(user_input)

    metric_info = detect_metric(text_lower)
    index_code = detect_index_code(text_lower)
    sector = detect_sector(text_lower, original)
    metric_filter = detect_metric_filter(text_lower)

    # 1) Index + Metric filter
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

    # 2) Sector + Metric filter
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

    # 3) Index without filter
    if index_code and metric_info is None:
        return {
            "mode": "list_by_index",
            "index_code": index_code,
            "metric_filter": None,
            "raw": {"input": original}
        }

    # 4) Sector-based listing
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

    # 5) Metric filter
    if metric_filter is not None:
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

    # 6) Stock + metric
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

    # 7) Single stock overview
    stock_query = extract_stock_query(original, text_lower, None)
    return {
        "mode": "single_stock_overview",
        "stock_query": stock_query or original,
        "raw": {"input": original}
    }


# ============================================================
# Azure AI Search: spec -> SDK parameters
# ============================================================

def _build_metric_filter_odata(metric_filter: Dict[str, Any]) -> Optional[str]:
    """Convert metric filter to OData expression."""
    if not metric_filter:
        return None
    metric = metric_filter.get("metric")
    op = metric_filter.get("op")
    value = metric_filter.get("value")
    if not metric or not op or value is None:
        return None

    if op not in ("lt", "gt", "le", "ge"):
        return None

    return f"{metric} {op} {value}"


def build_search_request_from_user_input_sdk(user_input: str) -> Dict[str, Any]:
    """
    End-to-end helper for SDK:
    - Parses user input -> spec
    - Builds SDK parameters
    
    Returns dict with spec and SDK parameters.
    """
    spec = parse_user_query(user_input)
    mode = spec["mode"]

    # Default parameters
    search_text = "*"
    filter_expr = None
    select_fields = None
    top = 50
    include_total_count = True

    # Common overview fields
    overview_fields = ["Symbol", "SymbolRaw", "Name", "Sector", "MarketCapCr", 
                      "PE", "PB", "EPS", "DividendYieldPct", "AllIndices"]

    if mode == "single_stock_metric":
        metric = spec["metric"]
        essential_fields = ["SymbolRaw", "Name", "Symbol"]
        if metric not in essential_fields:
            essential_fields.append(metric)
        
        search_text = spec["stock_query"]
        select_fields = essential_fields
        top = 1

    elif mode == "single_stock_overview":
        search_text = spec["stock_query"]
        select_fields = overview_fields
        top = 1

    elif mode == "list_by_index":
        index_code = spec.get("index_code")
        if index_code:
            filter_expr = f"AllIndices/any(i: i eq '{index_code}')"
        select_fields = overview_fields

    elif mode == "list_by_sector":
        sector = spec.get("sector")
        if sector:
            filter_expr = f"Sector eq '{sector}'"
        select_fields = overview_fields

    elif mode == "list_by_sector_with_filter":
        sector = spec.get("sector")
        metric_filter = spec.get("metric_filter")
        
        filter_clauses = []
        if sector:
            filter_clauses.append(f"Sector eq '{sector}'")
        
        metric_odata = _build_metric_filter_odata(metric_filter)
        if metric_odata:
            filter_clauses.append(metric_odata)
        
        filter_expr = " and ".join(filter_clauses) if filter_clauses else None
        
        select_fields = ["SymbolRaw", "Name", "Symbol", "Sector"]
        if metric_filter and metric_filter.get("metric"):
            metric_name = metric_filter["metric"]
            if metric_name not in select_fields:
                select_fields.append(metric_name)

    elif mode == "list_by_metric_filter":
        index_code = spec.get("index_code")
        metric_filter = spec.get("metric_filter")

        filter_clauses = []
        if index_code:
            filter_clauses.append(f"AllIndices/any(i: i eq '{index_code}')")

        metric_odata = _build_metric_filter_odata(metric_filter)
        if metric_odata:
            filter_clauses.append(metric_odata)

        filter_expr = " and ".join(filter_clauses) if filter_clauses else None

        select_fields = ["SymbolRaw", "Name", "Symbol", "Sector"]
        if metric_filter and metric_filter.get("metric"):
            metric_name = metric_filter["metric"]
            if metric_name not in select_fields:
                select_fields.append(metric_name)
        if index_code:
            select_fields.append("AllIndices")

    else:
        # Fallback
        search_text = spec.get("stock_query") or spec["raw"]["input"]
        select_fields = overview_fields
        top = 1

    return {
        "spec": spec,
        "search_text": search_text,
        "filter_expr": filter_expr,
        "select_fields": select_fields,
        "top": top,
        "include_total_count": include_total_count
    }


# ============================================================
# Main execution wrapper
# ============================================================

def execute_search_from_user_input_sdk(user_input: str) -> dict:
    """
    Complete wrapper: parse user input and execute search using SDK.
    
    Args:
        user_input: Natural language query
    
    Returns:
        Search results dict matching REST API format
    """
    params = build_search_request_from_user_input_sdk(user_input)
    
    result = execute_search_request_sdk(
        spec=params["spec"],
        search_text=params["search_text"],
        filter_expr=params["filter_expr"],
        select_fields=params["select_fields"],
        top=params["top"],
        include_total_count=params["include_total_count"]
    )
    
    return result


# ============================================================
# Demo / Console Interface
# ============================================================

if __name__ == "__main__":
    if not SERVICE_ENDPOINT or not INDEX_NAME or not API_KEY:
        print("❌ Error: Missing required environment variables")
        print("Please ensure the following are set in your .env file:")
        print("  - AZURE_SEARCH_ENDPOINT")
        print("  - AZURE_SEARCH_INDEX_NAME")
        print("  - AZURE_SEARCH_API_KEY")
        exit(1)

    print("=== Azure AI Search Stock Query Interface (SDK Version) ===")
    print("Type your query or 'exit' to quit\n")

    while True:
        try:
            user_query = input("Enter your query: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\nExiting...")
            break

        if user_query.lower() in ['exit', 'quit', 'q']:
            print("Exiting...")
            break

        if not user_query:
            continue

        print("\n==============================")
        print("User query:", user_query)

        t1_input_received = time.time()
        print(f"[TIMESTAMP] Input received at: {t1_input_received:.6f}")

        try:
            params = build_search_request_from_user_input_sdk(user_query)
            
            print("Spec:", params["spec"])
            print("Search text:", params["search_text"])
            print("Filter:", params["filter_expr"])
            print("Select fields:", params["select_fields"])
            print("Top:", params["top"])

            t2_before_search = time.time()
            print(f"[TIMESTAMP] Calling Azure AI Search at: {t2_before_search:.6f}")

            result = execute_search_request_sdk(
                spec=params["spec"],
                search_text=params["search_text"],
                filter_expr=params["filter_expr"],
                select_fields=params["select_fields"],
                top=params["top"],
                include_total_count=params["include_total_count"]
            )

            t3_response_received = time.time()
            print(f"[TIMESTAMP] Response received at: {t3_response_received:.6f}")

            print("Status code:", result["status_code"])
            print("Response JSON:")
            print(json.dumps(result["response"], indent=2, default=str))

            time_parsing_ms = (t2_before_search - t1_input_received) * 1000
            time_search_ms = (t3_response_received - t2_before_search) * 1000
            time_total_ms = (t3_response_received - t1_input_received) * 1000

            print("\n[PERFORMANCE BREAKDOWN]")
            print(f"  1. Input processing & request building: {time_parsing_ms:.2f} ms")
            print(f"  2. Azure AI Search call (SDK): {time_search_ms:.2f} ms")
            print(f"  3. Total time: {time_total_ms:.2f} ms")
            print("\n")

        except Exception as e:
            print(f"\n❌ Error processing query: {e}")
            print("Please try again.\n")

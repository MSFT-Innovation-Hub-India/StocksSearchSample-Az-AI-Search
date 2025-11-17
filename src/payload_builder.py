"""
Azure Search payload builder module.

Converts parsed query specifications into Azure Search REST API payloads.
This module is shared across app.py and app_sdk.py to avoid code duplication.
"""

from typing import Dict, Any, Optional


def build_metric_filter_odata(metric_filter: Dict[str, Any]) -> Optional[str]:
    """
    Convert metric filter to OData expression.
    
    Args:
        metric_filter: Dictionary with {"metric": "PE", "op": "lt", "value": 20.0}
        
    Returns:
        OData filter string like "PE lt 20" or None if invalid
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
    Build Azure Search REST API JSON payload from parsed query specification.
    
    Args:
        spec: Query specification from query_parser.parse_user_query()
        
    Returns:
        Dictionary with search, filter, select, top, count parameters for Azure Search API
        
    Note:
        This function only builds the JSON body - it does NOT include URL or headers.
        Those are added by the caller (app.py or app_sdk.py).
    """
    mode = spec["mode"]

    # Common baseline select set for overviews
    overview_select = "Symbol,SymbolRaw,Name,Sector,MarketCapCr,PE,PB,EPS,DividendYieldPct,AllIndices"

    # 1) Single stock metric query (e.g., "pe of reliance")
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

    # 2) Single stock overview (e.g., "infosys")
    if mode == "single_stock_overview":
        payload = {
            "search": spec["stock_query"],
            "searchFields": "SymbolRaw,Name,Symbol",
            "top": 1,
            "select": overview_select
        }
        return payload

    # 3) List by index (e.g., "nifty 50")
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

    # 4) List by sector (e.g., "banking stocks")
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

    # 5) Index + Sector combination (e.g., "nifty 50 banking stocks")
    if mode == "list_by_index_and_sector":
        index_code = spec.get("index_code")
        sector = spec.get("sector")
        
        filter_clauses = []
        if index_code:
            filter_clauses.append(f"AllIndices/any(i: i eq '{index_code}')")
        if sector:
            filter_clauses.append(f"Sector eq '{sector}'")
        
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

    # 6) Sector + Metric filter (e.g., "it stocks with pe more than 40")
    if mode == "list_by_sector_and_metric_filter":
        sector = spec.get("sector")
        metric_filter = spec.get("metric_filter")
        
        filter_clauses = []
        if sector:
            filter_clauses.append(f"Sector eq '{sector}'")
        
        metric_odata = build_metric_filter_odata(metric_filter)
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

    # 7) Metric filter (with or without index) (e.g., "stocks with pe less than 20" or "nifty 50 stocks with pe less than 50")
    if mode == "list_by_metric_filter":
        index_code = spec.get("index_code")
        metric_filter = spec.get("metric_filter")

        filter_clauses = []

        if index_code:
            filter_clauses.append(f"AllIndices/any(i: i eq '{index_code}')")

        metric_odata = build_metric_filter_odata(metric_filter)
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

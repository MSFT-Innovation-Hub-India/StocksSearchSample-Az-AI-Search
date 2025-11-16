import re
from typing import Dict, Any, Optional, List
import time
import os
from dotenv import load_dotenv

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import QueryType
import json

# Import shared modules
from query_parser import parse_user_query
from payload_builder import build_search_payload_from_spec

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
        
        # Convert SDK results to REST API format
        items = []
        for item in results:
            items.append(dict(item))
        
        response = {
            "value": items
        }
        
        # Add count if available
        if include_total_count and hasattr(results, 'get_count'):
            try:
                response["@odata.count"] = results.get_count()
            except:
                pass
        
        return {
            "status_code": 200,
            "spec": spec,
            "response": response
        }
        
    except Exception as e:
        return {
            "status_code": 500,
            "spec": spec,
            "response": {
                "error": {
                    "message": str(e),
                    "type": type(e).__name__
                }
            }
        }


def build_search_request_from_user_input_sdk(
    user_input: str,
    service_endpoint: str = None,
    index_name: str = None,
    api_key: str = None
) -> Dict[str, Any]:
    """
    SDK version: Parse user input and convert to SDK search parameters.
    
    This function orchestrates the query processing pipeline for SDK-based searches:
    1. Parses user input into structured spec (via query_parser module)
    2. Builds Azure Search parameters (via payload_builder module)
    3. Converts REST API format to SDK parameters
    
    Args:
        user_input: Natural language query (e.g., "pe of reliance", "nifty 50")
        service_endpoint: Not used (SDK uses global config), kept for API compatibility
        index_name: Not used (SDK uses global config), kept for API compatibility
        api_key: Not used (SDK uses global config), kept for API compatibility
        
    Returns:
        Dictionary containing:
            - "spec": Parsed query specification
            - "search_text": Search query text for SDK
            - "filter": OData filter expression
            - "select": List of fields to return
            - "top": Number of results
            - "include_total_count": Whether to include count
            
    Note:
        This is the main entry point for SDK-based searches.
        Pass the returned dict to execute_search_from_user_input_sdk() to execute the query.
    """
    # Use shared modules for parsing and payload building
    spec = parse_user_query(user_input)
    payload = build_search_payload_from_spec(spec)
    
    # Convert REST API payload to SDK parameters
    search_text = payload.get("search", "*")
    filter_expr = payload.get("filter")
    select_str = payload.get("select", "")
    select_fields = [f.strip() for f in select_str.split(",")] if select_str else None
    top = payload.get("top", 50)
    include_total_count = payload.get("count", False)
    
    return {
        "spec": spec,
        "search_text": search_text,
        "filter": filter_expr,
        "select": select_fields,
        "top": top,
        "include_total_count": include_total_count
    }


def execute_search_from_user_input_sdk(user_input: str) -> dict:
    """
    Complete SDK workflow: user input -> search results.
    
    This is a convenience function that combines:
    1. build_search_request_from_user_input_sdk() - parse and build params
    2. execute_search_request_sdk() - execute search with SDK
    
    Args:
        user_input: Natural language query (e.g., "pe of reliance", "nifty 50")
        
    Returns:
        Dictionary with search results in REST API-compatible format
        
    Note:
        This is the simplest way to use the SDK version - just pass a query string
        and get back results. All configuration comes from environment variables.
    """
    req = build_search_request_from_user_input_sdk(user_input)
    return execute_search_request_sdk(
        spec=req["spec"],
        search_text=req["search_text"],
        filter_expr=req["filter"],
        select_fields=req["select"],
        top=req["top"],
        include_total_count=req["include_total_count"]
    )


# ============================================================
# Small demo / examples
# ============================================================

if __name__ == "__main__":
    # Validate required environment variables
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
            # Build request
            req = build_search_request_from_user_input_sdk(user_query)

            # Log what we're sending
            print("Spec:", req["spec"])
            print("Search text:", req["search_text"])
            print("Filter:", req["filter"])
            print("Select:", req["select"])
            print("Top:", req["top"])

            # Timestamp 2: Before Azure AI Search call
            t2_before_search = time.time()
            print(f"[TIMESTAMP] Calling Azure AI Search at: {t2_before_search:.6f}")

            # Execute search
            result = execute_search_request_sdk(
                spec=req["spec"],
                search_text=req["search_text"],
                filter_expr=req["filter"],
                select_fields=req["select"],
                top=req["top"],
                include_total_count=req["include_total_count"]
            )

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

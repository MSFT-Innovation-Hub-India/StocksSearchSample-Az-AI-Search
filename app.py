import re
from typing import Dict, Any, Optional
import time
import os
from dotenv import load_dotenv

import requests
import json

# Import shared modules
from query_parser import parse_user_query
from payload_builder import build_search_payload_from_spec

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
# High-level API function: user input -> HTTP request
# ============================================================

def build_search_request_from_user_input(
    user_input: str,
    service_endpoint: str,
    index_name: str,
    api_key: str,
    api_version: str = "2025-09-01"
) -> Dict[str, Any]:
    """
    End-to-end helper function: converts user input to complete HTTP request dict.
    
    This function orchestrates the entire query processing pipeline:
    1. Parses user input into structured spec (via query_parser module)
    2. Builds Azure Search JSON payload (via payload_builder module)
    3. Constructs full HTTP request with URL, headers, and body
    
    Args:
        user_input: Natural language query (e.g., "pe of reliance", "nifty 50")
        service_endpoint: Azure Search service endpoint URL
        index_name: Name of the search index to query
        api_key: API key for authentication
        api_version: Azure Search API version (default: "2025-09-01")
        
    Returns:
        Dictionary containing:
            - "spec": Parsed query specification
            - "method": HTTP method ("POST")
            - "url": Complete API endpoint URL
            - "headers": HTTP headers including api-key
            - "json": Request body with search parameters
            
    Note:
        This is the main entry point for REST API-based searches.
        Pass the returned dict to execute_search_request() to execute the query.
    """
    # Use shared modules for parsing and payload building
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

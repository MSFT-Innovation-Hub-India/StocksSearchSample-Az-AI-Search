"""
Stock Search Application - Cosmos DB Integration (search_app_cosmos.py)

This module provides an interactive console application that integrates Azure AI Search
with Azure Cosmos DB for real-time stock data queries.

Capabilities:
1. Accepts natural language queries from users
2. Uses Azure AI Search to resolve stock symbols from company names
3. Parses user intent to identify requested fields (Price, Change, ChangePercent)
4. Queries Azure Cosmos DB for real-time/dynamic stock price data
5. Returns results with detailed performance metrics at each step

Features:
- Natural language processing for field extraction
- Symbol resolution via Azure AI Search
- Dynamic field selection based on user input
- Aggregation support (MIN/MAX for highest/lowest prices)
- Comprehensive performance timing (parsing, search, query, total)
- Interactive console interface with example queries

Architecture:
User Input → Parse Fields → AI Search (resolve symbol) → Parse Query → 
Cosmos DB Query → Return Results with Timing

Usage:
    python search_app_cosmos.py

Example Queries:
    - "What is the price of Reliance?"
    - "Show me price and change for TCS"
    - "What is the highest price for HDFC?"
    - "Get all data for INFY"
"""

import os
import re
import json
import time
from typing import Dict, Any, List, Optional, Tuple
from dotenv import load_dotenv

# Import existing modules
from src.query_parser import parse_user_query
from src.db_parser import get_latest_stock_data, get_stock_aggregation
import requests

# Load environment variables
load_dotenv()

# Configuration
AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
AZURE_SEARCH_INDEX = os.getenv("AZURE_SEARCH_INDEX_NAME", "stocks-search-index")
AZURE_SEARCH_API_KEY = os.getenv("AZURE_SEARCH_API_KEY")

# Load Cosmos DB field configuration
COSMOS_CONFIG_PATH = "config/cosmos_config.json"


class CosmosDynamicQueryApp:
    """
    Interactive application for querying real-time stock data from Cosmos DB.
    
    Integrates Azure AI Search for symbol resolution and natural language processing
    for field extraction and query execution.
    """
    
    def __init__(self):
        """Initialize the application with configuration."""
        self.load_cosmos_config()
        self.session = requests.Session()
        print("\n" + "="*80)
        print("Stock Search Application - Cosmos DB Integration")
        print("search_app_cosmos.py")
        print("="*80)
        print("Initialized successfully!\n")
    
    def load_cosmos_config(self):
        """Load Cosmos DB field configuration from JSON file."""
        try:
            with open(COSMOS_CONFIG_PATH, 'r') as f:
                self.cosmos_config = json.load(f)
            print(f"✓ Loaded Cosmos DB configuration from {COSMOS_CONFIG_PATH}")
        except FileNotFoundError:
            print(f"✗ Warning: {COSMOS_CONFIG_PATH} not found. Using default configuration.")
            self.cosmos_config = {
                "fields": {
                    "Price": {"cosmos_field": "Price", "aliases": ["price"]},
                    "Change": {"cosmos_field": "Change", "aliases": ["change"]},
                    "ChangePercent": {"cosmos_field": "ChangePercent", "aliases": ["change percent", "percentage"]}
                },
                "always_return": ["Symbol", "DateTime"]
            }
    
    def parse_fields_from_query(self, query: str) -> Tuple[List[str], float]:
        """
        Extract requested fields from user query.
        
        Args:
            query (str): User's natural language query
            
        Returns:
            Tuple of (list of field names, parse time in ms)
            
        Example:
            "show me price and change" → ["Price", "Change"]
            "what is the current price" → ["Price"]
            "get all data" → ["Price", "Change", "ChangePercent"]
        """
        start_time = time.time()
        query_lower = query.lower()
        
        requested_fields = []
        
        # Check each field's aliases
        for field_name, field_config in self.cosmos_config["fields"].items():
            aliases = field_config.get("aliases", [])
            for alias in aliases:
                if alias.lower() in query_lower:
                    if field_name not in requested_fields:
                        requested_fields.append(field_name)
                    break
        
        # If no specific fields mentioned, return all fields
        if not requested_fields:
            requested_fields = list(self.cosmos_config["fields"].keys())
        
        parse_time = (time.time() - start_time) * 1000
        return requested_fields, parse_time
    
    def detect_aggregation(self, query: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Detect if query is asking for aggregation (min/max).
        
        Args:
            query (str): User's natural language query
            
        Returns:
            Tuple of (aggregation_type, field_name) or (None, None)
            
        Example:
            "highest price" → ("MAX", "Price")
            "lowest change" → ("MIN", "Change")
            "maximum change percent" → ("MAX", "ChangePercent")
        """
        query_lower = query.lower()
        
        # Detect aggregation type
        aggregation = None
        if any(word in query_lower for word in ["highest", "maximum", "max", "peak", "top"]):
            aggregation = "MAX"
        elif any(word in query_lower for word in ["lowest", "minimum", "min", "bottom"]):
            aggregation = "MIN"
        
        if not aggregation:
            return None, None
        
        # Detect which field to aggregate
        for field_name, field_config in self.cosmos_config["fields"].items():
            aliases = field_config.get("aliases", [])
            for alias in aliases:
                if alias.lower() in query_lower:
                    return aggregation, field_name
        
        return None, None
    
    def resolve_symbol_from_ai_search(self, query: str) -> Tuple[Optional[str], Optional[str], float]:
        """
        Use Azure AI Search to resolve stock symbol from user query.
        
        Args:
            query (str): User's natural language query
            
        Returns:
            Tuple of (SymbolRaw, Symbol, time in ms)
            
        Uses the existing query_parser logic to detect company names/symbols
        and queries Azure AI Search to get the actual SymbolRaw.
        """
        start_time = time.time()
        
        # Parse query using existing logic
        spec = parse_user_query(query)
        
        # Build simplified payload for symbol resolution only
        # Don't use build_search_payload_from_spec to avoid including metric fields
        stock_query = spec.get("stock_query", query)
        
        payload = {
            "search": stock_query,
            "searchFields": "SymbolRaw,Name,Symbol",
            "top": 1,
            "select": "SymbolRaw,Name,Symbol"
        }
        
        # Execute Azure AI Search query
        url = f"{AZURE_SEARCH_ENDPOINT}/indexes/{AZURE_SEARCH_INDEX}/docs/search?api-version=2024-07-01"
        headers = {
            "Content-Type": "application/json",
            "api-key": AZURE_SEARCH_API_KEY
        }
        
        print(f"   Search Query: {stock_query}")
        
        response = self.session.post(url, json=payload, headers=headers)
        search_time = (time.time() - start_time) * 1000
        
        if response.status_code != 200:
            print(f"✗ Azure AI Search error: {response.status_code}")
            try:
                error_details = response.json()
                print(f"   Error details: {json.dumps(error_details, indent=2)}")
            except:
                print(f"   Error response: {response.text}")
            return None, None, search_time
        
        results = response.json()
        if results.get("value") and len(results["value"]) > 0:
            first_result = results["value"][0]
            symbol_raw = first_result.get("SymbolRaw")
            symbol = first_result.get("Symbol")
            return symbol_raw, symbol, search_time
        
        return None, None, search_time
    
    def process_query(self, query: str) -> Dict[str, Any]:
        """
        Process a user query end-to-end.
        
        Args:
            query (str): User's natural language query
            
        Returns:
            Dictionary with results and timing information
        """
        total_start = time.time()
        print(f"\n{'='*80}")
        print(f"Processing Query: {query}")
        print(f"{'='*80}\n")
        
        timing = {}
        
        # Step 1: Parse user query to detect fields
        print("Step 1: Parsing user query for requested fields...")
        requested_fields, parse_time = self.parse_fields_from_query(query)
        timing["field_parsing"] = parse_time
        print(f"   Requested Fields: {requested_fields}")
        print(f"   ⏱️  Parse Time: {parse_time:.2f}ms\n")
        
        # Step 1b: Check for aggregation
        aggregation_type, agg_field = self.detect_aggregation(query)
        if aggregation_type:
            print(f"   Detected Aggregation: {aggregation_type} of {agg_field}\n")
        
        # Step 2: Resolve symbol using Azure AI Search
        print("Step 2: Resolving stock symbol using Azure AI Search...")
        symbol_raw, symbol, search_time = self.resolve_symbol_from_ai_search(query)
        timing["ai_search"] = search_time
        
        if not symbol_raw:
            total_time = (time.time() - total_start) * 1000
            timing["total"] = total_time
            print(f"   ✗ Could not resolve stock symbol from query")
            print(f"   ⏱️  Total Time: {total_time:.2f}ms\n")
            return {
                "success": False,
                "error": "Could not identify stock symbol in query",
                "timing": timing
            }
        
        print(f"   Resolved Symbol: {symbol_raw} ({symbol})")
        print(f"   ⏱️  AI Search Time: {search_time:.2f}ms\n")
        
        # Step 3: Query Cosmos DB
        print("Step 3: Querying Cosmos DB for real-time data...")
        cosmos_start = time.time()
        
        if aggregation_type and agg_field:
            # Aggregation query
            result = get_stock_aggregation(symbol_raw, agg_field, aggregation_type)
        else:
            # Latest data query
            result = get_latest_stock_data(symbol_raw, requested_fields)
        
        cosmos_time = (time.time() - cosmos_start) * 1000
        timing["cosmos_query"] = cosmos_time
        
        if not result:
            total_time = (time.time() - total_start) * 1000
            timing["total"] = total_time
            print(f"   ✗ No data found in Cosmos DB for {symbol_raw}")
            print(f"   ⏱️  Total Time: {total_time:.2f}ms\n")
            return {
                "success": False,
                "error": f"No data found for {symbol_raw}",
                "timing": timing
            }
        
        # Step 4: Return results
        total_time = (time.time() - total_start) * 1000
        timing["total"] = total_time
        
        print(f"\n{'='*80}")
        print("Results:")
        print(f"{'='*80}")
        for key, value in result.items():
            print(f"   {key}: {value}")
        
        print(f"\n{'='*80}")
        print("Performance Metrics:")
        print(f"{'='*80}")
        print(f"   Field Parsing:        {timing['field_parsing']:.2f}ms")
        print(f"   AI Search:            {timing['ai_search']:.2f}ms")
        print(f"   Cosmos DB Query:      {timing['cosmos_query']:.2f}ms")
        print(f"   ─────────────────────────────────")
        print(f"   Total Time:           {timing['total']:.2f}ms")
        print(f"{'='*80}\n")
        
        return {
            "success": True,
            "data": result,
            "timing": timing,
            "resolved_symbol": symbol_raw
        }
    
    def run_interactive(self):
        """Run the application in interactive console mode."""
        print("\nWelcome to the Stock Search Application (Cosmos DB Integration)!")
        print("\nThis app integrates Azure AI Search with Cosmos DB for real-time stock data.")
        print("\nExample queries:")
        print("  • What is the price of Reliance?")
        print("  • Show me price and change for TCS")
        print("  • Get all data for INFY")
        print("  • What is the highest price for HDFC?")
        print("  • Show me the lowest change for ITC")
        print("\nType 'exit' or 'quit' to stop.\n")
        
        while True:
            try:
                query = input("Your query: ").strip()
                
                if not query:
                    continue
                
                if query.lower() in ["exit", "quit", "q"]:
                    print("\nThank you for using the application. Goodbye!")
                    break
                
                self.process_query(query)
                
            except KeyboardInterrupt:
                print("\n\nInterrupted by user. Goodbye!")
                break
            except Exception as e:
                print(f"\n✗ Error processing query: {str(e)}\n")


def main():
    """Main entry point for the application."""
    app = CosmosDynamicQueryApp()
    app.run_interactive()


if __name__ == "__main__":
    main()

"""
Cosmos DB Query Parser for Stock Dynamic Data

This module provides functions to query Azure Cosmos DB for stock price data
with dynamic field selection and aggregation capabilities.

Features:
- Get latest values for specific fields (Price, Change, ChangePercent)
- Get min/max aggregations for any field
- Dynamic query construction based on requested fields
- Efficient partition-key based queries
- Query logging with performance metrics
- Connection pooling for optimal performance

Requirements:
- Azure Cosmos DB with stock price data
- Managed Identity authentication configured
- Environment variables in .env file
"""

import os
import time
from typing import List, Optional, Dict, Any
from azure.cosmos import CosmosClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
COSMOS_ENDPOINT = os.getenv("COSMOS_ENDPOINT", "https://<your-account>.documents.azure.com:443/")
DATABASE_NAME = os.getenv("DATABASE_NAME", "db001")
CONTAINER_NAME = os.getenv("CONTAINER_NAME", "stocks-dynamic-data")


class CosmosDBStockQuery:
    """
    Handles dynamic queries to Cosmos DB for stock price data.
    
    Uses connection pooling by maintaining a single client instance for all queries,
    which significantly improves performance by reusing connections.
    
    Supports:
    - Latest value queries with selective field retrieval
    - Min/max aggregation queries
    - Efficient partition-key based filtering
    - Performance timing and metrics
    """
    
    # Class-level client for connection pooling (singleton pattern)
    _client = None
    _database = None
    _container = None
    
    def __init__(self):
        """
        Initialize Cosmos DB connection using managed identity.
        
        Uses singleton pattern to ensure only one client instance is created,
        which enables connection pooling and improves performance.
        """
        # Only create client once (singleton pattern for connection pooling)
        if CosmosDBStockQuery._client is None:
            init_start = time.time()
            credential = DefaultAzureCredential()
            CosmosDBStockQuery._client = CosmosClient(url=COSMOS_ENDPOINT, credential=credential)
            CosmosDBStockQuery._database = CosmosDBStockQuery._client.get_database_client(DATABASE_NAME)
            CosmosDBStockQuery._container = CosmosDBStockQuery._database.get_container_client(CONTAINER_NAME)
            init_time = (time.time() - init_start) * 1000
            print(f"[Connection] Cosmos DB client initialized in {init_time:.2f}ms\n")
        
        # Use class-level clients
        self.client = CosmosDBStockQuery._client
        self.database = CosmosDBStockQuery._database
        self.container = CosmosDBStockQuery._container
    
    def get_latest_data(
        self, 
        symbol: str, 
        fields: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get the latest data for a symbol with dynamic field selection.
        
        Args:
            symbol (str): Stock ticker symbol (e.g., 'RELIANCE', 'TCS')
            fields (List[str], optional): List of fields to retrieve.
                Valid values: ['Price', 'Change', 'ChangePercent']
                If None, returns all fields.
                
        Returns:
            dict or None: Dictionary containing requested fields plus Symbol and DateTime
            Example:
            {
                'Symbol': 'RELIANCE',
                'DateTime': '2025-11-17T15:30:00',
                'Price': 2500.50,
                'Change': 15.25,
                'ChangePercent': 0.61
            }
            
        Example Usage:
            >>> query = CosmosDBStockQuery()
            >>> # Get only Price
            >>> result = query.get_latest_data('RELIANCE', ['Price'])
            >>> # Get Price and Change
            >>> result = query.get_latest_data('TCS', ['Price', 'Change'])
            >>> # Get all fields
            >>> result = query.get_latest_data('INFY')
        """
        total_start = time.time()
        
        # Default to all fields if none specified
        if fields is None:
            fields = ['Price', 'Change', 'ChangePercent']
        
        # Validate fields
        prep_start = time.time()
        valid_fields = {'Price', 'Change', 'ChangePercent'}
        requested_fields = set(fields)
        invalid_fields = requested_fields - valid_fields
        if invalid_fields:
            raise ValueError(f"Invalid fields: {invalid_fields}. Valid fields are: {valid_fields}")
        
        # Build dynamic SELECT clause - always include Symbol and DateTime
        select_fields = ['c.Symbol', 'c.DateTime'] + [f'c.{field}' for field in fields]
        select_clause = ', '.join(select_fields)
        
        # Construct query
        query = f"""
        SELECT TOP 1 {select_clause}
        FROM c
        WHERE c.Symbol = @symbol
        ORDER BY c.DateTime DESC
        """
        
        params = [{"name": "@symbol", "value": symbol}]
        prep_time = (time.time() - prep_start) * 1000
        
        # Log query for debugging
        print(f"\n{'='*80}")
        print(f"[Cosmos DB Query - Latest Data]")
        print(f"{'='*80}")
        print(f"Symbol: {symbol}")
        print(f"Fields: {fields}")
        print(f"Query: {query.strip()}")
        print(f"Parameters: {params}")
        print(f"⏱️  Query Preparation Time: {prep_time:.2f}ms")
        
        # Execute query
        exec_start = time.time()
        items = list(
            self.container.query_items(
                query=query,
                parameters=params,
                enable_cross_partition_query=False  # Optimized for partition key
            )
        )
        exec_time = (time.time() - exec_start) * 1000
        
        result = items[0] if items else None
        total_time = (time.time() - total_start) * 1000
        
        print(f"⏱️  Query Execution Time: {exec_time:.2f}ms")
        print(f"⏱️  Total Time: {total_time:.2f}ms")
        print(f"Result: {result}")
        print(f"{'='*80}\n")
        
        return result
    
    def get_aggregated_data(
        self,
        symbol: str,
        field: str,
        aggregation: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get aggregated data (min/max) for a specific field across all records for a symbol.
        
        Args:
            symbol (str): Stock ticker symbol (e.g., 'RELIANCE', 'TCS')
            field (str): Field to aggregate. Valid values: 'Price', 'Change', 'ChangePercent'
            aggregation (str): Aggregation type. Valid values: 'MIN', 'MAX'
            
        Returns:
            dict or None: Dictionary containing the aggregated value, corresponding timestamp, and symbol
            Example:
            {
                'Symbol': 'RELIANCE',
                'DateTime': '2025-11-14T10:00:00',
                'MaxPrice': 2550.75
            }
            
        Note:
            Uses a single optimized query with ORDER BY to get the min/max record directly,
            which is more efficient than aggregation followed by lookup.
            
        Example Usage:
            >>> query = CosmosDBStockQuery()
            >>> # Get highest price
            >>> result = query.get_aggregated_data('RELIANCE', 'Price', 'MAX')
            >>> # Get lowest change
            >>> result = query.get_aggregated_data('TCS', 'Change', 'MIN')
            >>> # Get highest change percent
            >>> result = query.get_aggregated_data('INFY', 'ChangePercent', 'MAX')
        """
        total_start = time.time()
        
        # Validate inputs
        prep_start = time.time()
        valid_fields = {'Price', 'Change', 'ChangePercent'}
        if field not in valid_fields:
            raise ValueError(f"Invalid field: {field}. Valid fields are: {valid_fields}")
        
        valid_aggregations = {'MIN', 'MAX'}
        aggregation = aggregation.upper()
        if aggregation not in valid_aggregations:
            raise ValueError(f"Invalid aggregation: {aggregation}. Valid values are: {valid_aggregations}")
        
        # Determine sort order based on aggregation type
        # For MAX, we want DESC (highest first), for MIN we want ASC (lowest first)
        sort_order = "DESC" if aggregation == "MAX" else "ASC"
        
        # Single optimized query - ORDER BY the field and get TOP 1
        query = f"""
        SELECT TOP 1 c.Symbol, c.DateTime, c.{field}
        FROM c
        WHERE c.Symbol = @symbol
        ORDER BY c.{field} {sort_order}
        """
        
        params = [{"name": "@symbol", "value": symbol}]
        prep_time = (time.time() - prep_start) * 1000
        
        print(f"\n{'='*80}")
        print(f"[Cosmos DB Query - Aggregation (Optimized Single Query)]")
        print(f"{'='*80}")
        print(f"Symbol: {symbol}")
        print(f"Field: {field}")
        print(f"Aggregation: {aggregation}")
        print(f"Query: {query.strip()}")
        print(f"Parameters: {params}")
        print(f"⏱️  Query Preparation Time: {prep_time:.2f}ms")
        
        # Execute query
        exec_start = time.time()
        items = list(
            self.container.query_items(
                query=query,
                parameters=params,
                enable_cross_partition_query=False  # Optimized for partition key
            )
        )
        exec_time = (time.time() - exec_start) * 1000
        
        if not items:
            total_time = (time.time() - total_start) * 1000
            print(f"⏱️  Query Execution Time: {exec_time:.2f}ms")
            print(f"⏱️  Total Time: {total_time:.2f}ms")
            print(f"Result: No data found for symbol {symbol}")
            print(f"{'='*80}\n")
            return None
        
        result = items[0]
        
        # Rename the field to include aggregation type for clarity
        agg_field_name = f"{aggregation.capitalize()}{field}"
        result[agg_field_name] = result.pop(field)
        
        total_time = (time.time() - total_start) * 1000
        
        print(f"⏱️  Query Execution Time: {exec_time:.2f}ms")
        print(f"⏱️  Total Time: {total_time:.2f}ms")
        print(f"Result: {result}")
        print(f"{'='*80}\n")
        
        return result


# Convenience functions for easy import
def get_latest_stock_data(
    symbol: str, 
    fields: Optional[List[str]] = None
) -> Optional[Dict[str, Any]]:
    """
    Convenience function to get latest stock data.
    
    Args:
        symbol (str): Stock ticker symbol
        fields (List[str], optional): Fields to retrieve ['Price', 'Change', 'ChangePercent']
        
    Returns:
        dict or None: Latest data for the symbol
    """
    query = CosmosDBStockQuery()
    return query.get_latest_data(symbol, fields)


def get_stock_aggregation(
    symbol: str,
    field: str,
    aggregation: str
) -> Optional[Dict[str, Any]]:
    """
    Convenience function to get aggregated stock data.
    
    Args:
        symbol (str): Stock ticker symbol
        field (str): Field to aggregate ['Price', 'Change', 'ChangePercent']
        aggregation (str): Aggregation type ['MIN', 'MAX']
        
    Returns:
        dict or None: Aggregated data with timestamp
    """
    query = CosmosDBStockQuery()
    return query.get_aggregated_data(symbol, field, aggregation)


# Example usage and testing
if __name__ == "__main__":
    print("=" * 80)
    print("Testing Cosmos DB Stock Query Functions")
    print("=" * 80)
    
    # Test 1: Get latest price only
    print("\n--- Test 1: Get Latest Price Only ---")
    result = get_latest_stock_data("JSWENERGY", ["Price"])
    
    # Test 2: Get latest price and change
    print("\n--- Test 2: Get Latest Price and Change ---")
    result = get_latest_stock_data("JSWENERGY", ["Price", "Change"])
    
    # Test 3: Get all latest fields
    print("\n--- Test 3: Get All Latest Fields ---")
    result = get_latest_stock_data("JSWENERGY")
    
    # Test 4: Get highest price
    print("\n--- Test 4: Get Highest Price ---")
    result = get_stock_aggregation("JSWENERGY", "Price", "MAX")
    
    # Test 5: Get lowest price
    print("\n--- Test 5: Get Lowest Price ---")
    result = get_stock_aggregation("JSWENERGY", "Price", "MIN")
    
    # Test 6: Get highest change percent
    print("\n--- Test 6: Get Highest Change Percent ---")
    result = get_stock_aggregation("JSWENERGY", "ChangePercent", "MAX")
    
    # Test 7: Get lowest change
    print("\n--- Test 7: Get Lowest Change ---")
    result = get_stock_aggregation("JSWENERGY", "Change", "MIN")
    
    print("\n" + "=" * 80)
    print("Testing Complete")
    print("=" * 80)

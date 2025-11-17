"""
Azure Cosmos DB Data Import Script for Stock Dynamic Data

This script imports real-time/dynamic stock price data from a CSV file into Azure Cosmos DB.
It uses Azure Managed Identity (DefaultAzureCredential) for secure authentication without requiring keys.

Features:
- Imports CSV data containing stock symbols, datetime, price, and change information
- Uses managed identity authentication with Azure Cosmos DB
- Supports idempotent upsert operations (safe to re-run)
- Provides helper function to query latest price for a given stock symbol

Requirements:
- Azure Cosmos DB account with RBAC enabled
- User/Managed Identity with "Cosmos DB Built-in Data Contributor" role assigned
- Azure CLI login or managed identity configured
- Environment variables configured in .env file

Environment Variables:
- COSMOS_ENDPOINT: Cosmos DB account endpoint URL
- DATABASE_NAME: Name of the Cosmos DB database
- CONTAINER_NAME: Name of the Cosmos DB container

CSV Format:
The input CSV file should contain the following columns:
- Symbol: Stock ticker symbol
- DateTime: Timestamp of the price data
- Price: Current stock price
- Change: Price change value
- ChangePercent: Percentage change in price
"""

import csv
import os
from azure.cosmos import CosmosClient, PartitionKey
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

# Load environment variables from .env file (look in parent directory)
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=env_path)

# ============================
# CONFIG: UPDATE THESE VALUES
# ============================

COSMOS_ENDPOINT = os.getenv("COSMOS_ENDPOINT", "https://<your-account>.documents.azure.com:443/")

DATABASE_NAME = os.getenv("DATABASE_NAME", "db001")
CONTAINER_NAME = os.getenv("CONTAINER_NAME", "stocks-dynamic-data")

CSV_PATH = os.path.join(os.path.dirname(__file__), '..', 'sample_data', 'companies_dynamic_real.csv')  # path to your dynamic CSV file

# ============================
# CONNECT TO COSMOS
# ============================

def get_cosmos_container():
    """
    Establishes connection to Azure Cosmos DB using Managed Identity.
    
    Uses DefaultAzureCredential which automatically tries multiple authentication methods:
    - Managed Identity (in Azure environments)
    - Azure CLI (local development)
    - Visual Studio Code
    - Other Azure authentication methods
    
    Returns:
        Container client object for performing operations on the Cosmos DB container
        
    Raises:
        azure.core.exceptions.ClientAuthenticationError: If authentication fails
        azure.cosmos.exceptions.CosmosHttpResponseError: If container doesn't exist
    """
    credential = DefaultAzureCredential()
    client = CosmosClient(url=COSMOS_ENDPOINT, credential=credential)
    database = client.get_database_client(DATABASE_NAME)
    container = database.get_container_client(CONTAINER_NAME)
    return container

# ============================
# IMPORT CSV -> COSMOS
# ============================

def import_dynamic_prices(csv_path: str):
    """
    Imports stock price data from a CSV file into Cosmos DB.
    
    Reads a CSV file containing stock price information and upserts each record
    into Cosmos DB. The operation is idempotent - running it multiple times with
    the same data will not create duplicates.
    
    Args:
        csv_path (str): Path to the CSV file containing stock price data
        
    CSV Columns Expected:
        - Symbol: Stock ticker symbol (e.g., 'RELIANCE', 'TCS')
        - DateTime: Timestamp in ISO format
        - Price: Current stock price (float)
        - Change: Price change value (float)
        - ChangePercent: Percentage change in price (float)
        
    Document Structure:
        {
            "id": "SYMBOL_DATETIME",  # Unique identifier (e.g., "RELIANCE_2025-11-17T10:30:00")
            "Symbol": "RELIANCE",
            "DateTime": "2025-11-17T10:30:00",
            "Price": 2500.50,
            "Change": 15.25,
            "ChangePercent": 0.61
        }
        
    Note:
        - Progress is printed every 100 documents
        - Blank or missing numeric values are stored as None
        - Document IDs use underscore separator (# is not allowed in Cosmos DB IDs)
    """
    container = get_cosmos_container()

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        count = 0
        for row in reader:
            symbol = row["Symbol"].strip()
            dt = row["DateTime"].strip()

            # Build deterministic id (use underscore instead of # which is illegal)
            doc_id = f"{symbol}_{dt}"

            # Parse numeric fields (defensive: handle blanks)
            def to_float(val):
                val = val.strip()
                return float(val) if val not in ("", None) else None

            price = to_float(row.get("Price", ""))
            change = to_float(row.get("Change", ""))
            change_pct = to_float(row.get("ChangePercent", ""))

            doc = {
                "id": doc_id,
                "Symbol": symbol,
                "DateTime": dt,
                "Price": price,
                "Change": change,
                "ChangePercent": change_pct,
            }

            # Upsert so you can safely re-run the script
            container.upsert_item(doc)
            count += 1

            if count % 100 == 0:
                print(f"Upserted {count} documents...")

    print(f"✅ Done. Total documents upserted: {count}")


# ============================
# OPTIONAL: helper function
# ============================

def get_latest_price(symbol: str):
    """
    Retrieves the most recent price data for a given stock symbol.
    
    Queries Cosmos DB for the latest document matching the given stock symbol,
    ordered by DateTime in descending order.
    
    Args:
        symbol (str): Stock ticker symbol (e.g., 'RELIANCE', 'TCS')
        
    Returns:
        dict or None: Dictionary containing the latest price data with keys:
            - Symbol: Stock ticker symbol
            - DateTime: Timestamp of the price data
            - Price: Current stock price
            - Change: Price change value
            - ChangePercent: Percentage change in price
        Returns None if no data found for the symbol
        
    Example:
        >>> latest = get_latest_price("RELIANCE")
        >>> print(latest)
        {
            'Symbol': 'RELIANCE', 
            'DateTime': '2025-11-17T15:30:00',
            'Price': 2500.50,
            'Change': 15.25,
            'ChangePercent': 0.61
        }
        
    Note:
        - Uses partition key filtering (Symbol) for optimal performance
        - Returns only the most recent record (TOP 1)
    """
    container = get_cosmos_container()

    query = """
    SELECT TOP 1 c.Symbol, c.DateTime, c.Price, c.Change, c.ChangePercent
    FROM c
    WHERE c.Symbol = @symbol
    ORDER BY c.DateTime DESC
    """
    params = [
        {"name": "@symbol", "value": symbol}
    ]

    items = list(
        container.query_items(
            query=query,
            parameters=params,
            enable_cross_partition_query=False  # Symbol is the partition key
        )
    )

    return items[0] if items else None


# ============================
# MAIN
# ============================

if __name__ == "__main__":
    print(f"Using CSV: {CSV_PATH}")
    import_dynamic_prices(CSV_PATH)

    # quick sanity check:
    sample_symbol = "RELIANCE"
    latest = get_latest_price(sample_symbol)
    print(f"\nLatest price for {sample_symbol}:")
    print(latest)
    print(f"\nLatest price for {sample_symbol}:")
    print(latest)

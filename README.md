# Stock Search Application using Azure AI Search

## Overview

This application demonstrates how to build an intelligent stock search interface using Azure AI Search. It allows users to query stock information using natural language without requiring any Large Language Model (LLM) or Small Language Model (SLM). The application uses pattern matching and Azure AI Search's powerful features like synonyms and collection filters to understand user intent and retrieve relevant results.

### Data Storage Architecture

The application uses a **hybrid data storage approach** to optimize for different data access patterns:

#### 1. **Azure AI Search** - Static/Master Data
- **Purpose**: Stores company master data and metadata that changes infrequently
- **Data Type**: Company profiles, sectors, market cap, PE ratios, indices membership
- **Update Frequency**: Weekly or monthly
- **Strengths**: 
  - Full-text search with synonyms
  - Complex filtering and aggregations
  - Natural language query processing
- **Use Case**: "Find all NIFTY50 stocks in Energy sector with PE < 20"

#### 2. **Azure Cosmos DB** - Dynamic/Real-time Data
- **Purpose**: Stores frequently changing stock price data
- **Data Type**: Current prices, price changes, timestamps, trading volumes
- **Update Frequency**: Real-time or near-real-time (every few seconds/minutes)
- **Strengths**:
  - Low-latency reads/writes
  - Global distribution
  - Automatic indexing
  - Partition-based queries
- **Use Case**: "Get latest price and change for RELIANCE stock"

This architecture ensures optimal performance and cost-efficiency by storing each data type in the most appropriate service.

## Features

- **Natural Language Queries**: Query stocks using plain English (e.g., "sector materials with PE under 100")
- **Synonym Support**: Search for stocks using various names and abbreviations
- **Multi-Index Support**: Stocks can belong to multiple indices (NIFTY50, NIFTY100, sector-specific indices)
- **Flexible Filtering**: Filter by sector, index, PE ratio, market cap, and other metrics
- **No LLM Required**: Uses pattern matching and Azure AI Search capabilities for intent detection
- **Multiple Implementation Options**: REST API or Python SDK approaches
- **Modern Web UI**: Streamlit-based responsive interface with performance metrics

---

## Application Architecture

### Implementation Approaches

This solution provides **three entry points** for different use cases:

#### 1. **Console Application - REST API** (`app.py`)
- **Technology**: Direct HTTP calls using Python `requests` library
- **Connection Pooling**: Uses `requests.Session()` for connection reuse
- **Use Case**: Standalone scripts, batch processing, or integration with non-Python systems
- **Performance**: 160-350ms per query (after initial connection)
- **Run**: `python app.py` (interactive console)

```python
# Example usage
from app import build_search_request_from_user_input, execute_search_request

req = build_search_request_from_user_input(
    "nifty 50 stocks",
    service_endpoint="https://...",
    index_name="stocks-search-index",
    api_key="..."
)
result = execute_search_request(req)
```

#### 2. **Console Application - Python SDK** (`app_sdk.py`)
- **Technology**: Official Azure Search Python SDK (`azure-search-documents`)
- **Connection Management**: SDK handles connection pooling automatically
- **Use Case**: Python-native applications, better type safety, easier maintenance
- **Performance**: Similar to REST API (~160-350ms per query)
- **Run**: `python app_sdk.py` (interactive console)

```python
# Example usage
from app_sdk import execute_search_from_user_input_sdk

result = execute_search_from_user_input_sdk("nifty 50 stocks")
```

#### 3. **Web Application** (`streamlit_app.py`)
- **Technology**: Streamlit web framework
- **Backend**: Uses `app.py` (REST API version) by default
- **Features**: 
  - Modern gradient UI with responsive design
  - Real-time search with performance metrics
  - Query analysis showing detected parameters
  - Interactive results table with sorting/filtering
  - Collapsible technical details (request/response)
- **Use Case**: End-user interface, demos, data exploration
- **Run**: `streamlit run streamlit_app.py`
- **Access**: Browser at `http://localhost:8501`

### Key Components

```
stock-data-search/
├── app.py                  # REST API implementation (requests library)
├── app_sdk.py              # Python SDK implementation (azure-search-documents)
├── streamlit_app.py        # Web UI (uses app.py)
├── import_dynamic_data.py  # Cosmos DB data import script
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables (Azure credentials)
└── sample_data/            # Stock data CSV files
    ├── companies_static_cleansed_jsonindices_with_rawsymbol.csv  # Master data for AI Search
    └── companies_dynamic_real.csv  # Real-time price data for Cosmos DB
```

### Data Import Scripts

#### **import_dynamic_data.py** - Cosmos DB Data Import
Imports real-time stock price data into Azure Cosmos DB using managed identity authentication.

**Purpose**: Load dynamic price data (prices, changes, timestamps) from CSV into Cosmos DB

**Features**:
- Uses Azure Managed Identity (no keys required)
- Idempotent upsert operations (safe to re-run)
- Reads configuration from `.env` file
- Progress tracking during import
- Query helper function for latest prices

**Usage**:
```bash
# Ensure you're logged into Azure CLI
az login

# Run the import script
python import_dynamic_data.py
```

**Requirements**:
- Azure Cosmos DB account with RBAC enabled
- "Cosmos DB Built-in Data Contributor" role assigned to your identity
- Environment variables configured in `.env`:
  - `COSMOS_ENDPOINT`: Cosmos DB endpoint URL
  - `DATABASE_NAME`: Database name
  - `CONTAINER_NAME`: Container name

**CSV Format**:
```csv
Symbol,DateTime,Price,Change,ChangePercent
RELIANCE,2025-11-17T10:30:00,2500.50,15.25,0.61
TCS,2025-11-17T10:30:00,3450.75,-22.50,-0.65
```

---

## Setup Instructions

### 1. Upload Sample Data

The application uses a CSV file containing stock master data that doesn't change frequently.

**Data File Location**: `sample_data/companies_static_cleansed_jsonindices_with_rawsymbol.csv`

**Data Schema**:
- `Symbol`: Stock symbol (e.g., RELIANCE, TCS)
- `SymbolRaw`: Original symbol format (e.g., M&M for Mahindra & Mahindra)
- `Name`: Full company name
- `Sector`: Industry sector (Energy, Information Technology, Financials, etc.)
- `MarketCapCr`: Market capitalization in crores
- `PE`: Price-to-Earnings ratio
- `PB`: Price-to-Book ratio
- `EPS`: Earnings Per Share
- `DividendYieldPct`: Dividend yield percentage
- `AllIndices`: JSON array of indices the stock belongs to (e.g., `["NIFTY50", "NIFTYBANK"]`)

### 2. Create Synonym Map

Synonyms are created at the **Azure AI Search service level**, not linked to any specific index. This allows the same synonym map to be used across all indices in the service.

**Create Synonym Map using Azure Portal or REST API**:

```json
PUT https://[service-name].search.windows.net/synonymmaps/stock-names-synonyms?api-version=2024-07-01
{
  "name": "stock-names-synonyms",
  "format": "solr",
  "synonyms": "TCS, Tata Consultancy Services, Tata Consultancy, TATA CONSULTANCY\nHDFC, HDFC Bank, HDFCBANK\nRELIANCE, Reliance Industries, RIL\nINFY, Infosys, Infosys Limited\nICICIBANK, ICICI Bank, ICICI\nSBI, SBIN, State Bank of India, State Bank\nITC, ITC Limited\nWIPRO, Wipro Limited\nM&M, Mahindra, Mahindra & Mahindra, M_M\nTATAMOTORS, Tata Motors, TATAMOTORS"
}
```

**Key Points**:
- Synonyms are stored in **Solr format** (comma-separated values per line)
- Each line represents a group of equivalent terms
- The synonym map is reusable across all documents and indices
- Users can search using any variation (e.g., "TCS", "Tata Consultancy", "TATA CONSULTANCY") and get results for the canonical form

### 3. Create Azure AI Search Index

Create an index with the schema that associates the synonym map with specific fields.

**Index Schema Example**:

```json
{
  "name": "stocks-search-index",
  "fields": [
    {
      "name": "Symbol",
      "type": "Edm.String",
      "searchable": true,
      "filterable": true,
      "sortable": true,
      "facetable": false,
      "key": false,
      "analyzer": "stock_analyzer"
    },
    {
      "name": "SymbolRaw",
      "type": "Edm.String",
      "key": true,
      "searchable": true,
      "filterable": true,
      "analyzer": "stock_analyzer"
    },
    {
      "name": "Name",
      "type": "Edm.String",
      "searchable": true,
      "filterable": false,
      "sortable": false,
      "facetable": false,
      "analyzer": "stock_analyzer"
    },
    {
      "name": "Sector",
      "type": "Edm.String",
      "searchable": false,
      "filterable": true,
      "sortable": true,
      "facetable": true
    },
    {
      "name": "MarketCapCr",
      "type": "Edm.Double",
      "searchable": false,
      "filterable": true,
      "sortable": true,
      "facetable": false
    },
    {
      "name": "PE",
      "type": "Edm.Double",
      "searchable": false,
      "filterable": true,
      "sortable": true,
      "facetable": false
    },
    {
      "name": "PB",
      "type": "Edm.Double",
      "searchable": false,
      "filterable": true,
      "sortable": true,
      "facetable": false
    },
    {
      "name": "EPS",
      "type": "Edm.Double",
      "searchable": false,
      "filterable": true,
      "sortable": true,
      "facetable": false
    },
    {
      "name": "DividendYieldPct",
      "type": "Edm.Double",
      "searchable": false,
      "filterable": true,
      "sortable": true,
      "facetable": false
    },
    {
      "name": "AllIndices",
      "type": "Collection(Edm.String)",
      "searchable": false,
      "filterable": true,
      "sortable": false,
      "facetable": true
    }
  ],
  "analyzers": [
    {
      "name": "stock_analyzer",
      "@odata.type": "#Microsoft.Azure.Search.CustomAnalyzer",
      "tokenizer": "standard_v2",
      "tokenFilters": ["lowercase"],
      "charFilters": []
    }
  ],
  "synonymMaps": ["stock-names-synonyms"]
}
```

**Key Schema Design Points**:

#### a) **Synonym Map Association**
The synonym map is associated with the index at the **field level** using the `analyzer` property. In the example above, the `stock_analyzer` custom analyzer is applied to searchable fields like `Symbol`, `SymbolRaw`, and `Name`.

To link synonyms to a field:
```json
{
  "name": "Symbol",
  "type": "Edm.String",
  "searchable": true,
  "analyzer": "stock_analyzer",
  "synonymMaps": ["stock-names-synonyms"]
}
```

**OR** define a custom analyzer that references the synonym map:
```json
"analyzers": [
  {
    "name": "stock_analyzer",
    "@odata.type": "#Microsoft.Azure.Search.CustomAnalyzer",
    "tokenizer": "standard_v2",
    "tokenFilters": ["lowercase", "synonym-filter"],
    "charFilters": []
  }
],
"tokenFilters": [
  {
    "name": "synonym-filter",
    "@odata.type": "#Microsoft.Azure.Search.SynonymTokenFilter",
    "synonyms": ["stock-names-synonyms"]
  }
]
```

#### b) **Collection Data Type for Multi-Index Support**
The `AllIndices` field uses the **`Collection(Edm.String)`** data type, which allows storing multiple values (array/list) for a single document.

**Why this matters**:
- A single stock can belong to multiple indices (e.g., RELIANCE is in both NIFTY50 and NIFTYENERGY)
- When a user queries "nifty bank stocks", Azure AI Search can filter using: `AllIndices/any(i: i eq 'NIFTYBANK')`
- The `any()` lambda function checks if any value in the collection matches the filter condition
- This returns all stocks that include "NIFTYBANK" in their `AllIndices` array

**Example**:
```json
{
  "Symbol": "HDFCBANK",
  "Name": "HDFC Bank Ltd",
  "Sector": "Financials",
  "AllIndices": ["NIFTY50", "NIFTYBANK"]
}
```

When querying for "NIFTYBANK" stocks, this document will be included because "NIFTYBANK" is one of the values in the collection.

### 4. Load Data into Index

Upload the CSV data to the Azure AI Search index using:
- Azure Portal's "Import Data" wizard
- Azure AI Search REST API
- Azure SDK (Python, .NET, etc.)

**Example using Python SDK**:
```python
from azure.search.documents import SearchClient
import pandas as pd
import json

# Read CSV
df = pd.read_csv('sample_data/companies_static_cleansed_jsonindices_with_rawsymbol.csv')

# Convert AllIndices from JSON string to list
df['AllIndices'] = df['AllIndices'].apply(json.loads)

# Upload to Azure AI Search
search_client = SearchClient(endpoint, index_name, credential)
documents = df.to_dict('records')
search_client.upload_documents(documents)
```

### 5. Configure Application

Create a `.env` file in the project root with your Azure AI Search credentials:

```env
AZURE_SEARCH_ENDPOINT=https://your-service-name.search.windows.net
AZURE_SEARCH_INDEX_NAME=stocks-search-index
AZURE_SEARCH_API_KEY=your-admin-api-key
```

### 6. Install Dependencies

```bash
pip install -r requirements.txt
```

**Required packages**:
- `requests>=2.31.0` - HTTP library for REST API calls
- `python-dotenv>=1.0.0` - Environment variable management
- `streamlit>=1.28.0` - Web UI framework
- `azure-search-documents>=11.4.0` - Azure Search Python SDK
- `azure-identity>=1.12.0` - Azure authentication

### 7. Run the Application

**Option 1: Console Application (REST API)**
```bash
python app.py
```
- Interactive console interface
- Uses REST API with connection pooling
- Shows detailed timing and query analysis
- Type queries interactively

**Option 2: Console Application (Python SDK)**
```bash
python app_sdk.py
```
- Same interactive console interface
- Uses official Azure Search Python SDK
- Recommended for Python-native applications
- Better type hints and error handling

**Option 3: Web Application (Streamlit)**
```bash
streamlit run streamlit_app.py
```
- Modern web interface at `http://localhost:8501`
- Visual query analysis and results
- Performance metrics displayed
- Responsive design for mobile/desktop

**Example Console Session**:
```
=== Azure AI Search Stock Query Interface ===
Enter your query: nifty 50 stocks

User query: nifty 50 stocks
Spec: {'mode': 'list_by_index', 'index_code': 'NIFTY50', ...}
Status code: 200

[PERFORMANCE BREAKDOWN]
  1. Input processing: 0.5 ms
  2. Azure AI Search call: 165.2 ms
  3. Total time: 165.7 ms

Found 48 stocks in NIFTY50
```

---

## How It Works: Intent Detection Without LLM

This application **does not use any LLM or SLM** to interpret user input. Instead, it uses **rule-based pattern matching** and **keyword detection** to determine user intent and map queries to appropriate Azure AI Search requests.

### Intent Detection Flow

```
User Input → Normalize Text → Detect Components → Determine Mode → Build Azure AI Search Request
```

### Detection Components

The application detects the following components from user input:

1. **Metric Detection**: Identifies which financial metric the user is asking about
2. **Index Detection**: Detects if user mentions a specific index (NIFTY50, NIFTY100, etc.)
3. **Sector Detection**: Identifies sector mentions (Energy, IT, Banking, etc.)
4. **Metric Filter Detection**: Extracts comparison operators and values (e.g., "PE less than 50")
5. **Stock Name Detection**: Identifies if user is asking about a specific stock

### Pattern Matching Dictionaries

The application uses predefined dictionaries to map natural language variations to canonical values:

#### Metric Aliases
```python
METRIC_ALIASES = {
    "pe": "PE",
    "p/e": "PE",
    "price to earnings": "PE",
    "pb": "PB",
    "price to book": "PB",
    "market cap": "MarketCapCr",
    "eps": "EPS",
    "dividend": "DividendYieldPct",
    # ... more variations
}
```

#### Index Aliases
```python
INDEX_ALIASES = {
    "nifty 50": "NIFTY50",
    "nifty50": "NIFTY50",
    "nifty bank": "NIFTYBANK",
    "nifty it": "NIFTYIT",
    # ... more variations
}
```

#### Sector Aliases
```python
SECTOR_ALIASES = {
    "materials": "Materials",
    "material": "Materials",
    "steel": "Materials",
    "energy": "Energy",
    "oil": "Energy",
    "information technology": "Information Technology",
    "it": "Information Technology",
    # ... more variations
}
```

#### Comparator Aliases
```python
COMPARATOR_ALIASES = {
    ">": "gt",
    "greater than": "gt",
    "more than": "gt",
    "above": "gt",
    "<": "lt",
    "less than": "lt",
    "under": "lt",
    "below": "lt",
    # ... more variations
}
```

---

## Query Modes and Examples

The application translates user queries into one of several modes, each generating a specific Azure AI Search request:

### 1. **Single Stock Metric Query**

**User Input**: `"PE of Reliance"`, `"What is TCS PE ratio?"`, `"HDFC Bank market cap"`

**Intent**: User wants a specific metric for a specific stock

**Detection Logic**:
- Detects stock name using pattern matching against known stock names/synonyms
- Detects metric keyword (PE, PB, market cap, etc.)

**Generated Spec**:
```python
{
    "mode": "single_stock_metric",
    "stock_query": "Reliance",
    "metric": "PE",
    "raw": {"input": "PE of Reliance"}
}
```

**Azure AI Search Request**:
```json
{
  "search": "Reliance",
  "searchFields": "SymbolRaw,Name,Symbol",
  "top": 1,
  "select": "SymbolRaw,Name,Symbol,Sector,PE"
}
```

**Filter Properties Extracted**:
- `search`: Stock name extracted from user input
- `searchFields`: Limited to name/symbol fields using synonyms
- `select`: Includes only the requested metric field

---

### 2. **Single Stock Overview**

**User Input**: `"Show me Infosys"`, `"Get details for TCS"`, `"What about Reliance?"`

**Intent**: User wants all available information for a stock

**Detection Logic**:
- Detects stock name
- No specific metric mentioned

**Generated Spec**:
```python
{
    "mode": "single_stock_overview",
    "stock_query": "Infosys",
    "raw": {"input": "Show me Infosys"}
}
```

**Azure AI Search Request**:
```json
{
  "search": "Infosys",
  "searchFields": "SymbolRaw,Name,Symbol",
  "top": 1,
  "select": "SymbolRaw,Name,Symbol,Sector,MarketCapCr,PE,PB,EPS,DividendYieldPct,AllIndices"
}
```

**Filter Properties Extracted**:
- `search`: Stock name
- `select`: All available fields returned

---

### 3. **List by Index**

**User Input**: `"Nifty 50 stocks"`, `"Show nifty bank"`, `"List all nifty IT companies"`

**Intent**: User wants all stocks in a specific index

**Detection Logic**:
- Detects index keyword (nifty 50, nifty bank, etc.)
- No metric filter specified

**Generated Spec**:
```python
{
    "mode": "list_by_index",
    "index_code": "NIFTY50",
    "metric_filter": None,
    "raw": {"input": "Nifty 50 stocks"}
}
```

**Azure AI Search Request**:
```json
{
  "search": "*",
  "top": 50,
  "select": "SymbolRaw,Name,Symbol,Sector,MarketCapCr,PE,PB,EPS,DividendYieldPct,AllIndices",
  "count": true,
  "filter": "AllIndices/any(i: i eq 'NIFTY50')"
}
```

**Filter Properties Extracted**:
- `filter`: Uses collection filter with `any()` lambda to match index
- `AllIndices/any(i: i eq 'NIFTY50')` returns all stocks where "NIFTY50" is in the AllIndices array

---

### 4. **List by Index with Metric Filter**

**User Input**: `"Nifty 50 stocks with PE less than 20"`, `"Nifty bank PE above 30"`

**Intent**: User wants stocks from an index that meet a metric condition

**Detection Logic**:
- Detects index keyword
- Detects metric name (PE, PB, etc.)
- Detects comparator (less than, more than, etc.)
- Extracts numeric value

**Generated Spec**:
```python
{
    "mode": "list_by_metric_filter",
    "index_code": "NIFTY50",
    "metric_filter": {
        "metric": "PE",
        "op": "lt",
        "value": 20.0
    },
    "raw": {
        "input": "Nifty 50 stocks with PE less than 20",
        "metric_phrase": "pe",
        "comp_phrase": "less than"
    }
}
```

**Azure AI Search Request**:
```json
{
  "search": "*",
  "top": 50,
  "select": "SymbolRaw,Name,Symbol,Sector,PE,AllIndices",
  "count": true,
  "filter": "AllIndices/any(i: i eq 'NIFTY50') and PE lt 20.0"
}
```

**Filter Properties Extracted**:
- `filter`: Combines index filter with metric filter using `and`
- `AllIndices/any(i: i eq 'NIFTY50')`: Index membership check
- `PE lt 20.0`: Metric comparison using OData operators (`lt`, `gt`, `ge`, `le`, `eq`)
- `select`: Includes the filtered metric field

---

### 5. **List by Sector**

**User Input**: `"Healthcare companies"`, `"Show materials sector"`, `"Energy stocks"`

**Intent**: User wants all stocks in a specific sector

**Detection Logic**:
- Detects sector keyword (healthcare, materials, energy, etc.)
- No metric filter specified
- Contains listing keywords like "companies", "stocks", "list", "show"

**Generated Spec**:
```python
{
    "mode": "list_by_sector",
    "sector": "Materials",
    "raw": {"input": "Show materials sector"}
}
```

**Azure AI Search Request**:
```json
{
  "search": "*",
  "top": 50,
  "select": "SymbolRaw,Name,Symbol,Sector,MarketCapCr,PE,PB,EPS,DividendYieldPct,AllIndices",
  "count": true,
  "filter": "Sector eq 'Materials'"
}
```

**Filter Properties Extracted**:
- `filter`: Direct string equality match on Sector field
- `Sector eq 'Materials'`: OData equality filter

---

### 6. **List by Sector with Metric Filter**

**User Input**: `"Sector materials with PE under 100"`, `"Healthcare stocks with market cap above 50000"`

**Intent**: User wants stocks from a sector that meet a metric condition

**Detection Logic**:
- Detects sector keyword
- Detects metric filter (metric + comparator + value)
- Contains listing context (keywords or "sector" word)

**Generated Spec**:
```python
{
    "mode": "list_by_sector_with_filter",
    "sector": "Materials",
    "metric_filter": {
        "metric": "PE",
        "op": "lt",
        "value": 100.0
    },
    "raw": {
        "input": "sector materials with PE under 100",
        "metric_phrase": "pe",
        "comp_phrase": "under"
    }
}
```

**Azure AI Search Request**:
```json
{
  "search": "*",
  "top": 50,
  "select": "SymbolRaw,Name,Symbol,Sector,PE",
  "count": true,
  "filter": "Sector eq 'Materials' and PE lt 100.0"
}
```

**Filter Properties Extracted**:
- `filter`: Combines sector filter with metric filter using `and`
- `Sector eq 'Materials'`: String equality
- `PE lt 100.0`: Metric comparison
- `select`: Dynamically includes sector and the filtered metric

---

## Filter Property Extraction Details

### Metric Filter Pattern Matching

The application uses regex patterns to extract filter components:

```python
def detect_metric_filter(text_lower: str) -> Optional[Dict[str, Any]]:
    """
    Detect patterns like:
      'pe more than 10'
      'market cap above 50000'
      'dividend yield less than 2'
    """
    # Match pattern: <metric> <comparator> <number>
    pattern = r'(\w+(?:\s+\w+)*)\s+(greater than|more than|above|over|less than|under|below|>|<|>=|<=)\s+([\d.]+)'
    
    match = re.search(pattern, text_lower)
    if match:
        metric_phrase = match.group(1)
        comp_phrase = match.group(2)
        value_str = match.group(3)
        
        # Map to canonical names
        metric = METRIC_ALIASES.get(metric_phrase)
        op = COMPARATOR_ALIASES.get(comp_phrase)
        value = float(value_str)
        
        return {
            "metric": metric,
            "op": op,  # gt, lt, ge, le, eq
            "value": value,
            "raw_metric_phrase": metric_phrase,
            "raw_comp_phrase": comp_phrase
        }
    
    return None
```

### OData Filter Building

Azure AI Search uses OData syntax for filters. The application converts detected components to OData:

```python
def _build_metric_filter_odata(metric_filter: Dict[str, Any]) -> str:
    """
    Convert filter spec to OData syntax:
    {"metric": "PE", "op": "lt", "value": 50.0} → "PE lt 50.0"
    {"metric": "PE", "op": "gt", "value": 20.0} → "PE gt 20.0"
    """
    if not metric_filter:
        return None
    
    metric = metric_filter["metric"]
    op = metric_filter["op"]
    value = metric_filter["value"]
    
    return f"{metric} {op} {value}"
```

### Collection Filter for Multi-Index

For the `AllIndices` collection field, the application uses OData lambda expressions:

```python
# Single index filter
filter_str = "AllIndices/any(i: i eq 'NIFTY50')"

# Combined with metric filter
filter_str = "AllIndices/any(i: i eq 'NIFTY50') and PE lt 20.0"
```

The `any()` function checks if **any** element in the collection matches the condition, enabling multi-index support.

---

## Decision Tree for Query Mode Selection

```
1. Is there a stock name?
   └─ Yes → Is there a metric?
       └─ Yes → single_stock_metric
       └─ No → single_stock_overview

2. Is there an index code AND metric filter?
   └─ Yes → list_by_metric_filter (with index)

3. Is there a sector AND metric filter?
   └─ Yes → Has listing context?
       └─ Yes → list_by_sector_with_filter
       └─ No → (falls through)

4. Is there a sector only?
   └─ Yes → Has listing context?
       └─ Yes → list_by_sector
       └─ No → (falls through)

5. Is there a metric filter only?
   └─ Yes → list_by_metric_filter (no index)

6. Is there an index code only?
   └─ Yes → list_by_index

7. Default: single_stock_overview
```

---

## Code Structure and Implementation Details

### Modular Architecture

The codebase uses a **shared module architecture** to eliminate code duplication and improve maintainability:

```
┌─────────────────────────────────────────────────────────────┐
│                   User Input (Natural Language)              │
└────────────────┬────────────────────────────────────────────┘
                 │
    ┌────────────▼──────────────┐
    │  query_parser.py (521 lines) │  ← Shared Module
    │  • Parse natural language     │
    │  • Detect metrics, sectors    │
    │  • Return structured spec     │
    └────────────┬──────────────────┘
                 │
    ┌────────────▼─────────────────┐
    │ payload_builder.py (188 lines)│  ← Shared Module
    │ • Convert spec to Azure JSON  │
    │ • Build OData filters         │
    │ • Handle 7 query modes        │
    └────────────┬─────────────────┘
                 │
       ┌─────────┴──────────┐
       │                    │
  ┌────▼─────┐      ┌──────▼────┐
  │ app.py   │      │ app_sdk.py │
  │ (206 lines)│    │ (300 lines) │
  │ REST API │      │ Python SDK │
  └────┬─────┘      └──────┬────┘
       │                   │
       └─────────┬─────────┘
                 │
         ┌───────▼──────────┐
         │ streamlit_app.py  │
         │ (512 lines)       │
         │ Web UI Layer      │
         └───────────────────┘
```

**Code Reduction Results**:
- `app.py`: 950 lines → 206 lines (78% reduction)
- `app_sdk.py`: 774 lines → 300 lines (61% reduction)
- **Total**: Eliminated ~1,218 lines of duplicated code
- **Shared modules**: 709 lines (single source of truth)

---

### Core Modules

#### 1. `query_parser.py` - Natural Language Processing (521 lines)

**Purpose**: Convert natural language queries into structured specifications.

**Key Components**:

```python
# Configuration dictionaries (lines 15-232)
METRIC_ALIASES = {
    "PE": ["pe", "p/e", "price to earning", ...],
    "Market Cap": ["market cap", "mcap", "market capitalization", ...],
    # ... 20+ financial metrics with synonyms
}

def detect_metric(user_input: str) -> Optional[str]:
    """
    Longest-match strategy to detect financial metrics.
    Example: "price to earning" -> "PE"
    """

def detect_sector(user_input: str) -> Optional[str]:
    """
    Detects sector with company-name protection.
    Example: "energy sector" -> "Energy"
    (but "reliance energy" won't detect "Energy")
    """

def parse_user_query(user_input: str) -> dict:
    """
    Core routing logic with 9 priority modes:
    1. single_stock_metric: "pe of reliance"
    2. single_stock_overview: "reliance" or "show me reliance"
    3. list_by_index: "nifty 50"
    4. list_by_sector: "sector materials"
    5. list_by_index_and_sector: "nifty 50 materials"
    6. list_by_sector_and_metric_filter: "materials with pe under 20"
    7. list_by_metric_filter: "stocks with pe between 10 and 20"
    8. list_all: "all stocks" or "*"
    9. fallback: Generic stock name search
    
    Returns: {"mode": "...", "stock_query": "...", "metric": "...", ...}
    """
```

**When to Use Directly**:
- Testing query parsing logic
- Building custom UIs with different execution backends
- Debugging query interpretation issues

---

#### 2. `payload_builder.py` - Azure Search JSON Builder (188 lines)

**Purpose**: Convert query specifications into Azure AI Search REST API payloads.

**Key Components**:

```python
def build_metric_filter_odata(filter_dict: dict) -> str:
    """
    Converts filter dict to OData filter string.
    Example: {"metric": "PE", "op": "under", "value": 20}
          -> "PE lt 20"
    """

def build_search_payload_from_spec(spec: dict) -> dict:
    """
    Handles 7 query modes:
    
    Mode 1: single_stock_metric
      Input: "pe of reliance"
      Output: {"search": "reliance", "select": "PE,Name", "top": 1}
    
    Mode 2: single_stock_overview
      Input: "reliance"
      Output: {"search": "reliance", "select": "*", "top": 1}
    
    Mode 3: list_by_index
      Input: "nifty 50"
      Output: {"search": "*", "filter": "Index_Code eq 'NIFTY 50'"}
    
    Mode 4: list_by_sector
      Input: "materials"
      Output: {"search": "*", "filter": "Sector eq 'Materials'"}
    
    ... and 3 more modes for complex filters
    
    Returns: Azure Search JSON payload ready for REST API
    """
```

**When to Use Directly**:
- Testing payload generation logic
- Building custom backends (e.g., other search engines)
- Understanding Azure Search query syntax

---

#### 3. `app.py` - REST API Implementation (206 lines, was 950)

**Purpose**: Direct HTTP communication with Azure AI Search using Python `requests` library.

**Key Components**:

```python
# Import shared modules
from query_parser import parse_user_query
from payload_builder import build_search_payload_from_spec

# Global session for connection pooling
_http_session = requests.Session()

def execute_search_request(req: dict) -> dict:
    """
    Executes Azure AI Search request using persistent HTTP session.
    Connection pooling improves performance by reusing TCP connections.
    
    Performance: ~160-350ms per query (after initial connection)
    """
    response = _http_session.post(
        req["url"],
        headers=req["headers"],
        json=req["json"],
        timeout=10
    )
    return response.json()

def build_search_request_from_user_input(user_input: str, ...) -> dict:
    """
    Orchestrates the query processing pipeline:
    1. Parse user input -> spec (via query_parser)
    2. Build Azure Search payload (via payload_builder)
    3. Wrap in HTTP request (URL, headers, JSON)
    
    Returns: Complete HTTP request dict ready for execution
    """
    spec = parse_user_query(user_input)
    payload = build_search_payload_from_spec(spec)
    # ... builds URL, headers
    return {"spec": spec, "url": url, "headers": headers, "json": payload}
```

**When to Use**:
- Integration with non-Python systems
- Custom HTTP middleware requirements
- Learning Azure Search REST API
- Maximum control over HTTP request/response

---

#### 4. `app_sdk.py` - Python SDK Implementation (300 lines, was 774)

**Purpose**: Pythonic interface using official Azure Search Python SDK.

**Key Components**:

```python
# Import shared modules
from query_parser import parse_user_query
from payload_builder import build_search_payload_from_spec

from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential

# Singleton pattern for client reuse
_search_client = None

def get_search_client() -> SearchClient:
    """
    Creates or returns cached SearchClient instance.
    SDK handles connection pooling automatically.
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

def execute_search_request_sdk(spec: dict, search_text: str, 
                                filter_expr: Optional[str], ...) -> dict:
    """
    Executes search using SDK's native methods.
    Returns results in same format as REST API for compatibility.
    
    Performance: Similar to REST API (~160-350ms)
    """
    client = get_search_client()
    results = client.search(
        search_text=search_text,
        filter=filter_expr,
        select=select_fields,
        top=top,
        include_total_count=include_total_count
    )
    # Convert SDK results to REST API format
    return format_response(results)

def build_search_request_from_user_input_sdk(user_input: str) -> dict:
    """
    Orchestrates the SDK query pipeline:
    1. Parse user input -> spec (via query_parser)
    2. Build Azure Search payload (via payload_builder)
    3. Convert REST payload to SDK parameters
    
    Returns: SDK parameters ready for execution
    """
    spec = parse_user_query(user_input)
    payload = build_search_payload_from_spec(spec)
    # Convert REST params to SDK params
    return {
        "spec": spec,
        "search_text": payload.get("search", "*"),
        "filter": payload.get("filter"),
        "select": payload.get("select", "").split(","),
        "top": payload.get("top", 50)
    }

def execute_search_from_user_input_sdk(user_input: str) -> dict:
    """
    Complete wrapper combining parsing and SDK execution.
    Simplest interface for SDK-based queries.
    """
    params = build_search_request_from_user_input_sdk(user_input)
    return execute_search_request_sdk(**params)
```

**When to Use**:
- Python-native applications
- Better type safety with IDE autocomplete
- Easier maintenance and updates
- Cleaner code with less boilerplate
- Automatic credential refresh handling

**SDK Advantages**:
- ✅ Automatic retry logic for transient failures
- ✅ Built-in connection pooling and management
- ✅ Type hints and IntelliSense support
- ✅ Consistent error handling patterns
- ✅ Supports Azure Identity authentication

---

#### 5. `streamlit_app.py` - Web UI (512 lines)

**Purpose**: Modern web interface with Streamlit framework.

**Key Components**:

```python
# Backend flexibility - choose REST API or SDK
from app import (
    build_search_request_from_user_input,
    execute_search_request
)
# Alternative SDK import (commented):
# from app_sdk import (
#     build_search_request_from_user_input_sdk as build_search_request_from_user_input,
#     execute_search_from_user_input_sdk as execute_search_request
# )

# UI displays results with performance metrics
time_parsing_ms = (t2_before_search - t1_input_received) * 1000
time_search_ms = (t3_response_received - t2_before_search) * 1000
```

**Features**:
- 📱 Responsive design with modern CSS
- 📊 Performance metrics display
- 🎨 Color-coded metric cards
- 🔍 Query specification debugging
- 📈 Real-time search results

**Run**: `streamlit run streamlit_app.py`

---

### Module Responsibilities Summary

| Module | Lines | Responsibility | Used By |
|--------|-------|----------------|---------|
| `query_parser.py` | 521 | Natural language → structured spec | app.py, app_sdk.py |
| `payload_builder.py` | 188 | Structured spec → Azure JSON | app.py, app_sdk.py |
| `app.py` | 206 | REST API execution layer | streamlit_app.py |
| `app_sdk.py` | 300 | Python SDK execution layer | streamlit_app.py (optional) |
| `streamlit_app.py` | 512 | Web UI presentation layer | End users |

**Design Principles**:
- ✅ **Single Source of Truth**: All parsing logic in `query_parser.py`
- ✅ **Separation of Concerns**: Parsing, payload building, and execution are separate
- ✅ **DRY (Don't Repeat Yourself)**: Eliminated 1,218 lines of duplication
- ✅ **Testability**: Each module can be tested independently
- ✅ **Flexibility**: Easy to swap REST API ↔ SDK without changing parsing logic

---

#### 3. `streamlit_app.py` - Web Interface

**Purpose**: Modern, responsive web UI for end-users and demos.

**Key Components**:

```python
import streamlit as st
from app import build_search_request_from_user_input, execute_search_request

# Configuration caching (lines 209-220)
@st.cache_data
def get_config():
    """Cache environment variables to avoid repeated .env loads"""
    return {
        'endpoint': os.getenv("AZURE_SEARCH_ENDPOINT"),
        'index': os.getenv("AZURE_SEARCH_INDEX_NAME"),
        'api_key': os.getenv("AZURE_SEARCH_API_KEY")
    }

# Main search flow
if search_button or user_query:
    t0_total_start = time.time()  # Total execution timer
    
    # Build request using app.py
    req = build_search_request_from_user_input(user_query, ...)
    
    t2_before_search = time.time()
    result = execute_search_request(req)
    t3_response_received = time.time()
    
    # Display results with performance metrics
    st.markdown(f"Search Time: {(t3_response_received - t2_before_search) * 1000:.1f}ms")
    st.dataframe(results)  # Interactive results table
```

**UI Features**:
- **Query Analysis Cards**: Shows detected mode, index, sector, metrics
- **Performance Metrics**: Three cards showing processing, search, and total time
- **Results Table**: Interactive dataframe with sorting/filtering
- **Technical Details**: Collapsible section with request/response JSON
- **Responsive Design**: Works on desktop and mobile devices
- **Modern Styling**: Gradient header, smooth animations, clean typography

**Customization**:
To use SDK version instead of REST API:
```python
# Change imports at top of streamlit_app.py
from app_sdk import execute_search_from_user_input_sdk

# Update search execution
result = execute_search_from_user_input_sdk(user_query)
```

---

### Shared Query Parsing Logic

Both `app.py` and `app_sdk.py` share identical query parsing functions (lines 290-600):

#### **Core Parsing Functions**

```python
def parse_user_query(user_input: str) -> Dict[str, Any]:
    """
    Master router: Analyzes input and determines query mode.
    
    Priority order (critical for correct interpretation):
    1. Index + Metric filter → list_by_metric_filter
    2. Sector + Metric filter → list_by_sector_with_filter
    3. Index alone → list_by_index
    4. Sector alone → list_by_sector
    5. Metric filter → list_by_metric_filter (all stocks)
    6. Stock + Metric → single_stock_metric
    7. Stock alone → single_stock_overview
    
    Returns spec dict with mode and parameters.
    """

def detect_metric(text_lower: str) -> Optional[Dict[str, Any]]:
    """
    Searches for metric keywords using longest-match strategy.
    Handles variations: "pe", "p/e", "price to earnings"
    """

def detect_index_code(text_lower: str) -> Optional[str]:
    """
    Detects index mentions: "nifty 50", "nifty bank", etc.
    Prioritizes longer matches to avoid false positives.
    """

def detect_sector(text_lower: str, original_text: str) -> Optional[str]:
    """
    Identifies sector with smart heuristics to avoid false positives.
    
    Example: "axis bank" should NOT trigger "bank" sector
    Logic: If sector keyword is preceded by a non-modifier word
           in a short query, it's likely a company name.
    """

def detect_metric_filter(text_lower: str) -> Optional[Dict[str, Any]]:
    """
    Regex-based extraction of metric comparisons.
    Pattern: <metric> <operator> <value>
    Example: "pe less than 20" → {"metric": "PE", "op": "lt", "value": 20.0}
    """

def extract_stock_query(original: str, text_lower: str, 
                        metric_info: Optional[Dict]) -> Optional[str]:
    """
    Extracts stock name by removing stopwords and metric keywords.
    Preserves company names even with sector keywords (e.g., "axis bank").
    """
```

#### **Priority Order Importance**

The order of condition checking in `parse_user_query` is crucial:

```python
# CORRECT: Check index BEFORE sector
if index_code and metric_info is None:
    return {"mode": "list_by_index", ...}

if sector is not None:
    return {"mode": "list_by_sector", ...}

# This ensures "niftyenergy stocks" matches index, not sector
```

---

## Performance Considerations

- **Synonym Lookup**: Happens at query time in Azure AI Search's analyzer pipeline (no application overhead)
- **Pattern Matching**: Lightweight keyword detection using dictionaries (O(n) complexity)
- **Filter Efficiency**: Azure AI Search indexes all filterable fields for fast lookups
- **Collection Filters**: Efficiently handled by Azure AI Search's inverted index structure

### HTTP Connection Pooling Optimization

**Issue Identified**: Initial implementation created a new HTTP connection for every Azure AI Search API call, resulting in:
- First request: ~700-800ms (includes connection setup, SSL handshake, DNS lookup)
- Subsequent requests: ~600-700ms (repeated connection overhead)

**Solution Implemented**: Added persistent session with connection pooling in `app.py` (lines 13-15, 29):

```python
# Create a global session for connection pooling (reuse connections)
_http_session = requests.Session()

def execute_search_request(req: dict) -> dict:
    response = _http_session.post(...)  # Uses persistent session
```

**Performance Improvement**:
- First request: ~700-800ms (one-time connection setup)
- Subsequent requests: **~160-350ms** (80% faster via connection reuse)

**Impact**:
- Console app: Faster repeated queries in interactive mode
- Streamlit app: Significantly faster searches after initial load
- Matches PowerShell/curl performance (~350ms) for steady-state requests

---

## Advantages of This Approach

1. **No LLM Required**: Lower latency, no API costs, deterministic behavior
2. **Transparent Logic**: Easy to debug and understand query transformations
3. **Predictable Performance**: No variability from LLM token processing
4. **Cost Effective**: Only Azure AI Search costs, no LLM API charges
5. **Extendable**: Easy to add new patterns, metrics, or indices by updating dictionaries

---

## Limitations

1. **Fixed Patterns**: Cannot understand completely novel query structures
2. **No Reasoning**: Cannot answer questions that require calculation or inference
3. **Limited Context**: Cannot maintain conversation history or understand pronouns
4. **Exact Match Required**: User input must contain recognizable keywords

---

## Future Enhancements

- Add caching layer for frequently queried stocks
- Implement real-time price updates from market data APIs
- Add more complex query patterns (e.g., "top 10 stocks by market cap in energy sector")
- Support for date range filters (e.g., "stocks with PE ratio below 20 in last quarter")
- Export results to CSV/Excel

---

## License

MIT License

---

## Contact

For questions or support, please open an issue in the repository.

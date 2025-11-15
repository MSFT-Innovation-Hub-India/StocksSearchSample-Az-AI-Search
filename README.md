# Stock Search Application using Azure AI Search

## Overview

This application demonstrates how to build an intelligent stock search interface using Azure AI Search. It allows users to query stock information using natural language without requiring any Large Language Model (LLM) or Small Language Model (SLM). The application uses pattern matching and Azure AI Search's powerful features like synonyms and collection filters to understand user intent and retrieve relevant results.

## Features

- **Natural Language Queries**: Query stocks using plain English (e.g., "sector materials with PE under 100")
- **Synonym Support**: Search for stocks using various names and abbreviations
- **Multi-Index Support**: Stocks can belong to multiple indices (NIFTY50, NIFTY100, sector-specific indices)
- **Flexible Filtering**: Filter by sector, index, PE ratio, market cap, and other metrics
- **No LLM Required**: Uses pattern matching and Azure AI Search capabilities for intent detection

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

### 7. Run the Application

```bash
python app.py
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

## Performance Considerations

- **Synonym Lookup**: Happens at query time in Azure AI Search's analyzer pipeline (no application overhead)
- **Pattern Matching**: Lightweight keyword detection using dictionaries (O(n) complexity)
- **Filter Efficiency**: Azure AI Search indexes all filterable fields for fast lookups
- **Collection Filters**: Efficiently handled by Azure AI Search's inverted index structure

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

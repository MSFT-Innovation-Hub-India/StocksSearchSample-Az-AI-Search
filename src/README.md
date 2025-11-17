# Source Code Directory

This directory contains the core modules for Azure AI Search and Cosmos DB integration.

## Modules

### query_parser.py
Parses natural language queries into structured search specifications.
- Detects stock symbols, company names
- Identifies sectors and indices
- Recognizes metric queries (PE, PB, etc.)
- Maps natural language to search parameters

### payload_builder.py
Builds Azure Search REST API payloads from parsed query specifications.
- Converts specifications to OData filters
- Constructs search requests
- Handles field selection
- Supports various query modes (single stock, sector, index, etc.)

### db_parser.py
Provides dynamic query capabilities for Azure Cosmos DB.
- Connection pooling using singleton pattern
- Latest data queries with dynamic field selection
- Aggregation queries (MIN/MAX) with optimization
- Comprehensive performance metrics
- Natural language field mapping

## Usage
These modules are imported by:
- `search_app_cosmos.py` (main Cosmos DB integration app in root)
- `search_app_sdk.py` (Azure Search SDK app in root)
- `apps/app.py` (REST API app)
- `apps/streamlit_app.py` (web UI)

## Architecture
```
User Query → query_parser → payload_builder → Azure AI Search
                                                      ↓
                                                 SymbolRaw
                                                      ↓
User Query → field detection → db_parser → Cosmos DB → Results
```

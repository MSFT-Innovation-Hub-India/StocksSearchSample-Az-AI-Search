# Stock Query Request Flows

This document captures the end-to-end request flow for both stock search experiences:

1. **Azure AI Search only** (implemented in `search_app_sdk.py`)
2. **Azure AI Search + Azure Cosmos DB** (implemented in `search_app_cosmos.py`)

It highlights where user input is parsed, how synonym maps and `AllIndices` collection filters are applied, and how Cosmos DB stores and retrieves the live time-series data.

---

## Azure AI Search–Only Flow (`search_app_sdk.py`)

- `src/query_parser.parse_user_query` is the component that interprets natural language input, extracts stock/entity hints, desired metrics, and filters.
- `src.payload_builder.build_search_payload_from_spec` translates that spec into Azure AI Search parameters, including search text, OData filters, selected fields, and `AllIndices` collection filters when the query targets specific indices.
- Azure AI Search uses a synonym map so that names like "Reliance Industries" or "RIL" resolve to the canonical stock symbol.
- The `AllIndices` field is modeled as `Collection(Edm.String)`; filters such as `any(i: i eq 'NIFTY 50')` ensure the result set restricts to stocks that exist in the requested index, covering scenarios where the same stock belongs to multiple indices.

```
     ┌───────────┐      ┌──────────────────────┐      ┌────────────────────────────┐
     │  End User │ ---> │ search_app_sdk.py    │ ---> │ Response + Timing          │
     │  (CLI/UI) │      │ Interactive loop     │      │ (printed / Streamlit)      │
     └───────────┘      │  • capture query     │      └────────────────────────────┘
                        │  • log timestamps    │
                        └───────────────┬──────┘
                                        │ user text
                                        ▼
                                    ┌──────────────────────────┐
                                    │ query_parser.parse_user… │
                                    │  • detect stocks         │
                                    │  • infer metrics/filters │
                                    └────────┬─────────────────┘
                                             │ structured spec
                                             ▼
                                    ┌──────────────────────────┐
                                    │ payload_builder.build…   │
                                    │  • search text           │
                                    │  • AllIndices filter     │
                                    │  • select fields / top   │
                                    └────────┬─────────────────┘
                                             │ Azure AI Search request
                                             ▼
                        ┌───────────────────────────────────────────────┐
                        │ Azure AI Search Index                         │
                        │  • Documents: Name, Symbol, SymbolRaw,        │
                        │    AllIndices[] collection, metrics           │
                        │  • Synonym map: "Reliance" ↔ "RELIANCE"       │
                        │  • Collection filter: any(AllIndices eq …)    │
                        └────────┬──────────────────────────────────────┘
                                 │ ranked docs + @odata.count
                                 ▼
                        ┌───────────────────────────────────────────────┐
                        │ Formatter (search_app_sdk.py)                 │
                        │  • convert iterator→dict                      │
                        │  • attach spec & timing                       │
                        └───────────────────────────────────────────────┘
```

**Sample data as it progresses**

```
Step 0 - User input
    "Show NIFTY 50 banking stocks with PE < 20"

Step 1 - Parsed spec (simplified)
    {
        "indices": ["NIFTY 50"],
        "sector": "Banking",
        "filters": {"pe_ratio": {"lt": 20}},
        "metrics": ["Stock_Name", "PE_Ratio"]
    }

Step 2 - Built search payload
    search: "banking stocks"
    filter: "(Sector eq 'Banking') and (PE_Ratio lt 20) and AllIndices/any(i: i eq 'NIFTY 50')"
    select: "Stock_Name,Symbol,PE_Ratio,AllIndices"
    top: 20

Step 3 - Azure AI Search document excerpt
    {
        "Stock_Name": "HDFC Bank Ltd",
        "Symbol": "HDFCBANK",
        "SymbolRaw": "HDFCBANK.NS",
        "AllIndices": ["NIFTY 50", "NIFTY BANK"],
        "PE_Ratio": 19.2
    }

Step 4 - Response snippet surfaced to user
    ┌──────────────┬───────────┬──────────┬────────────────────────────┐
    │ Stock_Name   │ Symbol    │ PE_Ratio │ AllIndices                 │
    ├──────────────┼───────────┼──────────┼────────────────────────────┤
    │ HDFC Bank…   │ HDFCBANK  │ 19.2     │ ["NIFTY 50","NIFTY BANK"]  │
    └──────────────┴───────────┴──────────┴────────────────────────────┘
```

**Key behaviors**
- Synonym matching ensures free-form user strings map to the correct stock symbol without the user needing to type the symbol explicitly.
- `AllIndices` filters work alongside other filters (sector, ratios, etc.) so multi-index stocks appear once but still honor the user-requested index scope.
- Response timing metadata helps operators see parsing vs. search latency.

---

## Azure AI Search + Cosmos DB Flow (`search_app_cosmos.py`)

- `CosmosDynamicQueryApp.parse_fields_from_query` and `detect_aggregation` parse the user input to decide which dynamic fields (Price, Change, ChangePercent) or aggregations (MIN/MAX) are requested.
- `resolve_symbol_from_ai_search` runs a targeted Azure AI Search lookup (re-using `parse_user_query`) to fetch the canonical `SymbolRaw` and `Symbol`. Synonym matching and `AllIndices` filtering work the same as in the SDK-only flow.
- Once the symbol is known, the app queries Cosmos DB via `src.db_parser.get_latest_stock_data` or `get_stock_aggregation` to return the latest or aggregated time-series metrics.
- Cosmos DB stores data keyed by `SymbolRaw` and timestamp, with a composite index on `(SymbolRaw ASC, DateTime DESC)` to accelerate fetching the newest record or running ordered aggregations.

```
     ┌───────────┐      ┌────────────────────────────┐       ┌────────────────────────┐
     │  End User │ ---> │ CosmosDynamicQueryApp       │ ---> │ Response + Timings     │
     │  (CLI/UI) │      │ search_app_cosmos.py        │      │ (console output)       │
     └───────────┘      │  • parse fields / aggs      │      └────────────────────────┘
                        │  • orchestrate search+DB    │
                        └────┬────────────────────────┘
                             │ user text
                             ▼
                 ┌────────────────────────────────┐
                 │ parse_fields_from_query        │
                 │ detect_aggregation             │
                 └──────────┬─────────────────────┘
                            │ requested fields + agg
                            ▼
                 ┌────────────────────────────────┐
                 │ resolve_symbol_from_ai_search  │
                 │  • uses query_parser           │
                 │  • posts to Azure AI Search    │
                 │  • synonym map + AllIndices    │
                 └──────────┬─────────────────────┘
                            │ SymbolRaw, Symbol
                            ▼
                 ┌────────────────────────────────┐
                 │ Cosmos DB (stock time-series)  │
                 │  • Partition/PK: SymbolRaw     │
                 │  • Composite idx: SymbolRaw,   │
                 │    DateTime                    │
                 │  • Metrics: Price, Change, %   │
                 └──────────┬─────────────────────┘
                            │ latest row / aggregation
                            ▼
                 ┌────────────────────────────────┐
                 │ Result builder                 │
                 │  • include requested fields    │
                 │  • show timing (parse/search/  │
                 │    cosmos/total)               │
                 └────────────────────────────────┘
```

**Sample data as it progresses**

```
Step 0 - User input
    "What is the highest price for Infosys in NIFTY 100?"

Step 1 - Field parsing & aggregation detection
    requested_fields: ["Price"]
    aggregation: ("MAX", "Price")

Step 2 - AI Search symbol resolution payload
    search: "Infosys"
    searchFields: "SymbolRaw,Name,Symbol"
    filter: "AllIndices/any(i: i eq 'NIFTY 100')"
    top: 1

Step 3 - AI Search response excerpt
    {
        "Name": "Infosys Ltd",
        "Symbol": "INFY",
        "SymbolRaw": "INFY.NS",
        "AllIndices": ["NIFTY 50", "NIFTY 100", "NIFTY IT"]
    }

Step 4 - Cosmos DB aggregation request
    partition key: SymbolRaw = "INFY.NS"
    query: SELECT VALUE MAX(c.Price) FROM c WHERE c.SymbolRaw = 'INFY.NS'

Step 5 - Cosmos DB document snapshot
    {
        "id": "INFY.NS|2024-09-12T09:15:00Z",
        "SymbolRaw": "INFY.NS",
        "DateTime": "2024-09-12T09:15:00Z",
        "Price": 1525.65,
        "Change": 8.75,
        "ChangePercent": 0.58
    }

Step 6 - Response snippet
    ┌──────────┬─────────┬──────────────┬──────────────┬───────────────┐
    │ Symbol   │ Metric  │ Value        │ Source       │ Notes         │
    ├──────────┼─────────┼──────────────┼──────────────┼───────────────┤
    │ INFY.NS  │ Price   │ 1525.65      │ Cosmos DB    │ MAX over data │
    └──────────┴─────────┴──────────────┴──────────────┴───────────────┘
    Timings: parsing 12ms | AI Search 45ms | Cosmos 30ms | total 95ms
```

**Key behaviors**
- Azure AI Search remains the source of truth for resolving the correct stock symbol; Cosmos DB never guesses symbols independently.
- The synonym map ensures that "Infosys", "Infy", or "INFOSYS LTD" all resolve to the same `SymbolRaw`, which matches the partition key stored in Cosmos DB.
- If the user references an index ("NIFTY 100"), the `AllIndices` collection filter limits the AI Search candidate list before Cosmos DB lookups, preventing collisions when the same company trades on multiple indices.
- Cosmos DB's composite index on `(SymbolRaw, DateTime)` optimizes both the "latest" query pattern (top 1 by DateTime per symbol) and aggregation scans constrained to a symbol and time window.
- Performance metrics (field parsing, AI Search lookup, Cosmos query, total) make it easy to see which hop dominates latency when troubleshooting.

---

## Additional Notes

- Both flows rely on shared modules in `src/` so that parsing, payload building, and synonym-aware logic stay consistent across interfaces.
- Synonym definitions should include company names, tickers, colloquial abbreviations, and historical names to maintain high recall.
- Maintaining the `AllIndices` collection field in Azure AI Search documents ensures downstream experiences can add or remove index-level filters without re-modeling data.
- For Cosmos DB, consider TTL or archiving strategies if time-series data grows quickly; the composite index already reduces query RU costs for the hot path.

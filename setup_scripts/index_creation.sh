curl -X POST \
  "https://ai-search-vector-001.search.windows.net/indexes?api-version=2025-09-01" \
  -H "Content-Type: application/json" \
  -H "api-key: <YOUR-ADMIN-KEY>" \
  --data-binary '{
    "name": "stocks-search-index",
    "fields": [
      {
        "name": "Symbol",
        "type": "Edm.String",
        "key": true,
        "searchable": true,
        "filterable": true,
        "sortable": true,
        "facetable": true
      },
      {
        "name": "SymbolRaw",
        "type": "Edm.String",
        "searchable": true,
        "filterable": false,
        "sortable": false,
        "facetable": false,
        "synonymMaps": ["stock-synonyms"]
      },
      {
        "name": "Name",
        "type": "Edm.String",
        "searchable": true,
        "filterable": false,
        "sortable": false,
        "facetable": false,
        "synonymMaps": ["stock-synonyms"]
      },
      {
        "name": "Sector",
        "type": "Edm.String",
        "searchable": true,
        "filterable": true,
        "sortable": false,
        "facetable": true
      },
      {
        "name": "MarketCapCr",
        "type": "Edm.Double",
        "searchable": false,
        "filterable": true,
        "sortable": true,
        "facetable": true
      },
      {
        "name": "PE",
        "type": "Edm.Double",
        "searchable": false,
        "filterable": true,
        "sortable": true,
        "facetable": true
      },
      {
        "name": "PB",
        "type": "Edm.Double",
        "searchable": false,
        "filterable": true,
        "sortable": true,
        "facetable": true
      },
      {
        "name": "EPS",
        "type": "Edm.Double",
        "searchable": false,
        "filterable": true,
        "sortable": true,
        "facetable": true
      },
      {
        "name": "DividendYieldPct",
        "type": "Edm.Double",
        "searchable": false,
        "filterable": true,
        "sortable": true,
        "facetable": true
      },
      {
        "name": "AllIndices",
        "type": "Collection(Edm.String)",
        "searchable": false,
        "filterable": true,
        "sortable": false,
        "facetable": true
      }
    ]
  }'



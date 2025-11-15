curl -X POST "https://ai-search-vector-001.search.windows.net/indexers?api-version=2025-09-01" -H "Content-Type: application/json" -H "api-key: <search-api-key>" --data-binary '{
  "name": "stocks-csv-indexer",
  "dataSourceName": "stocks-csv-datasource",
  "targetIndexName": "stocks-search-index",
  "parameters": {
    "configuration": {
      "parsingMode": "delimitedText",
      "firstLineContainsHeaders": true,
      "delimitedTextDelimiter": ","
    }
  },
  "fieldMappings": [
    {
      "sourceFieldName": "AllIndices",
      "targetFieldName": "AllIndices",
      "mappingFunction": {
        "name": "jsonArrayToStringCollection"
      }
    }
  ]
}'
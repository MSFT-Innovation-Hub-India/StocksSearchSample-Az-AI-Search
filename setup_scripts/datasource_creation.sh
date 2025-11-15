curl -X POST \
  "https://ai-search-vector-001.search.windows.net/datasources?api-version=2025-09-01" \
  -H "Content-Type: application/json" \
  -H "api-key: <YOUR-ADMIN-KEY>" \
  --data-binary '{
    "name": "stocks-csv-datasource",
    "type": "azureblob",
    "credentials": {
      "connectionString": "<BLOB_CONNECTION_STRING>"
    },
    "container": {
      "name": "stocks-container",
      "query": "" 
    }
  }'

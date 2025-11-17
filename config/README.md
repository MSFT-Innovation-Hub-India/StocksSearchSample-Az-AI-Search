# Configuration Directory

This directory contains configuration files for the application.

## Files

### cosmos_config.json
Configuration for Cosmos DB field mappings and natural language aliases.

**Structure:**
```json
{
  "fields": {
    "FieldName": {
      "cosmos_field": "ActualCosmosDBFieldName",
      "aliases": ["alias1", "alias2", "natural language phrase"],
      "description": "Description of the field"
    }
  },
  "always_return": ["Field1", "Field2"]
}
```

**Current Fields:**
- **Price**: Current stock price
- **Change**: Price change value
- **ChangePercent**: Percentage change in price

**Usage:**
The `search_app_cosmos.py` uses this configuration to:
1. Map natural language queries to Cosmos DB fields
2. Support multiple aliases for each field (e.g., "price", "current price", "stock price")
3. Ensure essential fields (Symbol, DateTime) are always returned

## Adding New Fields
To add support for new Cosmos DB fields:
1. Add a new entry to the `fields` object
2. Specify the `cosmos_field` name (must match Cosmos DB schema)
3. List all natural language `aliases` users might use
4. Provide a helpful `description`
5. Update `always_return` if the field should always be included

# Data Import Directory

This directory contains scripts for importing dynamic stock price data into Azure Cosmos DB.

## Scripts

### import_dynamic_data.py
Imports real-time stock price data from CSV files into Azure Cosmos DB.

**Features:**
- Uses managed identity authentication (DefaultAzureCredential)
- Idempotent upsert operations (safe to re-run)
- Supports querying latest prices
- Automatic partition key handling

**Requirements:**
- Azure Cosmos DB account with RBAC enabled
- User/Managed Identity with "Cosmos DB Built-in Data Contributor" role
- Azure CLI login or managed identity configured

**Usage:**
```powershell
cd data_import
python import_dynamic_data.py
```

**CSV Format:**
The input CSV should contain:
- Symbol: Stock ticker symbol
- DateTime: Timestamp (ISO format)
- Price: Current price
- Change: Price change
- ChangePercent: Percentage change

## Environment Variables
Configure these in the root `.env` file:
- `COSMOS_ENDPOINT`: Cosmos DB endpoint URL
- `DATABASE_NAME`: Database name
- `CONTAINER_NAME`: Container name

The script automatically looks for `.env` in the parent directory.

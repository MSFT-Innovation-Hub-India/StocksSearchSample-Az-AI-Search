# Apps Directory

This directory contains optional web and API applications for the stock data search system.

## Applications

### app.py
REST API-based search application using direct HTTP requests to Azure AI Search.
- Uses connection pooling for performance
- Direct control over HTTP requests
- Minimal dependencies

**Run:**
```powershell
cd apps
python app.py
```

### app_sdk.py
Azure SDK-based search application using the official Azure Search Python SDK.
- Type-safe API
- Automatic connection pooling
- Built-in retry logic
- Pythonic interface

**Run:**
```powershell
cd apps
python app_sdk.py
```

### streamlit_app.py
Web-based UI for the stock search application built with Streamlit.
- Interactive web interface
- Visual stock data presentation
- Can use either REST API or SDK backend

**Run:**
```powershell
cd apps
streamlit run streamlit_app.py
```

## Note
These apps are optional and primarily for demonstration/experimentation. 

The main applications are in the root directory:
- `search_app_cosmos.py` - Cosmos DB + AI Search integration (recommended)
- `search_app_sdk.py` - Azure Search SDK implementation

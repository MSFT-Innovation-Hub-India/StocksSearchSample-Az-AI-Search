import streamlit as st
import time
import json

# ============================================================
# Backend Import Configuration
# ============================================================
# This application supports two backend implementations:
#
# Option 1 (DEFAULT): REST API with manual connection pooling
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from apps.app import (
    build_search_request_from_user_input,
    execute_search_request
)
# Option 2: Azure SDK with automatic connection pooling
# from apps.app_sdk import (
#     build_search_request_from_user_input_sdk as build_search_request_from_user_input,
#     execute_search_from_user_input_sdk as execute_search_request
# )
#
# Both implementations provide identical functionality with similar performance.
# Choose based on your preference:
#   - REST API (app.py): Direct HTTP control, minimal dependencies
#   - SDK (app_sdk.py): Type-safe, Pythonic, auto-retry capabilities
# ============================================================

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="Stock Search Assistant",
    page_icon="",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for modern, responsive design
st.markdown("""
<style>
    /* Import modern font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Global styles */
    * {
        font-family: 'Inter', sans-serif;
    }
    
    /* Main container */
    .main {
        padding: 2rem 1rem;
        max-width: 1400px;
        margin: 0 auto;
    }
    
    /* Header styling */
    .header-container {
        text-align: center;
        padding: 2rem 0 3rem 0;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 20px;
        margin-bottom: 2rem;
        box-shadow: 0 10px 40px rgba(102, 126, 234, 0.3);
    }
    
    .header-title {
        color: white;
        font-size: 2.5rem;
        font-weight: 700;
        margin: 0;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
    }
    
    .header-subtitle {
        color: rgba(255, 255, 255, 0.9);
        font-size: 1.1rem;
        margin-top: 0.5rem;
        font-weight: 400;
    }
    
    /* Search input styling */
    .stTextInput > div > div > input {
        border-radius: 15px;
        border: 2px solid #e0e0e0;
        padding: 1rem 1.5rem;
        font-size: 1.05rem;
        transition: all 0.3s ease;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
    }
    
    /* Button styling */
    .stButton > button {
        width: 100%;
        border-radius: 15px;
        padding: 0.75rem 2rem;
        font-size: 1.05rem;
        font-weight: 600;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border: none;
        color: white;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.5);
    }
    
    /* Response card styling */
    .response-card {
        background: white;
        border-radius: 20px;
        padding: 2rem;
        margin: 1.5rem 0;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
        border: 1px solid #f0f0f0;
        animation: slideIn 0.4s ease;
    }
    
    @keyframes slideIn {
        from {
            opacity: 0;
            transform: translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    /* Section headers */
    .section-header {
        color: #667eea;
        font-size: 1.3rem;
        font-weight: 600;
        margin: 1.5rem 0 1rem 0;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #f0f0f0;
    }
    
    /* Info boxes */
    .info-box {
        background: linear-gradient(135deg, #f5f7fa 0%, #f0f3f7 100%);
        border-left: 4px solid #667eea;
        border-radius: 10px;
        padding: 1rem 1.5rem;
        margin: 1rem 0;
    }
    
    .info-label {
        color: #667eea;
        font-weight: 600;
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .info-value {
        color: #333;
        font-size: 1.05rem;
        margin-top: 0.3rem;
    }
    
    /* Performance metrics */
    .perf-metric {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 15px;
        padding: 1.5rem;
        text-align: center;
        color: white;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
    }
    
    .perf-label {
        font-size: 0.9rem;
        opacity: 0.9;
        font-weight: 500;
    }
    
    .perf-value {
        font-size: 2rem;
        font-weight: 700;
        margin-top: 0.3rem;
    }
    
    /* Mobile responsiveness */
    @media (max-width: 768px) {
        .header-title {
            font-size: 1.8rem;
        }
        
        .header-subtitle {
            font-size: 0.95rem;
        }
        
        .response-card {
            padding: 1.5rem;
        }
        
        .perf-value {
            font-size: 1.5rem;
        }
    }
    
    /* Hide Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="header-container">
    <h1 class="header-title"> Stock Search Assistant</h1>
    <p class="header-subtitle">Powered by Azure AI Search | Natural Language Stock Queries</p>
</div>
""", unsafe_allow_html=True)

# ============================================================
# Environment Configuration with Caching
# ============================================================
# Streamlit's @st.cache_data decorator ensures environment variables
# are loaded only once and cached across all user sessions.
#
# Performance Benefits:
#   - Avoids repeated file I/O for .env loading
#   - Reduces overhead on every page interaction
#   - Improves responsiveness for multi-user deployments
#
# Cache Lifetime:
#   - Cached for the entire app lifecycle
#   - Cleared only on app restart or manual cache clear
# ============================================================

@st.cache_data
def get_config():
    """
    Load and cache environment configuration for Azure Search.
    
    This function is called once and the result is cached for all users.
    Streamlit automatically manages cache invalidation and persistence.
    
    Returns:
        Dictionary with:
            - 'endpoint': Azure Search service endpoint URL
            - 'index': Index name for stock data
            - 'api_key': API key for authentication
            
    Note:
        Using @st.cache_data improves performance by avoiding repeated
        environment variable lookups on every user interaction.
    """
    return {
        'endpoint': os.getenv("AZURE_SEARCH_ENDPOINT"),
        'index': os.getenv("AZURE_SEARCH_INDEX_NAME"),
        'api_key': os.getenv("AZURE_SEARCH_API_KEY")
    }

config = get_config()
SERVICE_ENDPOINT = config['endpoint']
INDEX_NAME = config['index']
API_KEY = config['api_key']

if not all([SERVICE_ENDPOINT, INDEX_NAME, API_KEY]):
    st.error(" Missing environment variables. Please configure .env file with Azure Search credentials.")
    st.stop()

# Search input section
col1, col2 = st.columns([4, 1])

with col1:
    user_query = st.text_input(
        "Search Query",
        placeholder="e.g., 'nifty 50 stocks', 'axis bank', 'it stocks with pe less than 20'",
        label_visibility="collapsed",
        key="search_input"
    )

with col2:
    search_button = st.button(" Search", use_container_width=True)

# Example queries section
with st.expander(" Example Queries", expanded=False):
    st.markdown("""
    <div class="example-queries">
        <div class="example-item"> Show me nifty 50 stocks</div>
        <div class="example-item"> What is the PE ratio of Reliance?</div>
        <div class="example-item"> IT sector companies</div>
        <div class="example-item"> Energy stocks with PE less than 15</div>
        <div class="example-item"> HDFC Bank overview</div>
        <div class="example-item"> Nifty Energy stocks</div>
    </div>
    """, unsafe_allow_html=True)

# ============================================================
# Main Search Flow with Performance Instrumentation
# ============================================================
# This section handles user queries and measures performance at key stages:
#
# Timestamp Breakdown:
#   t0: Total start (includes Streamlit rendering overhead)
#   t1: Input received (query parsing begins)
#   t2: Before Azure Search API call
#   t3: After Azure Search API response
#
# Measured Metrics:
#   - Query parsing time: t2 - t1 (typically 1-5ms)
#   - Azure Search API time: t3 - t2 (160-350ms with connection pooling)
#   - Total backend time: t3 - t1 (parsing + API + processing)
#   - Total execution time: Displayed at end (includes UI rendering)
#
# Performance Optimization:
#   - Connection pooling reduces API time by 80% (1400ms → 160-350ms)
#   - Streamlit caching reduces config loading overhead
#   - Timestamp tracking helps identify bottlenecks for debugging
# ============================================================

# Process search when button is clicked or Enter is pressed
if search_button or user_query:
    if user_query and user_query.strip():
        # Timestamp 0: Total start (including Streamlit overhead)
        t0_total_start = time.time()
        
        with st.spinner(" Searching..."):
            # Timestamp 1: Input received
            t1_input_received = time.time()
            
            try:
                # Build search request (parse query → spec → REST API params)
                req = build_search_request_from_user_input(
                    user_query,
                    service_endpoint=SERVICE_ENDPOINT,
                    index_name=INDEX_NAME,
                    api_key=API_KEY
                )
                
                # Timestamp 2: Before Azure AI Search call
                t2_before_search = time.time()
                
                # Execute search (uses connection-pooled HTTP session or SDK)
                result = execute_search_request(req)
                
                # Timestamp 3: After receiving response
                t3_response_received = time.time()
                
                # Calculate time breakdowns for performance analysis
                time_parsing_ms = (t2_before_search - t1_input_received) * 1000
                time_search_ms = (t3_response_received - t2_before_search) * 1000
                time_total_ms = (t3_response_received - t1_input_received) * 1000
                
                # Display results in a modern card
                st.markdown('<div class="response-card">', unsafe_allow_html=True)
                
                # Query Analysis Section
                st.markdown('<div class="section-header"> Query Analysis</div>', unsafe_allow_html=True)
                
                spec = req["spec"]
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"""
                    <div class="info-box">
                        <div class="info-label">Query Mode</div>
                        <div class="info-value">{spec.get('mode', 'N/A')}</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    # Determine what was detected
                    detected_info = []
                    if 'index_code' in spec and spec['index_code']:
                        detected_info.append(f"Index: {spec['index_code']}")
                    if 'sector' in spec and spec['sector']:
                        detected_info.append(f"Sector: {spec['sector']}")
                    if 'metric' in spec and spec['metric']:
                        detected_info.append(f"Metric: {spec['metric']}")
                    if 'stock_query' in spec and spec['stock_query']:
                        detected_info.append(f"Stock: {spec['stock_query']}")
                    
                    detected_str = ", ".join(detected_info) if detected_info else "General search"
                    
                    st.markdown(f"""
                    <div class="info-box">
                        <div class="info-label">Detected Parameters</div>
                        <div class="info-value">{detected_str}</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Performance Metrics
                st.markdown('<div class="section-header"> Performance Metrics</div>', unsafe_allow_html=True)
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.markdown(f"""
                    <div class="perf-metric">
                        <div class="perf-label">Processing Time</div>
                        <div class="perf-value">{time_parsing_ms:.1f}ms</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.markdown(f"""
                    <div class="perf-metric">
                        <div class="perf-label">Search Time</div>
                        <div class="perf-value">{time_search_ms:.1f}ms</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col3:
                    st.markdown(f"""
                    <div class="perf-metric">
                        <div class="perf-label">Total Time</div>
                        <div class="perf-value">{time_total_ms:.1f}ms</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Status
                st.markdown('<div class="section-header"> Response Status</div>', unsafe_allow_html=True)
                
                status_code = result["status_code"]
                if status_code == 200:
                    status_html = '<span class="status-badge status-success"> Success (200)</span>'
                else:
                    status_html = f'<span class="status-badge status-error"> Error ({status_code})</span>'
                
                st.markdown(status_html, unsafe_allow_html=True)
                
                # Search Results
                if status_code == 200 and "value" in result["response"]:
                    st.markdown('<div class="section-header"> Search Results</div>', unsafe_allow_html=True)
                    
                    results = result["response"]["value"]
                    total_count = result["response"].get("@odata.count", len(results))
                    
                    st.markdown(f"**Found {total_count} results** (showing {len(results)})")
                    
                    if results:
                        # Convert to display format
                        display_data = []
                        for item in results:
                            row = {
                                "Symbol": item.get("Symbol", ""),
                                "Name": item.get("Name", ""),
                                "Sector": item.get("Sector", ""),
                            }
                            
                            # Add available metrics
                            if "PE" in item:
                                row["PE"] = item["PE"]
                            if "PB" in item:
                                row["PB"] = item["PB"]
                            if "MarketCapCr" in item:
                                row["Market Cap (Cr)"] = item["MarketCapCr"]
                            if "EPS" in item:
                                row["EPS"] = item["EPS"]
                            if "DividendYieldPct" in item:
                                row["Dividend %"] = item["DividendYieldPct"]
                            
                            display_data.append(row)
                        
                        # Display as table (optimized rendering)
                        st.dataframe(
                            display_data,
                            use_container_width=True,
                            hide_index=True,
                            height=400
                        )
                
                # Technical Details (collapsible)
                with st.expander(" Technical Details", expanded=False):
                    st.markdown("**Azure Search URL:**")
                    st.code(req["url"], language="text")
                    
                    st.markdown("**Request Payload:**")
                    st.json(req["json"])
                    
                    st.markdown("**Full Response:**")
                    st.json(result["response"])
                
                st.markdown('</div>', unsafe_allow_html=True)
                
                # Total execution time (including rendering)
                t4_total_end = time.time()
                total_execution_ms = (t4_total_end - t0_total_start) * 1000
                streamlit_overhead_ms = total_execution_ms - time_total_ms
                
                st.info(f"📊 **Full Execution:** {total_execution_ms:.0f}ms total ({time_total_ms:.0f}ms API + {streamlit_overhead_ms:.0f}ms rendering)")
                
            except Exception as e:
                st.error(f" Error processing query: {str(e)}")
                st.exception(e)
    else:
        st.info(" Enter a search query above to get started")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; font-size: 0.9rem; padding: 1rem;">
    <p>Built with Streamlit & Azure AI Search | Natural Language Processing for Stock Queries</p>
</div>
""", unsafe_allow_html=True)

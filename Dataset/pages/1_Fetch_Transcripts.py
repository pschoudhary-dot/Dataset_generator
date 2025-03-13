import streamlit as st
import os
import json
import sqlite3
from pathlib import Path
import sys

# Add the parent directory to sys.path to import from sibling directories
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Add the Dataset directory to sys.path
dataset_dir = os.path.dirname(parent_dir)
if dataset_dir not in sys.path:
    sys.path.append(dataset_dir)

# Import the necessary modules
from create_db import RetellDatabase, init_database
from fetch_call_transcript import RetellTranscriptFetcher, SpecificCallFetcher

# Define the correct database path
DB_PATH = "/mount/src/dataset_generator/DB/UI/retell.sqlite"

# Page configuration
st.set_page_config(
    page_title="Fetch Call Transcripts",
    page_icon="📞",
    layout="wide"
)

st.title("Fetch Call Transcripts")
st.markdown("Connect to the database and fetch call transcripts by ID or in bulk.")

# Database setup section
st.header("1. Database Setup")

# Initialize database if not exists
if 'db' not in st.session_state:
    st.session_state.db = init_database(db_path=DB_PATH)
    st.success("✅ Database initialized successfully!")

# Fetch transcripts section
st.header("2. Fetch Call Transcripts")

# Create tabs for different fetching methods
fetch_tab1, fetch_tab2 = st.tabs(["Fetch All Calls", "Fetch Specific Calls"])

# Tab 1: Fetch all calls
with fetch_tab1:
    st.markdown("Fetch all successful calls from the Retell API and store them in the database.")
    
    # Get API key from session state
    api_key = st.session_state.api_keys.get('retell_api_key', '')
    if not api_key:
        st.warning("⚠️ Please configure your Retell API key in the sidebar first")
    
    # Limit input
    limit = st.number_input("Maximum number of calls to fetch", min_value=1, max_value=1000, value=200)
    
    # Fetch button
    if st.button("Fetch All Calls"):
        if not api_key:
            st.error("❌ Please configure your Retell API key in the sidebar first")
        else:
            # Set the API key as an environment variable
            os.environ["RETELL"] = api_key
            
            # Create progress bar
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                # Initialize the fetcher with the correct DB path
                fetcher = RetellTranscriptFetcher(db_path=DB_PATH)
                
                # Fetch all calls
                status_text.text("Fetching calls from Retell API...")
                result = fetcher.fetch_all_calls(limit=limit)
                
                if result:
                    st.success(f"✅ Successfully fetched {len(result)} calls!")
                else:
                    st.warning("⚠️ No new calls found")
                    
            except Exception as e:
                st.error(f"❌ Error fetching calls: {str(e)}")
            finally:
                # Clean up
                if 'fetcher' in locals():
                    fetcher.close()

# Tab 2: Fetch specific calls
with fetch_tab2:
    st.markdown("Fetch specific calls by their IDs.")
    
    # Call ID input
    call_ids = st.text_input(
        "Call IDs",
        help="Enter comma-separated call IDs to fetch"
    )
    
    # Fetch button
    if st.button("Fetch Specific Calls"):
        if not call_ids:
            st.error("❌ Please enter at least one Call ID")
        else:
            try:
                # Initialize the fetcher with the correct DB path
                fetcher = SpecificCallFetcher(db_path=DB_PATH)
                
                # Fetch specific calls
                result = fetcher.fetch_specific_calls(call_ids.split(','))
                
                if result:
                    st.success(f"✅ Successfully fetched {len(result)} calls!")
                else:
                    st.warning("⚠️ No calls found with the provided IDs")
                    
            except Exception as e:
                st.error(f"❌ Error fetching calls: {str(e)}")
            finally:
                # Clean up
                if 'fetcher' in locals():
                    fetcher.close()
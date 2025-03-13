import streamlit as st
import os
from pathlib import Path
import json

# App title and configuration
st.set_page_config(
    page_title="Call Transcript Dataset Manager",
    page_icon="📞",
    layout="wide"
)

# Main page content
st.title("Call Transcript Dataset Manager")

# API Key Management in Sidebar
st.sidebar.title("Navigation")

# API Keys Configuration Section
st.sidebar.header("API Configuration")

# Initialize session state for API keys if not exists
if 'api_keys' not in st.session_state:
    st.session_state.api_keys = {
        'retell_api_key': '',
        'gemini_api_key': ''
    }

# API Key Input Fields
retell_api_key = st.sidebar.text_input(
    "Retell API Key",
    value=st.session_state.api_keys.get('retell_api_key', ''),
    type="password"
)

gemini_api_key = st.sidebar.text_input(
    "Google Gemini API Key",
    value=st.session_state.api_keys.get('gemini_api_key', ''),
    type="password"
)

# Save API Keys to session state
if st.sidebar.button("Save API Keys"):
    st.session_state.api_keys = {
        'retell_api_key': retell_api_key,
        'gemini_api_key': gemini_api_key
    }
    st.sidebar.success("API keys saved successfully!")

# Navigation Info
st.sidebar.info("""
Select a page from the dropdown in the sidebar to navigate through the different features of the application.
""")

# Documentation Section
st.markdown("""
## Documentation

This multi-page application helps you manage call transcript datasets for training conversational AI models.

### Features

1. **Fetch Call Transcripts** - Connect to the database and fetch call transcripts by ID or in bulk
2. **Generate QA Pairs** - Create question-answer pairs from call transcripts using AI
3. **Export Data** - Convert data to various formats (Excel, JSON, JSONL) for model training

### Workflow

1. Start by fetching call transcripts from the database
2. Generate QA pairs from the transcripts
3. Export the data in your preferred format
4. Use the exported data for training your AI model

### Navigation

Use the sidebar to navigate between different pages of the application:

- **Home** - This documentation page
- **Fetch Transcripts** - Connect to database and fetch call transcripts
- **Generate QA** - Create question-answer pairs from transcripts
- **Export Data** - Convert data to various formats

### Getting Started

1. First, configure your API keys in the sidebar
2. Click on the **Fetch Transcripts** page to begin working with call transcripts
""")

# Display information about the database
db_folder = Path(os.path.dirname(os.path.abspath(__file__))) / "DB"
db_path = db_folder / "retell.sqlite"

# Database status
st.subheader("Database Status")

# Initialize database path
db_folder = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) / "UI" / "DB"
db_path = db_folder / "retell.sqlite"

# Database status
if db_path.exists():
    st.success(f"✅ Database found at {db_path}")
    
    # Try to connect and get some stats
    try:
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get call count
        cursor.execute("SELECT COUNT(*) FROM calls")
        call_count = cursor.fetchone()[0]
        
        # Get utterance count
        cursor.execute("SELECT COUNT(*) FROM utterances")
        utterance_count = cursor.fetchone()[0]
        
        # Get QA pair count
        cursor.execute("SELECT COUNT(*) FROM qa_pairs")
        qa_count = cursor.fetchone()[0]
        
        # Display stats in columns
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Calls", call_count)
        with col2:
            st.metric("Total Utterances", utterance_count)
        with col3:
            st.metric("Total QA Pairs", qa_count)
            
        conn.close()
    except Exception as e:
        st.warning(f"Connected to database but couldn't fetch stats: {str(e)}")
        
    # Show sample code for using the database
    with st.expander("Sample Code for Database Connection"):
        st.code("""
        from pathlib import Path
        import sqlite3
        
        # Connect to the database
        db_path = Path("DB/retell.sqlite")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Example: Fetch all call IDs
        cursor.execute("SELECT call_id FROM calls")
        call_ids = [row[0] for row in cursor.fetchall()]
        
        # Don't forget to close the connection
        conn.close()
        """)
        
else:
    st.error(f"❌ Database not found at {db_path}")
    st.info("You need to create the database first. Go to the 'Fetch Transcripts' page to set up the database.")
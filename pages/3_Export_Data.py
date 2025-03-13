import streamlit as st
import os
import json
import sqlite3
import pandas as pd
from pathlib import Path
import sys
from datetime import datetime

# Add the parent directory to sys.path to import from sibling directories
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Import the necessary modules
from excel_to_jsonl import convert_excel_files_to_jsonl

# Page configuration
st.set_page_config(
    page_title="Export Data",
    page_icon="📊",
    layout="wide"
)

st.title("Export Data")
st.markdown("Export QA pairs from the database in various formats for model training.")

# Set up paths
db_folder = Path(parent_dir) / "DB"
db_path = db_folder / "retell.sqlite"

# Create export directories if they don't exist
excel_dir = db_folder / "excel"
excel_dir.mkdir(parents=True, exist_ok=True)

json_dir = db_folder / "json"
json_dir.mkdir(parents=True, exist_ok=True)

jsonl_dir = db_folder / "jsonl"
jsonl_dir.mkdir(parents=True, exist_ok=True)

# Check if database exists
if not db_path.exists():
    st.error(f"❌ Database not found at {db_path}")
    st.info("Please go to the 'Fetch Transcripts' page to set up the database first.")
    st.stop()

# Connect to the database
try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get QA pair count
    cursor.execute("SELECT COUNT(*) FROM qa_pairs")
    qa_count = cursor.fetchone()[0]
    
    if qa_count == 0:
        st.warning("No QA pairs found in the database. Please generate QA pairs first.")
        st.info("Go to the 'Generate QA' page to create question-answer pairs.")
        conn.close()
        st.stop()
    
    # Get unique call IDs
    cursor.execute("SELECT DISTINCT call_id FROM qa_pairs")
    unique_calls = cursor.fetchall()
    num_calls = len(unique_calls)
    
    st.success(f"Found {qa_count} QA pairs from {num_calls} calls in the database")
    
    # Create tabs for different export formats
    export_tab1, export_tab2, export_tab3 = st.tabs(["Export to Excel", "Export to JSON", "Export to JSONL"])
    
    # Tab 1: Export to Excel
    with export_tab1:
        st.markdown("Export QA pairs to an Excel file.")
        
        # Options for export
        st.subheader("Export Options")
        
        # Filter by call IDs
        filter_by_call = st.checkbox("Filter by Call IDs", value=False)
        
        call_ids = []
        if filter_by_call:
            # Get all call IDs
            cursor.execute("SELECT DISTINCT call_id FROM qa_pairs")
            all_call_ids = [row[0] for row in cursor.fetchall()]
            
            # Display a sample of call IDs
            with st.expander("View available call IDs"):
                st.write(all_call_ids[:10] if len(all_call_ids) > 10 else all_call_ids)
            
            # Input for specific call IDs
            call_id_input = st.text_area(
                "Enter call IDs (one per line)", 
                height=100,
                help="Enter the call IDs you want to export QA pairs for, one per line"
            )
            
            if call_id_input.strip():
                call_ids = [call_id.strip() for call_id in call_id_input.splitlines() if call_id.strip()]
        
        # Output filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"qa_pairs_{timestamp}.xlsx"
        output_filename = st.text_input("Output filename", default_filename)
        
        # Export button
        if st.button("Export to Excel"):
            try:
                # Create a query based on filters
                if filter_by_call and call_ids:
                    placeholders = ", ".join(["?" for _ in call_ids])
                    query = f"SELECT call_id, question, answer FROM qa_pairs WHERE call_id IN ({placeholders})"
                    cursor.execute(query, call_ids)
                else:
                    cursor.execute("SELECT call_id, question, answer FROM qa_pairs")
                
                # Fetch all rows
                rows = cursor.fetchall()
                
                if not rows:
                    st.warning("No QA pairs found with the selected filters.")
                else:
                    # Create DataFrame
                    df = pd.DataFrame(rows, columns=["Call ID", "Question", "Answer"])
                    
                    # Save to Excel
                    output_path = excel_dir / output_filename
                    df.to_excel(output_path, index=False)
                    
                    # Show success message
                    st.success(f"✅ Successfully exported {len(df)} QA pairs to {output_path}")
                    
                    # Provide download button
                    with open(output_path, "rb") as f:
                        excel_data = f.read()
                    
                    st.download_button(
                        label="Download Excel File",
                        data=excel_data,
                        file_name=output_filename,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                    
                    # Display preview
                    with st.expander("Preview Data"):
                        st.dataframe(df.head(10) if len(df) > 10 else df)
            
            except Exception as e:
                st.error(f"❌ Error exporting to Excel: {str(e)}")
    
    # Tab 2: Export to JSON
    with export_tab2:
        st.markdown("Export QA pairs to a JSON file.")
        
        # Options for export
        st.subheader("Export Options")
        
        # Filter by call IDs
        filter_by_call_json = st.checkbox("Filter by Call IDs", value=False, key="json_filter")
        
        call_ids_json = []
        if filter_by_call_json:
            # Get all call IDs
            cursor.execute("SELECT DISTINCT call_id FROM qa_pairs")
            all_call_ids = [row[0] for row in cursor.fetchall()]
            
            # Display a sample of call IDs
            with st.expander("View available call IDs"):
                st.write(all_call_ids[:10] if len(all_call_ids) > 10 else all_call_ids)
            
            # Input for specific call IDs
            call_id_input = st.text_area(
                "Enter call IDs (one per line)", 
                height=100,
                help="Enter the call IDs you want to export QA pairs for, one per line",
                key="json_call_ids"
            )
            
            if call_id_input.strip():
                call_ids_json = [call_id.strip() for call_id in call_id_input.splitlines() if call_id.strip()]
        
        # System message for JSON format
        system_message = st.text_area(
            "System Message", 
            "You are a helpful customer support assistant. Answer questions accurately and professionally.",
            help="This message will be included as the system message in the JSON format"
        )
        
        # Output filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename_json = f"qa_pairs_{timestamp}.json"
        output_filename_json = st.text_input("Output filename", default_filename_json, key="json_filename")
        
        # Export button
        if st.button("Export to JSON"):
            try:
                # Create a query based on filters
                if filter_by_call_json and call_ids_json:
                    placeholders = ", ".join(["?" for _ in call_ids_json])
                    query = f"SELECT call_id, question, answer FROM qa_pairs WHERE call_id IN ({placeholders})"
                    cursor.execute(query, call_ids_json)
                else:
                    cursor.execute("SELECT call_id, question, answer FROM qa_pairs")
                
                # Fetch all rows
                rows = cursor.fetchall()
                
                if not rows:
                    st.warning("No QA pairs found with the selected filters.")
                else:
                    # Create JSON structure
                    qa_data = []
                    for call_id, question, answer in rows:
                        qa_data.append({
                            "call_id": call_id,
                            "messages": [
                                {"role": "system", "content": system_message},
                                {"role": "user", "content": question},
                                {"role": "assistant", "content": answer}
                            ]
                        })
                    
                    # Save to JSON
                    output_path = json_dir / output_filename_json
                    with open(output_path, "w", encoding="utf-8") as f:
                        json.dump(qa_data, f, indent=2, ensure_ascii=False)
                    
                    # Show success message
                    st.success(f"✅ Successfully exported {len(qa_data)} QA pairs to {output_path}")
                    
                    # Provide download button
                    with open(output_path, "r", encoding="utf-8") as f:
                        json_data = f.read()
                    
                    st.download_button(
                        label="Download JSON File",
                        data=json_data,
                        file_name=output_filename_json,
                        mime="application/json"
                    )
                    
                    # Display preview
                    with st.expander("Preview Data"):
                        st.json(qa_data[:3] if len(qa_data) > 3 else qa_data)
            
            except Exception as e:
                st.error(f"❌ Error exporting to JSON: {str(e)}")
    
    # Tab 3: Export to JSONL
    with export_tab3:
        st.markdown("Export QA pairs to a JSONL file for model training.")
        
        st.info("This will first export to Excel and then convert to JSONL format.")
        
        # System message for JSONL format
        system_message_jsonl = st.text_area(
            "System Message", 
            "You are a helpful customer support assistant. Answer questions accurately and professionally.",
            help="This message will be included as the system message in the JSONL format",
            key="jsonl_system"
        )
        
        # Export button
        if st.button("Export to JSONL"):
            try:
                # First export to Excel
                cursor.execute("SELECT call_id, question, answer FROM qa_pairs")
                rows = cursor.fetchall()
                
                if not rows:
                    st.warning("No QA pairs found in the database.")
                else:
                    # Create DataFrame
                    df = pd.DataFrame(rows, columns=["Call ID", "Question", "Answer"])
                    
                    # Save to Excel temporarily
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    temp_excel_filename = f"temp_qa_pairs_{timestamp}.xlsx"
                    temp_excel_path = excel_dir / temp_excel_filename
                    df.to_excel(temp_excel_path, index=False)
                    
                    # Convert Excel to JSONL
                    jsonl_path = convert_excel_files_to_jsonl(
                        excel_dir=str(excel_dir),
                        output_dir=str(jsonl_dir),
                        system_message=system_message_jsonl
                    )
                    
                    # Show success message
                    st.success(f"✅ Successfully exported {len(df)} QA pairs to {jsonl_path}")
                    
                    # Provide download button
                    with open(jsonl_path, "r", encoding="utf-8") as f:
                        jsonl_data = f.read()
                    
                    jsonl_filename = os.path.basename(jsonl_path)
                    st.download_button(
                        label="Download JSONL File",
                        data=jsonl_data,
                        file_name=jsonl_filename,
                        mime="application/jsonl"
                    )
                    
                    # Display preview
                    with st.expander("Preview Data"):
                        # Show first few lines of JSONL
                        lines = jsonl_data.splitlines()[:5]
                        for i, line in enumerate(lines):
                            st.code(line, language="json")
                            if i < len(lines) - 1:
                                st.markdown("---")
            
            except Exception as e:
                st.error(f"❌ Error exporting to JSONL: {str(e)}")

except Exception as e:
    st.error(f"❌ Error connecting to database: {str(e)}")
    if 'conn' in locals():
        conn.close()

# Add information about the next steps
st.header("Next Steps")
st.markdown("""
Once you have exported the data, you can use it to:

1. Train a conversational AI model
2. Analyze the QA pairs for insights
3. Import the data into other systems

The exported data is in standard formats (Excel, JSON, JSONL) that can be used with various AI frameworks and tools.
""")
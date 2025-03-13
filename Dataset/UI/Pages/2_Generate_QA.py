import streamlit as st
import os
import json
import pandas as pd
import sys
from pathlib import Path
import time
from datetime import datetime
import random
import base64
import sqlite3

# Add parent directory to path to import from Dataset modules
sys.path.append(str(Path(__file__).parent.parent.parent))
from generate_QA import QAPairGenerator
from fetch_call_transcript import RetellTranscriptFetcher, SpecificCallFetcher

def convert_excel_to_jsonl(excel_file):
    """Convert Excel file to JSONL format."""
    try:
        # Read Excel file
        df = pd.read_excel(excel_file)
        
        # Create output path
        output_dir = Path(os.path.dirname(os.path.abspath(__file__))).parent / "DB" / "local_json"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"dataset_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
        
        # Convert to JSONL
        with open(output_path, 'w', encoding='utf-8') as f:
            for _, row in df.iterrows():
                json_line = row.to_dict()
                f.write(json.dumps(json_line, ensure_ascii=False) + '\n')
        
        return str(output_path)
    except Exception as e:
        st.error(f"Error converting Excel to JSONL: {e}")
        return None

def get_download_link(file_path, link_text):
    """Generate a download link for a file."""
    try:
        with open(file_path, 'rb') as f:
            data = f.read()
            b64 = base64.b64encode(data).decode()
            href = f'data:application/octet-stream;base64,{b64}'
            return f'<a href="{href}" download="{os.path.basename(file_path)}">{link_text}</a>'
    except Exception as e:
        st.error(f"Error generating download link: {e}")
        return None

def load_transcripts(source_type, call_ids=None, count=10):
    """Load transcripts based on source type."""
    st.info(f"Loading transcripts from {source_type}...")
    
    if source_type == "Specific Call IDs":
        if not call_ids:
            st.error("Please enter at least one Call ID")
            return None, None
            
        fetcher = SpecificCallFetcher()
        try:
            # Using the correct method from SpecificCallFetcher
            output_filename = f"selected_transcripts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            transcripts = fetcher.fetch_specific_calls(
                call_ids.split(','), 
                output_path=output_filename
            )
            transcripts_file = str(fetcher.db_folder / output_filename)
        finally:
            fetcher.close()
            
    elif source_type == "Random Calls":
        # For random calls, we'll first fetch all call IDs, then select random ones
        fetcher = RetellTranscriptFetcher()
        try:
            # Get all existing call IDs
            existing_call_ids = fetcher.get_existing_call_ids()
            if not existing_call_ids:
                st.error("No calls found in the database")
                return None, None
                
            # Select random call IDs
            random_call_ids = random.sample(
                list(existing_call_ids), 
                min(count, len(existing_call_ids))
            )
            
            # Close RetellTranscriptFetcher and use SpecificCallFetcher to get the transcripts
            fetcher.close()
            
            specific_fetcher = SpecificCallFetcher()
            try:
                output_filename = f"random_transcripts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                transcripts = specific_fetcher.fetch_specific_calls(
                    random_call_ids,
                    output_path=output_filename
                )
                transcripts_file = str(specific_fetcher.db_folder / output_filename)
            finally:
                specific_fetcher.close()
        except Exception as e:
            st.error(f"Error fetching random calls: {e}")
            return None, None
        finally:
            if not fetcher.db.conn.closed:
                fetcher.close()
            
    elif source_type == "JSON File":
        transcripts_file = st.session_state.get('selected_json_file')
        if not transcripts_file:
            st.error("Please select a JSON file first")
            return None, None
            
        with open(transcripts_file, 'r', encoding='utf-8') as f:
            transcripts = json.load(f)
    
    else:
        st.error("Invalid source type")
        return None, None
        
    return transcripts, transcripts_file

def generate_qa_pairs(transcripts, output_filename=None):
    """Generate QA pairs from transcripts."""
    if not output_filename:
        output_filename = f"qa_pairs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
    generator = QAPairGenerator()
    qa_pairs, output_path = generator.process_transcripts(transcripts, output_filename)
    
    return qa_pairs, output_path

def display_qa_pairs(qa_pairs, max_display=10):
    """Display QA pairs in a nice format."""
    if not qa_pairs:
        st.warning("No QA pairs to display")
        return
        
    st.write(f"### Sample QA Pairs (showing {min(max_display, len(qa_pairs))} of {len(qa_pairs)})")
    
    # Convert to DataFrame for better display
    df = pd.DataFrame(qa_pairs)
    
    # Group by call_id
    call_ids = df['call_id'].unique()
    
    for i, call_id in enumerate(call_ids):
        if i >= max_display:
            break
            
        call_qa_pairs = df[df['call_id'] == call_id]
        st.write(f"#### Call ID: {call_id}")
        
        for _, row in call_qa_pairs.iterrows():
            with st.expander(f"Q: {row['question']}"):
                st.write(f"A: {row['answer']}")
                
def export_to_excel(qa_pairs, output_path):
    """Export QA pairs to Excel."""
    if not qa_pairs:
        st.warning("No QA pairs to export")
        return None
        
    # Convert to DataFrame
    df = pd.DataFrame(qa_pairs)
    
    # Create Excel file path
    excel_dir = Path(os.path.dirname(os.path.abspath(__file__))).parent / "DB" / "excel"
    excel_dir.mkdir(parents=True, exist_ok=True)
    
    excel_path = excel_dir / f"qa_pairs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    # Export to Excel
    df.to_excel(excel_path, index=False)
    
    return str(excel_path)

def app():
    st.title("Generate QA Pairs")
    
    st.write("""
    This tool generates question-answer pairs from call transcripts. 
    These QA pairs can be used to train or fine-tune a chatbot.
    """)
    
    # Source selection
    st.subheader("Step 1: Select Transcript Source")
    source_type = st.radio(
        "Choose transcript source:",
        ["Specific Call IDs", "Random Calls", "JSON File"]
    )
    
    # Source-specific inputs
    if source_type == "Specific Call IDs":
        call_ids = st.text_input(
            "Enter Call IDs (comma-separated):",
            help="Example: call_123456,call_789012"
        )
        
    elif source_type == "Random Calls":
        count = st.number_input("Number of random calls to fetch:", min_value=1, max_value=50, value=10)
        
    elif source_type == "JSON File":
        json_dir = Path(os.path.dirname(os.path.abspath(__file__))).parent / "DB" / "local_json"
        json_files = list(json_dir.glob("*.json"))
        
        if not json_files:
            st.warning("No JSON files found in the DB/local_json directory")
        else:
            selected_file = st.selectbox(
                "Select JSON file:",
                options=[str(f) for f in json_files],
                format_func=lambda x: os.path.basename(x)
            )
            st.session_state['selected_json_file'] = selected_file
    
    # Load transcripts button
    if st.button("Load Transcripts"):
        with st.spinner("Loading transcripts..."):
            if source_type == "Specific Call IDs":
                transcripts, transcripts_file = load_transcripts(source_type, call_ids=call_ids)
            elif source_type == "Random Calls":
                transcripts, transcripts_file = load_transcripts(source_type, count=count)
            else:
                transcripts, transcripts_file = load_transcripts(source_type)
                
            if transcripts:
                st.session_state['transcripts'] = transcripts
                st.session_state['transcripts_file'] = transcripts_file
                st.success(f"Loaded {len(transcripts)} transcripts")
                
                # Add download link for transcripts
                st.markdown(get_download_link(transcripts_file, "Download Transcripts JSON"), unsafe_allow_html=True)
                
                # Display transcript preview
                st.subheader("Transcript Preview")
                for i, transcript in enumerate(transcripts[:3]):
                    with st.expander(f"Transcript {i+1} (Call ID: {transcript['call_id']})"): 
                        st.text_area("Content:", value=transcript['transcript'][:500] + "...", height=200, disabled=True)
                
                if len(transcripts) > 3:
                    st.info(f"... and {len(transcripts) - 3} more transcripts")
    
    # Generate QA pairs
    st.subheader("Step 2: Generate QA Pairs")
    
    output_filename = st.text_input(
        "Output filename (optional):",
        value=f"qa_pairs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        help="Name of the JSON file to save QA pairs"
    )
    
    if st.button("Generate QA Pairs"):
        if 'transcripts' not in st.session_state:
            st.error("Please load transcripts first")
        else:
            with st.spinner("Generating QA pairs... This may take a while."):
                progress_bar = st.progress(0)
                
                # Start time for estimation
                start_time = time.time()
                
                # Get transcripts
                transcripts = st.session_state['transcripts']
                
                # Generate QA pairs with progress updates
                generator = QAPairGenerator()
                
                # Process each transcript with progress updates
                all_qa_pairs = []
                for i, call_data in enumerate(transcripts):
                    # Update progress
                    progress = (i + 1) / len(transcripts)
                    progress_bar.progress(progress)
                    
                    # Estimate remaining time
                    elapsed = time.time() - start_time
                    estimated_total = elapsed / progress if progress > 0 else 0
                    remaining = estimated_total - elapsed
                    
                    # Display status
                    st.write(f"Processing transcript {i+1}/{len(transcripts)} - Call ID: {call_data['call_id']}")
                    st.write(f"Estimated time remaining: {int(remaining/60)} minutes {int(remaining%60)} seconds")
                    
                    # Generate QA pairs for this transcript
                    call_id = call_data["call_id"]
                    transcript = call_data["transcript"]
                    
                    # Skip empty or very short transcripts
                    if not transcript or len(transcript) < 50:
                        st.write(f"Skipping call {call_id} - transcript too short")
                        continue
                    
                    # Check if QA pairs already exist for this call_id
                    try:
                        # Access cursor directly from the generator instance
                        cursor = generator.cursor
                        cursor.execute("SELECT COUNT(*) FROM qa_pairs WHERE call_id = ?", (call_id,))
                        existing_count = cursor.fetchone()[0]
                        
                        if existing_count > 0:
                            # Show existing QA pairs
                            cursor.execute("SELECT question, answer FROM qa_pairs WHERE call_id = ?", (call_id,))
                            existing_pairs = cursor.fetchall()
                            
                            st.warning(f"QA pairs already exist for call {call_id}")
                            with st.expander("View Existing QA Pairs"):
                                for q, a in existing_pairs:
                                    st.write(f"Q: {q}")
                                    st.write(f"A: {a}")
                                    st.markdown("---")
                            
                            # Add regenerate button
                            if st.button(f"Regenerate QA Pairs for {call_id}", key=f"regenerate_{call_id}"):
                                # Delete existing QA pairs
                                cursor.execute("DELETE FROM qa_pairs WHERE call_id = ?", (call_id,))
                                generator.conn.commit()  # Use conn directly from generator
                                
                                # Generate new QA pairs
                                qa_pairs = generator.generate_qa_pairs(transcript, call_id)
                                st.success(f"Regenerated {len(qa_pairs)} QA pairs for call {call_id}")
                            else:
                                continue
                        else:
                            # Generate QA pairs
                            qa_pairs = generator.generate_qa_pairs(transcript, call_id)
                    except (AttributeError, sqlite3.Error) as e:
                        # If there's an error accessing the database, just generate QA pairs
                        st.warning(f"Could not check for existing QA pairs: {e}")
                        qa_pairs = generator.generate_qa_pairs(transcript, call_id)
                    
                    if qa_pairs:
                        all_qa_pairs.extend(qa_pairs)
                        st.write(f"Generated {len(qa_pairs)} QA pairs for call {call_id}")
                    else:
                        st.write(f"No relevant QA pairs generated for call {call_id}")
                    
                    # Add a small delay to avoid rate limiting
                    time.sleep(1)
                
                # Save all QA pairs to a JSON file
                output_dir = Path(os.path.dirname(os.path.abspath(__file__))).parent / "DB" / "local_json"
                output_path = output_dir / output_filename
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(all_qa_pairs, f, indent=2, ensure_ascii=False)
                
                st.session_state['qa_pairs'] = all_qa_pairs
                st.session_state['qa_pairs_path'] = str(output_path)
                
                st.success(f"Generated {len(all_qa_pairs)} QA pairs from {len(transcripts)} transcripts")
                st.success(f"Results saved to {output_path}")
                
                # Add download link for JSON output
                st.markdown(get_download_link(str(output_path), "Download QA Pairs JSON"), unsafe_allow_html=True)
    
    # Display and export QA pairs
    st.subheader("Step 3: View and Export QA Pairs")
    
    if 'qa_pairs' in st.session_state:
        display_qa_pairs(st.session_state['qa_pairs'])
        
        if st.button("Export to Excel"):
            with st.spinner("Exporting to Excel..."):
                excel_path = export_to_excel(st.session_state['qa_pairs'], st.session_state['qa_pairs_path'])
                if excel_path:
                    st.success(f"Exported to Excel: {excel_path}")
                    st.markdown(get_download_link(excel_path, "Download Excel file"), unsafe_allow_html=True)
    
    # Add Excel to JSONL conversion as Step 4
    st.subheader("Step 4: Convert to JSONL Format")
    st.write("""
    Convert Excel files with QA pairs to JSONL format for model fine-tuning.
    The JSONL format is required for training or fine-tuning language models.
    """)
    
    # System message for JSONL
    default_system_message = "You are a helpful customer support assistant for Wellness Wag, a company that provides ESA (Emotional Support Animal) letters. Answer questions accurately and professionally."
    
    system_message = st.text_area(
        "System Message (instructions for the AI):",
        value=default_system_message,
        height=100,
        help="This message sets the context and instructions for the AI model"
    )
    
    # Source selection for Excel files
    excel_source = st.radio(
        "Choose Excel source:",
        ["Upload Excel File", "Use Excel Files from DB/excel Folder"]
    )
    
    if excel_source == "Upload Excel File":
        uploaded_file = st.file_uploader("Upload Excel file", type=['xlsx', 'xls'])
        
        if uploaded_file is not None:
            # Preview the Excel file
            try:
                df = pd.read_excel(uploaded_file)
                st.write("### Excel File Preview:")
                st.dataframe(df.head(3))
                
                # Show JSONL preview
                if len(df) > 0:
                    st.write("### JSONL Preview (first entry):")
                    
                    # Map column names (case-insensitive)
                    question_col = None
                    answer_col = None
                    
                    for col in df.columns:
                        col_lower = str(col).lower()
                        if 'question' in col_lower:
                            question_col = col
                        elif 'answer' in col_lower:
                            answer_col = col
                    
                    if not question_col or not answer_col:
                        if 'Q' in df.columns and 'A' in df.columns:
                            question_col = 'Q'
                            answer_col = 'A'
                        else:
                            st.warning("Could not identify question/answer columns. Please ensure your Excel file has columns named 'question' and 'answer' or 'Q' and 'A'.")
                    
                    if question_col and answer_col:
                        # Create a sample JSONL entry
                        sample_row = df.iloc[0]
                        jsonl_entry = {
                            "messages": [
                                {"role": "system", "content": system_message},
                                {"role": "user", "content": str(sample_row[question_col])},
                                {"role": "assistant", "content": str(sample_row[answer_col])}
                            ]
                        }
                        
                        # Display the sample
                        st.code(json.dumps(jsonl_entry, indent=2, ensure_ascii=False))
                
                if st.button("Convert Uploaded Excel to JSONL"):
                    with st.spinner("Converting to JSONL..."):
                        # Create a temporary file to save the uploaded Excel
                        temp_dir = Path(os.path.dirname(os.path.abspath(__file__))).parent.parent / "DB" / "temp"
                        temp_dir.mkdir(parents=True, exist_ok=True)
                        temp_excel = temp_dir / f"temp_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                        
                        with open(temp_excel, 'wb') as f:
                            f.write(uploaded_file.getvalue())
                        
                        # Import the function from excel_to_jsonl.py
                        sys.path.append(str(Path(__file__).parent.parent.parent))
                        from excel_to_jsonl import convert_excel_files_to_jsonl
                        
                        # Convert to JSONL
                        output_file = convert_excel_files_to_jsonl(
                            excel_dir=temp_dir,
                            system_message=system_message
                        )
                        
                        st.success(f"Converted successfully to JSONL format")
                        st.markdown(get_download_link(str(output_file), "Download JSONL file"), unsafe_allow_html=True)
                        
                        # Clean up temp file
                        os.remove(temp_excel)
            
            except Exception as e:
                st.error(f"Error processing Excel file: {e}")
    
    else:  # Use Excel Files from DB/excel Folder
        # Import the function from excel_to_jsonl.py
        sys.path.append(str(Path(__file__).parent.parent.parent))
        from excel_to_jsonl import convert_excel_files_to_jsonl
        
        excel_dir = Path(os.path.dirname(os.path.abspath(__file__))).parent.parent / "DB" / "excel"
        excel_files = list(excel_dir.glob("*.xlsx")) + list(excel_dir.glob("*.xls"))
        
        if not excel_files:
            st.warning("No Excel files found in the DB/excel directory")
        else:
            st.write(f"Found {len(excel_files)} Excel files in DB/excel folder:")
            for excel_file in excel_files:
                st.write(f"- {excel_file.name}")
            
            # Show preview of the first Excel file
            if len(excel_files) > 0:
                try:
                    df = pd.read_excel(excel_files[0])
                    st.write(f"### Preview of {excel_files[0].name}:")
                    st.dataframe(df.head(3))
                    
                    # Show JSONL preview
                    if len(df) > 0:
                        st.write("### JSONL Preview (first entry):")
                        
                        # Map column names (case-insensitive)
                        question_col = None
                        answer_col = None
                        
                        for col in df.columns:
                            col_lower = str(col).lower()
                            if 'question' in col_lower:
                                question_col = col
                            elif 'answer' in col_lower:
                                answer_col = col
                        
                        if not question_col or not answer_col:
                            if 'Q' in df.columns and 'A' in df.columns:
                                question_col = 'Q'
                                answer_col = 'A'
                            else:
                                st.warning("Could not identify question/answer columns in the preview file.")
                        
                        if question_col and answer_col:
                            # Create a sample JSONL entry
                            sample_row = df.iloc[0]
                            jsonl_entry = {
                                "messages": [
                                    {"role": "system", "content": system_message},
                                    {"role": "user", "content": str(sample_row[question_col])},
                                    {"role": "assistant", "content": str(sample_row[answer_col])}
                                ]
                            }
                            
                            # Display the sample
                            st.code(json.dumps(jsonl_entry, indent=2, ensure_ascii=False))
                
                except Exception as e:
                    st.error(f"Error previewing Excel file: {e}")
            
            if st.button("Convert All Excel Files to JSONL"):
                with st.spinner("Converting to JSONL..."):
                    try:
                        # Convert to JSONL
                        output_file = convert_excel_files_to_jsonl(
                            system_message=system_message,
                            include_call_id=False  # Explicitly exclude call_id
                        )
                        
                        st.success(f"Converted successfully to JSONL format")
                        st.markdown(get_download_link(str(output_file), "Download JSONL file"), unsafe_allow_html=True)
                    except Exception as e:
                        st.error(f"Error during conversion: {e}")
                        import traceback
                        traceback.print_exc()

if __name__ == "__main__":
    app()

# Page configuration
st.set_page_config(
    page_title="Generate Q&A Pairs",
    page_icon="❓",
    layout="wide"
)

st.title("Generate Q&A Pairs")
st.markdown("Generate question-answer pairs from call transcripts using AI.")

# Source selection
st.header("1. Select Transcript Source")
source_type = st.radio(
    "Select source for transcripts",
    ["Specific Call IDs", "Random Calls"]
)

# Input based on source type
if source_type == "Specific Call IDs":
    call_ids = st.text_input(
        "Call IDs",
        help="Enter comma-separated call IDs"
    )
else:
    count = st.number_input(
        "Number of random calls",
        min_value=1,
        max_value=50,
        value=10
    )

# Load transcripts button
if st.button("Load Transcripts"):
    transcripts = load_transcripts(
        source_type,
        call_ids if source_type == "Specific Call IDs" else None,
        count if source_type == "Random Calls" else None
    )
    
    if transcripts:
        st.session_state.transcripts = transcripts
        st.success(f"✅ Loaded {len(transcripts)} transcripts successfully!")
        
        # Store in session state for QA generation
        if 'loaded_transcripts' not in st.session_state:
            st.session_state.loaded_transcripts = {}
        st.session_state.loaded_transcripts.update(transcripts)

# QA Generation section
st.header("2. Generate Q&A Pairs")

if 'loaded_transcripts' in st.session_state and st.session_state.loaded_transcripts:
    # Get API key from session state
    api_key = st.session_state.api_keys.get('gemini_api_key', '')
    if not api_key:
        st.warning("⚠️ Please configure your Google Gemini API key in the sidebar first")
    else:
        # Set environment variable for API key
        os.environ["GOOGLE_API_KEY"] = api_key
        
        if st.button("Generate Q&A Pairs"):
            try:
                # Initialize QA generator
                generator = QAPairGenerator()
                
                # Process each transcript
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                qa_pairs = []
                total = len(st.session_state.loaded_transcripts)
                
                for i, (call_id, transcript) in enumerate(st.session_state.loaded_transcripts.items()):
                    status_text.text(f"Processing transcript {i+1}/{total}...")
                    
                    # Generate QA pairs
                    pairs = generator.generate_qa_pairs(transcript)
                    if pairs:
                        for pair in pairs:
                            qa_pairs.append({
                                'call_id': call_id,
                                'question': pair['question'],
                                'answer': pair['answer']
                            })
                    
                    # Update progress
                    progress_bar.progress((i + 1) / total)
                
                if qa_pairs:
                    # Convert to DataFrame
                    df = pd.DataFrame(qa_pairs)
                    
                    # Store in session state
                    st.session_state.qa_pairs = df
                    
                    # Show success message
                    st.success(f"✅ Generated {len(qa_pairs)} Q&A pairs!")
                    
                    # Export options
                    st.header("3. Export Q&A Pairs")
                    
                    # Show preview
                    st.subheader("Preview")
                    st.dataframe(df)
                    
                    # Export buttons
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # Export as Excel
                        excel_buffer = pd.ExcelWriter()
                        df.to_excel(excel_buffer, index=False)
                        excel_data = excel_buffer.getvalue()
                        st.markdown(
                            get_download_link(
                                excel_data,
                                f"qa_pairs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            ),
                            unsafe_allow_html=True
                        )
                    
                    with col2:
                        # Export as JSONL
                        jsonl_data = convert_excel_to_jsonl(df)
                        if jsonl_data:
                            st.markdown(
                                get_download_link(
                                    jsonl_data,
                                    f"qa_pairs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl",
                                    "application/jsonl"
                                ),
                                unsafe_allow_html=True
                            )
                
            except Exception as e:
                st.error(f"❌ Error generating Q&A pairs: {str(e)}")
            finally:
                if 'generator' in locals():
                    generator.close()
else:
    st.info("Please load transcripts first to generate Q&A pairs.")
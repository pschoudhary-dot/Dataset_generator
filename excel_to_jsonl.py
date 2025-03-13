import pandas as pd
import json
import os
from pathlib import Path
from datetime import datetime

def convert_excel_files_to_jsonl(excel_dir=None, output_dir=None, system_message=None):
    """
    Convert all Excel files with QA pairs from a directory to a single JSONL file for chatbot training.
    
    Args:
        excel_dir: Directory containing Excel files with QA pairs
        output_dir: Directory to save the JSONL file
        system_message: System message to include in each JSONL entry
    
    Returns:
        Path to the created JSONL file
    """
    # Set up paths
    script_dir = Path(os.path.dirname(os.path.abspath(__file__)))
    
    if excel_dir is None:
        excel_dir = script_dir / "DB" / "excel"
    else:
        excel_dir = Path(excel_dir)
    
    if output_dir is None:
        output_dir = script_dir / "DB" / "jsonl"
    else:
        output_dir = Path(output_dir)
    
    if system_message is None:
        system_message = "You are a helpful customer support assistant for Wellness Wag, a company that provides ESA (Emotional Support Animal) letters. Answer questions accurately and professionally."
    
    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Find all Excel files in the directory
    excel_files = list(excel_dir.glob("*.xlsx")) + list(excel_dir.glob("*.xls"))
    
    if not excel_files:
        raise FileNotFoundError(f"No Excel files found in {excel_dir}")
    
    print(f"Found {len(excel_files)} Excel files in {excel_dir}")
    
    # Create a timestamp for the output file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"qa_pairs_{timestamp}.jsonl"
    
    # Process each Excel file and write to a single JSONL file
    total_qa_pairs = 0
    
    with open(output_file, 'w', encoding='utf-8') as f:
        for excel_file in excel_files:
            try:
                # Load the Excel file
                df = pd.read_excel(excel_file)
                
                # Print column names for debugging
                print(f"Columns in {excel_file.name}: {list(df.columns)}")
                
                # Map column names (case-insensitive)
                question_col = None
                answer_col = None
                call_id_col = None
                
                for col in df.columns:
                    col_lower = str(col).lower()
                    if 'question' in col_lower:
                        question_col = col
                    elif 'answer' in col_lower:
                        answer_col = col
                    elif 'call' in col_lower and 'id' in col_lower:
                        call_id_col = col
                
                if not question_col or not answer_col:
                    print(f"Warning: Could not find question/answer columns in {excel_file.name}")
                    # Try common alternative column names
                    if 'Q' in df.columns and 'A' in df.columns:
                        question_col = 'Q'
                        answer_col = 'A'
                    else:
                        # If we still can't find the columns, skip this file
                        print(f"Skipping {excel_file.name} - Could not identify question/answer columns")
                        continue
                
                print(f"Using columns: Question='{question_col}', Answer='{answer_col}', Call ID='{call_id_col}'")
                
                file_qa_pairs = len(df)
                total_qa_pairs += file_qa_pairs
                print(f"Processing {excel_file.name} - Found {file_qa_pairs} QA pairs")
                
                # Convert each row to JSONL format and write to file
                for _, row in df.iterrows():
                    # Create the JSONL entry
                    jsonl_entry = {
                        "messages": [
                            {"role": "system", "content": system_message},
                            {"role": "user", "content": str(row[question_col])},
                            {"role": "assistant", "content": str(row[answer_col])}
                        ]
                    }
                    
                    # Add call_id if it exists in the row
                    if call_id_col and call_id_col in row:
                        jsonl_entry["call_id"] = str(row[call_id_col])
                    
                    # Write to the JSONL file
                    f.write(json.dumps(jsonl_entry, ensure_ascii=False) + '\n')
                    
            except Exception as e:
                print(f"Error processing {excel_file.name}: {e}")
                import traceback
                traceback.print_exc()
    
    print(f"\nSuccessfully converted {total_qa_pairs} QA pairs from {len(excel_files)} Excel files to JSONL format")
    print(f"Output file: {output_file}")
    
    return output_file

def main():
    try:
        # Convert all Excel files to a single JSONL file
        output_file = convert_excel_files_to_jsonl()
        print(f"Conversion complete. JSONL file created at: {output_file}")
        
        # Print a sample of the JSONL file
        with open(output_file, 'r', encoding='utf-8') as f:
            sample_lines = []
            for _ in range(3):
                line = f.readline()
                if line:
                    sample_lines.append(line)
        
        if sample_lines:
            print("\nSample of the JSONL file (first 3 entries):")
            for i, line in enumerate(sample_lines):
                print(f"\nEntry {i+1}:")
                print(line)
        
    except Exception as e:
        print(f"Error during conversion: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
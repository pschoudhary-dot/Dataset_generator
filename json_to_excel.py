'''
(venv) PS D:\Projects\chatbot\chatbot\Dataset> python d:\Projects\chatbot\chatbot\Dataset\json_to_excel.py --input d:\Projects\chatbot\chatbot\Dataset\DB\local_json\<file name>
'''

import os
import json
import argparse
import pandas as pd
from pathlib import Path

def convert_json_to_excel(json_file_path, excel_file_path=None):
    """
    Convert a JSON file containing question-answer pairs to an Excel file.
    
    Args:
        json_file_path (str): Path to the JSON file
        excel_file_path (str, optional): Path to save the Excel file. If None, 
                                         will use the same name as JSON but with .xlsx extension
    
    Returns:
        str: Path to the created Excel file
    """
    # Determine output path if not provided
    if excel_file_path is None:
        excel_file_path = os.path.splitext(json_file_path)[0] + '.xlsx'
    
    # Load JSON data
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Check if data is a list
    if not isinstance(data, list):
        # If data is a dictionary with sections, flatten it
        if isinstance(data, dict):
            flattened_data = []
            for section, qa_pairs in data.items():
                if isinstance(qa_pairs, list):
                    flattened_data.extend(qa_pairs)
            data = flattened_data
        else:
            raise ValueError("JSON data must be a list of QA pairs or a dictionary of sections with QA pairs")
    
    # Extract questions and answers
    qa_pairs = []
    for item in data:
        if "question" in item and "answer" in item:
            qa_pairs.append({
                "Question": item["question"],
                "Answer": item["answer"]
            })
    
    # Create DataFrame
    df = pd.DataFrame(qa_pairs)
    
    # Save to Excel
    df.to_excel(excel_file_path, index=False)
    
    print(f"Converted {len(qa_pairs)} QA pairs to Excel file: {excel_file_path}")
    return excel_file_path

def process_directory(input_dir, output_dir=None):
    """
    Process all JSON files in a directory and convert them to Excel.
    
    Args:
        input_dir (str): Directory containing JSON files
        output_dir (str, optional): Directory to save Excel files. If None, 
                                    will save in the same directory as JSON files
    """
    input_path = Path(input_dir)
    
    if output_dir:
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True, parents=True)
    else:
        output_path = input_path
    
    # Find all JSON files
    json_files = list(input_path.glob('*.json'))
    
    if not json_files:
        print(f"No JSON files found in {input_dir}")
        return
    
    print(f"Found {len(json_files)} JSON files to process")
    
    # Process each file
    for json_file in json_files:
        output_file = output_path / f"{json_file.stem}.xlsx"
        try:
            convert_json_to_excel(str(json_file), str(output_file))
        except Exception as e:
            print(f"Error processing {json_file}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Convert JSON QA pairs to Excel files")
    parser.add_argument("--input", required=True, help="Input JSON file or directory")
    parser.add_argument("--output", help="Output Excel file or directory (optional)")
    parser.add_argument("--batch", action="store_true", help="Process all JSON files in the input directory")
    
    args = parser.parse_args()
    
    if args.batch:
        process_directory(args.input, args.output)
    else:
        convert_json_to_excel(args.input, args.output)

if __name__ == "__main__":
    main()
# Dataset Management System

This directory contains the dataset management system for processing and storing call transcripts, including database operations, data format conversion utilities, and a user interface for data management.

## Directory Structure

```
Dataset/
├── DB/                     # Database and data storage directory
│   ├── assets/            # Additional assets and resources
│   ├── excel/            # Excel files storage
│   ├── jsonl/            # JSONL format data for training
│   ├── local_json/       # Local JSON storage
│   ├── temp/             # Temporary files
│   └── retell.sqlite     # SQLite database file
├── UI/                    # User Interface components
│   ├── DB/               # Database mirror for UI operations
│   │   ├── excel/        # Processed Q&A pairs
│   │   ├── json/         # JSON format storage
│   │   ├── jsonl/        # Training data
│   │   ├── local_json/   # Local processing storage
│   │   └── retell.sqlite # UI database instance
│   ├── Pages/            # Streamlit application pages
│   │   ├── 1_Fetch_Transcripts.py  # Transcript management
│   │   ├── 2_Generate_QA.py        # Q&A generation
│   │   ├── 3_Export_Data.py        # Data export utilities
│   │   └── 3_chatbot.py            # Interactive chatbot
│   └── main.py           # Main UI application entry
├── json_to_excel.py      # Convert JSON to Excel format
├── excel_to_jsonl.py     # Convert Excel to JSONL format
├── md_to_qa.py          # Convert Markdown to Q&A format
├── fetch_call_transcript.py # Fetch call transcripts
└── README.md            # This documentation file
```

## Components

### Core Scripts

#### json_to_excel.py
Converts JSON files containing question-answer pairs to Excel format.
- Input: JSON files from `DB/local_json/`
- Output: Excel files with Q&A pairs
- Features:
  - Handles both single JSON files and batch processing
  - Supports command-line arguments
  - Preserves call IDs and conversation structure
  - Validates input JSON format
  - Handles nested conversation structures

#### excel_to_jsonl.py
Converts Excel files with QA pairs to JSONL format for chatbot training.
- Input: Excel files from `DB/excel/`
- Output: JSONL files in `DB/jsonl/`
- Features:
  - Processes multiple Excel files
  - Adds system messages for context
  - Generates timestamped output files
  - Supports custom column mapping
  - Handles various Excel formats

#### md_to_qa.py
Converts Markdown files to Q&A format for training data generation.

#### fetch_call_transcript.py
Retrieves and processes call transcripts for storage and analysis.

### UI Application

The UI component provides a user-friendly interface for managing the dataset:

#### Pages
- **Fetch Transcripts**: Interface for retrieving and managing call transcripts
- **Generate Q&A**: Tools for creating and editing Q&A pairs
- **Export Data**: Utilities for exporting data in various formats
- **Chatbot**: Interactive interface for testing the chatbot

## Data Storage

### DB Directory

- **assets/**: Additional resources and assets for data processing
- **excel/**: Stores Excel files containing processed Q&A pairs
- **jsonl/**: Contains JSONL format files optimized for training
- **local_json/**: Stores raw JSON files with conversation data
- **temp/**: Temporary storage for data processing
- **retell.sqlite**: SQLite database for efficient data management

### UI/DB Directory
Mirrors the main DB structure for UI operations, ensuring data consistency and separation of concerns.

## Usage

### Converting JSON to Excel
```bash
python json_to_excel.py --input DB/local_json/<file_name>
```

### Converting Excel to JSONL
```python
from excel_to_jsonl import convert_excel_files_to_jsonl

# Convert all Excel files in the directory
output_file = convert_excel_files_to_jsonl()
```

### Running the UI Application
```bash
streamlit run UI/main.py
```

## Data Format Examples

### JSON Format
```json
{
  "call_id": "call_xxxx",
  "transcript": "User: Question\nAgent: Answer"
}
```

### JSONL Format
```json
{"messages": [{"role": "system", "content": "System message"}, {"role": "user", "content": "Question"}, {"role": "assistant", "content": "Answer"}], "call_id": "call_xxxx"}
```

## Notes

- All timestamps in filenames follow the format: YYYYMMDD_HHMMSS
- The system supports batch processing for efficient data handling
- Data validation ensures integrity during format conversion
- Comprehensive error handling and logging for all operations
- Regular backups of the SQLite database are recommended
- The UI application provides real-time data management and visualization
- Database operations are synchronized between core and UI components
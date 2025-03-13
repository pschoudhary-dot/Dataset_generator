# Chatbot Dataset Management UI

A streamlined user interface for managing and processing chatbot training data.

## Overview

This application provides a user-friendly interface for managing conversation datasets, from fetching call transcripts to generating training data for chatbots.

## Directory Structure

```
UI/
├── DB/                     # Database and data storage
│   ├── excel/             # Processed Q&A pairs in Excel format
│   ├── json/              # JSON format data storage
│   ├── jsonl/             # JSONL format training data
│   ├── local_json/        # Local JSON storage for processing
│   └── retell.sqlite      # SQLite database for data management
├── Pages/                 # Streamlit pages for different functions
│   ├── 1_Fetch_Transcripts.py  # Fetch and process call transcripts
│   ├── 2_Generate_QA.py        # Generate Q&A pairs
│   ├── 3_Export_Data.py        # Export data in various formats
│   └── 3_chatbot.py            # Interactive chatbot interface
└── main.py               # Main application entry point
```

## Features

### Data Management
- **Database Storage**: Efficient SQLite database for managing conversation data
- **Multiple Format Support**: Handle data in Excel, JSON, and JSONL formats
- **Organized Structure**: Clear separation of raw data, processed Q&A pairs, and training datasets

### User Interface
1. **Fetch Transcripts**
   - Retrieve call transcripts from various sources
   - Process and store raw conversation data

2. **Generate Q&A**
   - Convert conversations into structured Q&A pairs
   - Apply data cleaning and formatting

3. **Export Data**
   - Export datasets in multiple formats (Excel, JSON, JSONL)
   - Generate training-ready data files

4. **Chatbot Interface**
   - Interactive testing environment
   - Real-time conversation simulation

## Getting Started

1. Launch the application:
   ```bash
   streamlit run main.py
   ```

2. Navigate through the sidebar to access different features:
   - Use "Fetch Transcripts" to import new conversation data
   - Process data into Q&A pairs using "Generate Q&A"
   - Export processed data in your preferred format
   - Test the chatbot using the interactive interface

## Data Flow

1. Raw transcripts → DB/local_json/
2. Processed Q&A pairs → DB/excel/
3. Training data → DB/jsonl/

## File Formats

- **Excel Files**: Structured Q&A pairs with metadata
- **JSON Files**: Raw conversation data and intermediate processing
- **JSONL Files**: Training-ready data format for machine learning

## Database Schema

The SQLite database (retell.sqlite) maintains:
- Conversation metadata
- Processing status
- Data relationships
- Export history
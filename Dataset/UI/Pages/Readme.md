# Pages Directory Documentation

This directory contains the Streamlit pages that make up the Chatbot Dataset Management UI. Each page serves a specific function in the data processing pipeline.

## Page Overview

### 1. Fetch Transcripts (1_Fetch_Transcripts.py)

**Purpose**: Retrieve and process call transcripts from various sources.

**Features**:
- Connect to transcript sources
- Download and validate transcripts
- Initial data cleaning and formatting
- Store raw transcripts in DB/local_json/

**Workflow**:
1. Select data source
2. Configure fetch parameters
3. Download transcripts
4. Validate and store data

### 2. Generate Q&A (2_Generate_QA.py)

**Purpose**: Convert raw transcripts into structured Q&A pairs.

**Features**:
- Conversation segmentation
- Q&A pair extraction
- Data cleaning and normalization
- Export to Excel format

**Workflow**:
1. Select source transcripts
2. Configure Q&A generation parameters
3. Process conversations
4. Save Q&A pairs to DB/excel/

### 3. Export Data (3_Export_Data.py)

**Purpose**: Convert and export data in various formats for different use cases.

**Features**:
- Multiple format support (Excel, JSON, JSONL)
- Batch processing
- Export configuration
- Data validation

**Workflow**:
1. Select source data
2. Choose export format
3. Configure export parameters
4. Generate output files

### 4. Chatbot Interface (3_chatbot.py)

**Purpose**: Provide an interactive environment for testing the chatbot.

**Features**:
- Real-time conversation
- Response evaluation
- Performance monitoring
- Debug information

**Workflow**:
1. Initialize chatbot model
2. Load training data
3. Start interactive session
4. Test and evaluate responses

## Common Utilities

Each page utilizes shared utilities for:
- Database operations
- File handling
- Data validation
- Error handling

## Best Practices

1. **Data Validation**
   - Always validate input data
   - Check file formats and content
   - Handle errors gracefully

2. **Performance**
   - Use batch processing for large datasets
   - Implement progress indicators
   - Cache intermediate results

3. **User Experience**
   - Provide clear feedback
   - Include help text and tooltips
   - Maintain consistent UI elements
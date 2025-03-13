'''
2. it connects with the sqlite db and stores the transcript string 
This code provides:

1. RetellTranscriptFetcher class:
   
   - Fetches all successful calls from the Retell API
   - Checks for existing call IDs to avoid duplicates
   - Stores transcripts and utterances in the database

2. SpecificCallFetcher class:
   
   - Fetches transcripts for specific call IDs
   - Reconstructs transcripts from utterances if needed
   - Exports results to a JSON file
   
3. Command-line interface:
   
   - Supports two modes: "all" or "specific"
   - Allows customizing database name, output file, and other parameters
'''

import os
import json
import sqlite3
import argparse
from pathlib import Path
from dotenv import load_dotenv
from retell import Retell
from create_db import RetellDatabase

class RetellTranscriptFetcher:
    """Class to fetch and store call transcripts from Retell API."""
    
    def __init__(self, db_folder="DB", db_name="retell.sqlite"):
        """Initialize with database connection and Retell API client."""
        # Setup database
        self.db = RetellDatabase(db_folder, db_name)
        self.db.connect()
        
        # Check if database exists and tables are created
        if not os.path.exists(self.db.db_path):
            print(f"Database not found at {self.db.db_path}. Creating...")
            self.db.create_tables()
        
        # Setup Retell API client
        load_dotenv()
        api_key = os.getenv("RETELL")
        if not api_key:
            raise ValueError("RETELL API KEY not found in environment variables")
        self.client = Retell(api_key=api_key)
    
    def get_existing_call_ids(self) -> set:
        """Return a set of all call IDs already in the database."""
        self.db.cursor.execute("SELECT call_id FROM calls")
        return set(row[0] for row in self.db.cursor.fetchall())
    
    def store_call(self, call_id: str, transcript: str, transcript_objects: list = None) -> bool:
        """Store a call and its transcript in the database if not already present."""
        try:
            # Check for duplicates
            self.db.cursor.execute("SELECT 1 FROM calls WHERE call_id = ?", (call_id,))
            if self.db.cursor.fetchone():
                print(f"Call ID {call_id} already exists. Skipping.")
                return False
            
            # Insert call with transcript
            self.db.cursor.execute('INSERT INTO calls (call_id, transcript) VALUES (?, ?)', 
                              (call_id, transcript))
            
            # Optionally store utterances (if provided)
            if transcript_objects:
                for idx, utterance in enumerate(transcript_objects):
                    role = getattr(utterance, 'role', 'unknown')
                    content = getattr(utterance, 'content', '')
                    self.db.cursor.execute('''
                    INSERT INTO utterances (call_id, role, content, utterance_index)
                    VALUES (?, ?, ?, ?)
                    ''', (call_id, role, content, idx))
            
            self.db.conn.commit()
            return True
        except Exception as e:
            print(f"Error storing call {call_id}: {e}")
            self.db.conn.rollback()
            return False
    
    def fetch_all_calls(self, limit: int = 200):
        """Fetch all successful calls from Retell API and store them in the database."""
        existing_call_ids = self.get_existing_call_ids()
        print(f"Found {len(existing_call_ids)} existing calls in the database")
        
        filter_criteria = {
            "call_successful": [True],
            "in_voicemail": [False]
        }
        
        try:
            calls = self.client.call.list(filter_criteria=filter_criteria, limit=limit)
            print(f"Fetched {len(calls)} calls from Retell API")
            
            new_calls_count = 0
            for call in calls:
                call_id = getattr(call, 'call_id', None)
                transcript = getattr(call, 'transcript', "")
                transcript_objects = getattr(call, 'transcript_object', [])
                
                if not call_id or not transcript:
                    print(f"Skipping call due to missing data: call_id={call_id}")
                    continue
                
                if call_id in existing_call_ids:
                    print(f"Call ID {call_id} already exists. Skipping.")
                    continue
                
                if self.store_call(call_id, transcript, transcript_objects):
                    print(f"Stored call ID: {call_id}")
                    new_calls_count += 1
                else:
                    print(f"Failed to store call ID: {call_id}")
            
            print(f"Successfully stored {new_calls_count} new calls")
            return new_calls_count
        
        except Exception as e:
            print(f"Error fetching calls: {e}")
            return 0
    
    def close(self):
        """Close the database connection."""
        self.db.close()


class SpecificCallFetcher:
    """Class to fetch and process specific call IDs from the database."""
    
    def __init__(self, db_folder="DB", db_name="retell.sqlite"):
        """Initialize with database connection."""
        # Setup database path
        self.db_folder = Path(os.path.dirname(os.path.abspath(__file__))) / db_folder
        self.db_path = self.db_folder / db_name
        
        # Check if database exists
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Database not found at {self.db_path}")
        
        # Connect to database
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
    
    def fetch_specific_calls(self, call_ids, output_path="call_transcripts.json"):
        """Fetch transcripts for specific call IDs and save to JSON."""
        # List to store call data
        call_data = []
        
        # Process each call ID
        for call_id in call_ids:
            print(f"Processing call ID: {call_id}")
            
            # Try to fetch transcript from the database
            self.cursor.execute("SELECT transcript FROM calls WHERE call_id = ?", (call_id,))
            result = self.cursor.fetchone()
            
            if result and result[0] is not None:
                transcript = result[0]
                call_data.append({
                    "call_id": call_id,
                    "transcript": transcript
                })
                print(f"  Found transcript ({len(transcript)} characters)")
            else:
                # If no transcript found or transcript is None, check if we can reconstruct from utterances
                self.cursor.execute("""
                    SELECT role, content FROM utterances 
                    WHERE call_id = ? 
                    ORDER BY utterance_index
                """, (call_id,))
                
                utterances = self.cursor.fetchall()
                
                if utterances:
                    # Reconstruct transcript from utterances
                    transcript = ""
                    for role, content in utterances:
                        if content is None:
                            content = ""
                        role_display = "Agent" if role.lower() == "agent" else "User"
                        transcript += f"{role_display}: {content}\n"
                    
                    call_data.append({
                        "call_id": call_id,
                        "transcript": transcript.strip()
                    })
                    print(f"  Reconstructed transcript from {len(utterances)} utterances")
                else:
                    # No data found for this call ID
                    call_data.append({
                        "call_id": call_id,
                        "transcript": "No transcript available"
                    })
                    print(f"  No transcript found")
        
        # Write to JSON file
        output_file = self.db_folder / output_path
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(call_data, f, indent=2, ensure_ascii=False)
        
        print(f"\nJSON file created successfully at {output_file}")
        print(f"Total calls processed: {len(call_data)}")
        print(f"Calls with transcripts: {sum(1 for call in call_data if call['transcript'] != 'No transcript available')}")
        
        return call_data
    
    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()


def fetch_all_call_transcripts():
    """Command-line function to fetch all call transcripts."""
    parser = argparse.ArgumentParser(description="Fetch and store Retell call transcripts.")
    parser.add_argument("--limit", type=int, default=200, help="Number of calls to fetch")
    parser.add_argument("--db_name", type=str, default="retell_conversations.sqlite", 
                        help="Name of the database file")
    args = parser.parse_args()
    
    fetcher = RetellTranscriptFetcher(db_name=args.db_name)
    try:
        fetcher.fetch_all_calls(limit=args.limit)
    finally:
        fetcher.close()


def fetch_specific_call_transcripts():
    """Command-line function to fetch specific call transcripts."""
    parser = argparse.ArgumentParser(description="Fetch specific call transcripts and save to JSON.")
    parser.add_argument("--call_ids", nargs="+", required=True, help="List of call IDs to fetch")
    parser.add_argument("--output", type=str, default="call_transcripts.json", 
                        help="Output JSON file name")
    parser.add_argument("--db_name", type=str, default="retell.sqlite", 
                        help="Name of the database file")
    args = parser.parse_args()
    
    fetcher = SpecificCallFetcher(db_name=args.db_name)
    try:
        fetcher.fetch_specific_calls(args.call_ids, args.output)
    finally:
        fetcher.close()


if __name__ == "__main__":
    # By default, fetch all calls
    # To fetch specific calls, run with --call_ids argument
    parser = argparse.ArgumentParser(description="Fetch Retell call transcripts.")
    parser.add_argument("--mode", choices=["all", "specific"], default="all",
                        help="Fetch all calls or specific call IDs")
    parser.add_argument("--call_ids", nargs="+", help="List of call IDs to fetch (for specific mode)")
    parser.add_argument("--limit", type=int, default=200, help="Number of calls to fetch (for all mode)")
    parser.add_argument("--output", type=str, default="call_transcripts.json", 
                        help="Output JSON file name (for specific mode)")
    parser.add_argument("--db_name", type=str, default="retell.sqlite", 
                        help="Name of the database file")
    
    args = parser.parse_args()
    
    if args.mode == "all":
        fetcher = RetellTranscriptFetcher(db_name=args.db_name)
        try:
            fetcher.fetch_all_calls(limit=args.limit)
        finally:
            fetcher.close()
    else:
        if not args.call_ids:
            print("Error: --call_ids is required for specific mode")
            exit(1)
        
        fetcher = SpecificCallFetcher(db_name=args.db_name)
        try:
            fetcher.fetch_specific_calls(args.call_ids, args.output)
        finally:
            fetcher.close()
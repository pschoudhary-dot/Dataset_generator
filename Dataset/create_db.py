'''
1. This is the starting point of the code 
- Creates a reusable RetellDatabase class that can be imported and used from other files
- Creates and Places the database in a "DB" subfolder within the Dataset directory
- Checks if the database already exists and notifies the user
- Only creates the tables if needed with the create_tables() method
- Provides connection management with connect() and close() methods
- Includes a command-line interface to create the database with an optional custom name
'''

import os
import sqlite3
import argparse
import streamlit as st
from pathlib import Path

class RetellDatabase:
    """Database manager for Retell call data with tables for calls, utterances, and Q&A pairs."""
    
    def __init__(self, db_name="retell.sqlite"):
        """Initialize database connection and setup paths."""
        # Use Streamlit's session state for database configuration
        if 'db_path' not in st.session_state:
            # Create DB folder in the UI directory
            db_folder = Path(os.path.dirname(os.path.abspath(__file__))) / "UI" / "DB"
            db_folder.mkdir(parents=True, exist_ok=True)
            st.session_state.db_path = db_folder / db_name
        
        self.db_path = st.session_state.db_path
        self.db_exists = self.db_path.exists()
        
        # Connect to database
        self.conn = None
        self.cursor = None
    
    def connect(self):
        """Connect to the SQLite database."""
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
        return self.conn
    
    def create_tables(self):
        """Create tables for storing calls, utterances, and Q&A pairs if they don't exist."""
        if self.db_exists:
            print(f"Database already exists at {self.db_path}")
        else:
            print(f"Creating new database at {self.db_path}")
        
        self.connect()
        
        # Calls table with transcript
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS calls (
            call_id TEXT PRIMARY KEY,
            transcript TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Utterances table
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS utterances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            call_id TEXT,
            role TEXT,
            content TEXT,
            utterance_index INTEGER,
            FOREIGN KEY (call_id) REFERENCES calls (call_id)
        )
        ''')
        
        # Q&A pairs table
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS qa_pairs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            call_id TEXT,
            question TEXT,
            answer TEXT,
            FOREIGN KEY (call_id) REFERENCES calls (call_id)
        )
        ''')
        
        self.conn.commit()
        print("Database tables created successfully")
        return True
    
    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
            self.cursor = None

# Initialize database when imported
def init_database():
    """Initialize the database with Streamlit."""
    db = RetellDatabase()
    db.create_tables()
    return db

def create_database():
    """Create the database and tables."""
    parser = argparse.ArgumentParser(description="Create Retell database tables.")
    parser.add_argument("--db_name", type=str, default="retell.sqlite", 
                        help="Name of the database file")
    args = parser.parse_args()
    
    db = RetellDatabase(db_name=args.db_name)
    db.create_tables()
    db.close()
    
    print(f"Database setup complete at {db.db_path}")


if __name__ == "__main__":
    create_database()

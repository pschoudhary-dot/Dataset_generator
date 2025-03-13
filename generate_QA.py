import os
import json
import random
import sqlite3
import argparse
import time
from pathlib import Path
from tqdm import tqdm
from dotenv import load_dotenv
import google.generativeai as genai

class TranscriptFetcher:
    """Class to fetch specific call transcripts from the database and convert to JSON."""
    
    def __init__(self, db_folder="DB", db_name="retell.sqlite"):
        """Initialize with database connection."""
        # Setup database path
        self.db_folder = Path(os.path.dirname(os.path.abspath(__file__))) / db_folder
        self.db_path = self.db_folder / db_name
        
        # Check if database exists
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Database not found at {self.db_path}")
        
        # Create output directory if it doesn't exist
        self.output_dir = self.db_folder / "local_json"
        self.output_dir.mkdir(exist_ok=True)
        
        # Connect to database
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
    
    def fetch_specific_calls(self, call_ids, output_filename="selected_transcripts.json"):
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
                # If no transcript found, try to reconstruct from utterances
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
                    print(f"  No transcript found for {call_id}")
        
        # Write to JSON file
        output_path = self.output_dir / output_filename
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(call_data, f, indent=2, ensure_ascii=False)
        
        print(f"\nJSON file created successfully at {output_path}")
        print(f"Total calls processed: {len(call_data)}")
        
        return call_data, str(output_path)
    
    def __del__(self):
        """Cleanup database connection."""
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()

    def __del__(self):
        """Destructor to ensure database connection is closed."""
        self.close()


class RandomTranscriptFetcher:
    """Class to fetch random call transcripts from the database and convert to JSON."""
    
    def __init__(self, db_folder="DB", db_name="retell.sqlite"):
        """Initialize with database connection."""
        # Setup database path
        self.db_folder = Path(os.path.dirname(os.path.abspath(__file__))) / db_folder
        self.db_path = self.db_folder / db_name
        
        # Check if database exists
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Database not found at {self.db_path}")
        
        # Create output directory if it doesn't exist
        self.output_dir = self.db_folder / "local_json"
        self.output_dir.mkdir(exist_ok=True)
        
        # Connect to database
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
    
    def fetch_random_calls(self, count=10, min_length=200, output_filename="random_transcripts.json"):
        """Fetch random call transcripts and save to JSON."""
        # Get all call IDs with transcripts longer than min_length
        self.cursor.execute("""
            SELECT call_id, length(transcript) as transcript_length 
            FROM calls 
            WHERE length(transcript) > ? 
            ORDER BY transcript_length DESC
        """, (min_length,))
        
        eligible_calls = self.cursor.fetchall()
        
        if not eligible_calls:
            print(f"No calls found with transcript length > {min_length}")
            return [], ""
        
        print(f"Found {len(eligible_calls)} eligible calls")
        
        # Select random calls (up to count)
        sample_size = min(count, len(eligible_calls))
        selected_calls = random.sample(eligible_calls, sample_size)
        
        # Get call IDs from selected calls
        selected_call_ids = [call[0] for call in selected_calls]
        
        # Fetch full transcripts for selected calls
        call_data = []
        for call_id in selected_call_ids:
            self.cursor.execute("SELECT transcript FROM calls WHERE call_id = ?", (call_id,))
            result = self.cursor.fetchone()
            
            if result and result[0]:
                call_data.append({
                    "call_id": call_id,
                    "transcript": result[0]
                })
                print(f"Selected call {call_id} with {len(result[0])} characters")
        
        # Write to JSON file
        output_path = self.output_dir / output_filename
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(call_data, f, indent=2, ensure_ascii=False)
        
        print(f"\nJSON file created successfully at {output_path}")
        print(f"Total random calls selected: {len(call_data)}")
        
        return call_data, str(output_path)
    
    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()


class QAPairGenerator:
    """Class to generate QA pairs from call transcripts using Gemini API."""
    
    def __init__(self, db_folder="DB", db_name="retell.sqlite"):
        """Initialize the QA generator with Gemini API and database connection."""
        # Load environment variables
        load_dotenv()
        
        # Configure Gemini API
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-2.0-pro-exp-02-05')

        # Setup database connection
        self.db_folder = Path(os.path.dirname(os.path.abspath(__file__))) / db_folder
        self.db_path = self.db_folder / db_name
        
        # Check if database exists
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Database not found at {self.db_path}")
        
        # Connect to database
        self.conn = sqlite3.connect(self.db_path)
        self.db = self.conn
        self.cursor = self.conn.cursor()
    
    def generate_qa_pairs(self, transcript, call_id):
        """Generate QA pairs from a transcript using Gemini."""
        # Clean transcript by replacing placeholders and removing personal identifiers
        cleaned_transcript = transcript.replace("[Customer's Name]", "Customer")
        
        prompt = f"""
            Below is a transcript from a customer service call about ESA (Emotional Support Animal) letters from Wellness Wag.
            Generate 5-8 question-answer pairs that simulate a NATURAL conversation between a customer and a Wellness Wag support agent.

            WHAT I NEED:
            - Create question-answer pairs that sound like they come from REAL HUMAN CONVERSATIONS
            - Questions should be in NATURAL, CASUAL language - not perfect or formal
            - Focus on how REAL CUSTOMERS actually speak (with hesitations, simple language, etc.)
            - The answers should be helpful but conversational, like a real support agent would speak

            IMPORTANT REQUIREMENTS FOR QUESTIONS:
            1. Make questions sound NATURAL and CONVERSATIONAL - use contractions, simple language
            2. Include natural speech patterns like "Um," "So," "Hey," "I was wondering," etc.
            3. Keep questions SHORT and SIMPLE as real customers would ask
            4. Avoid formal language or perfectly structured sentences in questions
            5. Questions should only contain information the customer would actually know
            6. Make questions sound like they're spoken, not written

            IMPORTANT REQUIREMENTS FOR ANSWERS:
            1. Answers should be HELPFUL and COMPLETE but still sound conversational
            2. Include Wellness Wag's contact info (email: hello@wellnesswag.com, phone: (415) 570-7864) when relevant
            3. Focus ONLY on topics discussed in this specific transcript
            4. Include exact prices, timeframes, and processes mentioned in the transcript
            5. Make the answers thorough but still sound like a real person speaking
            6. NEVER mention "the transcript" or refer to information being in or not in "the transcript"
            7. If a question asks for information not explicitly in the conversation, provide a helpful response that directs them to contact Wellness Wag instead of saying "the transcript doesn't mention this"
            8. For uncertain information, say things like "I believe" or "typically" or offer to check for them, rather than pointing out missing information
            9. Always respond as if you ARE the Wellness Wag agent, not as someone analyzing a transcript

            EXAMPLES OF GOOD NATURAL QUESTIONS:
            - "So how much is this gonna cost me if I have two pets?"
            - "Can you just send me that payment link thing to my phone?"
            - "Do you guys have any discounts? It's kind of expensive."
            - "I'm a bit confused about the price - I thought I saw something about $32?"

            EXAMPLES OF BAD QUESTIONS (TOO FORMAL):
            - "Can you please confirm the exact cost for an ESA letter for two pets?" (too formal)
            - "Would you be willing to send the payment link to both my email and phone number?" (too stiff)
            - "I'm inquiring about potential discounts on your ESA letter service." (no real person talks like this)

            EXAMPLES OF GOOD NATURAL ANSWERS:
            - "So the ESA letter for up to two pets costs $129. If you'd like, I can send a payment link right to your email and phone to make it easier. And if you need anything else, just give us a call at (415) 570-7864."
            - "I'd be happy to send you that payment link right away! We'll send it to both your email and phone so you can just click and complete your application whenever you're ready. If you get stuck with anything, just email us at hello@wellnesswag.com."

            EXAMPLES OF BAD ANSWERS (DO NOT WRITE LIKE THIS):
            - "The transcript doesn't specify the exact timeframe." (Never refer to "the transcript")
            - "This information wasn't mentioned in our conversation." (Don't point out missing info)
            - "I don't have information about that specific question." (Instead, offer to help or check)

            GOOD WAYS TO HANDLE INFORMATION NOT IN THE TRANSCRIPT:
            - "Typically, we process those within 24-48 hours, but I can double-check the exact timeframe for your state if you'd like."
            - "I'd be happy to look into that for you. If you'd like that specific information, you can give us a call at (415) 570-7864 or email us at hello@wellnesswag.com."
            - "While I don't have the exact figure in front of me, I can certainly find out for you if you'd like to know the precise amount. Would you like me to check that?"

            Transcript:
            {cleaned_transcript}

            Format your response as a JSON array of objects, each with 'question' and 'answer' fields.
            Make the questions sound like they came from a real person on the phone, not from written text.
            If you cannot generate relevant questions from this transcript, return an empty array [].
        """
        
        # The rest of the function remains the same
        try:
            response = self.model.generate_content(prompt)
            
            # Extract text from response
            if hasattr(response, 'text'):
                response_text = response.text
            else:
                response_text = ''.join([part.text for part in response.parts])
            
            # Clean up the response text to ensure it's valid JSON
            response_text = response_text.replace('```json', '').replace('```', '').strip()
            
            # Parse the JSON
            qa_pairs = json.loads(response_text)
            
            # If no relevant QA pairs could be generated, return empty list
            if not qa_pairs:
                print(f"No relevant QA pairs could be generated for call {call_id}")
                return []
            
            # Add call_id to each QA pair and ensure proper formatting
            for qa in qa_pairs:
                qa['call_id'] = call_id
                
                # Ensure questions end with question marks
                if not qa['question'].endswith('?'):
                    qa['question'] = qa['question'] + '?'
                
                # Remove any markdown formatting from answers
                qa['answer'] = qa['answer'].replace('**', '').replace('*', '').replace('_', '')
                
                # Ensure answers are complete sentences
                if qa['answer'] and not qa['answer'].endswith(('.', '!', '?')):
                    qa['answer'] = qa['answer'] + '.'
                
            return qa_pairs
            
        except Exception as e:
            print(f"Error generating QA pairs for call {call_id}: {e}")
            # Return empty list instead of fallback QA pair
            return []
    
    def process_transcripts(self, transcripts_data, output_filename="qa_pairs.json"):
        """Process transcripts and generate QA pairs."""
        # Check if transcripts_data is a file path or a list
        if isinstance(transcripts_data, str):
            # Load transcripts from file
            with open(transcripts_data, 'r', encoding='utf-8') as f:
                transcripts = json.load(f)
        else:
            # Use provided list
            transcripts = transcripts_data
        
        print(f"Processing {len(transcripts)} call transcripts")
        
        all_qa_pairs = []
        processed_count = 0
        skipped_count = 0
        empty_result_count = 0
        
        # Process each transcript with progress bar
        for call_data in tqdm(transcripts, desc="Generating QA pairs"):
            call_id = call_data["call_id"]
            transcript = call_data["transcript"]
            
            # Skip empty or very short transcripts
            if not transcript or len(transcript) < 50:
                print(f"Skipping call {call_id} - transcript too short")
                skipped_count += 1
                continue
                
            # Generate QA pairs
            qa_pairs = self.generate_qa_pairs(transcript, call_id)
            
            if qa_pairs:
                all_qa_pairs.extend(qa_pairs)
                processed_count += 1
            else:
                empty_result_count += 1
            
            # Add a small delay to avoid rate limiting
            time.sleep(1)
        
        # Save all QA pairs to a JSON file
        output_path = self.output_dir / output_filename
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(all_qa_pairs, f, indent=2, ensure_ascii=False)
        
        print(f"\nGenerated {len(all_qa_pairs)} QA pairs from {processed_count} transcripts")
        print(f"Skipped {skipped_count} transcripts (too short)")
        print(f"No relevant QA pairs from {empty_result_count} transcripts")
        print(f"Results saved to {output_path}")
        
        # Print a few examples
        if all_qa_pairs:
            print("\nExample QA pairs:")
            for i, qa in enumerate(all_qa_pairs[:3]):
                print(f"\nExample {i+1}:")
                print(f"Q: {qa['question']}")
                print(f"A: {qa['answer']}")
        
        return all_qa_pairs, str(output_path)


def main():
    """Main function to run the QA generation process."""
    parser = argparse.ArgumentParser(description="Generate QA pairs from call transcripts.")
    parser.add_argument("--mode", choices=["specific", "random", "file"], default="random",
                        help="Mode to fetch transcripts: specific call IDs, random calls, or from file")
    parser.add_argument("--call_ids", nargs="+", help="List of call IDs (for specific mode)")
    parser.add_argument("--count", type=int, default=10, help="Number of random calls to fetch (for random mode)")
    parser.add_argument("--input_file", type=str, help="Input JSON file with transcripts (for file mode)")
    parser.add_argument("--output_file", type=str, default="gemini.json", help="Output JSON file for QA pairs")
    
    args = parser.parse_args()
    
    # Step 1: Fetch transcripts based on mode
    transcripts = None
    transcripts_file = None
    
    if args.mode == "specific":
        if not args.call_ids:
            print("Error: --call_ids is required for specific mode")
            return
        
        fetcher = TranscriptFetcher()
        try:
            transcripts, transcripts_file = fetcher.fetch_specific_calls(
                args.call_ids, 
                output_filename="selected_transcripts.json"
            )
        finally:
            fetcher.close()
    
    elif args.mode == "random":
        fetcher = RandomTranscriptFetcher()
        try:
            transcripts, transcripts_file = fetcher.fetch_random_calls(
                count=args.count,
                output_filename="random_transcripts.json"
            )
        finally:
            fetcher.close()
    
    elif args.mode == "file":
        if not args.input_file:
            print("Error: --input_file is required for file mode")
            return
        
        transcripts_file = args.input_file
        # Transcripts will be loaded by the QA generator
    
    # Step 2: Generate QA pairs
    if transcripts_file or transcripts:
        qa_generator = QAPairGenerator()
        qa_generator.process_transcripts(
            transcripts if transcripts else transcripts_file,
            output_filename=args.output_file
        )
    else:
        print("No transcripts to process")


if __name__ == "__main__":
    main()

'''
run this 
(venv) PS D:\Projects\chatbot\chatbot\Dataset> python d:\Projects\chatbot\chatbot\Dataset\3_generate_QA.py --mode specific --call_ids call_daad7a6df40210c2941a6f8eb47 call_65ed744f5c5f270e112a288de8a call_8e579736e08dd1d3966fde7f242 call_ea664a6b2b67ce3ae6f3eabd8cd call_a4acbfa181503f513939691789d call_89b1d78f4dbe77259ef789217cb call_b561c4c8fa0ea90a5c690af6a93 call_a5efe770cff4527c48c8386f8c4 call_823851840dd5fcb7dbdc554c450 call_dc5818d19caf2a43c430fc693a8 call_be9b29af303e10e6e36eb3022cb
'''
import os
import json
import re
import time
from pathlib import Path
from tqdm import tqdm
from dotenv import load_dotenv
import google.generativeai as genai

class MDQAPairGenerator:
    """Class to generate QA pairs from markdown files using Gemini API."""
    
    def __init__(self):
        """Initialize the QA generator with Gemini API."""
        # Load environment variables
        load_dotenv()
        
        # Configure Gemini API
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Create output directory if it doesn't exist
        self.output_dir = Path(os.path.dirname(os.path.abspath(__file__))) / "DB" / "local_json"
        self.output_dir.mkdir(exist_ok=True, parents=True)
    
    def extract_sections(self, md_file_path):
        """Extract sections from a markdown file."""
        with open(md_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find all section headers (lines starting with # or ##)
        section_pattern = r'(^|\n)#{1,3}\s+(.*?)(?=\n)'
        section_matches = re.finditer(section_pattern, content)
        
        sections = []
        last_pos = 0
        
        # Extract sections and their positions
        for match in section_matches:
            section_title = match.group(2).strip()
            start_pos = match.start()
            
            # Add previous section if it exists
            if sections and last_pos < start_pos:
                sections[-1]['end_pos'] = start_pos
                sections[-1]['content'] = content[sections[-1]['start_pos']:sections[-1]['end_pos']]
            
            # Add current section
            sections.append({
                'title': section_title,
                'start_pos': start_pos,
                'end_pos': len(content)  # Will be updated in next iteration
            })
            
            last_pos = start_pos
        
        # Add content to the last section
        if sections:
            sections[-1]['content'] = content[sections[-1]['start_pos']:sections[-1]['end_pos']]
        
        return sections
    
    def extract_existing_qa_pairs(self, section_content):
        """Extract existing QA pairs from section content."""
        # Extract existing QA pairs
        existing_qa_pattern = r'Q:\s*(.*?)\s*\n\s*A:\s*(.*?)(?=\n\s*Q:|$)'
        existing_qa_matches = re.findall(existing_qa_pattern, section_content, re.DOTALL)
        
        existing_qa_pairs = []
        for q, a in existing_qa_matches:
            existing_qa_pairs.append({
                "question": q.strip(),
                "answer": a.strip()
            })
        
        return existing_qa_pairs
    
    def generate_state_specific_qa_pairs(self, section_content, section_title):
        """Generate state-specific QA pairs for laws and requirements."""
        # Check if this is a section about laws or state requirements
        if "law" in section_title.lower() or "state" in section_title.lower():
            # Extract state names and their requirements
            state_pattern = r'(?:in|for)\s+([A-Z][a-z]+)(?:,|\s+Law|\s+[A-Z]{2}-\d+)'
            state_matches = re.finditer(state_pattern, section_content)
            
            states = []
            for match in state_matches:
                state = match.group(1)
                if state not in states and state not in ["Law", "ESA"]:
                    states.append(state)
            
            # Generate QA pairs for each state
            state_qa_pairs = []
            for state in states:
                # Find content related to this state
                state_content_pattern = r'(?:in|for)\s+' + state + r'(?:,|\s+Law|\s+[A-Z]{2}-\d+).*?(?=(?:in|for)\s+[A-Z][a-z]+(?:,|\s+Law|\s+[A-Z]{2}-\d+)|$)'
                state_content_match = re.search(state_content_pattern, section_content, re.DOTALL)
                
                if state_content_match:
                    state_content = state_content_match.group(0)
                    
                    # Create a QA pair for this state
                    state_qa_pairs.append({
                        "question": f"What are the requirements for obtaining an ESA letter in {state}?",
                        "answer": f"In {state}, {state_content.strip()}",
                        "section": section_title,
                        "state": state
                    })
            
            return state_qa_pairs
        
        return []
    
    def generate_qa_pairs_for_section(self, section):
        """Generate QA pairs for a section using Gemini."""
        section_title = section['title']
        section_content = section['content']
        
        # Extract existing QA pairs
        existing_qa_pairs = self.extract_existing_qa_pairs(section_content)
        
        # Generate state-specific QA pairs if applicable
        state_qa_pairs = self.generate_state_specific_qa_pairs(section_content, section_title)
        
        # If there are existing QA pairs, use them as examples
        examples = ""
        if existing_qa_pairs:
            examples = "Here are some example QA pairs from the content:\n"
            for i, qa in enumerate(existing_qa_pairs[:3]):  # Use up to 3 examples
                examples += f"Example {i+1}:\nQ: {qa['question']}\nA: {qa['answer']}\n\n"
        
        prompt = f"""
        Below is content from a section titled "{section_title}" about ESA (Emotional Support Animal) letters from Wellness Wag. 
        Generate 5-8 meaningful question-answer pairs that could be used to train a customer support chatbot.
        
        {examples}
        
        Focus on:
        1. Create a separate question for EACH specific piece of information in the content
        2. If there are multiple states mentioned, create a separate question for EACH state
        3. If there are specific laws or requirements mentioned, create questions about those specific details
        4. Use simple, direct language that customers would actually use
        5. Make sure answers are comprehensive and include all relevant details
        
        Important guidelines:
        - DO NOT use placeholders like [state] or [requirement] - fill in the actual information
        - Include specific information like prices, timeframes, and requirements when mentioned
        - Make the questions sound like real customer inquiries
        - Ensure answers are accurate based on the provided content
        - If the section mentions specific states (Arkansas, California, Iowa, Louisiana, Montana), create separate questions for each state
        
        Section Content:
        {section_content}
        
        Format your response as a JSON array of objects, each with 'question' and 'answer' fields.
        Example:
        [
            {{"question": "What is the requirement in Arkansas for obtaining an ESA letter?", "answer": "In Arkansas, Law HB1420 requires a 30-day relationship with a licensed mental health professional before issuing an ESA letter. Our process makes this easy: after you register, a licensed Arkansas physician will give you an initial call to gather some basic information and start the relationship. After 30 days, the same physician will follow up to ensure everything is in order and then issue your ESA letter."}},
            {{"question": "How does the ESA letter process work in California?", "answer": "California Law AB-468 mandates a 30-day relationship with a licensed mental health professional before an ESA letter can be provided. Once you register for an ESA letter, a licensed California physician will reach out for an introductory call to begin the relationship. After 30 days, they will follow up, confirm everything is on track, and issue your ESA letter."}}
        ]
        """
        
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
            
            # Add section to each QA pair
            for qa in qa_pairs:
                qa['section'] = section_title
                
            # Add state-specific QA pairs if any
            if state_qa_pairs:
                qa_pairs.extend(state_qa_pairs)
            
            # Add existing QA pairs if they're not already covered
            existing_questions = [qa['question'].lower() for qa in qa_pairs]
            for qa in existing_qa_pairs:
                if qa['question'].lower() not in existing_questions:
                    qa['section'] = section_title
                    qa_pairs.append(qa)
            
            return qa_pairs
            
        except Exception as e:
            print(f"Error generating QA pairs for section '{section_title}': {e}")
            # Return existing QA pairs if any, or a minimal fallback QA pair
            if existing_qa_pairs:
                for qa in existing_qa_pairs:
                    qa['section'] = section_title
                return existing_qa_pairs
            elif state_qa_pairs:
                return state_qa_pairs
            else:
                return [{
                    "question": f"What information is available about {section_title}?", 
                    "answer": "Please refer to our documentation for detailed information on this topic.",
                    "section": section_title
                }]
    
    def process_markdown_file(self, md_file_path, output_filename=None):
        """Process markdown file and generate QA pairs for each section."""
        # Extract file name for default output
        if output_filename is None:
            file_name = os.path.basename(md_file_path)
            base_name = os.path.splitext(file_name)[0]
            output_filename = f"{base_name}_qa_pairs.json"
        
        # Extract sections
        sections = self.extract_sections(md_file_path)
        
        # Generate QA pairs for each section
        all_qa_pairs = []
        qa_by_section = {}
        
        # Process each section with progress bar
        for section in tqdm(sections, desc="Processing sections"):
            print(f"\nProcessing section: {section['title']}")
            section_qa_pairs = self.generate_qa_pairs_for_section(section)
            
            # Add to overall list
            all_qa_pairs.extend(section_qa_pairs)
            
            # Add to section dictionary
            qa_by_section[section['title']] = section_qa_pairs
            
            print(f"Generated {len(section_qa_pairs)} QA pairs for section '{section['title']}'")
            
            # Add a small delay to avoid rate limiting
            time.sleep(1)
        
        # Save all QA pairs
        output_path = self.output_dir / output_filename
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(all_qa_pairs, f, indent=2, ensure_ascii=False)
        
        print(f"Saved {len(all_qa_pairs)} QA pairs to {output_path}")
        
        # Save QA pairs by section
        section_output_path = self.output_dir / f"sections_{output_filename}"
        with open(section_output_path, 'w', encoding='utf-8') as f:
            json.dump(qa_by_section, f, indent=2, ensure_ascii=False)
        
        print(f"Saved QA pairs by section to {section_output_path}")
        
        # Print a few examples
        if all_qa_pairs:
            print("\nExample QA pairs:")
            for i, qa in enumerate(all_qa_pairs[:3]):
                print(f"\nExample {i+1}:")
                print(f"Q: {qa['question']}")
                print(f"A: {qa['answer']}")
        
        return all_qa_pairs, qa_by_section


def main():
    """Main function to generate QA pairs from markdown files."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate QA pairs from markdown files using Gemini API.")
    parser.add_argument("--input", type=str, required=True, help="Input markdown file path")
    parser.add_argument("--output", type=str, default=None, help="Output JSON file name")
    
    args = parser.parse_args()
    
    generator = MDQAPairGenerator()
    generator.process_markdown_file(args.input, args.output)


if __name__ == "__main__":
    main()
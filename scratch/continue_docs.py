import os
import io
import time
from dotenv import load_dotenv
import google.genai as genai
from google.genai import types

load_dotenv()

SYSTEM_PROMPT = """You are a senior full-stack engineer tasked with producing complete, accurate technical documentation for this entire codebase. 
You previously stopped generating at the middle of Section 3.
Continue the documentation from where you stopped. Resume at the exact point you got cut off and complete all remaining sections through Section 23. Same rules apply — read the code, paste verbatim. Do not repeat the beginning of the document.

The output must be valid Markdown.
"""

def continue_docs():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not found in .env")
        return

    client = genai.Client(api_key=api_key)
    
    print("Reading all_code.txt...")
    with open('scratch/all_code.txt', 'r', encoding='utf-8') as f:
        code_content = f.read()

    print("Reading current PROJECT_DOCS.md...")
    with open('docs/PROJECT_DOCS.md', 'r', encoding='utf-8') as f:
        current_docs = f.read()

    prompt = f"Here is the codebase:\n<CODEBASE>\n{code_content}\n</CODEBASE>\n\nHere is what you have generated so far:\n<GENERATED>\n{current_docs}\n</GENERATED>\n\nContinue generating exactly where you left off. Start your response exactly with the text following the cut-off point."

    print("Calling Gemini API...")
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.0
            )
        )
        
        output_path = os.path.join(os.getcwd(), 'docs', 'PROJECT_DOCS.md')
        with open(output_path, 'a', encoding='utf-8') as f:
            f.write(response.text)
        print(f"Documentation continued successfully at {output_path}")
        
    except Exception as e:
        print(f"Generation failed: {e}")

if __name__ == '__main__':
    continue_docs()

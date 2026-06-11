import os
from google import genai
from google.genai import types
import sys
import dotenv
import time

dotenv.load_dotenv("D:/pantrymind-desktop/.env")
api_key = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=api_key)
model = "gemini-2.5-flash" # Use flash for higher quota

with open("D:/pantrymind-desktop/scratch/all_code.txt", "r", encoding="utf-8") as f:
    codebase = f.read()

with open("D:/pantrymind-desktop/scratch/doc_prompt.txt", "r", encoding="utf-8") as f:
    prompt = f.read()

os.makedirs("D:/pantrymind-desktop/docs", exist_ok=True)
outfile = "D:/pantrymind-desktop/docs/PROJECT_DOCS.md"

chunks = [
    "Generate ONLY Sections 1 through 6 of the requested documentation. Start directly with the # PantryMind — Complete Project Documentation title and Section 1.",
    "Generate ONLY Sections 7 through 11. Do not repeat previous sections. Start directly with ## 7. AI AGENTS",
    "Generate ONLY Sections 12 through 16. Do not repeat previous sections. Start directly with ## 12. KITCHEN AI CHEF",
    "Generate ONLY Sections 17 through 23. Do not repeat previous sections. Start directly with ## 17. FRONTEND"
]

with open(outfile, "w", encoding="utf-8") as out:
    for i, chunk_instruction in enumerate(chunks):
        print(f"Generating chunk {i+1}/4...")
        full_prompt = codebase + "\n\n" + prompt + "\n\nCRITICAL INSTRUCTION FOR THIS REQUEST: " + chunk_instruction
        try:
            response = client.models.generate_content(
                model=model,
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    temperature=0.0
                )
            )
            text = response.text
            if text.startswith('```markdown'):
                text = text[11:]
                if text.endswith('```'):
                    text = text[:-3]
            elif text.startswith('```'):
                text = text[3:]
                if text.endswith('```'):
                    text = text[:-3]
            
            out.write(text.strip() + "\n\n")
            print(f"Chunk {i+1} done. Wrote {len(text)} chars.")
            out.flush()
        except Exception as e:
            print(f"Failed on chunk {i+1}: {e}")
        
        # Sleep to avoid rate limits
        if i < len(chunks) - 1:
            print("Sleeping for 15 seconds to respect rate limits...")
            time.sleep(15)

print(f"Done! Documentation saved to {outfile}")

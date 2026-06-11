import os
from google import genai
from google.genai import types
import sys
import dotenv
import time

dotenv.load_dotenv("D:/pantrymind-desktop/.env")
api_key = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=api_key)
model = "gemini-2.5-flash"

with open("D:/pantrymind-desktop/scratch/all_code.txt", "r", encoding="utf-8") as f:
    codebase = f.read()

with open("D:/pantrymind-desktop/scratch/doc_prompt.txt", "r", encoding="utf-8") as f:
    prompt = f.read()

chunks = [
    (2, "Generate ONLY Sections 7 through 11. Do not repeat previous sections. Start directly with ## 7. AI AGENTS"),
    (3, "Generate ONLY Sections 12 through 16. Do not repeat previous sections. Start directly with ## 12. KITCHEN AI CHEF")
]

for chunk_num, chunk_instruction in chunks:
    outfile = f"D:/pantrymind-desktop/docs/PROJECT_DOCS_{chunk_num}.md"
    print(f"Generating chunk {chunk_num}...")
    full_prompt = codebase + "\n\n" + prompt + "\n\nCRITICAL INSTRUCTION FOR THIS REQUEST: " + chunk_instruction
    
    # Retry loop in case of quota hit
    while True:
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
            
            with open(outfile, "w", encoding="utf-8") as out:
                out.write(text.strip() + "\n\n")
            
            print(f"Chunk {chunk_num} done. Wrote {len(text)} chars.")
            break
        except Exception as e:
            print(f"Failed on chunk {chunk_num}: {e}")
            print("Retrying in 65 seconds...")
            time.sleep(65)
    
    if chunk_num != chunks[-1][0]:
        print("Sleeping for 65 seconds before next chunk...")
        time.sleep(65)

print("Done generating chunks 2 and 3!")

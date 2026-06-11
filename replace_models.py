import os
import glob

replacements = [
    ("Gemini 2.5 Flash", "Gemini 3.1 Pro"),
    ("gemini-2.5-flash-lite", "gemini-3.1-pro"),
    ("gemini-2.5-flash", "gemini-3.1-pro"),
    ("gemini-2.5-pro", "gemini-3.1-pro"),
    ("gemini-live-2.5-flash-native-audio", "gemini-live-3.1-pro-native-audio"),
    ("gemini-2.0-flash-exp", "gemini-3.1-pro"),
    ("gemini-2.0-flash", "gemini-3.1-pro"),
    ("gemini-1.5-flash", "gemini-3.1-pro"),
    ("Gemini 1.5 Flash", "Gemini 3.1 Pro"),
    ("Gemini 2", "Gemini 3"),
    ("gemini-2", "gemini-3")
]

# Include python files in key directories, markdown files, and .env
files_to_process = glob.glob("*.md") + \
                   glob.glob("docs/*.md") + \
                   glob.glob(".env") + \
                   glob.glob("main.py") + \
                   glob.glob("adk/**/*.py", recursive=True) + \
                   glob.glob("agents/**/*.py", recursive=True) + \
                   glob.glob("services/**/*.py", recursive=True) + \
                   glob.glob("tools/**/*.py", recursive=True)

count = 0
for filepath in set(files_to_process):
    if not os.path.isfile(filepath): continue
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        
        new_content = content
        for old, new in replacements:
            new_content = new_content.replace(old, new)
            
        if new_content != content:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(new_content)
            count += 1
            print(f"Updated {filepath}")
    except Exception as e:
        print(f"Failed {filepath}: {e}")
        
print(f"Total files updated: {count}")

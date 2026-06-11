import os

EXTENSIONS = {'.py', '.jsx', '.js', '.json', '.env', '.md'}
EXCLUDE_DIRS = {'node_modules', '.venv', '.git', '__pycache__', 'build', 'dist', 'public', 'assets'}

def dump_code():
    with open('scratch/all_code.txt', 'w', encoding='utf-8') as outfile:
        for root, dirs, files in os.walk('.'):
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            for file in files:
                if any(file.endswith(ext) for ext in EXTENSIONS):
                    if file == 'package-lock.json': continue
                    filepath = os.path.join(root, file)
                    outfile.write(f"\n\n{'='*80}\n")
                    outfile.write(f"FILE: {filepath}\n")
                    outfile.write(f"{'='*80}\n")
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            outfile.write(f.read())
                    except Exception as e:
                        outfile.write(f"Error reading file: {e}\n")

if __name__ == '__main__':
    dump_code()
    print("Dumped all code to scratch/all_code.txt")

import os

exts = ['.py', '.js', '.jsx', '.json', '.env', '.env.example', '.md', '.txt']
ignores = ['.venv', 'node_modules', '.git', '__pycache__', 'dist', 'build', 'public', 'assets']
large_ignores = ['package-lock.json', 'stitch_table.html', 'export_submission_evidence.py', 'package.json']

out = []
for root, dirs, files in os.walk('D:/pantrymind-desktop'):
    dirs[:] = [d for d in dirs if d not in ignores]
    for file in files:
        if file in large_ignores: continue
        if any(file.endswith(ext) for ext in exts):
            path = os.path.join(root, file)
            size = os.path.getsize(path)
            if size > 100000: continue # skip files > 100KB
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                out.append(f'\n\n--- FILE: {path} ---\n{content}')
            except:
                pass

with open('D:/pantrymind-desktop/scratch/all_code.txt', 'w', encoding='utf-8') as f:
    f.write(''.join(out))

print(f"Wrote {len(out)} files to scratch/all_code.txt")
print(f"Total size: {os.path.getsize('D:/pantrymind-desktop/scratch/all_code.txt') / 1024:.2f} KB")

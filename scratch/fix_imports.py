import os
import re

TARGET_DIR = r"c:\Users\Raj shekhar\Documents\raj\project\main\n3mo-saas"

MODULE_MAP = {
    'database': 'core.database',
    'run_indexer': 'core.run_indexer',
    'core_engine': 'core.core_engine',
    'symbol_extractor': 'core.symbol_extractor',
    'crawler': 'core.crawler',
    'git_hooks': 'core.git_hooks',
    'graph_visualizer': 'core.graph_visualizer',
    'resolve_calls': 'core.resolve_calls',
    'resolve_imports': 'core.resolve_imports',
    'mcp_server': 'mcp.mcp_server',
    'cli': 'cli.cli'
}

def fix_imports_in_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    new_content = content
    for old_mod, new_mod in MODULE_MAP.items():
        pattern1 = r'from n3mo\.' + old_mod + r'\b'
        repl1 = r'from n3mo.' + new_mod
        new_content = re.sub(pattern1, repl1, new_content)
        
        pattern2 = r'import n3mo\.' + old_mod + r'\b'
        repl2 = r'import n3mo.' + new_mod
        new_content = re.sub(pattern2, repl2, new_content)

    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Fixed: {filepath}")

for root, dirs, files in os.walk(TARGET_DIR):
    if '.git' in root or '__pycache__' in root or 'node_modules' in root:
        continue
    for file in files:
        if file.endswith('.py'):
            fix_imports_in_file(os.path.join(root, file))

print("Done.")

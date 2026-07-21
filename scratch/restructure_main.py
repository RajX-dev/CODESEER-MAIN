import os
import shutil
import glob
import re

print('Starting restructuring on main branch...')

dirs = [
    'n3mo/core',
    'n3mo/cli',
    'n3mo/mcp',
    'n3mo/common',
    'scripts'
]
for d in dirs:
    os.makedirs(d, exist_ok=True)
    init_path = os.path.join(d, '__init__.py')
    if not os.path.exists(init_path):
        with open(init_path, 'w') as f:
            f.write('')

file_map = {
    'n3mo/crawler.py': 'n3mo/core/crawler.py',
    'n3mo/database.py': 'n3mo/core/database.py',
    'n3mo/resolve_calls.py': 'n3mo/core/resolve_calls.py',
    'n3mo/resolve_imports.py': 'n3mo/core/resolve_imports.py',
    'n3mo/run_indexer.py': 'n3mo/core/run_indexer.py',
    'n3mo/symbol_extractor.py': 'n3mo/core/symbol_extractor.py',
    'n3mo/core_engine.py': 'n3mo/core/core_engine.py',
    'n3mo/cli.py': 'n3mo/cli/cli.py',
    'n3mo/graph_visualizer.py': 'n3mo/cli/graph_visualizer.py',
    'n3mo/mcp_server.py': 'n3mo/mcp/mcp_server.py',
    'n3mo/license_validator.py': 'n3mo/common/license_validator.py',
    'n3mo/git_hooks.py': 'n3mo/common/git_hooks.py',
    'bump.py': 'scripts/bump.py'
}

for src, dst in file_map.items():
    if os.path.exists(src):
        shutil.move(src, dst)
        print(f'Moved {src} -> {dst}')
    else:
        print(f'Skipped {src} (not found on main branch)')

import_replacements = {
    r'from\s+n3mo\.(crawler|database|resolve_calls|resolve_imports|run_indexer|symbol_extractor|core_engine)': r'from n3mo.core.\1',
    r'from\s+n3mo\.(cli|graph_visualizer)': r'from n3mo.cli.\1',
    r'from\s+n3mo\.(mcp_server)': r'from n3mo.mcp.\1',
    r'from\s+n3mo\.(license_validator|git_hooks)': r'from n3mo.common.\1',
    r'import\s+n3mo\.(crawler|database|resolve_calls|resolve_imports|run_indexer|symbol_extractor|core_engine)': r'import n3mo.core.\1',
    r'import\s+n3mo\.(cli|graph_visualizer)': r'import n3mo.cli.\1',
    r'import\s+n3mo\.(mcp_server)': r'import n3mo.mcp.\1',
    r'import\s+n3mo\.(license_validator|git_hooks)': r'import n3mo.common.\1',
}

all_py_files = glob.glob('**/*.py', recursive=True)
all_py_files = [f for f in all_py_files if not f.startswith('.') and 'venv' not in f]
if 'restructure_main.py' in all_py_files:
    all_py_files.remove('restructure_main.py')

for py_file in all_py_files:
    with open(py_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    new_content = content
    for pattern, replacement in import_replacements.items():
        new_content = re.sub(pattern, replacement, new_content)
    
    if new_content != content:
        with open(py_file, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f'Updated imports in {py_file}')

with open('setup.py', 'r', encoding='utf-8') as f:
    setup_content = f.read()

setup_content = setup_content.replace("'n3mo=n3mo.cli:main'", "'n3mo=n3mo.cli.cli:main'")
with open('setup.py', 'w', encoding='utf-8') as f:
    f.write(setup_content)
print('Updated setup.py')
print('Restructure on main complete.')

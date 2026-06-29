import os
import re

files = ['n3mo/graph_visualizer.py', 'public/index.html', 'server.json', 'setup.py']
for file in files:
    try:
        if os.path.exists(file):
            with open(file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            content = re.sub(r'version=".*?"', 'version="2.0.0"', content)
            content = re.sub(r'"version": ".*?"', '"version": "2.0.0"', content)
            content = re.sub(r'Release v.*? is Live', 'Release v2.0.0 is Live', content)
            content = re.sub(r'<div class="version">v.*?</div>', '<div class="version">v2.0.0</div>', content)
            
            with open(file, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Bumped version in {file}")
    except Exception as e:
        print(f"Error processing {file}: {e}")

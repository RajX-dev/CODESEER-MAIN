
files = ['impact_graph.html', 'n3mo/graph_visualizer.py', 'public/index.html', 'server.json', 'setup.py']
for file in files:
    try:
        with open(file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        content = content.replace('2.0.0', '2.0.1')
        
        with open(file, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Bumped version in {file}")
    except Exception as e:
        print(f"Error processing {file}: {e}")

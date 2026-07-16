
files_to_fix = [
    "saas_webhook_handler.py",
    "n3mo/worker.py",
    "n3mo/saas_db.py",
    "n3mo/api_server.py"
]

for filepath in files_to_fix:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    content = content.replace("'free'", "'none'")
    content = content.replace('"free"', '"none"')
    
    if filepath == "n3mo/api_server.py":
        content = content.replace('"FREE_UPGRADE"', '""')
        
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Removed free plan from {filepath}")

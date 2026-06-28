import re

with open('n3mo/core_engine.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Remove the unused import
content = re.sub(r'from n3mo\.run_indexer import run_indexer_for_path\n', '', content)

# 2. Remove fastapi import if it exists
content = re.sub(r'from fastapi import HTTPException\n', '', content)

# 3. Replace HTTPException in post_github_comment
content = content.replace('raise HTTPException(status_code=e.code, detail=f\'GitHub API Error: {err_msg}\')', 'raise Exception(f\'GitHub API Error: {err_msg}\')')

# 4. Add get_github_app_installation_token
func_code = '''
def get_github_app_installation_token(app_id, private_key_env, private_key_path, installation_id):
    if not app_id:
        raise Exception("Missing GITHUB_APP_ID")
        
    try:
        import jwt
        import time
    except ImportError:
        logger.error("jwt package not found.")
        raise Exception("PyJWT required for GitHub App auth")
        
    private_key = private_key_env
    if not private_key and private_key_path:
        if os.path.exists(private_key_path):
            with open(private_key_path, "r") as f:
                private_key = f.read()
                
    if not private_key:
        raise Exception("GitHub App private key is empty or not found")
        
    private_key = private_key.replace("\\\\n", "\\n")
    
    now = int(time.time())
    payload = {
        "iat": now - 60,
        "exp": now + 600,
        "iss": str(app_id)
    }
    
    token_jwt = jwt.encode(payload, private_key, algorithm="RS256")
    
    if not installation_id:
        raise Exception("Missing installation ID")
        
    url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token_jwt}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "N3MO-Impact-Tracker"
        },
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req) as resp:
            import json
            data = json.loads(resp.read().decode())
            return data.get("token")
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode()
        logger.error(f"Failed to get App installation token: {e.code} - {err_msg}")
        raise Exception(f"GitHub App Token Error: {err_msg}")
'''

content += '\n\n' + func_code

with open('n3mo/core_engine.py', 'w', encoding='utf-8') as f:
    f.write(content)

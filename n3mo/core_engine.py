# Copyright (C) 2026 Raj shekhar
#
# This file is part of N3MO.
# N3MO is licensed under the PolyForm Noncommercial License 1.0.0.
# You may obtain a copy of the License at
# https://polyformproject.org/licenses/noncommercial/1.0.0

import os
import logging
import subprocess
import urllib.request
import urllib.error
import json

from n3mo.crawler import crawl_directory
from n3mo.database import get_connection, release_connection

logger = logging.getLogger("n3mo.core_engine")



def get_workspace_dir(repo_name: str) -> str:
    workspace_root = os.getenv('N3MO_WORKSPACE_DIR', os.path.join(os.getcwd(), 'n3mo_workspaces'))
    return os.path.abspath(os.path.join(workspace_root, repo_name.replace('/', '_')))



def calculate_repo_loc(repo_dir: str) -> int:
    files = crawl_directory(repo_dir)
    total_lines = 0
    for fpath in files:
        if (not os.path.exists(fpath)):
            continue
        try:
            with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                total_lines += sum((1 for _ in f))
        except Exception:
            pass
    return total_lines



def checkout_repo(clone_url: str, repo_name: str, sha: str) -> str:
    repo_dir = get_workspace_dir(repo_name)
    os.makedirs(os.path.dirname(repo_dir), exist_ok=True)
    if (not os.path.exists(repo_dir)):
        logger.info(f'Cloning {clone_url} to {repo_dir}...')
        subprocess.run(['git', 'clone', clone_url, repo_dir], check=True)
    else:
        logger.info(f'Fetching updates for {repo_name}...')
        subprocess.run(['git', 'fetch', 'origin'], cwd=repo_dir, check=True)
    logger.info(f'Checking out {sha}...')
    subprocess.run(['git', 'checkout', '-f', sha], cwd=repo_dir, check=True)
    return repo_dir



def get_changed_files(repo_dir: str, base_sha: str, head_sha: str) -> list:
    res = subprocess.run(['git', 'diff', '--name-only', base_sha, head_sha], cwd=repo_dir, capture_output=True, text=True, check=True)
    return [line.strip() for line in res.stdout.splitlines() if line.strip()]



def get_project_id(repo_dir: str):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT id FROM projects WHERE repo_url = %s', (repo_dir,))
            row = cur.fetchone()
            return (row[0] if row else None)
    finally:
        release_connection(conn)



def get_impact_for_changed_files(project_id, changed_files: list) -> dict:
    if ((not project_id) or (not changed_files)):
        return {}
    conn = get_connection()
    impacts = {}
    try:
        with conn.cursor() as cur:
            cur.execute('\n                SELECT id, name, file_path, start_line\n                FROM symbols\n                WHERE project_id = %s AND file_path = ANY(%s)\n                ', (project_id, changed_files))
            symbols = cur.fetchall()
            for (sym_id, name, file_path, start_line) in symbols:
                query = '\n                WITH RECURSIVE impact_chain AS (\n                    SELECT s.name AS source, s.file_path, c.line_number, 1 AS depth, target_sym.name AS target, c.source_symbol_id AS source_id,\n                           ARRAY[c.source_symbol_id] AS path,\n                           FALSE AS cycle\n                    FROM calls c\n                    JOIN symbols s ON c.source_symbol_id = s.id\n                    JOIN symbols target_sym ON c.resolved_symbol_id = target_sym.id\n                    WHERE c.resolved_symbol_id = %s\n                    UNION ALL\n                    SELECT s.name, s.file_path, c.line_number, ic.depth + 1, ic.source, c.source_symbol_id,\n                           ic.path || c.source_symbol_id,\n                           c.source_symbol_id = ANY(ic.path)\n                    FROM impact_chain ic\n                    JOIN calls c ON c.resolved_symbol_id = ic.source_id\n                    JOIN symbols s ON c.source_symbol_id = s.id\n                    WHERE ic.depth < 4 AND NOT ic.cycle\n                )\n                SELECT DISTINCT source, file_path, line_number, depth, target\n                FROM impact_chain WHERE NOT cycle ORDER BY depth ASC, file_path;\n                '
                cur.execute(query, (sym_id,))
                callers = cur.fetchall()
                impacts[name] = {'file_path': file_path, 'line': start_line, 'callers': [{'source': c[0], 'file_path': c[1], 'line': c[2], 'depth': c[3]} for c in callers]}
    finally:
        release_connection(conn)
    return impacts



def merge_impacts(base_impacts: dict, head_impacts: dict) -> dict:
    merged = {}
    all_symbols = (set(base_impacts.keys()) | set(head_impacts.keys()))
    for sym in all_symbols:
        in_base = (sym in base_impacts)
        in_head = (sym in head_impacts)
        if (in_base and in_head):
            status = 'Modified'
            data = head_impacts[sym]
        elif in_head:
            status = 'Added'
            data = head_impacts[sym]
        else:
            status = 'Deleted'
            data = base_impacts[sym]
        merged[sym] = {'status': status, 'file_path': data['file_path'], 'line': data['line'], 'callers': data['callers']}
    return merged



def format_impact_markdown(merged_impacts: dict, repo_name: str, pr_number: int, total_lines: int) -> str:
    if (not merged_impacts):
        return '### ◈ N3MO Pull Request Impact Analysis\n\n✅ **No impact detected.** No active symbols were modified or affected in this PR.'

    # Separate symbols into impactful (have callers) and safe (zero callers)
    impactful_symbols = []
    safe_symbols = []
    for (name, data) in sorted(merged_impacts.items(), key=(lambda x: (x[1]['status'], x[0]))):
        callers = data['callers']
        direct_count = len([c for c in callers if (c['depth'] == 1)])
        total_count = len(callers)
        if total_count > 0:
            impactful_symbols.append((name, data, direct_count, total_count))
        else:
            safe_symbols.append((name, data))

    markdown = '### ◈ N3MO Pull Request Impact Analysis\n\n'
    markdown += f'Analyzed **{total_lines:,}** lines of code. Blast radius for PR #{pr_number}.\n\n'

    # If nothing is impactful, keep it very short
    if not impactful_symbols:
        markdown += f'✅ All **{len(safe_symbols)}** modified symbols have **0 callers** — safe to merge.\n'
        return markdown

    # Summary table — only symbols with callers
    markdown += '| File | Symbol | Status | Direct Callers | Total Impacted |\n'
    markdown += '| :--- | :--- | :--- | :---: | :---: |\n'
    for (name, data, direct_count, total_count) in impactful_symbols:
        status = data['status']
        file_path = data['file_path']
        status_badge = _format_status_badge(status)
        markdown += f'| `{file_path}` | `{name}` | {status_badge} | {direct_count} | {total_count} |\n'

    # One-liner for safe symbols
    if safe_symbols:
        safe_count = len(safe_symbols)
        markdown += f'\n✅ {safe_count} other symbol{"s" if safe_count != 1 else ""} modified with **0 callers** (safe to change).\n'

    # Collapsible details — only for impactful symbols
    markdown += '\n<details>\n<summary><b>🔍 View Impact Details</b></summary>\n\n'
    for (name, data, direct_count, total_count) in impactful_symbols:
        status = data['status']
        file_path = data['file_path']
        line = data['line']
        callers = data['callers']
        markdown += f'#### ◉ `{name}` ({status})\n'
        markdown += f'*   **Location:** `{file_path}:{line}`\n'
        direct_callers = [c for c in callers if (c['depth'] == 1)]
        ripple_callers = [c for c in callers if (c['depth'] > 1)]
        if direct_callers:
            markdown += '*   **Direct Callers:**\n'
            for c in direct_callers:
                markdown += f'    *   `{c["source"]}` (`{c["file_path"]}:{c["line"]}`)\n'
        if ripple_callers:
            markdown += f'\n<details>\n<summary>View {len(ripple_callers)} Ripple Effects</summary>\n\n'
            for c in sorted(ripple_callers, key=(lambda x: x['depth'])):
                indent = ('  ' * (c['depth'] - 1))
                markdown += f'{indent}* ─▸ `{c["source"]}` (`{c["file_path"]}:{c["line"]}`)\n'
            markdown += '\n</details>\n\n'
    markdown += '</details>\n'
    return markdown


def _format_status_badge(status: str) -> str:
    """Return a compact status badge string for the markdown table."""
    if (status == 'Modified'):
        return '🟠 Modified'
    elif (status == 'Added'):
        return '🟢 Added'
    elif (status == 'Deleted'):
        return '🔴 Deleted'
    return status



def post_github_comment(repo_name: str, pr_number: int, body_markdown: str, installation_id: ((str | int) | None)=None) -> dict:
    token = (os.getenv('GITHUB_TOKEN') or os.getenv('GITHUB_PAT'))
    app_id = os.getenv('GITHUB_APP_ID')
    private_key_env = os.getenv('GITHUB_APP_PRIVATE_KEY')
    private_key_path = (os.getenv('GITHUB_APP_PRIVATE_KEY_PATH') or os.getenv('GITHUB_PRIVATE_KEY_PATH'))
    if ((not token) and app_id and (private_key_env or private_key_path) and installation_id):
        logger.info('Authenticating as GitHub App...')
        token = get_github_app_installation_token(app_id, private_key_env, private_key_path, installation_id)
    if (not token):
        logger.warning('⚠️ No GITHUB_TOKEN or GITHUB_APP credentials found. Printing report to stdout.')
        print('\n--- REPORT COMMENT ---\n')
        print(body_markdown)
        print('\n----------------------\n')
        return {'status': 'printed_locally', 'reason': 'no_credentials'}
    url = f'https://api.github.com/repos/{repo_name}/issues/{pr_number}/comments'
    req = urllib.request.Request(url, data=json.dumps({'body': body_markdown}).encode('utf-8'), headers={'Authorization': f'token {token}', 'Accept': 'application/vnd.github.v3+json', 'Content-Type': 'application/json', 'User-Agent': 'N3MO-Impact-Tracker'}, method='POST')
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            logger.info(f'Successfully posted comment to PR #{pr_number}')
            return {'status': 'posted', 'comment_id': data.get('id')}
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode()
        logger.error(f'Failed to post comment: {e.code} - {err_msg}')
        raise Exception(f'GitHub API Error: {err_msg}')




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
        
    private_key = private_key.replace("\\n", "\n")
    
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

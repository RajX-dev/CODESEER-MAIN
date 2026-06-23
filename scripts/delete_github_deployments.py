import urllib.request
import urllib.error
import json
import sys

def delete_deployments(repo: str, token: str):
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"token {token}",
        "X-GitHub-Api-Version": "2022-11-28"
    }

    url = f"https://api.github.com/repos/{repo}/deployments?per_page=100"
    
    print(f"Fetching deployments for {repo}...")
    req = urllib.request.Request(url, headers=headers)
    
    try:
        with urllib.request.urlopen(req) as response:
            deployments = json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        print(f"Failed to fetch deployments: {e.code} {e.reason}")
        sys.exit(1)

    if not deployments:
        print("No deployments found.")
        return

    print(f"Found {len(deployments)} deployments. Starting deletion...")

    for dep in deployments:
        dep_id = dep["id"]
        # To delete a deployment, we need to set its status to 'inactive' first
        status_url = f"https://api.github.com/repos/{repo}/deployments/{dep_id}/statuses"
        data = json.dumps({"state": "inactive"}).encode("utf-8")
        status_req = urllib.request.Request(status_url, data=data, headers=headers, method="POST")
        try:
            urllib.request.urlopen(status_req)
        except urllib.error.HTTPError:
            pass # It might already be inactive
        
        # Now delete the deployment
        del_url = f"https://api.github.com/repos/{repo}/deployments/{dep_id}"
        del_req = urllib.request.Request(del_url, headers=headers, method="DELETE")
        try:
            urllib.request.urlopen(del_req)
            print(f"✅ Deleted deployment ID: {dep_id}")
        except urllib.error.HTTPError as e:
            print(f"❌ Failed to delete {dep_id}: {e.code} {e.reason}")

if __name__ == "__main__":
    print("GitHub Deployment Cleaner")
    repo = input("Enter repository (e.g., RajX-dev/N3MO or RajX-dev/N3MO-SaaS): ").strip()
    token = input("Enter your GitHub Personal Access Token (needs 'repo' scope): ").strip()
    if repo and token:
        delete_deployments(repo, token)
    else:
        print("Repository and token are required.")


with open('public/dashboard.js', 'r') as f:
    content = f.read()

replacement = """        githubIdEl.textContent = `GitHub ID: ${data.user.github_id}`;
        
        if (data.user.is_admin) {
            const adminLink = document.getElementById('admin-link');
            if (adminLink) adminLink.style.display = 'flex';
        }
        
        const planType = data.subscription?.plan_type || 'free';"""

content = content.replace("        githubIdEl.textContent = `GitHub ID: ${data.user.github_id}`;\n        const planType = data.subscription?.plan_type || 'free';", replacement)

with open('public/dashboard.js', 'w') as f:
    f.write(content)
print("patched")

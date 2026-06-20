document.addEventListener('DOMContentLoaded', async () => {
    const loadingState = document.getElementById('loading');
    const dashboardContent = document.getElementById('dashboard-content');
    
    // UI Elements
    const avatarEl = document.getElementById('user-avatar');
    const nameEl = document.getElementById('user-name');
    const githubIdEl = document.getElementById('user-github-id');
    const planBadge = document.getElementById('plan-badge');
    const planStatus = document.getElementById('plan-status');
    
    // Views
    const viewFree = document.getElementById('view-free');
    const viewPro = document.getElementById('view-pro');
    
    // Buttons & Inputs
    const upgradeBtn = document.getElementById('upgrade-btn');
    const logoutBtn = document.getElementById('logout-btn');
    const secretInput = document.getElementById('webhook-secret-input');
    const copyBtn = document.getElementById('copy-secret-btn');
    const toggleBtn = document.getElementById('toggle-secret-btn');

    let userData = null;

    // Fetch Dashboard Data
    try {
        const response = await fetch('/api/user/dashboard-data');
        if (!response.ok) {
            // Not logged in or error, redirect to home
            window.location.href = '/';
            return;
        }
        
        const data = await response.json();
        userData = data;
        
        // Populate Profile
        avatarEl.src = data.user.avatar_url || `https://avatars.githubusercontent.com/u/${data.user.github_id}?v=4`;
        nameEl.textContent = data.user.username;
        githubIdEl.textContent = `GitHub ID: ${data.user.github_id}`;
        
        // Populate Plan
        const planType = data.subscription?.plan_type || 'free';
        const isProOrEnt = planType === 'pro' || planType === 'enterprise';
        
        planBadge.textContent = planType.toUpperCase();
        
        if (isProOrEnt) {
            planBadge.className = "px-3 py-1 text-xs font-bold uppercase tracking-wider rounded-full bg-purple-500/20 text-purple-400 border border-purple-500/30";
            planStatus.classList.remove('hidden');
            
            viewPro.classList.remove('hidden');
            secretInput.value = data.webhook_secret;
        } else {
            viewFree.classList.remove('hidden');
        }

        // Show dashboard
        loadingState.classList.add('hidden');
        dashboardContent.classList.remove('hidden');

    } catch (err) {
        console.error("Failed to load dashboard data:", err);
        window.location.href = '/';
    }

    // Upgrade Button flow
    upgradeBtn.addEventListener('click', async () => {
        if (!userData || !userData.user.github_id) return;
        
        upgradeBtn.innerHTML = `Loading...`;
        upgradeBtn.disabled = true;
        
        try {
            const res = await fetch(`/api/create-checkout?github_id=${userData.user.github_id}`, { method: 'POST' });
            const data = await res.json();
            if (data.checkout_url) {
                window.location.href = data.checkout_url;
            } else {
                alert("Checkout failed. Please try again.");
                upgradeBtn.innerHTML = `Upgrade Now - $30/mo`;
                upgradeBtn.disabled = false;
            }
        } catch (e) {
            console.error(e);
            alert("Checkout failed. Please try again.");
            upgradeBtn.innerHTML = `Upgrade Now - $30/mo`;
            upgradeBtn.disabled = false;
        }
    });

    // Logout
    logoutBtn.addEventListener('click', async () => {
        await fetch('/api/auth/logout', { method: 'POST' });
        window.location.href = '/';
    });

    // Webhook Secret copy/toggle
    copyBtn.addEventListener('click', () => {
        secretInput.type = 'text';
        secretInput.select();
        document.execCommand('copy');
        secretInput.type = 'password';
        
        const originalText = copyBtn.innerText;
        copyBtn.innerText = 'Copied!';
        setTimeout(() => {
            copyBtn.innerText = originalText;
        }, 2000);
    });

    toggleBtn.addEventListener('click', () => {
        if (secretInput.type === 'password') {
            secretInput.type = 'text';
        } else {
            secretInput.type = 'password';
        }
    });
});

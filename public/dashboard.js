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
            if (response.status === 401) {
                window.location.href = '/api/auth/login';
            } else {
                document.getElementById('loading').innerHTML = `<p class="text-red-500">Error loading dashboard: ${response.statusText}</p>`;
            }
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
        let isExpired = false;
        
        // Show subscription details
        const subDetails = document.getElementById('sub-details');
        const subStart = document.getElementById('sub-start-date');
        const subExpires = document.getElementById('sub-expires-in');

        if (isProOrEnt) {
            subDetails.style.display = 'block';
            
            if (data.subscription && data.subscription.created_at) {
                const startD = new Date(data.subscription.created_at);
                subStart.textContent = startD.toLocaleDateString();
            } else {
                subStart.textContent = "N/A";
            }
            
            if (data.subscription && data.subscription.expires_at) {
                const expD = new Date(data.subscription.expires_at);
                const now = new Date();
                const diffTime = expD - now;
                if (diffTime > 0) {
                    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
                    subExpires.textContent = `${diffDays} days`;
                } else {
                    subExpires.textContent = "Expired";
                    subExpires.style.color = "#ef4444";
                    isExpired = true;
                }
            } else {
                subExpires.textContent = "Lifetime / Active";
            }
        }
        
        planBadge.textContent = planType.toUpperCase();
        
        if (isProOrEnt && !isExpired) {
            planBadge.className = "plan-badge pro";
            
            viewPro.style.display = 'block';
            secretInput.value = data.webhook_secret;
            
            // Dynamically update the webhook URL in the HTML
            const payloadUrlEl = document.getElementById('webhook-payload-url');
            if (payloadUrlEl) {
                payloadUrlEl.textContent = `${window.location.origin}/github/webhook`;
            }
        } else {
            if (isExpired) {
                planBadge.textContent = "EXPIRED";
                planBadge.style.backgroundColor = "rgba(239, 68, 68, 0.2)";
                planBadge.style.color = "#ef4444";
                planBadge.style.border = "1px solid rgba(239, 68, 68, 0.5)";
            }
            viewFree.style.display = 'block';
        }

        // Show dashboard
        loadingState.style.display = 'none';
        dashboardContent.style.display = 'block';

    } catch (err) {
        console.error("Failed to load dashboard data:", err);
        document.getElementById('loading').innerHTML = `<p class="text-red-500">Network or server error. Please try again later.</p>`;
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
                upgradeBtn.innerHTML = `Upgrade Now - $25/mo`;
                upgradeBtn.disabled = false;
            }
        } catch (e) {
            console.error(e);
            alert("Checkout failed. Please try again.");
            upgradeBtn.innerHTML = `Upgrade Now - $25/mo`;
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

// Mouse Tracker
const cursorGlow = document.querySelector('.cursor-glow');
const curDot = document.querySelector('.cur-dot');

if (cursorGlow || curDot) {
    let mouseX = window.innerWidth / 2;
    let mouseY = window.innerHeight / 2;
    let currentX = window.innerWidth / 2;
    let currentY = window.innerHeight / 2;

    document.addEventListener('mousemove', (e) => {
        if (cursorGlow) cursorGlow.style.opacity = '1';
        mouseX = e.clientX;
        mouseY = e.clientY;
    });
    
    document.addEventListener('mouseleave', () => {
        if (cursorGlow) cursorGlow.style.opacity = '0';
        if (curDot) curDot.style.opacity = '0';
    });

    document.addEventListener('mouseenter', () => {
        if (curDot) curDot.style.opacity = '1';
    });



    const interactives = document.querySelectorAll('a, button, .bento-card, input');
    interactives.forEach(el => {
        const isCardOrInput = el.classList.contains('bento-card') || el.tagName.toLowerCase() === 'input';
        
        el.addEventListener('mouseenter', () => {
            if (cursorGlow) cursorGlow.classList.add('glow-active');
            if (curDot && !isCardOrInput) curDot.classList.add('big');
        });
        el.addEventListener('mouseleave', () => {
            if (cursorGlow) cursorGlow.classList.remove('glow-active');
            if (curDot) curDot.classList.remove('big');
        });
        if (el.classList.contains('bento-card')) {
            el.addEventListener('mousemove', (e) => {
                const rect = el.getBoundingClientRect();
                el.style.setProperty('--card-x', `${e.clientX - rect.left}px`);
                el.style.setProperty('--card-y', `${e.clientY - rect.top}px`);
            });
        }
    });

    function animateGlow() {
        if (curDot) {
            curDot.style.transform = `translate(-50%, -50%) translate3d(${mouseX}px, ${mouseY}px, 0)`;
        }
        if (cursorGlow) {
            // LERP for ultra-fluid trailing
            currentX += (mouseX - currentX) * 0.1;
            currentY += (mouseY - currentY) * 0.1;
            
            cursorGlow.style.setProperty('--mouse-x', currentX);
            cursorGlow.style.setProperty('--mouse-y', currentY);
        }
        requestAnimationFrame(animateGlow);
    }
    
    animateGlow();
}

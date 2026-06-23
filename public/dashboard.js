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
        planBadge.textContent = 'CLI ONLY';
        
        // Show a message that the dashboard is for SaaS
        const actionArea = document.querySelector('.action-area');
        if (actionArea) {
            const msg = document.createElement('div');
            msg.className = 'bento-card';
            msg.innerHTML = `
                <h3 style="color: var(--accent); font-family: var(--font-heading); margin-bottom: 12px;">Community Edition</h3>
                <p style="color: var(--text-secondary); line-height: 1.6;">
                    You are running N3MO locally. You have full, unlimited access to the <strong>N3MO CLI</strong> to analyze codebases on your machine.
                    <br><br>
                    <em>Note: Automated GitHub Pull Request Webhooks are a SaaS-exclusive feature. Deploy N3MO to the cloud to enable it!</em>
                </p>
            `;
            actionArea.appendChild(msg);
        }

        // Show dashboard
        loadingState.style.display = 'none';
        dashboardContent.style.display = 'block';

    } catch (err) {
        console.error("Failed to load dashboard data:", err);
        document.getElementById('loading').innerHTML = `<p class="text-red-500">Network or server error. Please try again later.</p>`;
    }

    // Logout
    logoutBtn.addEventListener('click', async () => {
        await fetch('/api/auth/logout', { method: 'POST' });
        window.location.href = '/';
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

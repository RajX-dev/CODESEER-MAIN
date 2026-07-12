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
    const viewTeam = document.getElementById('view-team');
    
    // Buttons & Inputs
    const upgradeBtns = document.querySelectorAll('.upgrade-btn');
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
        avatarEl.src = `https://github.com/${data.user.username}.png`;
        nameEl.textContent = data.user.username;
        githubIdEl.textContent = `GitHub ID: ${data.user.github_id}`;
        
        // Populate Plan
        const planType = data.subscription?.plan_type || 'free';
        const isProOrEnt = planType === 'pro' || planType === 'enterprise';
        let isExpired = false;
        let isTrial = false;
        
        // Show subscription details
        const subDetails = document.getElementById('sub-details');
        const subStart = document.getElementById('sub-start-date');
        const subExpires = document.getElementById('sub-expires-in');

        if (isProOrEnt) {
            subDetails.style.display = 'block';
            let startD, expD;
            
            if (data.subscription && data.subscription.created_at) {
                startD = new Date(data.subscription.created_at);
                subStart.textContent = startD.toLocaleDateString();
            } else {
                subStart.textContent = "N/A";
            }
            
            if (data.subscription && data.subscription.expires_at) {
                expD = new Date(data.subscription.expires_at);
                const now = new Date();
                const diffTime = expD - now;
                if (diffTime > 0) {
                    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
                    subExpires.textContent = `${diffDays} days`;
                } else {
                    subExpires.textContent = "Expired";
                    subExpires.style.color = "#ef4444";
                    isExpired = true;
                    // Check if it was a trial (lasted less than 30 days total)
                    if (startD && (expD - startD) < (30 * 24 * 60 * 60 * 1000)) {
                        isTrial = true;
                    }
                }
            } else {
                subExpires.textContent = "Lifetime / Active";
            }
        }
        
        planBadge.textContent = planType === 'free' ? 'UNLICENSED' : planType.toUpperCase();
        
        // Show webhook section only for active paid plans
        const webhookSection = document.getElementById('webhook-section');
        if (webhookSection) {
            webhookSection.style.display = (planType !== 'free' && !isExpired) ? 'block' : 'none';
        }
        
        secretInput.value = data.webhook_secret;
        
        // Dynamically update the webhook URL in the HTML
        const payloadUrlEl = document.getElementById('webhook-payload-url');
        if (payloadUrlEl) {
            payloadUrlEl.textContent = `${window.location.origin}/github/webhook`;
        }
        
        if (!isExpired && (isProOrEnt || planType === 'team')) {
            planBadge.className = "plan-badge pro";
            if (planType === 'team') {
                viewTeam.style.display = 'block';
                planBadge.style.backgroundColor = 'var(--accent-purple)';
                planBadge.style.borderColor = 'var(--accent-purple)';
            } else if (planType === 'enterprise') {
                viewPro.style.display = 'block';
                const titleEl = document.getElementById('paid-plan-title');
                const descEl = document.getElementById('paid-plan-desc');
                const upgradeSec = document.getElementById('pro-upgrade-section');
                if (titleEl) titleEl.textContent = 'Enterprise Subscription Active';
                if (descEl) descEl.innerHTML = 'Thank you for supporting N3MO! You can now analyze repositories with <strong>unlimited lines of code</strong>.';
                if (upgradeSec) upgradeSec.style.display = 'none';
            } else {
                viewPro.style.display = 'block';
            }
        } else {
            if (isExpired) {
                planBadge.textContent = isTrial ? "TRIAL ENDED" : "EXPIRED";
                planBadge.style.backgroundColor = "rgba(239, 68, 68, 0.2)";
                planBadge.style.color = "#ef4444";
                planBadge.style.border = "1px solid rgba(239, 68, 68, 0.5)";
            }
            viewFree.style.display = 'block';
        }

        // Fetch config to check if SaaS mode is active
        try {
            const configRes = await fetch('/api/config');
            if (configRes.ok) {
                const configData = await configRes.json();
                if (!configData.saas_mode) {
                    // Hide pricing and subscription views for local/free mode
                    viewFree.style.display = 'none';
                    viewPro.style.display = 'none';
                    planBadge.textContent = 'CLI ONLY';
                    
                    const webhookSection = document.getElementById('webhook-section');
                    if (webhookSection) webhookSection.style.display = 'none';
                    
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
                }
            }
        } catch (e) {
            console.warn("Could not fetch config", e);
        }

        // Show dashboard
        loadingState.style.display = 'none';
        dashboardContent.style.display = 'block';

        // Auto-checkout if triggered from landing page
        const urlParams = new URLSearchParams(window.location.search);
        const requestedPlan = urlParams.get('plan');
        if (requestedPlan) {
            const targetBtn = document.querySelector(`.upgrade-btn[data-plan="${requestedPlan}"]`);
            if (targetBtn && targetBtn.offsetParent !== null) {
                // Remove the parameter so it doesn't loop on refresh
                window.history.replaceState({}, document.title, window.location.pathname);
                targetBtn.click();
            }
        }

    } catch (err) {
        console.error("Failed to load dashboard data:", err);
        document.getElementById('loading').innerHTML = `<p class="text-red-500">Network or server error. Please try again later.</p>`;
    }

    // Upgrade Button flow
    upgradeBtns.forEach(btn => {
        btn.addEventListener('click', async (e) => {
            if (!userData || !userData.user.github_id) return;
            
            const targetBtn = e.target;
            const targetPlan = targetBtn.getAttribute('data-plan') || 'pro';
            const originalText = targetBtn.innerHTML;
            
            targetBtn.innerHTML = `Loading...`;
            targetBtn.disabled = true;
            
            try {
                let country = "US";
                try {
                    const geoRes = await fetch("https://ipapi.co/json/");
                    if (geoRes.ok) {
                        const geoData = await geoRes.json();
                        if (geoData && geoData.country_code) {
                            country = geoData.country_code;
                        }
                    }
                } catch (e) {
                    console.warn("Could not fetch location, defaulting to US");
                }

                const discountCode = document.getElementById('discount-code').value.trim();
                // Call the new subscription API. By default passing billing_cycle=monthly, they can add a toggle later.
                const res = await fetch(`/api/create-subscription?github_id=${userData.user.github_id}&country=${country}&discount=${discountCode}&plan_type=${targetPlan}&billing_cycle=monthly`, { method: 'POST' });
                if (!res.ok) throw new Error("Failed to create subscription");
                
                const data = await res.json();
                if (data.free_upgrade) {
                    alert(`100% Discount applied! Upgraded to ${targetPlan.toUpperCase()} successfully.`);
                    window.location.reload();
                    return;
                }
                if (data.subscription_id) {
                    const options = {
                        "key": data.key_id,
                        "name": "N3MO",
                        "description": `${targetPlan.toUpperCase()} Subscription`,
                        "subscription_id": data.subscription_id,
                        "handler": async function (response) {
                            try {
                                const verifyRes = await fetch('/api/verify-payment', {
                                    method: 'POST',
                                    headers: { 'Content-Type': 'application/json' },
                                    body: JSON.stringify({
                                        razorpay_payment_id: response.razorpay_payment_id,
                                        razorpay_subscription_id: response.razorpay_subscription_id,
                                        razorpay_signature: response.razorpay_signature,
                                        github_id: userData.user.github_id.toString(),
                                        plan_type: targetPlan
                                    })
                                });
                                
                                if (verifyRes.ok) {
                                    alert(`Payment successful! Upgraded to ${targetPlan.toUpperCase()}.`);
                                    window.location.reload();
                                } else {
                                    alert("Payment verification failed. Please contact support.");
                                    targetBtn.innerHTML = originalText;
                                    targetBtn.disabled = false;
                                }
                            } catch (err) {
                                console.error(err);
                                alert("Error verifying payment.");
                                targetBtn.innerHTML = originalText;
                                targetBtn.disabled = false;
                            }
                        },
                        "prefill": {
                            "name": userData.user.username
                        },
                        "theme": {
                            "color": "#10b981"
                        },
                        "modal": {
                            "ondismiss": function() {
                                targetBtn.innerHTML = originalText;
                                targetBtn.disabled = false;
                            }
                        }
                    };
                    
                    const rzp = new window.Razorpay(options);
                    rzp.on('payment.failed', function (response){
                        alert("Payment failed: " + response.error.description);
                        targetBtn.innerHTML = originalText;
                        targetBtn.disabled = false;
                    });
                    rzp.open();
                    
                } else {
                    alert("Checkout failed. Please try again.");
                    targetBtn.innerHTML = originalText;
                    targetBtn.disabled = false;
                }
            } catch (e) {
                console.error(e);
                alert("Checkout error. Please try again.");
                targetBtn.innerHTML = originalText;
                targetBtn.disabled = false;
            }
        });
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

// Copy command helper function
function copyCommand() {
    const commandText = document.getElementById("install-cmd").innerText;
    
    // Copy to clipboard
    navigator.clipboard.writeText(commandText).then(() => {
        const copyBtn = document.querySelector(".copy-btn");
        const copyIcon = copyBtn.querySelector("i");
        
        // Show success checkmark
        copyIcon.className = "fa-solid fa-check";
        copyIcon.style.color = "#10b981";
        
        setTimeout(() => {
            // Revert back to copy icon
            copyIcon.className = "fa-regular fa-copy";
            copyIcon.style.color = "";
        }, 2000);
    }).catch(err => {
        console.error("Failed to copy text: ", err);
    });
}

// Live Interactive Playground Logic
document.addEventListener("DOMContentLoaded", () => {
    // Inject Auth/Dashboard CTA dynamically based on server session
    fetch('/api/user/dashboard-data')
        .then(res => {
            const navCta = document.querySelector('.nav-cta');
            if (!navCta) return;
            
            if (res.ok) {
                // Logged in
                const dashboardBtn = document.createElement('a');
                dashboardBtn.href = 'dashboard.html';
                dashboardBtn.className = 'btn btn-primary';
                dashboardBtn.innerHTML = '<i class="fa-solid fa-chart-line"></i> Dashboard';
                dashboardBtn.style.marginRight = '12px';
                navCta.prepend(dashboardBtn);
            } else {
                // Not logged in
                const loginBtn = document.createElement('a');
                loginBtn.href = '/api/auth/login';
                loginBtn.className = 'btn btn-outline';
                loginBtn.innerHTML = '<i class="fa-brands fa-github"></i> Sign In';
                loginBtn.style.marginRight = '12px';
                navCta.prepend(loginBtn);
            }
        })
        .catch(err => console.log("API not reachable, static mode"));

    const symbolBtns = document.querySelectorAll(".symbol-btn");
    const centerNode = document.getElementById("graph-center");
    
    // Telemetry display elements
    const telFiles = document.getElementById("telemetry-files");
    const telCallers = document.getElementById("telemetry-callers");
    const telSeverity = document.getElementById("telemetry-severity");
    
    // Orbit nodes
    const orbitNodes = document.querySelectorAll(".orbit-node");

    // Simulated symbol database
    const symbolData = {
        auth_user: {
            centerName: "auth_user",
            files: "3",
            callers: "8",
            severity: "High Impact",
            severityClass: "high",
            activeNodes: ["login_endpoint", "refresh_token", "validate_session", "POST /login", "admin_login", "require_auth"]
        },
        db_pool: {
            centerName: "db_pool",
            files: "5",
            callers: "12",
            severity: "Critical",
            severityClass: "high",
            activeNodes: ["validate_session", "refresh_token", "admin_login", "require_auth"]
        },
        validate_jwt: {
            centerName: "validate_jwt",
            files: "2",
            callers: "4",
            severity: "Medium Impact",
            severityClass: "medium",
            activeNodes: ["validate_session", "require_auth"]
        }
    };

    // Symbol selection handler
    symbolBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            // Update active button state
            symbolBtns.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");

            // Retrieve selected data
            const symbolKey = btn.getAttribute("data-symbol");
            const data = symbolData[symbolKey];

            if (data) {
                // Update text & layout content
                centerNode.textContent = data.centerName;
                telFiles.textContent = data.files;
                telCallers.textContent = data.callers;
                telSeverity.textContent = data.severity;

                // Adjust severity badge class
                telSeverity.className = `severity-badge ${data.severityClass}`;

                // Toggle active/inactive states on visualizer nodes
                orbitNodes.forEach(node => {
                    const nodeName = node.getAttribute("data-name");
                    if (data.activeNodes.includes(nodeName)) {
                        node.classList.remove("inactive");
                    } else {
                        node.classList.add("inactive");
                    }
                });
            }
        });
    });

    // Hover effect on orbits
    const ring1 = document.querySelector(".r1");
    const ring2 = document.querySelector(".r2");

    orbitNodes.forEach(node => {
        node.addEventListener("mouseenter", () => {
            ring1.style.animationPlayState = "paused";
            ring2.style.animationPlayState = "paused";
        });

        node.addEventListener("mouseleave", () => {
            ring1.style.animationPlayState = "running";
            ring2.style.animationPlayState = "running";
        });
    });

    // Scroll Reveal Intersection Observer
    const reveals = document.querySelectorAll(".reveal-fade, .reveal-text");
    const revealObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add("active");
                observer.unobserve(entry.target);
            }
        });
    }, {
        root: null,
        threshold: 0.1,
        rootMargin: "0px 0px -50px 0px"
    });

    reveals.forEach(reveal => revealObserver.observe(reveal));
});

// LemonSqueezy / Gumroad Checkout Flow
async function handleCheckout(planType) {
    if (planType !== 'pro') return;

    // Redirect to login -> dashboard flow
    // The user will upgrade from their actual dashboard once logged in.
    window.location.href = '/api/auth/login';
}

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

    const interactives = document.querySelectorAll('a, button, .bento-card, .price-card, .orbit-node, .symbol-btn');
    interactives.forEach(el => {
        const isCard = el.classList.contains('bento-card') || el.classList.contains('price-card');
        
        el.addEventListener('mouseenter', () => {
            if (cursorGlow) cursorGlow.classList.add('glow-active');
            if (curDot && !isCard) curDot.classList.add('big');
        });
        el.addEventListener('mouseleave', () => {
            if (cursorGlow) cursorGlow.classList.remove('glow-active');
            if (curDot) curDot.classList.remove('big');
        });
        if (isCard) {
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

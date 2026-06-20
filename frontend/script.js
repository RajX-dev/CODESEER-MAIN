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
});

// Gumroad Checkout Flow
async function handleCheckout(planType) {
    if (planType !== 'pro') return;

    try {
        // In a real app, you would get the github_id from the logged-in user's session.
        // For the demo, we will prompt the user to enter their GitHub ID or username.
        const githubId = prompt("Enter your GitHub ID to upgrade (e.g. 12345):", "12345");
        if (!githubId) return;

        const btn = document.querySelector(`button[onclick="handleCheckout('${planType}')"]`);
        const originalText = btn.innerHTML;
        btn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Loading...';
        btn.disabled = true;

        const response = await fetch('/api/create-checkout', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ github_id: githubId })
        });

        const data = await response.json();
        
        if (data.checkout_url) {
            // LemonSqueezy Checkout overlay or redirect
            window.location.href = data.checkout_url;
        } else {
            alert('Failed to generate checkout URL');
            btn.innerHTML = originalText;
            btn.disabled = false;
        }
    } catch (error) {
        console.error('Checkout error:', error);
        alert('An error occurred. Please try again.');
        const btn = document.querySelector(`button[onclick="handleCheckout('${planType}')"]`);
        if (btn) {
            btn.innerHTML = 'Upgrade Now';
            btn.disabled = false;
        }
    }
}

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

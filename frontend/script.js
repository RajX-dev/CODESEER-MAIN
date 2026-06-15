// Copy command helper function
function copyCommand() {
    const commandText = document.getElementById("install-cmd").innerText;
    
    // Copy to clipboard
    navigator.clipboard.writeText(commandText).then(() => {
        const copyBtn = document.querySelector(".copy-btn");
        const copyIcon = copyBtn.querySelector("i");
        
        // Show success checkmark
        copyIcon.className = "fa-solid fa-check";
        copyIcon.style.color = "#50fa7b";
        
        setTimeout(() => {
            // Revert back to copy icon
            copyIcon.className = "fa-regular fa-copy";
            copyIcon.style.color = "";
        }, 2000);
    }).catch(err => {
        console.error("Failed to copy text: ", err);
    });
}

// Add interactive hover highlighting for CSS visualizer nodes
document.addEventListener("DOMContentLoaded", () => {
    const nodes = document.querySelectorAll(".orbit-visualizer .node");
    const centerNode = document.querySelector(".orbit-visualizer .orbit-center");
    
    nodes.forEach(node => {
        node.addEventListener("mouseenter", () => {
            // Pause the orbit animations when inspecting a node
            document.querySelector(".ring-1").style.animationPlayState = "paused";
            document.querySelector(".ring-2").style.animationPlayState = "paused";
            centerNode.style.boxShadow = "0 0 30px rgba(157, 78, 221, 0.8)";
        });
        
        node.addEventListener("mouseleave", () => {
            // Resume the orbit animations
            document.querySelector(".ring-1").style.animationPlayState = "running";
            document.querySelector(".ring-2").style.animationPlayState = "running";
            centerNode.style.boxShadow = "";
        });
    });
});

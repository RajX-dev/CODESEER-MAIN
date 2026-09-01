// ── Copy Command ───────────────────────────────────────────────
function copyCommand() {
    const commandText = document.getElementById("install-cmd").innerText;
    navigator.clipboard.writeText(commandText).then(() => {
        const copyBtn = document.querySelector(".copy-btn");
        const copyIcon = copyBtn.querySelector("i");
        copyIcon.className = "fa-solid fa-check";
        copyIcon.style.color = "#10b981";
        setTimeout(() => {
            copyIcon.className = "fa-regular fa-copy";
            copyIcon.style.color = "";
        }, 2000);
    }).catch(err => console.error("Failed to copy:", err));
}

// ── Razorpay Checkout Flow (PRESERVED — do not modify) ─────────
async function handleCheckout(planType) {
    window.location.href = `/api/auth/login?plan=${planType}`;
}

// ── Scroll Progress Bar ────────────────────────────────────────
function initScrollProgress() {
    const bar = document.getElementById('scroll-progress');
    if (!bar) return;
    window.addEventListener('scroll', () => {
        const scrolled = window.scrollY;
        const max = document.body.scrollHeight - window.innerHeight;
        bar.style.width = ((scrolled / max) * 100).toFixed(2) + '%';
    }, { passive: true });
}

// ── Counter Animation ──────────────────────────────────────────
function animateCounter(el, target, suffix = '', duration = 1800) {
    const start = performance.now();
    const isDecimal = target % 1 !== 0;
    function step(now) {
        const elapsed = now - start;
        const progress = Math.min(elapsed / duration, 1);
        // Ease out expo
        const eased = 1 - Math.pow(2, -10 * progress);
        const current = Math.round(eased * target);
        el.textContent = (isDecimal ? current.toFixed(1) : current) + suffix;
        if (progress < 1) requestAnimationFrame(step);
        else el.textContent = target + suffix;
    }
    requestAnimationFrame(step);
}

// ── 3D Magnetic Tilt on Cards ──────────────────────────────────
function init3DTilt() {
    const cards = document.querySelectorAll('.bento-card, .price-card');
    cards.forEach(card => {
        card.addEventListener('mousemove', (e) => {
            const rect = card.getBoundingClientRect();
            const cx = rect.left + rect.width / 2;
            const cy = rect.top + rect.height / 2;
            const dx = (e.clientX - cx) / (rect.width / 2);
            const dy = (e.clientY - cy) / (rect.height / 2);
            const tiltX = dy * -6;
            const tiltY = dx * 6;
            card.style.transform = `perspective(900px) rotateX(${tiltX}deg) rotateY(${tiltY}deg) translateY(-4px) scale(1.02)`;
            // Update card glow origin
            card.style.setProperty('--card-x', `${e.clientX - rect.left}px`);
            card.style.setProperty('--card-y', `${e.clientY - rect.top}px`);
        });
        card.addEventListener('mouseleave', () => {
            card.style.transform = '';
        });
    });
}

// ── Magnetic Button Effect ─────────────────────────────────────
function initMagneticButtons() {
    const btns = document.querySelectorAll('.hero-actions .btn');
    btns.forEach(btn => {
        btn.addEventListener('mousemove', (e) => {
            const rect = btn.getBoundingClientRect();
            const cx = rect.left + rect.width / 2;
            const cy = rect.top + rect.height / 2;
            const dx = (e.clientX - cx) * 0.25;
            const dy = (e.clientY - cy) * 0.25;
            btn.style.transform = `translate(${dx}px, ${dy}px) scale(1.05)`;
        });
        btn.addEventListener('mouseleave', () => {
            btn.style.transform = '';
        });
    });
}

// ── Section title word-split animation ────────────────────────
function initSplitTitles() {
    document.querySelectorAll('.section-title').forEach(el => {
        const words = el.textContent.trim().split(' ');
        el.innerHTML = words.map((w, i) =>
            `<span class="reveal-text reveal-delay-${(i % 3) + 1}" style="display:inline-block;margin-right:0.25em;">
                <span class="reveal-inner">${w}</span>
             </span>`
        ).join('');
    });
}

// ── Parallax on aurora orbs ────────────────────────────────────
function initParallax() {
    const orbs = document.querySelectorAll('.orb');
    let ticking = false;
    window.addEventListener('scroll', () => {
        if (!ticking) {
            requestAnimationFrame(() => {
                const y = window.scrollY;
                orbs.forEach((orb, i) => {
                    const speed = [0.04, -0.03, 0.06, -0.02][i] || 0.03;
                    orb.style.transform = `translateY(${y * speed}px)`;
                });
                ticking = false;
            });
            ticking = true;
        }
    }, { passive: true });
}

// ── Scroll Reveal Observer ─────────────────────────────────────
function initReveal() {
    // Add reveal-fade to bento cards and price cards automatically
    document.querySelectorAll('.bento-card, .price-card').forEach(el => {
        if (!el.classList.contains('reveal-fade')) el.classList.add('reveal-fade');
    });

    const reveals = document.querySelectorAll('.reveal-fade, .reveal-text');
    const observer = new IntersectionObserver((entries, obs) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('active');
                obs.unobserve(entry.target);
            }
        });
    }, { threshold: 0.06, rootMargin: '0px 0px -40px 0px' });
    reveals.forEach(el => observer.observe(el));
}

// ── Custom Cursor & Glow ───────────────────────────────────────
function initCursor() {
    const cursorGlow = document.querySelector('.cursor-glow');
    const curDot = document.querySelector('.cur-dot');
    if (!cursorGlow && !curDot) return;

    let mouseX = 0, mouseY = 0;
    let currentX = 0, currentY = 0;
    let cursorInitialized = false;

    document.addEventListener('mousemove', (e) => {
        if (!cursorInitialized) {
            mouseX = currentX = e.clientX;
            mouseY = currentY = e.clientY;
            if (curDot) curDot.style.opacity = '1';
            if (cursorGlow) cursorGlow.style.opacity = '1';
            cursorInitialized = true;
        }
        mouseX = e.clientX;
        mouseY = e.clientY;
        if (cursorGlow) cursorGlow.style.opacity = '1';
    });

    document.addEventListener('mouseleave', () => {
        if (cursorGlow) cursorGlow.style.opacity = '0';
        if (curDot) curDot.style.opacity = '0';
    });

    const interactives = document.querySelectorAll('a, button, .bento-card, .price-card');
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
    });

    function animateGlow() {
        if (curDot) {
            curDot.style.transform = `translate(-50%, -50%) translate3d(${mouseX}px, ${mouseY}px, 0)`;
        }
        if (cursorGlow) {
            currentX += (mouseX - currentX) * 0.08;
            currentY += (mouseY - currentY) * 0.08;
            cursorGlow.style.setProperty('--mouse-x', currentX);
            cursorGlow.style.setProperty('--mouse-y', currentY);
        }
        requestAnimationFrame(animateGlow);
    }
    animateGlow();
}

// ── Live Stats ─────────────────────────────────────────────────
function initLiveStats() {
    // GitHub Stars
    fetch('https://api.github.com/repos/RajX-dev/N3MO')
        .then(r => r.json())
        .then(data => {
            const el = document.getElementById('gh-stars');
            if (el && data.stargazers_count != null) {
                const count = data.stargazers_count;
                // Animate to value when visible
                const obs = new IntersectionObserver(entries => {
                    if (entries[0].isIntersecting) {
                        animateCounter(el, count, '');
                        obs.disconnect();
                    }
                }, { threshold: 0.5 });
                obs.observe(el);
            }
        })
        .catch(() => {
            const el = document.getElementById('gh-stars');
            if (el) el.textContent = '900+';
        });

    // PyPI Downloads
    fetch('https://api.pepy.tech/api/v2/projects/n3mo')
        .then(r => r.json())
        .then(data => {
            const el = document.getElementById('pypi-downloads');
            if (el && data.total_downloads != null) {
                const count = data.total_downloads;
                const obs = new IntersectionObserver(entries => {
                    if (entries[0].isIntersecting) {
                        const displayVal = count >= 1000 ? Math.floor(count / 1000) : count;
                        const suffix = count >= 1000 ? 'K+' : '';
                        animateCounter(el, displayVal, suffix);
                        obs.disconnect();
                    }
                }, { threshold: 0.5 });
                obs.observe(el);
            }
        })
        .catch(() => {
            const el = document.getElementById('pypi-downloads');
            if (el) el.textContent = '12K+';
        });

    // Edges indexed — count up from 0 to 480K
    const edgesEl = document.getElementById('edges-count');
    if (edgesEl) {
        const obs = new IntersectionObserver(entries => {
            if (entries[0].isIntersecting) {
                animateCounter(edgesEl, 480, 'K');
                obs.disconnect();
            }
        }, { threshold: 0.5 });
        obs.observe(edgesEl);
    }
}

// ── Auth check ─────────────────────────────────────────────────
function initAuth() {
    fetch('/api/auth/me', { credentials: 'include' })
        .then(res => {
            const navCta = document.querySelector('.nav-cta');
            if (!navCta) return;
            if (res.ok) {
                const btn = document.createElement('a');
                btn.href = 'dashboard.html';
                btn.className = 'btn btn-primary';
                btn.innerHTML = '<i class="fa-solid fa-chart-line"></i> Dashboard';
                btn.style.cssText = 'margin-right:8px;padding:7px 14px;border-radius:6px;font-size:12.5px;animation:none;';
                navCta.prepend(btn);
            } else {
                const btn = document.createElement('a');
                btn.href = '/api/auth/login';
                btn.className = 'btn btn-outline';
                btn.innerHTML = '<i class="fa-brands fa-github"></i> Sign In';
                btn.style.cssText = 'margin-right:8px;padding:7px 14px;border-radius:6px;font-size:12.5px;animation:none;';
                navCta.prepend(btn);
            }
        })
        .catch(() => {});
}

// ── Hero CTA primary button — id-based scroll to pricing ───────
function initHeroCTA() {
    const cta = document.getElementById('hero-cta-primary');
    if (cta) {
        cta.addEventListener('click', (e) => {
            // Only intercept if not logged in (dashboard link handled by auth)
            if (cta.href && cta.href.includes('dashboard')) return;
        });
    }
}

// ── Init all ──────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    initScrollProgress();
    initSplitTitles();
    initReveal();
    init3DTilt();
    initMagneticButtons();
    initParallax();
    initLiveStats();
    initAuth();
    initHeroCTA();
    initCursor();
});

const API_BASE = '/api/admin';

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    const token = localStorage.getItem('n3mo_token');
    if (!token) {
        window.location.href = '/index.html';
        return;
    }
    
    // Test auth first
    fetch('/api/auth/me', {
        headers: { 'Authorization': `Bearer ${token}` }
    })
    .then(r => {
        if (!r.ok) throw new Error();
        return r.json();
    })
    .then(data => {
        if (!data.is_admin) {
            alert('Access Denied: Admin privileges required.');
            window.location.href = '/dashboard.html';
        }
        document.getElementById('admin-username').innerText = data.username;
        loadUsers();
    })
    .catch(() => {
        window.location.href = '/dashboard.html';
    });
});

function switchTab(tabId, element) {
    document.querySelectorAll('.admin-nav a').forEach(a => a.classList.remove('active'));
    element.classList.add('active');
    
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    document.getElementById(tabId).classList.add('active');
    
    if (tabId === 'users-tab') {
        document.getElementById('tab-title').innerText = 'Users & Plans';
        document.getElementById('tab-desc').innerText = 'Manage all SaaS subscriptions and users.';
        loadUsers();
    } else {
        document.getElementById('tab-title').innerText = 'Discount Codes';
        document.getElementById('tab-desc').innerText = 'Generate and track usage of discount codes.';
        loadDiscounts();
    }
}

async function fetchAuth(url, options = {}) {
    const token = localStorage.getItem('n3mo_token');
    return fetch(url, {
        ...options,
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
            ...(options.headers || {})
        }
    });
}

async function loadUsers() {
    try {
        const res = await fetchAuth(`${API_BASE}/users`);
        const data = await res.json();
        
        const tbody = document.getElementById('users-table-body');
        tbody.innerHTML = '';
        
        data.users.forEach(u => {
            const tr = document.createElement('tr');
            const statusClass = u.status === 'active' ? 'status-active' : (u.status === 'none' ? 'status-none' : 'status-cancelled');
            
            tr.innerHTML = `
                <td>${u.github_id}</td>
                <td><strong>${u.username}</strong> ${u.is_admin ? '<i class="fa-solid fa-crown" style="color:var(--primary)"></i>' : ''}</td>
                <td>${u.email || '-'}</td>
                <td>
                    <select class="plan-select" id="plan-${u.id}">
                        <option value="none" ${u.plan_type === 'none' ? 'selected' : ''}>None</option>
                        <option value="starter" ${u.plan_type === 'starter' ? 'selected' : ''}>Starter</option>
                        <option value="pro" ${u.plan_type === 'pro' ? 'selected' : ''}>Pro</option>
                        <option value="team" ${u.plan_type === 'team' ? 'selected' : ''}>Team</option>
                        <option value="enterprise" ${u.plan_type === 'enterprise' ? 'selected' : ''}>Enterprise</option>
                    </select>
                </td>
                <td><span class="status-badge ${statusClass}">${u.status.toUpperCase()}</span></td>
                <td>
                    <button class="btn btn-outline" style="padding: 6px 12px; font-size:0.8rem;" onclick="updatePlan('${u.id}')">Save Plan</button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (e) {
        console.error(e);
        alert('Failed to load users');
    }
}

async function updatePlan(userId) {
    const plan = document.getElementById(`plan-${userId}`).value;
    const status = plan === 'none' ? 'cancelled' : 'active';
    
    try {
        const res = await fetchAuth(`${API_BASE}/users/${userId}/subscription`, {
            method: 'PUT',
            body: JSON.stringify({ plan_type: plan, status: status })
        });
        
        if (res.ok) {
            alert('Plan updated successfully');
            loadUsers();
        } else {
            alert('Failed to update plan');
        }
    } catch (e) {
        console.error(e);
    }
}

async function loadDiscounts() {
    try {
        const res = await fetchAuth(`${API_BASE}/discounts`);
        const data = await res.json();
        
        const tbody = document.getElementById('discounts-table-body');
        tbody.innerHTML = '';
        
        data.discounts.forEach(d => {
            const tr = document.createElement('tr');
            const max = d.max_uses === -1 ? '∞' : d.max_uses;
            const created = new Date(d.created_at).toLocaleDateString();
            
            tr.innerHTML = `
                <td><strong>${d.code}</strong></td>
                <td>${d.discount_percentage}% OFF</td>
                <td>${d.uses} / ${max}</td>
                <td>${created}</td>
                <td>
                    <button class="btn btn-outline" style="padding: 6px 12px; font-size:0.8rem; border-color:#ef4444; color:#ef4444;" onclick="deleteDiscount('${d.code}')">Delete</button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (e) {
        console.error(e);
    }
}

async function createDiscount() {
    const code = document.getElementById('new-code').value;
    const perc = parseInt(document.getElementById('new-percentage').value);
    const maxUses = parseInt(document.getElementById('new-max-uses').value);
    
    if (!code || isNaN(perc)) {
        alert('Please fill out code and percentage');
        return;
    }
    
    try {
        const res = await fetchAuth(`${API_BASE}/discounts`, {
            method: 'POST',
            body: JSON.stringify({
                code: code,
                discount_percentage: perc,
                max_uses: maxUses
            })
        });
        
        if (res.ok) {
            document.getElementById('new-code').value = '';
            loadDiscounts();
        } else {
            alert('Failed to create discount code');
        }
    } catch (e) {
        console.error(e);
    }
}

async function deleteDiscount(code) {
    if (!confirm(`Are you sure you want to delete ${code}?`)) return;
    
    try {
        const res = await fetchAuth(`${API_BASE}/discounts/${code}`, {
            method: 'DELETE'
        });
        
        if (res.ok) loadDiscounts();
    } catch (e) {
        console.error(e);
    }
}

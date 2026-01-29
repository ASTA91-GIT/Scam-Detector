// Load dashboard data
async function loadDashboard() {
    try {
        const token = localStorage.getItem('token');
        if (!token) {
            window.location.href = 'login.html';
            return;
        }

        await loadUserInfo();
        await loadStats();
        await loadAnalyses();

    } catch (error) {
        console.error('Error loading dashboard:', error);
    }
}

// Load logged-in user info
// dashboard.js

async function loadUserInfo() {
    try {
        const response = await fetch(`${API_BASE_URL}/auth/me`, {
            headers: {
                Authorization: `Bearer ${localStorage.getItem('token')}`
            }
        });

        if (!response.ok) throw new Error('User fetch failed');

        const user = await response.json();
        
        // FIX: Change user.name to user.username to match backend
        document.getElementById('userName').innerText = `Name: ${user.username || 'User'}`;
        document.getElementById('userEmail').innerText = `Email: ${user.email || 'No Email'}`;

    } catch (err) {
        console.error(err);
    }
}

// Load stats
async function loadStats() {
    try {
        const res = await fetch(`${API_BASE_URL}/dashboard/stats`, {
            headers: getAuthHeaders()
        });

        if (!res.ok) return;

        const stats = await res.json();
        document.getElementById('statsCards').innerHTML = `
            <div class="stat-card">
                <h3>Safe</h3>
                <div class="stat-value">${stats.safe_count}</div>
            </div>
            <div class="stat-card">
                <h3>Suspicious</h3>
                <div class="stat-value">${stats.suspicious_count}</div>
            </div>
            <div class="stat-card">
                <h3>High Risk</h3>
                <div class="stat-value">${stats.high_risk_count}</div>
            </div>
        `;
    } catch (err) {
        console.error(err);
    }
}

// Load analyses
// Load analyses
async function loadAnalyses() {
    try {
        const res = await fetch(`${API_BASE_URL}/dashboard/analyses`, {
            headers: getAuthHeaders()
        });

        if (!res.ok) return;

        const data = await res.json();

        document.getElementById('analysesList').innerHTML =
            data.analyses.length === 0
                ? '<p>No analyses yet</p>'
                : data.analyses.map(a => `
                    <div class="analysis-item" data-risk="${a.risk_level}">
                        <div class="analysis-item-info">
                            <h3>${a.risk_level}</h3>

                            <!-- TRUST SCORE BLOCK -->
                            <div class="analysis-score">
                                <span>Trust Score</span>
                                <strong>${a.trust_score}</strong>
                            </div>
                        </div>

                        <span class="dashboard-badge ${
                            a.risk_level === 'Safe'
                                ? 'safe'
                                : a.risk_level === 'Suspicious'
                                ? 'warning'
                                : 'danger'
                        }">
                            ${a.risk_level}
                        </span>
                    </div>
                `).join('');

    } catch (err) {
        console.error(err);
    }
}
document.addEventListener('DOMContentLoaded', loadDashboard);

// Logout functionality
/**
 * Dashboard Controller
 * Fetches real telemetry from /api/dashboard/stats and /api/dashboard/analyses,
 * renders Donut chart on Canvas, draws activity timeline and trend bars.
 */

document.addEventListener('DOMContentLoaded', async () => {
    // 1. Initialize shell
    renderAppShell('dashboard');

    if (!requireAuth()) return;

    // 2. Personalize greeting
    setupGreeting();

    // 3. Load stats & telemetry
    await loadDashboardTelemetry();
});

function setupGreeting() {
    const user = getUser();
    const name = user?.username || 'Analyst';
    const hour = new Date().getHours();
    let timeGreeting = 'Good morning';
    if (hour >= 12 && hour < 17) timeGreeting = 'Good afternoon';
    else if (hour >= 17) timeGreeting = 'Good evening';

    const greetingEl = document.getElementById('dashGreeting');
    if (greetingEl) {
        greetingEl.textContent = `${timeGreeting}, ${name}`;
    }
}

async function loadDashboardTelemetry() {
    try {
        const [statsRes, analysesRes] = await Promise.all([
            fetch(`${API_BASE_URL}/dashboard/stats`, { headers: getAuthHeaders(true) }),
            fetch(`${API_BASE_URL}/dashboard/analyses?limit=6`, { headers: getAuthHeaders(true) })
        ]);

        if (statsRes.status === 401 || analysesRes.status === 401) {
            logout();
            return;
        }

        const statsData = statsRes.ok ? await statsRes.json() : {};
        const analysesData = analysesRes.ok ? await analysesRes.json() : { analyses: [] };

        renderStatsCards(statsData);
        renderSafetyScore(statsData);
        renderDonutChart(statsData);
        renderTimeline(analysesData.analyses || []);
        renderTrendChart(statsData.risk_trend || []);
        renderThreatSignals(statsData.top_threat_signals || []);

    } catch (err) {
        console.error('Error loading dashboard data:', err);
        showToast('Failed to load dashboard telemetry. Please refresh.', 'danger');
    }
}

function renderStatsCards(data) {
    document.getElementById('statTotalScans').textContent = data.total_analyses ?? 0;
    document.getElementById('statHighRisk').textContent = data.high_risk_count ?? 0;
    document.getElementById('statSuspicious').textContent = data.suspicious_count ?? 0;
    document.getElementById('statSafe').textContent = data.safe_count ?? 0;
    document.getElementById('statSavedReports').textContent = data.saved_reports_count ?? 0;
    document.getElementById('donutAvgScore').textContent = data.average_trust_score ?? '--';
}

function renderSafetyScore(data) {
    const score = data.safety_score ?? 100;
    const scoreEl = document.getElementById('dashSafetyScore');
    const explEl = document.getElementById('dashSafetyExplanation');

    if (scoreEl) scoreEl.textContent = score;
    if (explEl && data.safety_explanation) explEl.textContent = data.safety_explanation;
}

function renderDonutChart(data) {
    const canvas = document.getElementById('riskDonutCanvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const w = canvas.width;
    const h = canvas.height;
    const cx = w / 2;
    const cy = h / 2;
    const radius = 65;
    const lineWidth = 16;

    ctx.clearRect(0, 0, w, h);

    const safe = data.safe_count || 0;
    const susp = data.suspicious_count || 0;
    const high = data.high_risk_count || 0;
    const total = safe + susp + high;

    if (total === 0) {
        // Draw baseline empty track
        ctx.beginPath();
        ctx.arc(cx, cy, radius, 0, 2 * Math.PI);
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.08)';
        ctx.lineWidth = lineWidth;
        ctx.stroke();
        return;
    }

    const segments = [
        { count: safe, color: '#10b981' },
        { count: susp, color: '#f59e0b' },
        { count: high, color: '#ef4444' }
    ];

    let startAngle = -0.5 * Math.PI;

    segments.forEach(seg => {
        if (seg.count === 0) return;
        const sliceAngle = (seg.count / total) * 2 * Math.PI;
        ctx.beginPath();
        ctx.arc(cx, cy, radius, startAngle, startAngle + sliceAngle);
        ctx.strokeStyle = seg.color;
        ctx.lineWidth = lineWidth;
        ctx.lineCap = 'round';
        ctx.stroke();
        startAngle += sliceAngle;
    });
}

function renderTimeline(analyses) {
    const container = document.getElementById('dashTimelineList');
    if (!container) return;

    if (!analyses || analyses.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">🛡️</div>
                <div class="empty-title">No analyses yet</div>
                <p class="empty-desc">Run your first forensic scan to detect scam job offers and verify recruiters.</p>
                <a href="analyze.html" class="btn btn-primary btn-sm">Analyze a Job Offer</a>
            </div>
        `;
        return;
    }

    container.innerHTML = analyses.map(a => {
        const isSafe = a.risk_level === 'Safe';
        const isHigh = a.risk_level === 'High Risk' || a.risk_level === 'High';
        const badgeClass = isSafe ? 'badge-safe' : (isHigh ? 'badge-danger' : 'badge-warning');
        const dateStr = a.created_at ? new Date(a.created_at).toLocaleDateString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : 'Recent';

        return `
            <div class="timeline-row">
                <div class="timeline-meta">
                    <div class="timeline-title">${a.job_title || 'Job Offer Analysis'}</div>
                    <div class="timeline-sub">${a.company_name || 'Unspecified Company'} &bull; ${dateStr}</div>
                </div>
                <div class="timeline-badges">
                    <span class="badge ${badgeClass}">${a.risk_level} (${a.trust_score})</span>
                    <a href="result.html?id=${a._id}" class="btn btn-outline btn-sm" title="View full report">
                        View Dossier
                    </a>
                </div>
            </div>
        `;
    }).join('');
}

function renderTrendChart(trendData) {
    const container = document.getElementById('riskTrendContainer');
    if (!container) return;

    if (!trendData || trendData.length === 0) {
        container.innerHTML = `
            <p style="color: var(--text-muted); font-size: 0.85rem; text-align: center; margin: auto;">
                Trend telemetry will populate as you scan job postings over time.
            </p>
        `;
        return;
    }

    const maxTotal = Math.max(...trendData.map(d => d.total), 1);

    container.innerHTML = trendData.map(item => {
        const heightPct = Math.max(15, Math.round((item.total / maxTotal) * 100));
        const hasThreat = item.high_risk > 0;
        const barColor = hasThreat ? 'var(--risk-danger)' : 'var(--accent-cyan)';

        return `
            <div style="display: flex; flex-direction: column; align-items: center; gap: 6px; flex: 1;">
                <div style="font-size: 0.72rem; font-weight: 600; color: var(--text-primary);">${item.total}</div>
                <div style="width: 100%; max-width: 32px; height: 110px; display: flex; align-items: flex-end; background: var(--bg-surface); border-radius: 4px; overflow: hidden; padding: 2px;">
                    <div style="width: 100%; height: ${heightPct}%; background: ${barColor}; border-radius: 3px; transition: height 0.6s ease;" title="${item.date}: ${item.total} scans (Avg Trust: ${item.avg_score}/100)"></div>
                </div>
                <div style="font-size: 0.68rem; color: var(--text-muted); white-space: nowrap;">${item.date}</div>
            </div>
        `;
    }).join('');
}

function renderThreatSignals(signals) {
    const container = document.getElementById('threatSignalsList');
    if (!container) return;

    if (!signals || signals.length === 0) {
        container.innerHTML = `
            <p style="color: var(--text-muted); font-size: 0.85rem; text-align: center; padding: 1.5rem;">
                No scam indicators identified yet.
            </p>
        `;
        return;
    }

    container.innerHTML = signals.map(s => `
        <div class="signal-pill">
            <span>${s.signal}</span>
            <span>${s.count} flag${s.count > 1 ? 's' : ''}</span>
        </div>
    `).join('');
}
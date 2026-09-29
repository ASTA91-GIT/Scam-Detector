/**
 * ScamGuard / Scam Detector - Core Frontend Architecture
 * Provides API client, authentication guards, theme manager, sidebar/topbar shell,
 * toast notification center, confirmation modals, global search (Ctrl+K),
 * and live notification polling.
 */

// 1. Dynamic API Base URL
const API_BASE_URL = (window.location.protocol === 'file:')
    ? 'http://127.0.0.1:5000/api'
    : `${window.location.origin}/api`;

// 2. Auth State Management
function getToken() {
    return localStorage.getItem('token');
}

function getUser() {
    try {
        const u = localStorage.getItem('user');
        return u ? JSON.parse(u) : null;
    } catch {
        return null;
    }
}

function setUser(user) {
    if (!user) {
        localStorage.removeItem('user');
    } else {
        localStorage.setItem('user', JSON.stringify(user));
    }
}

function setToken(token) {
    if (!token) {
        localStorage.removeItem('token');
    } else {
        localStorage.setItem('token', token);
    }
}

function getAuthHeaders(isJson = true) {
    const token = getToken();
    const headers = {};
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    if (isJson) {
        headers['Content-Type'] = 'application/json';
    }
    return headers;
}

function getErrorMessage(data, fallback = 'An error occurred. Please try again.') {
    if (!data) return fallback;
    if (typeof data === 'string') return data;
    if (data.error) {
        if (typeof data.error === 'string') return data.error;
        if (data.error.message && typeof data.error.message === 'string') return data.error.message;
        if (typeof data.error === 'object') return data.error.message || JSON.stringify(data.error);
    }
    if (data.message && typeof data.message === 'string') return data.message;
    return fallback;
}

function requireAuth() {
    const token = getToken();
    if (!token) {
        // If on a protected page, redirect to login
        const path = window.location.pathname;
        if (!path.includes('login.html') && !path.includes('signup.html') && !path.includes('index.html') && path !== '/' && !path.includes('intelligence.html')) {
            window.location.href = 'login.html?redirect=' + encodeURIComponent(window.location.pathname + window.location.search);
        }
        return false;
    }
    return true;
}

function logout() {
    fetch(`${API_BASE_URL}/auth/logout`, { method: 'POST' }).catch(() => {});
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    showToast('Logged out successfully', 'info');
    setTimeout(() => {
        window.location.href = 'login.html';
    }, 400);
}

// 3. Theme Manager
function initTheme() {
    const savedTheme = localStorage.getItem('theme') || 'dark';
    applyTheme(savedTheme);
}

function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    document.body?.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);

    // Update toggles in DOM
    const toggles = document.querySelectorAll('.theme-toggle-btn');
    toggles.forEach(btn => {
        btn.innerHTML = theme === 'dark' 
            ? `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg><span>Light</span>`
            : `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg><span>Dark</span>`;
    });
}

function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme') || 'dark';
    const next = current === 'dark' ? 'light' : 'dark';
    applyTheme(next);

    // Optionally sync with user preferences API if logged in
    if (getToken()) {
        fetch(`${API_BASE_URL}/auth/preferences`, {
            method: 'PUT',
            headers: getAuthHeaders(true),
            body: JSON.stringify({ theme: next })
        }).catch(() => {});
    }
}

// 4. Toast Notification System
function showToast(message, type = 'info', duration = 4000) {
    let container = document.getElementById('cyberToastContainer');
    if (!container) {
        container = document.createElement('div');
        container.id = 'cyberToastContainer';
        container.className = 'cyber-toast-container';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `cyber-toast toast-${type}`;

    let iconSvg = '';
    if (type === 'success') {
        iconSvg = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>`;
    } else if (type === 'danger' || type === 'error') {
        iconSvg = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>`;
    } else if (type === 'warning') {
        iconSvg = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" stroke-width="2"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`;
    } else {
        iconSvg = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#06b6d4" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>`;
    }

    toast.innerHTML = `
        <div class="toast-icon">${iconSvg}</div>
        <div class="toast-message">${message}</div>
        <button class="toast-close" aria-label="Close">&times;</button>
    `;

    toast.querySelector('.toast-close').addEventListener('click', () => {
        toast.classList.add('hide');
        setTimeout(() => toast.remove(), 250);
    });

    container.appendChild(toast);

    setTimeout(() => {
        if (toast.parentElement) {
            toast.classList.add('hide');
            setTimeout(() => toast.remove(), 250);
        }
    }, duration);
}

// 5. Accessible Confirmation Modal
function showConfirmModal({ title, message, confirmText = 'Confirm', confirmClass = 'btn-danger', onConfirm }) {
    let modalOverlay = document.getElementById('cyberConfirmModal');
    if (!modalOverlay) {
        modalOverlay = document.createElement('div');
        modalOverlay.id = 'cyberConfirmModal';
        modalOverlay.className = 'cyber-modal-overlay';
        document.body.appendChild(modalOverlay);
    }

    modalOverlay.innerHTML = `
        <div class="cyber-modal">
            <div class="cyber-modal-header">
                <h3 class="cyber-modal-title">${title}</h3>
                <button class="cyber-modal-close" id="confirmModalClose">&times;</button>
            </div>
            <div class="cyber-modal-body">
                <p>${message}</p>
            </div>
            <div class="cyber-modal-footer">
                <button class="btn btn-outline" id="confirmModalCancel">Cancel</button>
                <button class="btn ${confirmClass}" id="confirmModalAction">${confirmText}</button>
            </div>
        </div>
    `;

    modalOverlay.classList.add('active');

    function close() {
        modalOverlay.classList.remove('active');
    }

    modalOverlay.querySelector('#confirmModalClose').onclick = close;
    modalOverlay.querySelector('#confirmModalCancel').onclick = close;
    modalOverlay.querySelector('#confirmModalAction').onclick = () => {
        close();
        if (typeof onConfirm === 'function') onConfirm();
    };

    modalOverlay.onclick = (e) => {
        if (e.target === modalOverlay) close();
    };
}

// 6. User Avatar Generator / Renderer
function getInitials(name = '') {
    if (!name) return 'SA';
    const parts = name.trim().split(/\s+/);
    if (parts.length >= 2) {
        return (parts[0][0] + parts[1][0]).toUpperCase();
    }
    return name.slice(0, 2).toUpperCase();
}

function renderAvatarElement(user, sizeClass = '') {
    const initials = getInitials(user?.username || 'User');
    if (user?.avatar_url) {
        return `<img src="${user.avatar_url}" alt="${user.username}" class="user-avatar-img ${sizeClass}" onerror="this.outerHTML='<div class=\\'user-avatar-initials ${sizeClass}\\'>${initials}</div>'">`;
    }
    return `<div class="user-avatar-initials ${sizeClass}">${initials}</div>`;
}

// 7. Global Command Search Modal (Ctrl + K)
function setupCommandPalette() {
    let palette = document.getElementById('cyberCommandPalette');
    if (!palette) {
        palette = document.createElement('div');
        palette.id = 'cyberCommandPalette';
        palette.className = 'cyber-modal-overlay command-palette-overlay';
        palette.innerHTML = `
            <div class="command-palette-card">
                <div class="palette-input-wrap">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
                    <input type="text" id="paletteSearchInput" placeholder="Search analyses, red flags, pages (e.g., 'crypto', 'history', 'telegram')..." autocomplete="off">
                    <span class="palette-esc-badge">ESC</span>
                </div>
                <div class="palette-results" id="paletteResults">
                    <div class="palette-section-title">Quick Navigation</div>
                    <a href="dashboard.html" class="palette-item">
                        <span class="palette-item-icon">📊</span>
                        <div><strong>Security Dashboard</strong><small>Overview and telemetry</small></div>
                    </a>
                    <a href="analyze.html" class="palette-item">
                        <span class="palette-item-icon">🛡️</span>
                        <div><strong>New Job Analysis</strong><small>Scan offer letters & job postings</small></div>
                    </a>
                    <a href="history.html" class="palette-item">
                        <span class="palette-item-icon">📜</span>
                        <div><strong>Analysis History</strong><small>Review past forensic scans</small></div>
                    </a>
                    <a href="saved.html" class="palette-item">
                        <span class="palette-item-icon">🔖</span>
                        <div><strong>Saved Reports</strong><small>Bookmarked verified reports</small></div>
                    </a>
                    <a href="intelligence.html" class="palette-item">
                        <span class="palette-item-icon">🧠</span>
                        <div><strong>Scam Intelligence Center</strong><small>Scam patterns & safety checklist</small></div>
                    </a>
                </div>
            </div>
        `;
        document.body.appendChild(palette);

        const input = palette.querySelector('#paletteSearchInput');
        const results = palette.querySelector('#paletteResults');

        palette.onclick = (e) => {
            if (e.target === palette) palette.classList.remove('active');
        };

        input.addEventListener('input', () => {
            const query = input.value.trim().toLowerCase();
            if (!query) {
                results.innerHTML = `
                    <div class="palette-section-title">Quick Navigation</div>
                    <a href="dashboard.html" class="palette-item"><span class="palette-item-icon">📊</span><div><strong>Security Dashboard</strong><small>Overview and telemetry</small></div></a>
                    <a href="analyze.html" class="palette-item"><span class="palette-item-icon">🛡️</span><div><strong>New Job Analysis</strong><small>Scan offer letters & job postings</small></div></a>
                    <a href="history.html" class="palette-item"><span class="palette-item-icon">📜</span><div><strong>Analysis History</strong><small>Review past forensic scans</small></div></a>
                    <a href="saved.html" class="palette-item"><span class="palette-item-icon">🔖</span><div><strong>Saved Reports</strong><small>Bookmarked verified reports</small></div></a>
                    <a href="intelligence.html" class="palette-item"><span class="palette-item-icon">🧠</span><div><strong>Scam Intelligence Center</strong><small>Scam patterns & safety checklist</small></div></a>
                `;
                return;
            }

            // Quick live knowledge search
            const items = [
                { title: 'New Job Offer Scan', url: 'analyze.html', desc: 'Paste text or upload PDF/DOCX to detect fraud', icon: '🛡️' },
                { title: 'Analysis History', url: 'history.html', desc: 'Browse and filter all past scans', icon: '📜' },
                { title: 'Saved Reports Repository', url: 'saved.html', desc: 'View bookmarked scam dossiers and custom notes', icon: '🔖' },
                { title: 'Scam Intelligence Hub', url: 'intelligence.html', desc: 'Explore common employment scams and checklists', icon: '🧠' },
                { title: 'Profile & Security', url: 'profile.html', desc: 'Manage credentials, avatar, and activity log', icon: '👤' },
                { title: 'Platform Settings', url: 'settings.html', desc: 'Theme, notification toggles, privacy export', icon: '⚙️' },
                { title: 'Advance Fee Scam Red Flag', url: 'intelligence.html#red-flags', desc: 'Employer demanding training or registration payment', icon: '🚩' },
                { title: 'Crypto Job Fraud', url: 'intelligence.html#crypto', desc: 'USDT/Bitcoin task schemes and fake crypto re-shipping', icon: '🚩' },
                { title: 'Telegram / WhatsApp Hiring', url: 'intelligence.html#red-flags', desc: 'Unverified recruiters avoiding official corporate channels', icon: '🚩' },
                { title: 'Fake Check Overpayment', url: 'intelligence.html#red-flags', desc: 'Bounced cashier checks for home office equipment', icon: '🚩' }
            ];

            const filtered = items.filter(i => i.title.toLowerCase().includes(query) || i.desc.toLowerCase().includes(query));
            if (filtered.length === 0) {
                results.innerHTML = `<div class="palette-empty"><p>No results found for "${query}"</p><a href="analyze.html" class="btn btn-sm btn-primary">Run Analysis with "${query}"</a></div>`;
            } else {
                results.innerHTML = filtered.map(i => `
                    <a href="${i.url}" class="palette-item">
                        <span class="palette-item-icon">${i.icon}</span>
                        <div><strong>${i.title}</strong><small>${i.desc}</small></div>
                    </a>
                `).join('');
            }
        });
    }

    window.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            palette.classList.toggle('active');
            if (palette.classList.contains('active')) {
                setTimeout(() => palette.querySelector('#paletteSearchInput').focus(), 50);
            }
        }
        if (e.key === 'Escape' && palette.classList.contains('active')) {
            palette.classList.remove('active');
        }
    });
}

// 8. Notification Bell & Center Logic
async function initNotifications() {
    const bellBtn = document.getElementById('notifBellBtn');
    const badge = document.getElementById('notifBadge');
    const dropdown = document.getElementById('notifDropdown');
    const list = document.getElementById('notifList');

    if (!bellBtn || !getToken()) return;

    async function fetchNotifications() {
        try {
            const res = await fetch(`${API_BASE_URL}/notifications`, {
                headers: getAuthHeaders(true)
            });
            if (!res.ok) return;
            const data = await res.json();
            const unread = data.unread_count || 0;

            if (badge) {
                if (unread > 0) {
                    badge.textContent = unread > 99 ? '99+' : unread;
                    badge.style.display = 'flex';
                } else {
                    badge.style.display = 'none';
                }
            }

            if (list) {
                if (!data.notifications || data.notifications.length === 0) {
                    list.innerHTML = `<div class="notif-empty"><p>No notifications yet</p></div>`;
                } else {
                    list.innerHTML = data.notifications.map(n => `
                        <div class="notif-item ${n.read ? 'read' : 'unread'}" data-id="${n._id}">
                            <div class="notif-dot ${n.type || 'info'}"></div>
                            <div class="notif-content">
                                <div class="notif-title">${n.title}</div>
                                <div class="notif-desc">${n.message}</div>
                                <div class="notif-time">${new Date(n.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</div>
                            </div>
                            ${n.link ? `<a href="${n.link}" class="notif-link-btn" title="View"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14M12 5l7 7-7 7"/></svg></a>` : ''}
                        </div>
                    `).join('');

                    // Attach click handler to mark individual item as read
                    list.querySelectorAll('.notif-item.unread').forEach(item => {
                        item.addEventListener('click', async () => {
                            const id = item.dataset.id;
                            await fetch(`${API_BASE_URL}/notifications/${id}/read`, {
                                method: 'POST',
                                headers: getAuthHeaders(true)
                            });
                            item.classList.remove('unread');
                            item.classList.add('read');
                            fetchNotifications();
                        });
                    });
                }
            }
        } catch (err) {
            console.error('Failed to load notifications:', err);
        }
    }

    bellBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        dropdown.classList.toggle('active');
        if (dropdown.classList.contains('active')) {
            fetchNotifications();
        }
    });

    document.addEventListener('click', (e) => {
        if (dropdown && !dropdown.contains(e.target) && !bellBtn.contains(e.target)) {
            dropdown.classList.remove('active');
        }
    });

    const markAllBtn = document.getElementById('notifMarkAllRead');
    if (markAllBtn) {
        markAllBtn.addEventListener('click', async () => {
            await fetch(`${API_BASE_URL}/notifications/mark-all-read`, {
                method: 'POST',
                headers: getAuthHeaders(true)
            });
            fetchNotifications();
            showToast('All notifications marked as read', 'info');
        });
    }

    const clearBtn = document.getElementById('notifClearAll');
    if (clearBtn) {
        clearBtn.addEventListener('click', async () => {
            await fetch(`${API_BASE_URL}/notifications/clear`, {
                method: 'DELETE',
                headers: getAuthHeaders(true)
            });
            fetchNotifications();
            showToast('Notification center cleared', 'info');
        });
    }

    // Initial fetch
    fetchNotifications();
    // Poll every 45s for updates
    setInterval(fetchNotifications, 45000);
}

// 9. Global Navigation Injection (Sidebar & Topbar)
function renderAppShell(activePage) {
    const user = getUser();
    const token = getToken();

    // Check if on protected page without auth
    if (!token && activePage !== 'landing' && activePage !== 'login' && activePage !== 'signup' && activePage !== 'intelligence' && activePage !== 'result') {
        window.location.href = 'login.html';
        return;
    }

    // Sidebar Container
    const sidebarEl = document.getElementById('appSidebar');
    if (sidebarEl) {
        const collapsedState = localStorage.getItem('sidebar_collapsed') === 'true';
        if (collapsedState) sidebarEl.classList.add('collapsed');

        sidebarEl.innerHTML = `
            <div class="sidebar-header">
                <a href="dashboard.html" class="sidebar-brand">
                    <div class="brand-shield">
                        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
                    </div>
                    <span class="brand-name">ScamGuard<span class="brand-ai">AI</span></span>
                </a>
                <button class="sidebar-toggle-btn" id="sidebarCollapseBtn" title="Toggle Sidebar">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 18 9 12 15 6"/></svg>
                </button>
            </div>

            <div class="sidebar-cta">
                <a href="analyze.html" class="btn btn-primary btn-block sidebar-scan-btn">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/><path d="M11 8v6M8 11h6"/></svg>
                    <span>Analyze Offer</span>
                </a>
            </div>

            <nav class="sidebar-nav">
                <div class="nav-section-label">MAIN MODULES</div>
                <a href="dashboard.html" class="sidebar-nav-item ${activePage === 'dashboard' ? 'active' : ''}">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>
                    <span>Overview</span>
                </a>
                <a href="analyze.html" class="sidebar-nav-item ${activePage === 'analyze' ? 'active' : ''}">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
                    <span>Analyze</span>
                </a>
                <a href="history.html" class="sidebar-nav-item ${activePage === 'history' ? 'active' : ''}">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                    <span>Analysis History</span>
                </a>
                <a href="saved.html" class="sidebar-nav-item ${activePage === 'saved' ? 'active' : ''}">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m19 21-7-4-7 4V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16z"/></svg>
                    <span>Saved Reports</span>
                </a>
                <a href="intelligence.html" class="sidebar-nav-item ${activePage === 'intelligence' ? 'active' : ''}">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/></svg>
                    <span>Scam Intelligence</span>
                </a>

                <div class="nav-section-label">ACCOUNT & SYSTEM</div>
                <a href="profile.html" class="sidebar-nav-item ${activePage === 'profile' ? 'active' : ''}">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
                    <span>Profile</span>
                </a>
                <a href="settings.html" class="sidebar-nav-item ${activePage === 'settings' ? 'active' : ''}">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
                    <span>Settings</span>
                </a>
            </nav>

            <div class="sidebar-user-footer">
                <a href="profile.html" class="user-pill-link">
                    ${renderAvatarElement(user, 'avatar-sm')}
                    <div class="user-pill-meta">
                        <span class="user-pill-name">${user?.username || 'Security Analyst'}</span>
                        <span class="user-pill-status">Active Guard</span>
                    </div>
                </a>
                <button class="user-logout-icon-btn" id="sidebarLogoutBtn" title="Logout">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
                </button>
            </div>
        `;

        // Toggle sidebar collapse
        const collapseBtn = sidebarEl.querySelector('#sidebarCollapseBtn');
        if (collapseBtn) {
            collapseBtn.addEventListener('click', () => {
                sidebarEl.classList.toggle('collapsed');
                localStorage.setItem('sidebar_collapsed', sidebarEl.classList.contains('collapsed'));
            });
        }

        const logoutBtn = sidebarEl.querySelector('#sidebarLogoutBtn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', (e) => {
                e.preventDefault();
                showConfirmModal({
                    title: 'Confirm Logout',
                    message: 'Are you sure you want to end your current cybersecurity analyst session?',
                    confirmText: 'Sign Out',
                    confirmClass: 'btn-danger',
                    onConfirm: logout
                });
            });
        }
    }

    // Topbar Container
    const topbarEl = document.getElementById('appTopbar');
    if (topbarEl) {
        topbarEl.innerHTML = `
            <div class="topbar-left">
                <button class="mobile-drawer-toggle" id="mobileDrawerToggle" aria-label="Open navigation menu">
                    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
                </button>
                <button class="topbar-search-btn" id="topbarSearchTrigger">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
                    <span>Search or jump to...</span>
                    <span class="topbar-kbd">Ctrl K</span>
                </button>
            </div>

            <div class="topbar-right">
                <!-- Notifications Center -->
                <div class="notif-bell-wrap">
                    <button class="icon-btn" id="notifBellBtn" title="Notifications" aria-label="Notifications">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>
                        <span class="notif-badge" id="notifBadge" style="display:none">0</span>
                    </button>
                    <div class="notif-dropdown" id="notifDropdown">
                        <div class="notif-dropdown-header">
                            <h4>Security Notifications</h4>
                            <div class="notif-dropdown-actions">
                                <button id="notifMarkAllRead" class="btn-text">Mark all read</button>
                                <button id="notifClearAll" class="btn-text">Clear</button>
                            </div>
                        </div>
                        <div class="notif-list" id="notifList">
                            <div class="notif-loading"><div class="spinner"></div></div>
                        </div>
                    </div>
                </div>

                <!-- Theme Toggle Button -->
                <button class="icon-btn theme-toggle-btn" id="themeToggleBtn" title="Toggle Theme" aria-label="Toggle dark/light mode">
                    <!-- Icon populated by initTheme() -->
                </button>

                <!-- User Dropdown Pill -->
                <a href="profile.html" class="topbar-profile-pill" title="View Profile">
                    ${renderAvatarElement(user, 'avatar-xs')}
                    <span class="profile-pill-name">${user?.username || 'Analyst'}</span>
                </a>
            </div>
        `;

        // Search trigger
        const searchTrigger = topbarEl.querySelector('#topbarSearchTrigger');
        if (searchTrigger) {
            searchTrigger.addEventListener('click', () => {
                const palette = document.getElementById('cyberCommandPalette');
                if (palette) {
                    palette.classList.add('active');
                    setTimeout(() => palette.querySelector('#paletteSearchInput')?.focus(), 50);
                }
            });
        }

        // Mobile drawer toggle
        const drawerToggle = topbarEl.querySelector('#mobileDrawerToggle');
        if (drawerToggle && sidebarEl) {
            drawerToggle.addEventListener('click', () => {
                sidebarEl.classList.toggle('drawer-open');
                let backdrop = document.getElementById('sidebarBackdrop');
                if (!backdrop) {
                    backdrop = document.createElement('div');
                    backdrop.id = 'sidebarBackdrop';
                    backdrop.className = 'sidebar-backdrop';
                    document.body.appendChild(backdrop);
                    backdrop.addEventListener('click', () => {
                        sidebarEl.classList.remove('drawer-open');
                        backdrop.classList.remove('active');
                    });
                }
                backdrop.classList.toggle('active', sidebarEl.classList.contains('drawer-open'));
            });
        }

        // Theme toggle listener
        const themeBtn = topbarEl.querySelector('#themeToggleBtn');
        if (themeBtn) {
            themeBtn.addEventListener('click', toggleTheme);
        }
    }

    // Mobile Bottom Navigation Bar
    let mobileNav = document.getElementById('appMobileNav');
    if (!mobileNav && sidebarEl) {
        mobileNav = document.createElement('div');
        mobileNav.id = 'appMobileNav';
        mobileNav.className = 'app-mobile-nav';
        mobileNav.innerHTML = `
            <a href="dashboard.html" class="mobile-nav-item ${activePage === 'dashboard' ? 'active' : ''}">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>
                <span>Dashboard</span>
            </a>
            <a href="analyze.html" class="mobile-nav-item ${activePage === 'analyze' ? 'active' : ''}">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
                <span>Analyze</span>
            </a>
            <a href="history.html" class="mobile-nav-item ${activePage === 'history' ? 'active' : ''}">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                <span>History</span>
            </a>
            <a href="intelligence.html" class="mobile-nav-item ${activePage === 'intelligence' ? 'active' : ''}">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/></svg>
                <span>Intel</span>
            </a>
            <a href="profile.html" class="mobile-nav-item ${activePage === 'profile' ? 'active' : ''}">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
                <span>Profile</span>
            </a>
        `;
        document.body.appendChild(mobileNav);
    }

    // Refresh profile in background if stale
    if (token) {
        fetch(`${API_BASE_URL}/auth/me`, { headers: getAuthHeaders(true) })
            .then(res => res.ok ? res.json() : null)
            .then(freshUser => {
                if (freshUser) {
                    setUser(freshUser);
                }
            })
            .catch(() => {});
    }

    initNotifications();
    setupCommandPalette();
    initTheme();

    // Automatically mount CaseAI assistant for authenticated users
    if (token && !document.getElementById('caseAiScript')) {
        const s = document.createElement('script');
        s.id = 'caseAiScript';
        s.src = 'case_ai.js';
        document.body.appendChild(s);
    }
}

// Automatically init theme on parse to avoid flash
initTheme();

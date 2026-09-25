/**
 * Profile Controller
 * Manages profile tabs, avatar upload/remove, credentials change,
 * activity history log, system preferences, data export, and account deletion.
 */

document.addEventListener('DOMContentLoaded', async () => {
    renderAppShell('profile');
    if (!requireAuth()) return;

    setupTabs();
    setupPasswordMeter();
    setupPasswordToggles();
    setupAvatarHandling();

    await loadProfileData();
    await loadPreferences();
    await loadActivityLog();

    setupFormSubmissions();
    setupDestructiveActions();
});

// 1. Tab Switching
function setupTabs() {
    const tabButtons = document.querySelectorAll('#profileTabs .cyber-tab-btn');
    const tabPanels = document.querySelectorAll('.cyber-tab-panel');

    tabButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const target = btn.dataset.tab;
            tabButtons.forEach(b => b.classList.remove('active'));
            tabPanels.forEach(p => p.classList.remove('active'));

            btn.classList.add('active');
            document.getElementById(`tab-${target}`)?.classList.add('active');
        });
    });

    // Quick edit button navigates to edit tab
    document.getElementById('quickEditBtn')?.addEventListener('click', () => {
        tabButtons.forEach(b => b.classList.toggle('active', b.dataset.tab === 'edit'));
        tabPanels.forEach(p => p.classList.toggle('active', p.id === 'tab-edit'));
    });
}

// 2. Load Profile Data
async function loadProfileData() {
    try {
        const res = await fetch(`${API_BASE_URL}/auth/profile`, { headers: getAuthHeaders(true) });
        if (!res.ok) {
            if (res.status === 401) logout();
            return;
        }

        const data = await res.json();
        setUser(data);

        // Header info
        document.getElementById('profileHeaderName').textContent = data.username || 'Analyst';
        document.getElementById('profileHeaderEmail').textContent = data.email || '';

        const createdStr = data.created_at ? new Date(data.created_at).toLocaleDateString([], { year: 'numeric', month: 'short', day: 'numeric' }) : 'Verified';
        const loginStr = data.last_login ? new Date(data.last_login).toLocaleDateString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : 'Active now';

        document.getElementById('profileMemberSince').textContent = createdStr;
        document.getElementById('profileLastLogin').textContent = loginStr;

        // Render Avatar
        renderHeaderAvatar(data);

        // Meta Tab info
        document.getElementById('metaUsername').textContent = data.username || '--';
        document.getElementById('metaEmail').textContent = data.email || '--';
        document.getElementById('metaCreated').textContent = createdStr;
        document.getElementById('metaLogin').textContent = loginStr;

        // Stats
        if (data.stats) {
            document.getElementById('overviewTotalScans').textContent = data.stats.total_analyses ?? 0;
            document.getElementById('overviewHighRisk').textContent = data.stats.high_risk_detected ?? 0;
            document.getElementById('overviewSavedCount').textContent = data.stats.saved_reports ?? 0;
        }

        // Form fields
        document.getElementById('editUsername').value = data.username || '';
        document.getElementById('editEmail').value = data.email || '';

    } catch (err) {
        console.error('Failed to load profile:', err);
    }
}

function renderHeaderAvatar(user) {
    const wrap = document.getElementById('profileHeaderAvatar');
    const removeBtn = document.getElementById('removeAvatarBtn');
    if (!wrap) return;

    const initials = getInitials(user?.username || 'Analyst');
    if (user?.avatar_url) {
        wrap.innerHTML = `<img src="${user.avatar_url}" alt="${user.username}" class="user-avatar-img avatar-lg" onerror="this.outerHTML='<div class=\\'user-avatar-initials avatar-lg\\'>${initials}</div>'">`;
        if (removeBtn) removeBtn.style.display = 'inline-block';
    } else {
        wrap.innerHTML = `<div class="user-avatar-initials avatar-lg">${initials}</div>`;
        if (removeBtn) removeBtn.style.display = 'none';
    }
}

// 3. Avatar Handling
function setupAvatarHandling() {
    const fileInput = document.getElementById('avatarFileInput');
    const removeBtn = document.getElementById('removeAvatarBtn');

    fileInput?.addEventListener('change', async () => {
        const file = fileInput.files[0];
        if (!file) return;

        if (!['image/png', 'image/jpeg', 'image/webp'].includes(file.type)) {
            showToast('Invalid image format. Allowed: PNG, JPG, WEBP', 'danger');
            return;
        }

        if (file.size > 3 * 1024 * 1024) {
            showToast('Image size exceeds 3MB limit.', 'danger');
            return;
        }

        const formData = new FormData();
        formData.append('avatar', file);

        try {
            showToast('Uploading profile photo...', 'info', 2000);
            const res = await fetch(`${API_BASE_URL}/auth/avatar`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${getToken()}` },
                body: formData
            });
            const data = await res.json();

            if (!res.ok) throw new Error(data.error || 'Upload failed');

            showToast('Avatar updated successfully!', 'success');
            await loadProfileData();

        } catch (err) {
            showToast(err.message, 'danger');
        }
    });

    removeBtn?.addEventListener('click', async () => {
        showConfirmModal({
            title: 'Remove Profile Photo',
            message: 'Revert to automatic initials avatar?',
            confirmText: 'Remove Photo',
            confirmClass: 'btn-outline',
            onConfirm: async () => {
                try {
                    const res = await fetch(`${API_BASE_URL}/auth/avatar`, {
                        method: 'DELETE',
                        headers: getAuthHeaders(true)
                    });
                    if (res.ok) {
                        showToast('Photo removed. Initial avatar restored.', 'info');
                        await loadProfileData();
                    }
                } catch (err) {
                    showToast('Failed to remove photo.', 'danger');
                }
            }
        });
    });
}

// 4. Form Submissions
function setupFormSubmissions() {
    // Edit Profile
    const editForm = document.getElementById('editProfileForm');
    editForm?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('editUsername').value.trim();
        const email = document.getElementById('editEmail').value.trim();

        const btn = document.getElementById('saveProfileBtn');
        const text = document.getElementById('saveProfileText');
        const spinner = document.getElementById('saveProfileSpinner');

        btn.disabled = true;
        text.style.display = 'none';
        spinner.style.display = 'inline-block';

        try {
            const res = await fetch(`${API_BASE_URL}/auth/profile`, {
                method: 'PUT',
                headers: getAuthHeaders(true),
                body: JSON.stringify({ username, email })
            });
            const data = await res.json();

            if (!res.ok) throw new Error(data.error || 'Failed to update profile');

            showToast('Profile information saved successfully!', 'success');
            await loadProfileData();

        } catch (err) {
            showToast(err.message, 'danger');
        } finally {
            btn.disabled = false;
            text.style.display = 'inline';
            spinner.style.display = 'none';
        }
    });

    // Cancel Edit Profile
    document.getElementById('cancelEditProfileBtn')?.addEventListener('click', () => {
        const overviewBtn = document.querySelector('#profileTabs button[data-tab="overview"]');
        overviewBtn?.click();
    });

    // Change Password
    const passForm = document.getElementById('changePasswordForm');
    passForm?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const old_password = document.getElementById('currentPassword').value;
        const new_password = document.getElementById('newPassword').value;
        const confirm_password = document.getElementById('confirmNewPassword').value;

        if (new_password !== confirm_password) {
            showToast('New passwords do not match.', 'danger');
            return;
        }

        const btn = document.getElementById('changePasswordBtn');
        const text = document.getElementById('changePassText');
        const spinner = document.getElementById('changePassSpinner');

        btn.disabled = true;
        text.style.display = 'none';
        spinner.style.display = 'inline-block';

        try {
            const res = await fetch(`${API_BASE_URL}/auth/change-password`, {
                method: 'POST',
                headers: getAuthHeaders(true),
                body: JSON.stringify({ old_password, new_password })
            });
            const data = await res.json();

            if (!res.ok) throw new Error(data.error || 'Password update failed');

            showToast('Password updated successfully!', 'success');
            passForm.reset();
            document.getElementById('newPassMeter').style.width = '0%';
            document.querySelectorAll('#newPassRules li').forEach(li => {
                li.classList.remove('valid');
                li.querySelector('span').textContent = '○';
            });

        } catch (err) {
            showToast(err.message, 'danger');
        } finally {
            btn.disabled = false;
            text.style.display = 'inline';
            spinner.style.display = 'none';
        }
    });

    // Preferences
    const prefsForm = document.getElementById('preferencesForm');
    prefsForm?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const theme = document.querySelector('input[name="prefTheme"]:checked')?.value || 'dark';
        const analysis_notifications = document.getElementById('prefAnalysisNotifs').checked;
        const security_notifications = document.getElementById('prefSecurityNotifs').checked;
        const email_notifications = document.getElementById('prefEmailNotifs').checked;
        const default_mode = document.getElementById('prefDefaultMode').value;

        try {
            const res = await fetch(`${API_BASE_URL}/auth/preferences`, {
                method: 'PUT',
                headers: getAuthHeaders(true),
                body: JSON.stringify({
                    theme,
                    analysis_notifications,
                    security_notifications,
                    email_notifications,
                    default_mode
                })
            });

            if (res.ok) {
                applyTheme(theme);
                showToast('System preferences saved!', 'success');
            } else {
                throw new Error('Failed to save preferences');
            }
        } catch (err) {
            showToast(err.message, 'danger');
        }
    });
}

// 5. Password Strength Meter
function setupPasswordMeter() {
    const input = document.getElementById('newPassword');
    const meter = document.getElementById('newPassMeter');
    const rules = {
        length: document.getElementById('rule-p-length'),
        upper: document.getElementById('rule-p-upper'),
        lower: document.getElementById('rule-p-lower'),
        number: document.getElementById('rule-p-number'),
        special: document.getElementById('rule-p-special')
    };

    if (!input) return;

    input.addEventListener('input', () => {
        const val = input.value;
        const results = {
            length: val.length >= 8,
            upper: /[A-Z]/.test(val),
            lower: /[a-z]/.test(val),
            number: /\d/.test(val),
            special: /[@$!%*?&#^()_+\-=\[\]{};:\'",.<>\/]/.test(val)
        };

        let count = 0;
        for (const [k, ok] of Object.entries(results)) {
            if (ok) {
                count++;
                rules[k].classList.add('valid');
                rules[k].querySelector('span').textContent = '●';
            } else {
                rules[k].classList.remove('valid');
                rules[k].querySelector('span').textContent = '○';
            }
        }

        const pct = (count / 5) * 100;
        meter.style.width = `${pct}%`;
        if (pct <= 20) meter.style.backgroundColor = '#ef4444';
        else if (pct <= 60) meter.style.backgroundColor = '#f59e0b';
        else if (pct <= 80) meter.style.backgroundColor = '#38bdf8';
        else meter.style.backgroundColor = '#10b981';
    });
}

function setupPasswordToggles() {
    document.querySelectorAll('.pwd-toggle').forEach(btn => {
        btn.addEventListener('click', () => {
            const targetId = btn.dataset.target;
            const input = document.getElementById(targetId);
            if (!input) return;
            const isPass = input.type === 'password';
            input.type = isPass ? 'text' : 'password';
            btn.style.color = isPass ? 'var(--accent-cyan)' : 'var(--text-muted)';
        });
    });
}

// 6. Activity Log
async function loadActivityLog() {
    const container = document.getElementById('activityLogContainer');
    if (!container) return;

    try {
        const res = await fetch(`${API_BASE_URL}/auth/activity`, { headers: getAuthHeaders(true) });
        if (!res.ok) return;

        const data = await res.json();
        const logs = data.activity || [];

        if (logs.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">📜</div>
                    <div class="empty-title">No audit activity recorded</div>
                    <p class="empty-desc">Your session authentications, scan creation, and security events will log here.</p>
                </div>
            `;
            return;
        }

        container.innerHTML = logs.map(l => {
            const timeStr = l.created_at ? new Date(l.created_at).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' }) : 'Recent';
            return `
                <div class="activity-row">
                    <div>
                        <div class="activity-action">${formatActionTitle(l.action)}</div>
                        <div class="activity-details">${l.details || 'System event'}</div>
                    </div>
                    <div class="activity-time">${timeStr}</div>
                </div>
            `;
        }).join('');

    } catch (err) {
        console.error('Failed to load activity logs:', err);
    }
}

function formatActionTitle(action) {
    if (!action) return 'Security Event';
    return action.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
}

document.getElementById('refreshActivityBtn')?.addEventListener('click', loadActivityLog);

// 7. Preferences Loading
async function loadPreferences() {
    try {
        const res = await fetch(`${API_BASE_URL}/auth/preferences`, { headers: getAuthHeaders(true) });
        if (!res.ok) return;
        const prefs = await res.json();

        // Theme
        const themeRadio = document.querySelector(`input[name="prefTheme"][value="${prefs.theme || 'dark'}"]`);
        if (themeRadio) themeRadio.checked = true;

        // Checkboxes
        const notifA = document.getElementById('prefAnalysisNotifs');
        if (notifA) notifA.checked = prefs.analysis_notifications !== false;

        const notifS = document.getElementById('prefSecurityNotifs');
        if (notifS) notifS.checked = prefs.security_notifications !== false;

        const notifE = document.getElementById('prefEmailNotifs');
        if (notifE) notifE.checked = prefs.email_notifications !== false;

        const defMode = document.getElementById('prefDefaultMode');
        if (defMode && prefs.default_mode) defMode.value = prefs.default_mode;

    } catch (err) {
        console.error('Failed to load preferences:', err);
    }
}

// 8. Destructive Actions & Data Export
function setupDestructiveActions() {
    // Logout from all sessions
    document.getElementById('logoutAllSessionsBtn')?.addEventListener('click', () => {
        showConfirmModal({
            title: 'Terminate All Active Sessions',
            message: 'This will invalidate current access tokens across all devices.',
            confirmText: 'Sign Out All Devices',
            confirmClass: 'btn-danger',
            onConfirm: async () => {
                try {
                    await fetch(`${API_BASE_URL}/auth/logout-all`, {
                        method: 'POST',
                        headers: getAuthHeaders(true)
                    });
                    logout();
                } catch (err) {
                    showToast('Failed to terminate sessions.', 'danger');
                }
            }
        });
    });

    // Export Data JSON
    document.getElementById('exportDataBtn')?.addEventListener('click', async () => {
        try {
            showToast('Generating GDPR data export archive...', 'info', 3000);
            const res = await fetch(`${API_BASE_URL}/auth/export-data`, { headers: getAuthHeaders(true) });
            if (!res.ok) throw new Error('Data export failed');

            const blob = await res.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = `scamguard_export_${Date.now()}.json`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            showToast('Personal archive downloaded successfully!', 'success');

        } catch (err) {
            showToast(err.message, 'danger');
        }
    });

    // Clear History
    document.getElementById('clearHistoryBtn')?.addEventListener('click', () => {
        showConfirmModal({
            title: 'Purge All Scan History?',
            message: 'All your previous forensic analyses and stored file metadata will be permanently deleted from the database. This action cannot be reversed.',
            confirmText: 'Purge All History',
            confirmClass: 'btn-danger',
            onConfirm: async () => {
                try {
                    const res = await fetch(`${API_BASE_URL}/dashboard/clear-history`, {
                        method: 'POST',
                        headers: getAuthHeaders(true)
                    });
                    if (res.ok) {
                        showToast('All scan history permanently cleared.', 'success');
                        await loadProfileData();
                        await loadActivityLog();
                    } else {
                        throw new Error('Failed to clear history');
                    }
                } catch (err) {
                    showToast(err.message, 'danger');
                }
            }
        });
    });

    // Delete Account Modal
    const deleteModal = document.getElementById('deleteAccountModal');
    const deleteBtn = document.getElementById('deleteAccountBtn');
    const cancelModal = document.getElementById('cancelDeleteModal');
    const closeModal = document.getElementById('closeDeleteModal');
    const confirmDeleteBtn = document.getElementById('confirmPermanentDeleteBtn');
    const pwdInput = document.getElementById('deleteConfirmPassword');

    deleteBtn?.addEventListener('click', () => {
        deleteModal?.classList.add('active');
        pwdInput.value = '';
    });

    const closeDelete = () => deleteModal?.classList.remove('active');
    cancelModal?.addEventListener('click', closeDelete);
    closeModal?.addEventListener('click', closeDelete);

    confirmDeleteBtn?.addEventListener('click', async () => {
        const password = pwdInput.value.trim();
        if (!password) {
            showToast('Please enter your password to confirm.', 'danger');
            return;
        }

        try {
            confirmDeleteBtn.disabled = true;
            const res = await fetch(`${API_BASE_URL}/auth/delete-account`, {
                method: 'POST',
                headers: getAuthHeaders(true),
                body: JSON.stringify({ password })
            });
            const data = await res.json();

            if (!res.ok) throw new Error(data.error || 'Failed to delete account');

            closeDelete();
            showToast('Account permanently deleted. Farewell.', 'info', 4000);
            localStorage.clear();
            setTimeout(() => { window.location.href = 'index.html'; }, 800);

        } catch (err) {
            showToast(err.message, 'danger');
        } finally {
            confirmDeleteBtn.disabled = false;
        }
    });
}

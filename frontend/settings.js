/**
 * Settings Controller - Security Center & Platform Preferences
 * Handles theme switching, notification preferences, active session management,
 * email verification status, data retention, and account deletion.
 */

document.addEventListener('DOMContentLoaded', async () => {
    renderAppShell('settings');
    if (!requireAuth()) return;

    setupThemeSelectors();
    await loadSecurityCenter();
    await loadNotificationPreferences();
    setupPasswordForm();
    setupNotificationForm();
    setupPrivacyActions();
});

function setupThemeSelectors() {
    const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
    const darkRadio = document.querySelector('input[name="settingsTheme"][value="dark"]');
    const lightRadio = document.querySelector('input[name="settingsTheme"][value="light"]');

    if (currentTheme === 'light' && lightRadio) {
        lightRadio.checked = true;
        updateThemeCardBorders('light');
    } else if (darkRadio) {
        darkRadio.checked = true;
        updateThemeCardBorders('dark');
    }

    document.querySelectorAll('input[name="settingsTheme"]').forEach(radio => {
        radio.addEventListener('change', () => {
            const chosen = radio.value;
            applyTheme(chosen);
            updateThemeCardBorders(chosen);

            fetch(`${API_BASE_URL}/auth/preferences`, {
                method: 'PUT',
                headers: getAuthHeaders(true),
                body: JSON.stringify({ theme: chosen })
            }).catch(() => {});

            showToast(`Theme switched to ${chosen} mode`, 'info');
        });
    });
}

function updateThemeCardBorders(theme) {
    const darkCard = document.getElementById('themeOptionDark');
    const lightCard = document.getElementById('themeOptionLight');

    if (theme === 'dark') {
        if (darkCard) darkCard.style.borderColor = 'var(--accent-cyan)';
        if (lightCard) lightCard.style.borderColor = 'var(--border-subtle)';
    } else {
        if (lightCard) lightCard.style.borderColor = 'var(--accent-cyan)';
        if (darkCard) darkCard.style.borderColor = 'var(--border-subtle)';
    }
}

async function loadSecurityCenter() {
    try {
        // Load user info for email verification status
        const userRes = await fetch(`${API_BASE_URL}/auth/me`, { headers: getAuthHeaders(true) });
        if (userRes.ok) {
            const userData = await userRes.json();
            const user = userData.user || userData;
            const isVerified = user.email_verified === true;

            const badge = document.getElementById('emailVerifiedBadge');
            const verifyTitle = document.getElementById('verifyStatusTitle');
            const verifyDesc = document.getElementById('verifyStatusDesc');
            const resendBtn = document.getElementById('resendVerifyBtn');

            if (isVerified) {
                if (badge) {
                    badge.textContent = 'EMAIL VERIFIED';
                    badge.className = 'badge badge-success';
                }
                if (verifyTitle) verifyTitle.textContent = 'Email Verified';
                if (verifyDesc) verifyDesc.textContent = `Your address (${user.email}) is verified for forensic dispatches and threat alerts.`;
                if (resendBtn) resendBtn.style.display = 'none';
            } else {
                if (badge) {
                    badge.textContent = 'VERIFICATION REQUIRED';
                    badge.className = 'badge badge-warning';
                }
                if (verifyTitle) verifyTitle.textContent = 'Email Verification Pending';
                if (verifyDesc) verifyDesc.textContent = `Please verify your email address (${user.email}) to unlock full forensic delivery capabilities.`;
                if (resendBtn) {
                    resendBtn.style.display = 'inline-block';
                    resendBtn.onclick = async () => {
                        try {
                            resendBtn.disabled = true;
                            resendBtn.textContent = 'Sending...';
                            const res = await fetch(`${API_BASE_URL}/auth/resend-verification`, {
                                method: 'POST',
                                headers: getAuthHeaders(true)
                            });
                            const data = await res.json();
                            if (res.ok) {
                                showToast(data.message || 'Verification link sent!', 'success');
                            } else {
                                showToast(data.error?.message || data.error || 'Failed to resend verification.', 'danger');
                            }
                        } catch (err) {
                            showToast(err.message, 'danger');
                        } finally {
                            resendBtn.disabled = false;
                            resendBtn.textContent = 'Resend Verification Link';
                        }
                    };
                }
            }
        }

        // Load active sessions
        await loadActiveSessions();

    } catch (err) {
        console.error('Failed to load security center:', err);
    }
}

async function loadActiveSessions() {
    const listEl = document.getElementById('sessionsList');
    if (!listEl) return;

    try {
        const res = await fetch(`${API_BASE_URL}/auth/sessions`, { headers: getAuthHeaders(true) });
        if (!res.ok) {
            listEl.innerHTML = '<div style="padding: 0.5rem; font-size: 0.85rem; color: var(--text-muted);">Session telemetry unavailable.</div>';
            return;
        }

        const data = await res.json();
        const sessions = data.sessions || [];

        if (sessions.length === 0) {
            listEl.innerHTML = '<div style="padding: 0.5rem; font-size: 0.85rem; color: var(--text-muted);">No active sessions found.</div>';
            return;
        }

        listEl.innerHTML = sessions.map(s => {
            const isCurrent = s.is_current ? true : false;
            const deviceName = `${s.browser || 'Browser'} on ${s.os || 'OS'}`;
            const timeAgo = s.last_seen ? new Date(s.last_seen).toLocaleString() : 'Active now';

            return `
                <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.75rem 1rem; background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: var(--radius-sm);">
                    <div>
                        <div style="display: flex; align-items: center; gap: 0.5rem;">
                            <strong style="font-size: 0.9rem;">${deviceName}</strong>
                            ${isCurrent ? '<span class="badge badge-primary" style="font-size: 0.7rem; padding: 2px 6px;">CURRENT SESSION</span>' : ''}
                        </div>
                        <small style="color: var(--text-muted); font-size: 0.78rem;">IP: ${s.ip_address || 'Protected'} • Last Active: ${timeAgo}</small>
                    </div>
                    ${!isCurrent ? `
                        <button class="btn btn-outline btn-sm" onclick="revokeSingleSession('${s.session_id}')" style="font-size: 0.75rem; padding: 3px 8px; color: var(--risk-danger);">
                            Revoke
                        </button>
                    ` : '<span style="font-size: 0.78rem; color: var(--accent-cyan);">● Active Now</span>'}
                </div>
            `;
        }).join('');

        // Wire Revoke Others button
        const revokeOthersBtn = document.getElementById('revokeOthersBtn');
        if (revokeOthersBtn) {
            revokeOthersBtn.onclick = () => {
                showConfirmModal({
                    title: 'Sign Out Other Sessions',
                    message: 'Terminate all active logins on other devices and browsers? You will remain logged in on this browser.',
                    confirmText: 'Sign Out Others',
                    confirmClass: 'btn-danger',
                    onConfirm: async () => {
                        try {
                            const revRes = await fetch(`${API_BASE_URL}/auth/sessions/revoke-others`, {
                                method: 'POST',
                                headers: getAuthHeaders(true)
                            });
                            if (revRes.ok) {
                                showToast('Other active sessions revoked.', 'success');
                                await loadActiveSessions();
                            } else {
                                showToast('Failed to revoke other sessions.', 'danger');
                            }
                        } catch (err) {
                            showToast(err.message, 'danger');
                        }
                    }
                });
            };
        }

    } catch (err) {
        listEl.innerHTML = '<div style="padding: 0.5rem; font-size: 0.85rem; color: var(--text-muted);">Error loading sessions.</div>';
    }
}

window.revokeSingleSession = async function(sessionId) {
    try {
        const res = await fetch(`${API_BASE_URL}/auth/sessions/revoke/${sessionId}`, {
            method: 'POST',
            headers: getAuthHeaders(true)
        });
        if (res.ok) {
            showToast('Session revoked successfully.', 'success');
            await loadActiveSessions();
        } else {
            showToast('Failed to revoke session.', 'danger');
        }
    } catch (err) {
        showToast(err.message, 'danger');
    }
};

function setupPasswordForm() {
    const form = document.getElementById('settingsPasswordForm');
    form?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const current_password = document.getElementById('settingsCurrentPwd').value;
        const new_password = document.getElementById('settingsNewPwd').value;

        try {
            const res = await fetch(`${API_BASE_URL}/auth/change-password`, {
                method: 'POST',
                headers: getAuthHeaders(true),
                body: JSON.stringify({ current_password, new_password })
            });
            const data = await res.json();
            if (res.ok) {
                showToast('Password updated successfully! All other sessions terminated.', 'success');
                form.reset();
                await loadActiveSessions();
            } else {
                showToast(data.error?.message || data.error || 'Failed to update password.', 'danger');
            }
        } catch (err) {
            showToast(err.message, 'danger');
        }
    });
}

async function loadNotificationPreferences() {
    try {
        const res = await fetch(`${API_BASE_URL}/auth/notification-preferences`, {
            headers: getAuthHeaders(true)
        });
        if (!res.ok) return;

        const data = await res.json();
        const prefs = data.notification_preferences || {};

        const notifA = document.getElementById('settingNotifAnalysis');
        const notifH = document.getElementById('settingNotifHighRisk');
        const notifS = document.getElementById('settingNotifSecurity');
        const notifU = document.getElementById('settingNotifUpdates');

        if (notifA) notifA.checked = prefs.analysis_completed !== false;
        if (notifH) notifH.checked = prefs.high_risk_alerts !== false;
        if (notifS) notifS.checked = prefs.security_alerts !== false;
        if (notifU) notifU.checked = prefs.product_updates === true;

    } catch (err) {
        console.error('Failed to load notification preferences:', err);
    }
}

function setupNotificationForm() {
    const form = document.getElementById('settingsNotifForm');
    form?.addEventListener('submit', async (e) => {
        e.preventDefault();

        const analysis_completed = document.getElementById('settingNotifAnalysis')?.checked ?? true;
        const high_risk_alerts = document.getElementById('settingNotifHighRisk')?.checked ?? true;
        const security_alerts = document.getElementById('settingNotifSecurity')?.checked ?? true;
        const product_updates = document.getElementById('settingNotifUpdates')?.checked ?? false;

        try {
            const res = await fetch(`${API_BASE_URL}/auth/notification-preferences`, {
                method: 'PUT',
                headers: getAuthHeaders(true),
                body: JSON.stringify({
                    analysis_completed,
                    high_risk_alerts,
                    security_alerts,
                    product_updates
                })
            });

            if (res.ok) {
                showToast('Notification preferences saved successfully!', 'success');
            } else {
                throw new Error('Failed to update notification preferences');
            }
        } catch (err) {
            showToast(err.message, 'danger');
        }
    });
}

function setupPrivacyActions() {
    // Export Data
    document.getElementById('settingsExportBtn')?.addEventListener('click', async () => {
        try {
            showToast('Generating personal GDPR archive...', 'info', 3000);
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
            showToast('Personal archive downloaded!', 'success');
        } catch (err) {
            showToast(err.message, 'danger');
        }
    });

    // Delete All My Analysis Data
    document.getElementById('settingsDeleteDataBtn')?.addEventListener('click', () => {
        showConfirmModal({
            title: 'Delete All Analysis Records',
            message: 'Permanently delete all your uploaded documents, OCR files, and forensic analysis history? This action is irreversible.',
            confirmText: 'Delete All Data',
            confirmClass: 'btn-danger',
            onConfirm: async () => {
                try {
                    const res = await fetch(`${API_BASE_URL}/auth/delete-all-data`, {
                        method: 'POST',
                        headers: getAuthHeaders(true)
                    });
                    const data = await res.json();
                    if (res.ok) {
                        showToast(data.message || 'All personal analysis records purged.', 'success');
                    } else {
                        showToast(data.error?.message || data.error || 'Failed to delete data.', 'danger');
                    }
                } catch (err) {
                    showToast(err.message, 'danger');
                }
            }
        });
    });

    // Delete Account
    document.getElementById('deleteAccountBtn')?.addEventListener('click', () => {
        showConfirmModal({
            title: 'Delete ScamGuard Account',
            message: 'Are you sure you want to permanently delete your account? All forensic dossiers, saved reports, active sessions, and personal files will be purged immediately.',
            confirmText: 'Permanently Delete Account',
            confirmClass: 'btn-danger',
            onConfirm: async () => {
                try {
                    const res = await fetch(`${API_BASE_URL}/auth/delete-account`, {
                        method: 'DELETE',
                        headers: getAuthHeaders(true)
                    });
                    if (res.ok) {
                        showToast('Account successfully deleted.', 'info');
                        setTimeout(logout, 1500);
                    } else {
                        const data = await res.json();
                        showToast(data.error?.message || data.error || 'Failed to delete account.', 'danger');
                    }
                } catch (err) {
                    showToast(err.message, 'danger');
                }
            }
        });
    });
}

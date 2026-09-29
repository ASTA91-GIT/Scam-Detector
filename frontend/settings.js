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
    setupTwoFactorAuth();
    await setupApiAndWebhooks();
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

// ==============================================================================
// TWO-FACTOR AUTHENTICATION CONTROLLER (SECTION 12)
// ==============================================================================
function setupTwoFactorAuth() {
    const badge = document.getElementById('twoFactorBadge');
    const setupBtn = document.getElementById('setup2faBtn');
    const disableBtn = document.getElementById('disable2faBtn');
    const setupBox = document.getElementById('twoFactorSetupBox');
    const secretCodeEl = document.getElementById('twoFactorSecretCode');
    const recoveryContainer = document.getElementById('twoFactorRecoveryCodes');
    const copySecretBtn = document.getElementById('copy2faSecretBtn');
    const cancelBtn = document.getElementById('cancel2faBtn');
    const verifyForm = document.getElementById('verify2faForm');
    const verifyInput = document.getElementById('verify2faInput');

    async function refresh2faState() {
        try {
            const res = await fetch(`${API_BASE_URL}/auth/profile`, { headers: getAuthHeaders(true) });
            if (res.ok) {
                const data = await res.json();
                const is2fa = data.two_factor_enabled === true;
                if (badge) {
                    badge.textContent = is2fa ? 'ACTIVE' : 'DISABLED';
                    badge.className = is2fa ? 'badge badge-success' : 'badge badge-warning';
                }
                if (setupBtn) setupBtn.style.display = is2fa ? 'none' : 'inline-block';
                if (disableBtn) disableBtn.style.display = is2fa ? 'inline-block' : 'none';
                if (setupBox) setupBox.style.display = 'none';
            }
        } catch (e) {}
    }

    refresh2faState();

    setupBtn?.addEventListener('click', async () => {
        try {
            setupBtn.disabled = true;
            setupBtn.textContent = 'Generating Key...';
            const res = await fetch(`${API_BASE_URL}/auth/2fa/setup`, {
                method: 'POST',
                headers: getAuthHeaders(true)
            });
            const data = await res.json();
            setupBtn.disabled = false;
            setupBtn.textContent = 'Enable Two-Factor Authentication';

            if (res.ok) {
                if (secretCodeEl) secretCodeEl.textContent = data.secret;
                if (recoveryContainer) {
                    recoveryContainer.innerHTML = (data.recovery_codes || []).map(c => `<div style="padding: 3px 6px; background: rgba(255,255,255,0.05); border-radius: 3px; text-align: center;">${c}</div>`).join('');
                }
                if (setupBox) setupBox.style.display = 'block';
                if (verifyInput) verifyInput.focus();
            } else {
                showToast(data.error?.message || 'Failed to initiate 2FA setup.', 'danger');
            }
        } catch (err) {
            setupBtn.disabled = false;
            setupBtn.textContent = 'Enable Two-Factor Authentication';
            showToast(err.message, 'danger');
        }
    });

    copySecretBtn?.addEventListener('click', () => {
        if (secretCodeEl && secretCodeEl.textContent) {
            navigator.clipboard.writeText(secretCodeEl.textContent).then(() => {
                showToast('2FA secret key copied to clipboard!', 'success');
            });
        }
    });

    cancelBtn?.addEventListener('click', () => {
        if (setupBox) setupBox.style.display = 'none';
    });

    verifyForm?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const code = (verifyInput?.value || '').trim();
        if (!code || code.length !== 6) {
            showToast('Please enter a valid 6-digit code.', 'warning');
            return;
        }

        try {
            const submitBtn = verifyForm.querySelector('button[type="submit"]');
            if (submitBtn) { submitBtn.disabled = true; submitBtn.textContent = 'Verifying...'; }

            const res = await fetch(`${API_BASE_URL}/auth/2fa/verify`, {
                method: 'POST',
                headers: getAuthHeaders(true),
                body: JSON.stringify({ code })
            });
            const data = await res.json();
            if (submitBtn) { submitBtn.disabled = false; submitBtn.textContent = 'Verify & Activate'; }

            if (res.ok) {
                showToast('Two-factor authentication successfully activated!', 'success');
                refresh2faState();
            } else {
                showToast(data.error?.message || 'Invalid code. Verification failed.', 'danger');
            }
        } catch (err) {
            showToast(err.message, 'danger');
        }
    });

    disableBtn?.addEventListener('click', () => {
        const pwd = prompt('Enter your current account password to disable 2FA:');
        if (!pwd) return;

        fetch(`${API_BASE_URL}/auth/2fa/disable`, {
            method: 'POST',
            headers: getAuthHeaders(true),
            body: JSON.stringify({ password: pwd })
        }).then(async res => {
            const data = await res.json();
            if (res.ok) {
                showToast('Two-factor authentication disabled.', 'info');
                refresh2faState();
            } else {
                showToast(data.error?.message || 'Failed to disable 2FA.', 'danger');
            }
        }).catch(err => showToast(err.message, 'danger'));
    });
}

// ==============================================================================
// DEVELOPER API & WEBHOOKS CONTROLLER (SECTIONS 49 & 50)
// ==============================================================================
async function setupApiAndWebhooks() {
    const keysListEl = document.getElementById('apiKeysList');
    const webhooksListEl = document.getElementById('webhooksList');
    const genKeyBtn = document.getElementById('generateApiKeyBtn');
    const keyAlertEl = document.getElementById('apiKeyDisplayAlert');
    const keyStrEl = document.getElementById('newApiKeyString');
    const copyKeyBtn = document.getElementById('copyNewApiKeyBtn');
    const toggleWhBtn = document.getElementById('addWebhookToggleBtn');
    const whBoxEl = document.getElementById('addWebhookFormBox');
    const cancelWhBtn = document.getElementById('cancelWebhookBtn');
    const newWhForm = document.getElementById('newWebhookForm');

    // 1. Load API Keys
    async function loadApiKeys() {
        try {
            const res = await fetch('/api/v1/keys', { headers: getAuthHeaders(true) });
            if (res.ok) {
                const data = await res.json();
                const keys = data.keys || [];
                if (!keysListEl) return;
                if (keys.length === 0) {
                    keysListEl.innerHTML = `<div style="padding: 0.75rem 1rem; background: var(--bg-surface); border-radius: var(--radius-sm); font-size: 0.85rem; color: var(--text-muted);">No active API keys created yet.</div>`;
                    return;
                }
                keysListEl.innerHTML = keys.map(k => `
                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.75rem 1rem; background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: var(--radius-md);">
                        <div>
                            <strong style="font-size: 0.9rem;">${k.name}</strong>
                            <div style="font-family: monospace; font-size: 0.82rem; color: var(--accent-cyan); margin-top: 2px;">${k.prefix}</div>
                            <small style="color: var(--text-muted); font-size: 0.75rem;">Created: ${k.created_at ? new Date(k.created_at).toLocaleDateString() : 'Recent'}</small>
                        </div>
                        <button class="btn btn-outline btn-sm revoke-key-btn" data-id="${k.id}" style="color: var(--risk-danger); border-color: var(--border-subtle); font-size: 0.75rem;">Revoke</button>
                    </div>
                `).join('');

                keysListEl.querySelectorAll('.revoke-key-btn').forEach(btn => {
                    btn.addEventListener('click', async () => {
                        const kid = btn.dataset.id;
                        if (!confirm('Are you sure you want to revoke this API key? Applications using it will lose access immediately.')) return;
                        const dres = await fetch(`/api/v1/keys/${kid}`, { method: 'DELETE', headers: getAuthHeaders(true) });
                        if (dres.ok) {
                            showToast('API key revoked.', 'info');
                            loadApiKeys();
                        } else {
                            showToast('Failed to revoke key.', 'danger');
                        }
                    });
                });
            }
        } catch (e) {}
    }

    // 2. Load Webhooks
    async function loadWebhooks() {
        try {
            const res = await fetch('/api/v1/webhooks', { headers: getAuthHeaders(true) });
            if (res.ok) {
                const data = await res.json();
                const hooks = data.webhooks || [];
                if (!webhooksListEl) return;
                if (hooks.length === 0) {
                    webhooksListEl.innerHTML = `<div style="padding: 0.75rem 1rem; background: var(--bg-surface); border-radius: var(--radius-sm); font-size: 0.85rem; color: var(--text-muted);">No outbound webhooks configured.</div>`;
                    return;
                }
                webhooksListEl.innerHTML = hooks.map(h => `
                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.75rem 1rem; background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: var(--radius-md);">
                        <div>
                            <div style="font-family: monospace; font-size: 0.88rem; color: var(--text-primary);">${h.url}</div>
                            <div style="font-size: 0.75rem; color: var(--accent-cyan); margin-top: 2px;">Events: ${(h.events || []).join(', ')}</div>
                        </div>
                        <div style="display: flex; gap: 0.5rem;">
                            <button class="btn btn-outline btn-sm test-wh-btn" data-id="${h.id}" style="font-size: 0.75rem;">Test Ping</button>
                            <button class="btn btn-outline btn-sm del-wh-btn" data-id="${h.id}" style="color: var(--risk-danger); border-color: var(--border-subtle); font-size: 0.75rem;">Delete</button>
                        </div>
                    </div>
                `).join('');

                webhooksListEl.querySelectorAll('.test-wh-btn').forEach(btn => {
                    btn.addEventListener('click', async () => {
                        btn.disabled = true;
                        btn.textContent = 'Pinging...';
                        const pres = await fetch(`/api/v1/webhooks/${btn.dataset.id}/test`, { method: 'POST', headers: getAuthHeaders(true) });
                        btn.disabled = false;
                        btn.textContent = 'Test Ping';
                        if (pres.ok) {
                            showToast('Signed test webhook event dispatched successfully!', 'success');
                        } else {
                            showToast('Failed to dispatch test webhook.', 'danger');
                        }
                    });
                });

                webhooksListEl.querySelectorAll('.del-wh-btn').forEach(btn => {
                    btn.addEventListener('click', async () => {
                        if (!confirm('Delete this webhook?')) return;
                        const dres = await fetch(`/api/v1/webhooks/${btn.dataset.id}`, { method: 'DELETE', headers: getAuthHeaders(true) });
                        if (dres.ok) {
                            showToast('Webhook deleted.', 'info');
                            loadWebhooks();
                        } else {
                            showToast('Failed to delete webhook.', 'danger');
                        }
                    });
                });
            }
        } catch (e) {}
    }

    genKeyBtn?.addEventListener('click', async () => {
        const name = prompt('Enter a label for this API key (e.g., "Production Crawler", "SIEM Connector"):', 'Production Key');
        if (!name) return;

        try {
            genKeyBtn.disabled = true;
            const res = await fetch('/api/v1/keys', {
                method: 'POST',
                headers: getAuthHeaders(true),
                body: JSON.stringify({ name })
            });
            const data = await res.json();
            genKeyBtn.disabled = false;

            if (res.ok) {
                if (keyStrEl) keyStrEl.textContent = data.api_key;
                if (keyAlertEl) keyAlertEl.style.display = 'block';
                showToast('API Key generated successfully! Make sure to copy it now.', 'success');
                loadApiKeys();
            } else {
                showToast(data.error?.message || 'Failed to create API key.', 'danger');
            }
        } catch (err) {
            genKeyBtn.disabled = false;
            showToast(err.message, 'danger');
        }
    });

    copyKeyBtn?.addEventListener('click', () => {
        if (keyStrEl && keyStrEl.textContent) {
            navigator.clipboard.writeText(keyStrEl.textContent).then(() => {
                showToast('API Key copied to clipboard!', 'success');
            });
        }
    });

    toggleWhBtn?.addEventListener('click', () => {
        if (whBoxEl) whBoxEl.style.display = whBoxEl.style.display === 'none' ? 'block' : 'none';
    });

    cancelWhBtn?.addEventListener('click', () => {
        if (whBoxEl) whBoxEl.style.display = 'none';
    });

    newWhForm?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const url = (document.getElementById('webhookUrlInput')?.value || '').trim();
        const evts = [];
        if (document.getElementById('whEvtCompleted')?.checked) evts.push('analysis.completed');
        if (document.getElementById('whEvtHighRisk')?.checked) evts.push('analysis.high_risk');

        try {
            const res = await fetch('/api/v1/webhooks', {
                method: 'POST',
                headers: getAuthHeaders(true),
                body: JSON.stringify({ url, events: evts })
            });
            const data = await res.json();
            if (res.ok) {
                showToast('Webhook successfully registered with cryptographic signing secret!', 'success');
                if (whBoxEl) whBoxEl.style.display = 'none';
                newWhForm.reset();
                loadWebhooks();
            } else {
                showToast(data.error?.message || 'Failed to register webhook.', 'danger');
            }
        } catch (err) {
            showToast(err.message, 'danger');
        }
    });

    await loadApiKeys();
    await loadWebhooks();
}


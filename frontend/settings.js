/**
 * Settings Controller
 * Handles appearance theme switching, notification alerts, data export,
 * and navigation shortcuts.
 */

document.addEventListener('DOMContentLoaded', async () => {
    renderAppShell('settings');
    if (!requireAuth()) return;

    setupThemeSelectors();
    await loadSettingsPreferences();
    setupNotificationForm();
    setupShortcuts();
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

            // Sync with backend preferences
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

async function loadSettingsPreferences() {
    try {
        const res = await fetch(`${API_BASE_URL}/auth/preferences`, { headers: getAuthHeaders(true) });
        if (!res.ok) return;

        const prefs = await res.json();
        const notifA = document.getElementById('settingNotifAnalysis');
        const notifS = document.getElementById('settingNotifSecurity');
        const notifE = document.getElementById('settingNotifEmail');

        if (notifA) notifA.checked = prefs.analysis_notifications !== false;
        if (notifS) notifS.checked = prefs.security_notifications !== false;
        if (notifE) notifE.checked = prefs.email_notifications !== false;

    } catch (err) {
        console.error('Failed to load preferences:', err);
    }
}

function setupNotificationForm() {
    const form = document.getElementById('settingsNotifForm');
    form?.addEventListener('submit', async (e) => {
        e.preventDefault();

        const analysis_notifications = document.getElementById('settingNotifAnalysis').checked;
        const security_notifications = document.getElementById('settingNotifSecurity').checked;
        const email_notifications = document.getElementById('settingNotifEmail').checked;

        try {
            const res = await fetch(`${API_BASE_URL}/auth/preferences`, {
                method: 'PUT',
                headers: getAuthHeaders(true),
                body: JSON.stringify({
                    analysis_notifications,
                    security_notifications,
                    email_notifications
                })
            });

            if (res.ok) {
                showToast('Notification alert preferences saved!', 'success');
            } else {
                throw new Error('Failed to update preferences');
            }
        } catch (err) {
            showToast(err.message, 'danger');
        }
    });
}

function setupShortcuts() {
    // Logout
    document.getElementById('settingsLogoutBtn')?.addEventListener('click', () => {
        showConfirmModal({
            title: 'Confirm Session Sign Out',
            message: 'Sign out of your active ScamGuard AI session on this browser?',
            confirmText: 'Sign Out',
            confirmClass: 'btn-danger',
            onConfirm: logout
        });
    });

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
}

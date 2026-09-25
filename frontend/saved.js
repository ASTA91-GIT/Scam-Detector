/**
 * Saved Reports Controller
 * Searches, displays, edits notes, and deletes bookmarked reports from MongoDB.
 */

let activeEditingReportId = null;
let searchDebounce = null;

document.addEventListener('DOMContentLoaded', () => {
    renderAppShell('saved');
    if (!requireAuth()) return;

    loadSavedReports();
    setupSearch();
    setupEditModal();
});

function setupSearch() {
    const input = document.getElementById('savedSearchInput');
    input?.addEventListener('input', () => {
        clearTimeout(searchDebounce);
        searchDebounce = setTimeout(() => {
            loadSavedReports(input.value.trim());
        }, 300);
    });
}

async function loadSavedReports(query = '') {
    const container = document.getElementById('savedReportsContainer');
    if (!container) return;

    try {
        const url = query ? `${API_BASE_URL}/saved-reports?search=${encodeURIComponent(query)}` : `${API_BASE_URL}/saved-reports`;
        const res = await fetch(url, { headers: getAuthHeaders(true) });

        if (!res.ok) {
            if (res.status === 401) logout();
            return;
        }

        const data = await res.json();
        const reports = data.saved_reports || [];

        if (reports.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">🔖</div>
                    <div class="empty-title">${query ? 'No matching saved reports' : 'No saved reports yet'}</div>
                    <p class="empty-desc">${query ? 'Try searching by a different term or keyword.' : 'When reviewing a scan result, click "Save Report" to bookmark it with personal notes.'}</p>
                    <a href="analyze.html" class="btn btn-primary btn-sm">Scan an Offer Letter</a>
                </div>
            `;
            return;
        }

        container.innerHTML = reports.map(r => {
            const isSafe = r.risk_level === 'Safe';
            const isHigh = r.risk_level === 'High Risk' || r.risk_level === 'High';
            const badgeClass = isSafe ? 'badge-safe' : (isHigh ? 'badge-danger' : 'badge-warning');
            const dateStr = r.created_at ? new Date(r.created_at).toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' }) : 'Saved';

            return `
                <div class="cyber-card" style="padding: 1.5rem;" data-id="${r._id}">
                    <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:1rem; margin-bottom:0.75rem;">
                        <div>
                            <div style="display:flex; align-items:center; gap:0.5rem; margin-bottom:0.35rem;">
                                <span class="badge ${badgeClass}">${r.risk_level} (${r.trust_score})</span>
                                <span style="font-size:0.78rem; color:var(--text-muted);">${dateStr}</span>
                            </div>
                            <h3 style="font-size:1.2rem; margin-bottom:0.25rem;">${r.custom_title || r.job_title}</h3>
                            <div style="font-size:0.88rem; color:var(--text-secondary);">
                                Company: <strong style="color:var(--text-primary);">${r.company_name}</strong> &bull; ${r.job_title}
                            </div>
                        </div>

                        <div style="display:flex; align-items:center; gap:0.65rem; flex-wrap:wrap;">
                            <button class="btn btn-outline btn-sm ask-caseai-saved-btn" data-analysis-id="${r.analysis_id}" style="border-color:var(--accent-cyan); color:var(--accent-cyan); background:rgba(0,229,255,0.06);" title="Investigate with CaseAI">
                                ✦ CaseAI
                            </button>
                            <a href="result.html?id=${r.analysis_id}" class="btn btn-outline btn-sm">View Full Dossier</a>
                            <button class="btn btn-outline btn-sm edit-report-btn" data-id="${r._id}" data-title="${encodeURIComponent(r.custom_title || '')}" data-notes="${encodeURIComponent(r.notes || '')}">
                                Edit Notes
                            </button>
                            <button class="btn btn-outline btn-sm delete-report-btn" data-id="${r._id}" style="color:var(--risk-danger);">
                                Delete
                            </button>
                        </div>
                    </div>

                    ${r.notes ? `
                        <div style="background:var(--bg-surface); border:1px solid var(--border-subtle); border-radius:var(--radius-md); padding:0.85rem 1rem; margin-top:0.75rem;">
                            <div style="font-size:0.75rem; font-weight:700; color:var(--accent-cyan); text-transform:uppercase; margin-bottom:2px;">Investigator Notes</div>
                            <p style="color:var(--text-secondary); font-size:0.88rem; line-height:1.4;">${r.notes}</p>
                        </div>
                    ` : ''}
                </div>
            `;
        }).join('');

        attachActionHandlers();

    } catch (err) {
        console.error('Failed to load saved reports:', err);
    }
}

function attachActionHandlers() {
    // Edit Notes
    document.querySelectorAll('.edit-report-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            activeEditingReportId = btn.dataset.id;
            const title = decodeURIComponent(btn.dataset.title || '');
            const notes = decodeURIComponent(btn.dataset.notes || '');

            const modal = document.getElementById('editSavedReportModal');
            document.getElementById('editSavedTitle').value = title;
            document.getElementById('editSavedNotes').value = notes;
            modal?.classList.add('active');
        });
    });

    // Delete
    document.querySelectorAll('.delete-report-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const id = btn.dataset.id;
            showConfirmModal({
                title: 'Delete Saved Report',
                message: 'Remove this bookmarked report from your saved repository?',
                confirmText: 'Remove Report',
                confirmClass: 'btn-danger',
                onConfirm: async () => {
                    try {
                        const res = await fetch(`${API_BASE_URL}/saved-reports/${id}`, {
                            method: 'DELETE',
                            headers: getAuthHeaders(true)
                        });
                        if (res.ok) {
                            showToast('Report removed from saved repository', 'info');
                            loadSavedReports();
                        }
                    } catch {
                        showToast('Failed to delete saved report', 'danger');
                    }
                }
            });
        });
    });

    // Ask CaseAI buttons
    document.querySelectorAll('.ask-caseai-saved-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const analysisId = btn.dataset.analysisId;
            if (window.openCaseAI && analysisId) {
                window.openCaseAI(analysisId);
            }
        });
    });
}

function setupEditModal() {
    const modal = document.getElementById('editSavedReportModal');
    const closeBtn = document.getElementById('closeEditSavedModal');
    const cancelBtn = document.getElementById('cancelEditSavedModal');
    const saveBtn = document.getElementById('saveEditSavedModalBtn');

    const closeModal = () => modal?.classList.remove('active');
    closeBtn?.addEventListener('click', closeModal);
    cancelBtn?.addEventListener('click', closeModal);

    saveBtn?.addEventListener('click', async () => {
        if (!activeEditingReportId) return;

        const custom_title = document.getElementById('editSavedTitle').value.trim();
        const notes = document.getElementById('editSavedNotes').value.trim();

        try {
            saveBtn.disabled = true;
            const res = await fetch(`${API_BASE_URL}/saved-reports/${activeEditingReportId}`, {
                method: 'PUT',
                headers: getAuthHeaders(true),
                body: JSON.stringify({ custom_title, notes })
            });

            if (res.ok) {
                closeModal();
                showToast('Report dossier updated successfully!', 'success');
                loadSavedReports();
            } else {
                throw new Error('Failed to update report');
            }
        } catch (err) {
            showToast(err.message, 'danger');
        } finally {
            saveBtn.disabled = false;
        }
    });
}

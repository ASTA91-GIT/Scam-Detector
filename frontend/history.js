/**
 * Analysis History Controller
 * Search, filter by risk level, sort, paginated query,
 * view dossier, delete scan, and save/unsave bookmarks.
 */

let currentPage = 1;
const pageLimit = 10;
let debounceTimeout = null;
let selectedForCompare = new Set();

document.addEventListener('DOMContentLoaded', () => {
    renderAppShell('history');
    if (!requireAuth()) return;

    setupFilterListeners();
    setupCompareModal();
    loadHistory();
});

function setupFilterListeners() {
    const searchInput = document.getElementById('historySearchInput');
    const riskFilter = document.getElementById('historyRiskFilter');
    const sortSelect = document.getElementById('historySortSelect');
    const resetBtn = document.getElementById('resetHistoryFiltersBtn');
    const prevBtn = document.getElementById('prevPageBtn');
    const nextBtn = document.getElementById('nextPageBtn');

    searchInput?.addEventListener('input', () => {
        clearTimeout(debounceTimeout);
        debounceTimeout = setTimeout(() => {
            currentPage = 1;
            loadHistory();
        }, 300);
    });

    riskFilter?.addEventListener('change', () => {
        currentPage = 1;
        loadHistory();
    });

    sortSelect?.addEventListener('change', () => {
        currentPage = 1;
        loadHistory();
    });

    resetBtn?.addEventListener('click', () => {
        if (searchInput) searchInput.value = '';
        if (riskFilter) riskFilter.value = 'All';
        if (sortSelect) sortSelect.value = 'newest';
        currentPage = 1;
        loadHistory();
    });

    prevBtn?.addEventListener('click', () => {
        if (currentPage > 1) {
            currentPage--;
            loadHistory();
        }
    });

    nextBtn?.addEventListener('click', () => {
        currentPage++;
        loadHistory();
    });
}

async function loadHistory() {
    const container = document.getElementById('historyListContainer');
    const pagination = document.getElementById('historyPagination');
    const prevBtn = document.getElementById('prevPageBtn');
    const nextBtn = document.getElementById('nextPageBtn');
    const pageIndicator = document.getElementById('pageIndicator');
    const summary = document.getElementById('paginationSummary');

    const search = document.getElementById('historySearchInput')?.value.trim() || '';
    const risk = document.getElementById('historyRiskFilter')?.value || 'All';
    const sort = document.getElementById('historySortSelect')?.value || 'newest';

    const queryParams = new URLSearchParams({
        page: currentPage,
        limit: pageLimit,
        search: search,
        risk_level: risk,
        sort: sort
    });

    try {
        const res = await fetch(`${API_BASE_URL}/dashboard/analyses?${queryParams.toString()}`, {
            headers: getAuthHeaders(true)
        });

        if (!res.ok) {
            if (res.status === 401) logout();
            return;
        }

        const data = await res.json();
        const items = data.analyses || [];
        const total = data.total || 0;
        const totalPages = data.total_pages || 1;

        if (items.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">🔍</div>
                    <div class="empty-title">${search || risk !== 'All' ? 'No matching analyses found' : 'No analyses yet'}</div>
                    <p class="empty-desc">${search || risk !== 'All' ? 'Try adjusting your search keywords or resetting your risk level filters.' : 'Analyze your first job description or offer letter to begin building your forensic archive.'}</p>
                    <a href="analyze.html" class="btn btn-primary btn-sm">Scan a Job Offer</a>
                </div>
            `;
            if (pagination) pagination.style.display = 'none';
            return;
        }

        updateCompareBtnState();

        // Render Cards
        container.innerHTML = items.map(item => {
            const isSafe = item.risk_level === 'Safe';
            const isHigh = item.risk_level === 'High Risk' || item.risk_level === 'High';
            const badgeClass = isSafe ? 'badge-safe' : (isHigh ? 'badge-danger' : 'badge-warning');
            const dateStr = item.created_at ? new Date(item.created_at).toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' }) : 'Verified';
            const isChecked = selectedForCompare.has(item._id);

            return `
                <div class="cyber-card" style="padding: 1.25rem 1.5rem;" data-id="${item._id}">
                    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:1rem;">
                        <div style="display:flex; align-items:flex-start; gap:0.75rem; flex:1; min-width:240px;">
                            <input type="checkbox" class="compare-checkbox" data-id="${item._id}" ${isChecked ? 'checked' : ''} style="margin-top: 4px; width: 18px; height: 18px; accent-color: var(--accent-cyan); cursor: pointer;" title="Select to compare (choose 2)">
                            <div>
                                <div style="display:flex; align-items:center; gap:0.5rem; margin-bottom:0.25rem;">
                                    <span class="badge ${badgeClass}">${item.risk_level} (${item.trust_score})</span>
                                    <span style="font-size:0.78rem; color:var(--text-muted);">${dateStr}</span>
                                </div>
                                <h3 style="font-size:1.15rem; margin-bottom:0.25rem;">${item.job_title || 'Job Offer'}</h3>
                                <div style="font-size:0.88rem; color:var(--text-secondary);">
                                    Company: <strong style="color:var(--text-primary);">${item.company_name || 'Not Specified'}</strong>
                                    ${item.company_website ? `&bull; <a href="${item.company_website}" target="_blank" rel="noopener" style="font-size:0.82rem;">${item.company_website}</a>` : ''}
                                </div>
                            </div>
                        </div>

                        <div style="display:flex; align-items:center; gap:0.5rem; flex-wrap:wrap;">
                            <button class="btn btn-sm btn-outline ask-caseai-btn" data-id="${item._id}" style="border-color:var(--accent-cyan); color:var(--accent-cyan); background:rgba(0,229,255,0.06);" title="Investigate with CaseAI">
                                ✦ CaseAI
                            </button>
                            <a href="result.html?id=${item._id}" class="btn btn-outline btn-sm">View Dossier</a>
                            <button class="btn btn-sm btn-outline bookmark-btn" data-id="${item._id}" title="Save / Bookmark">
                                🔖
                            </button>
                            <button class="btn btn-sm btn-outline delete-analysis-btn" data-id="${item._id}" title="Delete record" style="color:var(--risk-danger);">
                                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                            </button>
                        </div>
                    </div>
                </div>
            `;
        }).join('');

        // Attach Checkbox Compare Handlers
        container.querySelectorAll('.compare-checkbox').forEach(cb => {
            cb.addEventListener('change', () => {
                const id = cb.dataset.id;
                if (cb.checked) {
                    if (selectedForCompare.size >= 2) {
                        cb.checked = false;
                        showToast('You can only select exactly 2 analyses to compare side-by-side.', 'warning');
                        return;
                    }
                    selectedForCompare.add(id);
                } else {
                    selectedForCompare.delete(id);
                }
                updateCompareBtnState();
            });
        });

        // Attach Delete & Bookmark Handlers
        attachItemActions();

        // Update Pagination Bar
        if (pagination) {
            pagination.style.display = 'flex';
            if (prevBtn) prevBtn.disabled = currentPage <= 1;
            if (nextBtn) nextBtn.disabled = currentPage >= totalPages;
            if (pageIndicator) pageIndicator.textContent = `Page ${currentPage} of ${totalPages}`;
            if (summary) {
                const start = (currentPage - 1) * pageLimit + 1;
                const end = Math.min(currentPage * pageLimit, total);
                summary.textContent = `Showing ${start}–${end} of ${total} scans`;
            }
        }

    } catch (err) {
        console.error('Failed to load history:', err);
        container.innerHTML = `<div style="color:var(--risk-danger); padding:2rem; text-align:center;">Failed to load history records.</div>`;
    }
}

function attachItemActions() {
    // Delete buttons
    document.querySelectorAll('.delete-analysis-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const id = btn.dataset.id;
            showConfirmModal({
                title: 'Delete Scan Record',
                message: 'Are you sure you want to permanently delete this forensic analysis dossier?',
                confirmText: 'Delete Record',
                confirmClass: 'btn-danger',
                onConfirm: async () => {
                    try {
                        const res = await fetch(`${API_BASE_URL}/dashboard/analyses/${id}`, {
                            method: 'DELETE',
                            headers: getAuthHeaders(true)
                        });
                        if (res.ok) {
                            showToast('Analysis record deleted successfully', 'info');
                            loadHistory();
                        } else {
                            throw new Error('Failed to delete');
                        }
                    } catch (err) {
                        showToast(err.message, 'danger');
                    }
                }
            });
        });
    });

    // Bookmark buttons
    document.querySelectorAll('.bookmark-btn').forEach(btn => {
        btn.addEventListener('click', async () => {
            const id = btn.dataset.id;
            try {
                const res = await fetch(`${API_BASE_URL}/saved-reports`, {
                    method: 'POST',
                    headers: getAuthHeaders(true),
                    body: JSON.stringify({ analysis_id: id })
                });
                if (res.ok) {
                    showToast('Report bookmarked to Saved Reports!', 'success');
                    btn.style.color = 'var(--accent-cyan)';
                }
            } catch {
                showToast('Failed to save bookmark', 'danger');
            }
        });
    });

    // Ask CaseAI buttons
    document.querySelectorAll('.ask-caseai-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const id = btn.dataset.id;
            if (window.openCaseAI && id) {
                window.openCaseAI(id);
            }
        });
    });
}

function setupCompareModal() {
    const compareBtn = document.getElementById('compareSelectedBtn');
    const modal = document.getElementById('compareModal');
    const closeBtn = document.getElementById('closeCompareModal');
    const modalBody = document.getElementById('compareModalBody');

    if (!compareBtn || !modal) return;

    closeBtn?.addEventListener('click', () => {
        modal.style.display = 'none';
    });

    window.addEventListener('click', (e) => {
        if (e.target === modal) modal.style.display = 'none';
    });

    compareBtn.addEventListener('click', async () => {
        if (selectedForCompare.size !== 2) {
            showToast('Please select exactly 2 analyses to compare.', 'warning');
            return;
        }

        const [id1, id2] = Array.from(selectedForCompare);
        modal.style.display = 'flex';
        modalBody.innerHTML = `<div style="text-align: center; padding: 3rem; color: var(--text-muted);"><div class="spinner"></div><p style="margin-top: 1rem;">Computing forensic delta and comparative telemetry...</p></div>`;

        try {
            const res = await fetch(`${API_BASE_URL}/analysis/compare?id1=${encodeURIComponent(id1)}&id2=${encodeURIComponent(id2)}`, {
                headers: getAuthHeaders(true)
            });

            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.message || 'Comparison request failed');
            }

            const data = await res.json();
            renderComparisonData(modalBody, data);
        } catch (err) {
            modalBody.innerHTML = `<div style="padding: 2rem; color: var(--risk-danger); text-align: center;">${escapeHtml(err.message)}</div>`;
        }
    });
}

function renderComparisonData(container, data) {
    const diffSign = data.score_diff > 0 ? `+${data.score_diff}` : `${data.score_diff}`;
    const diffColor = data.score_diff > 0 ? 'var(--risk-danger)' : (data.score_diff < 0 ? 'var(--risk-safe)' : 'var(--text-muted)');

    const changedEntitiesHtml = Object.keys(data.changed_entities || {}).length > 0 ? `
        <div style="margin-top: 1.5rem; background: rgba(255,255,255,0.02); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 1rem;">
            <h4 style="font-size: 0.9rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--accent-cyan); margin-bottom: 0.75rem;">Detected Entity Variance</h4>
            <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 0.5rem; font-size: 0.85rem; border-bottom: 1px solid var(--border-subtle); padding-bottom: 0.5rem; font-weight: 600; color: var(--text-muted);">
                <div>Property</div>
                <div>Case A</div>
                <div>Case B</div>
            </div>
            ${Object.entries(data.changed_entities).map(([key, val]) => `
                <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 0.5rem; font-size: 0.82rem; padding: 0.4rem 0; border-bottom: 1px solid rgba(255,255,255,0.03);">
                    <div style="color: var(--text-muted); font-family: var(--font-jetbrains);">${escapeHtml(key)}</div>
                    <div style="color: #fff;">${escapeHtml(String(val.doc1 || 'None'))}</div>
                    <div style="color: var(--accent-cyan); font-weight: 500;">${escapeHtml(String(val.doc2 || 'None'))}</div>
                </div>
            `).join('')}
        </div>
    ` : `<div style="margin-top: 1rem; color: var(--text-muted); font-size: 0.85rem;">No significant entity discrepancies detected between documents.</div>`;

    const addedFindingsHtml = (data.added_findings || []).length > 0 ? `
        <div style="margin-top: 1rem;">
            <h5 style="color: var(--risk-danger); font-size: 0.85rem; margin-bottom: 0.5rem;">+ Red Flags Introduced in Case B (${data.added_findings.length}):</h5>
            <ul style="margin: 0; padding-left: 1.25rem; font-size: 0.82rem; color: #fff;">
                ${data.added_findings.map(f => `<li style="margin-bottom: 0.25rem;">${escapeHtml(f)}</li>`).join('')}
            </ul>
        </div>
    ` : '';

    const removedFindingsHtml = (data.removed_findings || []).length > 0 ? `
        <div style="margin-top: 1rem;">
            <h5 style="color: var(--risk-safe); font-size: 0.85rem; margin-bottom: 0.5rem;">- Red Flags Absent in Case B (${data.removed_findings.length}):</h5>
            <ul style="margin: 0; padding-left: 1.25rem; font-size: 0.82rem; color: var(--text-muted);">
                ${data.removed_findings.map(f => `<li style="margin-bottom: 0.25rem;">${escapeHtml(f)}</li>`).join('')}
            </ul>
        </div>
    ` : '';

    container.innerHTML = `
        <div style="display: grid; grid-template-columns: 1fr auto 1fr; gap: 1rem; align-items: center; background: rgba(0,0,0,0.2); padding: 1.25rem; border-radius: var(--radius-md); border: 1px solid var(--border-subtle);">
            <div>
                <span class="badge" style="font-size: 0.7rem; background: rgba(255,255,255,0.06); color: var(--text-muted);">CASE A</span>
                <h4 style="margin: 0.5rem 0 0.25rem; color: #fff; font-size: 1rem;">${escapeHtml(data.doc1_title)}</h4>
                <div style="font-size: 1.5rem; font-weight: 700; font-family: var(--font-jetbrains); color: ${data.score1 >= 70 ? 'var(--risk-danger)' : (data.score1 <= 30 ? 'var(--risk-safe)' : 'var(--risk-warning)')};">
                    ${data.score1} <span style="font-size: 0.8rem; font-weight: 400; color: var(--text-muted);">/ 100</span>
                </div>
                <div style="font-size: 0.8rem; color: var(--text-muted);">${escapeHtml(data.classification1)}</div>
            </div>

            <div style="text-align: center; padding: 0 1rem;">
                <div style="font-size: 0.75rem; text-transform: uppercase; color: var(--text-muted); letter-spacing: 0.05em;">Risk Delta</div>
                <div style="font-size: 1.5rem; font-weight: 800; font-family: var(--font-jetbrains); color: ${diffColor};">
                    ${diffSign}
                </div>
                <div style="font-size: 0.75rem; color: var(--text-muted);">${data.classification_changed ? 'Classification Shifted' : 'Classification Stable'}</div>
            </div>

            <div style="text-align: right;">
                <span class="badge" style="font-size: 0.7rem; background: rgba(0,240,255,0.1); color: var(--accent-cyan);">CASE B</span>
                <h4 style="margin: 0.5rem 0 0.25rem; color: #fff; font-size: 1rem;">${escapeHtml(data.doc2_title)}</h4>
                <div style="font-size: 1.5rem; font-weight: 700; font-family: var(--font-jetbrains); color: ${data.score2 >= 70 ? 'var(--risk-danger)' : (data.score2 <= 30 ? 'var(--risk-safe)' : 'var(--risk-warning)')};">
                    ${data.score2} <span style="font-size: 0.8rem; font-weight: 400; color: var(--text-muted);">/ 100</span>
                </div>
                <div style="font-size: 0.8rem; color: var(--text-muted);">${escapeHtml(data.classification2)}</div>
            </div>
        </div>

        ${changedEntitiesHtml}
        ${addedFindingsHtml}
        ${removedFindingsHtml}

        <div style="margin-top: 1.5rem; display: flex; justify-content: flex-end; gap: 0.75rem;">
            <a href="result.html?id=${encodeURIComponent(data.id1)}" class="btn btn-outline btn-sm" target="_blank">Open Case A Dossier ↗</a>
            <a href="result.html?id=${encodeURIComponent(data.id2)}" class="btn btn-primary btn-sm" target="_blank">Open Case B Dossier ↗</a>
        </div>
    `;
}

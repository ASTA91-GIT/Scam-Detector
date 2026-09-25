/**
 * Analysis History Controller
 * Search, filter by risk level, sort, paginated query,
 * view dossier, delete scan, and save/unsave bookmarks.
 */

let currentPage = 1;
const pageLimit = 10;
let debounceTimeout = null;

document.addEventListener('DOMContentLoaded', () => {
    renderAppShell('history');
    if (!requireAuth()) return;

    setupFilterListeners();
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

        // Render Cards
        container.innerHTML = items.map(item => {
            const isSafe = item.risk_level === 'Safe';
            const isHigh = item.risk_level === 'High Risk' || item.risk_level === 'High';
            const badgeClass = isSafe ? 'badge-safe' : (isHigh ? 'badge-danger' : 'badge-warning');
            const dateStr = item.created_at ? new Date(item.created_at).toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' }) : 'Verified';

            return `
                <div class="cyber-card" style="padding: 1.25rem 1.5rem;" data-id="${item._id}">
                    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:1rem;">
                        <div style="flex:1; min-width:240px;">
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

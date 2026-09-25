/**
 * Forensic Result Dossier Controller
 * Loads detailed analysis by ID, animates radial trust score,
 * renders 6 risk breakdown pillars, red flag evidence quotes,
 * company validation, save/unsave toggles, printable report, and share link.
 */

let currentAnalysis = null;
let currentAnalysisId = null;
let isCurrentlySaved = false;
let savedRecordId = null;

document.addEventListener('DOMContentLoaded', async () => {
    renderAppShell('result');

    const urlParams = new URLSearchParams(window.location.search);
    currentAnalysisId = urlParams.get('id');

    if (!currentAnalysisId) {
        showError('No Analysis ID Specified', 'Please provide a valid forensic audit identifier to load a dossier.');
        return;
    }

    await loadDossier(currentAnalysisId);
    setupActionButtons();
});

async function loadDossier(id) {
    const loading = document.getElementById('resultLoadingState');
    const main = document.getElementById('resultMainContainer');

    try {
        let res = await fetch(`${API_BASE_URL}/analysis/result/${id}`, { headers: getAuthHeaders(true) });

        // If unauthorized or not found under user, check public share endpoint
        if (!res.ok && res.status !== 401) {
            res = await fetch(`${API_BASE_URL}/analysis/share/${id}`);
            if (res.ok) {
                const shareData = await res.json();
                currentAnalysis = shareData.report;
            }
        } else if (res.ok) {
            const data = await res.json();
            currentAnalysis = data.analysis;
        }

        if (!currentAnalysis) {
            throw new Error('Analysis record could not be found or access is restricted.');
        }

        loading.style.display = 'none';
        main.style.display = 'block';

        renderAnalysisData(currentAnalysis);
        checkSavedStatus(id);

    } catch (err) {
        loading.style.display = 'none';
        showError('Failed to Load Assessment', err.message);
    }
}

function showError(title, message) {
    document.getElementById('resultLoadingState').style.display = 'none';
    const errBox = document.getElementById('resultErrorState');
    errBox.style.display = 'block';
    document.getElementById('resultErrorTitle').textContent = title;
    document.getElementById('resultErrorDesc').textContent = message;
}

function renderAnalysisData(a) {
    const score = a.trust_score ?? 0;
    const isSafe = a.risk_level === 'Safe';
    const isHigh = a.risk_level === 'High Risk' || a.risk_level === 'High';
    const riskBadgeClass = isSafe ? 'badge-safe' : (isHigh ? 'badge-danger' : 'badge-warning');
    const strokeColor = isSafe ? '#10b981' : (isHigh ? '#ef4444' : '#f59e0b');

    // Header info
    document.getElementById('resultJobTitle').textContent = a.job_title || 'Employment Offer Assessment';
    document.getElementById('resultCompanyName').textContent = a.company_name || 'Claimed Employer';
    document.getElementById('resultAuditId').textContent = `ID: #${(a.analysis_id || a._id || '').slice(-8).toUpperCase()}`;

    const dateStr = a.created_at ? new Date(a.created_at).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' }) : 'Verified';
    document.getElementById('resultTimestamp').textContent = dateStr;

    const badge = document.getElementById('resultRiskBadge');
    badge.className = `badge ${riskBadgeClass}`;
    badge.textContent = a.risk_level || 'EVALUATED';

    // Radial Score Animation
    const fillCircle = document.getElementById('resultRadialFill');
    const scoreNum = document.getElementById('resultTrustScore');

    fillCircle.style.stroke = strokeColor;
    const targetOffset = 440 - (440 * (score / 100));

    setTimeout(() => {
        fillCircle.style.strokeDashoffset = targetOffset;
    }, 150);

    // Number Count-up
    let current = 0;
    const countInterval = setInterval(() => {
        if (current >= score) {
            scoreNum.textContent = score;
            clearInterval(countInterval);
        } else {
            current = Math.min(score, current + Math.ceil((score - current) / 6));
            scoreNum.textContent = current;
        }
    }, 25);

    // Executive Summary / AI Explanation
    const aiText = a.ai_explanation || (a.explanations && a.explanations.join('. ')) || 'Forensic heuristics evaluated semantic intent and domain indicators.';
    document.getElementById('resultAiExplanation').textContent = aiText;

    // 6 Risk Breakdown Pillars
    const b = a.risk_breakdown || {};
    setBreakdownPill('scorePayment', b.payment_risk ?? (a.financial_flags_count ? 30 : 100));
    setBreakdownPill('scoreIdentity', b.identity_risk ?? 100);
    setBreakdownPill('scoreUrgency', b.urgency_risk ?? (a.urgency_score ? 45 : 100));
    setBreakdownPill('scoreContact', b.contact_risk ?? (a.email_domain_suspicious ? 25 : 100));
    setBreakdownPill('scoreCompany', b.company_risk ?? (a.website_exists ? 95 : 30));
    setBreakdownPill('scoreLanguage', b.language_risk ?? (a.grammar_issues ? 50 : 100));

    // Detected Red Flags with Evidence Snippets
    renderRedFlags(a);

    // Recommended Actions Checklist
    renderRecommendations(a.recommendations || []);

    // Company Verification Card
    renderCompanyFootprint(a);
}

function setBreakdownPill(id, val) {
    const el = document.getElementById(id);
    if (!el) return;
    el.textContent = `${val}/100`;
    if (val >= 80) el.style.color = 'var(--risk-safe)';
    else if (val >= 50) el.style.color = 'var(--risk-warning)';
    else el.style.color = 'var(--risk-danger)';
}

function renderRedFlags(a) {
    const container = document.getElementById('redFlagsContainer');
    if (!container) return;

    const flags = a.structured_red_flags || [];

    if (flags.length === 0) {
        // Fallback to legacy red flags if present
        const legacy = a.red_flags || [];
        if (legacy.length === 0) {
            container.innerHTML = `
                <div class="cyber-card" style="border-left: 4px solid var(--risk-safe); padding: 1.5rem;">
                    <div style="display:flex; align-items:center; gap:0.75rem;">
                        <span style="font-size:1.5rem; color:var(--risk-safe);">✓</span>
                        <div>
                            <strong>No Critical Threat Indicators Detected</strong>
                            <p style="color:var(--text-secondary); font-size:0.88rem; margin-top:2px;">
                                Offer text and recruiter contact credentials conform to standard professional norms. Always conduct standard due diligence.
                            </p>
                        </div>
                    </div>
                </div>
            `;
            return;
        }

        container.innerHTML = legacy.map(flagTitle => `
            <div class="red-flag-card HIGH">
                <div class="red-flag-head">
                    <span class="badge badge-warning">HIGH</span>
                    <span class="red-flag-title">${flagTitle}</span>
                </div>
                <div class="red-flag-rec">
                    <span>🛡️ Action:</span> Verify recruiter claims independently before taking action.
                </div>
            </div>
        `).join('');
        return;
    }

    container.innerHTML = flags.map(f => {
        const sevClass = f.severity || 'HIGH';
        const badgeStyle = sevClass === 'CRITICAL' ? 'badge-danger' : (sevClass === 'HIGH' ? 'badge-warning' : 'badge-cyan');

        return `
            <div class="red-flag-card ${sevClass}">
                <div class="red-flag-head">
                    <span class="badge ${badgeStyle}">${sevClass}</span>
                    <span class="red-flag-title">${f.title}</span>
                </div>
                <p style="color: var(--text-secondary); font-size: 0.9rem; line-height: 1.5; margin-top: 4px;">
                    ${f.explanation}
                </p>

                ${f.evidence ? `
                    <div class="evidence-quote-box">
                        <strong>Observed Pattern:</strong> "${f.evidence}"
                    </div>
                ` : ''}

                <div class="red-flag-rec">
                    <span>🛡️ Recommended Countermeasure:</span> ${f.recommendation}
                </div>
            </div>
        `;
    }).join('');
}

function renderRecommendations(recs) {
    const list = document.getElementById('recommendationsList');
    if (!list) return;

    if (recs.length === 0) {
        list.innerHTML = `
            <li style="display:flex; gap:0.5rem; align-items:flex-start; color:var(--text-secondary); font-size:0.9rem;">
                <span style="color:var(--risk-safe);">✓</span> Verify company contact details through official public switchboard.
            </li>
            <li style="display:flex; gap:0.5rem; align-items:flex-start; color:var(--text-secondary); font-size:0.9rem;">
                <span style="color:var(--risk-safe);">✓</span> Never transfer personal funds, wire transfers, or crypto for employment.
            </li>
        `;
        return;
    }

    list.innerHTML = recs.map((rec, i) => `
        <li style="display:flex; gap:0.75rem; align-items:flex-start; padding: 0.5rem 0; border-bottom: 1px solid var(--border-subtle);">
            <input type="checkbox" id="recCheck_${i}" style="margin-top:3px; accent-color: var(--accent-cyan);">
            <label for="recCheck_${i}" style="color:var(--text-primary); font-size:0.88rem; line-height:1.4; cursor:pointer;">
                ${rec}
            </label>
        </li>
    `).join('');
}

function renderCompanyFootprint(a) {
    const dnsStatus = document.getElementById('verifyDnsStatus');
    const emailDomain = document.getElementById('verifyEmailDomain');
    const domainMatch = document.getElementById('verifyDomainMatch');
    const webLink = document.getElementById('verifyWebsiteLink');

    if (dnsStatus) {
        if (a.website_exists === false) {
            dnsStatus.textContent = 'Unreachable / Inactive DNS';
            dnsStatus.style.color = 'var(--risk-danger)';
        } else if (a.company_website) {
            dnsStatus.textContent = 'Active DNS Verified';
            dnsStatus.style.color = 'var(--risk-safe)';
        } else {
            dnsStatus.textContent = 'Not Provided';
            dnsStatus.style.color = 'var(--text-muted)';
        }
    }

    if (emailDomain) {
        if (a.email_domain_suspicious) {
            emailDomain.textContent = `Public / Free (@${a.email_domain || 'generic'})`;
            emailDomain.style.color = 'var(--risk-danger)';
        } else if (a.company_email) {
            emailDomain.textContent = `Enterprise (@${a.email_domain || 'corporate'})`;
            emailDomain.style.color = 'var(--risk-safe)';
        } else {
            emailDomain.textContent = 'Not Specified';
            emailDomain.style.color = 'var(--text-muted)';
        }
    }

    if (domainMatch) {
        if (a.company_match === false) {
            domainMatch.textContent = 'Domain Mismatch ⚠️';
            domainMatch.style.color = 'var(--risk-danger)';
        } else if (a.company_email && a.company_website) {
            domainMatch.textContent = 'Matched Authenticated Host';
            domainMatch.style.color = 'var(--risk-safe)';
        } else {
            domainMatch.textContent = 'Inconclusive (No pair)';
            domainMatch.style.color = 'var(--text-muted)';
        }
    }

    if (webLink && a.company_website) {
        webLink.innerHTML = `
            <a href="${a.company_website}" target="_blank" rel="noopener noreferrer" style="font-size:0.82rem; display:inline-flex; align-items:center; gap:4px;">
                <span>Visit Official Domain (${a.company_website})</span>
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
            </a>
        `;
    }
}

// Check saved status
async function checkSavedStatus(analysisId) {
    if (!getToken()) return;
    try {
        const res = await fetch(`${API_BASE_URL}/saved-reports/check/${analysisId}`, { headers: getAuthHeaders(true) });
        if (res.ok) {
            const data = await res.json();
            isCurrentlySaved = data.is_saved;
            savedRecordId = data.saved_id;
            updateSaveButtonUI();
        }
    } catch (err) {
        console.error('Failed to check saved status:', err);
    }
}

function updateSaveButtonUI() {
    const btn = document.getElementById('saveReportBtn');
    const text = document.getElementById('saveBtnText');
    if (!btn || !text) return;

    if (isCurrentlySaved) {
        btn.classList.remove('btn-outline');
        btn.classList.add('btn-primary');
        text.textContent = 'Saved ✓';
    } else {
        btn.classList.remove('btn-primary');
        btn.classList.add('btn-outline');
        text.textContent = 'Save Report';
    }
}

// Action Buttons
function setupActionButtons() {
    const saveBtn = document.getElementById('saveReportBtn');
    const printBtn = document.getElementById('downloadPdfBtn');
    const shareBtn = document.getElementById('shareReportBtn');

    // Save / Unsave
    saveBtn?.addEventListener('click', async () => {
        if (!requireAuth()) return;

        if (isCurrentlySaved) {
            // Unsave
            try {
                const res = await fetch(`${API_BASE_URL}/saved-reports/by-analysis/${currentAnalysisId}`, {
                    method: 'DELETE',
                    headers: getAuthHeaders(true)
                });
                if (res.ok) {
                    isCurrentlySaved = false;
                    savedRecordId = null;
                    updateSaveButtonUI();
                    showToast('Report removed from saved dossier list', 'info');
                }
            } catch {
                showToast('Failed to unsave report', 'danger');
            }
        } else {
            // Open Save Modal
            const modal = document.getElementById('saveReportModal');
            const titleInput = document.getElementById('savedReportTitle');
            if (titleInput && currentAnalysis) {
                titleInput.value = `${currentAnalysis.job_title || 'Offer'} - ${currentAnalysis.company_name || 'Employer'}`;
            }
            modal?.classList.add('active');
        }
    });

    // Save Modal Handlers
    const saveModal = document.getElementById('saveReportModal');
    document.getElementById('closeSaveModal')?.addEventListener('click', () => saveModal?.classList.remove('active'));
    document.getElementById('cancelSaveModal')?.addEventListener('click', () => saveModal?.classList.remove('active'));

    document.getElementById('confirmSaveReportBtn')?.addEventListener('click', async () => {
        const title = document.getElementById('savedReportTitle').value.trim();
        const notes = document.getElementById('savedReportNotes').value.trim();

        try {
            const res = await fetch(`${API_BASE_URL}/saved-reports`, {
                method: 'POST',
                headers: getAuthHeaders(true),
                body: JSON.stringify({
                    analysis_id: currentAnalysisId,
                    custom_title: title,
                    notes: notes
                })
            });
            const data = await res.json();
            if (res.ok) {
                isCurrentlySaved = true;
                savedRecordId = data.saved_id;
                updateSaveButtonUI();
                saveModal?.classList.remove('active');
                showToast('Report bookmarked successfully to Saved Reports!', 'success');
            } else {
                throw new Error(data.error || 'Failed to save');
            }
        } catch (err) {
            showToast(err.message, 'danger');
        }
    });

    // Download / Print PDF
    printBtn?.addEventListener('click', () => {
        window.print();
    });

    // Share Modal Handlers
    const shareModal = document.getElementById('shareReportModal');
    shareBtn?.addEventListener('click', () => {
        const linkInput = document.getElementById('shareableLinkInput');
        if (linkInput) {
            linkInput.value = `${window.location.origin}/result.html?id=${currentAnalysisId}`;
        }
        shareModal?.classList.add('active');
    });

    document.getElementById('closeShareModal')?.addEventListener('click', () => shareModal?.classList.remove('active'));
    document.getElementById('doneShareBtn')?.addEventListener('click', () => shareModal?.classList.remove('active'));

    document.getElementById('copyShareLinkBtn')?.addEventListener('click', async () => {
        const linkInput = document.getElementById('shareableLinkInput');
        try {
            await navigator.clipboard.writeText(linkInput.value);
            showToast('Share link copied to clipboard!', 'success');
        } catch {
            linkInput.select();
            document.execCommand('copy');
            showToast('Link copied to clipboard!', 'success');
        }
    });

    // Ask CaseAI Handler
    document.getElementById('askCaseAiBtn')?.addEventListener('click', () => {
        if (window.openCaseAI && currentAnalysisId) {
            window.openCaseAI(currentAnalysisId);
        }
    });
}

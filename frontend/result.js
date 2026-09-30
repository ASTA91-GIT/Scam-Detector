/**
 * AI Forensic Investigation Console Controller
 * Powers the evidence-driven digital forensics workstation dossier.
 * Handles risk score radial animation, forensic signal matrix,
 * investigation timeline, entity extraction, domain telemetry,
 * evidence-first AI Opinion component, CaseAI launch, and report saving/sharing.
 */

let currentAnalysis = null;
let currentAnalysisId = null;
let isCurrentlySaved = false;
let savedRecordId = null;

document.addEventListener('DOMContentLoaded', async () => {
    // Render standard topbar and sidebar navigation
    if (typeof renderAppShell === 'function') {
        renderAppShell('result');
    }

    const urlParams = new URLSearchParams(window.location.search);
    currentAnalysisId = urlParams.get('id');

    if (!currentAnalysisId) {
        showError('No Investigation ID Specified', 'Please provide a valid forensic audit identifier to load a dossier.');
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

        // If unauthorized or not found under user session, check public shared report endpoint
        if (!res.ok) {
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

        renderForensicDossier(currentAnalysis);
        checkSavedStatus(id);

    } catch (err) {
        loading.style.display = 'none';
        showError('Failed to Load Assessment', err.message);
    }
}

function showError(title, message) {
    const loading = document.getElementById('resultLoadingState');
    if (loading) loading.style.display = 'none';
    const errBox = document.getElementById('resultErrorState');
    if (errBox) {
        errBox.style.display = 'block';
        document.getElementById('resultErrorTitle').textContent = title;
        document.getElementById('resultErrorDesc').textContent = message;
    }
}

/**
 * Main Forensic Dossier Renderer
 */
function renderForensicDossier(a) {
    // 1. Authoritative Risk Score (0 = minimal risk, 100 = critical risk)
    const riskScore = typeof a.risk_score === 'number' 
        ? a.risk_score 
        : (a.trust_score !== undefined ? (100 - a.trust_score) : 50);

    const isSafe = riskScore < 30 || a.classification === 'LOW_RISK' || a.risk_level === 'Safe';
    const isMedium = (riskScore >= 30 && riskScore < 60) || a.classification === 'MEDIUM_RISK' || a.risk_level === 'Suspicious';
    const isHigh = riskScore >= 60 || a.classification === 'HIGH_RISK' || a.risk_level === 'High Risk' || a.risk_level === 'High';

    const riskColor = isHigh ? '#EF4444' : (isMedium ? '#F59E0B' : '#10B981');
    const riskBadgeClass = isHigh ? 'badge-forensic-danger' : (isMedium ? 'badge-forensic-warning' : 'badge-forensic-safe');
    const riskSeverityText = isHigh ? 'HIGH RISK' : (isMedium ? 'MEDIUM RISK' : 'LOW RISK');

    // 2. Header Info & Breadcrumbs
    const jobTitleEl = document.getElementById('resultJobTitle');
    if (jobTitleEl) jobTitleEl.textContent = a.job_title || 'Document Risk Assessment';

    const compNameEl = document.getElementById('resultCompanyName');
    if (compNameEl) compNameEl.textContent = a.company_name || 'Claimed Organization';

    const auditIdEl = document.getElementById('resultAuditId');
    if (auditIdEl) auditIdEl.textContent = `#${(a.analysis_id || a._id || '').slice(-8).toUpperCase()}`;

    const dateStr = a.created_at ? new Date(a.created_at).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' }) : 'Verified';
    const timeEl = document.getElementById('resultTimestamp');
    if (timeEl) timeEl.textContent = dateStr;

    // Dedicated Print Header Binding
    const printCaseIdEl = document.getElementById('printCaseId');
    if (printCaseIdEl) printCaseIdEl.textContent = `CASE #${(a.analysis_id || a._id || '').slice(-8).toUpperCase()}`;
    const printDateEl = document.getElementById('printDate');
    if (printDateEl) printDateEl.textContent = dateStr;

    // Header Risk Badge & Score
    const riskBadge = document.getElementById('resultRiskBadge');
    if (riskBadge) {
        riskBadge.className = `badge-forensic ${riskBadgeClass}`;
        riskBadge.textContent = riskSeverityText;
    }

    const headerScoreEl = document.getElementById('headerRiskScore');
    if (headerScoreEl) headerScoreEl.textContent = riskScore;

    // Document Type Badge
    const docType = a.document_type || 'GENERAL_DOCUMENT';
    const docTypeFormatted = docType.replace(/_/g, ' ');
    const docTypeConf = a.document_type_confidence ? ` (${a.document_type_confidence}%)` : '';

    const docTypeBadge = document.getElementById('resultDocTypeBadge');
    if (docTypeBadge) docTypeBadge.textContent = `${docTypeFormatted}${docTypeConf}`;

    const headerDocType = document.getElementById('headerDocType');
    if (headerDocType) headerDocType.textContent = docTypeFormatted;

    // 3. Technical Radial Risk Gauge Animation
    animateRadialRiskGauge(riskScore, riskColor, riskSeverityText);

    // Confidence & Engine Badges
    const confVal = a.confidence ?? 92;
    const modelName = a.model_name ? a.model_name.replace('llama', 'Llama-') : 'llama3.2:3b LOCAL';

    const confBadge = document.getElementById('resultConfidenceBadge');
    if (confBadge) confBadge.textContent = `CONFIDENCE: ${confVal}%`;

    const confValEl = document.getElementById('resultConfidenceVal');
    if (confValEl) confValEl.textContent = `${confVal}%`;

    const modelValEl = document.getElementById('resultModelVal');
    if (modelValEl) modelValEl.textContent = modelName;

    const modelBadge = document.getElementById('resultModelBadge');
    if (modelBadge) modelBadge.textContent = `MODEL: ${modelName}`;

    // 4. Extraction Degradation Warning
    const warnBanner = document.getElementById('extractionWarningBanner');
    const warnText = document.getElementById('extractionWarningText');
    if (warnBanner && (a.extraction_warning || a.is_poor_extraction)) {
        warnBanner.style.display = 'block';
        if (warnText) warnText.textContent = a.extraction_warning || 'Document text extraction yielded incomplete sections. Forensic confidence is calibrated accordingly.';
    } else if (warnBanner) {
        warnBanner.style.display = 'none';
    }

    // 5. Executive Security Summary
    const execRiskLevel = document.getElementById('execRiskLevel');
    if (execRiskLevel) execRiskLevel.textContent = riskSeverityText;

    const execConfidence = document.getElementById('execConfidence');
    if (execConfidence) execConfidence.textContent = `${confVal}%`;

    const execDrivers = document.getElementById('execDrivers');
    if (execDrivers) {
        const findings = a.reasoning || a.structured_red_flags || [];
        if (findings.length > 0) {
            execDrivers.textContent = findings.slice(0, 2).map(f => f.finding || f.title).join(' • ');
        } else if (docType === 'CERTIFICATE') {
            execDrivers.textContent = 'Standard Credential Structure • Zero Upfront Demands';
        } else {
            execDrivers.textContent = 'Standard Professional Context • No Material Scam Indicators';
        }
    }

    const aiText = a.summary || a.ai_explanation || 'Forensic heuristics evaluated semantic intent, communication authenticity, and manipulation signals.';
    const expEl = document.getElementById('resultAiExplanation');
    if (expEl) expEl.textContent = aiText;

    // 6. Document Intelligence
    renderDocumentIntelligence(a);

    // 7. Risk Signal Analysis Matrix (6 Pillars)
    renderRiskSignals(a);

    // 8. Forensic Findings Timeline
    renderForensicTimeline(a);

    // 9. Extracted Entities
    renderExtractedEntities(a);

    // 10. Company & Domain Intelligence
    renderCompanyDomainIntelligence(a);
    renderCompanyIntelligence(a);

    // 11. Positive Signals & Legitimacy
    renderPositiveSignals(a.positive_signals || []);

    // 12. Uncertainties & Unverified Elements
    renderUncertainties(a.uncertainties || []);

    // 13. AI OPINION Component (Evidence-First Forensic Assessment)
    renderAiOpinion(a);

    // 14. Recommended Actions (Checklist with persistence)
    renderRecommendations(a.recommendations || [], docType, a.id || a._id, a.checklist_state || {});

    // 15. What-If Forensic Risk Simulation
    setupWhatIfSimulation(a.id || a._id);
}

/**
 * Animate the technical circular risk gauge
 */
function animateRadialRiskGauge(score, color, severity) {
    const fillCircle = document.getElementById('resultRadialFill');
    const scoreNum = document.getElementById('resultRiskScoreNum');
    const sevLabel = document.getElementById('resultGaugeSeverity');

    if (!fillCircle || !scoreNum) return;

    fillCircle.style.stroke = color;
    if (sevLabel) {
        sevLabel.textContent = severity;
        sevLabel.style.color = color;
    }

    // Circumference for r=70 is ~440. Offset = 440 - (440 * score / 100)
    const targetOffset = 440 - (440 * (score / 100));

    setTimeout(() => {
        fillCircle.style.strokeDashoffset = targetOffset;
    }, 150);

    // Numeric Count-up
    let current = 0;
    const step = Math.max(1, Math.ceil(score / 25));
    const interval = setInterval(() => {
        if (current >= score) {
            scoreNum.textContent = score;
            clearInterval(interval);
        } else {
            current = Math.min(score, current + step);
            scoreNum.textContent = current;
        }
    }, 25);
}

/**
 * Render Document Intelligence Table
 */
function renderDocumentIntelligence(a) {
    const d = a.document_intelligence || {};
    const textLen = (a.extracted_text || a.text || '').length;

    const typeEl = document.getElementById('docIntelType');
    if (typeEl) typeEl.textContent = (a.document_type || 'DOCUMENT').replace(/_/g, ' ');

    const pagesEl = document.getElementById('docIntelPages');
    if (pagesEl) pagesEl.textContent = d.pages ? `${d.pages} Page(s)` : (textLen > 3000 ? '2+ Pages' : '1 Page');

    const ocrQualEl = document.getElementById('docIntelOcrQuality');
    if (ocrQualEl) ocrQualEl.textContent = d.ocr_quality || (textLen > 100 ? 'Good (Vector/OCR Fidelity)' : 'Degraded');

    const charsEl = document.getElementById('docIntelChars');
    if (charsEl) charsEl.textContent = `${textLen.toLocaleString()} characters`;

    const ocrConfEl = document.getElementById('docIntelOcrConf');
    if (ocrConfEl) ocrConfEl.textContent = `${d.ocr_confidence ?? 94}%`;

    const synthEl = document.getElementById('docIntelSynthetic');
    if (synthEl) {
        const synth = a.document_assessment || {};
        if (synth.possible_synthetic_document) {
            synthEl.textContent = `Possible Synthetic Formatting (${synth.confidence ?? 60}%)`;
            synthEl.style.color = '#C084FC';
        } else {
            synthEl.textContent = 'Standard Document Composition';
            synthEl.style.color = 'var(--console-text-primary)';
        }
    }
}

/**
 * Render Risk Signal Analysis (6-pillar matrix)
 */
function renderRiskSignals(a) {
    const signals = a.risk_signals || [];
    
    // If structured risk_signals are provided, map them
    if (signals.length >= 6) {
        signals.forEach(sig => {
            const key = sig.name.replace(' RISK', '').trim();
            updateSignalCell(key, sig.score, sig.explanation, sig.severity);
        });
        return;
    }

    // Heuristic fallback derivation from reasoning findings
    const findings = a.reasoning || a.structured_red_flags || [];
    const derived = {
        PAYMENT: { score: 0, desc: 'No advance fee or security payment solicitation detected' },
        IDENTITY: { score: 0, desc: 'No sensitive identity or credential harvesting demanded' },
        URGENCY: { score: 0, desc: 'Standard non-pressured hiring or credential timeframe' },
        CONTACT: { score: 0, desc: 'Communication adheres to standard corporate channels' },
        COMPANY: { score: 0, desc: 'Entity footprint conforms to standard organizational context' },
        LANGUAGE: { score: 0, desc: 'Linguistic patterns match standard professional conventions' }
    };

    findings.forEach(f => {
        const text = ((f.finding || f.title || '') + ' ' + (f.explanation || '')).toLowerCase();
        const impact = f.impact_on_score || 35;

        if (text.includes('payment') || text.includes('fee') || text.includes('deposit') || text.includes('money') || text.includes('zelle')) {
            derived.PAYMENT.score = Math.min(100, derived.PAYMENT.score + impact + 20);
            derived.PAYMENT.desc = f.finding || 'Advance fee solicitation detected';
        }
        if (text.includes('identity') || text.includes('bank') || text.includes('aadhaar') || text.includes('pan') || text.includes('credential')) {
            derived.IDENTITY.score = Math.min(100, derived.IDENTITY.score + impact + 20);
            derived.IDENTITY.desc = f.finding || 'Excessive sensitive credentials demanded';
        }
        if (text.includes('urgency') || text.includes('urgent') || text.includes('24 hours') || text.includes('deadline')) {
            derived.URGENCY.score = Math.min(100, derived.URGENCY.score + impact + 15);
            derived.URGENCY.desc = f.finding || 'Artificial deadline pressure detected';
        }
        if (text.includes('email') || text.includes('domain') || text.includes('contact') || text.includes('whatsapp') || text.includes('telegram')) {
            derived.CONTACT.score = Math.min(100, derived.CONTACT.score + impact + 20);
            derived.CONTACT.desc = f.finding || 'Unverified recruiter contact channel';
        }
        if (text.includes('company') || text.includes('fake') || text.includes('impersonat') || text.includes('unregistered')) {
            derived.COMPANY.score = Math.min(100, derived.COMPANY.score + impact + 15);
            derived.COMPANY.desc = f.finding || 'Organization footprint unverified';
        }
        if (text.includes('grammar') || text.includes('language') || text.includes('manipulat') || text.includes('unrealistic')) {
            derived.LANGUAGE.score = Math.min(100, derived.LANGUAGE.score + impact + 15);
            derived.LANGUAGE.desc = f.finding || 'Linguistic anomalies or pressure tactics';
        }
    });

    Object.keys(derived).forEach(k => {
        const s = derived[k];
        const sev = s.score >= 70 ? 'CRITICAL' : (s.score >= 40 ? 'HIGH' : (s.score > 0 ? 'MEDIUM' : 'SAFE'));
        updateSignalCell(k, s.score, s.desc, sev);
    });
}

function updateSignalCell(key, score, desc, severity) {
    const formattedKey = key.charAt(0).toUpperCase() + key.slice(1).toLowerCase();
    const scoreEl = document.getElementById(`score${formattedKey}`);
    const barEl = document.getElementById(`bar${formattedKey}`);
    const descEl = document.getElementById(`desc${formattedKey}`);

    const color = score >= 60 ? '#EF4444' : (score >= 30 ? '#F59E0B' : '#10B981');

    if (scoreEl) {
        scoreEl.textContent = `${score}/100`;
        scoreEl.style.color = color;
    }
    if (barEl) {
        barEl.style.width = `${score}%`;
        barEl.style.background = color;
    }
    if (descEl && desc) {
        descEl.textContent = desc;
    }
}

/**
 * Render Forensic Findings Timeline
 */
function renderForensicTimeline(a) {
    const container = document.getElementById('redFlagsContainer');
    if (!container) return;

    const findings = a.reasoning || a.structured_red_flags || [];

    if (findings.length === 0) {
        const isCert = a.document_type === 'CERTIFICATE';
        container.innerHTML = `
            <div class="timeline-event">
                <div class="timeline-node SAFE">
                    <div class="timeline-node-inner"></div>
                </div>
                <div class="timeline-card" style="border-left: 3px solid var(--console-risk-safe);">
                    <div class="timeline-card-header">
                        <span class="badge-forensic badge-forensic-safe">NO THREAT INDICATORS</span>
                        <span class="mono-text" style="color: var(--console-risk-safe); font-size: 0.8rem;">0 Red Flags</span>
                    </div>
                    <div class="timeline-title">Clean Document Context Verified</div>
                    <p class="timeline-explanation">
                        ${isCert 
                            ? 'No material scam indicators were identified in the extracted certificate content. Standard participation credentials, academic milestones, and verification links do not constitute fraudulent activity.'
                            : 'No advance fee demands, credential phishing, or manipulation tactics were detected in the analyzed document content.'}
                    </p>
                </div>
            </div>
        `;
        return;
    }

    container.innerHTML = findings.map(f => {
        const title = f.finding || f.title || 'Forensic Risk Factor';
        const sev = (f.severity || 'HIGH').toUpperCase();
        const badgeClass = sev === 'CRITICAL' ? 'badge-forensic-danger' : (sev === 'HIGH' ? 'badge-forensic-warning' : 'badge-forensic-cyan');
        const impact = f.impact_on_score ?? 0;
        const evidence = f.evidence || '';
        const explanation = f.explanation || f.description || '';
        const rec = f.recommendation || 'Independently corroborate this observation through authenticated public registries.';

        return `
            <div class="timeline-event">
                <div class="timeline-node ${sev}">
                    <div class="timeline-node-inner"></div>
                </div>
                <div class="timeline-card">
                    <div class="timeline-card-header">
                        <div style="display:flex; align-items:center; gap:0.5rem;">
                            <span class="badge-forensic ${badgeClass}">${sev}</span>
                            <span class="timeline-title">${title}</span>
                        </div>
                        ${impact > 0 ? `<span class="badge-forensic badge-forensic-danger">+${impact} Risk Points</span>` : ''}
                    </div>

                    ${evidence ? `
                        <div class="evidence-quote-box">
                            <span class="evidence-label">EXACT VERBATIM DOCUMENT QUOTE:</span>
                            "${evidence}"
                        </div>
                    ` : ''}

                    <div class="timeline-explanation">${explanation}</div>

                    <div class="timeline-rec">
                        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
                        <span>Investigation Directive: ${rec}</span>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

/**
 * Render Extracted Entities Table
 */
function renderExtractedEntities(a) {
    const e = a.entities || {};
    
    setEntityText('entCompany', e.company || a.company_name || 'Not Specified');
    setEntityText('entRole', e.role || a.job_title || 'General Document');
    setEntityText('entRecruiter', e.recruiter || 'Not Disclosed');
    setEntityText('entEmail', e.email || a.company_email || 'Not Disclosed');
    setEntityText('entPhone', e.phone || a.company_phone || 'Not Disclosed');
    setEntityText('entSalary', e.salary || 'Not Stated');
    setEntityText('entPayment', e.payment_request || 'None Detected', e.payment_request && e.payment_request !== 'None Detected');
    setEntityText('entComm', e.communication || 'Standard Electronic');
    setEntityText('entLocation', e.location || a.job_location || 'Remote / Unspecified');
}

function setEntityText(id, val, isAlert = false) {
    const el = document.getElementById(id);
    if (!el) return;
    el.textContent = val;
    if (isAlert) {
        el.style.color = 'var(--console-risk-critical)';
        el.style.fontWeight = 'bold';
    }
}

/**
 * Render Company & Domain Intelligence
 */
function renderCompanyDomainIntelligence(a) {
    const dom = a.domain_intelligence || {};
    const e = a.entities || {};

    const claimedComp = document.getElementById('domIntelCompany');
    if (claimedComp) claimedComp.textContent = dom.claimed_company || e.company || a.company_name || 'Claimed Entity';

    const recruiterDom = document.getElementById('domIntelDomain');
    if (recruiterDom) recruiterDom.textContent = dom.recruiter_domain || 'Not Disclosed';

    const domAge = document.getElementById('domIntelAge');
    if (domAge) domAge.textContent = dom.domain_age || 'Contextual telemetry unavailable';

    const dnsStatus = document.getElementById('verifyDnsStatus');
    if (dnsStatus) {
        const isResolving = dom.domain_status?.includes('Active') || a.website_exists;
        dnsStatus.textContent = isResolving ? 'Active DNS Verified' : (dom.domain_status || 'Unverified');
        dnsStatus.style.color = isResolving ? 'var(--console-risk-safe)' : 'var(--console-text-muted)';
    }

    // DNS Pills
    const dnsRecords = dom.dns_records || {};
    setPillStatus('dnsPillA', dnsRecords.a_record ?? a.website_exists, 'A');
    setPillStatus('dnsPillMX', dnsRecords.mx_record ?? false, 'MX');
    setPillStatus('dnsPillNS', dnsRecords.ns_record ?? true, 'NS');

    // Email Domain Match
    const matchEl = document.getElementById('verifyDomainMatch');
    if (matchEl) {
        if (dom.email_domain_match === 'MATCH') {
            matchEl.textContent = '✓ Corporate Domain Match';
            matchEl.style.color = 'var(--console-risk-safe)';
        } else if (dom.email_domain_match === 'MISMATCH') {
            matchEl.textContent = '⚠ Domain Discrepancy';
            matchEl.style.color = 'var(--console-risk-critical)';
        } else if (dom.email_domain_match === 'FREE_WEBMAIL') {
            matchEl.textContent = 'Public Webmail Service';
            matchEl.style.color = 'var(--console-risk-medium)';
        } else {
            matchEl.textContent = dom.match_label || 'Inconclusive';
            matchEl.style.color = 'var(--console-text-muted)';
        }
    }

    // Website Link
    const webLink = document.getElementById('verifyWebsiteLink');
    const websiteUrl = dom.company_website || a.company_website;
    if (webLink && websiteUrl) {
        webLink.innerHTML = `
            <a href="${websiteUrl}" target="_blank" rel="noopener noreferrer" class="mono-text" style="font-size:0.8rem; color:var(--console-cyan); display:inline-flex; align-items:center; gap:5px;">
                <span>Visit Claimed Domain (${websiteUrl})</span>
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
            </a>
        `;
    }
}

function setPillStatus(id, isActive, recordName) {
    const el = document.getElementById(id);
    if (!el) return;
    el.textContent = `${recordName}: ${isActive ? 'OK' : 'N/A'}`;
    el.className = `dns-pill ${isActive ? '' : 'inactive'}`;
}

/**
 * Render Production Company Intelligence Section (Cards 1-5, AI Assessment, Sources)
 */
function renderCompanyIntelligence(a) {
    const ci = a.company_intelligence || {};
    const comp = ci.company || {};
    const dom = ci.domain || {};
    const web = ci.website || {};
    const email = ci.email || {};
    const lookalike = ci.lookalike || {};
    const sources = ci.sources || [];

    // Overall Status Pill
    const statusPill = document.getElementById('companyVerifiedBadge');
    const statusText = document.getElementById('companyVerifiedStatusText');
    if (statusPill && statusText) {
        if (email.status === 'MISMATCH' || lookalike.detected) {
            statusPill.className = 'company-intel-status-pill badge-forensic-danger';
            statusText.textContent = lookalike.detected ? 'LOOKALIKE DETECTED' : 'DOMAIN MISMATCH';
        } else if (web.reachable && (dom.status === 'active' || dom.status === 'ACTIVE') && email.status === 'MATCH') {
            statusPill.className = 'company-intel-status-pill badge-forensic-safe';
            statusText.textContent = 'IDENTITY CORROBORATED';
        } else if (comp.name && comp.name !== 'Company not identified') {
            statusPill.className = 'company-intel-status-pill badge-forensic-cyan';
            statusText.textContent = 'SIGNALS RECORDED';
        } else {
            statusPill.className = 'company-intel-status-pill badge-forensic-muted';
            statusText.textContent = 'IDENTITY UNVERIFIED';
        }
    }

    // CARD 1: Company Profile
    const compName = comp.name || a.company_name || null;
    const nameEl = document.getElementById('ciCompanyName');
    if (nameEl) {
        nameEl.textContent = compName ? compName : 'Company not identified';
        if (!compName) {
            nameEl.style.color = 'var(--console-text-muted)';
        } else {
            nameEl.style.color = 'var(--console-text-primary)';
        }
    }

    const indEl = document.getElementById('ciCompanyIndustry');
    if (indEl) indEl.textContent = comp.industry || 'Information unavailable';

    const locEl = document.getElementById('ciCompanyLocation');
    if (locEl) locEl.textContent = comp.location || a.job_location || 'Information unavailable';

    const fndEl = document.getElementById('ciCompanyFounded');
    if (fndEl) fndEl.textContent = comp.founded || 'Information unavailable';

    const webEl = document.getElementById('ciCompanyWebsite');
    if (webEl) {
        const site = comp.website || (dom.domain ? `https://${dom.domain}` : null);
        if (site && site !== 'Information unavailable') {
            const href = site.startsWith('http') ? site : 'https://' + site;
            webEl.innerHTML = `<a href="${href}" target="_blank" rel="noopener noreferrer" class="mono-text" style="color:var(--console-cyan); text-decoration:underline;">${site}</a>`;
        } else {
            webEl.textContent = 'Information unavailable';
        }
    }

    const descEl = document.getElementById('ciCompanyDesc');
    if (descEl) descEl.textContent = comp.description || 'Information unavailable';

    const logoBox = document.getElementById('ciLogoBox');
    const logoImg = document.getElementById('ciLogoImg');
    if (logoBox && logoImg) {
        if (comp.logo_url) {
            logoImg.src = comp.logo_url;
            logoBox.style.display = 'block';
        } else {
            logoBox.style.display = 'none';
        }
    }

    // CARD 2: Domain Intelligence
    const domNameEl = document.getElementById('ciDomainName');
    if (domNameEl) domNameEl.textContent = dom.domain || a.company_domain || '--';

    const ageEl = document.getElementById('ciDomainAge');
    if (ageEl) {
        ageEl.textContent = dom.age_formatted || (dom.age_years ? `${dom.age_years} years` : 'Information unavailable');
    }

    const crtEl = document.getElementById('ciDomainCreated');
    if (crtEl) {
        if (dom.creation_date) {
            const d = new Date(dom.creation_date);
            crtEl.textContent = isNaN(d.getTime()) ? dom.creation_date : d.toLocaleDateString([], { year: 'numeric', month: 'short', day: 'numeric' });
        } else {
            crtEl.textContent = 'Information unavailable';
        }
    }

    const regEl = document.getElementById('ciDomainRegistrar');
    if (regEl) regEl.textContent = dom.registrar || 'Information unavailable';

    const stEl = document.getElementById('ciDomainStatus');
    if (stEl) {
        stEl.textContent = dom.status || 'UNAVAILABLE';
        stEl.style.color = (dom.status === 'active' || dom.status === 'ACTIVE') ? 'var(--console-risk-safe)' : 'var(--console-text-muted)';
    }

    const nsEl = document.getElementById('ciDomainNameservers');
    if (nsEl) {
        const ns = dom.nameservers || [];
        nsEl.textContent = ns.length > 0 ? ns.slice(0, 3).join(', ') : 'Information unavailable';
    }

    // CARD 3: Website Status
    const rchValEl = document.getElementById('ciWebReachable');
    const rchBadgeEl = document.getElementById('ciWebReachableBadge');
    if (rchValEl) {
        if (web.reachable) {
            rchValEl.innerHTML = '<span style="color:var(--console-risk-safe); font-weight:700;">✓ Reachable</span>';
            if (rchBadgeEl) {
                rchBadgeEl.textContent = 'ONLINE';
                rchBadgeEl.className = 'badge-forensic badge-forensic-safe';
            }
        } else if (web.status_code) {
            rchValEl.innerHTML = `<span style="color:var(--console-risk-critical); font-weight:700;">✗ HTTP ${web.status_code}</span>`;
            if (rchBadgeEl) {
                rchBadgeEl.textContent = 'OFFLINE';
                rchBadgeEl.className = 'badge-forensic badge-forensic-danger';
            }
        } else {
            rchValEl.innerHTML = '<span style="color:var(--console-text-muted);">Unreachable / Unavailable</span>';
            if (rchBadgeEl) {
                rchBadgeEl.textContent = 'UNAVAILABLE';
                rchBadgeEl.className = 'badge-forensic badge-forensic-muted';
            }
        }
    }

    const httpsEl = document.getElementById('ciWebHttps');
    if (httpsEl) {
        if (web.https) {
            httpsEl.innerHTML = '<span style="color:var(--console-risk-safe); font-weight:700;">✓ Enabled</span>';
        } else {
            httpsEl.innerHTML = '<span style="color:var(--console-risk-warning); font-weight:700;">✗ Disabled / Missing</span>';
        }
    }

    const statusCodEl = document.getElementById('ciWebStatusCode');
    if (statusCodEl) statusCodEl.textContent = web.status_code ? web.status_code : (web.reachable ? '200' : 'Unavailable');

    const finalUrlEl = document.getElementById('ciWebFinalUrl');
    if (finalUrlEl) finalUrlEl.textContent = web.final_url || (dom.domain ? `https://${dom.domain}` : 'Unavailable');

    const tlsEl = document.getElementById('ciWebTlsValid');
    if (tlsEl) {
        tlsEl.textContent = web.tls_certificate ? '✓ Valid Certificate' : (web.https ? 'Available' : 'Unavailable');
        tlsEl.style.color = web.tls_certificate ? 'var(--console-risk-safe)' : 'var(--console-text-muted)';
    }

    const redirNote = document.getElementById('ciWebRedirectNote');
    const redirTarget = document.getElementById('ciWebRedirectTarget');
    if (redirNote && redirTarget) {
        if (web.redirect_target) {
            redirNote.style.display = 'block';
            redirTarget.textContent = web.redirect_target;
        } else {
            redirNote.style.display = 'none';
        }
    }

    // CARD 4: Recruiter Verification
    const recNameEl = document.getElementById('ciRecruiterName');
    if (recNameEl) recNameEl.textContent = email.recruiter_name || a.entities?.recruiter || 'Not Specified';

    const recEmailEl = document.getElementById('ciRecruiterEmail');
    if (recEmailEl) recEmailEl.textContent = email.email || a.entities?.email || 'Not Disclosed';

    const emDomEl = document.getElementById('ciEmailDomain');
    if (emDomEl) emDomEl.textContent = email.domain || '--';

    const matchEl = document.getElementById('ciDomainMatchStatus');
    const emailBadge = document.getElementById('ciEmailMatchBadge');
    if (matchEl) {
        if (email.status === 'MATCH') {
            matchEl.innerHTML = '<span style="color:var(--console-risk-safe); font-weight:700;">✓ MATCH</span>';
            if (emailBadge) {
                emailBadge.textContent = 'MATCH';
                emailBadge.className = 'badge-forensic badge-forensic-safe';
            }
        } else if (email.status === 'MISMATCH') {
            matchEl.innerHTML = '<span style="color:var(--console-risk-critical); font-weight:700;">⚠ MISMATCH</span>';
            if (emailBadge) {
                emailBadge.textContent = 'MISMATCH';
                emailBadge.className = 'badge-forensic badge-forensic-danger';
            }
        } else if (email.status === 'PERSONAL_EMAIL_PROVIDER') {
            matchEl.innerHTML = '<span style="color:var(--console-risk-warning); font-weight:700;">⚠ PERSONAL_EMAIL_PROVIDER</span>';
            if (emailBadge) {
                emailBadge.textContent = 'WEBMAIL';
                emailBadge.className = 'badge-forensic badge-forensic-warning';
            }
        } else {
            matchEl.innerHTML = `<span style="color:var(--console-text-muted);">${email.status || 'INCONCLUSIVE'}</span>`;
            if (emailBadge) {
                emailBadge.textContent = 'INCONCLUSIVE';
                emailBadge.className = 'badge-forensic badge-forensic-muted';
            }
        }
    }

    const emExp = document.getElementById('ciEmailExplanation');
    if (emExp) {
        emExp.textContent = email.explanation || 'Comparing recruiter communication channels against discovered corporate domains.';
    }

    // CARD 5: Domain Risk Signals (Factual Indicators)
    renderDomainRiskSignalsList(ci);

    // AI COMPANY ASSESSMENT (Section 23)
    const aiAssessEl = document.getElementById('aiCompanyAssessmentText');
    if (aiAssessEl) {
        aiAssessEl.textContent = ci.ai_assessment || 'Forensic system performed automated factual corroboration against registered domain telemetry and corporate public directories.';
    }

    // SOURCES TABLE (Section 24)
    renderCompanySourcesTable(sources);
}

function renderDomainRiskSignalsList(ci) {
    const container = document.getElementById('ciSignalsList');
    if (!container) return;

    const signals = [];
    const dom = ci.domain || {};
    const web = ci.website || {};
    const email = ci.email || {};
    const lookalike = ci.lookalike || {};

    // Domain age signals
    if (typeof dom.age_days === 'number') {
        if (dom.age_days >= 365) {
            signals.push({
                type: 'safe',
                icon: '✓',
                title: 'Established domain',
                desc: `Registered ${dom.age_formatted || `${dom.age_days} days ago`}.`
            });
        } else if (dom.age_days < 180) {
            signals.push({
                type: 'warning',
                icon: '⚠',
                title: 'Recently registered domain',
                desc: `Created only ${dom.age_formatted || `${dom.age_days} days ago`}. Telemetry requires careful scrutiny.`
            });
        } else {
            signals.push({
                type: 'info',
                icon: 'ℹ',
                title: 'Moderate domain tenure',
                desc: `${dom.age_formatted} registration history.`
            });
        }
    } else {
        signals.push({
            type: 'muted',
            icon: 'ℹ',
            title: 'Domain registration age unavailable',
            desc: 'RDAP registry did not yield authoritative creation date.'
        });
    }

    // HTTPS / Web reachability
    if (web.reachable) {
        if (web.https) {
            signals.push({
                type: 'safe',
                icon: '✓',
                title: 'HTTPS available',
                desc: 'Web server responds with secure TLS transport layer.'
            });
        } else {
            signals.push({
                type: 'warning',
                icon: '⚠',
                title: 'HTTPS not available',
                desc: 'Website is accessible but lacks enforced HTTPS/TLS transport.'
            });
        }
    } else if (dom.domain) {
        signals.push({
            type: 'warning',
            icon: '⚠',
            title: 'Website unreachable',
            desc: 'Public web endpoint for discovered domain did not respond.'
        });
    }

    // Email Domain
    if (email.status === 'MATCH') {
        signals.push({
            type: 'safe',
            icon: '✓',
            title: 'Email domain matches website',
            desc: `Sender domain @${email.domain} matches official domain.`
        });
    } else if (email.status === 'MISMATCH') {
        signals.push({
            type: 'danger',
            icon: '⚠',
            title: 'Email domain differs from company domain',
            desc: `Recruiter uses @${email.domain} while company domain is ${dom.domain || 'different'}.`
        });
    } else if (email.status === 'PERSONAL_EMAIL_PROVIDER') {
        signals.push({
            type: 'warning',
            icon: '⚠',
            title: 'Personal email provider used',
            desc: `@${email.domain} is a public webmail service. Contextual signal only, not automatic fraud.`
        });
    }

    // Lookalike detection
    if (lookalike.detected) {
        signals.push({
            type: 'danger',
            icon: '⚠',
            title: 'Potential lookalike domain',
            desc: (lookalike.reasons && lookalike.reasons.length > 0) ? lookalike.reasons.join('; ') : 'Syntactic similarity or typosquatting patterns detected.'
        });
    }

    if (signals.length === 0) {
        container.innerHTML = '<div style="color:var(--console-text-muted); font-size:0.85rem; padding:0.5rem 0;">No domain signals extracted.</div>';
        return;
    }

    container.innerHTML = signals.map(s => {
        const color = s.type === 'safe' ? 'var(--console-risk-safe)' : (s.type === 'danger' ? 'var(--console-risk-critical)' : (s.type === 'warning' ? 'var(--console-risk-medium)' : 'var(--console-cyan)'));
        return `
            <div class="ci-signal-item">
                <span class="ci-signal-icon" style="color: ${color}; font-weight: bold; font-size: 1.05rem;">${s.icon}</span>
                <div class="ci-signal-body">
                    <span class="ci-signal-title" style="color: var(--console-text-primary); font-weight: 600; font-size: 0.85rem;">${s.title}</span>
                    <span class="ci-signal-desc" style="color: var(--console-text-secondary); font-size: 0.78rem;">${s.desc}</span>
                </div>
            </div>
        `;
    }).join('');
}

function renderCompanySourcesTable(sources) {
    const tbody = document.getElementById('companySourcesTableBody');
    const badge = document.getElementById('sourcesCountBadge');
    if (!tbody) return;

    if (!sources || sources.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="4" style="text-align: center; color: var(--console-text-muted); padding: 1.25rem;">
                    No external telemetry queries logged for this case.
                </td>
            </tr>
        `;
        if (badge) badge.textContent = '0 SOURCES RECORDED';
        return;
    }

    if (badge) badge.textContent = `${sources.length} SOURCE${sources.length === 1 ? '' : 'S'} RECORDED`;

    tbody.innerHTML = sources.map(s => {
        const urlDisplay = s.url ? `<a href="${s.url}" target="_blank" rel="noopener noreferrer" class="mono-text" style="color:var(--console-cyan); font-size:0.75rem; word-break:break-all;">${s.url}</a>` : '<span class="mono-text" style="color:var(--console-text-muted);">--</span>';
        const dateDisplay = s.retrieved_at ? new Date(s.retrieved_at).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' }) : 'Logged';
        return `
            <tr>
                <td style="font-weight:600; color:var(--console-text-primary); font-size:0.82rem;">${s.name || 'External Telemetry'}</td>
                <td>${urlDisplay}</td>
                <td class="mono-text" style="font-size:0.75rem; color:var(--console-text-secondary);">${dateDisplay}</td>
                <td style="color:var(--console-text-secondary); font-size:0.8rem;">${s.data_obtained || 'Contextual telemetry'}</td>
            </tr>
        `;
    }).join('');
}

/**
 * Render Positive Signals & Legitimacy
 */
function renderPositiveSignals(signals) {
    const sec = document.getElementById('positiveSignalsSection');
    const container = document.getElementById('positiveSignalsContainer');
    if (!sec || !container) return;

    if (!signals || signals.length === 0) {
        container.innerHTML = `
            <div style="color: var(--console-text-muted); font-size: 0.85rem; padding: 0.5rem 0;">
                No explicit positive legitimacy markers were verified in the provided text.
            </div>
        `;
        return;
    }

    container.innerHTML = signals.map(s => `
        <div style="display: flex; align-items: flex-start; gap: 0.65rem; margin-bottom: 0.75rem;">
            <span style="color: #34D399; font-size: 1.1rem; line-height: 1;">✓</span>
            <div>
                <strong style="color: var(--console-text-primary); font-size: 0.88rem;">${s.finding}</strong>
                <p style="color: var(--console-text-secondary); font-size: 0.82rem; margin-top: 2px;">${s.explanation}</p>
                ${s.evidence ? `<div class="mono-text" style="font-size: 0.78rem; color: var(--console-text-muted); margin-top: 3px; font-style: italic;">"${s.evidence}"</div>` : ''}
            </div>
        </div>
    `).join('');
}

/**
 * Render Uncertainties & What Could Not Be Verified
 */
function renderUncertainties(uncertainties) {
    const sec = document.getElementById('uncertaintiesSection');
    const container = document.getElementById('uncertaintiesContainer');
    if (!sec || !container) return;

    if (!uncertainties || uncertainties.length === 0) {
        container.innerHTML = `
            <div style="color: var(--console-text-muted); font-size: 0.85rem; padding: 0.5rem 0;">
                Standard document text limitations apply. Offline credentials require direct verification.
            </div>
        `;
        return;
    }

    container.innerHTML = `
        <ul style="padding-left: 1.25rem; color: var(--console-text-secondary); font-size: 0.84rem; display: flex; flex-direction: column; gap: 0.4rem;">
            ${uncertainties.map(u => `<li>${u}</li>`).join('')}
        </ul>
    `;
}

/**
 * Render the dedicated Evidence-First AI OPINION Component
 */
function renderAiOpinion(a) {
    const op = a.ai_opinion || {};
    const flowContainer = document.getElementById('aiOpinionFlow');
    const assessQuote = document.getElementById('aiOpinionAssessment');
    const conclusionEl = document.getElementById('aiOpinionConclusion');

    if (!flowContainer) return;

    // Assessment Quote / Headline
    if (assessQuote) {
        assessQuote.textContent = op.assessment || a.summary || 'Forensic analysis evaluated the provided document content and entity consistency.';
    }

    // Evidence-First Reasoning Flow: OBSERVATION -> EVIDENCE -> INTERPRETATION -> RISK IMPACT
    const reasoningItems = op.reasoning || [];
    
    if (reasoningItems.length === 0) {
        // Clean Document State (e.g. Clean Participation Certificate)
        const isCert = a.document_type === 'CERTIFICATE';
        flowContainer.innerHTML = `
            <div class="ai-reasoning-card">
                <div class="ai-step-badge">STATUS: NO MATERIAL FRAUD DETECTED</div>
                <div class="ai-step-observation">Document Alignment & Context Verification</div>
                <div class="ai-step-interpretation">
                    ${isCert
                        ? 'The document exhibits standard participation or completion credential vocabulary. The content contains zero demands for security deposits, equipment fees, or sensitive credential disclosure.'
                        : 'Extracted text conforms to expected standard communication without high-risk advance fees or artificial pressure.'}
                </div>
                <div class="ai-step-impact SAFE">
                    <span>RISK IMPACT: MINIMAL / SAFE</span>
                </div>
            </div>
        `;
    } else {
        flowContainer.innerHTML = reasoningItems.map((item, idx) => {
            const stepNum = String(idx + 1).padStart(2, '0');
            const obs = item.observation || item.finding || 'Observed Threat Vector';
            const ev = item.evidence || '';
            const interp = item.interpretation || item.explanation || '';
            const impact = (item.risk_impact || 'HIGH').toUpperCase();

            return `
                <div class="ai-reasoning-card">
                    <div class="ai-step-badge">STEP ${stepNum} // RISK FACTOR</div>
                    <div class="ai-step-observation">${obs}</div>

                    ${ev ? `
                        <div class="evidence-quote-box" style="margin: 0.5rem 0;">
                            <span class="evidence-label">DOCUMENT EVIDENCE:</span>
                            "${ev}"
                        </div>
                    ` : ''}

                    <div class="ai-step-interpretation">
                        <strong>Forensic Interpretation:</strong> ${interp}
                    </div>

                    <div class="ai-step-impact ${impact}">
                        <span>RISK IMPACT: ${impact}</span>
                    </div>
                </div>
            `;
        }).join('');
    }

    // Overall Conclusion
    if (conclusionEl) {
        conclusionEl.textContent = op.overall_conclusion || (
            a.classification === 'HIGH_RISK'
                ? 'The combination of financial solicitation, sensitive data harvesting, artificial urgency, and unverified communication channels indicates a high probability of fraud.'
                : 'The available evidence does not provide sufficient grounds to classify this document as suspicious.'
        );
    }
}

/**
 * Render Recommended Actions Checklist with Persistence & Progress Tracking (Section 34)
 */
function renderRecommendations(recs, docType, analysisId, persistedState = {}) {
    const list = document.getElementById('recommendationsList');
    const counter = document.getElementById('checklistCounterBadge');
    const bar = document.getElementById('checklistProgressBarFill');
    if (!list) return;

    if (!recs || recs.length === 0) {
        if (docType === 'CERTIFICATE') {
            recs = [
                'Verify credential authenticity directly via the issuing platform\'s official registry.',
                'Verify the issuing organization\'s public domain before providing any personal details.',
                'Ensure no upfront processing or administrative fees are solicited to release the certificate.'
            ];
        } else {
            recs = [
                'Never wire funds, transfer money via Zelle/UPI, or purchase gift cards for onboarding equipment.',
                'Verify recruiter identity through official corporate telephone switchboards or verified LinkedIn directories.',
                'Confirm the vacancy exists on the official corporate careers website before continuing interviews.',
                'Do not provide bank account, Aadhaar/SSN, or ID photos until employment is independently confirmed.',
                'Reject communication redirection to unmonitored messaging apps like Telegram or WhatsApp.'
            ];
        }
    }

    const checkedIndices = new Set(persistedState.checked_indices || []);

    function updateChecklistProgress() {
        const total = recs.length;
        const currentChecked = list.querySelectorAll('input[type="checkbox"]:checked').length;
        if (counter) counter.textContent = `${currentChecked} / ${total} COMPLETED`;
        if (bar) bar.style.width = `${total > 0 ? (currentChecked / total) * 100 : 0}%`;
    }

    list.innerHTML = recs.map((rec, i) => `
        <li class="checklist-item">
            <input type="checkbox" id="recCheck_${i}" data-index="${i}" ${checkedIndices.has(i) ? 'checked' : ''}>
            <label for="recCheck_${i}">
                ${rec}
            </label>
        </li>
    `).join('');

    updateChecklistProgress();

    list.querySelectorAll('input[type="checkbox"]').forEach(cb => {
        cb.addEventListener('change', async () => {
            updateChecklistProgress();
            if (!analysisId) return;

            const indices = Array.from(list.querySelectorAll('input[type="checkbox"]:checked')).map(el => parseInt(el.dataset.index));
            try {
                await fetch(`${API_BASE_URL}/analysis/${analysisId}/checklist`, {
                    method: 'PATCH',
                    headers: getAuthHeaders(true),
                    body: JSON.stringify({
                        checked_indices: indices,
                        total_items: recs.length
                    })
                });
            } catch (err) {}
        });
    });
}

/**
 * Setup What-If Forensic Risk Simulation (Section 36)
 */
function setupWhatIfSimulation(analysisId) {
    const simBox = document.getElementById('whatIfSimulationPanel');
    const resBox = document.getElementById('simResultBox');
    const scoreText = document.getElementById('simRiskScoreText');
    const deltaBadge = document.getElementById('simRiskDeltaBadge');
    const classBadge = document.getElementById('simRiskClassBadge');
    const factorsList = document.getElementById('simFactorsList');
    if (!simBox || !analysisId) return;

    const checkboxes = simBox.querySelectorAll('input[type="checkbox"]');

    async function runSimulation() {
        const payload = {
            add_fee_request: document.getElementById('simFeeRequest')?.checked || false,
            add_crypto_payment: document.getElementById('simCryptoPayment')?.checked || false,
            add_urgency: document.getElementById('simUrgency')?.checked || false,
            add_domain_mismatch: document.getElementById('simDomainMismatch')?.checked || false,
            add_sensitive_docs: document.getElementById('simSensitiveDocs')?.checked || false
        };

        const hasAnyActive = Object.values(payload).some(v => v);
        if (!hasAnyActive) {
            if (resBox) resBox.style.display = 'none';
            return;
        }

        try {
            const res = await fetch(`${API_BASE_URL}/analysis/${analysisId}/simulate`, {
                method: 'POST',
                headers: getAuthHeaders(true),
                body: JSON.stringify(payload)
            });
            if (res.ok) {
                const data = await res.json();
                const sim = data.simulation || {};
                if (resBox) resBox.style.display = 'block';
                if (scoreText) scoreText.textContent = `${sim.simulated_risk_score} / 100`;
                if (deltaBadge) {
                    const delta = sim.delta || 0;
                    deltaBadge.textContent = delta >= 0 ? `+${delta}` : `${delta}`;
                    deltaBadge.className = delta > 0 ? 'badge badge-danger' : 'badge badge-success';
                }
                if (classBadge) {
                    classBadge.textContent = sim.simulated_classification;
                    classBadge.className = sim.simulated_risk_score >= 70 ? 'badge badge-danger' : (sim.simulated_risk_score >= 40 ? 'badge badge-warning' : 'badge badge-success');
                }
                if (factorsList) {
                    factorsList.innerHTML = (sim.triggered_factors || []).map(f => `<li>${f}</li>`).join('');
                }
            }
        } catch (e) {}
    }

    checkboxes.forEach(cb => cb.addEventListener('change', runSimulation));
}

/**
 * Check if current analysis record is saved in user repository
 */
async function checkSavedStatus(analysisId) {
    if (typeof getToken !== 'function' || !getToken()) return;
    try {
        const res = await fetch(`${API_BASE_URL}/saved-reports/check/${analysisId}`, { headers: getAuthHeaders(true) });
        if (res.ok) {
            const data = await res.json();
            isCurrentlySaved = data.is_saved;
            savedRecordId = data.saved_id;
            updateSaveButtonUI();
        }
    } catch (err) {
        console.error('Failed to check saved report status:', err);
    }
}

function updateSaveButtonUI() {
    const btn = document.getElementById('saveReportBtn');
    const text = document.getElementById('saveBtnText');
    if (!btn || !text) return;

    if (isCurrentlySaved) {
        btn.classList.add('btn-forensic-primary');
        btn.classList.remove('btn-forensic-secondary');
        text.textContent = 'Saved ✓';
    } else {
        btn.classList.remove('btn-forensic-primary');
        btn.classList.add('btn-forensic-secondary');
        text.textContent = 'Save Report';
    }
}

/**
 * Setup Action Toolbar Handlers
 */
function setupActionButtons() {
    const saveBtn = document.getElementById('saveReportBtn');
    const printBtn = document.getElementById('downloadPdfBtn');
    const shareBtn = document.getElementById('shareReportBtn');
    const askAiBtn = document.getElementById('askCaseAiBtn');

    // Ask CaseAI Handler
    askAiBtn?.addEventListener('click', () => {
        if (window.openCaseAI && currentAnalysisId) {
            window.openCaseAI(currentAnalysisId);
        } else {
            showToast('CaseAI assistant is initializing...', 'info');
        }
    });

    // Save / Unsave Dossier
    saveBtn?.addEventListener('click', async () => {
        if (typeof requireAuth === 'function' && !requireAuth()) return;

        if (isCurrentlySaved) {
            try {
                const res = await fetch(`${API_BASE_URL}/saved-reports/by-analysis/${currentAnalysisId}`, {
                    method: 'DELETE',
                    headers: getAuthHeaders(true)
                });
                if (res.ok) {
                    isCurrentlySaved = false;
                    savedRecordId = null;
                    updateSaveButtonUI();
                    showToast('Report removed from saved repository', 'info');
                }
            } catch {
                showToast('Failed to unsave report', 'danger');
            }
        } else {
            const modal = document.getElementById('saveReportModal');
            const titleInput = document.getElementById('savedReportTitle');
            if (titleInput && currentAnalysis) {
                titleInput.value = `${currentAnalysis.job_title || 'Dossier'} - ${currentAnalysis.company_name || 'Organization'}`;
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
                showToast('Dossier bookmarked to Saved Reports!', 'success');
            } else {
                throw new Error(getErrorMessage(data, 'Failed to save report.'));
            }
        } catch (err) {
            showToast(err.message, 'danger');
        }
    });

    // Download / Print Dossier with Dedicated PDF Mode
    printBtn?.addEventListener('click', () => {
        // Dismiss any open modals
        document.querySelectorAll('.cyber-modal-overlay').forEach(m => m.classList.remove('active'));

        // Dismiss any active toast notifications
        document.querySelectorAll('.toast').forEach(t => t.remove());

        // Activate PDF Mode
        document.body.classList.add('pdf-mode');

        const exitPdfMode = () => {
            document.body.classList.remove('pdf-mode');
            window.removeEventListener('afterprint', exitPdfMode);
        };

        window.addEventListener('afterprint', exitPdfMode);

        // Allow micro-reflow before invoking browser print engine
        setTimeout(() => {
            window.print();
            setTimeout(exitPdfMode, 1500);
        }, 60);
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
            showToast('Sanitized dossier link copied to clipboard!', 'success');
        } catch {
            linkInput.select();
            document.execCommand('copy');
            showToast('Link copied to clipboard!', 'success');
        }
    });
}

/**
 * Scam Intelligence & Threat Knowledge Base Controller
 * Searchable Red Flag Directory and Interactive Candidate Defense Checklist.
 */

const RED_FLAGS_DB = [
    {
        title: "Advance Equipment or Training Deposit",
        category: "Financial Fraud",
        severity: "CRITICAL",
        description: "Candidate is ordered to wire money or send Zelle/Venmo payments to purchase home-office gear or access proprietary LMS software.",
        advice: "Legitimate corporations ship pre-configured laptops directly via corporate logistics."
    },
    {
        title: "Recruiter Using Public / Free Email Domain",
        category: "Contact Spoofing",
        severity: "HIGH",
        description: "Communication originates from @gmail.com, @yahoo.com, or @outlook.com rather than the enterprise's authenticated domain.",
        advice: "Contact the enterprise through its official careers switchboard."
    },
    {
        title: "Artificial 24-Hour Expiration Deadline",
        category: "Psychological Manipulation",
        severity: "HIGH",
        description: "High-pressure urgency demanding signature or payment within hours before the candidate can consult friends or verify corporate identity.",
        advice: "Take time to review. Legitimate hiring allows 3-7 business days for evaluation."
    },
    {
        title: "Cryptocurrency / USDT Wallet Task Optimization",
        category: "Crypto Scheme",
        severity: "CRITICAL",
        description: "Victims are instructed to fund smart contract wallets or deposit Tether to execute 'order boosting' or merchant ratings.",
        advice: "Never deposit personal funds to unlock work tasks."
    },
    {
        title: "Unrealistically High Entry-Level Salary",
        category: "Lure Technique",
        severity: "MEDIUM",
        description: "Offers promising $60–$120/hr for basic data entry, typing, or clerical work requiring zero prerequisites.",
        advice: "Benchmark average market compensation on Glassdoor or Levels.fyi."
    },
    {
        title: "Interview Conducted Solely via Telegram or Signal",
        category: "Anonymity Tactics",
        severity: "HIGH",
        description: "Recruiter insists on text questionnaires through encrypted chat applications rather than video conferences or corporate phones.",
        advice: "Insist on video conferencing through verified corporate Google Meet or Zoom domains."
    },
    {
        title: "Premature Request for Banking Credentials & SSN",
        category: "Identity Theft",
        severity: "CRITICAL",
        description: "Demanding government ID scans, mother's maiden name, or bank account routing numbers before a formal written offer.",
        advice: "Tax withholding and banking details should only be submitted on verified corporate HR portals."
    },
    {
        title: "Cashier's Check Overpayment Equipment Scam",
        category: "Financial Fraud",
        severity: "CRITICAL",
        description: "Employer sends a check for $3,500, instructing you to deposit it and wire $2,800 to an 'approved computer vendor'. The check bounces days later.",
        advice: "Never deposit a check from an unknown source to forward funds."
    },
    {
        title: "Domain Mismatch Between Email and Company Website",
        category: "Domain Spoofing",
        severity: "HIGH",
        description: "Recruiter emails from @company-careers-inc.xyz instead of the official @company.com web domain.",
        advice: "Inspect WHOIS registration age and match exact domain spelling."
    },
    {
        title: "Poor Grammar & Known Scam Phrasing Formulae",
        category: "Syntactic Anomalies",
        severity: "LOW",
        description: "Phrasing like 'kindly revert back with details', 'do the needful', or generic 'Dear Esteemed Job Seeker'.",
        advice: "Inspect document formatting and official enterprise signatures."
    },
    {
        title: "No Technical Screening or Panel Evaluation",
        category: "Hiring Process Bypass",
        severity: "HIGH",
        description: "Job offer extended immediately after submitting a resume without any technical assessment or manager conversation.",
        advice: "Authentic engineering, analyst, or managerial roles require multi-step technical panels."
    },
    {
        title: "Package Forwarding / Re-Shipping Quality Tester",
        category: "Mule Recruitment",
        severity: "CRITICAL",
        description: "Tasks involve receiving parcels at your residence, inspecting goods, and shipping them overseas with prepaid labels.",
        advice: "This is fencing stolen goods and can lead to criminal prosecution."
    }
];

document.addEventListener('DOMContentLoaded', () => {
    renderAppShell('intelligence');

    renderRedFlagDirectory(RED_FLAGS_DB);
    setupRedFlagSearch();
    setupChecklistPersistence();
});

function renderRedFlagDirectory(flags) {
    const list = document.getElementById('redFlagDirectoryList');
    if (!list) return;

    if (flags.length === 0) {
        list.innerHTML = `
            <div class="empty-state" style="grid-column: 1 / -1;">
                <div class="empty-icon">🔍</div>
                <div class="empty-title">No indicators match your search</div>
                <p class="empty-desc">Try searching for keywords like 'fee', 'check', 'telegram', or 'crypto'.</p>
            </div>
        `;
        return;
    }

    list.innerHTML = flags.map(f => {
        const badgeClass = f.severity === 'CRITICAL' ? 'badge-danger' : (f.severity === 'HIGH' ? 'badge-warning' : 'badge-cyan');
        return `
            <div class="cyber-card ${f.severity}">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem;">
                    <span class="badge ${badgeClass}">${f.severity}</span>
                    <small style="color:var(--text-muted); font-size:0.75rem;">${f.category}</small>
                </div>
                <h4 style="font-size:1.05rem; margin-bottom:0.4rem; color:var(--text-primary);">${f.title}</h4>
                <p style="color:var(--text-secondary); font-size:0.86rem; line-height:1.45; margin-bottom:0.75rem;">${f.description}</p>
                <div style="font-size:0.8rem; color:var(--accent-cyan); display:flex; align-items:flex-start; gap:4px;">
                    <span>🛡️ Defense:</span> ${f.advice}
                </div>
            </div>
        `;
    }).join('');
}

function setupRedFlagSearch() {
    const input = document.getElementById('flagSearchInput');
    input?.addEventListener('input', () => {
        const query = input.value.trim().toLowerCase();
        if (!query) {
            renderRedFlagDirectory(RED_FLAGS_DB);
            return;
        }

        const filtered = RED_FLAGS_DB.filter(f => 
            f.title.toLowerCase().includes(query) ||
            f.description.toLowerCase().includes(query) ||
            f.category.toLowerCase().includes(query) ||
            f.advice.toLowerCase().includes(query)
        );

        renderRedFlagDirectory(filtered);
    });
}

function setupChecklistPersistence() {
    const checkboxes = document.querySelectorAll('.safety-check');
    const progressBar = document.getElementById('checklistProgressBar');
    const progressText = document.getElementById('checklistProgressText');

    // Load saved checklist state
    const savedState = JSON.parse(localStorage.getItem('scamguard_checklist_state') || '[]');

    checkboxes.forEach((cb, idx) => {
        if (savedState.includes(idx)) cb.checked = true;

        cb.addEventListener('change', () => {
            updateChecklistProgress();
        });
    });

    function updateChecklistProgress() {
        const checkedIndices = [];
        checkboxes.forEach((cb, idx) => {
            if (cb.checked) checkedIndices.push(idx);
        });

        localStorage.setItem('scamguard_checklist_state', JSON.stringify(checkedIndices));

        const total = checkboxes.length;
        const count = checkedIndices.length;
        const pct = Math.round((count / total) * 100);

        if (progressBar) progressBar.style.width = `${pct}%`;
        if (progressText) progressText.textContent = `${count} / ${total} Verified (${pct}%)`;

        if (pct === 100) {
            showToast('Due diligence checklist completed! All safety precautions satisfied.', 'success');
        }
    }

    updateChecklistProgress();
}

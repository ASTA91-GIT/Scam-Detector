/**
 * Analysis Workspace Controller
 * Handles text input, drag & drop file upload, sample loaders, URL scanner,
 * multi-step scanning animation, and redirection to forensic result dossier.
 */

document.addEventListener('DOMContentLoaded', () => {
    renderAppShell('analyze');
    if (!requireAuth()) return;

    setupModeSwitching();
    setupTextEditor();
    setupFileUpload();
    setupSampleLoaders();
    setupUrlScanner();
    setupFormSubmission();

    // Check query params if user clicked "Upload Doc" from dashboard
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('mode') === 'file') {
        document.getElementById('tabModeFile')?.click();
    }
});

// 1. Mode Switching
function setupModeSwitching() {
    const tabs = document.querySelectorAll('.mode-tab-btn');
    const secText = document.getElementById('sectionText');
    const secFile = document.getElementById('sectionFile');
    const secUrl = document.getElementById('sectionUrl');

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            const mode = tab.dataset.mode;

            if (secText) secText.style.display = mode === 'text' ? 'block' : 'none';
            if (secFile) secFile.style.display = mode === 'file' ? 'block' : 'none';
            if (secUrl) secUrl.style.display = mode === 'url' ? 'block' : 'none';
        });
    });
}

// 2. Text Editor & Counter
function setupTextEditor() {
    const textarea = document.getElementById('jobText');
    const counter = document.getElementById('charCounter');
    const clearBtn = document.getElementById('clearTextBtn');
    const pasteBtn = document.getElementById('pasteClipboardBtn');

    if (!textarea) return;

    function updateCounter() {
        const text = textarea.value.trim();
        const chars = text.length;
        const words = text ? text.split(/\s+/).length : 0;
        if (counter) counter.textContent = `${chars} characters | ${words} words`;
    }

    textarea.addEventListener('input', updateCounter);

    clearBtn?.addEventListener('click', () => {
        textarea.value = '';
        updateCounter();
        textarea.focus();
    });

    pasteBtn?.addEventListener('click', async () => {
        try {
            const clipText = await navigator.clipboard.readText();
            if (clipText) {
                textarea.value = clipText;
                updateCounter();
                showToast('Pasted content from clipboard', 'info');
            }
        } catch {
            showToast('Unable to read clipboard automatically. Please press Ctrl+V.', 'warning');
        }
    });
}

// 3. File Upload & Drag & Drop
let selectedFile = null;

function setupFileUpload() {
    const dropzone = document.getElementById('fileDropzone');
    const fileInput = document.getElementById('fileUploadInput');
    const previewCard = document.getElementById('filePreviewCard');
    const previewName = document.getElementById('previewFileName');
    const previewSize = document.getElementById('previewFileSize');
    const removeBtn = document.getElementById('removeFileBtn');

    if (!dropzone || !fileInput) return;

    dropzone.addEventListener('click', () => fileInput.click());

    fileInput.addEventListener('change', () => {
        if (fileInput.files.length > 0) {
            handleSelectedFile(fileInput.files[0]);
        }
    });

    dropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropzone.classList.add('drag-over');
    });

    dropzone.addEventListener('dragleave', () => {
        dropzone.classList.remove('drag-over');
    });

    dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropzone.classList.remove('drag-over');
        if (e.dataTransfer.files.length > 0) {
            fileInput.files = e.dataTransfer.files;
            handleSelectedFile(e.dataTransfer.files[0]);
        }
    });

    function handleSelectedFile(file) {
        if (!file) return;
        selectedFile = file;

        if (previewName) previewName.textContent = file.name;
        if (previewSize) {
            const kb = (file.size / 1024).toFixed(1);
            const sizeStr = file.size > 1024 * 1024 ? `${(file.size / (1024 * 1024)).toFixed(2)} MB` : `${kb} KB`;
            previewSize.textContent = `${sizeStr} &bull; Ready for forensic extraction`;
        }

        dropzone.style.display = 'none';
        if (previewCard) previewCard.style.display = 'flex';
        showToast(`Document "${file.name}" staged for analysis`, 'success');
    }

    removeBtn?.addEventListener('click', () => {
        selectedFile = null;
        fileInput.value = '';
        if (previewCard) previewCard.style.display = 'none';
        dropzone.style.display = 'flex';
    });
}

// 4. Sample Loaders
function setupSampleLoaders() {
    const textarea = document.getElementById('jobText');
    const compName = document.getElementById('companyName');
    const compEmail = document.getElementById('companyEmail');
    const compWeb = document.getElementById('companyWebsite');
    const jobTitle = document.getElementById('jobTitle');

    // Crypto Scam Sample
    document.getElementById('sampleCrypto')?.addEventListener('click', () => {
        document.getElementById('tabModeText')?.click();
        if (textarea) {
            textarea.value = `URGENT OFFER: Online Task Processing Agent & Crypto Optimization Specialist.
Guaranteed earnings of $350 to $800 daily working 1 hour from home. No interview or prior experience needed!
Immediate opening: To activate your VIP Merchant terminal and receive your starter funds, you must deposit 100 USDT into the smart contract address for verification.
All funds are guaranteed and 100% refundable upon completion of 38 daily order submissions. Act right away! Reply ASAP on Telegram @HR_FastCryptoRecruit to start immediately!`;
        }
        if (compName) compName.value = 'Global Decentralized Tasks Ltd';
        if (jobTitle) jobTitle.value = 'Crypto Task Specialist';
        if (compEmail) compEmail.value = 'fastrecruitment99@gmail.com';
        if (compWeb) compWeb.value = 'https://global-task-reward.xyz';
        document.getElementById('charCounter')?.dispatchEvent(new Event('input'));
        showToast('Loaded realistic crypto task scam sample', 'info');
    });

    // Advance Fee Scam Sample
    document.getElementById('sampleFee')?.addEventListener('click', () => {
        document.getElementById('tabModeText')?.click();
        if (textarea) {
            textarea.value = `CONGRATULATIONS! You have been selected for the position of Senior Executive Assistant.
Salary: $95,000 / year + Comprehensive Health & 401(k) matching.
Before issuing your laptop and equipment courier, you are required to pay a refundable security deposit and training registration fee of $320 via Zelle or wire transfer to our certified vendor.
Kindly revert back immediately with your bank account number and routing number for direct deposit payroll enrollment. This offer expires today at 5:00 PM EST.`;
        }
        if (compName) compName.value = 'Apex Corporate Services';
        if (jobTitle) jobTitle.value = 'Senior Executive Assistant';
        if (compEmail) compEmail.value = 'hr.apexcorp@outlook.com';
        if (compWeb) compWeb.value = 'https://apex-corporate-portal.biz';
        showToast('Loaded advance training fee scam sample', 'info');
    });

    // Legitimate Offer Sample
    document.getElementById('sampleLegit')?.addEventListener('click', () => {
        document.getElementById('tabModeText')?.click();
        if (textarea) {
            textarea.value = `Dear Candidate,
Following your technical interview panel and portfolio review with our engineering leadership, we are delighted to extend a formal offer of employment for the role of Senior Frontend Engineer at CloudScale Technologies.
Your starting base salary will be $135,000 annualized, accompanied by equity participation and full medical coverage.
Please review the attached formal compensation breakdown and employee handbook. Standard onboarding documentation will be processed through our secure enterprise HR portal at https://cloudscale.io/careers following signature. No payment or equipment fees will ever be requested.
Best regards,
Talent Acquisition Team, CloudScale Technologies`;
        }
        if (compName) compName.value = 'CloudScale Technologies';
        if (jobTitle) jobTitle.value = 'Senior Frontend Engineer';
        if (compEmail) compEmail.value = 'careers@cloudscale.io';
        if (compWeb) compWeb.value = 'https://cloudscale.io';
        showToast('Loaded legitimate corporate tech offer sample', 'info');
    });
}

// 5. URL Scanner
function setupUrlScanner() {
    const runBtn = document.getElementById('runUrlScanBtn');
    const input = document.getElementById('scanUrlInput');
    const resultBox = document.getElementById('urlScanResult');
    const compName = document.getElementById('companyName');

    runBtn?.addEventListener('click', async () => {
        const url = input.value.trim();
        if (!url) {
            showToast('Please enter a valid URL to scan.', 'warning');
            return;
        }

        runBtn.disabled = true;
        runBtn.textContent = 'Scanning...';
        resultBox.style.display = 'block';
        resultBox.innerHTML = '<div class="spinner"></div> Performing domain & SSL heuristics...';

        try {
            const res = await fetch(`${API_BASE_URL}/analysis/scan-url`, {
                method: 'POST',
                headers: getAuthHeaders(true),
                body: JSON.stringify({ url, company_name: compName?.value.trim() || '' })
            });
            const data = await res.json();

            if (!res.ok) throw new Error(data.error || 'Scan failed');

            const scan = data.scan || {};
            const isDanger = scan.risk_level === 'High Risk';
            const badgeClass = isDanger ? 'badge-danger' : (scan.risk_level === 'Safe' ? 'badge-safe' : 'badge-warning');

            resultBox.innerHTML = `
                <div style="background:var(--bg-surface); border:1px solid var(--border-medium); border-radius:var(--radius-md); padding:1.25rem;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.75rem;">
                        <strong>Domain: ${scan.domain}</strong>
                        <span class="badge ${badgeClass}">${scan.risk_level} (${scan.score}/100)</span>
                    </div>
                    <ul style="padding-left:1.2rem; font-size:0.85rem; color:var(--text-secondary); display:flex; flex-direction:column; gap:4px;">
                        ${(scan.findings || []).map(f => `<li>${f}</li>`).join('')}
                    </ul>
                </div>
            `;

        } catch (err) {
            resultBox.innerHTML = `<div style="color:var(--risk-danger); font-size:0.88rem;">${err.message}</div>`;
        } finally {
            runBtn.disabled = false;
            runBtn.textContent = 'Scan URL';
        }
    });
}

// 6. Form Submission & Multi-Step Scanning Progress
function setupFormSubmission() {
    const form = document.getElementById('analyzeForm');
    const progressModal = document.getElementById('scanProgressModal');
    const progressBar = document.getElementById('scanProgressBar');
    const submitBtn = document.getElementById('submitScanBtn');

    form?.addEventListener('submit', async (e) => {
        e.preventDefault();

        const text = document.getElementById('jobText').value.trim();
        const company_name = document.getElementById('companyName').value.trim();
        const job_title = document.getElementById('jobTitle').value.trim();
        const company_email = document.getElementById('companyEmail').value.trim();
        const company_website = document.getElementById('companyWebsite').value.trim();
        const company_phone = document.getElementById('companyPhone').value.trim();
        const job_location = document.getElementById('jobLocation').value.trim();

        if (!text && !selectedFile) {
            showToast('Please paste offer text or upload a document.', 'warning');
            return;
        }

        // Show progress modal
        progressModal?.classList.add('active');
        submitBtn.disabled = true;

        // Step animation timers
        updateStep(1, 20);
        const timer1 = setTimeout(() => updateStep(2, 40), 500);
        const timer2 = setTimeout(() => updateStep(3, 65), 1100);
        const timer3 = setTimeout(() => updateStep(4, 85), 1700);

        try {
            let res;
            if (selectedFile) {
                const formData = new FormData();
                formData.append('file', selectedFile);
                if (text) formData.append('text', text);
                if (company_name) formData.append('company_name', company_name);
                if (job_title) formData.append('job_title', job_title);
                if (company_email) formData.append('company_email', company_email);
                if (company_website) formData.append('company_website', company_website);
                if (company_phone) formData.append('company_phone', company_phone);
                if (job_location) formData.append('job_location', job_location);

                res = await fetch(`${API_BASE_URL}/analysis/analyze`, {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${getToken()}` },
                    body: formData
                });
            } else {
                res = await fetch(`${API_BASE_URL}/analysis/analyze`, {
                    method: 'POST',
                    headers: getAuthHeaders(true),
                    body: JSON.stringify({
                        text,
                        company_name,
                        job_title,
                        company_email,
                        company_website,
                        company_phone,
                        job_location
                    })
                });
            }

            const data = await res.json();

            if (!res.ok) {
                throw new Error(data.error || 'Forensic analysis failed.');
            }

            // Complete animation
            clearTimeout(timer1);
            clearTimeout(timer2);
            clearTimeout(timer3);

            updateStep(5, 100);

            const result = data.result || {};
            const analysisId = result.analysis_id || result._id;

            showToast('Forensic analysis completed! Loading dossier...', 'success');
            setTimeout(() => {
                window.location.href = `result.html?id=${analysisId}`;
            }, 600);

        } catch (err) {
            progressModal?.classList.remove('active');
            submitBtn.disabled = false;
            showToast(err.message, 'danger');
        }
    });

    function updateStep(stepNum, progressPct) {
        if (progressBar) progressBar.style.width = `${progressPct}%`;
        const steps = ['stepUpload', 'stepExtract', 'stepHeuristics', 'stepDomain', 'stepDossier'];
        steps.forEach((id, index) => {
            const el = document.getElementById(id);
            if (!el) return;
            if (index + 1 < stepNum) {
                el.className = 'scan-step-item completed';
                el.querySelector('.scan-step-icon').textContent = '✓';
            } else if (index + 1 === stepNum) {
                el.className = 'scan-step-item active';
                el.querySelector('.scan-step-icon').textContent = stepNum;
            } else {
                el.className = 'scan-step-item';
                el.querySelector('.scan-step-icon').textContent = index + 1;
            }
        });
    }
}

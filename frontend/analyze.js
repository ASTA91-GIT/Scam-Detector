// analyze.js
// API_BASE_URL & getAuthHeaders() come from auth.js

const form = document.getElementById('analysisForm');
const fileInput = document.getElementById('fileInput');
const fileUploadArea = document.getElementById('fileUploadArea');
const fileName = document.getElementById('fileName');
const resultContainer = document.getElementById('resultContainer');

/* =========================
   TAB SWITCHING
   ========================= */

const tabButtons = document.querySelectorAll('.tab-btn');
const tabContents = document.querySelectorAll('.tab-content');

tabButtons.forEach(btn => {
    btn.addEventListener('click', () => {
        const target = btn.dataset.tab;

        tabButtons.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');

        tabContents.forEach(tab => tab.classList.remove('active'));
        document.getElementById(`${target}Tab`).classList.add('active');
    });
});

/* =========================
   FILE UPLOAD UI (FIXED)
   ========================= */

fileUploadArea.addEventListener('click', () => fileInput.click());

fileInput.addEventListener('change', () => {
    handleFileSelected(fileInput.files[0]);
});

fileUploadArea.addEventListener('dragover', e => {
    e.preventDefault();
    fileUploadArea.classList.add('drag-over');
});

fileUploadArea.addEventListener('dragleave', () => {
    fileUploadArea.classList.remove('drag-over');
});

fileUploadArea.addEventListener('drop', e => {
    e.preventDefault();
    fileUploadArea.classList.remove('drag-over');

    if (e.dataTransfer.files.length > 0) {
        fileInput.files = e.dataTransfer.files;
        handleFileSelected(e.dataTransfer.files[0]);
    }
});

/* =========================
   FILE SELECT HANDLER
   ========================= */

function handleFileSelected(file) {
    if (!file) return;

    fileName.classList.remove('hidden');
    fileName.innerHTML = `
        ✅ <strong>${file.name}</strong><br>
        <small>File ready for analysis</small>
    `;

    // Visual success state
    fileUploadArea.style.borderColor = '#10b981';
    fileUploadArea.style.background = 'rgba(16, 185, 129, 0.08)';
}


/* =========================
   FORM SUBMIT
   ========================= */

form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const analyzeBtnText = document.getElementById('analyzeBtnText');
    const analyzeSpinner = document.getElementById('analyzeSpinner');

    hideError('errorMessage');

    const jobText = document.getElementById('jobText').value.trim();
    const companyEmail = document.getElementById('companyEmail').value.trim();
    const companyWebsite = document.getElementById('companyWebsite').value.trim();
    const file = fileInput.files[0];

    if (!jobText && !file) {
        showError('errorMessage', 'Please paste text OR upload a file');
        return;
    }

    analyzeBtnText.style.display = 'none';
    analyzeSpinner.style.display = 'inline-block';

    try {
        let response;

        // FILE ANALYSIS
        if (file) {
            const formData = new FormData();
            formData.append('file', file);
            if (companyEmail) formData.append('company_email', companyEmail);
            if (companyWebsite) formData.append('company_website', companyWebsite);

            response = await fetch(`${API_BASE_URL}/analysis/analyze`, {
                method: 'POST',
                headers: {
                    Authorization: `Bearer ${localStorage.getItem('token')}`
                },
                body: formData
            });

            // TEXT ANALYSIS
        } else {
            response = await fetch(`${API_BASE_URL}/analysis/analyze`, {
                method: 'POST',
                headers: getAuthHeaders(true),
                body: JSON.stringify({
                    text: jobText,
                    company_email: companyEmail,
                    company_website: companyWebsite
                })
            });
        }

        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'Analysis failed');

        const result = data.result || {};

        /* =========================
           POPULATE RESULT UI
           ========================= */

        resultContainer.classList.remove('hidden');

        // SCORE SUMMARY
        document.getElementById('riskLevelTitle').innerText =
            `Risk Level: ${result.risk_level || 'Unknown'}`;

        document.getElementById('trustScoreText').innerText =
            `Trust Score: ${result.trust_score ?? '--'}`;

        // AI REASONING
        const aiList = document.getElementById('aiReasoningList');
        aiList.innerHTML = '';
        (result.explanations || []).forEach(reason => {
            const li = document.createElement('li');
            li.textContent = reason;
            aiList.appendChild(li);
        });

        if (aiList.children.length === 0) {
            aiList.innerHTML = '<li>No strong scam patterns detected.</li>';
        }

        // =========================
        // AI DETAILED EXPLANATION
        // =========================
        const aiExplanationCard = document.getElementById('aiExplanationCard');
        const aiExplanationText = document.getElementById('aiExplanationText');

        if (result.ai_explanation && result.ai_explanation.trim() !== "") {
            aiExplanationCard.classList.remove('hidden');
            aiExplanationText.textContent = result.ai_explanation;
        } else {
            aiExplanationCard.classList.add('hidden');
        }




        // RED FLAGS
        const redFlagsList = document.getElementById('redFlagsList');
        redFlagsList.innerHTML = '';
        (result.red_flags || []).forEach(flag => {
            const li = document.createElement('li');
            li.textContent = flag;
            redFlagsList.appendChild(li);
        });

        if (redFlagsList.children.length === 0) {
            redFlagsList.innerHTML = '<li>No major red flags found.</li>';
        }

        // RECOMMENDATIONS
        const recommendationList = document.getElementById('recommendationList');
        recommendationList.innerHTML = '';
        (result.recommendations || []).forEach(rec => {
            const li = document.createElement('li');
            li.textContent = rec;
            recommendationList.appendChild(li);
        });

        if (recommendationList.children.length === 0) {
            recommendationList.innerHTML =
                '<li>This offer appears safe. Continue normal verification.</li>';
        }

        // Scroll to result
        resultContainer.scrollIntoView({ behavior: 'smooth' });

    } catch (error) {
        console.error('Analysis error:', error);
        showError('errorMessage', error.message);
    } finally {
        analyzeBtnText.style.display = 'inline';
        analyzeSpinner.style.display = 'none';
    }
});
/* =========================
   NEW ANALYSIS / RESET
   ========================= */

document.addEventListener('DOMContentLoaded', () => {
    const resetBtn = document.getElementById('resetAnalysisBtn');

    if (!resetBtn) return;
    resetBtn.addEventListener('click', () => {
        document.getElementById('jobText').value = '';
        document.getElementById('companyEmail').value = '';
        document.getElementById('companyWebsite').value = '';
        fileInput.value = '';

        fileName.classList.add('hidden');
        fileName.innerHTML = '';

        fileUploadArea.style.borderColor = '';
        fileUploadArea.style.background = '';

        resultContainer.classList.add('hidden');
        window.scrollTo({ top: 0, behavior: 'smooth' });
    });
});

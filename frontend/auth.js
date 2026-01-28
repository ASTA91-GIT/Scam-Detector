// auth.js
// SINGLE source of API configuration
const API_BASE_URL = 'http://localhost:5000/api';

/* =========================
   AUTH CHECK
   ========================= */
function checkAuth(redirect = true) {
    const token = localStorage.getItem('token');

    if (!token && redirect) {
        if (
            !window.location.pathname.includes('login.html') &&
            !window.location.pathname.includes('signup.html') &&
            !window.location.pathname.includes('index.html')
        ) {
            window.location.href = 'login.html';
        }
    }

    return token;
}

/* =========================
   AUTH HEADERS (FIXED)
   ========================= */
// isJson = true  → application/json
// isJson = false → FormData (browser sets headers)
function getAuthHeaders(isJson = true) {
    const token = localStorage.getItem('token');

    const headers = {
        'Authorization': `Bearer ${token}`
    };

    if (isJson) {
        headers['Content-Type'] = 'application/json';
    }

    return headers;
}

/* =========================
   ERROR HELPERS
   ========================= */
function showError(elementId, message) {
    const errorEl = document.getElementById(elementId);
    if (!errorEl) return;
    errorEl.textContent = message;
    errorEl.style.display = 'block';
}

function hideError(elementId) {
    const errorEl = document.getElementById(elementId);
    if (!errorEl) return;
    errorEl.style.display = 'none';
}

/* =========================
   SIGNUP
   ========================= */
if (document.getElementById('signupForm')) {
    document.getElementById('signupForm').addEventListener('submit', async (e) => {
        e.preventDefault();

        const username = document.getElementById('username').value.trim();
        const email = document.getElementById('email').value.trim();
        const password = document.getElementById('password').value;
        const confirmPassword = document.getElementById('confirmPassword').value;

        hideError('errorMessage');

        if (!username) {
            showError('errorMessage', 'Username is required');
            return;
        }

        if (password !== confirmPassword) {
            showError('errorMessage', 'Passwords do not match');
            return;
        }

        if (password.length < 6) {
            showError('errorMessage', 'Password must be at least 6 characters');
            return;
        }

        try {
            const response = await fetch(`${API_BASE_URL}/auth/signup`, {
                method: 'POST',
                headers: getAuthHeaders(true),
                body: JSON.stringify({ username, email, password })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Signup failed');
            }

            localStorage.setItem('token', data.token);
            localStorage.setItem('user', JSON.stringify(data.user));
            window.location.href = 'dashboard.html';

        } catch (error) {
            showError('errorMessage', error.message);
        }
    });
}

/* =========================
   LOGIN
   ========================= */
if (document.getElementById('loginForm')) {
    document.getElementById('loginForm').addEventListener('submit', async (e) => {
        e.preventDefault();

        const email = document.getElementById('email').value.trim();
        const password = document.getElementById('password').value;

        hideError('errorMessage');

        try {
            const response = await fetch(`${API_BASE_URL}/auth/login`, {
                method: 'POST',
                headers: getAuthHeaders(true),
                body: JSON.stringify({ email, password })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Login failed');
            }

            localStorage.setItem('token', data.token);
            localStorage.setItem('user', JSON.stringify(data.user));
            window.location.href = 'dashboard.html';

        } catch (error) {
            showError('errorMessage', error.message);
        }
    });
}

/* =========================
   LOGOUT
   ========================= */
if (document.getElementById('logoutBtn')) {
    document.getElementById('logoutBtn').addEventListener('click', () => {
        localStorage.clear();
        window.location.href = 'index.html';
    });
}

/* =========================
   PROTECTED PAGE GUARD
   ========================= */
if (
    window.location.pathname.includes('dashboard.html') ||
    window.location.pathname.includes('analyze.html') ||
    window.location.pathname.includes('result.html')
) {
    checkAuth(true);
}
/* =========================
   PASSWORD STRENGTH CHECK
   ========================= */

document.addEventListener('DOMContentLoaded', () => {
    const passwordInput = document.getElementById('password');
    if (!passwordInput) return;

    const rules = {
        length: document.getElementById('rule-length'),
        upper: document.getElementById('rule-upper'),
        lower: document.getElementById('rule-lower'),
        number: document.getElementById('rule-number'),
        special: document.getElementById('rule-special')
    };

    passwordInput.addEventListener('input', () => {
        const value = passwordInput.value;

        // At least 8 chars
        rules.length.classList.toggle('valid', value.length >= 8);

        // Uppercase
        rules.upper.classList.toggle('valid', /[A-Z]/.test(value));

        // Lowercase
        rules.lower.classList.toggle('valid', /[a-z]/.test(value));

        // Number
        rules.number.classList.toggle('valid', /\d/.test(value));

        // Special char
        rules.special.classList.toggle('valid', /[@$!%*?&]/.test(value));
    });
});
/* =========================
   DARK MODE TOGGLE (FIXED)
   ========================= */

document.addEventListener('DOMContentLoaded', () => {
    const themeToggle = document.getElementById('themeToggle');

    function applyTheme(theme) {
        document.body.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);

        if (themeToggle) {
            themeToggle.textContent = theme === 'dark' ? '☀️ Light' : '🌙 Dark';
        }
    }

    // Load saved theme OR system preference
    const savedTheme = localStorage.getItem('theme');
    const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

    applyTheme(savedTheme || (systemPrefersDark ? 'dark' : 'light'));

    // Toggle theme
    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            const currentTheme = document.body.getAttribute('data-theme');
            applyTheme(currentTheme === 'dark' ? 'light' : 'dark');
        });
    }
});


const profileBtn = document.getElementById("profileBtn");

if (profileBtn) {
    profileBtn.addEventListener("click", () => {
        const token = localStorage.getItem("token");

        if (!token) {
            window.location.href = "login.html";
        } else {
            window.location.href = "profile.html";
        }
    });
}

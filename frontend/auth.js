// auth.js - Backward compatibility wrapper for core.js
if (typeof API_BASE_URL === 'undefined') {
    const API_BASE_URL = (window.location.protocol === 'file:')
        ? 'http://127.0.0.1:5000/api'
        : `${window.location.origin}/api`;
}

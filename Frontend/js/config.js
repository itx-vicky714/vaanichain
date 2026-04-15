const CONFIG = {
  BASE_URL: (function() {
    if (window.__VC_BACKEND_URL__) return window.__VC_BACKEND_URL__;
    const host = window.location.hostname;
    if (host === 'localhost' || host === '127.0.0.1') return 'http://127.0.0.1:5000';
    return 'https://vaanichain-backend.onrender.com';
  })()
};
const API = CONFIG.BASE_URL;
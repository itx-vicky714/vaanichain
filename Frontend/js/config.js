const CONFIG = { 
    BASE_URL: window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' 
        ? 'http://127.0.0.1:5000' 
        : 'https://vaanichain-backend.onrender.com' 
};
const API = CONFIG.BASE_URL;
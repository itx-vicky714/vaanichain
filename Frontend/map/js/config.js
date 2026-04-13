const CONFIG = {
    BASE_URL: (function() {
        const host = window.location.hostname;
        if (host === 'localhost' || host === '127.0.0.1') {
            return 'http://localhost:5000';
        }
        return 'https://vaanichain-backend-1099191343978.asia-south1.run.app';
    })()
};
const API = CONFIG.BASE_URL;
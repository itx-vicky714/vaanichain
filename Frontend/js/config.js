if (window.location.hostname === 'localhost' || 
    window.location.hostname === '127.0.0.1') {
  var API = 'http://localhost:5000';
} else {
  var API = 'https://vaanichain-backend.onrender.com';
}
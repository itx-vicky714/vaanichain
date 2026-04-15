// NOTE: API is defined as a string (= CONFIG.BASE_URL) in config.js
// So `${API}/shipments` correctly becomes "https://your-backend.run.app/shipments"
// Do NOT redefine API as an object here — that was the bug causing [object Object] URLs

const ApiClient = {
    getShipments: async () => {
        const res = await fetch(`${API}/shipments`);
        if (!res.ok) throw new Error("Shipments API failed");
        return res.json();
    },
    getStatus: async () => {
        const res = await fetch(`${API}/status`);
        if (!res.ok) throw new Error("Status API failed");
        return res.json();
    },
    sendMessage: async (message) => {
        const res = await fetch(`${API}/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message })
        });
        if (!res.ok) throw new Error("Chat API failed");
        return res.json();
    }
};
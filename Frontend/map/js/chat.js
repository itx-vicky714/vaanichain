// Fixed chat.js
// Old version used getElementById("chat-input") but dashboard.html uses id="chat-inp"
// Added null guard so it doesn't crash on pages without a chat box

async function sendMessage() {
    // Support both possible IDs used across pages
    const input = document.getElementById("chat-inp") || document.getElementById("chat-input");
    if (!input) return;

    const message = input.value.trim();
    if (!message) return;

    const chatBox = document.getElementById("chat-box") || document.getElementById("chat-msgs");
    if (chatBox) {
        chatBox.innerHTML += `<div><b>You:</b> ${message}</div>`;
    }

    try {
        const res = await fetch(`${API}/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message })
        });
        const data = await res.json();
        const reply = data?.reply || data?.response || "No response from AI";
        if (chatBox) {
            chatBox.innerHTML += `<div><b>AI:</b> ${reply}</div>`;
        }
    } catch (err) {
        if (chatBox) {
            chatBox.innerHTML += `<div><b>AI:</b> Error connecting to server</div>`;
        }
        console.warn("Chat error:", err);
    }
    input.value = "";
}
// Fixed shipments.js
// Old version crashed with "Cannot set properties of null" because
// it ran loadShipments() on every page but id="shipments" only exists
// on pages that have that container. Now it checks first.

async function loadShipments() {
    const container = document.getElementById("shipments");
    if (!container) return; // Guard: only run on pages that have this element

    try {
        const res = await fetch(`${API}/shipments`);
        if (!res.ok) throw new Error("Failed");
        const data = await res.json();

        container.innerHTML = "";
        data.forEach(s => {
            const div = document.createElement("div");
            div.className = "shipment-card";
            div.innerHTML = `
                <h3>${s.id}</h3>
                <p>${s.origin} → ${s.destination}</p>
                <p>Status: <b style="color:${s.status === "at_risk" ? "red" : "green"}">
                    ${s.status}
                </b></p>
            `;
            container.appendChild(div);
        });
    } catch (err) {
        console.warn("loadShipments error:", err);
    }
}

// Only auto-run if the container exists
if (document.getElementById("shipments")) {
    loadShipments();
}
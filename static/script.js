async function loadData() {
    try {
        const resp = await fetch("/api/top5");
        const data = await resp.json();

        if (data.loading) {
            document.getElementById("amazon-list").innerHTML =
                '<p class="no-data">Demarrage en cours... Les donnees arrivent dans 1-2 minutes.</p>';
            document.getElementById("cadeaucity-list").innerHTML =
                '<p class="no-data">Demarrage en cours... Les donnees arrivent dans 1-2 minutes.</p>';
            document.getElementById("last-updated").textContent = data.last_updated;
            // Auto-retry after 30 seconds
            setTimeout(loadData, 30000);
            return;
        }

        renderProducts("amazon-list", data.amazon);
        renderProducts("cadeaucity-list", data.cadeaucity);

        document.getElementById("last-updated").textContent =
            "Derniere mise a jour : " + data.last_updated;
    } catch (err) {
        console.error("Erreur de chargement:", err);
        document.getElementById("amazon-list").innerHTML =
            '<p class="no-data">Erreur de chargement</p>';
        document.getElementById("cadeaucity-list").innerHTML =
            '<p class="no-data">Erreur de chargement</p>';
    }
}

function renderProducts(containerId, products) {
    const container = document.getElementById(containerId);

    if (!products || products.length === 0) {
        container.innerHTML =
            '<p class="no-data">Aucune donnee disponible pour le moment</p>';
        return;
    }

    container.innerHTML = products
        .map(
            (product, index) => `
        <div class="product-item">
            <div class="product-rank">${index + 1}</div>
            ${
                product.image_url
                    ? `<img class="product-image" src="${product.image_url}" alt="${product.name}" loading="lazy">`
                    : ""
            }
            <div class="product-info">
                <div class="product-name">
                    ${
                        product.url
                            ? `<a href="${product.url}" target="_blank" rel="noopener">${product.name}</a>`
                            : product.name
                    }
                </div>
                <div class="product-meta">
                    ${product.price ? `<span class="product-price">${product.price}</span>` : ""}
                    ${product.rating ? `<span class="product-rating">${renderStars(product.rating)} ${product.rating.toFixed(1)}</span>` : ""}
                    ${product.review_count ? `<span class="product-reviews">${product.review_count} avis</span>` : ""}
                    ${product.badge ? `<span class="badge">${product.badge}</span>` : ""}
                    ${product.kpi_score != null ? `<span class="kpi-score">KPI: ${product.kpi_score}%</span>` : ""}
                </div>
            </div>
        </div>
    `
        )
        .join("");
}

function renderStars(rating) {
    const full = Math.floor(rating);
    const half = rating % 1 >= 0.5 ? 1 : 0;
    const empty = 5 - full - half;
    return "\u2605".repeat(full) + (half ? "\u00BD" : "") + "\u2606".repeat(empty);
}

async function refreshData() {
    const btn = document.getElementById("refresh-btn");
    btn.disabled = true;
    btn.textContent = "Rafraichissement...";

    try {
        await fetch("/api/refresh", { method: "POST" });
        await loadData();
    } catch (err) {
        console.error("Erreur de rafraichissement:", err);
    } finally {
        btn.disabled = false;
        btn.textContent = "Rafraichir";
    }
}

// Load data on page load
loadData();

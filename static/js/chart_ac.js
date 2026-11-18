let barChartInstance = null;
let scatterChartInstance = null;

function initializeCharts() {
    if (barChartInstance) {
        barChartInstance.destroy();
        barChartInstance = null;
    }
    if (scatterChartInstance) {
        scatterChartInstance.destroy();
        scatterChartInstance = null;
    }
    if (typeof Chart === "undefined") return;

    const canvas = document.getElementById("chartAc");
    if (!canvas) return;

    const hargaNonAc = Number(canvas.dataset.nonAc) || 0;
    const hargaAc = Number(canvas.dataset.ac) || 0;
    const usesPredictions = canvas.dataset.mode === "prediksi";
    const hasPrediction = canvas.dataset.estimasi !== "";
    const labels = usesPredictions
        ? ["Prediksi Non-AC", "Prediksi Ber-AC"]
        : ["Rata-rata Non-AC", "Rata-rata Ber-AC"];
    const values = [hargaNonAc, hargaAc];
    const selectedAc = canvas.dataset.acSelected === "ya";
    const backgroundColors = hasPrediction
        ? [selectedAc ? "#C5D1C9" : "#116530", selectedAc ? "#116530" : "#15803D"]
        : ["#C5D1C9", "#15803D"];
    const hoverBackgroundColors = hasPrediction
        ? [selectedAc ? "#AEBDB3" : "#0D5126", selectedAc ? "#0D5126" : "#116530"]
        : ["#AEBDB3", "#116530"];

    barChartInstance = new Chart(canvas, {
        type: "bar",
        data: {
            labels: labels,
            datasets: [
                {
                    label: "Tarif Bulanan",
                    data: values,
                    backgroundColor: backgroundColors,
                    hoverBackgroundColor: hoverBackgroundColors,
                    borderRadius: 10,
                    barThickness: 48,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: "#12211A",
                    titleFont: { family: "'Plus Jakarta Sans', sans-serif", size: 12 },
                    bodyFont: { family: "'JetBrains Mono', monospace", size: 12 },
                    padding: 12,
                    cornerRadius: 10,
                    callbacks: {
                        label: function (ctx) {
                            return " Rp " + ctx.raw.toLocaleString("id-ID") + " / bulan";
                        },
                    },
                },
            },
            scales: {
                x: {
                    grid: { display: false },
                    border: { display: false },
                    ticks: {
                        color: "#12211A",
                        font: { family: "'Plus Jakarta Sans', sans-serif", weight: "700", size: 13 },
                    },
                },
                y: {
                    beginAtZero: true,
                    border: { display: false },
                    grid: { color: "#E4ECE7" },
                    ticks: {
                        color: "#5B6E64",
                        font: { family: "'JetBrains Mono', monospace", size: 11 },
                        callback: function (value) {
                            return "Rp " + (value / 1000).toLocaleString("id-ID") + "k";
                        },
                    },
                },
            },
        },
    });

    const scatterCanvas = document.getElementById("chartScatter");
    const scatterDataElement = document.getElementById("scatter-data");
    if (scatterCanvas && scatterDataElement) {
        const scatterData = JSON.parse(scatterDataElement.textContent);
        const nonAcPoints = scatterData
            .filter(function (point) { return point.ac !== "ya"; })
            .map(function (point) { return { x: point.jarak_km, y: point.harga_rp }; });
        const acPoints = scatterData
            .filter(function (point) { return point.ac === "ya"; })
            .map(function (point) { return { x: point.jarak_km, y: point.harga_rp }; });
        const datasets = [
            {
                label: "Non-AC",
                data: nonAcPoints,
                backgroundColor: "#C5D1C9",
                pointRadius: 5,
                pointHoverRadius: 7,
            },
            {
                label: "Ber-AC",
                data: acPoints,
                backgroundColor: "#15803D",
                pointRadius: 5,
                pointHoverRadius: 7,
            },
        ];
        if (scatterCanvas.dataset.predictionDistance && scatterCanvas.dataset.predictionPrice) {
            datasets.push({
                label: "Prediksi saat ini",
                data: [{
                    x: Number(scatterCanvas.dataset.predictionDistance),
                    y: Number(scatterCanvas.dataset.predictionPrice),
                }],
                backgroundColor: "#116530",
                pointStyle: "triangle",
                pointRadius: 9,
                pointHoverRadius: 11,
            });
        }

        scatterChartInstance = new Chart(scatterCanvas, {
            type: "scatter",
            data: { datasets: datasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: "bottom",
                        labels: {
                            usePointStyle: true,
                            boxWidth: 8,
                            font: { family: "'Plus Jakarta Sans', sans-serif", size: 11 },
                        },
                    },
                    tooltip: {
                        callbacks: {
                            label: function (ctx) {
                                const point = ctx.raw;
                                return ctx.dataset.label + ": " +
                                    point.x.toLocaleString("id-ID") + " km, Rp " +
                                    point.y.toLocaleString("id-ID") + " / bulan";
                            },
                        },
                    },
                },
                scales: {
                    x: {
                        type: "linear",
                        title: {
                            display: true,
                            text: "Jarak ke kampus (km)",
                            color: "#5B6E64",
                            font: { family: "'Plus Jakarta Sans', sans-serif", size: 11 },
                        },
                        grid: { color: "#E4ECE7" },
                        ticks: { color: "#5B6E64" },
                    },
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: "Harga sewa / bulan (Rp)",
                            color: "#5B6E64",
                            font: { family: "'Plus Jakarta Sans', sans-serif", size: 11 },
                        },
                        grid: { color: "#E4ECE7" },
                        ticks: {
                            color: "#5B6E64",
                            callback: function (value) {
                                return "Rp " + (value / 1000).toLocaleString("id-ID") + "k";
                            },
                        },
                    },
                },
            },
        });
    }

}

function bindChartExplanations() {
    bindExplanationForm(
        "chartAiForm",
        "chartAiExplanation",
        "Meminta AI menjelaskan perbandingan tarif..."
    );
    bindExplanationForm(
        "scatterAiForm",
        "scatterAiExplanation",
        "Meminta AI menganalisis scatter plot..."
    );
}

function replacePredictionSections(html) {
    const updatedDocument = new DOMParser().parseFromString(html, "text/html");
    const sectionIds = ["kartu-hasil", "grafik", "scatter", "riwayat"];
    const replacements = sectionIds.map(function (id) {
        return {
            current: document.getElementById(id),
            updated: updatedDocument.getElementById(id),
        };
    });

    if (replacements.some(function (item) { return !item.current || !item.updated; })) {
        throw new Error("Hasil perhitungan tidak lengkap. Silakan coba lagi.");
    }

    replacements.forEach(function (item) {
        item.current.replaceWith(item.updated);
    });
    initializeCharts();
    bindChartExplanations();
}

function bindPredictionForm() {
    const form = document.getElementById("form-prediksi");
    if (!form) return;

    const submitButton = form.querySelector('button[type="submit"]');
    const originalButtonText = submitButton ? submitButton.textContent : "";
    form.addEventListener("submit", async function (event) {
        event.preventDefault();
        if (submitButton) {
            submitButton.disabled = true;
            submitButton.textContent = "Menghitung...";
        }

        try {
            const response = await fetch(form.action || window.location.href, {
                method: "POST",
                body: new FormData(form),
                headers: { "X-Requested-With": "XMLHttpRequest" },
            });
            const html = await response.text();
            if (!response.ok) {
                throw new Error("Perhitungan gagal. Silakan coba lagi.");
            }
            replacePredictionSections(html);
        } catch (error) {
            window.alert(error.message || "Perhitungan gagal. Silakan coba lagi.");
        } finally {
            if (submitButton) {
                submitButton.disabled = false;
                submitButton.textContent = originalButtonText;
            }
        }
    });
}

async function refreshHistorySection() {
    const response = await fetch(window.location.pathname + window.location.search, {
        headers: { "X-Requested-With": "XMLHttpRequest" },
    });
    const html = await response.text();
    if (!response.ok) {
        throw new Error("Daftar riwayat tidak dapat dimuat ulang.");
    }

    const updatedDocument = new DOMParser().parseFromString(html, "text/html");
    const currentSection = document.getElementById("riwayat");
    const updatedSection = updatedDocument.getElementById("riwayat");
    if (!currentSection || !updatedSection) {
        throw new Error("Bagian riwayat tidak ditemukan.");
    }
    currentSection.replaceWith(updatedSection);
    return updatedSection;
}

function bindHistoryDeletion() {
    document.addEventListener("submit", async function (event) {
        if (event.defaultPrevented) return;
        const form = event.target.closest("form[data-ajax-delete]");
        if (!form) return;
        event.preventDefault();

        const submitButton = form.querySelector('button[type="submit"]');
        if (submitButton) submitButton.disabled = true;

        let result;
        try {
            const response = await fetch(form.action, {
                method: "POST",
                body: new FormData(form),
                headers: { "X-Requested-With": "XMLHttpRequest" },
            });
            result = await response.json();
            if (!response.ok) {
                throw new Error(result.error || "Riwayat gagal dihapus.");
            }
        } catch (error) {
            if (submitButton) submitButton.disabled = false;
            window.alert(error.message || "Riwayat gagal dihapus.");
            return;
        }

        try {
            const historySection = await refreshHistorySection();
            const feedback = historySection.querySelector("#riwayat-feedback");
            if (feedback) {
                feedback.textContent = result.message;
                feedback.classList.remove("hidden");
            }
        } catch (error) {
            window.alert("Riwayat berhasil dihapus, tetapi tampilan gagal diperbarui: " + error.message);
        }
    });
}

document.addEventListener("DOMContentLoaded", function () {
    bindChartExplanations();
    bindPredictionForm();
    bindHistoryDeletion();
    initializeCharts();
});

function bindExplanationForm(formId, explanationId, loadingText) {
    const form = document.getElementById(formId);
    const explanation = document.getElementById(explanationId);
    if (!form || !explanation) return;

    explanation.textContent = loadingText;
    fetch(form.action, {
        method: "POST",
        body: new FormData(form),
        headers: { "X-Requested-With": "XMLHttpRequest" },
    })
        .then(function (response) {
            return response.json().then(function (data) {
                if (!response.ok) {
                    throw new Error(data.error || "Penjelasan dari API gagal dimuat.");
                }
                return data;
            });
        })
        .then(function (data) {
            explanation.textContent = data.explanation;
        })
        .catch(function (error) {
            explanation.textContent = error.message;
        });
}
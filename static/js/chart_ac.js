document.addEventListener("DOMContentLoaded", function () {
    const canvas = document.getElementById("chartAc");
    if (!canvas) return;

    const hargaNonAc = Number(canvas.dataset.nonAc) || 0;
    const hargaAc = Number(canvas.dataset.ac) || 0;

    new Chart(canvas, {
        type: "bar",
        data: {
            labels: ["Kamar Non-AC", "Kamar Ber-AC"],
            datasets: [
                {
                    label: "Rata-rata Sewa Bulanan",
                    data: [hargaNonAc, hargaAc],
                    backgroundColor: ["#C5D1C9", "#15803D"],
                    hoverBackgroundColor: ["#AEBDB3", "#116530"],
                    borderRadius: 10,
                    barThickness: 64,
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
});
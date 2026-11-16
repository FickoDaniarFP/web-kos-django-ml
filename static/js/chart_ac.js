document.addEventListener("DOMContentLoaded", function () {
    const canvas = document.getElementById("grafikAc");
    if (!canvas) return;

    const hargaAcYa = Number(canvas.dataset.acYa || 0);
    const hargaAcTidak = Number(canvas.dataset.acTidak || 0);

    const formatRp = (nilai) => "Rp " + Number(nilai).toLocaleString("id-ID");

    const ctx = canvas.getContext("2d");
    new Chart(ctx, {
        type: "bar",
        data: {
            labels: ["Dengan AC (ya)", "Tanpa AC (tidak)"],
            datasets: [
                {
                    label: "Rata-rata Harga per Bulan",
                    data: [hargaAcYa, hargaAcTidak],
                    backgroundColor: ["#2563eb", "#94a3b8"],
                    borderRadius: 8,
                    barThickness: 60,
                },
            ],
        },
        options: {
            responsive: true,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: (context) => formatRp(context.raw),
                    },
                },
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: (value) => formatRp(value),
                    },
                },
            },
        },
    });
});
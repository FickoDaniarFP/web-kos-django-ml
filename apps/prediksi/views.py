from django.shortcuts import render
from apps.analytics.services import format_rupiah, get_statistik_kos
from apps.prediksi.services import hitung_prediksi_harga


def index(request):
    statistik = get_statistik_kos()

    hasil_prediksi = None
    selisih_angka = 0
    selisih_harga = None
    input_data = {
        "jarak": 1.0,
        "rating": 4.5,
        "ac": "ya",
    }

    if request.method == "POST":
        jarak = float(request.POST.get("jarak", 1.0))
        rating = float(request.POST.get("rating", 4.5))
        ac = request.POST.get("ac", "ya")

        input_data = {
            "jarak": jarak,
            "rating": rating,
            "ac": ac,
        }

        hasil_prediksi_angka = hitung_prediksi_harga(jarak, rating, ac)
        hasil_prediksi = format_rupiah(hasil_prediksi_angka)
        selisih_angka = hasil_prediksi_angka - statistik["rata_total_angka"]
        selisih_harga = format_rupiah(abs(selisih_angka))

    context = {
        **statistik,
        "hasil_prediksi": hasil_prediksi,
        "selisih_angka": selisih_angka,
        "selisih_harga": selisih_harga,
        "input_data": input_data,
    }
    return render(request, "prediksi/index.html", context)
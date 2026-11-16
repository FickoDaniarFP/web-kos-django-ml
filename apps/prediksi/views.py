import os

from django.conf import settings
from django.contrib import messages
from django.db import OperationalError
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST
from apps.analytics.services import format_rupiah, get_statistik_kos
from apps.prediksi.models import RiwayatPrediksi
from apps.prediksi.services import (
    analisis_kos_ai,
    get_openai_compatible_url,
    hitung_prediksi_harga,
)

AI_PROVIDERS = {
    "groq": ("Groq", "GROQ_API_KEY"),
    "gemini": ("Gemini", "GEMINI_API_KEY"),
    "openai_compatible": ("API kustom (OpenAI-compatible)", ""),
}


def index(request):
    context = get_statistik_kos()
    provider = request.session.get("ai_provider", "groq")
    if provider not in AI_PROVIDERS or (provider == "openai_compatible" and not settings.DEBUG):
        provider = "groq"
    api_key = request.session.get(f"ai_api_key_{provider}")
    if provider == "groq":
        api_key = api_key or request.session.get("groq_api_key")
    environment_key = AI_PROVIDERS[provider][1]

    if request.method == "POST":
        jarak_input = float(request.POST.get("jarak", 1.5))
        rating_input = float(request.POST.get("rating", 4.2))
        ac_input = request.POST.get("ac", "tidak")

        hasil_angka = hitung_prediksi_harga(jarak_input, rating_input, ac_input)
        hasil_rp = format_rupiah(hasil_angka)
        selisih = hasil_angka - context["rata_total_angka"]
        analisis_ai = analisis_kos_ai(
            jarak_input,
            rating_input,
            ac_input,
            hasil_rp,
            provider,
            api_key,
            request.session.get("ai_custom_base_url", ""),
            request.session.get("ai_custom_model", ""),
        )

        try:
            RiwayatPrediksi.objects.create(
                jarak_km=jarak_input,
                rating=rating_input,
                ac=ac_input,
                estimasi_harga=hasil_angka,
                analisis_ai=analisis_ai,
            )
        except OperationalError:
            pass

        context.update({
            "jarak_input": jarak_input,
            "rating_input": rating_input,
            "ac_input": ac_input,
            "hasil_prediksi": hasil_rp,
            "selisih_rp": format_rupiah(abs(selisih)),
            "lebih_mahal": selisih >= 0,
            "analisis_ai": analisis_ai,
        })

    try:
        total_riwayat = RiwayatPrediksi.objects.count()
        riwayat_list = list(RiwayatPrediksi.objects.order_by("-created_at")[:5])
        for item in riwayat_list:
            item.harga_rp = format_rupiah(item.estimasi_harga)
    except OperationalError:
        total_riwayat = 0
        riwayat_list = []

    context.update({
        "riwayat_list": riwayat_list,
        "total_riwayat": total_riwayat,
        "harga_ac_ya_rp": format_rupiah(context["harga_ac_ya"]),
        "harga_ac_tidak_rp": format_rupiah(context["harga_ac_tidak"]),
        "ai_provider": provider,
        "ai_provider_label": AI_PROVIDERS[provider][0],
        "ai_api_key_saved": bool(api_key),
        "ai_api_key_configured": bool(api_key or (environment_key and os.getenv(environment_key))),
        "ai_custom_base_url": request.session.get("ai_custom_base_url", ""),
        "ai_custom_model": request.session.get("ai_custom_model", ""),
        "ai_custom_provider_enabled": settings.DEBUG,
    })
    return render(request, "prediksi/index.html", context)


@require_POST
def atur_ai_api(request):
    provider = request.POST.get("provider", "groq")
    if provider not in AI_PROVIDERS:
        messages.error(request, "Mode API yang dipilih tidak dikenal.")
        return redirect("prediksi:index")

    if request.POST.get("action") == "clear":
        request.session.pop(f"ai_api_key_{provider}", None)
        if provider == "groq":
            request.session.pop("groq_api_key", None)
        if provider == "openai_compatible":
            request.session.pop("ai_custom_base_url", None)
            request.session.pop("ai_custom_model", None)
        if request.session.get("ai_provider", "groq") == provider:
            request.session["ai_provider"] = "groq"
        messages.success(request, f"Konfigurasi {AI_PROVIDERS[provider][0]} di sesi ini sudah dihapus.")
        return redirect("prediksi:index")

    request.session["ai_provider"] = provider
    request.session.set_expiry(0)
    api_key = request.POST.get("api_key", "").strip()
    if len(api_key) > 512:
        messages.error(request, "API key terlalu panjang.")
        return redirect("prediksi:index")

    custom_base_url = ""
    custom_model = ""
    if provider == "openai_compatible":
        if not settings.DEBUG:
            messages.error(request, "Mode API kustom hanya tersedia saat aplikasi berjalan lokal.")
            return redirect("prediksi:index")
        custom_base_url = request.POST.get("base_url", "").strip()
        custom_model = request.POST.get("model", "").strip()
        try:
            get_openai_compatible_url(custom_base_url)
        except ValueError:
            messages.error(request, "URL API kustom harus berupa alamat HTTPS publik yang valid.")
            return redirect("prediksi:index")
        if len(custom_base_url) > 300 or not custom_model or len(custom_model) > 128:
            messages.error(request, "Isi URL API dan nama model kustom dengan benar.")
            return redirect("prediksi:index")

    current_api_key = request.session.get(f"ai_api_key_{provider}")
    if provider == "groq":
        current_api_key = current_api_key or request.session.get("groq_api_key")
    env_name = AI_PROVIDERS[provider][1]
    has_environment_key = bool(env_name and os.getenv(env_name))
    if not api_key and not current_api_key and not has_environment_key:
        messages.error(request, "Masukkan API key untuk provider yang dipilih.")
        return redirect("prediksi:index")

    if api_key:
        request.session[f"ai_api_key_{provider}"] = api_key
    if provider == "openai_compatible":
        request.session["ai_custom_base_url"] = custom_base_url
        request.session["ai_custom_model"] = custom_model
    request.session["ai_provider"] = provider
    request.session.set_expiry(0)
    messages.success(request, f"Pengaturan {AI_PROVIDERS[provider][0]} tersimpan untuk sesi browser ini.")

    return redirect("prediksi:index")
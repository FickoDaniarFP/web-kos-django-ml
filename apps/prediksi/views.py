import math
import os
import logging

from django.conf import settings
from django.contrib import messages
from django.db import OperationalError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST
import requests
from apps.analytics.services import format_rupiah, get_statistik_kos
from apps.prediksi.models import RiwayatPrediksi
from apps.prediksi.services import (
    AI_PROVIDER_LABELS,
    analisis_kos_ai,
    analisis_perbandingan_tarif_ai,
    analisis_scatter_ai,
    get_openai_compatible_url,
    hitung_prediksi_harga,
)

logger = logging.getLogger(__name__)

AI_PROVIDERS = {
    "groq": ("Groq", "GROQ_API_KEY"),
    "gemini": ("Gemini", "GEMINI_API_KEY"),
    "openai_compatible": ("API kustom (OpenAI-compatible)", ""),
}


def _scatter_points(rows):
    return [
        {
            "jarak_km": float(row["jarak_km"]),
            "harga_rp": int(round(float(row["harga"])) * 1000),
            "ac": row["ac"],
        }
        for row in rows
    ]


def _parse_prediction_inputs(post_data):
    try:
        jarak = float(post_data.get("jarak", ""))
        rating = float(post_data.get("rating", ""))
    except (TypeError, ValueError) as exc:
        raise ValueError("Jarak dan rating harus berupa angka yang valid.") from exc

    if not (math.isfinite(jarak) and math.isfinite(rating)):
        raise ValueError("Jarak dan rating harus berupa angka terbatas yang valid.")
    if not (0.1 <= jarak <= 25.0):
        raise ValueError("Jarak ke kampus harus berada di antara 0.1 hingga 25.0 km.")
    if not (1.0 <= rating <= 5.0):
        raise ValueError("Rating penghuni harus berada di antara 1.0 hingga 5.0.")

    ac = post_data.get("ac", "tidak")
    if ac not in ("ya", "tidak"):
        raise ValueError("Pilihan fasilitas pendingin harus Ber-AC atau Non-AC.")

    return jarak, rating, ac


def index(request):
    context = get_statistik_kos()
    context["scatter_data"] = _scatter_points(context["data_kos"])
    provider = request.session.get("ai_provider", "groq")
    if provider not in AI_PROVIDERS or (provider == "openai_compatible" and not settings.DEBUG):
        provider = "groq"
    api_key = request.session.get(f"ai_api_key_{provider}")
    if provider == "groq":
        api_key = api_key or request.session.get("groq_api_key")
    environment_key = AI_PROVIDERS[provider][1]
    status_code = 200

    if request.method == "POST":
        try:
            jarak_input, rating_input, ac_input = _parse_prediction_inputs(request.POST)
        except ValueError as error:
            messages.error(request, str(error))
            status_code = 400
        else:
            harga_non_ac_grafik = hitung_prediksi_harga(jarak_input, rating_input, "tidak")
            harga_ac_grafik = hitung_prediksi_harga(jarak_input, rating_input, "ya")
            hasil_angka = harga_ac_grafik if ac_input == "ya" else harga_non_ac_grafik
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
                "harga_non_ac_grafik": harga_non_ac_grafik,
                "harga_non_ac_grafik_rp": format_rupiah(harga_non_ac_grafik),
                "harga_ac_grafik": harga_ac_grafik,
                "harga_ac_grafik_rp": format_rupiah(harga_ac_grafik),
                "hasil_prediksi_angka": hasil_angka,
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
    return render(request, "prediksi/index.html", context, status=status_code)


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


@require_POST
def analisis_grafik_ai(request):
    provider = request.session.get("ai_provider", "groq")
    if provider not in AI_PROVIDERS or (provider == "openai_compatible" and not settings.DEBUG):
        provider = "groq"

    api_key = request.session.get(f"ai_api_key_{provider}")
    if provider == "groq":
        api_key = api_key or request.session.get("groq_api_key")

    try:
        harga_non_ac = int(request.POST["harga_non_ac"])
        harga_ac = int(request.POST["harga_ac"])
    except (KeyError, TypeError, ValueError):
        return JsonResponse({"error": "Data grafik tidak valid. Hitung estimasi terlebih dahulu."}, status=400)
    if harga_non_ac < 0 or harga_ac < 0:
        return JsonResponse({"error": "Nilai tarif grafik tidak valid."}, status=400)

    try:
        explanation = analisis_perbandingan_tarif_ai(
            harga_non_ac,
            harga_ac,
            provider,
            api_key,
            request.session.get("ai_custom_base_url", ""),
            request.session.get("ai_custom_model", ""),
        )
    except ValueError as error:
        return JsonResponse({"error": str(error)}, status=400)
    except (requests.RequestException, KeyError, TypeError):
        logger.warning("Request penjelasan grafik ke %s gagal.", provider, exc_info=True)
        return JsonResponse(
            {"error": f"Gagal mendapatkan penjelasan dari {AI_PROVIDER_LABELS[provider]}."},
            status=502,
        )

    return JsonResponse({"explanation": explanation})


@require_POST
def analisis_scatter_ai_view(request):
    provider = request.session.get("ai_provider", "groq")
    if provider not in AI_PROVIDERS or (provider == "openai_compatible" and not settings.DEBUG):
        provider = "groq"

    api_key = request.session.get(f"ai_api_key_{provider}")
    if provider == "groq":
        api_key = api_key or request.session.get("groq_api_key")

    data_points = _scatter_points(get_statistik_kos()["data_kos"])
    try:
        explanation = analisis_scatter_ai(
            data_points,
            provider,
            api_key,
            request.session.get("ai_custom_base_url", ""),
            request.session.get("ai_custom_model", ""),
        )
    except ValueError as error:
        return JsonResponse({"error": str(error)}, status=400)
    except (requests.RequestException, KeyError, TypeError):
        logger.warning("Request penjelasan scatter plot ke %s gagal.", provider, exc_info=True)
        return JsonResponse(
            {"error": f"Gagal mendapatkan penjelasan dari {AI_PROVIDER_LABELS[provider]}."},
            status=502,
        )

    return JsonResponse({"explanation": explanation})


@require_POST
def hapus_riwayat(request, pk):
    riwayat = get_object_or_404(RiwayatPrediksi, pk=pk)
    riwayat.delete()
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"message": "Riwayat berhasil dihapus."})
    messages.success(request, "Riwayat berhasil dihapus.")
    return redirect(f"{reverse('prediksi:index')}#riwayat")


@require_POST
def hapus_semua_riwayat(request):
    deleted_count, _ = RiwayatPrediksi.objects.all().delete()
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"message": f"{deleted_count} riwayat berhasil dihapus."})
    messages.success(request, f"{deleted_count} riwayat berhasil dihapus.")
    return redirect(f"{reverse('prediksi:index')}#riwayat")
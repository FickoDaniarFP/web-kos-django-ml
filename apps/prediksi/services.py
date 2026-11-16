import ipaddress
import logging
import os
from urllib.parse import urlsplit

import joblib
import pandas as pd
import requests
from django.conf import settings

MODEL_PATH = os.path.join(settings.BASE_DIR, "dataset", "model_kos.joblib")
model = joblib.load(MODEL_PATH)
logger = logging.getLogger(__name__)


def _analisis_lokal(jarak, rating, ac, harga_rp):
    if ac == "ya":
        if jarak <= 1.5 and rating >= 4.5:
            return (
                f"Harga {harga_rp} masih wajar untuk kamar ber-AC dengan rating tinggi dan jarak dekat ke kampus. "
                "Ini menunjukkan value-for-money yang cukup baik untuk kebutuhan mahasiswa."
            )
        return (
            f"Harga {harga_rp} terbilang masuk akal untuk kamar ber-AC; estimasi ini masih layak bila kualitas "
            "fasilitas dan lokasi sesuai kebutuhanmu."
        )

    if jarak <= 1.5 and rating >= 4.5:
        return (
            f"Harga {harga_rp} untuk kamar non-AC masih wajar mengingat jarak strategis dan rating yang bagus. "
            "Cek fasilitas tambahan agar keputusan sewa tetap menguntungkan."
        )

    return (
        f"Harga {harga_rp} berada dalam kisaran umum untuk kamar non-AC. Pastikan lokasi dan fasilitas dasar "
        "masih sesuai kebutuhanmu agar tidak terlalu mahal untuk tipe kamar ini."
    )


def _fallback_analysis(reason, jarak, rating, ac, harga_rp):
    return f"{reason} Rekomendasi lokal: {_analisis_lokal(jarak, rating, ac, harga_rp)}"


def get_openai_compatible_url(base_url):
    parsed = urlsplit(base_url.strip())
    hostname = parsed.hostname
    if (
        parsed.scheme != "https"
        or not hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or hostname.lower() == "localhost"
        or hostname.lower().endswith((".localhost", ".local"))
    ):
        raise ValueError("Gunakan URL HTTPS publik yang valid tanpa kredensial.")

    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        address = None
    if address is not None and not address.is_global:
        raise ValueError("Alamat IP privat atau lokal tidak diizinkan.")

    endpoint = base_url.strip().rstrip("/")
    if not endpoint.endswith("/chat/completions"):
        endpoint += "/chat/completions"
    return endpoint


def _extract_openai_content(payload):
    if not isinstance(payload, dict):
        return ""
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        return ""
    message = choices[0].get("message")
    if not isinstance(message, dict):
        return ""
    content = message.get("content")
    return content.strip() if isinstance(content, str) else ""


def _request_openai_compatible(url, api_key, model, prompt):
    response = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": 180,
        },
        timeout=20,
    )
    response.raise_for_status()
    return _extract_openai_content(response.json())


def _request_gemini(api_key, model, prompt):
    response = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        headers={
            "x-goog-api-key": api_key,
            "Content-Type": "application/json",
        },
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.7, "maxOutputTokens": 180},
        },
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        return ""
    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or not candidates or not isinstance(candidates[0], dict):
        return ""
    content = candidates[0].get("content")
    if not isinstance(content, dict):
        return ""
    parts = content.get("parts")
    if not isinstance(parts, list):
        return ""
    return " ".join(
        part["text"].strip()
        for part in parts
        if isinstance(part, dict) and isinstance(part.get("text"), str) and part["text"].strip()
    )


def analisis_kos_ai(
    jarak,
    rating,
    ac,
    harga_rp,
    provider="groq",
    api_key=None,
    base_url="",
    model="",
):
    provider_defaults = {
        "groq": ("GROQ_API_KEY", "llama-3.1-8b-instant"),
        "gemini": ("GEMINI_API_KEY", "gemini-2.5-flash"),
        "openai_compatible": ("", ""),
    }
    provider_labels = {
        "groq": "Groq",
        "gemini": "Gemini",
        "openai_compatible": "API kustom",
    }
    if provider not in provider_defaults:
        return _fallback_analysis("Provider AI tidak dikenal.", jarak, rating, ac, harga_rp)

    environment_key, default_model = provider_defaults[provider]
    api_key = api_key or (os.getenv(environment_key) if environment_key else None)
    prompt = (
        f"Kamu adalah asisten penilai sewa kos. Berikan rekomendasi singkat dalam Bahasa Indonesia. "
        f"Data: jarak={jarak} km, rating={rating}, fasilitas={'AC' if ac == 'ya' else 'Non-AC'}, "
        f"estimasi_harga={harga_rp}. Jelaskan apakah harga tersebut wajar dan berikan saran praktis."
    )

    if not api_key:
        return _fallback_analysis(
            f"API key {provider_labels[provider]} belum diatur.",
            jarak,
            rating,
            ac,
            harga_rp,
        )

    try:
        if provider == "gemini":
            content = _request_gemini(api_key, model or default_model, prompt)
        else:
            if provider == "groq":
                url = "https://api.groq.com/openai/v1/chat/completions"
                model = model or default_model
            else:
                if not settings.DEBUG:
                    return _fallback_analysis(
                        "API kustom hanya dapat digunakan saat aplikasi berjalan lokal.",
                        jarak,
                        rating,
                        ac,
                        harga_rp,
                    )
                url = get_openai_compatible_url(base_url)
                if not model.strip():
                    return _fallback_analysis(
                        "Nama model API kustom belum diatur.",
                        jarak,
                        rating,
                        ac,
                        harga_rp,
                    )
            content = _request_openai_compatible(url, api_key, model, prompt)
        if content:
            return content
        return _fallback_analysis(
            f"API {provider_labels[provider]} tidak mengembalikan rekomendasi.",
            jarak,
            rating,
            ac,
            harga_rp,
        )
    except (requests.RequestException, ValueError, KeyError, TypeError):
        logger.warning("Request ke provider AI %s gagal.", provider, exc_info=True)
        return _fallback_analysis(
            f"API {provider_labels[provider]} gagal dihubungi.",
            jarak,
            rating,
            ac,
            harga_rp,
        )



def hitung_prediksi_harga(jarak, rating, ac):
    ac_num = 1 if ac == "ya" else 0
    fitur = pd.DataFrame(
        [[jarak, rating, ac_num]], columns=["jarak_km", "rating", "ac_num"]
    )
    prediksi = model.predict(fitur)[0]
    return round(prediksi) * 1000
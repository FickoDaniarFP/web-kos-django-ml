import ipaddress
import json
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

DEFAULT_GROQ_MODELS = (
    "openai/gpt-oss-20b",
    "openai/gpt-oss-120b",
)

AI_PROVIDER_DEFAULTS = {
    "groq": ("GROQ_API_KEY", DEFAULT_GROQ_MODELS[0]),
    "gemini": ("GEMINI_API_KEY", "gemini-2.5-flash"),
    "openai_compatible": ("", ""),
}
AI_PROVIDER_LABELS = {
    "groq": "Groq",
    "gemini": "Gemini",
    "openai_compatible": "API kustom",
}


def _resolve_api_key(provider, api_key):
    if api_key:
        return api_key
    environment_key, _ = AI_PROVIDER_DEFAULTS[provider]
    if provider == "groq":
        return settings.GROQ_API_KEY
    return os.getenv(environment_key) if environment_key else None


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


def _request_openai_compatible(url, api_key, model, prompt, reasoning_effort=None):
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
    }
    if reasoning_effort:
        payload.update({
            "max_completion_tokens": 512,
            "reasoning_effort": reasoning_effort,
            "reasoning_format": "hidden",
        })
    else:
        payload["max_tokens"] = 180

    response = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
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


def _request_ai_provider(provider, api_key, model, base_url, prompt):
    if provider == "gemini":
        return _request_gemini(
            api_key,
            model or AI_PROVIDER_DEFAULTS["gemini"][1],
            prompt,
        )

    if provider == "groq":
        groq_models = settings.GROQ_MODELS or DEFAULT_GROQ_MODELS
        for index, groq_model in enumerate(groq_models):
            try:
                return _request_openai_compatible(
                    "https://api.groq.com/openai/v1/chat/completions",
                    api_key,
                    groq_model,
                    prompt,
                    reasoning_effort=(
                        "low" if groq_model.startswith("openai/gpt-oss-") else None
                    ),
                )
            except requests.HTTPError as error:
                response = error.response
                if (
                    response is None
                    or response.status_code != 429
                    or index == len(groq_models) - 1
                ):
                    raise
                logger.warning(
                    "Groq model %s was rate-limited; trying model %s.",
                    groq_model,
                    groq_models[index + 1],
                )

    if provider == "openai_compatible":
        if not model.strip():
            raise ValueError("Nama model API kustom belum diatur.")
        return _request_openai_compatible(
            get_openai_compatible_url(base_url),
            api_key,
            model,
            prompt,
        )

    raise ValueError("Provider AI tidak dikenal.")


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
    if provider not in AI_PROVIDER_DEFAULTS:
        return "Provider AI tidak dikenal."

    api_key = _resolve_api_key(provider, api_key)
    prompt = (
        "Kamu adalah asisten penilai sewa kos. Jawab dalam Bahasa Indonesia, maksimal 45 kata. "
        "Gunakan format wajib berikut, tepat satu bagian per baris:\n"
        "Penilaian: [apakah harga wajar]\n"
        "Pertimbangan: [alasan singkat]\n"
        "Saran: [saran praktis]\n"
        "Jangan gunakan Markdown, tanda bintang, daftar bernomor, atau pembuka. "
        f"Data: jarak={jarak} km, rating={rating}, fasilitas={'AC' if ac == 'ya' else 'Non-AC'}, "
        f"estimasi_harga={harga_rp}. Nilai kewajaran harga dan beri saran praktis berdasarkan data ini saja."
    )

    if not api_key:
        return f"API key {AI_PROVIDER_LABELS[provider]} belum diatur."
    if provider == "openai_compatible" and not model.strip():
        return "Nama model API kustom belum diatur."

    try:
        content = _request_ai_provider(provider, api_key, model, base_url, prompt)
        if content:
            return content
        return f"API {AI_PROVIDER_LABELS[provider]} tidak mengembalikan rekomendasi."
    except (requests.RequestException, ValueError, KeyError, TypeError):
        logger.warning("Request ke provider AI %s gagal.", provider, exc_info=True)
        return f"API {AI_PROVIDER_LABELS[provider]} gagal dihubungi."


def analisis_perbandingan_tarif_ai(
    harga_non_ac,
    harga_ac,
    provider="groq",
    api_key=None,
    base_url="",
    model="",
):
    if provider not in AI_PROVIDER_DEFAULTS:
        raise ValueError("Provider AI tidak dikenal.")

    api_key = _resolve_api_key(provider, api_key)
    if not api_key:
        raise ValueError(f"API key {AI_PROVIDER_LABELS[provider]} belum diatur.")

    difference = harga_ac - harga_non_ac
    percentage = difference / harga_non_ac * 100 if harga_non_ac else 0
    prompt = (
        "Jelaskan grafik perbandingan tarif sewa kos bulanan di Madiun dalam Bahasa Indonesia. "
        "Jelaskan kamar mana yang lebih mahal dan selisihnya, lalu beri satu interpretasi singkat. "
        "Gunakan maksimal 60 kata, 2-3 kalimat, teks biasa tanpa Markdown. "
        f"Data grafik saat ini: Non-AC Rp{harga_non_ac}; Ber-AC Rp{harga_ac}; "
        f"selisih Ber-AC terhadap Non-AC Rp{difference} ({percentage:.1f}%). "
        "Jangan membuat klaim di luar data tersebut."
    )
    content = _request_ai_provider(provider, api_key, model, base_url, prompt)
    if not content:
        raise ValueError(
            f"API {AI_PROVIDER_LABELS[provider]} tidak mengembalikan penjelasan."
        )
    return content


def analisis_scatter_ai(
    data_points,
    provider="groq",
    api_key=None,
    base_url="",
    model="",
):
    if provider not in AI_PROVIDER_DEFAULTS:
        raise ValueError("Provider AI tidak dikenal.")
    if not data_points:
        raise ValueError("Data scatter plot tidak tersedia.")

    api_key = _resolve_api_key(provider, api_key)
    if not api_key:
        raise ValueError(f"API key {AI_PROVIDER_LABELS[provider]} belum diatur.")

    prompt = (
        "Jelaskan scatter plot harga sewa kos di Madiun dalam Bahasa Indonesia. "
        "Sumbu X adalah jarak ke kampus dalam km, sumbu Y adalah harga sewa bulanan dalam rupiah, "
        "dan tiap titik menunjukkan fasilitas AC atau Non-AC. Sebutkan pola umum hubungan jarak "
        "dan harga serta perbedaan kelompok AC secara hati-hati; jangan menganggap korelasi sebagai sebab-akibat. "
        "Gunakan maksimal 80 kata, 2-4 kalimat, teks biasa tanpa Markdown. "
        f"Data titik: {json.dumps(data_points, ensure_ascii=False)}"
    )
    content = _request_ai_provider(provider, api_key, model, base_url, prompt)
    if not content:
        raise ValueError(
            f"API {AI_PROVIDER_LABELS[provider]} tidak mengembalikan penjelasan scatter plot."
        )
    return content



def hitung_prediksi_harga(jarak, rating, ac):
    ac_num = 1 if ac == "ya" else 0
    fitur = pd.DataFrame(
        [[jarak, rating, ac_num]], columns=["jarak_km", "rating", "ac_num"]
    )
    prediksi = model.predict(fitur)[0]
    return round(prediksi) * 1000
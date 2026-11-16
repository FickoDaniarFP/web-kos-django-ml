# rediksi Harga Kos Sekitar Kampus Madiun

Aplikasi web berbasis **Django** dan **Machine Learning (Linear Regression)** untuk memprediksi estimasi biaya sewa kos bulanan di sekitar kampus Madiun berdasarkan jarak ke kampus, rating, dan fasilitas AC.

## Identitas Mahasiswa (Pengerjaan Individu)
- **Nama:** Ficko Daniar Fachryza Putra
- **NIM:** 253307043
- **Program Studi:** D3 Teknologi Informasi - Politeknik Negeri Madiun
- **Keterangan:** Dikerjakan secara mandiri (individu)

## Sumber & Lisensi Dataset
- **Nama File:** `dataset/kos_madiun.csv`
- **Sumber:** Data sampel observasi tarif sewa kos di sekitar area kampus Kota Madiun (30 data sampel dengan fitur `jarak_km`, `rating`, `ac`, dan target `harga`).
- **Lisensi:** Penggunaan terbuka untuk keperluan akademik dan praktikum mata kuliah Sistem Cerdas (2026).

## Struktur Direktori
- `config/` : Pengaturan utama dan konfigurasi URL root Django
- `apps/prediksi/` : Modul layanan prediksi ML (`services.py`), `views.py`, dan `urls.py`
- `apps/analytics/` : Modul pengolahan statistik deskriptif dataset (`services.py`)
- `templates/` : Kerangka antarmuka HTML modular (`base.html` dan `prediksi/index.html`)
- `static/` : Aset CSS kustom (`style.css`) dan skrip grafik Chart.js (`chart_ac.js`)
- `dataset/` : File dataset `kos_madiun.csv` dan model terlatih `model_kos.joblib`

## Mengatur API AI
Pilih **API AI** di navbar untuk memilih Groq, Google Gemini, atau API kustom yang kompatibel dengan format OpenAI. Masukkan key provider lalu simpan; key disimpan pada sesi browser sampai browser ditutup dan dapat dihapus dari menu yang sama. API kustom memerlukan URL dasar HTTPS dan nama model, serta hanya diizinkan saat aplikasi lokal berjalan dengan `DEBUG=True`.

Sebagai alternatif, Groq dan Gemini dapat memakai environment variable `GROQ_API_KEY` dan `GEMINI_API_KEY`. Key sesi provider yang dipilih akan digunakan lebih dahulu daripada environment variable.

## Cara Menjalankan Aplikasi
1. Buka terminal dan arahkan ke direktori proyek `web_kos`.
2. Pasang seluruh pustaka yang dibutuhkan:
   ```bash
   pip install -r requirements.txt
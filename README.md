# Prediksi Harga Kos Sekitar Kampus Madiun

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
- `apps/prediksi/` : Fitur prediksi (`views.py`, `services.py`, `urls.py`, dan `models.py`) beserta template dan aset UI milik app
- `apps/analytics/` : Pengolahan statistik dataset, terpisah dari fitur prediksi
- `dataset/` : File dataset `kos_madiun.csv` dan model terlatih `model_kos.joblib`

## Mengatur API AI
Groq adalah provider default. Untuk pengembangan lokal, salin `.env.example` menjadi `.env`, lalu isi `GROQ_API_KEY`. Key Groq hanya dibaca server dan tidak disimpan di sesi browser.

`GROQ_MODELS` adalah daftar model Groq dipisahkan koma. Jika sebuah model mengembalikan HTTP 429 (rate limit), aplikasi mencoba model berikutnya. Default menggunakan `openai/gpt-oss-20b` lalu `openai/gpt-oss-120b`; daftar ini dapat diganti melalui environment variable. Lihat [katalog model Groq](https://console.groq.com/docs/models) untuk model yang tersedia pada akunmu.

Saat deploy ke Vercel, tambahkan `GROQ_API_KEY` dan, bila perlu, `GROQ_MODELS` pada **Project Settings → Environment Variables**. Jangan unggah `.env`; Vercel menyediakan nilai tersebut sebagai environment variable saat aplikasi berjalan. Status provider ditampilkan di navbar; pengaturan key tidak tersedia di UI.

## Cara Menjalankan Aplikasi
1. Buka terminal dan arahkan ke direktori proyek `web_kos`.
2. Pasang seluruh pustaka yang dibutuhkan:
   ```bash
   pip install -r requirements.txt
   ```
3. Siapkan environment lokal:
   ```powershell
   Copy-Item .env.example .env
   ```
   Isi `GROQ_API_KEY` di `.env`, lalu jalankan migrasi database SQLite:
   ```bash
   python manage.py migrate
   ```
4. Aktifkan mode pengembangan lalu jalankan server (PowerShell):
   ```powershell
   $env:DEBUG = "True"
   python manage.py runserver
   ```
   `runserver` hanya melayani aset app secara langsung ketika `DEBUG=True`.
5. Untuk mode production, biarkan `DEBUG=False` dan kumpulkan aset sebelum menjalankan server:
   ```bash
   python manage.py collectstatic --no-input
   ```
   WhiteNoise menyajikan aset hasil `collectstatic`.
6. Buka browser dan akses `http://127.0.0.1:8000/`.

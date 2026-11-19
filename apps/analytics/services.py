import os
import pandas as pd
from django.conf import settings
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

CSV_PATH = os.path.join(settings.BASE_DIR, "dataset", "kos_madiun.csv")
df = pd.read_csv(CSV_PATH)


def format_rupiah(angka):
    return f"{int(angka):,}".replace(",", ".")


def get_statistik_kos():
    rata_total_angka = round(df["harga"].mean()) * 1000
    harga_min_angka = round(df["harga"].min()) * 1000
    harga_max_angka = round(df["harga"].max()) * 1000
    total_data = len(df)

    df_model = df.copy()
    df_model["ac_num"] = df_model["ac"].map({"tidak": 0, "ya": 1})
    fitur = df_model[["jarak_km", "rating", "ac_num"]]
    target = df_model["harga"] * 1000
    model_evaluasi = LinearRegression().fit(fitur, target)
    prediksi_evaluasi = model_evaluasi.predict(fitur)
    mae = mean_absolute_error(target, prediksi_evaluasi)
    rmse = mean_squared_error(target, prediksi_evaluasi) ** 0.5
    r2 = r2_score(target, prediksi_evaluasi)

    rata_ac = df.groupby("ac")["harga"].mean()
    harga_ac_ya = round(rata_ac.get("ya", 0)) * 1000
    harga_ac_tidak = round(rata_ac.get("tidak", 0)) * 1000

    data_kos = []
    for row in df.to_dict(orient="records"):
        row["harga_rp"] = format_rupiah(round(row["harga"]) * 1000)
        data_kos.append(row)

    return {
        "total_data": total_data,
        "rata_total_angka": rata_total_angka,
        "rata_total": format_rupiah(rata_total_angka),
        "harga_min": format_rupiah(harga_min_angka),
        "harga_max": format_rupiah(harga_max_angka),
        "harga_ac_ya": harga_ac_ya,
        "harga_ac_tidak": harga_ac_tidak,
        "model_mae": format_rupiah(round(mae)),
        "model_rmse": format_rupiah(round(rmse)),
        "model_r2": f"{r2:.3f}",
        "model_r2_persen": f"{r2 * 100:.1f}",
        "data_kos": data_kos,
    }
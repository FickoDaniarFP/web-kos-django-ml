import os
import pandas as pd
from django.conf import settings

CSV_PATH = os.path.join(settings.BASE_DIR, "dataset", "kos_madiun.csv")
df = pd.read_csv(CSV_PATH)


def format_rupiah(angka):
    return f"{int(angka):,}".replace(",", ".")


def get_statistik_kos():
    rata_total_angka = round(df["harga"].mean()) * 1000
    harga_min_angka = round(df["harga"].min()) * 1000
    harga_max_angka = round(df["harga"].max()) * 1000
    total_data = len(df)

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
        "data_kos": data_kos,
    }
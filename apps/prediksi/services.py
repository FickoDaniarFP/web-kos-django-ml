import os
import joblib
import pandas as pd
from django.conf import settings

MODEL_PATH = os.path.join(settings.BASE_DIR, "dataset", "model_kos.joblib")
model = joblib.load(MODEL_PATH)


def hitung_prediksi_harga(jarak, rating, ac):
    ac_num = 1 if ac == "ya" else 0
    fitur = pd.DataFrame(
        [[jarak, rating, ac_num]], columns=["jarak_km", "rating", "ac_num"]
    )
    prediksi = model.predict(fitur)[0]
    return round(prediksi) * 1000
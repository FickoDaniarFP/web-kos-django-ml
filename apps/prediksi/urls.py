from django.urls import path
from . import views

app_name = "prediksi"

urlpatterns = [
    path("", views.index, name="index"),
    path("atur-api/", views.atur_ai_api, name="atur_ai_api"),
    path("analisis-grafik-ai/", views.analisis_grafik_ai, name="analisis_grafik_ai"),
    path("analisis-scatter-ai/", views.analisis_scatter_ai_view, name="analisis_scatter_ai"),
]
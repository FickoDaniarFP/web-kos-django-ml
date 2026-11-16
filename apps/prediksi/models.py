from django.db import models


class RiwayatPrediksi(models.Model):
    jarak_km = models.FloatField()
    rating = models.FloatField()
    ac = models.CharField(max_length=10)
    estimasi_harga = models.FloatField()
    analisis_ai = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.jarak_km} km / {self.rating} / {self.ac}"

from unittest.mock import Mock, patch

from django.test import TestCase
from django.urls import reverse
from apps.prediksi.models import RiwayatPrediksi
from apps.prediksi.services import analisis_kos_ai, analisis_scatter_ai


class AiApiSessionTests(TestCase):
    def test_saves_gemini_key_and_selects_provider(self):
        response = self.client.post(
            reverse("prediksi:atur_ai_api"),
            {"provider": "gemini", "api_key": "gemini-test-key"},
        )

        self.assertRedirects(response, reverse("prediksi:index"))
        self.assertEqual(self.client.session.get("ai_api_key_gemini"), "gemini-test-key")
        self.assertEqual(self.client.session.get("ai_provider"), "gemini")

    def test_saves_custom_openai_compatible_settings(self):
        response = self.client.post(
            reverse("prediksi:atur_ai_api"),
            {
                "provider": "openai_compatible",
                "api_key": "custom-test-key",
                "base_url": "https://api.example.com/v1",
                "model": "example-model",
            },
        )

        self.assertRedirects(response, reverse("prediksi:index"))
        self.assertEqual(self.client.session.get("ai_api_key_openai_compatible"), "custom-test-key")
        self.assertEqual(self.client.session.get("ai_custom_base_url"), "https://api.example.com/v1")
        self.assertEqual(self.client.session.get("ai_custom_model"), "example-model")

    def test_rejects_non_https_custom_api_url(self):
        response = self.client.post(
            reverse("prediksi:atur_ai_api"),
            {
                "provider": "openai_compatible",
                "api_key": "custom-test-key",
                "base_url": "http://localhost:8000/v1",
                "model": "example-model",
            },
        )

        self.assertRedirects(response, reverse("prediksi:index"))
        self.assertNotIn("ai_api_key_openai_compatible", self.client.session)

    def test_clears_current_provider_configuration(self):
        session = self.client.session
        session["ai_api_key_gemini"] = "gemini-test-key"
        session["ai_provider"] = "gemini"
        session.save()

        response = self.client.post(
            reverse("prediksi:atur_ai_api"),
            {"action": "clear", "provider": "gemini"},
        )

        self.assertRedirects(response, reverse("prediksi:index"))
        self.assertNotIn("ai_api_key_gemini", self.client.session)
        self.assertEqual(self.client.session.get("ai_provider"), "groq")

    @patch("apps.prediksi.views.os.getenv", return_value=None)
    def test_rejects_missing_api_key(self, _getenv):
        response = self.client.post(
            reverse("prediksi:atur_ai_api"),
            {"provider": "gemini", "api_key": "  "},
        )

        self.assertRedirects(response, reverse("prediksi:index"))
        self.assertNotIn("ai_api_key_gemini", self.client.session)


class AiProviderRequestTests(TestCase):
    @patch("apps.prediksi.services.requests.post")
    def test_sends_scatter_data_to_ai_provider(self, post):
        response = Mock()
        response.json.return_value = {
            "choices": [{"message": {"content": "Harga cenderung turun saat jarak bertambah."}}]
        }
        post.return_value = response
        data_points = [{"jarak_km": 1.5, "harga_rp": 850000, "ac": "ya"}]

        result = analisis_scatter_ai(data_points, "groq", "test-key")

        self.assertEqual(result, "Harga cenderung turun saat jarak bertambah.")
        prompt = post.call_args.kwargs["json"]["messages"][0]["content"]
        self.assertIn('"jarak_km": 1.5', prompt)
        self.assertIn('"harga_rp": 850000', prompt)

    @patch("apps.prediksi.services.requests.post")
    def test_sends_request_to_groq_with_active_replacement_model(self, post):
        response = Mock()
        response.json.return_value = {
            "choices": [{"message": {"content": "Rekomendasi Groq"}}]
        }
        post.return_value = response

        result = analisis_kos_ai(1.0, 4.5, "ya", "900.000", "groq", "test-key")

        self.assertEqual(result, "Rekomendasi Groq")
        self.assertEqual(
            post.call_args.args[0],
            "https://api.groq.com/openai/v1/chat/completions",
        )
        request_payload = post.call_args.kwargs["json"]
        self.assertEqual(request_payload["model"], "openai/gpt-oss-20b")
        self.assertEqual(request_payload["max_completion_tokens"], 512)
        self.assertEqual(request_payload["reasoning_effort"], "low")
        self.assertEqual(request_payload["reasoning_format"], "hidden")
        prompt = request_payload["messages"][0]["content"]
        self.assertIn("maksimal 45 kata", prompt)
        self.assertIn(
            "Penilaian: [apakah harga wajar]\n"
            "Pertimbangan: [alasan singkat]\n"
            "Saran: [saran praktis]",
            prompt,
        )
        self.assertIn("Jangan gunakan Markdown", prompt)

    @patch("apps.prediksi.services.requests.post")
    def test_sends_request_to_gemini(self, post):
        response = Mock()
        response.json.return_value = {
            "candidates": [
                {"content": {"parts": [{"text": "Rekomendasi Gemini"}]}}
            ]
        }
        post.return_value = response

        result = analisis_kos_ai(1.0, 4.5, "ya", "900.000", "gemini", "test-key")

        self.assertEqual(result, "Rekomendasi Gemini")
        self.assertIn("generativelanguage.googleapis.com", post.call_args.args[0])
        self.assertEqual(post.call_args.kwargs["headers"]["x-goog-api-key"], "test-key")

    @patch("apps.prediksi.services.requests.post")
    def test_sends_request_to_custom_openai_compatible_api(self, post):
        response = Mock()
        response.json.return_value = {
            "choices": [{"message": {"content": "Rekomendasi kustom"}}]
        }
        post.return_value = response

        result = analisis_kos_ai(
            1.0,
            4.5,
            "ya",
            "900.000",
            "openai_compatible",
            "test-key",
            "https://api.example.com/v1",
            "example-model",
        )

        self.assertEqual(result, "Rekomendasi kustom")
        self.assertEqual(
            post.call_args.args[0],
            "https://api.example.com/v1/chat/completions",
        )
        self.assertEqual(post.call_args.kwargs["json"]["model"], "example-model")


class ChartAiAnalysisTests(TestCase):
    def test_index_renders_resized_chart_and_ai_explanation_panel(self):
        response = self.client.get(reverse("prediksi:index"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Jelaskan dengan AI")
        self.assertContains(response, 'id="chartScatter"')
        self.assertNotContains(response, "Jelaskan Scatter dengan AI")
        self.assertContains(response, "lg:grid-cols-[minmax(0,1.6fr)_minmax(16rem,1fr)]")

    @patch(
        "apps.prediksi.views.hitung_prediksi_harga",
        side_effect=[800000, 875000],
    )
    @patch("apps.prediksi.views.analisis_kos_ai", return_value="Analisis lokal")
    def test_new_prediction_updates_both_ac_chart_values(self, _analysis, _predict):
        response = self.client.post(
            reverse("prediksi:index"),
            {"jarak": "2.0", "rating": "4.5", "ac": "ya"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="kartu-hasil"')
        self.assertContains(response, 'id="riwayat"')
        self.assertContains(response, 'data-non-ac="800000"')
        self.assertContains(response, 'data-ac="875000"')
        self.assertContains(response, 'data-estimasi="875000"')
        self.assertContains(response, 'data-ac-selected="ya"')
        self.assertContains(response, "Prediksi Non-AC")
        self.assertContains(response, "Prediksi Ber-AC")
        self.assertContains(response, "Rp 800.000")
        self.assertContains(response, "Rp 875.000")

    @patch("apps.prediksi.views.analisis_perbandingan_tarif_ai")
    def test_returns_ai_explanation_for_dataset_chart(self, analyze):
        analyze.return_value = "Tarif ber-AC lebih tinggi berdasarkan rata-rata dataset."
        session = self.client.session
        session["ai_provider"] = "groq"
        session["ai_api_key_groq"] = "test-key"
        session.save()

        response = self.client.post(
            reverse("prediksi:analisis_grafik_ai"),
            {"harga_non_ac": "800000", "harga_ac": "875000"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"explanation": "Tarif ber-AC lebih tinggi berdasarkan rata-rata dataset."},
        )
        args = analyze.call_args.args
        self.assertEqual(args[:2], (800000, 875000))
        self.assertEqual(args[2], "groq")
        self.assertEqual(args[3], "test-key")

    @patch("apps.prediksi.views.analisis_scatter_ai")
    def test_returns_ai_explanation_for_scatter_dataset(self, analyze):
        analyze.return_value = "Harga cenderung berubah terhadap jarak."
        session = self.client.session
        session["ai_provider"] = "groq"
        session["ai_api_key_groq"] = "test-key"
        session.save()

        response = self.client.post(reverse("prediksi:analisis_scatter_ai"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"explanation": "Harga cenderung berubah terhadap jarak."})
        data_points = analyze.call_args.args[0]
        self.assertTrue(data_points)
        self.assertEqual(set(data_points[0]), {"jarak_km", "harga_rp", "ac"})


class RiwayatDeletionTests(TestCase):
    def create_riwayat(self):
        return RiwayatPrediksi.objects.create(
            jarak_km=1.5,
            rating=4.2,
            ac="ya",
            estimasi_harga=900000,
            analisis_ai="Rekomendasi",
        )

    def test_history_section_shows_row_and_clear_all_actions(self):
        item = self.create_riwayat()

        response = self.client.get(reverse("prediksi:index"))

        self.assertContains(response, reverse("prediksi:hapus_semua_riwayat"))
        self.assertContains(
            response,
            reverse("prediksi:hapus_riwayat", args=[item.pk]),
        )
        self.assertContains(response, "Hapus semua")
        self.assertContains(response, "Hapus")

    def test_deletes_one_history_record(self):
        target = self.create_riwayat()
        other = self.create_riwayat()

        response = self.client.post(
            reverse("prediksi:hapus_riwayat", args=[target.pk])
        )

        self.assertRedirects(response, f"{reverse('prediksi:index')}#riwayat")
        self.assertFalse(RiwayatPrediksi.objects.filter(pk=target.pk).exists())
        self.assertTrue(RiwayatPrediksi.objects.filter(pk=other.pk).exists())

    def test_ajax_deletes_one_history_record_without_redirecting(self):
        target = self.create_riwayat()

        response = self.client.post(
            reverse("prediksi:hapus_riwayat", args=[target.pk]),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"message": "Riwayat berhasil dihapus."})
        self.assertFalse(RiwayatPrediksi.objects.filter(pk=target.pk).exists())

    def test_deletes_all_history_records(self):
        self.create_riwayat()
        self.create_riwayat()

        response = self.client.post(reverse("prediksi:hapus_semua_riwayat"))

        self.assertRedirects(response, f"{reverse('prediksi:index')}#riwayat")
        self.assertEqual(RiwayatPrediksi.objects.count(), 0)

    def test_ajax_deletes_all_history_records_without_redirecting(self):
        self.create_riwayat()
        self.create_riwayat()

        response = self.client.post(
            reverse("prediksi:hapus_semua_riwayat"),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"message": "2 riwayat berhasil dihapus."})
        self.assertEqual(RiwayatPrediksi.objects.count(), 0)

    def test_history_deletion_requires_post(self):
        item = self.create_riwayat()

        response = self.client.get(
            reverse("prediksi:hapus_riwayat", args=[item.pk])
        )

        self.assertEqual(response.status_code, 405)
        self.assertTrue(RiwayatPrediksi.objects.filter(pk=item.pk).exists())


class PredictionInputValidationTests(TestCase):
    def test_rejects_non_numeric_prediction_inputs(self):
        response = self.client.post(
            reverse("prediksi:index"),
            {"jarak": "abc", "rating": "4.2", "ac": "ya"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            "Jarak dan rating harus berupa angka yang valid.",
            status_code=400,
        )
        self.assertEqual(RiwayatPrediksi.objects.count(), 0)

    def test_rejects_empty_prediction_inputs(self):
        response = self.client.post(
            reverse("prediksi:index"),
            {"jarak": "", "rating": "", "ac": "tidak"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(RiwayatPrediksi.objects.count(), 0)

    def test_rejects_nan_and_infinite_prediction_inputs(self):
        response = self.client.post(
            reverse("prediksi:index"),
            {"jarak": "NaN", "rating": "inf", "ac": "ya"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            "Jarak dan rating harus berupa angka terbatas yang valid.",
            status_code=400,
        )
        self.assertEqual(RiwayatPrediksi.objects.count(), 0)

    def test_rejects_out_of_range_jarak_and_rating(self):
        response_jarak = self.client.post(
            reverse("prediksi:index"),
            {"jarak": "-1.0", "rating": "4.2", "ac": "ya"},
        )
        response_rating = self.client.post(
            reverse("prediksi:index"),
            {"jarak": "1.5", "rating": "6.0", "ac": "ya"},
        )

        self.assertEqual(response_jarak.status_code, 400)
        self.assertContains(
            response_jarak,
            "Jarak ke kampus harus berada di antara 0.1 hingga 25.0 km.",
            status_code=400,
        )
        self.assertEqual(response_rating.status_code, 400)
        self.assertContains(
            response_rating,
            "Rating penghuni harus berada di antara 1.0 hingga 5.0.",
            status_code=400,
        )
        self.assertEqual(RiwayatPrediksi.objects.count(), 0)

    def test_rejects_invalid_ac_choice(self):
        response = self.client.post(
            reverse("prediksi:index"),
            {"jarak": "1.5", "rating": "4.2", "ac": "invalid"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            "Pilihan fasilitas pendingin harus Ber-AC atau Non-AC.",
            status_code=400,
        )
        self.assertEqual(RiwayatPrediksi.objects.count(), 0)


from unittest.mock import Mock, patch

from django.test import TestCase
from django.urls import reverse
from apps.prediksi.services import analisis_kos_ai


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

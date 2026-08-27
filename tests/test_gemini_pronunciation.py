import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import app as app_module
from services.gemini_pronunciation import (
    GeminiPronunciationService,
    GeminiServiceError,
)


VALID_MODEL_RESULT = {
    "given_name": [
        {
            "text": "สม",
            "pronunciation": "สม",
            "initial": "ส",
            "vowel": "โอะ",
            "final": "ม",
            "final_group": "แม่กม",
            "confidence": "high",
        },
        {
            "text": "ชาย",
            "pronunciation": "ชาย",
            "initial": "ช",
            "vowel": "อา",
            "final": "ย",
            "final_group": "แม่เกย",
            "confidence": "high",
        },
    ],
    "surname": [
        {
            "text": "ใจ",
            "pronunciation": "ใจ",
            "initial": "จ",
            "vowel": "ไอ",
            "final": "",
            "final_group": "แม่ ก กา",
            "confidence": "high",
        },
        {
            "text": "ดี",
            "pronunciation": "ดี",
            "initial": "ด",
            "vowel": "อี",
            "final": "",
            "final_group": "แม่ ก กา",
            "confidence": "high",
        },
    ],
}


class FakeModels:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(text=json.dumps(self.result, ensure_ascii=False))


class FakeClient:
    def __init__(self, result=VALID_MODEL_RESULT):
        self.models = FakeModels(result)


class GeminiPronunciationServiceTest(unittest.TestCase):
    def test_returns_structured_breakdown_and_uses_requested_model(self):
        client = FakeClient()
        service = GeminiPronunciationService(
            model="gemini-3.1-flash-lite", client=client
        )

        result = service.analyze("สมชาย", "ใจดี")

        self.assertEqual(result["provider"], "gemini")
        self.assertEqual(result["model"], "gemini-3.1-flash-lite")
        self.assertEqual(
            {
                key: result["given_name"]["syllables"][0][key]
                for key in ("initial", "vowel", "final")
            },
            {"initial": "ส", "vowel": "โอะ", "final": "ม"},
        )
        call = client.models.calls[0]
        self.assertEqual(call["model"], "gemini-3.1-flash-lite")
        self.assertEqual(call["config"]["response_mime_type"], "application/json")
        self.assertIn("response_json_schema", call["config"])
        self.assertEqual(result["surname"]["warnings"], [])

    def test_rejects_inconsistent_model_output(self):
        invalid = json.loads(json.dumps(VALID_MODEL_RESULT, ensure_ascii=False))
        invalid["given_name"][0]["final_group"] = "แม่กน"
        service = GeminiPronunciationService(client=FakeClient(invalid))

        with self.assertRaises(GeminiServiceError):
            service.analyze("สมชาย", "ใจดี")

    def test_endpoint_selects_gemini_provider(self):
        service = GeminiPronunciationService(client=FakeClient())
        app_module.app.config.update(TESTING=True)

        with patch.object(app_module, "gemini_pronunciation_service", service):
            response = app_module.app.test_client().post(
                "/api/v1/pronunciations",
                json={
                    "given_name": "สมชาย",
                    "surname": "ใจดี",
                    "provider": "gemini",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["provider"], "gemini")


if __name__ == "__main__":
    unittest.main()

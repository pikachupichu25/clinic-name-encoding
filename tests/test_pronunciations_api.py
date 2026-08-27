import unittest
from unittest.mock import patch

from app import app
from services.pronunciation import PronunciationService


class PronunciationsApiTest(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True)
        self.client = app.test_client()

    def test_returns_selected_syllable_metadata_for_both_names(self):
        response = self.client.post(
            "/api/v1/pronunciations",
            json={"given_name": "สมชาย", "surname": "ใจดี"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.get_json()

        self.assertEqual(body["given_name"]["first_syllable_index"], 0)
        self.assertIn("syllables", body["given_name"])
        self.assertIn("syllables", body["surname"])
        self.assertIn("encoding_form", body["surname"]["syllables"][0])
        self.assertEqual(
            {
                key: body["given_name"]["syllables"][0][key]
                for key in ("initial", "vowel", "final")
            },
            {"initial": "ส", "vowel": "โอะ", "final": "ม"},
        )

    def test_serves_api_driven_frontend(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'/api/v1/pronunciations', response.data)
        response.close()

    def test_rejects_non_thai_names(self):
        response = self.client.post(
            "/api/v1/pronunciations",
            json={"given_name": "Alice", "surname": "Smith"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"]["code"], "invalid_thai_name")

    def test_uses_pronunciation_override(self):
        service = PronunciationService()
        service._overrides = {
            "given_name": {"อักษรพิเศษ": ["อัก", "สะ", "พิเศษ"]},
            "surname": {},
        }

        result = service.analyze("อักษรพิเศษ", "ใจดี")

        self.assertEqual(
            [syllable["encoding_form"] for syllable in result["given_name"]["syllables"]],
            ["อัก", "สะ", "พิเศษ"],
        )
        self.assertEqual(result["given_name"]["last_syllable_index"], 2)
        self.assertEqual(result["given_name"]["syllables"][0]["source"], "override")
        self.assertEqual(result["given_name"]["syllables"][0]["confidence"], "high")

    def test_pronounces_whole_name_then_cross_checks_original_initial(self):
        service = PronunciationService()
        service._overrides = {"given_name": {}, "surname": {}}

        with patch("services.pronunciation.pronunciate", return_value="สม-สี") as pronounce:
            result = service._analyze_name("สมศรี", "given_name")

        pronounce.assert_called_once_with("สมศรี")
        self.assertEqual(result["pronunciation_syllables"], ["สม", "สี"])
        self.assertEqual([item["text"] for item in result["syllables"]], ["สม", "ศรี"])
        self.assertEqual([item["encoding_form"] for item in result["syllables"]], ["สม", "สี"])
        self.assertEqual(result["syllables"][1]["initial"], "ศ")
        self.assertEqual(result["syllables"][1]["original_initial"], "ศ")
        self.assertEqual(result["syllables"][1]["pronounced_initial"], "ส")
        self.assertFalse(result["syllables"][1]["initial_matches_original"])

    def test_keeps_original_initial_for_matching_sounds(self):
        service = PronunciationService()
        service._overrides = {"given_name": {}, "surname": {}}

        with patch("services.pronunciation.pronunciate", return_value="สัก-สี"):
            result = service._analyze_name("ศักดิ์ศรี", "given_name")

        self.assertEqual([item["initial"] for item in result["syllables"]], ["ศ", "ศ"])
        self.assertEqual([item["pronounced_initial"] for item in result["syllables"]], ["ส", "ส"])
        self.assertTrue(all(item["initial_code_source"] == "original" for item in result["syllables"]))


if __name__ == "__main__":
    unittest.main()

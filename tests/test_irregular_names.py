import unittest

from app import app


class IrregularNamePronunciationTest(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True)
        self.client = app.test_client()

    def test_irregular_name_cases(self):
        cases = [
            ("เสือดาว", ["เสือ", "ดาว"], ["เสือ", "ดาว"], "pythainlp"),
            ("สมศรี", ["สม", "ศรี"], ["สม", "สี"], "pythainlp"),
            ("สมัคร", ["สะ", "มัก"], ["สะ", "มัก"], "override"),
        ]

        for name, expected_text, expected_encoding, expected_source in cases:
            with self.subTest(name=name):
                response = self.client.post(
                    "/api/v1/pronunciations",
                    json={"given_name": name, "surname": "ใจดี"},
                )

                self.assertEqual(response.status_code, 200)
                syllables = response.get_json()["given_name"]["syllables"]
                self.assertEqual([item["text"] for item in syllables], expected_text)
                self.assertEqual(
                    [item["encoding_form"] for item in syllables], expected_encoding
                )
                self.assertTrue(all(item["source"] == expected_source for item in syllables))


if __name__ == "__main__":
    unittest.main()

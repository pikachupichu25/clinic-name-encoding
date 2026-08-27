from __future__ import annotations

import json
import os
from typing import Any

from services.pronunciation import PronunciationService, THAI_CHARACTER
from services.syllable_analysis import THAI_CONSONANTS

try:
    from google import genai

    GOOGLE_GENAI_AVAILABLE = True
except ImportError:
    genai = None
    GOOGLE_GENAI_AVAILABLE = False


DEFAULT_MODEL = "gemini-3.1-flash-lite"
CANONICAL_VOWELS = (
    "อะ",
    "อา",
    "อิ",
    "อี",
    "อึ",
    "อื",
    "อุ",
    "อู",
    "เอะ",
    "เอ",
    "แอะ",
    "แอ",
    "โอะ",
    "โอ",
    "เอาะ",
    "ออ",
    "เออะ",
    "เออ",
    "เอือะ",
    "เอือ",
    "เอียะ",
    "เอีย",
    "อัวะ",
    "อัว",
    "เอา",
    "อำ",
    "ไอ",
)
UNCODED_VOWELS_BY_FIELD = {"given_name": {"อำ"}, "surname": set()}
FINAL_GROUPS = {
    "": "แม่ ก กา",
    "ก": "แม่กก",
    "ด": "แม่กด",
    "บ": "แม่กบ",
    "ม": "แม่กม",
    "ง": "แม่กง",
    "น": "แม่กน",
    "ว": "แม่เกอว",
    "ย": "แม่เกย",
}

SYLLABLE_SCHEMA = {
    "type": "object",
    "required": [
        "text",
        "pronunciation",
        "initial",
        "vowel",
        "final",
        "final_group",
        "confidence",
    ],
    "properties": {
        "text": {
            "type": "string",
            "description": "Thai-script syllable as it belongs to the name.",
        },
        "pronunciation": {
            "type": "string",
            "description": "Spoken syllable written in Thai script, never IPA or Latin.",
        },
        "initial": {
            "type": "string",
            "description": "One written Thai initial used by the clinic encoder.",
        },
        "vowel": {"type": "string", "enum": list(CANONICAL_VOWELS)},
        "final": {"type": "string", "enum": list(FINAL_GROUPS)},
        "final_group": {"type": "string", "enum": list(FINAL_GROUPS.values())},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
    },
}

RESPONSE_SCHEMA = {
    "type": "object",
    "required": ["given_name", "surname"],
    "properties": {
        "given_name": {
            "type": "array",
            "items": SYLLABLE_SCHEMA,
            "minItems": 1,
        },
        "surname": {
            "type": "array",
            "items": SYLLABLE_SCHEMA,
            "minItems": 1,
        },
    },
}


class GeminiConfigurationError(RuntimeError):
    pass


class GeminiServiceError(RuntimeError):
    pass


class GeminiPronunciationService:
    """Ask Gemini to segment Thai names and return clinic-ready sound parts."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        client: Any | None = None,
    ):
        self._api_key = api_key
        self.model = model or os.getenv("GEMINI_MODEL", DEFAULT_MODEL)
        self._client = client

    def analyze(self, given_name: object, surname: object) -> dict[str, Any]:
        normalized_given = PronunciationService._normalize_name(
            given_name, "given_name"
        )
        normalized_surname = PronunciationService._normalize_name(surname, "surname")
        client = self._get_client()

        try:
            response = client.models.generate_content(
                model=self.model,
                contents=self._prompt(normalized_given, normalized_surname),
                config={
                    "response_mime_type": "application/json",
                    "response_json_schema": RESPONSE_SCHEMA,
                    "temperature": 0,
                },
            )
        except Exception as error:
            raise GeminiServiceError(
                "Gemini could not analyze the Thai name. Check the model name, "
                "API key, quota, and network connection."
            ) from error

        raw_text = getattr(response, "text", None)
        if not isinstance(raw_text, str) or not raw_text.strip():
            raise GeminiServiceError("Gemini returned an empty pronunciation result.")

        try:
            payload = json.loads(raw_text)
        except json.JSONDecodeError as error:
            raise GeminiServiceError("Gemini returned invalid JSON.") from error

        return {
            "provider": "gemini",
            "model": self.model,
            "given_name": self._name_response(
                given_name, normalized_given, payload, "given_name"
            ),
            "surname": self._name_response(
                surname, normalized_surname, payload, "surname"
            ),
        }

    def _get_client(self):
        if self._client is not None:
            return self._client
        if not GOOGLE_GENAI_AVAILABLE:
            raise GeminiConfigurationError(
                "Gemini support is not installed. Run pip install -r requirements.txt."
            )

        api_key = self._api_key or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise GeminiConfigurationError(
                "GEMINI_API_KEY is not configured on the Flask server."
            )
        self._client = genai.Client(api_key=api_key)
        return self._client

    def _name_response(
        self,
        raw_value: object,
        normalized: str,
        payload: object,
        field: str,
    ) -> dict[str, Any]:
        if not isinstance(payload, dict) or not isinstance(payload.get(field), list):
            raise GeminiServiceError(f"Gemini omitted {field} from its JSON response.")

        syllables = [
            self._validated_syllable(item, field) for item in payload[field]
        ]
        if not syllables:
            raise GeminiServiceError(f"Gemini returned no syllables for {field}.")

        warnings = []
        if len(syllables) == 1:
            warnings.append(
                {
                    "code": "single_syllable_name",
                    "field": field,
                    "message": "Only one syllable was found. Please verify the name.",
                }
            )
        if any(item["confidence"] == "low" for item in syllables):
            warnings.append(
                {
                    "code": "gemini_pronunciation_needs_review",
                    "field": field,
                    "message": "Gemini marked part of this pronunciation as uncertain.",
                }
            )
        uncoded_vowels = sorted(
            {
                item["vowel"]
                for item in syllables
                if item["vowel"] in UNCODED_VOWELS_BY_FIELD[field]
            }
        )
        if uncoded_vowels:
            warnings.append(
                {
                    "code": "vowel_code_missing",
                    "field": field,
                    "message": (
                        "The clinic code table has no mapping for vowel "
                        + ", ".join(uncoded_vowels)
                        + ". Please review it before encoding."
                    ),
                }
            )

        return {
            "input": raw_value.strip() if isinstance(raw_value, str) else raw_value,
            "normalized": normalized,
            "syllables": syllables,
            "first_syllable_index": 0,
            "last_syllable_index": len(syllables) - 1,
            "warnings": warnings,
        }

    @staticmethod
    def _validated_syllable(item: object, field: str) -> dict[str, str]:
        if not isinstance(item, dict):
            raise GeminiServiceError(f"Gemini returned an invalid syllable for {field}.")

        required = (
            "text",
            "pronunciation",
            "initial",
            "vowel",
            "final",
            "final_group",
            "confidence",
        )
        if any(not isinstance(item.get(key), str) for key in required):
            raise GeminiServiceError(f"Gemini returned an incomplete syllable for {field}.")
        if not item["text"].strip() or not item["pronunciation"].strip():
            raise GeminiServiceError(f"Gemini returned an empty syllable for {field}.")
        if not THAI_CHARACTER.search(item["text"]) or not THAI_CHARACTER.search(
            item["pronunciation"]
        ):
            raise GeminiServiceError(
                f"Gemini returned a non-Thai pronunciation for {field}."
            )
        initial = item["initial"].strip()
        if len(initial) != 1 or initial not in THAI_CONSONANTS:
            raise GeminiServiceError(f"Gemini returned an invalid initial for {field}.")
        if item["vowel"] not in CANONICAL_VOWELS:
            raise GeminiServiceError(f"Gemini returned an unknown vowel for {field}.")

        final = item["final"]
        if final not in FINAL_GROUPS or item["final_group"] != FINAL_GROUPS[final]:
            raise GeminiServiceError(
                f"Gemini returned an inconsistent final sound for {field}."
            )
        if item["confidence"] not in {"high", "medium", "low"}:
            raise GeminiServiceError(f"Gemini returned invalid confidence for {field}.")

        return {
            "text": item["text"].strip(),
            "encoding_form": item["pronunciation"].strip(),
            "pronunciation": item["pronunciation"].strip(),
            "initial": initial,
            "vowel": item["vowel"],
            "final": final,
            "final_group": item["final_group"],
            "confidence": item["confidence"],
            "source": "gemini",
        }

    @staticmethod
    def _prompt(given_name: str, surname: str) -> str:
        return f"""You are a Thai linguist preparing names for a clinic code system.

Analyze every spoken syllable in the given name and surname. Return only the
JSON required by the supplied schema. Use Thai script for both text and
pronunciation; never return IPA, RTGS, explanations, or code numbers.

Rules:
- initial is the single WRITTEN Thai letter that carries the initial sound.
- Preserve a pronounced written initial even when its sound matches another
  letter: ศุกร์ has initial ศ, not ส.
- Remove a silent tone-class leader: หนู has initial น, not ห.
- vowel must be one canonical value permitted by the schema.
- final is the canonical PRONOUNCED coda: ก ด บ ม ง น ว ย, or an empty string.
- final_group must exactly match final.
- text is the logical Thai syllable from the name; pronunciation is how that
  syllable is spoken, written in ordinary Thai spelling.
- Mark genuinely ambiguous analyses as low confidence.

Reviewed examples:
สม -> initial ส, vowel โอะ, final ม, final_group แม่กม
เรียน -> initial ร, vowel เอีย, final น, final_group แม่กน
เสือ -> initial ส, vowel เอือ, final empty, final_group แม่ ก กา
ศุกร์ (pronounced สุก) -> initial ศ, vowel อุ, final ก, final_group แม่กก
หนู -> initial น, vowel อู, final empty, final_group แม่ ก กา
สมัคร -> two spoken syllables สะ and มัก

given_name: {given_name}
surname: {surname}
"""

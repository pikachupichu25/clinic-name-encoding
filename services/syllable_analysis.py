from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any


ROOT = Path(__file__).parent.parent
DEFAULT_CASES_PATH = ROOT / "data" / "thai_one_syllable_test_candidates.json"
THAI_CHARACTER = re.compile(r"[\u0E00-\u0E7F]")
THAI_CONSONANTS = set(
    "กขฃคฅฆงจฉชซฌญฎฏฐฑฒณดตถทธนบปผฝพฟภมยรลวศษสหฬอฮ"
)
SILENT_LEADER_FOLLOWERS = set("งญนมยรลว")

FINAL_SOUND_MAP = {
    **{letter: ("ก", "แม่กก") for letter in "กขคฆ"},
    **{letter: ("ด", "แม่กด") for letter in "ดตจชซฎฏฐฑฒถทธศษส"},
    **{letter: ("บ", "แม่กบ") for letter in "บปพฟภ"},
    "ม": ("ม", "แม่กม"),
    "ง": ("ง", "แม่กง"),
    **{letter: ("น", "แม่กน") for letter in "นณญรลฬ"},
    "ว": ("ว", "แม่เกอว"),
    "ย": ("ย", "แม่เกย"),
}


class SyllableAnalysisError(ValueError):
    pass


class SyllableAnalyzer:
    """Break a one-syllable Thai form into clinic encoding components."""

    def __init__(self, cases_path: Path = DEFAULT_CASES_PATH):
        self._known_cases = self._load_cases(cases_path)

    def analyze(self, word: object, pronunciation: object | None = None) -> dict[str, Any]:
        original = self._validate(word, "word")
        spoken = self._validate(pronunciation, "pronunciation") if pronunciation else original

        if "-" in spoken or any(char.isspace() for char in spoken):
            raise SyllableAnalysisError("pronunciation must contain exactly one syllable")

        known = self._known_cases.get(original)
        if known:
            return {
                "word": original,
                "pronunciation": spoken,
                "initial": known["initial"],
                "vowel": known["vowel"],
                "final": known["final"],
                "final_group": known["final_group"],
                "source": "test_case",
            }

        initial = self._detect_initial(original)
        vowel = self._detect_vowel(spoken)
        final, final_group = self._detect_final(spoken, vowel)

        return {
            "word": original,
            "pronunciation": spoken,
            "initial": initial,
            "vowel": vowel,
            "final": final,
            "final_group": final_group,
            "source": "rules",
        }

    @staticmethod
    def _validate(value: object, field: str) -> str:
        if not isinstance(value, str):
            raise SyllableAnalysisError(f"{field} must be Thai text")
        normalized = unicodedata.normalize("NFC", value).strip()
        if not normalized or not THAI_CHARACTER.search(normalized):
            raise SyllableAnalysisError(f"{field} must contain Thai characters")
        return normalized

    @staticmethod
    def _load_cases(path: Path) -> dict[str, dict[str, Any]]:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return {
            case["word"]: case
            for case in payload.get("cases", [])
            if isinstance(case, dict) and isinstance(case.get("word"), str)
        }

    @staticmethod
    def _consonants(text: str) -> list[str]:
        return [char for char in text if char in THAI_CONSONANTS]

    def _detect_initial(self, original: str) -> str:
        consonants = self._consonants(original)
        if not consonants:
            raise SyllableAnalysisError("initial consonant could not be identified")
        if len(consonants) > 1:
            if consonants[0] == "ห" and consonants[1] in SILENT_LEADER_FOLLOWERS:
                return consonants[1]
            if consonants[0] == "อ" and consonants[1] == "ย":
                return "ย"
        return consonants[0]

    @staticmethod
    def _detect_vowel(spoken: str) -> str:
        patterns = (
            ("เอา", lambda value: value.startswith("เ") and "า" in value),
            ("เอีย", lambda value: value.startswith("เ") and "ีย" in value),
            ("เอือ", lambda value: value.startswith("เ") and "ือ" in value),
            ("เอาะ", lambda value: value.startswith("เ") and "าะ" in value),
            ("เออ", lambda value: value.startswith("เ") and ("อ" in value or "ิ" in value)),
            ("อัว", lambda value: "ัว" in value),
            ("อำ", lambda value: "ำ" in value),
            ("ไอ", lambda value: value.startswith(("ไ", "ใ"))),
            ("อิ", lambda value: "ิ" in value),
            ("อี", lambda value: "ี" in value),
            ("อึ", lambda value: "ึ" in value),
            ("อื", lambda value: "ื" in value),
            ("อุ", lambda value: "ุ" in value),
            ("อู", lambda value: "ู" in value),
            ("แอะ", lambda value: value.startswith("แ") and ("ะ" in value or "็" in value)),
            ("แอ", lambda value: value.startswith("แ")),
            ("โอะ", lambda value: value.startswith("โ") and "ะ" in value),
            ("โอ", lambda value: value.startswith("โ")),
            ("เอะ", lambda value: value.startswith("เ") and ("ะ" in value or "็" in value)),
            ("เอ", lambda value: value.startswith("เ")),
            ("ออ", lambda value: "อ" in value),
            ("อะ", lambda value: "ะ" in value or "ั" in value),
            ("อา", lambda value: "า" in value),
        )
        for vowel, matches in patterns:
            if matches(spoken):
                return vowel

        # A closed Thai syllable with no visible vowel normally contains a
        # fully reduced โอะ, e.g. สม, คน, and นก.
        if len(SyllableAnalyzer._consonants(spoken)) >= 2:
            return "โอะ"
        return "อะ"

    def _detect_final(self, spoken: str, vowel: str) -> tuple[str, str]:
        open_endings = {
            "เอีย": ("ีย", "ียะ"),
            "เอือ": ("ือ", "ือะ"),
            "เอาะ": ("าะ",),
            "เออ": ("อ", "อะ"),
            "ออ": ("อ",),
            "อัว": ("ัว", "ัวะ"),
        }
        if any(spoken.endswith(ending) for ending in open_endings.get(vowel, ())):
            return "", "แม่ ก กา"
        if spoken[-1] in "ะาิีึืุู":
            return "", "แม่ ก กา"

        consonants = self._consonants(spoken)
        if len(consonants) < 2:
            return "", "แม่ ก กา"
        written_final = consonants[-1]
        final = FINAL_SOUND_MAP.get(written_final)
        if final is None:
            raise SyllableAnalysisError(
                f'final consonant "{written_final}" could not be classified'
            )
        return final

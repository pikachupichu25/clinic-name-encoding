from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from services.syllable_analysis import SyllableAnalyzer

try:
    from pythainlp.tokenize import syllable_tokenize
    from pythainlp.transliterate import pronunciate

    PYTHAINLP_AVAILABLE = True
except ImportError:  # Allows a useful development error before dependencies install.
    PYTHAINLP_AVAILABLE = False


THAI_CHARACTER = re.compile(r"[\u0E00-\u0E7F]")
MAX_NAME_LENGTH = 100
DEFAULT_OVERRIDES_PATH = Path(__file__).parent.parent / "data" / "pronunciation_overrides.json"


@dataclass(frozen=True)
class InputValidationError(Exception):
    code: str
    message: str


class PronunciationService:
    """Analyze ThaiNLP pronunciation before mapping selected syllables to code parts."""

    def __init__(self, overrides_path: Path = DEFAULT_OVERRIDES_PATH):
        self._overrides = self._load_overrides(overrides_path)
        self._syllable_analyzer = SyllableAnalyzer()

    def analyze(self, given_name: object, surname: object) -> dict[str, Any]:
        return {
            "given_name": self._analyze_name(given_name, "given_name"),
            "surname": self._analyze_name(surname, "surname"),
        }

    def _analyze_name(self, raw_value: object, field: str) -> dict[str, Any]:
        name = self._normalize_name(raw_value, field)
        override = self._overrides.get(field, {}).get(name)
        pronunciation = self._pronounce_name(name)
        spoken_syllables = override or self._split_pronunciation(pronunciation)
        used_nlp = PYTHAINLP_AVAILABLE and not override
        source = "override" if override is not None else ("pythainlp" if used_nlp else "fallback")

        if not spoken_syllables:
            raise InputValidationError(
                "pronunciation_unavailable",
                f"Could not find Thai syllables in {field}.",
            )

        # An approved override supplies clinic-ready forms, so use those forms
        # as its own traceable pair when the original tokenizer cannot align
        # one written token to the corrected spoken syllables (for example สมัคร).
        original_syllables = override or self._segment_original_syllables(name)
        syllables = self._syllables(
            original_syllables, spoken_syllables, source, "high" if override else ("medium" if used_nlp and len(spoken_syllables) > 1 else "low")
        )

        warning: list[dict[str, str]] = []
        if not used_nlp:
            warning.append(
                {
                    "code": "pronunciation_needs_review",
                    "field": field,
                    "message": "Thai NLP is unavailable. Please verify the selected syllables.",
                }
            )
        elif len(spoken_syllables) == 1:
            warning.append(
                {
                    "code": "single_syllable_name",
                    "field": field,
                    "message": "Only one syllable was found. Please verify the name.",
                }
            )

        return {
            "input": raw_value.strip() if isinstance(raw_value, str) else raw_value,
            "normalized": name,
            "pronunciation": pronunciation,
            "pronunciation_syllables": spoken_syllables,
            "syllables": syllables,
            "first_syllable_index": 0,
            "last_syllable_index": len(syllables) - 1,
            "warnings": warning,
        }

    @staticmethod
    def _normalize_name(raw_value: object, field: str) -> str:
        if not isinstance(raw_value, str):
            raise InputValidationError(
                "invalid_thai_name", f"{field} must be a text value."
            )

        name = unicodedata.normalize("NFC", raw_value).strip()
        if not name or len(name) > MAX_NAME_LENGTH or not THAI_CHARACTER.search(name):
            raise InputValidationError(
                "invalid_thai_name", f"{field} must contain Thai characters."
            )

        return name

    @staticmethod
    def _load_overrides(path: Path) -> dict[str, dict[str, list[str]]]:
        if not path.exists():
            return {"given_name": {}, "surname": {}}

        try:
            import json

            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {"given_name": {}, "surname": {}}

        valid_overrides: dict[str, dict[str, list[str]]] = {"given_name": {}, "surname": {}}
        for field in valid_overrides:
            entries = payload.get(field, {}) if isinstance(payload, dict) else {}
            if not isinstance(entries, dict):
                continue
            valid_overrides[field] = {
                name: syllables
                for name, syllables in entries.items()
                if isinstance(name, str)
                and isinstance(syllables, list)
                and len(syllables) >= 2
                and all(isinstance(syllable, str) and syllable for syllable in syllables)
            }

        return valid_overrides

    def _syllables(
        self,
        original_syllables: list[str],
        spoken_syllables: list[str],
        source: str,
        confidence: str,
    ) -> list[dict[str, str | bool]]:
        return [
            self._syllable_response(
                self._original_syllable_for_position(
                    original_syllables, position, len(spoken_syllables)
                ),
                spoken_syllable,
                source,
                confidence,
            )
            for position, spoken_syllable in enumerate(spoken_syllables)
        ]

    @staticmethod
    def _original_syllable_for_position(
        original_syllables: list[str], position: int, syllable_count: int
    ) -> str:
        if len(original_syllables) == syllable_count:
            return original_syllables[position]
        if position == 0 or len(original_syllables) == 1:
            return original_syllables[0]
        if position == syllable_count - 1:
            return original_syllables[-1]
        return original_syllables[min(position, len(original_syllables) - 1)]

    def _syllable_response(
        self, original_syllable: str, spoken_syllable: str, source: str, confidence: str
    ) -> dict[str, str | bool]:
        # Analyze the spoken form for vowel and final values. The clinic's
        # initial code remains tied to the original spelling, so a changed
        # pronunciation initial (for example ศ → ส) is recorded but does not
        # replace the original initial used for encoding.
        spoken_breakdown = self._syllable_analyzer.analyze(spoken_syllable, spoken_syllable)
        original_breakdown = self._syllable_analyzer.analyze(original_syllable, original_syllable)

        return {
            "text": original_syllable,
            "encoding_form": spoken_syllable,
            "pronunciation": spoken_syllable,
            "source": source,
            "confidence": confidence,
            "initial": original_breakdown["initial"],
            "vowel": spoken_breakdown["vowel"],
            "final": spoken_breakdown["final"],
            "final_group": spoken_breakdown["final_group"],
            "original_initial": original_breakdown["initial"],
            "pronounced_initial": spoken_breakdown["initial"],
            "initial_matches_original": original_breakdown["initial"] == spoken_breakdown["initial"],
            "initial_code_source": "original",
        }

    @staticmethod
    def _split_pronunciation(pronunciation: str) -> list[str]:
        return [part for part in re.split(r"[-\s]+", pronunciation) if part]

    @staticmethod
    def _segment_original_syllables(name: str) -> list[str]:
        if not PYTHAINLP_AVAILABLE:
            return [name]

        try:
            syllables = [
                syllable.strip()
                for syllable in syllable_tokenize(name)
                if syllable.strip()
            ]
        except Exception:
            return [name]

        return syllables or [name]

    @staticmethod
    def _pronounce_name(name: str) -> str:
        if not PYTHAINLP_AVAILABLE:
            return name

        try:
            return pronunciate(name)
        except Exception:
            return name

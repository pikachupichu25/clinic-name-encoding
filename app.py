from __future__ import annotations

from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from dotenv import load_dotenv

from services.gemini_pronunciation import (
    GeminiConfigurationError,
    GeminiPronunciationService,
    GeminiServiceError,
)
from services.pronunciation import InputValidationError, PronunciationService


ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env")
app = Flask(__name__)
pronunciation_service = PronunciationService()
gemini_pronunciation_service = GeminiPronunciationService()


@app.get("/")
def index():
    return send_from_directory(ROOT, "index.html")


@app.post("/api/v1/pronunciations")
def pronunciations():
    payload = request.get_json(silent=True)

    if not isinstance(payload, dict):
        return error_response(
            "invalid_json",
            "Request body must be a JSON object.",
        )

    provider = payload.get("provider", "pythainlp")
    if provider not in {"pythainlp", "gemini"}:
        return error_response(
            "invalid_provider",
            'provider must be either "pythainlp" or "gemini".',
        )

    service = (
        gemini_pronunciation_service if provider == "gemini" else pronunciation_service
    )
    try:
        result = service.analyze(
            given_name=payload.get("given_name"),
            surname=payload.get("surname"),
        )
    except InputValidationError as error:
        return error_response(error.code, error.message)
    except GeminiConfigurationError as error:
        return error_response("gemini_not_configured", str(error), 503)
    except GeminiServiceError as error:
        return error_response("gemini_request_failed", str(error), 502)

    return jsonify(result)

def error_response(code: str, message: str, status: int = 400):
    return jsonify({"error": {"code": code, "message": message}}), status


if __name__ == "__main__":
    app.run(debug=True)

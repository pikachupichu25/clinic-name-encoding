# Clinic Name Encoder

Flask application for deriving the clinic's eight-digit code from a Thai given
name and surname. Flask and PyThaiNLP determine the first and final spoken
syllables; the browser applies the clinic's existing code tables.

## Setup

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/thainlp data get thai_w2p_npz
```

The final command downloads PyThaiNLP's word-to-phoneme corpus. It is required
for the API's pronunciation field. The syllable segmenter is supplied by
`python-crfsuite`, and the G2P model requires NumPy; both are listed in
`requirements.txt`.

Create `.env` from `.env.example` if you do not already have one, then set
`GEMINI_API_KEY` to a key created in Google AI Studio. The default model is
`gemini-3.1-flash-lite`; override it with `GEMINI_MODEL` if the model ID
available to your account differs. Never put this key in `index.html` or send
it from the browser.

## Run

```sh
.venv/bin/flask --app app run --debug
```

Open <http://127.0.0.1:5000>.

## API

Analyze a full name with `POST /api/v1/pronunciations`. Every returned
syllable includes its `initial`, `vowel`, and pronounced `final`:

```json
{
  "given_name": "สมชาย",
  "surname": "ใจดี",
  "provider": "gemini"
}
```

Use `provider: "pythainlp"` to compare with the existing local analyzer. The
Gemini provider sends both names in one server-side request and validates the
model's JSON before returning it to the frontend.

Accurate vowels that do not yet exist in the clinic table, currently `อำ` and
`ไอ`, are returned unchanged with a `vowel_code_missing` review warning. The
server does not guess a numeric code for them. The response includes every
detected syllable; the frontend uses the first and last syllables for the
clinic code. For a one-syllable given name, the first syllable is encoded
normally and the final two given-name digits are `00`; for a one-syllable
surname, the final surname digit is `0`.

## Test

```sh
.venv/bin/python -m unittest discover -s tests -v
node tests/test_encoder.js
```

## Pronunciation overrides

Add non-standard personal-name pronunciations to
`data/pronunciation_overrides.json`. Each value must contain at least two
Thai-script syllables that can be passed to the frontend encoder.

```json
{
  "given_name": {
    "ตัวอย่าง": ["ตัว", "อย่าง"]
  },
  "surname": {}
}
```

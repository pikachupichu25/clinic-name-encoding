# Thai Name Encoder — Flask Specification

## 1. Goal

Convert a real Thai given name and surname into an eight-digit clinic code:

```text
[6 digits for given name]-[2 digits for surname]
```

The Flask API is responsible for Thai-language analysis and pronunciation. The
browser is responsible for applying the existing consonant, vowel, and final
consonant code tables.

Example format:

```text
018022-12
```

## 2. User flow

1. A user enters a complete Thai given name and surname by typing or using the
   microphone button beside either field.
2. A speech transcript is placed in the targeted field for user review; speech
   recognition must never submit or encode the name automatically.
3. The user confirms or edits both text fields and requests analysis.
4. The frontend submits both values to the pronunciation API.
5. The API normalizes the text, finds the likely spoken syllables, and returns
   the first and final syllable of each name together with its pronunciation.
6. The frontend applies the existing `INITIAL_CODES`, `VOWEL_CODES`, and
   `FINAL_CODES` rules to those returned syllables.
7. The frontend renders:
   - a 6-digit given-name code;
   - two surname vowel digits;
   - the combined code as `XXXXXX-YY`;
   - a breakdown of all four selected syllables.
8. If the API cannot confidently pronounce a name, the user can correct the
   selected syllables before encoding.

## 3. Architecture

```text
Browser
  ├─ Form: typed or spoken given name + surname
  ├─ Browser Thai speech recognition (when supported)
  ├─ POST /api/v1/pronunciations
  └─ Existing JavaScript encoder
       └─ XXXXXX-YY

Flask application
  ├─ Input validation and normalization
  ├─ Name-pronunciation overrides
  ├─ Thai NLP word/syllable segmentation
  ├─ Thai grapheme-to-phoneme (G2P) service
  └─ JSON response
```

The server does not generate a numeric code. This keeps the clinic's code
tables in one frontend encoder and lets the UI show exactly how every digit was
derived.

## 4. Thai NLP and pronunciation pipeline

### 4.1 Processing order

For each name field:

1. Trim whitespace and normalize Unicode to NFC.
2. Verify that the input contains Thai characters and is within the maximum
   supported length.
3. Check an administrator-maintained pronunciation override dictionary first.
4. Segment the name into Thai syllables using PyThaiNLP.
5. Run the selected syllables through a Thai G2P engine to obtain a display
   pronunciation (IPA or a readable phoneme string).
6. Return a Thai-script `encoding_form` for every syllable. This must use a
   spelling/form that the existing JavaScript encoder recognizes.
7. Attach warnings when segmentation or pronunciation is uncertain.

### 4.2 Required behavior for names

Thai personal names are often absent from ordinary dictionaries and may have
non-obvious pronunciation. The implementation must therefore use a custom
name dictionary and allow a user correction. It must never silently claim that
an uncertain pronunciation is certain.

The initial implementation may use PyThaiNLP for syllable segmentation and its
compatible pronunciation tooling. Before production release, validate the
chosen G2P engine with a clinic-provided set of Thai names; the API contract
must not depend on a particular G2P library's internal output format.

## 5. API

### `POST /api/v1/pronunciations`

Analyze one real given name and one real surname.

#### Request

```json
{
  "given_name": "กอวิด",
  "surname": "ใจดี"
}
```

#### Successful response — `200 OK`

```json
{
  "given_name": {
    "input": "กอวิด",
    "normalized": "กอวิด",
    "syllables": [
      {
        "text": "กอ",
        "encoding_form": "กอ",
        "pronunciation": "kɔː",
        "initial": "ก",
        "vowel": "ออ",
        "final": "",
        "final_group": "แม่ ก กา",
        "source": "dictionary",
        "confidence": "high"
      },
      {
        "text": "วิด",
        "encoding_form": "วิด",
        "pronunciation": "wít",
        "initial": "ว",
        "vowel": "อิ",
        "final": "ด",
        "final_group": "แม่กด",
        "source": "g2p",
        "confidence": "medium"
      }
    ],
    "first_syllable_index": 0,
    "last_syllable_index": 1,
    "warnings": []
  },
  "surname": {
    "input": "ใจดี",
    "normalized": "ใจดี",
    "syllables": [
      {
        "text": "ใจ",
        "encoding_form": "ใจ",
        "pronunciation": "t͡ɕaj",
        "initial": "จ",
        "vowel": "ไอ",
        "final": "",
        "final_group": "แม่ ก กา",
        "source": "g2p",
        "confidence": "medium"
      },
      {
        "text": "ดี",
        "encoding_form": "ดี",
        "pronunciation": "diː",
        "initial": "ด",
        "vowel": "อี",
        "final": "",
        "final_group": "แม่ ก กา",
        "source": "g2p",
        "confidence": "medium"
      }
    ],
    "first_syllable_index": 0,
    "last_syllable_index": 1,
    "warnings": []
  }
}
```

`encoding_form` is the required frontend input. `pronunciation` is for review
and transparency only; the numeric encoder must not parse IPA.

Each syllable also includes its encoding breakdown: `initial` is the coded
written initial, `vowel` is the canonical vowel form, and `final` is the
canonical pronounced final (an empty string for an open syllable).

#### Validation failure — `400 Bad Request`

```json
{
  "error": {
    "code": "invalid_thai_name",
    "message": "given_name must contain Thai characters"
  }
}
```

#### Uncertain result — `200 OK`

Return the best candidate, set `confidence` to `low`, and include a warning.
The frontend must ask the user to review or edit the selected syllables before
showing the final code.

```json
{
  "warnings": [
    {
      "code": "pronunciation_needs_review",
      "field": "surname",
      "message": "Please verify the first and last surname syllable."
    }
  ]
}
```

## 6. Frontend requirements

### Inputs

- Replace the manual first/last-syllable name fields with:
  - `ชื่อ` (complete given name)
  - `นามสกุล` (complete surname)
- Display the API's selected first and final syllable for each field.
- Provide editable syllable controls when the response has a warning.

### Speech-recognition input

Speech recognition is an optional input method for the two existing text
fields; it does not replace typed input.

#### Technology and support

- Use the browser Web Speech API through `window.SpeechRecognition` or the
  prefixed `window.webkitSpeechRecognition` implementation.
- Set `lang = "th-TH"`, `continuous = false`, `interimResults = true`, and
  `maxAlternatives = 3`.
- Treat the feature as progressive enhancement. The Speech Recognition API has
  limited browser availability; when unsupported, hide or disable microphone
  controls and leave the normal text form fully usable.
- Serve production over HTTPS. Local development may use `localhost`.
- The Flask API remains text-only for the first implementation. The browser
  must not upload or persist raw microphone audio to this application.

The browser API and its availability constraints are documented by
[MDN SpeechRecognition](https://developer.mozilla.org/en-US/docs/Web/API/SpeechRecognition).
Some browser implementations use a server-based recognition engine and may
send audio to the browser vendor's service, so the UI must disclose this before
the first microphone use.

#### Controls

- Place a microphone button inside or immediately beside each field:
  - `พูดชื่อ` targets the given-name field.
  - `พูดนามสกุล` targets the surname field.
- Only one field may listen at a time.
- Pressing a microphone button starts a fresh recognition session for that
  field. Pressing it again stops the active session.
- The active button must visibly change state and show `กำลังฟัง…` in an
  `aria-live` status region.
- The control must be a real `<button type="button">`, keyboard accessible,
  and have an explicit Thai `aria-label`.

#### Transcript review

- Interim text may appear as a temporary preview but must not overwrite the
  committed field value.
- When a final result arrives, show up to three transcript alternatives when
  the browser provides them.
- Preselect the highest-ranked transcript and place it in the targeted field.
- The user must be able to choose another alternative or edit the text.
- Never trigger `/api/v1/pronunciations` from the speech-result event. Encoding
  starts only after the user presses `วิเคราะห์และสร้างรหัส`.
- Keep the other name field unchanged when speech recognition updates one
  field.

#### Recognition states

Each microphone control must expose these states:

```text
unsupported → idle → requesting_permission → listening → reviewing → idle
                                                    └──→ error → idle
```

- `unsupported`: typed input remains available.
- `requesting_permission`: prevent repeated microphone starts.
- `listening`: provide visible and non-visual feedback and allow cancellation.
- `reviewing`: display the recognized transcript and alternatives.
- `error`: retain the user's previous typed value and show a recoverable Thai
  message.

#### Speech errors

Handle at least these Web Speech API error values:

| Error | Required UI behavior |
|---|---|
| `not-allowed` / `service-not-allowed` | Explain how to allow microphone access; preserve typed values. |
| `audio-capture` | Report that no usable microphone was found. |
| `no-speech` | Ask the user to try again and speak only the target name. |
| `network` | Explain that recognition service connectivity failed; offer typing. |
| `aborted` | Return silently to idle when user-initiated; otherwise show retry. |
| unknown | Show a generic retry message without clearing either field. |

Speech errors must not be sent to the Flask pronunciation API as name values.

### Numeric encoding

Keep the current encoding tables and JavaScript logic as the source of truth.

```text
given first syllable: initial(2) + vowel(1) + final(1)
given last syllable:  vowel(1) + final(1), or 00 when the given name has one syllable
surname first:        vowel(1)
surname last:         vowel(1), or 0 when the surname has one syllable

summary: XXXXXX-YY
```

The UI must retain the existing breakdown and add two surname rows that show
only their vowel code. The summary box must appear above all breakdown rows.

### Error states

- Disable the encode button while the API request is in progress.
- Show a Thai-language error if the API is unavailable or validation fails.
- A one-syllable name is valid: encode its first-syllable portion and show
  `00` for a given-name final position or `0` for a surname final position.
  Do not show a code when no usable syllable is available.
- Show a review warning rather than a definitive result for low-confidence
  pronunciation.
- If speech recognition fails or is unsupported, preserve the current field
  values and allow typed submission.

## 7. Flask application structure

```text
clinic-name-encoding/
├── app.py
├── requirements.txt
├── services/
│   ├── pronunciation.py
│   ├── thai_nlp.py
│   └── overrides.py
├── data/
│   └── pronunciation_overrides.json
├── static/
│   ├── css/app.css
│   └── js/encoder.js
├── templates/
│   └── index.html
└── tests/
    ├── test_pronunciations_api.py
    └── test_encoder.py
```

`pronunciation.py` owns the API response contract. `thai_nlp.py` isolates
PyThaiNLP and the G2P dependency so either can be replaced without changing
the route or frontend.

## 8. Data, privacy, and operations

- Names are personally identifiable information. Do not log request bodies or
  full API responses in production.
- Before first microphone use, explain that the browser may process audio
  through an external speech-recognition service. Do not imply that audio is
  processed locally unless the active browser explicitly guarantees it.
- The application must not record, store, log, or send raw microphone audio to
  Flask in the browser-recognition implementation.
- Do not persist names unless a future, explicit feature requires it.
- Limit request size and rate-limit the API endpoint.
- Store pronunciation overrides in source control or an access-controlled
  admin data store; include an audit trail when overrides become editable.
- Return only JSON over the API and set an explicit CORS policy if the frontend
  is hosted separately.

## 9. Acceptance criteria

1. A user can submit complete Thai given name and surname values.
2. The API returns ordered syllables, readable pronunciation, encoding forms,
   confidence, and warnings for both fields.
3. The frontend uses the API's first and last `encoding_form` values.
4. The summary always has exactly the form `XXXXXX-YY`.
5. The four first-syllable digits and two final-syllable digits of the given name,
   plus two surname vowel digits, are visibly broken
   down in the UI.
6. An uncertain or failed pronunciation cannot create an unreviewed final code.
7. Automated tests cover normal input, one-syllable input, invalid input,
   uncertain pronunciation, override pronunciation, and summary formatting.
8. In a supported browser, each microphone button updates only its associated
   field with a final `th-TH` transcript.
9. A speech transcript is editable and cannot trigger encoding without the
   user's explicit analyze action.
10. Denied permission, no speech, network failure, and unsupported-browser
    states preserve typed values and provide a Thai fallback message.
11. Only one recognition session can be active at a time, and listening state
    is communicated visually and through `aria-live`.

## 10. Out of scope for the first implementation

- Speech synthesis or audio playback.
- Server-side speech-to-text, raw-audio upload, or storing voice recordings.
- Automatic saving of patient records.
- An administrator user interface for editing overrides.
- Guaranteeing perfect pronunciation for every possible Thai personal name.

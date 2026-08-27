# Original Word + Pronunciation → Code Specification

## 1. Purpose

Convert a Thai word as written and its Thai-script pronunciation into the
clinic's numeric code. The backend analyzes the pronunciation for vowel and
final values, then cross-checks the original spelling for the initial value.
The frontend only maps those returned values to clinic code numbers; it does
not recognize or infer a vowel, initial, or final from spelling.

This resolves cases where spelling and sound differ:

```text
original word: ศรี
pronunciation: สี
code input:    initial ศ + vowel อี + no final
```

The output must explain every code digit so a user can review it.

## 2. Inputs and outputs

### Input: one word

```json
{
  "original_word": "สมศรี",
  "pronunciation": "สม-สี"
}
```

- `original_word` is the source spelling entered by the user or returned from
  Thai NLP segmentation.
- `pronunciation` is the Thai-script G2P result. Hyphens and spaces separate
  spoken syllables.
- The pronunciation must be Thai script, not IPA. IPA remains display-only.

### Output: one word

```json
{
  "original_word": "สมศรี",
  "pronunciation": "สม-สี",
  "syllables": [
    {
      "original_form": "สม",
      "pronunciation_form": "สม",
      "encoding_form": "สม",
      "initial": { "letter": "ศ", "code": "36" },
      "vowel": { "name": "โอะ", "code": 7 },
      "final": { "letter": "ม", "code": 6 }
    },
    {
      "original_form": "ศรี",
      "pronunciation_form": "สี",
      "encoding_form": "สี",
      "initial": { "letter": "ส", "code": "38" },
      "vowel": { "name": "อี", "code": 2 },
      "final": { "letter": "", "code": 0 }
    }
  ],
  "warnings": []
}
```

`encoding_form` is the exact Thai syllable sent to the browser encoder. It is
derived from the pronunciation, not copied blindly from the original spelling.

## 3. Conversion rules

### 3.1 Normalization and segmentation

1. Normalize both input values to Unicode NFC and trim whitespace.
2. Call ThaiNLP `pronunciate()` once for the complete name or surname.
3. Split the returned pronunciation on hyphens and whitespace, removing empty
   fragments.
4. Select the first and last spoken fragments. When there is one fragment, use
   it for both positions.
5. Analyze only those selected spoken syllables to obtain their initial, vowel,
   final, and final-group values.
6. Select the first and last original syllables separately and cross-check
   their initials against the spoken initials. Retain both values when they
   differ, and use the original initial for code lookup.

Example:

```text
original:      สมัคร
pronunciation: สะ-หฺมัก
spoken:        สะ / หฺมัก
```

An override may replace this with the clinic-approved encoding forms
`สะ / มัก`.

For example, `pronunciate("สมศรี")` returns `สม-สี`. The last original
syllable has initial `ศ`, while the last spoken syllable has initial `ส`. The
backend returns both values and uses original `ศ` for code lookup.

### 3.2 Backend analysis responsibilities

The backend is the sole source of the phonetic breakdown. For every selected
syllable, it must return the following values:

```json
{
  "encoding_form": "เสือ",
  "initial": "ส",
  "vowel": "เอือ",
  "final": "",
  "final_group": "แม่ ก กา",
  "original_initial": "ส",
  "pronounced_initial": "ส",
  "initial_matches_original": true,
  "initial_code_source": "original"
}
```

- `initial` is the original-spelling initial used as a key in the
  initial-letter map below.
- `vowel` is a canonical vowel name from the vowel map below.
- `final` is the canonical final sound when available.
- `final_group` is the matching Thai final-sound group and is a fallback key
  when `final` is absent.
- `original_initial`, `pronounced_initial`, and `initial_matches_original`
  preserve the original-spelling cross-check. For `ศรี → สี`, these are
  `ศ`, `ส`, and `false` respectively; the code uses `initial: ศ`.
- `initial_code_source` is always `original` for the ThaiNLP flow.

The only analysis endpoint is `/api/v1/pronunciations`. It returns every
detected syllable; the frontend uses the first and last entries to derive the
clinic code.

### 3.3 Initial-letter mapping

The frontend looks up the backend-provided `initial` directly in this map.
Letters not listed here have no clinic initial code and must be rejected for
review rather than guessed.

| Letter | Code | Letter | Code | Letter | Code | Letter | Code |
|---|---:|---|---:|---|---:|---|---:|
| ก | 01 | ข | 02 | ค | 03 | ฆ | 04 |
| ง | 05 | จ | 06 | ฉ | 07 | ช | 08 |
| ซ | 09 | ฌ | 10 | ญ | 11 | ฎ | 12 |
| ฏ | 13 | ฐ | 14 | ฑ | 15 | ฒ | 16 |
| ณ | 17 | ด | 18 | ต | 19 | ถ | 20 |
| ท | 21 | ธ | 22 | น | 23 | บ | 24 |
| ป | 25 | ผ | 26 | ฝ | 27 | พ | 28 |
| ฟ | 29 | ภ | 30 | ม | 31 | ย | 32 |
| ร | 33 | ล | 34 | ว | 35 | ศ | 36 |
| ษ | 37 | ส | 38 | ห | 39 | ฬ | 40 |
| อ | 41 | ฮ | 41 |  |  |  |  |

### 3.4 Vowel mapping

There is no frontend vowel-recognition priority. The backend returns the
canonical vowel name, and the frontend applies the applicable name or surname
map directly.

| Code | Given-name vowels | Surname vowels |
|---:|---|---|
| 0 | เอือะ, เอือ, เอียะ, เอีย, อัวะ, อัว | เอือะ, เอือ, เอียะ, เอีย, อัวะ, อัว |
| 1 | อะ, อา | อะ, อา, เอา, ไอ, อำ |
| 2 | อิ, อี | อิ, อี |
| 3 | อึ, อื | อึ, อื |
| 4 | อุ, อู | อุ, อู |
| 5 | เอะ, เอ | เอะ, เอ |
| 6 | แอะ, แอ | แอะ, แอ |
| 7 | โอะ, โอ | โอะ, โอ |
| 8 | เอาะ, ออ | เอาะ, ออ |
| 9 | เออะ, เออ | เออะ, เออ |
| 17 | ไอ | — |
| 18 | เอา | — |

`เอา` is the canonical backend value for the written vowel form `เ-า`, and
`ไอ` is the canonical backend value for `ไ-` or `ใ-`. `อำ` has no given-name
mapping, but has surname code `1`.

### 3.5 Final-sound mapping

The frontend resolves `final` first. If it is missing or unmapped, it resolves
`final_group`. Both keys must produce the same code where listed below.

| Canonical or written final | Final group | Code |
|---|---|---:|
| *(empty)* | แม่ ก กา | 0 |
| ก, ข, ค, ฆ | แม่กก | 1 |
| ด, ต, จ, ช, ซ, ฎ, ฏ, ฐ, ฑ, ฒ, ถ, ท, ธ, ศ, ษ, ส | แม่กด | 2 |
| บ, ป, พ, ฟ, ภ | แม่กบ | 3 |
| ง | แม่กง | 4 |
| น, ณ, ญ, ร, ล, ฬ | แม่กน | 5 |
| ม | แม่กม | 6 |
| ย | แม่เกย | 7 |
| ว | แม่เกอว | 8 |

## 4. Name and surname code rules

1. Use the first and last backend-selected syllables from the given name. If
   the given name has one syllable, encode it only in the first position and
   use `00` for the final-syllable position.
2. For the first given-name syllable, concatenate `initial code + given-name
   vowel code + final code` in that order. For the last given-name syllable,
   concatenate only its `vowel code + final code`; do not include its initial.
3. Use the first and last backend-selected syllables from the surname. If the
   surname has one syllable, encode its first position normally and use `0`
   for the final-syllable position.
4. For each surname syllable, use only the surname vowel code; do not append
   its initial or final code.
5. Combine the result as `given-name code-surname code`.

Most given-name vowels produce a one-digit code, so the common shape is
`XXXXXX-YY`. Given-name vowels `ไอ` (`17`) and `เอา` (`18`) are two-digit
codes, so the given-name portion is longer for names containing them. Codes
are concatenated exactly as mapped; they are not truncated or zero-padded.

The frontend must display the original and pronunciation form beside each
breakdown row whenever they differ.

## 5. Examples

### เสือดาว

```text
original:      เสือดาว
pronunciation: เสือ-ดาว

เสือ → initial ส = 38, vowel เอือ = 0, final none = 0
ดาว  → initial ด = 18, vowel อา = 1, final ว = 8
```

### สมศรี

```text
original:      สมศรี
pronunciation: สม-สี

สม → 38-7-6
สี → 38-2-0
```

The second syllable uses `สี`, not its written form `ศรี`.

### สมัคร

```text
original:      สมัคร
G2P result:    สะ-หฺมัก
override:      สะ-มัก

สะ  → 38-1-0
มัก → 31-1-1
```

### สมชาย ใจดี

```text
given name: สม / ชาย
สม   → 38 + 7 + 6 = 3876
ชาย  → 1 + 7 = 17

surname: ใจ / ดี
ใจ   → ไอ, surname code = 1
ดี   → อี, surname code = 2

summary: 387617-12
```

## 6. Warnings and manual review

Return a warning and require user review when:

- pronunciation is unavailable or is not Thai script;
- original and pronunciation syllable counts do not align;
- a pronunciation contains unsupported markers after applying an override;
- the backend cannot identify an initial, vowel, or final sound; or
- a backend-provided value has no matching clinic code.

The user may edit the selected `encoding_form` values, but the original word,
raw pronunciation, chosen form, and code trace must remain visible.

## 7. Acceptance tests

1. `เสือ` encodes as initial `38`, vowel `0`, final `0`.
2. The frontend accepts a backend syllable object and rejects raw Thai text;
   it must not perform vowel recognition.
3. `สมศรี` uses pronunciation form `สี` for the second syllable.
4. `สมัคร` uses approved override forms `สะ / มัก`.
5. Given-name `เอา` has code `18`, while surname `เอา` has code `1`.
6. Given-name `ไอ` has code `17`, while surname `ไอ` has code `1`.
7. Every output exposes original form, pronunciation form, encoding form, and
   the three code components.
8. The common full-name shape is `XXXXXX-YY`; the given-name portion grows
   by one digit for each selected `ไอ` or `เอา` vowel.

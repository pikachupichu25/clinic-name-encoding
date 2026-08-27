# PyThaiNLP Pronunciation Capabilities for the Clinic Name Encoder

## Scope of this evaluation

This document records what PyThaiNLP can and cannot provide for the clinic's
original-word + pronunciation → code workflow. It is based on the installed
project version, PyThaiNLP `5.3.7`, and direct calls to:

```python
from pythainlp.tokenize import word_tokenize, syllable_tokenize
from pythainlp.transliterate import pronunciate
```

PyThaiNLP documents `syllable_tokenize` as a Thai syllable segmenter and
`pronunciate(..., engine="w2p")` as a word-to-phoneme function that returns a
Thai-letter pronunciation string. [Syllable tokenizer documentation](https://pythainlp.org/docs/5.3.4/api/tokenize.html)
[Pronunciation documentation](https://pythainlp.org/dev-docs/api/transliterate.html)

## What it can do

### 1. Split a written word into spelling syllables

`syllable_tokenize()` returns a list of Thai syllable-like spelling units. It
is useful for displaying the original spelling and for a fallback when G2P is
unavailable.

```python
syllable_tokenize("เสือดาว")  # ["เสือ", "ดาว"]
syllable_tokenize("สมศรี")    # ["สม", "ศรี"]
```

### 2. Produce a Thai-script pronunciation for a complete word

`pronunciate()` uses the `w2p` engine and returns a phonetic Thai spelling;
hyphens mark spoken-syllable boundaries.

```python
pronunciate("เสือดาว")  # "เสือ-ดาว"
pronunciate("สมศรี")    # "สม-สี"
pronunciate("สามารถ")  # "สา-มาด"
```

This is the most useful PyThaiNLP output for this project because it can
correct spelling-driven pronunciation differences, such as `ศรี → สี` and
`มารถ → มาด`.

### 3. Expose spoken syllables not visible in written segmentation

G2P can produce more spoken syllables than `syllable_tokenize()` returns.

```python
syllable_tokenize("ภาพยนตร์")  # ["ภาพ", "ยนตร์"]
pronunciate("ภาพยนตร์")        # "พาบ-พะ-ยน"
```

For code generation, this means full-word `pronunciate()` must run **before**
selecting the first and last spoken syllable. Running G2P separately on the
written segments loses context:

```text
pronunciate("ยนตร์")    → ยน
pronunciate("ภาพยนตร์") → พาบ-พะ-ยน
```

## Measured results for this project

| Original word | `word_tokenize` | `syllable_tokenize` | `pronunciate` |
|---|---|---|---|
| เสือดาว | เสือดาว | เสือ / ดาว | เสือ-ดาว |
| สมศรี | สม / ศรี | สม / ศรี | สม-สี |
| สมัคร | สมัคร | สมัคร | สะ-หฺมัก |
| สามารถ | สามารถ | สา / มารถ | สา-มาด |
| ภาพยนตร์ | ภาพยนตร์ | ภาพ / ยนตร์ | พาบ-พะ-ยน |
| กอวิด | กอ / วิด | กอ / วิด | กอ-วิด |

## What it does not do

### It does not return vowel categories or numeric code components

The G2P result is a Thai spelling string, not structured phonetic data. It
does not report the initial sound, vowel class, coda, tone, confidence, or the
clinic's code.

For example, PyThaiNLP returns `สม` for the spoken first syllable of `สมศรี`.
It does **not** say that this syllable has the vowel `โอะ`. The clinic encoder
must infer that vowel from a dedicated phonological rule or a pronunciation
lexicon. A simple “visible vowel mark” parser will incorrectly classify it as
`อะ`.

### It does not guarantee personal-name pronunciation

The model is designed for Thai words, not a verified registry of Thai personal
names. Unusual names, loanwords, family-specific pronunciations, and
Pali/Sanskrit spellings can be wrong or ambiguous.

`สมัคร` demonstrates the issue:

```text
syllable_tokenize → สมัคร
pronunciate       → สะ-หฺมัก
```

The result is useful—it exposes two spoken parts—but `หฺมัก` is not yet the
clinic-ready form `มัก`. It needs a configurable normalization rule or a
name-specific override.

### It does not align original spelling syllables with G2P syllables

When the number of written and spoken syllables differs, the library provides
no source-to-pronunciation alignment. The application must preserve both lists
for audit and allow review rather than assume a one-to-one correspondence.

### It does not provide confidence scores or alternatives

`pronunciate()` returns one string. It does not report confidence, candidate
pronunciations, or whether a dictionary rule versus a model rule produced the
answer. Application-level warnings and overrides are required.

## Required project pipeline

```text
original full name
        │
        ├── keep for display, audit, and override lookup
        │
        ▼
PyThaiNLP pronunciate(full name)
        │
        ▼
Thai-script G2P string with hyphen-separated spoken syllables
        │
        ├── normalize approved patterns / name overrides
        ├── select first and last spoken syllable
        ├── infer initial, vowel, and final with clinic rules
        ▼
clinic numeric encoder
```

`syllable_tokenize()` should be supplementary: use it to show original spelling
segments and to assist manual review, not as the source of final spoken
syllables.

## Encoder work still required

PyThaiNLP provides pronunciation text; the clinic still needs a separate,
tested phonological encoder with these features:

1. A pronunciation normalizer for G2P notation, including hyphens and the
   phinthu mark (`ฺ`).
2. A vowel engine that recognizes compound and implicit vowels:
   - `เสือ → เอือ`
   - `สม → โอะ`
   - `สี → อี`
3. A configurable sound-to-canonical-letter map, for example `ศ/ษ/ซ → ส`
   when the clinic encodes the `/s/` sound as `ส`.
4. A final-sound map based on pronunciation, not written spelling.
5. A reviewed override dictionary for exceptional names, including `สมัคร`.
6. A review UI whenever the normalized G2P form cannot be parsed safely.

## Dependencies used by this project

```sh
.venv/bin/pip install -r requirements.txt
.venv/bin/thainlp data get thai_w2p_npz
```

The project requirements install PyThaiNLP, `python-crfsuite` for syllable
segmentation support, and NumPy for the downloaded W2P model.

## Recommendation

Use PyThaiNLP as the **pronunciation and spoken-syllable source**, but do not
use it as the numeric encoder. Build and validate a clinic-owned
pronunciation-to-code layer on top of its full-word G2P output, with explicit
rules and human-review overrides for irregular names.

# Candidate One-Syllable Thai Test Set

The machine-readable fixture is
[`data/thai_one_syllable_test_candidates.json`](data/thai_one_syllable_test_candidates.json).
It is intentionally marked `candidate_needs_native_review`; expected linguistic
labels should be approved before these cases become hard pass/fail tests.

## Coverage

The set contains one-spoken-syllable words covering:

- compound vowels: `เรียน`, `เสือ`, `เปียก`, `เลือด`, `สวน`, `กลัว`;
- reduced or changed vowel forms: `สม`, `คน`, `นก`, `รถ`, `เดิน`, `แข็ง`;
- silent letters and changed final sounds: `จันทร์`, `ศุกร์`, `พิมพ์`, `เลข`,
  `เมฆ`, `พรรค`, `พันธ์`, `มิตร`;
- special initial behavior: `ทราบ`, `ทราย`, `หนู`, `หมอ`, `หวาน`, `อยู่`;
- exceptional spelling: `จริง`, `ฤทธิ์`, `กรรม`, `สรร`, `ธรรม`, `พร`;
- unsupported clinic-table cases: `ลาภ`/`ทราบ` (แม่กบ), and
  `กรรม`/`น้ำ`/`ธรรม`/`ไทย` (อำ or ไอ).

## Important findings

PyThaiNLP's `spell_syllable()` is useful for visible compound vowels:

```python
spell_syllable("เรียน")  # ['รอ', 'นอ', 'เอีย', 'เรียน']
spell_syllable("เสือ")   # ['สอ', 'เอือ', 'เสือ']
```

It does not identify fully reduced vowels:

```python
spell_syllable("สม")     # ['สอ', 'มอ', 'สม']
```

The expected test label therefore supplies `โอะ` explicitly.

The fixture also records observed PyThaiNLP W2P failures instead of hiding
them. In the installed version, examples include:

```text
สวน → สะ-วะ-นะ   (expected one syllable สวน)
กลัว → กล-หฺวัว   (expected one syllable กลัว)
ทราย → ทราย      (expected pronunciation ซาย)
สรร → สอน        (expected pronunciation สัน)
```

## Fields

- `initial`: the sound-bearing consonant used for `INITIAL_CODES`; silent
  leading ห or อ is skipped, while a pronounced written letter such as ศ is
  preserved;
- `onset`: the full written onset when the spelling contains a cluster or
  leading consonant;
- `pronounced_initial`: included only when the spoken onset differs from the
  written initial, such as `ศุกร์` (`ศ` written, `ส` pronounced);
- `silent_leading_consonant`: a written tone-class leader excluded from the
  coded initial, such as `ห` in `หนู`;
- `vowel`: the canonical Thai vowel, including reduced vowels;
- `final`: the canonical pronounced final consonant;
- `final_group`: แม่ตัวสะกด, or `แม่ ก กา` for no final;
- `vowel_code` and `final_code`: current clinic mapping, with `null` exposing a
  missing mapping;
- `pythainlp_pronunciation`: direct installed W2P output for regression checks.

## Promotion process

1. A Thai-language reviewer approves or edits each expected analysis.
2. Change the fixture status to `approved`.
3. Convert each approved entry into an automated encoder test.
4. Keep incorrect PyThaiNLP outputs as regression inputs for the normalization
   and override layer.

The reduced `โอะ` rule is supported by Thai teaching material explaining that
the written `โ-ะ` disappears before a final consonant, leaving only the initial
and final. See [DLTV's lesson on reduced โอะ](https://dltv.ac.th/teachplan/episode/65346).

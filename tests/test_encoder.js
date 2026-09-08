const assert = require("node:assert/strict");
const fs = require("node:fs");

const html = fs.readFileSync("index.html", "utf8");
const script = html.match(/<script>([\s\S]*)<\/script>/)[1];
const elements = new Map();

assert.match(html, /<input type="radio" name="provider" value="pythainlp" checked/);
assert.match(script, /provider: selectedProvider\(\)/);

global.document = {
  getElementById(id) {
    if (!elements.has(id)) {
      elements.set(id, { style: {}, addEventListener() {} });
    }
    return elements.get(id);
  }
};

eval(`${script}
globalThis.encodeSyllableForTest = encodeSyllable;
globalThis.encodeGivenLastSyllableForTest = encodedGivenLastSyllable;
globalThis.encodeSurnameLastSyllableForTest = encodedSurnameLastSyllable;
globalThis.syllablePillsForTest = syllablePills;
globalThis.givenNameSummaryUnitsForTest = givenNameSummaryUnits;
globalThis.surnameVowelCodesForTest = SURNAME_VOWEL_CODES;
globalThis.requestJsonForTest = requestJson;
globalThis.initialOptionsForTest = INITIAL_OPTIONS;
globalThis.finalOptionsForTest = FINAL_OPTIONS;
globalThis.vowelOptionsForTest = vowelOptions;
globalThis.initAnalysisStateForTest = initAnalysisState;
globalThis.resolvedSyllableForTest = resolvedSyllable;
globalThis.defaultIndexForTest = defaultIndex;
globalThis.hasAnyCorrectionForTest = hasAnyCorrection;
globalThis.setCorrectionIndexForTest = (position, index) => { analysisState.positions[position].index = index; };
globalThis.setCorrectionOverrideForTest = (position, field, value) => { analysisState.positions[position].overrides[field] = value; };`);

const encode = globalThis.encodeSyllableForTest;
const encodeGivenLastSyllable = globalThis.encodeGivenLastSyllableForTest;
const encodeSurnameLastSyllable = globalThis.encodeSurnameLastSyllableForTest;
const getSyllablePills = globalThis.syllablePillsForTest;
const getGivenNameSummaryUnits = globalThis.givenNameSummaryUnitsForTest;
const surnameVowelCodes = globalThis.surnameVowelCodesForTest;
const syllable = (encoding_form, initial, vowel, final = "", final_group) => ({
  encoding_form, initial, vowel, final, final_group
});

assert.deepEqual(encode(syllable("เสือ", "ส", "เอือ")).code, { initial: "38", vowel: 0, final: 0 });
assert.deepEqual(encode(syllable("สา", "ส", "อา")).code, { initial: "38", vowel: 1, final: 0 });
assert.equal(encode(syllable("เกา", "ก", "เอา")).code.vowel, 18);
assert.equal(encode(syllable("ไก", "ก", "ไอ")).code.vowel, 17);
assert.equal(encode({ encoding_form: "เอา", initial: "อ", vowel: "เอา", final: "" }, surnameVowelCodes).code.vowel, 1);
assert.equal(encode({ encoding_form: "ใจ", initial: "จ", vowel: "ไอ", final: "" }, surnameVowelCodes).code.vowel, 1);
assert.equal(encode({ encoding_form: "น้ำ", initial: "น", vowel: "อำ", final: "ม" }, surnameVowelCodes).code.vowel, 1);
assert.deepEqual(
  encode({ encoding_form: "สม", initial: "ส", vowel: "โอะ", final: "ม" }).code,
  { initial: "38", vowel: 7, final: 6 }
);
const encodedLastGiven = encode(syllable("ชาย", "ช", "อา", "ย"));
assert.deepEqual(
  encodeGivenLastSyllable(syllable("สม", "ส", "โอะ", "ม"), true).code,
  { initial: "38", vowel: 0, final: 0 },
  "a one-syllable given name reserves its final two positions for 00"
);
assert.deepEqual(
  encodeGivenLastSyllable(syllable("ชาย", "ช", "อา", "ย"), false).code,
  { initial: "08", vowel: 1, final: 7 }
);
assert.equal(
  encodeSurnameLastSyllable(syllable("ใจ", "จ", "ไอ"), true).code.vowel,
  0,
  "a one-syllable surname reserves its final position for 0"
);
assert.equal(
  encodeSurnameLastSyllable(syllable("ดี", "ด", "อี"), false).code.vowel,
  2
);
assert.deepEqual(
  getSyllablePills(encodedLastGiven, { includeInitial: false }),
  [
    { field: "vowel", value: 1, label: "อา", edited: false },
    { field: "final", value: 7, label: "ย", edited: false }
  ]
);
assert.deepEqual(
  getGivenNameSummaryUnits(encode(syllable("สม", "ส", "โอะ", "ม")), encodedLastGiven),
  [["38", "ส"], [7, "โอะ"], [6, "ม"], [1, "อา"], [7, "ย"]]
);
assert.deepEqual(
  getGivenNameSummaryUnits(
    encode(syllable("สม", "ส", "โอะ", "ม")),
    encodeGivenLastSyllable(syllable("สม", "ส", "โอะ", "ม"), true),
    true
  ),
  [["38", "ส"], [7, "โอะ"], [6, "ม"], [0, ""], [0, ""]],
  "a one-syllable given name leaves the two final-syllable breakdowns blank"
);
assert.throws(() => encode("เสือ"), /ข้อมูลพยางค์จากระบบวิเคราะห์/);

// A syllable ThaiNLP produced but whose letter has no clinic code must not
// crash the render — it should come back reviewable instead of thrown away.
const unmappable = encode(syllable("๐", "๐", "โอะ", ""));
assert.deepEqual(unmappable.missing, ["initial"]);
assert.equal(unmappable.code.initial, null);
assert.deepEqual(encode(syllable("กอ", "ก", "ออ")).missing, []);

// --- Manual-correction state --------------------------------------------
const initialOptions = globalThis.initialOptionsForTest;
const finalOptions = globalThis.finalOptionsForTest;
const getVowelOptions = globalThis.vowelOptionsForTest;
assert.ok(initialOptions.find(option => option.value === "ก" && option.code === "01"));
assert.ok(initialOptions.find(option => option.value === "ฮ" && option.code === "41"));
assert.deepEqual(finalOptions.map(option => option.code), [0, 1, 2, 3, 4, 5, 6, 7, 8]);
assert.equal(getVowelOptions(surnameVowelCodes).find(option => option.value === "อำ").code, 1);

const sampleAnalysisBody = {
  given_name: {
    syllables: [
      { encoding_form: "สม", initial: "ส", vowel: "โอะ", final: "ม", final_group: "แม่กม", pronunciation: "som" },
      { encoding_form: "ชาย", initial: "ช", vowel: "อา", final: "ย", final_group: "แม่เกย", pronunciation: "chai" },
      { encoding_form: "ไช", initial: "ช", vowel: "ไอ", final: "", final_group: "แม่ ก กา", pronunciation: "chai" }
    ],
    first_syllable_index: 0,
    last_syllable_index: 1,
    warnings: []
  },
  surname: {
    syllables: [
      { encoding_form: "ใจ", initial: "จ", vowel: "ไอ", final: "", final_group: "แม่ ก กา", pronunciation: "jai" },
      { encoding_form: "ดี", initial: "ด", vowel: "อี", final: "", final_group: "แม่ ก กา", pronunciation: "dee" }
    ],
    first_syllable_index: 0,
    last_syllable_index: 1,
    warnings: []
  }
};

globalThis.initAnalysisStateForTest(sampleAnalysisBody);
assert.equal(globalThis.hasAnyCorrectionForTest(), false, "a freshly loaded analysis has no corrections yet");

const baseGivenLast = globalThis.resolvedSyllableForTest("givenLast");
assert.equal(baseGivenLast.text, "ชาย");
assert.equal(baseGivenLast.edited.syllable, false);

globalThis.setCorrectionIndexForTest("givenLast", 2);
const swappedGivenLast = globalThis.resolvedSyllableForTest("givenLast");
assert.equal(swappedGivenLast.text, "ไช", "picking another ThaiNLP-provided syllable changes the resolved syllable");
assert.equal(swappedGivenLast.edited.syllable, true);
assert.equal(globalThis.hasAnyCorrectionForTest(), true);

globalThis.setCorrectionIndexForTest("givenLast", globalThis.defaultIndexForTest("givenLast"));
assert.equal(globalThis.hasAnyCorrectionForTest(), false, "restoring ThaiNLP's own index clears the correction flag");

globalThis.setCorrectionOverrideForTest("givenFirst", "final", "");
const correctedGivenFirst = globalThis.resolvedSyllableForTest("givenFirst");
assert.equal(correctedGivenFirst.final, "", "a manual final override replaces the ThaiNLP-detected final");
assert.equal(correctedGivenFirst.edited.final, true);
assert.equal(correctedGivenFirst.edited.initial, false, "fields the user has not touched still fall back to ThaiNLP's value");
assert.equal(correctedGivenFirst.initial, "ส");
assert.equal(encode(correctedGivenFirst).code.final, 0);
assert.equal(globalThis.hasAnyCorrectionForTest(), true);

async function testJsonResponseHandling() {
  global.fetch = async () => ({
    ok: false,
    status: 404,
    headers: { get: () => "text/html; charset=utf-8" },
    text: async () => "<!doctype html><title>Not found</title>"
  });
  await assert.rejects(
    () => globalThis.requestJsonForTest("/missing", {}),
    /เซิร์ฟเวอร์ส่งหน้าเว็บกลับมาแทนข้อมูล API/
  );

  global.fetch = async () => ({
    ok: false,
    status: 400,
    headers: { get: () => "application/json" },
    text: async () => JSON.stringify({ error: { message: "ชื่อไม่ถูกต้อง" } })
  });
  await assert.rejects(
    () => globalThis.requestJsonForTest("/api/v1/pronunciations", {}),
    /ชื่อไม่ถูกต้อง/
  );
}

testJsonResponseHandling()
  .then(() => console.log("Frontend encoder and API response handling cases passed."))
  .catch(error => {
    console.error(error);
    process.exitCode = 1;
  });

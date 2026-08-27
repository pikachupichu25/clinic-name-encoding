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

eval(`${script}\nglobalThis.encodeSyllableForTest = encodeSyllable;\nglobalThis.encodeGivenLastSyllableForTest = encodedGivenLastSyllable;\nglobalThis.encodeSurnameLastSyllableForTest = encodedSurnameLastSyllable;\nglobalThis.syllableCodeHtmlForTest = syllableCodeHtml;\nglobalThis.givenNameSummaryUnitsForTest = givenNameSummaryUnits;\nglobalThis.surnameVowelCodesForTest = SURNAME_VOWEL_CODES;\nglobalThis.requestJsonForTest = requestJson;`);

const encode = globalThis.encodeSyllableForTest;
const encodeGivenLastSyllable = globalThis.encodeGivenLastSyllableForTest;
const encodeSurnameLastSyllable = globalThis.encodeSurnameLastSyllableForTest;
const formatSyllableCode = globalThis.syllableCodeHtmlForTest;
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
assert.equal(
  formatSyllableCode(encodedLastGiven, { includeInitial: false }),
  '<span class="code">1</span><span class="dot">•</span><span class="code">7</span>'
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

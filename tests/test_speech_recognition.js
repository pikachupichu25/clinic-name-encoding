const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

class FakeElement {
  constructor() {
    this.style = {};
    this.dataset = {};
    this.attributes = {};
    this.children = [];
    this.listeners = {};
    this.hidden = false;
    this.disabled = false;
    this.textContent = "";
    this.value = "";
  }

  addEventListener(type, listener) { this.listeners[type] = listener; }
  click() { this.listeners.click?.({}); }
  setAttribute(name, value) { this.attributes[name] = String(value); }
  append(...children) { this.children.push(...children); }
  appendChild(child) { this.children.push(child); }
  focus() { this.focused = true; }
}

const elements = new Map();
global.document = {
  getElementById(id) {
    if (!elements.has(id)) elements.set(id, new FakeElement());
    return elements.get(id);
  },
  createElement() { return new FakeElement(); }
};

class FakeRecognition {
  static instances = [];

  constructor() { FakeRecognition.instances.push(this); }
  start() { this.started = true; }
  stop() { this.stopped = true; }
}

global.window = { webkitSpeechRecognition: FakeRecognition };
let fetchCalls = 0;
global.fetch = () => { fetchCalls += 1; };
const html = fs.readFileSync("index.html", "utf8");
const script = html.match(/<script>([\s\S]*)<\/script>/)[1];
eval(script);

const givenButton = elements.get("givenSpeechButton");
const surnameButton = elements.get("surnameSpeechButton");
const givenInput = elements.get("givenName");
const surnameInput = elements.get("surname");
const status = elements.get("speechStatus");

givenButton.click();
const givenRecognition = FakeRecognition.instances[0];
assert.equal(givenRecognition.lang, "th-TH");
assert.equal(givenRecognition.continuous, false);
assert.equal(givenRecognition.interimResults, true);
assert.equal(givenRecognition.maxAlternatives, 3);
givenRecognition.onstart();
assert.match(status.textContent, /กำลังฟัง/);

const interim = Object.assign([{ transcript: "สม" }], { isFinal: false });
givenRecognition.onresult({ resultIndex: 0, results: [interim] });
assert.equal(givenInput.value, "", "interim speech must not overwrite the typed value");
assert.match(elements.get("givenSpeechPreview").textContent, /สม/);

const finalResult = Object.assign([
  { transcript: "สมชาย" },
  { transcript: "สมชัย" },
  { transcript: "สมชาญ" }
], { isFinal: true });
surnameInput.value = "ใจดี";
givenRecognition.onresult({ resultIndex: 0, results: [finalResult] });
assert.equal(givenInput.value, "สมชาย");
assert.equal(surnameInput.value, "ใจดี", "speech must not change the other field");
assert.equal(fetchCalls, 0, "a speech result must not start encoding");
const alternativeButtons = elements.get("givenSpeechReview").children[1].children;
assert.equal(alternativeButtons.length, 3);
alternativeButtons[1].click();
assert.equal(givenInput.value, "สมชัย", "an alternative transcript is selectable");

surnameButton.click();
assert.equal(givenRecognition.stopped, true, "starting the other field stops the current session");
givenRecognition.onend();
const surnameRecognition = FakeRecognition.instances[1];
assert.ok(surnameRecognition, "only a fresh, queued surname session starts after the first ends");
surnameRecognition.onstart();
surnameInput.value = "เดิม";
surnameRecognition.onerror({ error: "network" });
surnameRecognition.onend();
assert.equal(surnameInput.value, "เดิม", "recognition errors preserve the typed value");
assert.match(status.textContent, /เชื่อมต่อบริการรู้จำเสียงไม่ได้/);

const unsupportedElements = new Map();
const unsupportedDocument = {
  getElementById(id) {
    if (!unsupportedElements.has(id)) unsupportedElements.set(id, new FakeElement());
    return unsupportedElements.get(id);
  },
  createElement() { return new FakeElement(); }
};
vm.runInNewContext(script, { document: unsupportedDocument, window: {}, console });
assert.equal(unsupportedElements.get("givenSpeechButton").hidden, true);
assert.equal(unsupportedElements.get("surnameSpeechButton").hidden, true);
assert.match(unsupportedElements.get("speechStatus").textContent, /ไม่รองรับ/);

console.log("Frontend speech-recognition UI cases passed.");

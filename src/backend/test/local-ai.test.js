import test from "node:test";
import assert from "node:assert/strict";
import { LocalAiService, parseModelJson } from "../src/services/local-ai.js";

const options = {
  url: "http://local-ollama.test",
  textModel: "granite4:3b",
  visionModel: "granite3.2-vision:2b",
  timeoutMs: 1_000,
};

test("parses plain and fenced model JSON", () => {
  assert.deepEqual(parseModelJson('{"upperColor":"blue"}'), { upperColor: "blue" });
  assert.deepEqual(parseModelJson('```json\n{"upperColor":"blue"}\n```'), { upperColor: "blue" });
});

test("reports installed local models", async () => {
  const fakeFetch = async () => new Response(JSON.stringify({
    models: [{ name: "granite4:3b" }, { name: "granite3.2-vision:2b" }],
  }), { status: 200, headers: { "content-type": "application/json" } });
  const status = await new LocalAiService(options, fakeFetch).status();
  assert.equal(status.reachable, true);
  assert.equal(status.models.text.installed, true);
  assert.equal(status.models.vision.installed, true);
});

test("returns an offline status instead of crashing", async () => {
  const fakeFetch = async () => { throw new Error("connection refused"); };
  const status = await new LocalAiService(options, fakeFetch).status();
  assert.equal(status.reachable, false);
  assert.match(status.message, /connection refused/);
});

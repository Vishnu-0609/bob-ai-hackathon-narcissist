import test from "node:test";
import assert from "node:assert/strict";
import { compareRecords, rankCandidates, textSimilarity } from "../src/domain/scoring.js";
import { seedData } from "../src/data/seed.js";

test("normalizes common clothing and accessory synonyms", () => {
  assert.equal(textSimilarity("navy tee", "blue t-shirt"), 1);
  assert.equal(textSimilarity("black wrist watch", "black watch"), 1);
});

test("does not penalize a missing height observation", () => {
  const result = compareRecords(seedData.anteMortem[0], seedData.postMortem[0]);
  const height = result.evidence.find((item) => item.key === "height");
  assert.equal(height.result, "unknown");
  assert.ok(result.score >= 80);
});

test("ranks the strongly matching candidate first", () => {
  const results = rankCandidates(seedData.anteMortem, seedData.postMortem[0]);
  assert.equal(results[0].anteMortemId, "MP-023");
  assert.equal(results[0].rank, 1);
  assert.match(results[0].disclaimer, /forensic confirmation/i);
});

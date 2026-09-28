import test from "node:test";
import assert from "node:assert/strict";
import { RecordsService } from "../src/services/records.js";

test("creates a review-required post-mortem record from image characteristics", async () => {
  const stored = [];
  const repository = {
    list(collection) { return collection === "postMortem" ? stored : []; },
    async create(_collection, record) { stored.push(record); return record; },
  };
  const service = new RecordsService(repository);
  const extraction = {
    upperType: "t-shirt", upperColor: "blue", lowerType: "jeans", lowerColor: "black",
    visibleMarks: "scar on left forearm", accessories: "black wristwatch",
    textOnClothing: "rescue team", otherDescription: "red backpack", warnings: ["low light"],
  };

  const result = await service.createPostMortemFromExtraction({ incidentRef: "INC-TEST-1" }, extraction);

  assert.equal(result.record.incidentRef, "INC-TEST-1");
  assert.equal(result.record.extractionStatus, "ai-extracted-pending-review");
  assert.match(result.record.otherDescription, /rescue team/);
  assert.deepEqual(result.extraction.warnings, ["low light"]);
});

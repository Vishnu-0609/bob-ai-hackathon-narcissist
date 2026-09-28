import { ApiError } from "../lib/http.js";
import { rankCandidates } from "../domain/scoring.js";
import { validateAnteMortem, validatePostMortem } from "../lib/validation.js";

export class RecordsService {
  constructor(repository) {
    this.repository = repository;
  }

  dashboard() {
    const ante = this.repository.list("anteMortem");
    const post = this.repository.list("postMortem");
    const reviews = this.repository.list("reviews");
    return {
      totals: {
        missingPersons: ante.length,
        unidentifiedPersons: post.length,
        pendingReview: post.filter((record) => record.status === "unidentified").length,
        reconciled: reviews.filter((review) => review.status === "confirmed-externally").length,
      },
      recentActivity: [...ante, ...post].sort((a, b) => b.updatedAt.localeCompare(a.updatedAt)).slice(0, 5),
    };
  }

  listAnteMortem() { return this.repository.list("anteMortem"); }
  listPostMortem() { return this.repository.list("postMortem"); }

  async createAnteMortem(input) {
    const normalized = validateAnteMortem(input);
    return this.repository.create("anteMortem", withMetadata(normalized, nextId("MP", this.listAnteMortem())));
  }

  async createPostMortem(input) {
    const normalized = validatePostMortem(input);
    return this.repository.create("postMortem", {
      ...withMetadata(normalized, nextId("PM", this.listPostMortem())),
      extractionStatus: input.extractionStatus || "manual",
    });
  }

  async createPostMortemFromExtraction(input, extraction) {
    const readableText = extraction.textOnClothing
      ? `visible clothing text: ${extraction.textOnClothing}`
      : "";
    const otherDescription = [extraction.otherDescription, readableText]
      .filter(Boolean)
      .join("; ");
    const record = await this.createPostMortem({
      incidentRef: input.incidentRef,
      estimatedHeightCm: input.estimatedHeightCm,
      dentalNotes: input.dentalNotes,
      upperType: extraction.upperType,
      upperColor: extraction.upperColor,
      lowerType: extraction.lowerType,
      lowerColor: extraction.lowerColor,
      visibleMarks: extraction.visibleMarks,
      accessories: extraction.accessories,
      otherDescription,
      extractionStatus: "ai-extracted-pending-review",
    });
    return { record, extraction };
  }

  matches(postMortemId, limit = 3) {
    const post = this.repository.find("postMortem", postMortemId);
    if (!post) throw new ApiError(404, "RECORD_NOT_FOUND", `Post-mortem record ${postMortemId} was not found.`);
    return { postMortem: post, matches: rankCandidates(this.listAnteMortem(), post, limit) };
  }
}

function nextId(prefix, records) {
  const maximum = records.reduce((max, record) => Math.max(max, Number(record.id?.split("-")[1]) || 0), 0);
  return `${prefix}-${String(maximum + 1).padStart(3, "0")}`;
}

function withMetadata(record, id) {
  const now = new Date().toISOString();
  return { id, ...record, createdAt: now, updatedAt: now };
}

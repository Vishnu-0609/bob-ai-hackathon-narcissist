const WEIGHTS = Object.freeze({
  dental: 30,
  marks: 25,
  clothing: 15,
  accessories: 10,
  height: 10,
  other: 10,
});

const SYNONYMS = new Map([
  ["tee", "t-shirt"],
  ["t shirt", "t-shirt"],
  ["tshirt", "t-shirt"],
  ["wrist watch", "wristwatch"],
  ["watch", "wristwatch"],
  ["navy", "blue"],
  ["denim", "jeans"],
]);

function normalize(value) {
  let result = String(value || "").toLowerCase().replace(/[^a-z0-9\s-]/g, " ").replace(/\s+/g, " ").trim();
  for (const [from, to] of SYNONYMS) {
    const escaped = from.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    result = result.replace(new RegExp(`\\b${escaped}\\b`, "g"), to);
  }
  return result;
}

function tokens(value) {
  return new Set(normalize(value).split(" ").filter(Boolean));
}

export function textSimilarity(left, right) {
  const a = tokens(left);
  const b = tokens(right);
  if (!a.size || !b.size) return null;
  const intersection = [...a].filter((item) => b.has(item)).length;
  const union = new Set([...a, ...b]).size;
  return intersection / union;
}

function exactSimilarity(left, right) {
  const a = normalize(left);
  const b = normalize(right);
  if (!a || !b) return null;
  return a === b ? 1 : textSimilarity(a, b);
}

function heightSimilarity(left, right) {
  if (left == null || right == null) return null;
  const difference = Math.abs(Number(left) - Number(right));
  if (difference <= 2) return 1;
  if (difference <= 5) return 0.75;
  if (difference <= 10) return 0.35;
  return 0;
}

function combine(values) {
  const available = values.filter((value) => value != null);
  return available.length ? available.reduce((sum, value) => sum + value, 0) / available.length : null;
}

function resultLabel(value) {
  if (value == null) return "unknown";
  if (value >= 0.8) return "concordant";
  if (value >= 0.35) return "partial";
  return "contradictory";
}

export function compareRecords(ante, post) {
  const categories = [
    evidence("dental", "Dental observations", ante.dentalNotes, post.dentalNotes, textSimilarity),
    evidence("marks", "Distinguishing marks", ante.visibleMarks, post.visibleMarks, textSimilarity),
    {
      key: "clothing",
      label: "Clothing",
      anteValue: [ante.upperColor, ante.upperType, ante.lowerColor, ante.lowerType].filter(Boolean).join(" / "),
      postValue: [post.upperColor, post.upperType, post.lowerColor, post.lowerType].filter(Boolean).join(" / "),
      similarity: combine([
        exactSimilarity(ante.upperType, post.upperType),
        exactSimilarity(ante.upperColor, post.upperColor),
        exactSimilarity(ante.lowerType, post.lowerType),
        exactSimilarity(ante.lowerColor, post.lowerColor),
      ]),
    },
    evidence("accessories", "Accessories", ante.accessories, post.accessories, textSimilarity),
    {
      key: "height",
      label: "Height",
      anteValue: ante.heightCm == null ? "" : `${ante.heightCm} cm`,
      postValue: post.estimatedHeightCm == null ? "" : `${post.estimatedHeightCm} cm`,
      similarity: heightSimilarity(ante.heightCm, post.estimatedHeightCm),
    },
    evidence("other", "Other description", ante.otherDescription, post.otherDescription, textSimilarity),
  ].map((item) => ({ ...item, result: resultLabel(item.similarity), weight: WEIGHTS[item.key] }));

  const available = categories.filter((item) => item.similarity != null);
  const weightTotal = available.reduce((sum, item) => sum + item.weight, 0);
  const rawScore = weightTotal
    ? available.reduce((sum, item) => sum + item.similarity * item.weight, 0) / weightTotal
    : 0;
  const contradictions = categories.filter((item) => item.result === "contradictory").length;
  const score = Math.max(0, Math.round(rawScore * 100 - contradictions * 5));

  return {
    anteMortemId: ante.id,
    postMortemId: post.id,
    score,
    classification: score >= 75 ? "high" : score >= 50 ? "moderate" : "low",
    evidenceCoverage: Math.round(weightTotal),
    evidence: categories,
    rationale: buildRationale(ante, categories, score),
    disclaimer: "Candidate match only — requires forensic confirmation.",
  };
}

function evidence(key, label, anteValue, postValue, comparator) {
  return { key, label, anteValue: anteValue || "", postValue: postValue || "", similarity: comparator(anteValue, postValue) };
}

function buildRationale(ante, categories, score) {
  const matches = categories.filter((item) => item.result === "concordant").map((item) => item.label.toLowerCase());
  const conflicts = categories.filter((item) => item.result === "contradictory").map((item) => item.label.toLowerCase());
  const unknown = categories.filter((item) => item.result === "unknown").map((item) => item.label.toLowerCase());
  const parts = [`${ante.id} received a ${score}/100 match score.`];
  if (matches.length) parts.push(`Strong agreement was found in ${joinList(matches)}.`);
  if (conflicts.length) parts.push(`Conflicting evidence was found in ${joinList(conflicts)}.`);
  if (unknown.length) parts.push(`${joinList(unknown)} did not contribute because comparable evidence was unavailable.`);
  return parts.join(" ");
}

function joinList(items) {
  if (items.length < 2) return items[0] || "";
  return `${items.slice(0, -1).join(", ")} and ${items.at(-1)}`;
}

export function rankCandidates(anteRecords, postRecord, limit = 3) {
  return anteRecords
    .map((ante) => ({ ...compareRecords(ante, postRecord), candidate: ante }))
    .sort((a, b) => b.score - a.score)
    .slice(0, limit)
    .map((match, index) => ({ rank: index + 1, ...match }));
}

export { WEIGHTS };

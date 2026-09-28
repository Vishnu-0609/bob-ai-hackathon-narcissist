import { ApiError } from "./http.js";

const text = (value) => typeof value === "string" ? value.trim() : "";

export function validateAnteMortem(input) {
  const errors = [];
  const fullName = text(input.fullName);
  if (!fullName) errors.push({ field: "fullName", message: "Full name is required." });

  const age = input.age === "" || input.age == null ? null : Number(input.age);
  if (age != null && (!Number.isFinite(age) || age < 0 || age > 130)) {
    errors.push({ field: "age", message: "Age must be between 0 and 130." });
  }

  const heightCm = input.heightCm === "" || input.heightCm == null ? null : Number(input.heightCm);
  if (heightCm != null && (!Number.isFinite(heightCm) || heightCm < 30 || heightCm > 250)) {
    errors.push({ field: "heightCm", message: "Height must be between 30 and 250 cm." });
  }

  if (errors.length) throw new ApiError(422, "VALIDATION_FAILED", "Record validation failed.", errors);

  return normalizeRecord(input, {
    fullName,
    age,
    heightCm,
    status: "missing",
  });
}

export function validatePostMortem(input) {
  const errors = [];
  const incidentRef = text(input.incidentRef);
  if (!incidentRef) errors.push({ field: "incidentRef", message: "Incident reference is required." });

  const estimatedHeightCm = input.estimatedHeightCm === "" || input.estimatedHeightCm == null
    ? null
    : Number(input.estimatedHeightCm);
  if (estimatedHeightCm != null && (!Number.isFinite(estimatedHeightCm) || estimatedHeightCm < 30 || estimatedHeightCm > 250)) {
    errors.push({ field: "estimatedHeightCm", message: "Estimated height must be between 30 and 250 cm." });
  }

  if (errors.length) throw new ApiError(422, "VALIDATION_FAILED", "Record validation failed.", errors);

  return normalizeRecord(input, {
    incidentRef,
    estimatedHeightCm,
    status: "unidentified",
  });
}

function normalizeRecord(input, fixed) {
  return {
    ...fixed,
    upperType: text(input.upperType).toLowerCase(),
    upperColor: text(input.upperColor).toLowerCase(),
    lowerType: text(input.lowerType).toLowerCase(),
    lowerColor: text(input.lowerColor).toLowerCase(),
    visibleMarks: text(input.visibleMarks).toLowerCase(),
    accessories: text(input.accessories).toLowerCase(),
    dentalNotes: text(input.dentalNotes).toLowerCase(),
    otherDescription: text(input.otherDescription).toLowerCase(),
  };
}

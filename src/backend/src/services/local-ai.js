import { ApiError } from "../lib/http.js";

const OBSERVATION_SCHEMA = {
  type: "object",
  properties: {
    upperType: { type: "string" },
    upperColor: { type: "string" },
    lowerType: { type: "string" },
    lowerColor: { type: "string" },
    visibleMarks: { type: "string" },
    accessories: { type: "string" },
    textOnClothing: { type: "string" },
    otherDescription: { type: "string" },
    warnings: { type: "array", items: { type: "string" } },
  },
  required: [
    "upperType", "upperColor", "lowerType", "lowerColor", "visibleMarks",
    "accessories", "textOnClothing", "otherDescription", "warnings",
  ],
};

const NORMALIZATION_SCHEMA = {
  type: "object",
  properties: {
    upperType: { type: "string" },
    upperColor: { type: "string" },
    lowerType: { type: "string" },
    lowerColor: { type: "string" },
    visibleMarks: { type: "string" },
    accessories: { type: "string" },
    dentalNotes: { type: "string" },
    otherDescription: { type: "string" },
  },
  required: [
    "upperType", "upperColor", "lowerType", "lowerColor", "visibleMarks",
    "accessories", "dentalNotes", "otherDescription",
  ],
};

export class LocalAiService {
  constructor(options, fetchImplementation = fetch) {
    this.options = options;
    this.fetch = fetchImplementation;
  }

  async status() {
    try {
      const response = await this.request("/api/tags", { method: "GET" }, 5_000);
      const installed = (response.models || []).map((model) => model.name);
      return {
        provider: "ollama",
        reachable: true,
        endpoint: this.options.url,
        models: {
          text: modelState(this.options.textModel, installed),
          vision: modelState(this.options.visionModel, installed),
        },
        localOnly: true,
      };
    } catch (error) {
      return {
        provider: "ollama",
        reachable: false,
        endpoint: this.options.url,
        models: {
          text: { name: this.options.textModel, installed: false },
          vision: { name: this.options.visionModel, installed: false },
        },
        localOnly: true,
        message: error.message,
      };
    }
  }

  async extractImage({ imageBase64, mimeType = "image/jpeg" }) {
    validateImage(imageBase64, mimeType);
    const content = await this.chat({
      model: this.options.visionModel,
      format: OBSERVATION_SCHEMA,
      system: [
        "You assist an authorized disaster-victim-identification data-entry operator.",
        "Describe only directly visible, non-sensitive evidence.",
        "Never infer identity, name, ethnicity, gender, exact age, cause of death, or exact height.",
        "Use empty strings for anything not clearly visible. Put uncertainty or image limitations in warnings.",
      ].join(" "),
      user: "Extract clothing type and color, accessories, visible distinguishing marks, readable clothing text, and other observable belongings from this operational image.",
      images: [stripDataUrl(imageBase64)],
    });
    return sanitizeObject(content, OBSERVATION_SCHEMA.required);
  }

  async normalizeDescription({ description }) {
    if (typeof description !== "string" || !description.trim()) {
      throw new ApiError(422, "VALIDATION_FAILED", "A non-empty description is required.");
    }
    if (description.length > 10_000) {
      throw new ApiError(422, "VALIDATION_FAILED", "Description must not exceed 10,000 characters.");
    }

    const content = await this.chat({
      model: this.options.textModel,
      format: NORMALIZATION_SCHEMA,
      system: [
        "Convert a missing-person description into the supplied JSON schema.",
        "Do not invent facts or resolve ambiguity. Use lowercase concise values and empty strings for absent evidence.",
      ].join(" "),
      user: description,
    });
    return sanitizeObject(content, NORMALIZATION_SCHEMA.required);
  }

  async chat({ model, format, system, user, images }) {
    try {
      const response = await this.request("/api/chat", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          model,
          stream: false,
          format,
          options: { temperature: 0, seed: 7 },
          messages: [
            { role: "system", content: system },
            { role: "user", content: user, ...(images ? { images } : {}) },
          ],
        }),
      });
      return parseModelJson(response.message?.content);
    } catch (error) {
      if (error instanceof ApiError) throw error;
      throw new ApiError(503, "LOCAL_AI_UNAVAILABLE", `Local AI is unavailable: ${error.message}`);
    }
  }

  async request(path, init, timeoutMs = this.options.timeoutMs) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), timeoutMs);
    try {
      const response = await this.fetch(`${this.options.url}${path}`, { ...init, signal: controller.signal });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) {
        const message = body.error || `Ollama returned HTTP ${response.status}.`;
        if (response.status === 404 && /model/i.test(message)) {
          throw new ApiError(503, "MODEL_NOT_INSTALLED", message);
        }
        throw new Error(message);
      }
      return body;
    } catch (error) {
      if (error.name === "AbortError") throw new Error("The local model timed out.");
      throw error;
    } finally {
      clearTimeout(timeout);
    }
  }
}

function modelState(requested, installed) {
  const base = requested.split(":")[0];
  return { name: requested, installed: installed.some((name) => name === requested || name.split(":")[0] === base) };
}

function validateImage(image, mimeType) {
  if (typeof image !== "string" || !image.trim()) {
    throw new ApiError(422, "VALIDATION_FAILED", "imageBase64 is required.");
  }
  if (!new Set(["image/jpeg", "image/png", "image/webp"]).has(mimeType)) {
    throw new ApiError(415, "UNSUPPORTED_IMAGE_TYPE", "Only JPEG, PNG, and WebP images are accepted.");
  }
  const encoded = stripDataUrl(image);
  if (!/^[a-z0-9+/]+={0,2}$/i.test(encoded) || encoded.length % 4 !== 0) {
    throw new ApiError(422, "VALIDATION_FAILED", "imageBase64 must contain valid base64 image data.");
  }
}

function stripDataUrl(value) {
  return value.replace(/^data:image\/[a-z0-9.+-]+;base64,/i, "").replace(/\s/g, "");
}

export function parseModelJson(value) {
  if (typeof value === "object" && value !== null) return value;
  if (typeof value !== "string") throw new Error("The model returned an empty response.");
  const cleaned = value.trim().replace(/^```(?:json)?\s*/i, "").replace(/\s*```$/, "");
  try {
    return JSON.parse(cleaned);
  } catch {
    throw new Error("The model response was not valid JSON.");
  }
}

function sanitizeObject(value, keys) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new ApiError(502, "INVALID_MODEL_RESPONSE", "The local model returned an invalid object.");
  }
  return Object.fromEntries(keys.map((key) => {
    if (key === "warnings") return [key, Array.isArray(value[key]) ? value[key].map(String).slice(0, 10) : []];
    return [key, typeof value[key] === "string" ? value[key].trim().toLowerCase() : ""];
  }));
}

import path from "node:path";

const backendRoot = path.resolve(import.meta.dirname, "..");

export const config = Object.freeze({
  port: Number(process.env.PORT || 4000),
  host: process.env.HOST || "127.0.0.1",
  dataFile: path.resolve(backendRoot, process.env.DATA_FILE || "data/records.json"),
  databaseUrl: process.env.DATABASE_URL || "",
  allowedOrigin: process.env.ALLOWED_ORIGIN || "http://localhost:3000",
  maxBodyBytes: 12_000_000,
  ollama: Object.freeze({
    url: (process.env.OLLAMA_URL || "http://127.0.0.1:11434").replace(/\/$/, ""),
    textModel: process.env.OLLAMA_TEXT_MODEL || "granite4:3b",
    visionModel: process.env.OLLAMA_VISION_MODEL || "granite3.2-vision:2b",
    timeoutMs: Number(process.env.OLLAMA_TIMEOUT_MS || 120_000),
  }),
});

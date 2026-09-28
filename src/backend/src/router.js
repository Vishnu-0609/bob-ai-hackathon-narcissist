import { ApiError, getPathParam, readJson, sendJson } from "./lib/http.js";

export function createRouter({ service, localAi, config }) {
  return async function route(request, response) {
    const url = new URL(request.url, `http://${request.headers.host || "localhost"}`);
    const cors = {
      "access-control-allow-origin": config.allowedOrigin,
      "access-control-allow-methods": "GET,POST,OPTIONS",
      "access-control-allow-headers": "content-type",
    };

    if (request.method === "OPTIONS") {
      response.writeHead(204, cors);
      return response.end();
    }

    try {
      if (request.method === "GET" && url.pathname === "/health") {
        return sendJson(response, 200, { status: "ok", service: "reconcile-ai-api", time: new Date().toISOString() }, cors);
      }
      if (request.method === "GET" && url.pathname === "/api/v1/dashboard") {
        return sendJson(response, 200, { data: service.dashboard() }, cors);
      }
      if (request.method === "GET" && url.pathname === "/api/v1/ai/status") {
        return sendJson(response, 200, { data: await localAi.status() }, cors);
      }
      if (request.method === "POST" && url.pathname === "/api/v1/ai/normalize-description") {
        const result = await localAi.normalizeDescription(await readJson(request, config.maxBodyBytes));
        return sendJson(response, 200, { data: result }, cors);
      }
      if (request.method === "POST" && url.pathname === "/api/v1/ai/extract-image") {
        const result = await localAi.extractImage(await readJson(request, config.maxBodyBytes));
        return sendJson(response, 200, {
          data: result,
          meta: { model: config.ollama.visionModel, requiresHumanReview: true },
        }, cors);
      }
      if (request.method === "GET" && url.pathname === "/api/v1/ante-mortem") {
        return sendJson(response, 200, { data: service.listAnteMortem() }, cors);
      }
      if (request.method === "POST" && url.pathname === "/api/v1/ante-mortem") {
        const record = await service.createAnteMortem(await readJson(request, config.maxBodyBytes));
        return sendJson(response, 201, { data: record }, cors);
      }
      if (request.method === "GET" && url.pathname === "/api/v1/post-mortem") {
        return sendJson(response, 200, { data: service.listPostMortem() }, cors);
      }
      if (request.method === "POST" && url.pathname === "/api/v1/post-mortem") {
        const record = await service.createPostMortem(await readJson(request, config.maxBodyBytes));
        return sendJson(response, 201, { data: record }, cors);
      }
      if (request.method === "POST" && url.pathname === "/api/v1/post-mortem/from-image") {
        const input = await readJson(request, config.maxBodyBytes);
        const extraction = await localAi.extractImage(input);
        const result = await service.createPostMortemFromExtraction(input, extraction);
        return sendJson(response, 201, {
          data: result.record,
          meta: {
            extraction: result.extraction,
            model: config.ollama.visionModel,
            requiresHumanReview: true,
            rawImageStored: false,
          },
        }, cors);
      }
      const matchId = getPathParam(url.pathname, /^\/api\/v1\/post-mortem\/([^/]+)\/matches$/);
      if (request.method === "GET" && matchId) {
        const limit = Math.min(10, Math.max(1, Number(url.searchParams.get("limit")) || 3));
        return sendJson(response, 200, { data: service.matches(matchId, limit) }, cors);
      }
      throw new ApiError(404, "ROUTE_NOT_FOUND", "The requested endpoint does not exist.");
    } catch (error) {
      const status = error instanceof ApiError ? error.status : 500;
      const code = error instanceof ApiError ? error.code : "INTERNAL_ERROR";
      if (status === 500) console.error(error);
      return sendJson(response, status, {
        error: { code, message: status === 500 ? "An unexpected error occurred." : error.message, details: error.details },
      }, cors);
    }
  };
}

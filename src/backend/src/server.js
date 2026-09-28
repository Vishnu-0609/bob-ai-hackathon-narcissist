import { createServer } from "node:http";
import { config } from "./config.js";
import { JsonRepository } from "./data/repository.js";
import { PostgresRepository } from "./data/postgres-repository.js";
import { createRouter } from "./router.js";
import { RecordsService } from "./services/records.js";
import { LocalAiService } from "./services/local-ai.js";

const repository = config.databaseUrl
  ? new PostgresRepository(config.databaseUrl)
  : new JsonRepository(config.dataFile);
await repository.initialize();

const service = new RecordsService(repository);
const localAi = new LocalAiService(config.ollama);
const server = createServer(createRouter({ service, localAi, config }));

server.listen(config.port, config.host, () => {
  console.log(`ReconcileAI API listening on http://${config.host}:${config.port}`);
});

function shutdown(signal) {
  console.log(`\n${signal} received; closing server.`);
  server.close(async () => {
    await repository.close?.();
    process.exit(0);
  });
}

process.on("SIGINT", () => shutdown("SIGINT"));
process.on("SIGTERM", () => shutdown("SIGTERM"));

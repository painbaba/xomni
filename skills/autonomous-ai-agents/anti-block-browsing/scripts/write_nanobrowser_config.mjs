// Advanced Nanobrowser config: per-agent model split + tuned agent quality knobs.
// Planner gets gemini-3.1-pro-preview (strong reasoning — it plans the route);
// Navigator gets gemini-3.6-flash (fast + vision — it clicks/reads/scrolls).
// Vision ON for both (screenshot-based perception = reads canvas/JS-heavy sites).
//
// Usage: node write_nanobrowser_config.mjs [profile]
// Chrome MUST be closed (LevelDB LOCK). Default profile: Default
import { ClassicLevel } from "classic-level";

const profile = process.argv[2] || "Default";
const extId = "jjmpnipdclgmglamcncnbfgjedadkade";
const dbPath = `C:/Users/HP/AppData/Local/Google/Chrome/User Data/${profile}/Local Extension Settings/${extId}`;

let db;
try {
  db = new ClassicLevel(dbPath, { keyEncoding: "utf8", valueEncoding: "buffer" });
  await db.open();
} catch (e) {
  console.error("OPEN FAILED (is Chrome running? close it first):", e.message);
  process.exit(1);
}

try {
  // ---- llm-api-keys: one provider pointing at the rotation proxy ----
  const providerKey = "gemini-proxy";
  const provider = {
    name: "Gemini Proxy",
    type: "custom_openai",
    baseUrl: "http://localhost:8790/v1",
    apiKey: "proxy", // ignored — rotation happens in the proxy
    modelNames: ["gemini-3.6-flash", "gemini-3.1-pro-preview", "gemini-3.5-flash"],
    createdAt: Date.now()
  };
  let llm = { providers: {} };
  try {
    const existing = await db.get("llm-api-keys");
    if (existing) llm = JSON.parse(existing.toString("utf8"));
  } catch (e) { /* not present yet */ }
  llm.providers = llm.providers || {};
  llm.providers[providerKey] = provider;

  // ---- agent-models: per-agent split (README-recommended architecture) ----
  // Navigator = fast flash (it does the walking), Planner = pro (it does the thinking)
  const agentModels = {
    agents: {
      Navigator: { provider: providerKey, modelName: "gemini-3.6-flash",
                   parameters: { temperature: 0.1, topP: 0.1 } },
      Planner:   { provider: providerKey, modelName: "gemini-3.1-pro-preview",
                   parameters: { temperature: 0.2, topP: 0.2 } }
    }
  };

  // ---- general-settings: vision ON, tuned loop ----
  const generalSettings = {
    maxSteps: 100,          // cap per task
    maxActionsPerStep: 5,   // actions before re-snapshot
    maxFailures: 3,         // retries before giving up a step
    useVision: true,        // screenshot-based perception — reads canvas/JS sites
    useVisionForPlanner: true,
    planningInterval: 3,    // Planner re-plans every 3 steps
    displayHighlights: true,
    minWaitPageLoad: 250,   // ms min wait after navigation
    replayHistoricalTasks: false
  };

  await db.put("llm-api-keys", Buffer.from(JSON.stringify(llm), "utf8"));
  await db.put("agent-models", Buffer.from(JSON.stringify(agentModels), "utf8"));
  await db.put("general-settings", Buffer.from(JSON.stringify(generalSettings), "utf8"));
  console.log("WROTE llm-api-keys + agent-models + general-settings for", profile);

  const v1 = JSON.parse((await db.get("llm-api-keys")).toString("utf8"));
  const v2 = JSON.parse((await db.get("agent-models")).toString("utf8"));
  const v3 = JSON.parse((await db.get("general-settings")).toString("utf8"));
  console.log("VERIFY providers:", Object.keys(v1.providers));
  console.log("VERIFY Navigator:", JSON.stringify(v2.agents.Navigator));
  console.log("VERIFY Planner:  ", JSON.stringify(v2.agents.Planner));
  console.log("VERIFY vision:   ", v3.useVision, "| planningInterval:", v3.planningInterval);
} finally {
  await db.close();
}

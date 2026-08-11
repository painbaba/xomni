// Read Nanobrowser's storage LevelDB to verify config (Chrome must be closed)
// Usage: node read_nanobrowser_config.mjs [profile]
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
  for await (const [key, value] of db.iterator()) {
    let text = value.toString("utf8");
    if (text.length > 200) text = text.slice(0, 200) + "...";
    console.log(`${key} = ${text}`);
  }
} finally {
  await db.close();
}

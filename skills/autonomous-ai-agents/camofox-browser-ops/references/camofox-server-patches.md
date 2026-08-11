# Camofox server.js patch recipes

Target: `C:\Users\HP\camofox\node_modules\@askjo\camofox-browser\server.js`
(pkg `@askjo/camofox-browser` v1.13.1). Both patches are lost when the npm
package is reinstalled/upgraded. After re-applying, verify with
`node --check server.js` and restart the server (see the kill trap in SKILL.md).

## Patch 1 — health probe viewport crash (isMobile CDP scheme error)

**Symptom**: every ~3 min of idle time, log shows
`health probe failed ... Browser.setDefaultViewport ... Found property "<root>.viewport.isMobile" - false which is not described in this scheme`
followed by `restarting browser`. Each restart kills active browsing sessions.

**Cause**: the 60s health-probe interval calls `browser.newContext()` with the
Playwright default viewport, which includes `isMobile:false`. Camoufox's CDP
layer does not implement that field in this scheme version and rejects the call.

**Fix** (around line 6412, in the health-probe `setInterval`):

```diff
-    testContext = await browser.newContext();
+    testContext = await browser.newContext({ viewport: null });
```

The other probe (`probeGoogleSearch`, ~line 829) already passes
`viewport: null` — that's why it never failed. This is the same one-line fix.

## Patch 2 — tab reaper unhandledRejections ('reading url' on undefined)

**Symptom**: recurring log noise, ~1 per 60s:
`unhandledRejection ... TypeError: Cannot read properties of undefined (reading 'url')`

**Root cause**: Hermes browser tools create ephemeral `hermes_{uuid}` sessions
per task. When a session is mid-close (context already gone) while the
per-tab inactivity reaper iterates `session.tabGroups`, an unguarded read of a
now-undefined tab/page throws inside the `setInterval` → unhandledRejection.
Same class of error appears if tabs are deleted individually while the session
object lingers (`DELETE /tabs/:id` without `DELETE /sessions/:userId`).

**Fix**: wrap the per-session body of the "Per-tab inactivity reaper"
`setInterval` (around line 5468) in try/catch, logging instead of throwing:

```diff
 setInterval(() => {
   const now = Date.now();
   for (const [userId, session] of sessions) {
-    for (const [listItemId, group] of session.tabGroups) {
-      for (const [tabId, tabState] of group) {
+    try {
+      for (const [listItemId, group] of session.tabGroups) {
+        for (const [tabId, tabState] of group) {
         if (!tabState._lastReaperCheck) {
           ...
         }
       }
       if (group.size === 0) {
         session.tabGroups.delete(listItemId);
       }
     }
     // Clean up sessions with zero tabs remaining -- free browser context memory
     if (session.tabGroups.size === 0 && !hasActivePageLeases(session)) {
       session._closing = true;
       log('info', 'session empty after tab reaper, closing', { userId });
       closeSession(userId, session, { reason: 'tab_reaper_empty_session', clearDownloads: true, clearLocks: true }).catch(() => {});
       sessionsExpiredTotal.inc();
     }
+    } catch (reapErr) {
+      // A session can be mid-close (context gone) while the reaper iterates it.
+      // Guard so one inconsistent session cannot spam unhandledRejections.
+      log('warn', 'tab reaper skipped session', { userId, error: reapErr.message });
+    }
   }
   if (sessions.size === 0) scheduleBrowserIdleShutdown();
 }, 60_000);
```

## Operational notes

- `node --check server.js` is the fast syntax gate; `npm run build` (tsc +
  plugin copy) is the package's canonical build verification. `npm test` is NOT
  runnable: jest is a devDependency, npm does not install devDeps of nested
  dependencies, and no `tests/` directory ships in the installed package.
- After patching, restart via the two-step kill (netstat → taskkill /PID) then
  `npx camofox-browser` in background.
- Verify fix: `grep -c "unhandledRejection" camofox.log` stays frozen across a
  full 60s reaper cycle; `/health` shows `consecutiveFailures: 0`.

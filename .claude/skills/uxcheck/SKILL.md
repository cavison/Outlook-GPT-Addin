---
name: uxcheck
description: Runtime check of a running app in a real browser, separate from the code-reading /bughunt. Covers layout at phone, tablet, desktop and zoom widths; buttons, forms, back/refresh; keyboard and accessibility (WCAG 2.2 AA review); and selection switching. Browser agents cannot change code. They auto-select the ZZ-test property, enter only marked test data there, and never click actions that email, notify, text, pay or post. Every finding needs a screenshot plus steps that an independent agent reproduces. Feeds the same fix plan and approval loop.
argument-hint: "[app URL] [--screens \"Units, Notes\"] [--max-screens 20] [--allow-external-side-effects]"
disable-model-invocation: true
---

# UX check (runtime, in a browser)

You run the `uxcheck-run` workflow against the running app and report what survives replay. This step never edits code. Browser agents have only look-and-click tools; they have no editing, shell or in-page script tools. The only files written are reports and screenshots under `.bughunt/`.

## 0. Browser tools

Check that the `mcp__bughunt-browser__browser_navigate` tool is available (search for it with ToolSearch "bughunt-browser"). If it is not:
1. Tell the user the browser server is not installed or not loaded in this session.
2. Tell them to install it from the kit with `node .claude/bughunt-install.mjs <this repo> --with-ux`, which adds `bughunt-browser` to `.mcp.json` and enables it in `.claude/settings.json`.
3. Tell them to start a new session.
4. In cloud sessions, the environment's network access must allow the npm registry, because the server is fetched with npx.

Stop until the tools are available.

## 1. Settings (`.bughunt/ux.json`)

Read `<project root>/.bughunt/ux.json`. If it is missing, ask the user (AskUserQuestion, one round) and create it:
- **Where the app runs:** either a URL that is already up, or a start command plus the URL to wait for (for example `npm run dev` and `http://localhost:5173`).
- **Sign-in:**
  - none;
  - typed username and password, which uses environment secrets named `BUGHUNT_UX_USER` and `BUGHUNT_UX_PASSWORD`;
  - single sign-on with MFA (for example Power Apps or Microsoft 365), which uses a saved session, see below.

```json
{
  "base_url": "http://localhost:5173",
  "start_command": "npm run dev",
  "ready_url": "http://localhost:5173",
  "login": { "required": true, "user_secret": "BUGHUNT_UX_USER", "password_secret": "BUGHUNT_UX_PASSWORD", "notes": "" },
  "test_selection": "ZZ-test",
  "max_screens": 20,
  "allow_external_side_effects": false
}
```

**Never write secret values into this file, the chat or the repo.** The user sets them as environment variables: cloud environment secrets, or the shell environment for the local CLI. The browser server reads them at session start, so a new session is needed after adding them.

**Saved session for SSO/MFA:**
1. On their own computer, the user runs `npx playwright open --save-storage=storage-state.json <app URL>`, signs in (including MFA), then closes the window.
2. They store the file's contents, or its base64, as the environment secret `BUGHUNT_UX_STORAGE_STATE`.

Sessions expire, so this has to be repeated now and then. Some identity providers block automated browsers; if sign-in keeps failing, say so plainly.

`test_selection` is the property selected automatically whenever a property selection exists. The default is "ZZ-test". Do not ask the user about it on each run.

## 2. Start the app (if `start_command` is set)

Start it in the background (Bash with `run_in_background`). Poll `ready_url` with `curl -s -o /dev/null -w "%{http_code}"` every few seconds for up to 3 minutes. If it never answers, show the last lines of the app's output and stop.

## 3. Launch

1. Create the run directory `<root>/.bughunt/runs/<YYYYMMDD-HHMM>-ux/`. When called from `/bugloop`, use `cycle-NN/ux/`.
2. Optionally run the bughunt scope script (`.claude/skills/bughunt/scope.sh`) and pass its `files`, which helps the side-effect scan.
3. Tell the user in one short message what will happen:
   - the app will be tested in a browser, one screen at a time;
   - "ZZ-test" will be selected automatically;
   - marked test data will be entered there;
   - actions that contact real people or systems will not be clicked.
4. Call the Workflow tool with `name: "uxcheck-run"` and `args` as a JSON object:

```json
{
  "root": "<abs project root>",
  "run_dir": "<run dir relative to root>",
  "base_url": "<ux.json base_url, or the URL argument>",
  "app_context": "<1-3 sentences on what the app does>",
  "login": "<ux.json login>",
  "test_selection": "<ux.json test_selection or ZZ-test>",
  "screens": "<--screens as [{name, how_to_reach}], if given>",
  "files": "<scope files, optional>",
  "max_screens": "<number>",
  "allow_external_side_effects": "<true only if ux.json or the flag says so>",
  "previous_findings": "<from /bugloop only>",
  "clean_threshold": "medium"
}
```

Wait for the completion notification instead of polling.

## 4. Report

1. If `ok` is false, show the error. Typical causes: the app is not reachable, sign-in failed (check the secrets and `login.notes`), or the browser tools are not loaded.
2. Save the result, exactly as returned, as `findings.json` in the run directory. Then run the evidence gate: `node .claude/skills/bughunt/evidence-gate.mjs <run dir>/findings.json`. It rejects findings whose screenshot is missing, not an image or outside the project, or whose steps are empty.
3. Write `ux-report.md` in the run directory following the "ux-report.md" section of `.claude/skills/bughunt/report-format.md`.
4. Reply in chat with:
   - the verdict (CLEAN or NOT CLEAN; only `bug` findings at or above the threshold block);
   - **if `needs_test_selection` is true: say plainly that this app has a property selection but no "ZZ-test" option, so data-entry tests were skipped, and ask the user to add one;**
   - side effects:
     - actions not clicked because they reach real people or systems (`avoided_by_rule`);
     - any extra risks testers noticed;
     - the test records created (so the user can clean them up if they want);
   - a table of blocking bugs (ID, severity, screen, viewport, title), then shorter lists of cosmetic, accessibility and other findings;
   - the coverage grid summary and any gaps;
   - where the screenshots are.
5. Stop the app if you started it.

Next step: `/bugfix-plan <run dir>` designs fixes for these findings, the same as for code findings. Nothing changes until the user approves. `/bugloop --ux` includes this check in every cycle.

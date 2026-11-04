# Handoff: AI Tooling for Advanced Power Apps (as of Nov 2026)

## Who I am / what I want
I build Power Apps and want AI coding help that can produce **advanced, modern apps**: canvas apps with correct Power Apps YAML (`.pa.yaml`), modern controls, advanced Power Fx, custom controls (PCF), and React-based Code Apps.
A year ago, the "vibe-coding" tools were bad at Power Apps YAML. They made up properties and controls and produced output that wouldn't import. I researched what has changed since then. The findings are below. Continue from here.

## How to work with me
- If something is unclear, ask clarifying questions before producing long output.
- Before answering, weigh these perspectives and synthesize them into one answer: Analyst, Creative, Critic, Pragmatist, Empath, Historian, Skeptic-of-the-Skeptic, Visionary.
- Most of this tooling is **preview** and changes fast. Check the current docs and repos before giving exact commands.

## Research findings (verified Nov 2026)

### 1. Official Microsoft: `microsoft/power-platform-skills` (the key development)
A plugin collection for Claude Code, GitHub Copilot CLI and VS Code (agent plugins).

**canvas-apps plugin (preview)**
- Generates a `.pa.yaml` file for each screen (controls and Power Fx formulas).
- Validates the YAML with the **Canvas Authoring MCP server** (NuGet: `Microsoft.PowerApps.CanvasAuthoring.McpServer`, ~v1.1.5). Its tools include `compile_canvas`, `list_controls` and `sync_canvas`.
- Fixes validation errors automatically and syncs changes into a **live Power Apps Studio co-authoring session**.
- Skills: `/canvas-app` (build or edit), `/configure-canvas-mcp` (connect to Studio), `/add-data-source`.
- Requirements:
  - The app must already exist. Create and save it in Studio (it can be blank) and turn on **co-authoring**.
  - Keep the Studio tab open the whole time.
  - Paste the Studio URL into `/configure-canvas-mcp`.
  - Test the connection by asking "List the available Canvas App controls".
- Install:
  ```
  /plugin marketplace add microsoft/power-platform-skills
  /plugin install canvas-apps@power-platform-skills
  ```
  In VS Code, search the Extensions view for `@agentPlugins canvas apps`. If nothing shows up, set `"chat.plugins.enabled": true`.

**code-apps-preview plugin (preview)**
- Builds **Power Apps Code Apps**: React + Vite/TypeScript web apps that run inside Power Platform with connectors and Dataverse. Command: `/create-code-app`.
- Install: `/plugin install code-apps-preview@power-platform-skills`
- This replaces the plugin that used to live in `microsoft/PowerAppsCodeApps`.

### 2. Authoring agent inside Power Apps Studio (preview)
- Agentic building directly inside canvas studio: you describe the app, approve its plan, and it builds the screens, controls and formulas.
- Limits: US and English only. An admin must enable "Agentic Coauthoring in Power Apps using GitHub" in Power Platform Admin Center → Tenant Settings. It uses and bills your GitHub account.

### 3. Other Microsoft items
- `pac canvas validate` validates `.pa.yaml` from an unpacked `.msapp` (preview).
- Canvas source code management (pa.yaml) became generally available on Sep 15, 2025.
- "New Power Apps experience" (preview), Plans (plan designer), and Generative Pages (React pages in model-driven apps).
- Dataverse MCP server: lets an agent see real table and column names.
- PCF is still the route for custom controls. Ready-made controls: Creator Kit (Fluent UI) and pcf.gallery. Modern controls are mostly GA.

### 4. Community repos (newer; check how mature each one is)
- `satriotsubasa/PowerPlatform-Core`: 12 skills (ALM, PCF, flows, Dataverse schema, Code Apps, deployment). For Claude Code and Codex.
- `Lukacastro-PowerDev/power-apps-code-apps-agent-skill`: knowledge pack for Code Apps (SharePoint/Dataverse + React).
- `Powercademy` skills: a delivery-method layer built on top of Microsoft's plugins (not affiliated with Microsoft).
- `samcex/codex-powerapps-canvas`: a Codex wrapper around the Canvas MCP.

## Recommendation so far
- **Advanced canvas apps:** Microsoft `canvas-apps` plugin plus Claude Code. It validates against Power Apps itself, which solves the made-up-properties problem.
- **Highly custom or modern UI:** Code Apps (code-apps-preview), or PCF controls (PowerPlatform-Core helps here).
- **Cautions:**
  - Preview features aren't meant for production. Use a sandbox environment and back up apps.
  - Review all generated changes before publishing.
  - App context gets sent to the AI provider, so check org policy and DLP.

## Open questions / next steps
1. Is Code Apps generally available yet? Check Microsoft Learn and the release plan.
2. Install the canvas-apps plugin locally and connect it to a test app in a sandbox environment.
3. Do a trial build: an advanced screen (gallery with filters, a multi-step form, modern controls, a responsive layout), then check the YAML quality.
4. Compare with Code Apps for the same scenario, and decide which approach fits each type of app.
5. Look into PowerPlatform-Core's PCF skill for custom controls.

## Sources
- https://github.com/microsoft/power-platform-skills (plugins/canvas-apps, plugins/code-apps)
- https://learn.microsoft.com/power-apps/maker/canvas-apps/create-canvas-external-tools
- https://learn.microsoft.com/power-apps/maker/canvas-apps/canvas-authoring-agent
- https://learn.microsoft.com/power-apps/maker/canvas-apps/power-apps-yaml
- https://learn.microsoft.com/power-platform/developer/cli/reference/canvas
- https://www.nuget.org/packages/Microsoft.PowerApps.CanvasAuthoring.McpServer
- https://github.com/microsoft/PowerAppsCodeApps
- https://github.com/satriotsubasa/PowerPlatform-Core
- https://github.com/Lukacastro-PowerDev/power-apps-code-apps-agent-skill
- https://www.inogic.com/blog/2026/07/ai-assisted-power-apps-code-app-development-using-github-copilot-cli/
- https://rajeevpentyala.com/2026/06/11/build-a-power-apps-code-app-using-power-platform-skills/

**Start by:** confirming the current preview or GA status of the canvas-apps and code-apps plugins, then help me install the canvas-apps plugin and connect it to a sandbox test app.

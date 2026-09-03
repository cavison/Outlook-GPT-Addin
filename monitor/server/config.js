import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
export const ROOT = path.resolve(here, '..');
export const DATA_DIR = path.join(ROOT, 'data');

// Minimal .env reader — one less dependency, and this file only ever holds a
// handful of tenant ids.
function loadDotEnv() {
  const file = path.join(ROOT, '.env');
  if (!fs.existsSync(file)) return;
  for (const line of fs.readFileSync(file, 'utf8').split('\n')) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    const eq = trimmed.indexOf('=');
    if (eq === -1) continue;
    const key = trimmed.slice(0, eq).trim();
    const value = trimmed.slice(eq + 1).trim().replace(/^["']|["']$/g, '');
    if (!(key in process.env)) process.env[key] = value;
  }
}
loadDotEnv();

const bool = (v, fallback = false) =>
  v === undefined ? fallback : ['1', 'true', 'yes', 'on'].includes(String(v).toLowerCase());

export const config = {
  port: Number(process.env.PORT ?? 4310),

  // Poll cadence. Power Automate's management API is not generous with rate
  // limits, so anything under ~20s will start getting throttled on a real
  // tenant with more than a handful of flows.
  pollSeconds: Number(process.env.POLL_SECONDS ?? 20),

  // Which providers are live. Mock stays on until real credentials exist so the
  // city is never empty.
  providers: {
    mock: bool(process.env.ENABLE_MOCK, true),
    powerAutomate: bool(process.env.ENABLE_POWER_AUTOMATE, false),
    graph: bool(process.env.ENABLE_GRAPH, false),
    // A worked non-flow domain: properties sized by budget variance.
    portfolio: bool(process.env.ENABLE_PORTFOLIO, true),
    // Scale model of the flow checker. Off by default; set FLOW_FLEET to the
    // number of flows you want to simulate.
    flowFleet: Number(process.env.FLOW_FLEET ?? 0) > 0,
    // Phase 01: the property/parcel shell, driven by config/portfolio.json.
    estate: bool(process.env.ENABLE_ESTATE, true),
  },

  // Entra ID (Azure AD) app registration. Device-code flow: no client secret,
  // no redirect URI, works for a local single-user tool.
  azure: {
    clientId: process.env.AZURE_CLIENT_ID ?? '',
    tenantId: process.env.AZURE_TENANT_ID ?? 'common',
  },

  // Simulated severities until real connectors land, so the skyline has
  // something to say on first run. Set false for the bare shell.
  estateDemo: bool(process.env.ESTATE_DEMO, true),

  flowFleet: {
    size: Number(process.env.FLOW_FLEET ?? 0),
  },

  powerAutomate: {
    // Leave blank to auto-discover the default environment.
    environmentId: process.env.POWER_AUTOMATE_ENVIRONMENT ?? '',
  },

  // Write actions are opt-in twice: once here, once per-click in the UI.
  allowWriteActions: bool(process.env.ALLOW_WRITE_ACTIONS, true),

  // Guard rail — a flow re-run is a real production event.
  requireConfirmForWrites: bool(process.env.REQUIRE_CONFIRM, true),
};

fs.mkdirSync(DATA_DIR, { recursive: true });

export function dataPath(name) {
  return path.join(DATA_DIR, name);
}

export function readJson(name, fallback) {
  try {
    return JSON.parse(fs.readFileSync(dataPath(name), 'utf8'));
  } catch {
    return fallback;
  }
}

export function writeJson(name, value) {
  fs.writeFileSync(dataPath(name), JSON.stringify(value, null, 2));
}

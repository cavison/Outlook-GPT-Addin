#!/usr/bin/env node
// bughunt browser server: starts the Playwright MCP server that the /uxcheck browser agents use.
// Registered in the project's .mcp.json as "bughunt-browser" (the kit installer adds it).
//
// What it does before starting the server:
//  - writes .bughunt/.auth/secrets.env from environment variables named BUGHUNT_UX_* (for example
//    BUGHUNT_UX_USER, BUGHUNT_UX_PASSWORD). Agents type the variable NAME; the browser server swaps in
//    the value and blanks it out of everything the agents read back, so the AI never sees it.
//  - writes .bughunt/.auth/storage-state.json from BUGHUNT_UX_STORAGE_STATE (raw JSON or base64) if set,
//    for apps whose sign-in cannot be typed (SSO with MFA): export a signed-in session once, store it as a secret.
//  - keeps .bughunt/.auth and the server's scratch output out of git.
//  - picks a browser: BUGHUNT_UX_EXECUTABLE, else the preinstalled Chromium in cloud sessions, else
//    BUGHUNT_UX_BROWSER (chrome, msedge, firefox, webkit), else Edge on Windows and Chrome elsewhere.
//
// Never prints to stdout (stdout is the MCP channel). `--print-args` prints the planned command and exits.
import { spawn } from 'node:child_process'
import { existsSync, mkdirSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'

const PLAYWRIGHT_MCP = '@playwright/mcp@0.0.82'
const root = process.cwd()
const auth = join(root, '.bughunt', '.auth')
const scratch = join(root, '.bughunt', '.mcp-output')
const env = process.env
const say = msg => process.stderr.write(`[bughunt-browser] ${msg}\n`)

function prepare() {
  for (const dir of [auth, scratch]) {
    mkdirSync(dir, { recursive: true })
    const gi = join(dir, '.gitignore')
    if (!existsSync(gi)) writeFileSync(gi, '*\n')
  }
  const names = Object.keys(env).filter(k => /^BUGHUNT_UX_[A-Z0-9_]+$/.test(k) && !['BUGHUNT_UX_STORAGE_STATE', 'BUGHUNT_UX_BROWSER', 'BUGHUNT_UX_EXECUTABLE', 'BUGHUNT_UX_HEADED'].includes(k))
  const secretsFile = join(auth, 'secrets.env')
  // dotenv format; values are quoted so special characters survive.
  writeFileSync(secretsFile, names.map(k => `${k}=${JSON.stringify(env[k])}`).join('\n') + (names.length ? '\n' : ''), { mode: 0o600 })
  let storageState = null
  if (env.BUGHUNT_UX_STORAGE_STATE) {
    const raw = env.BUGHUNT_UX_STORAGE_STATE.trim()
    const json = raw.startsWith('{') ? raw : Buffer.from(raw, 'base64').toString('utf8')
    try {
      JSON.parse(json)
      storageState = join(auth, 'storage-state.json')
      writeFileSync(storageState, json, { mode: 0o600 })
    } catch {
      say('BUGHUNT_UX_STORAGE_STATE is not valid JSON or base64 JSON; ignoring it')
    }
  } else if (existsSync(join(auth, 'storage-state.json'))) {
    storageState = join(auth, 'storage-state.json')
  }
  return { names, secretsFile, storageState }
}

function buildArgs({ names, secretsFile, storageState }) {
  const args = ['--headless', '--isolated', '--snapshot-boxes', '--output-dir', scratch]
  if (env.BUGHUNT_UX_HEADED === '1') args.shift()
  if (names.length) args.push('--secrets', secretsFile)
  if (storageState) args.push('--storage-state', storageState)
  const cloudChromium = '/opt/pw-browsers/chromium'
  if (env.BUGHUNT_UX_EXECUTABLE) args.push('--executable-path', env.BUGHUNT_UX_EXECUTABLE)
  else if (existsSync(cloudChromium) && !env.BUGHUNT_UX_BROWSER) args.push('--executable-path', cloudChromium)
  else args.push('--browser', env.BUGHUNT_UX_BROWSER || (process.platform === 'win32' ? 'msedge' : 'chrome'))
  // Containers that run as root cannot use Chromium's sandbox.
  if (process.platform === 'linux' && typeof process.getuid === 'function' && process.getuid() === 0) args.push('--no-sandbox')
  return args
}

const plan = prepare()
const args = buildArgs(plan)
if (process.argv.includes('--print-args')) {
  process.stdout.write(JSON.stringify({ package: PLAYWRIGHT_MCP, args, secrets: plan.names }) + '\n')
  process.exit(0)
}
say(`starting ${PLAYWRIGHT_MCP}; secrets available to agents by name: ${plan.names.join(', ') || 'none'}`)
const isWin = process.platform === 'win32'
const child = spawn(isWin ? 'npx.cmd' : 'npx', ['-y', PLAYWRIGHT_MCP, ...args], { stdio: 'inherit', shell: isWin })
child.on('exit', code => process.exit(code ?? 0))
for (const sig of ['SIGINT', 'SIGTERM']) process.on(sig, () => child.kill(sig))

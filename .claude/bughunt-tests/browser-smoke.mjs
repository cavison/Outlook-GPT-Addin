// Browser self-test for /uxcheck (no AI, no tokens). Run: node .claude/bughunt-tests/browser-smoke.mjs
// Starts the practice app in ./fixture, launches the real bughunt browser server (.claude/skills/uxcheck/browser-server.mjs)
// in a temporary folder, and drives it the way the ux agents do:
//   - every browser tool named in the ux-tester/ux-skeptic agent files exists in the pinned server version
//   - signing in by typing secret NAMES works, and the real password never appears in tool output
//   - the ZZ-test property can be selected, element sizes are reported, and screenshots are saved as real PNGs
import { createServer } from 'node:http'
import { spawn } from 'node:child_process'
import { readFileSync, mkdtempSync, existsSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = fileURLToPath(new URL('.', import.meta.url))
const kit = fileURLToPath(new URL('..', import.meta.url))
const PASSWORD = 's3cret-pass' // the practice app's fake password
let failures = 0
const check = (ok, name, detail = '') => { if (!ok) failures++; console.log(`${ok ? 'PASS' : 'FAIL'} ${name}${detail ? ` - ${detail}` : ''}`) }

const html = readFileSync(join(here, 'fixture', 'index.html'))
const http = createServer((req, res) => { res.writeHead(200, { 'content-type': 'text/html' }); res.end(html) })
await new Promise(r => http.listen(0, '127.0.0.1', r))
const url = `http://127.0.0.1:${http.address().port}/index.html`

const ws = mkdtempSync(join(tmpdir(), 'bughunt-smoke-'))
const server = spawn('node', [join(kit, 'skills', 'uxcheck', 'browser-server.mjs')], {
  cwd: ws,
  stdio: ['pipe', 'pipe', 'inherit'],
  env: { ...process.env, BUGHUNT_UX_USER: 'tester', BUGHUNT_UX_PASSWORD: PASSWORD },
})
const timer = setTimeout(() => { console.log('FAIL timed out after 180s'); server.kill(); process.exit(1) }, 180000)

let buf = ''
const waiters = {}
server.stdout.on('data', d => {
  buf += d
  let i
  while ((i = buf.indexOf('\n')) >= 0) {
    const line = buf.slice(0, i); buf = buf.slice(i + 1)
    try { const m = JSON.parse(line); if (m.id && waiters[m.id]) waiters[m.id](m) } catch {}
  }
})
let id = 0
const rpc = (method, params) => new Promise(r => { const n = ++id; waiters[n] = r; server.stdin.write(JSON.stringify({ jsonrpc: '2.0', id: n, method, params }) + '\n') })
const tool = async (name, args) => {
  const r = await rpc('tools/call', { name, arguments: args })
  if (r.error) return `ERROR ${JSON.stringify(r.error)}`
  return (r.result?.content || []).filter(c => c.type === 'text').map(c => c.text).join('\n')
}
const refOf = (snap, text) => { const l = snap.split('\n').find(x => x.includes(text) && x.includes('[ref=')); return l && l.match(/\[ref=([^\]]+)\]/)[1] }

try {
  await rpc('initialize', { protocolVersion: '2025-06-18', capabilities: {}, clientInfo: { name: 'bughunt-smoke', version: '1' } })
  server.stdin.write(JSON.stringify({ jsonrpc: '2.0', method: 'notifications/initialized' }) + '\n')

  // 1. Tool names used by the agent definitions exist in this server version.
  const tools = new Set((await rpc('tools/list', {})).result.tools.map(t => t.name))
  for (const agentFile of ['ux-tester.md', 'ux-skeptic.md']) {
    const line = readFileSync(join(kit, 'agents', agentFile), 'utf8').split('\n').find(l => l.startsWith('tools:'))
    const wanted = line.replace('tools:', '').split(',').map(s => s.trim()).filter(s => s.startsWith('mcp__bughunt-browser__')).map(s => s.replace('mcp__bughunt-browser__', ''))
    const missing = wanted.filter(t => !tools.has(t))
    check(missing.length === 0, `${agentFile}: all ${wanted.length} browser tools exist`, missing.join(', '))
    for (const banned of ['browser_evaluate', 'browser_run_code_unsafe', 'browser_file_upload', 'browser_drop']) {
      check(!wanted.includes(banned), `${agentFile}: ${banned} is not granted`)
    }
  }

  // 2. Sign in by typing secret NAMES.
  await tool('browser_navigate', { url })
  const s1 = await tool('browser_snapshot', {})
  await tool('browser_type', { element: 'Username', target: refOf(s1, 'textbox "Username"'), text: 'BUGHUNT_UX_USER' })
  const typed = await tool('browser_type', { element: 'Password', target: refOf(s1, 'textbox "Password"'), text: 'BUGHUNT_UX_PASSWORD' })
  const clicked = await tool('browser_click', { element: 'Sign in', target: refOf(s1, 'button "Sign in"') })
  const s2 = await tool('browser_snapshot', {})
  check(s2.includes('Units'), 'signed in with secret names')
  check(![typed, clicked, s2].some(t => t.includes(PASSWORD)), 'real password never appears in tool output')

  // 3. Select ZZ-test, read element sizes, save a screenshot.
  await tool('browser_select_option', { element: 'Property', target: refOf(s2, 'combobox "Property"'), values: ['ZZ-test'] })
  const s3 = await tool('browser_snapshot', { boxes: true })
  check(/option "ZZ-test" \[selected\]/.test(s3), 'ZZ-test property selected')
  check(/\[box=\d+,\d+,\d+,\d+\]/.test(s3), 'element sizes reported for overflow and tap-target checks')
  const shot = '.bughunt/runs/smoke/ux-evidence/smoke.png'
  await tool('browser_resize', { width: 375, height: 812 })
  await tool('browser_take_screenshot', { filename: shot, scale: 'css' })
  const file = join(ws, shot)
  const isPng = existsSync(file) && readFileSync(file).subarray(0, 4).equals(Buffer.from([0x89, 0x50, 0x4e, 0x47]))
  check(isPng, 'screenshot saved as a PNG inside the project', file)
  check(existsSync(join(ws, '.bughunt', '.auth', '.gitignore')), 'credentials folder is git-ignored')
} catch (e) {
  check(false, 'browser smoke test crashed', e.message)
} finally {
  clearTimeout(timer)
  server.kill()
  http.close()
}
console.log(failures ? `\n${failures} FAILED` : '\nBROWSER SMOKE TEST PASSED')
process.exit(failures ? 1 : 0)

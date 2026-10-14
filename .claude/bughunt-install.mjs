#!/usr/bin/env node
// bughunt kit installer. Copies the kit into another project's .claude/ folder (or your user ~/.claude/).
//
//   node .claude/bughunt-install.mjs <path to app repo> [--with-ux] [--force] [--no-tests] [--dry-run]
//   node .claude/bughunt-install.mjs --user [--force] [--dry-run]
//
//   --with-ux   also register the "bughunt-browser" server for /uxcheck: adds it to the repo's .mcp.json and
//               enables it in .claude/settings.json (enabledMcpjsonServers)
//   --force     replace kit files that differ from this version (use it to upgrade; your other files are untouched)
//   --no-tests  skip the kit's offline tests
//   --dry-run   show what would happen without writing anything
//   --user      install agents, workflows and skills into ~/.claude for every project on this computer
//
// Never overwrites a file you changed unless --force is given; never deletes anything. Always makes sure
// .bughunt/.auth/ (credentials) and .bughunt/.mcp-output/ (browser scratch files) are git-ignored.
import { readFileSync, writeFileSync, existsSync, mkdirSync, copyFileSync, statSync, chmodSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { homedir } from 'node:os'
import { fileURLToPath } from 'node:url'

const kitDir = dirname(fileURLToPath(import.meta.url))
const manifest = JSON.parse(readFileSync(join(kitDir, 'bughunt-kit.json'), 'utf8'))
const argv = process.argv.slice(2)
const flag = f => argv.includes(f)
const target = argv.find(a => !a.startsWith('--'))
const dry = flag('--dry-run')
const user = flag('--user')

if (flag('--help') || (!target && !user)) {
  console.log(readFileSync(fileURLToPath(import.meta.url), 'utf8').split('\n').slice(1, 16).map(l => l.replace(/^\/\/ ?/, '')).join('\n'))
  process.exit(target || user ? 0 : 1)
}

const projectRoot = user ? null : resolve(target)
if (projectRoot && (!existsSync(projectRoot) || !statSync(projectRoot).isDirectory())) {
  console.error(`Not a folder: ${projectRoot}`)
  process.exit(1)
}
const destClaude = user ? join(homedir(), '.claude') : join(projectRoot, '.claude')
const files = [...manifest.files, ...(flag('--no-tests') || user ? [] : manifest.test_files)]
  .filter(f => !(user && (f === 'bughunt-install.mjs'))) // the installer stays with the kit source for user installs

const summary = { added: [], updated: [], kept: [], unchanged: [], config: [] }
const write = (path, content) => { if (!dry) { mkdirSync(dirname(path), { recursive: true }); writeFileSync(path, content) } }

for (const rel of files) {
  const src = join(kitDir, rel)
  const dest = join(destClaude, rel)
  if (resolve(src) === resolve(dest)) { summary.unchanged.push(rel); continue }
  if (!existsSync(src)) { console.error(`Kit file missing from the source: ${rel}`); process.exit(1) }
  if (!existsSync(dest)) {
    if (!dry) { mkdirSync(dirname(dest), { recursive: true }); copyFileSync(src, dest) }
    summary.added.push(rel)
  } else if (readFileSync(src).equals(readFileSync(dest))) {
    summary.unchanged.push(rel)
  } else if (flag('--force')) {
    if (!dry) copyFileSync(src, dest)
    summary.updated.push(rel)
  } else {
    summary.kept.push(rel)
  }
  if (!dry && /\.(sh|mjs)$/.test(rel) && existsSync(dest)) { try { chmodSync(dest, 0o755) } catch {} }
}

function mergeJson(path, mutate, label) {
  let data = {}
  if (existsSync(path)) {
    try { data = JSON.parse(readFileSync(path, 'utf8')) } catch {
      console.error(`Could not read ${path} as JSON; left unchanged. Add the ${label} entry by hand (see .claude/BUGHUNT.md).`)
      return
    }
  }
  const before = JSON.stringify(data)
  mutate(data)
  if (JSON.stringify(data) !== before) { write(path, JSON.stringify(data, null, 2) + '\n'); summary.config.push(`${label} (${path})`) }
}

if (!user) {
  // Keep credentials and browser scratch files out of git.
  const gi = join(projectRoot, '.gitignore')
  const current = existsSync(gi) ? readFileSync(gi, 'utf8') : ''
  const lines = ['.bughunt/.auth/', '.bughunt/.mcp-output/'].filter(l => !current.split(/\r?\n/).includes(l))
  if (lines.length) {
    write(gi, `${current}${current && !current.endsWith('\n') ? '\n' : ''}# bughunt kit: never commit credentials or browser scratch files\n${lines.join('\n')}\n`)
    summary.config.push(`git-ignored ${lines.join(', ')}`)
  }
  if (flag('--with-ux')) {
    mergeJson(join(projectRoot, '.mcp.json'), d => {
      d.mcpServers = d.mcpServers || {}
      if (!d.mcpServers['bughunt-browser']) d.mcpServers['bughunt-browser'] = { command: 'node', args: ['.claude/skills/uxcheck/browser-server.mjs'] }
    }, 'browser server "bughunt-browser" registered')
    mergeJson(join(destClaude, 'settings.json'), d => {
      const list = Array.isArray(d.enabledMcpjsonServers) ? d.enabledMcpjsonServers : []
      if (!list.includes('bughunt-browser')) d.enabledMcpjsonServers = [...list, 'bughunt-browser']
    }, 'browser server enabled')
  }
}

const show = (title, list) => { if (list.length) console.log(`${title} (${list.length}):\n  ${list.join('\n  ')}`) }
console.log(`${dry ? '[dry run] ' : ''}bughunt kit ${manifest.version} -> ${destClaude}`)
show('Added', summary.added)
show('Updated (--force)', summary.updated)
show('Kept your changed version (use --force to replace)', summary.kept)
console.log(`Unchanged: ${summary.unchanged.length}`)
show('Configuration', summary.config)
if (user && flag('--with-ux')) {
  console.log(`\nFor /uxcheck in every project, register the browser server once:\n  claude mcp add --scope user bughunt-browser -- node ${join(destClaude, 'skills', 'uxcheck', 'browser-server.mjs')}`)
}
console.log('\nStart a new Claude Code session so the agents, skills, workflows and browser server load.')
if (flag('--with-ux')) console.log('For apps that need sign-in, set BUGHUNT_UX_USER and BUGHUNT_UX_PASSWORD (or BUGHUNT_UX_STORAGE_STATE) as environment secrets first.')

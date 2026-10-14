// Offline harness: runs a workflow script with mocked agent()/parallel()/pipeline().
import { readFileSync } from 'node:fs'

const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor

export async function runWorkflow(path, args, mockAgent, { budget = { total: null, spent: () => 0, remaining: () => Infinity } } = {}) {
  const src = readFileSync(path, 'utf8').replace(/^export const meta/m, 'const meta')
  const calls = []
  const logs = []
  let active = 0, peak = 0
  const agent = async (prompt, opts = {}) => {
    calls.push({ prompt, opts })
    active++; peak = Math.max(peak, active)
    await new Promise(r => setTimeout(r, 1 + (calls.length % 5)))
    try { return await mockAgent(prompt, opts, calls.length) } finally { active-- }
  }
  const parallel = thunks => Promise.all(thunks.map(t => Promise.resolve().then(t).catch(() => null)))
  const pipeline = (items, ...stages) => Promise.all(items.map(async (it, i) => {
    let v = it
    for (const s of stages) { try { v = await s(v, it, i) } catch (e) { console.error('stage threw:', e); return null } }
    return v
  }))
  const fn = new AsyncFunction('agent', 'parallel', 'pipeline', 'log', 'phase', 'args', 'budget', 'workflow', src)
  const result = await fn(agent, parallel, pipeline, m => logs.push(m), () => {}, args, budget, async () => { throw new Error('nested workflow not mocked') })
  return { result, calls, logs, peak }
}

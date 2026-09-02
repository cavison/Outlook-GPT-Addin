import { Game, levelFromXp } from '../server/game.js';

// These lock down the one rule that makes the scoring worth having: XP is paid
// for interventions, never for uptime. If a future change starts paying for
// "still healthy", these fail.

const entity = (id, status) => ({ id, name: id, district: 'D', status });

let pass = 0;
let fail = 0;

function check(label, actual, expected) {
  const ok = JSON.stringify(actual) === JSON.stringify(expected);
  if (ok) {
    pass++;
    console.log(`  ok   ${label}`);
  } else {
    fail++;
    console.log(`  FAIL ${label}\n       got ${JSON.stringify(actual)}\n       want ${JSON.stringify(expected)}`);
  }
}

/** A Game with a clean slate — avoids inheriting whatever is in data/game.json. */
function freshGame() {
  const g = new Game();
  g.state = {
    ...g.state,
    xp: 0,
    streak: 0,
    incidents: {},
    history: [],
    events: [],
    totals: { resolved: 0, selfHealed: 0, actions: 0, acknowledged: 0 },
  };
  g.save = () => {}; // never touch disk from a test
  return g;
}

console.log('scoring');

{
  const g = freshGame();
  g.reconcile([entity('a', 'failed')]);
  g.reconcile([entity('a', 'healthy')]);
  check('self-healed incident earns token XP only', g.state.xp, 5);
  check('self-healed incident is not counted as resolved', g.state.totals, {
    resolved: 0, selfHealed: 1, actions: 0, acknowledged: 0,
  });
}

{
  const g = freshGame();
  g.reconcile([entity('b', 'failed')]);
  g.acknowledge('b', 'b');
  g.reconcile([entity('b', 'healthy')]);
  check('acknowledged then recovered = 10 + 40 + 30 rapid bonus', g.state.xp, 80);
  check('counted as a real resolution', g.state.totals.resolved, 1);
}

{
  const g = freshGame();
  g.reconcile([entity('c', 'failed')]);
  g.state.incidents.c.openedAt = Date.now() - 60 * 60 * 1000; // an hour old
  g.acknowledge('c', 'c');
  g.reconcile([entity('c', 'healthy')]);
  check('slow resolution earns no rapid-response bonus', g.state.xp, 50);
}

{
  const g = freshGame();
  for (let i = 0; i < 50; i++) {
    g.reconcile([entity('d', 'healthy'), entity('e', 'running')]);
  }
  check('50 polls of pure uptime pay zero XP', g.state.xp, 0);
}

{
  const g = freshGame();
  g.reconcile([entity('f', 'failed')]);
  g.reconcile([]); // entity deleted from the tenant
  check('a vanished entity pays nothing', g.state.xp, 0);
  check('a vanished entity leaves no open incident', Object.keys(g.state.incidents), []);
}

console.log('incident adoption');

{
  const g = freshGame();
  // Simulates a restart into an already-failing world: no transition ever fires,
  // so only reconcile() can open the incident.
  g.reconcile([entity('g', 'failed')]);
  check('pre-existing failure opens an incident', Object.keys(g.state.incidents), ['g']);
  check('and can be acknowledged', g.acknowledge('g', 'g'), { ok: true });
}

console.log('progression');

{
  check('level curve steps at the right thresholds', [
    levelFromXp(0).level,
    levelFromXp(99).level,
    levelFromXp(100).level,
    levelFromXp(500).level,
  ], [1, 1, 2, 4]);
}

{
  const g = freshGame();
  g.reconcile([entity('h', 'failed')]);
  g.acknowledge('h', 'h');
  g.reconcile([entity('h', 'healthy')]);
  const quest = g.state.quests.items.find((q) => q.id === 'resolve');
  check('resolving advances the daily quest', quest.progress, 1);
}

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);

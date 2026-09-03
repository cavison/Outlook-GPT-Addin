import { planLayout, auditPlan } from '../server/layout.js';

// The separation rule is the whole reason this planner exists, so it is the
// thing worth locking down: two regionals' books must never share an edge.

let pass = 0;
let fail = 0;
const check = (label, ok, detail = '') => {
  if (ok) { pass++; console.log(`  ok   ${label}`); }
  else { fail++; console.log(`  FAIL ${label}${detail ? ` — ${detail}` : ''}`); }
};

function makePortfolio(sizes) {
  const districts = [{ name: 'Town Centre', group: null }];
  for (const [region, n] of Object.entries(sizes)) {
    for (let i = 0; i < n; i++) districts.push({ name: `${region}-${i}`, group: region });
  }
  return districts;
}

console.log('layout separation');

{
  const districts = makePortfolio({ A: 50, B: 44, C: 56, D: 28, E: 8 });
  const plan = planLayout(districts, { townDistrict: 'Town Centre' });
  const report = auditPlan(districts, plan);

  check('every property gets a hex', plan.byDistrict.size, districts.length);
  check('town centre reserves ten hexes', plan.town.length === 10);

  const touching = report.reduce((n, r) => n + r.adjacentToOtherRegions, 0);
  check('no hex touches another regional', touching === 0, `${touching} adjacencies`);

  const worst = Math.min(...report.map((r) => r.contiguity));
  check('every book stays contiguous', worst >= 0.85, `worst ${Math.round(worst * 100)}%`);
}

{
  // A lopsided portfolio is the case most likely to box a small book in.
  const districts = makePortfolio({ Big: 120, Tiny: 2, Small: 5 });
  const plan = planLayout(districts, { townDistrict: 'Town Centre' });
  const report = auditPlan(districts, plan);
  check('lopsided portfolio still places everything', plan.byDistrict.size === districts.length);
  check('lopsided portfolio keeps books apart',
    report.reduce((n, r) => n + r.adjacentToOtherRegions, 0) === 0);
}

{
  const districts = makePortfolio({ Solo: 1 });
  const plan = planLayout(districts, { townDistrict: 'Town Centre' });
  check('a single property still lands somewhere', plan.byDistrict.has('Solo-0'));
  const c = plan.byDistrict.get('Solo-0');
  check('and not on top of the town centre',
    !plan.town.some((t) => t.q === c.q && t.r === c.r));
}

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);

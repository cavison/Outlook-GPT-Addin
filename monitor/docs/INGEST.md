# Getting data onto the map

Every KPI on every hex arrives the same way, whatever produced it. This
document is the contract.

There is one format, one validator and one store. A monthly spreadsheet, a
nightly signage agent and a Power Automate flow all go through the same door, so
no source gets a privileged path that skips the checks — and swapping how a KPI
is collected never touches the renderer.

---

## The two files you edit

**`config/kpis.json`** — what the city measures and where each measurement
stands. Tracked in git; it holds no business data.

**`data/measurements/<kpi-id>.json`** — the readings. Gitignored. You do not
write these by hand; the importer, the CLI and the HTTP endpoint write them.

---

## The batch

One batch is **one KPI across many properties, taken at one moment**.

```json
{
  "kpi": "signage-online",
  "asOf": "2026-09-08T06:00:00Z",
  "source": "signage vendor API",
  "rows": [
    { "property": "0175 IV Aurora", "value": 4, "total": 4 },
    { "property": "0200 IV Avon Lake", "value": 2, "total": 4, "note": "lobby + bistro dark" },
    { "property": "0312 StoryPoint Bath", "applicable": false, "note": "no screens installed" }
  ]
}
```

| Field | Meaning |
|---|---|
| `kpi` | An id from `config/kpis.json`. An unknown id is rejected — register it first. |
| `asOf` | When the readings were taken. **Not** when you imported them: loading July's numbers in October must not make them look like October's. |
| `source` | Free text for the audit trail. It shows on the detail card. |
| `rows[].property` | Must match the property name on the map exactly. |
| `rows[].value` | Shape depends on the KPI's kind — see below. |
| `rows[].applicable` | `false` means *we don't do this here*. Scored as neither pass nor fail. |
| `rows[].note` | Shown on hover. Use it: "lobby + bistro dark" is worth more than a number. |
| `rows[].url` | Optional deep link to the thing that needs fixing. |

`property` names must match, and a name that isn't on the roster is silently
skipped rather than inventing a property. Run
`node scripts/ingest.mjs --list` to see every registered KPI and the columns it
expects.

### Kinds

Which numbers a row carries depends on the KPI's `kind`. Four shapes cover
everything on the list; each turns into pillar height its own way, and all four
end up as one number between 0 (fine, flat) and 1 (as bad as this KPI gets).

| Kind | Row carries | Height means |
|---|---|---|
| `variance` | `value` (= budget − actual, so **negative is overspent**), optionally `budget` and `actual` | How far over, scaled against the 90th percentile of this line's own unfavourable readings |
| `ratio` | `value` and `total` (4 screens online out of 5) | Shortfall against target. `total: 0` = nothing to report here |
| `count` | `value`, optionally `target` | Miss against target, in the KPI's `direction` (`at-least` or `at-most`) |
| `boolean` | `value` — `true`/`yes`/`1`/`done` or `false`/`no`/`0`/`missing` | Not done = full height |
| `label` | `value` (text) | Nothing. It has no parcel; it shows on the roster and the detail card. The Life Enrichment Director is one of these. |

Why not one formula: money variance, a ratio of screens, a count of requests and
a yes/no submission are four different questions. Forcing them through one
scaling makes at least three of them lie. What they *can* share is the output,
and that is what makes a hex readable — every pillar answers "how bad", so
payroll dollars and a missing menu upload stand comparably tall.

---

## Three ways in

### 1. The monthly workbook

```
node scripts/import-financials.mjs "Jul YTD Actuals vs Budget.xlsx" --as-of 2026-07-31
```

Reads the Dashboard Data tab and writes one batch per budget line named by
`workbookLine` in the registry. It also refreshes the property roster and the
regional names into `data/portfolio.local.json`.

It stops rather than half-succeeding if the account names have changed, if a
merge in `data/merges.json` names a property that isn't in the workbook, or if
the variance sign convention has flipped.

### 2. A file — CSV, JSON or a spreadsheet

```
node scripts/ingest.mjs signage-online screens.csv --source "signage vendor export"
node scripts/ingest.mjs menu-upload menus.xlsx --sheet "September" --as-of 2026-09-01
node scripts/ingest.mjs --list
node scripts/ingest.mjs food-service-requests requests.csv --dry-run
```

Column names are matched loosely — `Property`, `Community`, `Community Name` and
`Site` all work for the property column; `Value`, `Count`, `Online`, `Completed`
and `Done` all work for the value. `$` signs, thousands separators and
`(1,234)`-style negatives are cleaned up. `--dry-run` validates and prints the
distribution without writing.

This is the path to use for anything a person exports by hand, and the path a
scheduled agent should use if it runs on the same machine.

### 3. HTTP — for Power Automate and anything remote

```
POST http://localhost:4310/api/ingest
Content-Type: application/json
X-Ingest-Token: <INGEST_TOKEN, if set>

{ "kpi": "interest-assessments", "asOf": "...", "source": "Power Automate", "rows": [...] }
```

Post one batch or an array of them; a push that gathers three KPIs in one run
should send all three together. **All or nothing** — if any batch fails
validation, nothing is written and the response lists what was wrong. On success
the map refreshes immediately rather than waiting for the next poll.

`GET /api/kpis` returns the registry, so a flow can check what the map expects
before it builds a payload.

#### The Power Automate shape

The flow only has to do three things:

1. **Trigger** on your cadence — Recurrence for daily/weekly checks, or an item
   trigger on the SharePoint list or Dataverse table that holds the source.
2. **Select** the source rows into the batch shape. One `Select` action, mapping
   your columns to `property` / `value` / `total`.
3. **HTTP POST** the batch.

```
Compose  batch:
{
  "kpi": "interest-assessments",
  "asOf": "@{utcNow()}",
  "source": "Power Automate: @{workflow()['name']}",
  "rows": @{body('Select_rows')}
}
```

Send the whole portfolio in one call, not one call per property: a batch is a
snapshot, and 185 separate posts would leave the map in 185 intermediate states.

**Reaching a machine that isn't in the cloud.** The server binds to localhost, so
a cloud-hosted flow cannot reach it directly. Three options, in the order I'd
try them:

- **Write to the shared OneDrive folder instead.** The flow drops a JSON or CSV
  file; a scheduled task on the machine runs `scripts/ingest.mjs` against it.
  This is the option that also works for the eventual "share it with my team"
  plan, because everyone's copy reads the same folder.
- **An on-premises data gateway**, if your tenant already has one.
- **A tunnel** (Dev Tunnels, Cloudflare, ngrok). If you do this, set
  `INGEST_TOKEN` in `.env` first and send it as `X-Ingest-Token`. An
  unauthenticated writer could otherwise quietly turn every KPI green, which is
  a worse failure than no data at all.

---

## What "no data" looks like, and why there are four kinds

The whole point of this map is that a broken feed cannot hide. So the four ways
a parcel can have nothing on it are four *different* objects:

| On the hex | Means |
|---|---|
| A flat green pillar | Reported, and fine |
| A small paved lot | `applicable: false` — a real answer, scored as neither |
| A faint marked-out circle, nothing built | Registered in `kpis.json`, never connected. Ground held for it |
| A **fenced plot with a marker post** | It *was* reporting and stopped, or the last batch skipped this property |

Only the last one is a problem, and it is the one that gets a beacon.

A reading also expires. Past its cadence window — `realtime` 1 day, `daily` 3,
`weekly` 10, `monthly` 45, `quarterly` 120 — the parcel goes back to a fenced
plot rather than showing a stale value forever. A KPI that stopped reporting in
March and still shows March's green is the exact failure this design exists to
prevent, so believing an old number is never the safe default.

---

## Adding a KPI

1. Add it to `config/kpis.json` with the **next vacant parcel number**. Never
   renumber and never reuse: position 10 is signage on every property forever,
   and that positional consistency is what lets you read a hex without a legend.
2. Pick the `kind` that matches the question, and set a real `target`. The
   targets currently in the file marked PLACEHOLDER are guesses.
3. Point a feed at it by any of the three routes above.

No code changes. The pillar, the legend entry, the roster column, the filter and
the detail card all come from the registry.

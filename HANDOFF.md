# Cottage Services Project — handoff to a local session

Written 18 Sep 2026 by the cloud session `session_014soNX6WqDmiQFChqL6urRE`
(started from iOS, so it never had access to the local OneDrive folder).
Everything needed to continue is in this repo or linked below.

---

## 1. Who and what

**Owner:** Curtis Avison. Building a cottage / villa service benchmark to decide
what services to offer cottage residents at Good / Better / Best tiers, and to
brief owners and internal service leaders.

**Function owners:**

| Function | Owner | State |
|---|---|---|
| Transportation | Curtis Avison (Life Enrichment) | Structure + terms confirmed by owner, 18 Sep |
| Life Enrichment | Curtis Avison | Structure + terms confirmed by owner, 18 Sep |
| Culinary | Kevin Penn | Confirmed on the 17 Sep call; Best only partly agreed |
| Settings: Housekeeping | Justin Hollabaugh | Confirmed through Better; Best NOT agreed |
| Settings: Maintenance | Justin Hollabaugh | Owner assigned 18 Sep; terms never put to him |

**Local files (on Curtis's machine, not in this repo):**
`C:\Users\cavis\OneDrive - Common Sail\SyncFile_Yoga\Cottage_ServicesOffered_Project\`
- `Cottage Master Workbook 9-18-26.xlsx` — his merged master workbook

---

## 2. Immediate next task

Replace the `Service Grid (MIM)` tab in the master workbook with the rebuilt
20-row version in this repo:

- Source: `Service_Grid_MIM_2026-09-18.xlsx` (single sheet, ready to copy)
- Keep tab position, delete the old 17-row tab, save in place

Then continue the function-by-function review. **Curtis got to the start of
Culinary.** Transportation and Life Enrichment are done.

---

## 3. Files in this repo

| Path | What |
|---|---|
| `Cottage_Villa_Service_Benchmark.xlsx` | 10-tab benchmark workbook, Service Grid already rebuilt |
| `Service_Grid_MIM_2026-09-18.xlsx` | The rebuilt tab alone, for merging into the master |
| `build/rebuild_service_grid.py` | Regenerates the Service Grid tab; edit the `GRID` list and re-run |
| `drills/drills.html` | The published teach-and-drill artifact |
| `drills/build/` | Its generators, per-operator dossiers, and the source table |

Workbook tabs: Start Here, Talking Points, Consolidated Data, Synthesis,
Good-Better-Best, **Service Grid (MIM)**, Service Elements, Service Docs Linear,
Transportation Detail, Sources & Method.

**Two artifacts (live, owner's account):**
- Tier worksheet (fillable, saves to its own database): https://claude.ai/artifact/LexeCCo7Hk7M4XmBWoReH5
- Drills / briefing game: https://claude.ai/artifact/R7csWbtpNZB6nzpxeipvC9

---

## 4. The priority ladder

The spine of Transportation and Life Enrichment. Good and Best are mirror images.

| Level | Who has priority |
|---|---|
| **N/A** | No programme, no involvement |
| **GOOD** | Main building first. The service already exists; cottage residents are invited in on a space-available basis, as the second priority |
| **BETTER** | Equal consideration. One shared sign-up pool, no priority either way |
| **BEST** | Cottage residents first. Built for them, run separately. The property may invite main-building residents in, never required |

`N/A` is a level on all five functions. `MIM = Yes` on all twenty options — every
new cottage resident is met by the team regardless of tier, including at N/A.

---

## 5. Decisions made 18 Sep (owner: Curtis)

**Transportation**
- Good: no guaranteed seat floor, deliberately. No cap either — cottage residents
  simply never hold priority over main-building residents.
- Good: no personal appointments. Coordination only (rideshare, county transit).
- Better: equal footing on outings; personal appointments purchasable.
- Best: dedicated cottage shuttle; cottage-first outings; appointments included
  at no cost to the resident.
- Best: where no shuttle or driver is available, the community may outsource to a
  contracted transportation partner.
- Radius: each community's existing defined radius. Does not change.
- Wait time: 1 hour included, additional time purchasable in 30-minute blocks.
- Pricing shape: flat base fare plus 30-minute increments. **Fare TBD.**
- "Airport runs" struck from the vocabulary entirely.

**Life Enrichment**
- N/A means no campus to access (a standalone cluster with no main building) —
  never "campus exists, access withheld".
- Good: full calendar, fitness centre and campus amenity access on the same basis
  as apartment residents, plus inclusion in the bi-annual community events.
  Outings are the exception and follow the Transportation Good rule.
- Better: equal standing, plus a resident-run cottage layer — a monthly planning
  meeting, one monthly cottage happy hour hosted by an LE team member, and a
  cottage calendar that staff build from what residents are already doing.
- Better: no dedicated liaison. ~4 hrs/wk (16 hrs/month) of LE team time.
- Best: a full cottage programme, 20–40 hrs/wk, delivered by a **Cottage Lead**.
  Separate programming and outings. Main building may be invited in, optionally.
- Best: **no enrichment credit** — that concept was removed by the owner.
- An outing sits in both functions: LE owns the event, Transportation owns the
  seat. Seats are capped by the vehicle.

---

## 6. Open items

1. **Housekeeping at Better and Best: in the fee, or purchased?** The market
   includes it 87% of the time; Justin frames it as purchased. Biggest open item.
2. **What separates a property into N/A / Good / Better / Best?** The staffing
   column is the raw material — a property qualifies for a level when it has
   those hours and assets. Recommended: two fields per property per function,
   a capability ceiling (owner-set) and a selected level (business choice,
   may sit below the ceiling).
3. **Transportation Best: is the contracted-partner fallback capped?** Included
   at no cost to the resident means the community absorbs the invoice, and the
   spend is driven by resident demand rather than our capacity.
4. **Culinary Best: pursue a limited included meal at all?** Kevin offered one
   meal a week staggered (4:12) and resisted daily inclusion.
5. **Pricing units.** Housekeeping (per sq ft / hour / visit) and the
   transportation fare are both unset.
6. **Cottage Lead 20 vs 40 hrs/wk** — no threshold set. A 2x range cannot be priced.
7. **LE Better: 4 hrs/wk vs 16 hrs/month** — 4 hrs/wk is 17.3 hrs/month. Reconcile.
8. **MIM at LE N/A** — if there is no LE presence, name who runs the move-in meeting.
9. **Maintenance terms have never been put to Justin.** Do the four housekeeping
   conditions apply to maintenance too?
10. **Per-transaction resident billing** is a shared dependency: Transportation
    Better, Culinary Good and Better, and Housekeeping Good and Better all need it.

---

## 7. Rules that must not be broken

- **Never invent a quote, a figure, or a source.** Curtis has to be able to go
  back to anyone and point at what they actually said.
- Call quotes by speaker and timestamp. The call is "Connect - cottage services",
  17 Sep 2026, 16m 48s. Kevin Penn (culinary), Justin Hollabaugh (settings),
  Curtis Avison.
- **Cite Kevin 11:42 on delivery, not 3:31.** He said early he would deliver,
  then reversed. The later position is the real one.
- These figures are NOT agreed rates: 25¢/sq ft (Justin 8:36, "we might say"),
  $40–50/hour (Curtis's own illustration, 15:07), one FTE a day / extra 8 hours a
  week (Curtis), Cottage Lead 20–40 hrs (owner proposal), the transportation fare.
- Market claims carry a status: verified / likely / falsified. Two of our own
  conclusions were reversed during verification and four fabricated directory
  details were removed. Do not reintroduce them.
- Directory sites publish AI-generated pseudo-detail. The reliable check is an
  exact-phrase search restricted to the operator's own domain.

---

## 8. Market facts worth having to hand

Laura Lopez's inventory: **215 cottage/villa communities**, mostly Midwest.
Consolidated with three other internal sources into 230 rows.

| Function | Mentions | Included |
|---|---|---|
| Maintenance | 103 of 215 | 99% — exactly one community prices it separately |
| Housekeeping | 69 | 87% |
| Wellness | 60 | — only 5 offer anything clinical |
| Transportation | 55 | every entry is the bare word, no radius/hours/price |
| Life Enrichment | 54 | 96% |
| Culinary | 53 | 68% — delivery appears at 1 of 215 |

Median published monthly fee $2,800 (range $515–$6,900, n=54). 63 of 215 require
an entrance fee. **Zero of roughly fifty communities researched in depth publish a
price, radius, hours or booking lead time.**

Operator standards (aggregated, from the October 2023 listing research — no public
URLs captured for these four, so confirm before quoting externally):
- **Five Star** (5 communities): weekly housekeeping with flat linen 5/5, maintenance 5/5, 24/7 concierge 5/5, transportation 0/5
- **Trilogy** (8): housekeeping 8/8 bi-weekly or bi-monthly, maintenance 7/8, transportation 0/8, everything else sold as "available"
- **Arrow / Vitalia** (7): campus amenities and maintenance only; transportation, housekeeping and dining absent at all seven
- **ASC** (5): transportation 5/5, one verbatim corporate sentence — "shopping, restaurants and appointments" (exact-phrase verified)

---

## 9. Getting set up locally

```
git clone https://github.com/cavison/Outlook-GPT-Addin.git
cd Outlook-GPT-Addin
git checkout claude/senior-living-cottage-analysis-lvnrf1
```

Or if already cloned: `git pull origin claude/senior-living-cottage-analysis-lvnrf1`

Python needs `openpyxl`. LibreOffice is used to recalculate formulas after
openpyxl writes them (openpyxl writes formulas with no cached value).

**Always validate a generated workbook before handing it over** — a variable
shadowing bug once corrupted `styles.xml` and made Excel repair the file.

/* one boss round per chapter, keyed by chapter name. The operator chapters
   carry their own, defined with the chapter in OPCH. */
var CORE_BOSS={
"The Shape":{
  q:"Give me the thirty-second version. What did you look at, and what did you find?",
  say:"Two hundred and fifteen cottage and villa products, mostly Midwest, from four internal sources, consolidated into one workbook with the source named on every row. The headline is that there is no standard cottage service model — packages run from a garage and a washer-dryer to a fully bundled villa. What is consistent is that operators remove the work of owning a house: maintenance shows up at a hundred and three communities and is included at ninety-nine per cent of them. Everything above that floor is a choice, and three operators bracket the range.",
  ev:"215 communities, 230 consolidated rows, four internal sources. Maintenance 103 mentions, 99% included.",
  s:["agg_215","agg_nostd","agg_maint"]},
"The Six Functions":{
  q:"Everybody else includes housekeeping. Why are we selling it?",
  say:"That is the one place the market is ahead of us, and I would not pretend otherwise. Eighty-seven per cent of operators who mention housekeeping include it, and every multi-site operator in the study sets one cadence across its whole portfolio — Five Star weekly at all five, Trilogy bi-weekly at all eight, Life Enriching at all five but light. Our settings leader frames housekeeping as purchased, and Flourish is the live example of why bundling is hard: a proper clean runs two to four hours and he said plainly it has to change. So this is an open decision, not a settled one.",
  ev:"Housekeeping 87% included across 69 mentions. Justin Hollabaugh, 14:26 and 7:13.",
  s:["agg_hk","justin_alc","justin_flourish"]},
"Money":{
  q:"What differentiates us if we include less than everyone else?",
  say:"Publishing the terms. Across roughly fifty communities researched in depth, not one publishes a price for any paid service, and not one publishes a radius, hours or a booking lead time. The vocabulary is nominal, a small fee, at cost. The category sells a one-word amenity list — all fifty-five transportation entries in our inventory are literally just the word. If we publish what a resident actually gets, we differentiate on transparency at no operating cost, and only four communities anywhere have even published an included-versus-chargeable split.",
  ev:"Zero of about fifty communities publish a rate. Four publish an included-versus-chargeable split.",
  s:["research_noprice","laurel","garbry"]},
"The Tiers":{
  q:"So which tier do we actually launch with?",
  say:"Good everywhere, and Better only where the building supports it. Good is the maintenance-free floor: maintenance, grounds, a scheduled shuttle and full campus access, with everything else bought at a published price. Better adds a bundled mid-level package and, crucially, a published à la carte menu — at Better the menu is the product, because without one residents experience services as unavailable rather than optional. And the gate is physical, not financial: the dining room either seats the extra covers or it does not, and our settings leader said he cannot commit universally and would have to go community by community. So the honest answer is one floor everywhere and a tier that is gated per site.",
  ev:"Good-Better-Best tab, 30 tier rows. Justin Hollabaugh 15:17, Kevin Penn 16:01.",
  s:["gbb","gbb_menu","call_capacity","justin_4cond"]},
"What Our Leaders Said":{
  q:"What is the biggest risk in this plan?",
  say:"Staffing fragility on a spread-out site, and both leaders raised it independently. A cottage neighbourhood adds staff travel time for housekeeping, maintenance and emergency response, and if one dedicated person quits you are in a bind immediately. That argues for raised ratios across existing staff rather than a single dedicated role. The second risk is funding shape: census flows through per-resident-day, but labour is not calculated that way, so any service we add has to arrive with a staffing number attached or it will not happen. And I should flag that maintenance was never discussed as a separate service line on the call — that part is our proposal, not his commitment.",
  ev:"Justin Hollabaugh 12:58 and 13:26; Kevin Penn 13:57 and 2:13. Maintenance not confirmed as a separate line.",
  s:["call_capacity","kevin_labor","maint_open"]},
"What Not To Say":{
  q:"How confident are you in this research?",
  say:"Confident in the shape, careful about the specifics, and I can show you the difference. The internal data is as reported by our four sources. The market research was verified quote by quote with exact-phrase probes and searches restricted to the operator's own domain, and that process overturned two of our own conclusions and removed four fabricated details — one of them a directory quote naming a hospital that does not exist. Every market claim in the workbook now carries a status: verified, likely or falsified. Where I have the operator's own words I can put the page in front of you. Where a claim rests on our October listing research, I will say so rather than pretend there is a link.",
  ev:"Two-round verification programme. Four fabrications removed, two conclusions reversed and disclosed.",
  s:["verify_method","fabrications","verify_cottage"]}
};

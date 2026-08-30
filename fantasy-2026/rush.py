# Dual-threat test, graded on ABSOLUTE 2025 standing across all quarterbacks — not against a player's own past.
# Two gates, both required for the DUAL badge:
#   RUN  — top-5 among QBs in rushing attempts, rushing yards, or rushing yards per game (min 30 carries)
#   PASS — a real, regular passing workload (roughly 3,200+ yards over a full season, or the per-game rate of one)
# A player who clears RUN but not PASS gets the RUN badge instead, because he is a runner, not a dual threat.

KINDS = {
 "dual": ("Dual-threat", "Top-five rushing volume among all quarterbacks AND a full passing workload."),
 "run":  ("Runner, thin passer", "Clears the rushing bar, but the passing volume is not there yet."),
}

# name: (kind, evidence-for-the-tooltip, row-note)
RUSH = {
"Josh Allen":("dual","112 carries (1st), 579 rush yds (1st), 14 rush TD (1st), 36.2 rush yds/g (3rd)",
 "The complete profile: he led every quarterback in 2025 in rushing attempts, rushing yards and rushing touchdowns, on a full passing workload. Nobody else is close on all three."),
"Drake Maye":("dual","98 carries (3rd) with 4,394 pass yds (4th)",
 "Arguably the best dual-threat combination in football right now — third among QBs in carries while finishing fourth in the league in passing yards. Both halves, at volume."),
"Jalen Hurts":("dual","105 carries (2nd), 421 rush yds (5th), 8 rush TD, 3,224 pass yds",
 "Second among quarterbacks in carries and fifth in rushing yards, with the goal-line role attached, on a full 3,200-yard passing season."),
"Justin Herbert":("dual","83 carries (4th), 498 rush yds (2nd), 31.1 rush yds/g (5th), 3,727 pass yds (9th)",
 "Top-five in all three rushing categories and ninth in the league in passing yards. On the raw numbers this is a genuine dual threat, and he is the cheapest one on the board."),
"Jayden Daniels":("dual","39.7 rush yds/g (2nd), 8.3 carries/g — over 7 games",
 "Second among all quarterbacks in rushing yards per game, at a carry rate nobody else sustains. The caveat is sample: elbow, knee and ankle injuries held him to seven games, and his yards per carry fell from 6.0 to 4.8."),
"Patrick Mahomes":("dual","422 rush yds (4th), 30.1 rush yds/start, full passing workload",
 "Fourth among quarterbacks in rushing yards, which is more than the reputation carries. Price in the December knee surgery."),
"Caleb Williams":("dual","77 carries, 388 rush yds, 3 rush TD, 3,942 pass yds (7th)",
 "77 carries and 388 yards on the ground with the seventh-most passing yards in the league. A tier below the top on rushing volume, but both halves are real."),
"Lamar Jackson":("dual","The archetype — but 2025 was injury-marred with steep rushing decline",
 "The profile that defined the category, entering 2026 off a year with steep declines in both passing and rushing. A new coordinator is the bet, and the badge is on reputation plus history rather than 2025."),

"Jaxson Dart":("run","81 carries (5th), 455 rush yds (3rd), 9 rush TD, 35.0 rush yds/g (4th) — but only 2,272 pass yds",
 "Top-five in carries and third in rushing yards with nine rushing scores in 12 starts. The passing half is not there: 2,272 yards in 14 games, and the Giants are expected to be run-first again. Elite runner, not yet a dual threat."),
"Malik Willis":("run","60.0 rush yds/start — highest rate of any QB — on a small starting sample",
 "The highest rushing rate at the position by a distance, but on limited starts and without the passing volume to pair with it. Great rushing floor, thin everything else."),
}

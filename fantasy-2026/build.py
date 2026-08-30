import csv, json, math
from notes import NOTES
from sleepers import SLEEPERS
from rush import RUSH
from top150 import TOP150
import tail

board = [{"name":n,"pos":p,"team":t} for n,p,t in TOP150]

# weave the skill-position tail into a consensus-shaped order
scored = []
for i,(n,t) in enumerate(tail.WR_TAIL):  scored.append((151 + i*2.55, n,"WR",t))
for i,(n,t) in enumerate(tail.RB_TAIL):  scored.append((152 + i*3.15, n,"RB",t))
for i,(n,t) in enumerate(tail.TE_TAIL):  scored.append((157 + i*4.90, n,"TE",t))
for i,(n,t) in enumerate(tail.QB_TAIL):  scored.append((149 + i*7.60, n,"QB",t))
scored.sort(key=lambda r: r[0])
for _,n,p,t in scored:
    board.append({"name":n,"pos":p,"team":t})

for team in tail.DST:
    board.append({"name":team+" D/ST","pos":"DST","team":team})
for n,t in tail.K:
    board.append({"name":n,"pos":"K","team":t})

assert len(board) == 500, len(board)

posrank = {}
for i,p in enumerate(board, start=1):
    p["rank"] = i
    posrank[p["pos"]] = posrank.get(p["pos"],0)+1
    p["posrank"] = f'{p["pos"]}{posrank[p["pos"]]}'
    p["round12"] = f'Rd {math.ceil(i/12)}' if i <= 216 else 'Deep / waiver'
    p["confidence"] = "High" if i<=150 else ("Medium" if i<=300 else "Low")
    p["note"] = NOTES.get(p["name"],"")
    sl = SLEEPERS.get(p["name"])
    p["sleeper"], p["cost"], p["case"] = (sl[0], sl[1], sl[2]) if sl else ("","","")
    ru = RUSH.get(p["name"])
    p["rush"], p["rushstat"], p["rushnote"] = ru if ru else ("", "", "")

with open("rankings_2026_top500.csv","w",newline="") as f:
    w = csv.DictWriter(f, fieldnames=["rank","name","pos","posrank","team","round12","confidence","sleeper","cost","rush","note","case","rushstat","rushnote"])
    w.writeheader()
    for p in board: w.writerow(p)
json.dump(board, open("rankings_2026_top500.json","w"), indent=1)

from collections import Counter
print(Counter(p["pos"] for p in board))
miss=[n for n in SLEEPERS if n not in {p["name"] for p in board}]
print("sleepers not on board:",miss)
print("sleepers matched:",sum(1 for p in board if p["sleeper"]))
bad=[n for n in RUSH if n not in {p["name"] for p in board}]
print("rush names off board:",bad)
from collections import Counter as C2
print("rush badges:", C2(p["rush"] for p in board if p["rush"]))
for i in (1,12,24,36,60,90,120,150,180,220,300,380,440,500):
    p=board[i-1]; print(i, p["posrank"], p["name"], p["team"], p["confidence"])

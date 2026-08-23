# DRUG WARS EVO  v2.0
# A modern port of the 1994 TI-82 classic by Jonathan Maier,
# itself based on John E. Dell's 1984 "Drug Wars".
#
# Runs on: TI-84 Evo (Python app), TI-84 Plus CE Python, and desktop
# Python 3. Uses only text I/O plus the standard random module, so
# there is nothing to install and nothing calculator-specific that
# can fail. Persistence uses ti_system when present, a file when not,
# and degrades to memory-only if neither works.

import random

# ---------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------

VERSION = "2.0"
W = 32              # console width; safe on both Evo and CE Python
THEME = "classic"   # "classic" or "spice"

THEMES = {
    "classic": {
        "title": "DRUG WARS",
        "goods": ["Cocaine", "Heroin", "Acid", "Weed", "Speed", "Ludes"],
        "coat": "Coat",
        "law": "Officers",
        "bust": "BUSTED!",
        "dealer": "A dealer",
    },
    "spice": {
        "title": "SPICE WARS",
        "goods": ["Saffron", "Truffle", "Caviar", "Vanilla", "Pepper", "Salt"],
        "coat": "Cart",
        "law": "Inspectors",
        "bust": "RAIDED!",
        "dealer": "A trader",
    },
}

# Price bands lifted from the original TI-BASIC source.
BANDS = [
    (16000, 28000),
    (5000, 12000),
    (1000, 4400),
    (330, 750),
    (70, 220),
    (10, 50),
]

CITIES = ["Bronx", "Ghetto", "Central Pk", "Manhattan", "Coney Is", "Brooklyn"]

# Per city: (price bias, heat). Bias tilts the whole market, heat
# drives police attention. This is new -- the original treated every
# location identically, which made travel a coin flip.
CITY_BIAS = [1.00, 0.88, 1.05, 1.18, 0.95, 0.98]
CITY_HEAT = [1.10, 1.35, 0.70, 1.00, 0.75, 0.95]

DIFFS = {
    1: ("Rookie", 3000, 4000, 0.07, 0.04, 0.70, 100),
    2: ("Classic", 2000, 5000, 0.10, 0.06, 1.00, 100),
    3: ("Kingpin", 1500, 7500, 0.14, 0.05, 1.40, 80),
}
# name, cash, debt, debt rate, bank rate, heat mult, start HP

DAYS = 31
SAVE_VER = 2

# ---------------------------------------------------------------
# STATE
# ---------------------------------------------------------------

G = {}


def new_game(diff):
    d = DIFFS[diff]
    G.clear()
    G.update({
        "diff": diff,
        "day": 1,
        "cash": d[1],
        "debt": d[2],
        "bank": 0,
        "coat": 100,
        "loc": 0,
        "hp": d[6],
        "maxhp": d[6],
        "guns": 0,
        "inv": [0] * 6,
        "cost": [0] * 6,      # average unit cost, for the P&L readout
        "price": [0] * 6,
        "last": [0] * 6,      # yesterday's prices, for trend arrows
        "peak": 0,
        "busts": 0,
        "won": 0,
        "dead": 0,
        "rumor": -1,
        "rumorg": -1,
        "seen": 0,
    })
    roll_market(True)


# ---------------------------------------------------------------
# I/O HELPERS
#
# Every read goes through ask(). The simulator swaps this out to
# drive thousands of games headlessly, which is how the balance
# numbers below got checked.
# ---------------------------------------------------------------

def cls():
    try:
        import ti_system
        ti_system.disp_clr()
        return
    except Exception:
        pass
    print("\n" * 3)


def rule(ch="="):
    print(ch * W)


def pad(s, n):
    s = str(s)
    if len(s) >= n:
        return s[:n]
    return s + " " * (n - len(s))


def rpad(s, n):
    s = str(s)
    if len(s) >= n:
        return s[:n]
    return " " * (n - len(s)) + s


def money(n):
    n = int(n)
    neg = n < 0
    s = str(abs(n))
    out = ""
    while len(s) > 3:
        out = "," + s[-3:] + out
        s = s[:-3]
    out = s + out
    return ("-$" if neg else "$") + out


def ask(prompt):
    try:
        return input(prompt)
    except EOFError:
        return "q"


def ask_choice(prompt, valid):
    while True:
        r = ask(prompt).strip().lower()
        if r in valid:
            return r
        print("  ? try: " + "/".join(valid))


def ask_num(prompt, lo, hi):
    # Accepts "max"/"m"/"a" for the largest legal amount, which on a
    # calculator keypad saves a lot of typing.
    while True:
        r = ask(prompt).strip().lower()
        if r in ("", "0", "q", "x"):
            return 0
        if r in ("max", "m", "a", "all"):
            return hi
        try:
            v = int(float(r))
        except Exception:
            print("  ? number, or M for max")
            continue
        if v < lo or v > hi:
            print("  ? " + str(lo) + "-" + str(hi))
            continue
        return v


def pause():
    ask("  [enter]")


def banner(text):
    rule()
    print(" " + text)
    rule()


# ---------------------------------------------------------------
# MARKET
# ---------------------------------------------------------------

def roll_market(first=False):
    G["last"] = G["price"][:]
    bias = CITY_BIAS[G["loc"]]
    for i in range(6):
        lo, hi = BANDS[i]
        p = random.randint(lo, hi) * bias
        # Crashes and spikes are the whole game -- these are what you
        # are travelling to find.
        r = random.randint(1, 100)
        if r <= 7:
            p = p * random.uniform(0.20, 0.40)     # crash: load up
        elif r <= 14:
            p = p * random.uniform(2.2, 4.0)       # spike: cash out
        elif r <= 22:
            p = 0                                  # unavailable today
        G["price"][i] = int(p)
    # Never leave the player with a completely dead market.
    if not any(G["price"]):
        G["price"][5] = random.randint(*BANDS[5])


def trend(i):
    a, b = G["last"][i], G["price"][i]
    if not a or not b:
        return " "
    if b > a * 1.35:
        return "^"
    if b < a * 0.74:
        return "v"
    return " "


def carried():
    return sum(G["inv"])


def stock_value():
    return sum(G["inv"][i] * G["price"][i] for i in range(6))


def goods():
    return THEMES[THEME]["goods"]


# ---------------------------------------------------------------
# SCREENS
# ---------------------------------------------------------------

def show_status():
    t = THEMES[THEME]
    cls()
    rule()
    print(" " + pad(t["title"], 14) + rpad("Day " + str(G["day"]) + "/" + str(DAYS), 16))
    print(" " + pad(CITIES[G["loc"]], 14) + rpad(money(G["cash"]), 16))
    line = " " + t["coat"] + " " + str(carried()) + "/" + str(G["coat"])
    line = pad(line, 15) + "HP " + str(G["hp"])
    if G["guns"]:
        line = line + "  x" + str(G["guns"])
    print(line)
    rule()


def show_market():
    print(" #  " + pad("ITEM", 9) + rpad("PRICE", 9) + rpad("HAVE", 6))
    for i in range(6):
        p = G["price"][i]
        ps = money(p) if p else "--"
        have = G["inv"][i]
        print(" " + str(i + 1) + trend(i) + " " + pad(goods()[i], 9) +
              rpad(ps, 9) + rpad(str(have) if have else "", 6))
    rule("-")
    if G["debt"]:
        print(" Debt " + money(G["debt"]) + "   Bank " + money(G["bank"]))
    else:
        print(" Bank " + money(G["bank"]))
    if G["rumor"] >= 0:
        print(" Word is " + goods()[G["rumorg"]] + " is")
        print("  moving in " + CITIES[G["rumor"]] + ".")
    rule("-")


# ---------------------------------------------------------------
# TRADING
# ---------------------------------------------------------------

def do_buy():
    live = [i for i in range(6) if G["price"][i] > 0]
    if not live:
        print(" Nothing for sale today.")
        pause()
        return
    r = ask(" Buy which # (enter=back)? ").strip()
    if not r.isdigit():
        return
    i = int(r) - 1
    if i < 0 or i > 5 or G["price"][i] <= 0:
        print(" Not available.")
        pause()
        return
    p = G["price"][i]
    room = G["coat"] - carried()
    afford = G["cash"] // p
    top = min(room, afford)
    if top <= 0:
        print(" No " + ("room" if room <= 0 else "cash") + ".")
        pause()
        return
    print(" " + goods()[i] + " at " + money(p))
    print(" Room " + str(room) + ", can afford " + str(afford))
    n = ask_num(" How many (M=max)? ", 1, top)
    if n <= 0:
        return
    spend = n * p
    # Weighted average cost, so the sell screen can show real P&L.
    held = G["inv"][i]
    G["cost"][i] = int((G["cost"][i] * held + spend) / (held + n))
    G["inv"][i] += n
    G["cash"] -= spend
    print(" Bought " + str(n) + " for " + money(spend))
    pause()


def do_sell():
    if carried() <= 0:
        print(" You're carrying nothing.")
        pause()
        return
    r = ask(" Sell which # (enter=back)? ").strip()
    if not r.isdigit():
        return
    i = int(r) - 1
    if i < 0 or i > 5:
        return
    if G["inv"][i] <= 0:
        print(" None held.")
        pause()
        return
    if G["price"][i] <= 0:
        print(" No buyers here today.")
        pause()
        return
    p = G["price"][i]
    unit = p - G["cost"][i]
    print(" " + goods()[i] + " at " + money(p))
    print(" Cost " + money(G["cost"][i]) + " -> " +
          ("+" if unit >= 0 else "") + money(unit) + " ea")
    n = ask_num(" How many (M=max)? ", 1, G["inv"][i])
    if n <= 0:
        return
    take = n * p
    G["inv"][i] -= n
    G["cash"] += take
    if G["inv"][i] == 0:
        G["cost"][i] = 0
    print(" Sold " + str(n) + " for " + money(take))
    print(" Profit " + money(unit * n))
    pause()


# ---------------------------------------------------------------
# MONEY
# ---------------------------------------------------------------

def do_bank():
    while True:
        cls()
        banner("BANK")
        print(" Cash " + money(G["cash"]))
        print(" Bank " + money(G["bank"]))
        print(" Interest " + str(int(DIFFS[G["diff"]][4] * 100)) + "%/day")
        rule("-")
        c = ask_choice(" (d)eposit (w)ithdraw (b)ack ", ["d", "w", "b"])
        if c == "b":
            return
        if c == "d":
            n = ask_num(" Deposit (M=all)? ", 1, max(G["cash"], 0))
            G["cash"] -= n
            G["bank"] += n
        else:
            n = ask_num(" Withdraw (M=all)? ", 1, max(G["bank"], 0))
            G["bank"] -= n
            G["cash"] += n


def do_shark():
    while True:
        cls()
        banner("LOAN SHARK")
        print(" Debt " + money(G["debt"]))
        print(" Cash " + money(G["cash"]))
        print(" Interest " + str(int(DIFFS[G["diff"]][3] * 100)) + "%/day")
        rule("-")
        c = ask_choice(" (p)ay (b)orrow (x)back ", ["p", "b", "x"])
        if c == "x":
            return
        if c == "p":
            if G["debt"] <= 0:
                print(" You owe nothing.")
                pause()
                continue
            n = ask_num(" Pay (M=max)? ", 1, min(G["cash"], G["debt"]))
            G["cash"] -= n
            G["debt"] -= n
            if G["debt"] <= 0:
                print(" Debt cleared. He's almost")
                print(" disappointed.")
                pause()
        else:
            # Credit limit scales with net worth, so borrowing stays
            # useful late instead of being a fixed early-game crutch.
            cap = max(5000, int((G["cash"] + G["bank"] + stock_value()) * 0.6))
            print(" He'll go to " + money(cap) + ".")
            n = ask_num(" Borrow? ", 1, cap)
            G["cash"] += n
            G["debt"] += n


def accrue():
    G["debt"] = int(G["debt"] * (1 + DIFFS[G["diff"]][3]))
    G["bank"] = int(G["bank"] * (1 + DIFFS[G["diff"]][4]))


# ---------------------------------------------------------------
# COMBAT
# ---------------------------------------------------------------

def combat():
    t = THEMES[THEME]
    cops = random.randint(2, 5)
    G["busts"] += 1
    while True:
        cls()
        banner(t["bust"])
        print(" " + str(cops) + " " + t["law"].lower() + " on you.")
        print(" HP " + str(G["hp"]) + "/" + str(G["maxhp"]) +
              "   Guns " + str(G["guns"]))
        rule("-")
        bribe = 600 * cops + int(stock_value() * 0.15)
        print(" (f)ight (r)un (b)ribe " + money(bribe))
        c = ask_choice(" > ", ["f", "r", "b"])

        if c == "b":
            if G["cash"] < bribe:
                print(" Not enough cash on you.")
                pause()
                continue
            G["cash"] -= bribe
            print(" Money changes hands.")
            print(" They lose interest.")
            pause()
            return True

        if c == "f":
            hit = 0.40 + 0.13 * G["guns"]
            if hit > 0.85:
                hit = 0.85
            if G["guns"] == 0:
                hit = 0.18
                print(" Bare hands. Not clever.")
            if random.random() < hit:
                cops -= 1
                print(" One down.")
                if cops <= 0:
                    loot = random.randint(750, 2000) * random.randint(1, 3)
                    G["cash"] += loot
                    G["won"] += 1
                    print(" All clear. You grab " + money(loot) + ".")
                    pause()
                    return True
            else:
                print(" You miss.")

        else:
            load = carried() / float(max(G["coat"], 1))
            esc = 0.62 - 0.05 * cops - 0.20 * load
            if random.random() < esc:
                print(" You lose them in an alley.")
                pause()
                return True
            print(" No good -- they're on you.")

        # Return fire.
        for _ in range(cops):
            if random.random() < 0.26:
                dmg = random.randint(6, 18)
                G["hp"] -= dmg
                print(" Hit for " + str(dmg) + ".")
        if G["hp"] <= 0:
            G["hp"] = 0
            print(" You don't get up.")
            pause()
            G["dead"] = 1
            return False
        pause()


# ---------------------------------------------------------------
# EVENTS
# ---------------------------------------------------------------

def ev_nothing():
    return


def ev_cheap():
    i = random.randint(0, 5)
    p = int(random.randint(*BANDS[i]) * random.uniform(0.15, 0.35))
    room = G["coat"] - carried()
    top = min(room, G["cash"] // max(p, 1))
    if top <= 0:
        return
    print(" " + THEMES[THEME]["dealer"] + " offers")
    print(" " + goods()[i] + " at " + money(p) + " each.")
    n = ask_num(" Take how many (M=max)? ", 1, top)
    if n <= 0:
        return
    held = G["inv"][i]
    G["cost"][i] = int((G["cost"][i] * held + n * p) / (held + n))
    G["inv"][i] += n
    G["cash"] -= n * p
    print(" Loaded up.")


def ev_find():
    room = G["coat"] - carried()
    if room <= 0:
        return
    i = random.randint(0, 5)
    n = min(room, random.randint(1, 7))
    G["inv"][i] += n
    print(" You find " + str(n) + " " + goods()[i])
    print(" abandoned on the subway.")


def ev_mug():
    if G["cash"] < 500:
        return
    loss = int(G["cash"] * random.uniform(0.20, 0.40))
    G["cash"] -= loss
    print(" Mugged on the platform.")
    print(" They take " + money(loss) + ".")


def ev_gun():
    price = 400 + 150 * G["guns"]
    if G["cash"] < price or G["guns"] >= 4:
        return
    print(" Someone offers a piece")
    print(" for " + money(price) + ".")
    if ask_choice(" Buy? (y/n) ", ["y", "n"]) == "y":
        G["cash"] -= price
        G["guns"] += 1
        print(" You feel better about")
        print(" the Ghetto now.")


def ev_coat():
    price = 200 + 40 * ((G["coat"] - 100) // 10)
    if G["cash"] < price:
        return
    t = THEMES[THEME]["coat"].lower()
    print(" A bigger " + t + " -- room for")
    print(" 10 more -- " + money(price) + ".")
    if ask_choice(" Buy? (y/n) ", ["y", "n"]) == "y":
        G["cash"] -= price
        G["coat"] += 10
        print(" Capacity now " + str(G["coat"]) + ".")


def ev_badbatch():
    held = [i for i in range(6) if G["inv"][i] > 0]
    if not held:
        return
    i = random.choice(held)
    n = max(1, int(G["inv"][i] * random.uniform(0.3, 0.7)))
    G["inv"][i] -= n
    print(" " + str(n) + " of your " + goods()[i])
    print(" turns out to be junk.")


def ev_rumor():
    G["rumor"] = random.randint(0, 5)
    G["rumorg"] = random.randint(0, 5)
    print(" You overhear something")
    print(" about the " + CITIES[G["rumor"]] + " market.")


def ev_collector():
    if G["debt"] < 10000:
        return
    print(" The shark's people find you.")
    if G["cash"] >= G["debt"] // 4:
        take = G["debt"] // 4
        G["cash"] -= take
        G["debt"] -= take
        print(" They take " + money(take) + " on")
        print(" account. Rude, but fair.")
    else:
        dmg = random.randint(8, 20)
        G["hp"] -= dmg
        print(" No cash means a beating.")
        print(" -" + str(dmg) + " HP.")


def ev_medic():
    if G["hp"] >= G["maxhp"]:
        return
    need = G["maxhp"] - G["hp"]
    price = need * 45
    if G["cash"] < price:
        return
    print(" A back-room doctor will")
    print(" patch you up: " + money(price) + ".")
    if ask_choice(" Pay? (y/n) ", ["y", "n"]) == "y":
        G["cash"] -= price
        G["hp"] = G["maxhp"]
        print(" Good as new.")


EVENTS = [
    (26, ev_nothing),
    (11, ev_cheap),
    (9, ev_find),
    (8, ev_mug),
    (8, ev_gun),
    (8, ev_coat),
    (7, ev_badbatch),
    (7, ev_rumor),
    (6, ev_collector),
    (6, ev_medic),
]


def pick_event():
    total = sum(w for w, _ in EVENTS)
    r = random.randint(1, total)
    for w, fn in EVENTS:
        r -= w
        if r <= 0:
            return fn
    return ev_nothing


def daily():
    # Police first: getting caught should pre-empt the day's luck.
    load = carried() / float(max(G["coat"], 1))
    heat = CITY_HEAT[G["loc"]] * DIFFS[G["diff"]][5]
    chance = (0.06 + 0.28 * load) * heat
    if carried() >= 10 and random.random() < chance:
        return combat()

    fn = pick_event()
    if fn is not ev_nothing:
        cls()
        banner("DAY " + str(G["day"]))
        fn()
        pause()
    if G["hp"] <= 0:
        G["dead"] = 1
        return False
    return True


# ---------------------------------------------------------------
# TRAVEL
# ---------------------------------------------------------------

def do_travel():
    cls()
    banner("JET WHERE?")
    for i in range(6):
        mark = "*" if i == G["loc"] else " "
        note = ""
        if i == G["rumor"]:
            note = "  <- word"
        print(" " + str(i + 1) + mark + " " + CITIES[i] + note)
    rule("-")
    r = ask(" Which # (enter=stay)? ").strip()
    if not r.isdigit():
        return True
    i = int(r) - 1
    if i < 0 or i > 5 or i == G["loc"]:
        return True
    G["loc"] = i
    G["day"] += 1
    if G["rumor"] == i:
        G["rumor"] = -1
    accrue()
    roll_market()
    net = G["cash"] + G["bank"] - G["debt"]
    if net > G["peak"]:
        G["peak"] = net
    return daily()


# ---------------------------------------------------------------
# SAVE / LOAD
# ---------------------------------------------------------------

SLOTS = ["diff", "day", "cash", "debt", "bank", "coat", "loc", "hp",
         "maxhp", "guns", "peak", "busts", "won", "rumor", "rumorg"]


def pack():
    out = [SAVE_VER]
    for k in SLOTS:
        out.append(int(G[k]))
    out.extend(int(x) for x in G["inv"])
    out.extend(int(x) for x in G["cost"])
    out.extend(int(x) for x in G["price"])
    return out


def unpack(v):
    if not v or int(v[0]) != SAVE_VER:
        return False
    n = 1
    G.clear()
    for k in SLOTS:
        G[k] = int(v[n]); n += 1
    G["inv"] = [int(x) for x in v[n:n + 6]]; n += 6
    G["cost"] = [int(x) for x in v[n:n + 6]]; n += 6
    G["price"] = [int(x) for x in v[n:n + 6]]; n += 6
    G["last"] = G["price"][:]
    G["dead"] = 0
    G["won"] = G.get("won", 0)
    G["seen"] = 0
    return True


def _write(name, nums):
    # Three backends, tried in order. Any failure is non-fatal --
    # a calculator that refuses to persist should still play.
    try:
        import ti_system
        ti_system.store_list(name, nums)
        return True
    except Exception:
        pass
    try:
        f = open(name + ".txt", "w")
        f.write(",".join(str(int(x)) for x in nums))
        f.close()
        return True
    except Exception:
        return False


def _read(name):
    try:
        import ti_system
        v = ti_system.recall_list(name)
        if v:
            return [int(x) for x in v]
    except Exception:
        pass
    try:
        f = open(name + ".txt", "r")
        s = f.read()
        f.close()
        if s.strip():
            return [int(x) for x in s.split(",")]
    except Exception:
        pass
    return None


def save_game():
    if _write("DWSAV", pack()):
        print(" Saved.")
    else:
        print(" Save unavailable here.")
    pause()


def load_game():
    v = _read("DWSAV")
    if v and unpack(v):
        return True
    return False


def add_score(score):
    v = _read("DWHI") or []
    v.append(int(score))
    v.sort()
    v.reverse()
    _write("DWHI", v[:5])
    return v[:5]


# ---------------------------------------------------------------
# ENDGAME
# ---------------------------------------------------------------

def rank(net):
    if net < 0:
        return "In The Hole"
    if net < 20000:
        return "Corner Kid"
    if net < 100000:
        return "Getting By"
    if net < 500000:
        return "Player"
    if net < 2000000:
        return "Heavy"
    if net < 10000000:
        return "Kingpin"
    return "Legend"


def endgame():
    net = G["cash"] + G["bank"] - G["debt"]
    cls()
    rule()
    print(" " + ("YOU DIED" if G["dead"] else "31 DAYS UP"))
    rule()
    print(" Cash " + money(G["cash"]))
    print(" Bank " + money(G["bank"]))
    print(" Debt " + money(G["debt"]))
    rule("-")
    print(" NET  " + money(net))
    print(" Peak " + money(G["peak"]))
    print(" Rank " + rank(net))
    rule("-")
    print(" Busts " + str(G["busts"]) + "   Won " + str(G["won"]))
    if G["dead"]:
        net = int(net * 0.4)
        print(" (death penalty applied)")
    rule()
    top = add_score(net)
    print(" BEST")
    for i, s in enumerate(top):
        print("  " + str(i + 1) + ". " + money(s))
    rule()
    pause()


# ---------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------

def title():
    t = THEMES[THEME]
    cls()
    rule()
    print(" " + t["title"] + "  EVO v" + VERSION)
    print(" 31 days. $5,000 owed.")
    print(" Buy low. Sell high. Run.")
    rule()


def play():
    alive = True
    while alive and G["day"] <= DAYS:
        show_status()
        show_market()
        print(" (b)uy (s)ell (j)et (l)oan")
        print(" (k)bank (v)save (q)uit")
        c = ask_choice(" > ", ["b", "s", "j", "l", "k", "v", "q"])
        if c == "b":
            do_buy()
        elif c == "s":
            do_sell()
        elif c == "j":
            alive = do_travel()
        elif c == "l":
            do_shark()
        elif c == "k":
            do_bank()
        elif c == "v":
            save_game()
        elif c == "q":
            if ask_choice(" Really quit? (y/n) ", ["y", "n"]) == "y":
                return
    endgame()


def main():
    title()
    if _read("DWSAV"):
        if ask_choice(" Resume saved game? (y/n) ", ["y", "n"]) == "y":
            if load_game():
                play()
                return
    print(" 1 Rookie   2 Classic")
    print(" 3 Kingpin")
    c = ask_choice(" Difficulty? ", ["1", "2", "3"])
    new_game(int(c))
    play()


if __name__ == "__main__":
    main()

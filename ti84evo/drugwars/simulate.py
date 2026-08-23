# Desktop-only test harness for DRUGWARS.py -- do NOT send to the
# calculator. Drives the game headlessly by replacing its input
# helpers, to fuzz for crashes and sanity-check the balance curve.

import random
import sys
import DRUGWARS as D


class Bot(object):
    def __init__(self, seed):
        self.rng = random.Random(seed)
        self.calls = 0

    def _tick(self):
        self.calls += 1
        if self.calls > 20000:
            raise RuntimeError("runaway prompt loop")

    def ask(self, prompt):
        self._tick()
        p = prompt.lower()
        if "which #" in p:
            # Sometimes back out, sometimes pick an item/city.
            return self.rng.choice([str(self.rng.randint(1, 6)), ""])
        return ""

    def ask_choice(self, prompt, valid):
        self._tick()
        # Favour travelling so games actually reach day 31, and never
        # quit voluntarily -- we want full runs.
        if "j" in valid:
            pool = [c for c in valid if c != "q"]
            return self.rng.choice(pool + ["j", "j", "j", "b", "s"])
        if "n" in valid and "y" in valid:
            return self.rng.choice(["y", "n"])
        return self.rng.choice(list(valid))

    def ask_num(self, prompt, lo, hi):
        self._tick()
        if hi < lo:
            return 0
        return self.rng.choice([hi, lo, self.rng.randint(lo, hi), 0])


def run(seed, quiet=True):
    bot = Bot(seed)
    D.ask = bot.ask
    D.ask_choice = bot.ask_choice
    D.ask_num = bot.ask_num
    D._write = lambda name, nums: True
    D._read = lambda name: None
    random.seed(seed)
    if quiet:
        out = sys.stdout
        sys.stdout = open("/dev/null", "w")
    try:
        D.main()
    finally:
        if quiet:
            sys.stdout.close()
            sys.stdout = out
    return {
        "net": D.G["cash"] + D.G["bank"] - D.G["debt"],
        "day": D.G["day"],
        "dead": D.G["dead"],
        "busts": D.G["busts"],
        "coat": D.G["coat"],
        "peak": D.G["peak"],
        "cash": D.G["cash"],
        "hp": D.G["hp"],
    }


def check_invariants(r):
    """Things that must never be true regardless of how play goes."""
    bad = []
    if r["cash"] < 0:
        bad.append("negative cash")
    if r["hp"] < 0:
        bad.append("negative hp")
    if r["coat"] < 100:
        bad.append("coat shrank")
    if r["day"] > D.DAYS:
        bad.append("overran day limit")
    return bad


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 400
    results, fails, broken = [], [], []
    for s in range(n):
        try:
            r = run(s)
            bad = check_invariants(r)
            if bad:
                broken.append((s, ",".join(bad)))
            results.append(r)
        except Exception as e:
            fails.append((s, type(e).__name__, str(e)[:90]))

    print("games        : %d" % n)
    print("crashes      : %d" % len(fails))
    for f in fails[:8]:
        print("   seed %-5d %s: %s" % f)
    print("invariant hits: %d" % len(broken))
    for b in broken[:8]:
        print("   seed %-5d %s" % b)
    if not results:
        return 1

    nets = sorted(r["net"] for r in results)
    deaths = sum(1 for r in results if r["dead"])
    full = sum(1 for r in results if r["day"] >= D.DAYS)
    busts = sum(r["busts"] for r in results) / float(len(results))

    def pct(q):
        return nets[min(len(nets) - 1, int(len(nets) * q))]

    print("reached d31  : %d (%.0f%%)" % (full, 100.0 * full / len(results)))
    print("died         : %d (%.0f%%)" % (deaths, 100.0 * deaths / len(results)))
    print("busts/game   : %.2f" % busts)
    print("net min      : %s" % D.money(nets[0]))
    print("net p25      : %s" % D.money(pct(0.25)))
    print("net median   : %s" % D.money(pct(0.50)))
    print("net p75      : %s" % D.money(pct(0.75)))
    print("net max      : %s" % D.money(nets[-1]))
    return 1 if (fails or broken) else 0


if __name__ == "__main__":
    sys.exit(main())

# Capability probe for the TI-84 Evo Python app.
#
# Send BOTH this file and pack1.py to the calculator, then run PROBE.
# It answers the two questions that decide how far Drug Wars Evo can grow:
#
#   1. Can a script import another script you wrote?
#      If yes, content can live in swappable packs held in archive.
#      If no, everything must fit in one resident module.
#
#   2. How much Python heap is actually free?
#      Turns the memory ceiling from a guess into a number.

print("=" * 22)
print("EVO CAPABILITY PROBE")
print("=" * 22)

# --- 1. user module import -------------------------------------
try:
    import pack1
    print("import: OK")
    print("  " + pack1.DATA)
    print("  rows: " + str(len(pack1.ROWS)))
    can_import = True
except Exception as e:
    print("import: NO")
    print("  " + str(e))
    can_import = False

# --- 2. heap ---------------------------------------------------
try:
    import gc
    gc.collect()
    free = gc.mem_free()
    print("free heap: " + str(free))
    print("  = " + str(free // 1024) + " KB")
except Exception as e:
    print("heap: unknown")
    print("  " + str(e))
    free = 0

# --- 3. can we unload a module again? --------------------------
# This is the half that makes swapping packs work. Importing is
# useless if the memory never comes back.
if can_import:
    try:
        import sys
        gc.collect()
        before = gc.mem_free()
        del pack1
        if "pack1" in sys.modules:
            del sys.modules["pack1"]
        gc.collect()
        after = gc.mem_free()
        print("unload: OK")
        print("  reclaimed " + str(after - before))
    except Exception as e:
        print("unload: NO")
        print("  " + str(e))

# --- 4. how big a list can we hold? ----------------------------
# Rough proxy for how much content data can be resident at once.
n = 0
try:
    probe = []
    for i in range(20000):
        probe.append(i)
        n = i
except Exception:
    pass
print("list cap: ~" + str(n) + " ints")

print("=" * 22)
print("Report these four lines back.")

# Drug Wars Evo

A modern port of the 1994 TI-82 game by Jonathan Maier (itself based on
John E. Dell's 1984 BASIC original), rebuilt for the TI-84 Evo.

The original was pulled from ticalc.org in 2001 and never made the jump
to the CE or the Evo. This is a rewrite in Python from the surviving
TI-BASIC source, keeping that source's price bands and event table so it
plays like the thing people remember.

## Files

| File | Goes on the calculator? | What it is |
|---|---|---|
| `DRUGWARS.py` | **yes** | The game. Single file, no dependencies. |
| `simulate.py` | no | Desktop balance/crash harness. |

## Playing it on a computer

```
python3 DRUGWARS.py
```

Any Python 3. Nothing to install.

There is also a browser build with a clickable keypad and a live state
panel — easier than a terminal, and it runs the identical logic.

## Putting it on the calculator

1. Open the game page in Chrome, Edge, or Firefox on a computer.
2. Plug the Evo in over USB-C and turn it on.
3. Send `DRUGWARS.py`, or paste it into TI Connect Evo.
4. On the calculator: `prgm` -> Python App -> `DRUGWARS` -> run.

Nothing here touches the OS or exam mode. It is an ordinary Python file.

## Compatibility

Written against the smallest common denominator on purpose:

- Text I/O only (`print` / `input`) — no `ti_draw`, no graphics calls.
- No f-strings, comprehensionless where it costs nothing, `%`-free
  formatting via helpers, so it survives older CircuitPython builds.
- 32-column layout, which fits both the Evo and the CE Python.
- Persistence tries `ti_system.store_list` first, then a plain file,
  then gives up quietly. A calculator that refuses to save still plays.

That means it also runs unmodified on a TI-84 Plus CE Python.

## Testing

```
python3 simulate.py 500
```

Plays 500 complete games with a random bot, then reports crash count,
invariant violations (negative cash, negative HP, overrun day counter)
and the net-worth spread. Run it after any balance change.

Current state on 500 games: 0 crashes, 46% death rate, median net worth
negative — the random bot borrows recklessly, so treat the median as a
floor rather than a typical player result.

## Balance constants

Lifted from the original TI-BASIC, so the economy feels the same:

| Item | Price band |
|---|---|
| Cocaine | 16,000 – 28,000 |
| Heroin | 5,000 – 12,000 |
| Acid | 1,000 – 4,400 |
| Weed | 330 – 750 |
| Speed | 70 – 220 |
| Ludes | 10 – 50 |

31 days, $2,000 start, $5,000 debt, 10%/day compounding on the
Classic difficulty.

## Theme switch

`THEME = "classic"` at the top of the file. Set it to `"spice"` and the
six goods become Saffron, Truffle, Caviar, Vanilla, Pepper and Salt.
Identical mechanics and price bands — only the nouns change.

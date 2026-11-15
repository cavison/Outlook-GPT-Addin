---
id: C-03
title: Program Your Baofeng with CHIRP
category: comms
phases: [before]
time: 1–2 h first time
difficulty: moderate
diagram: C-03.svg
---
Load your Baofeng with weather, calling and local repeater channels using a computer before the power goes out; hand-programming dozens of channels on the keypad is slow and error-prone.

## You need
- Baofeng radio (UV-5R class) with charged battery
- Computer with internet access (to download)
- CHIRP software (free, chirpmyradio.com)
- USB programming cable for your radio's 2-pin Kenwood-style jack (one with a genuine FTDI or CH340 chip is easiest)
- Your filled-in frequency list from [[C-04]]

## Steps
1. Download CHIRP from the official site (chirpmyradio.com) and install the USB cable driver.
2. Plug the cable into the computer, then push the plug firmly into the radio until it clicks fully in; a half-seated plug is the most common failure.
3. Turn the radio on, volume up. In CHIRP choose Radio > Download From Radio, pick the COM port, brand and model.
4. Save this first download as a backup file named with the date before changing anything.
5. Type your channels into the grid: frequency, name, duplex/offset and tone, using the list in [[C-04]]; set power to Low.
6. Choose Radio > Upload To Radio, wait for it to finish, then turn the radio off and back on.
7. Check every channel: weather channels should be receive-only listening; test ham channels only if you are licensed.
8. Save the final file and print the channel list; keep a copy on a USB stick in your go-bag.

## Michigan notes
Ottawa County has an active ARES/RACES group that uses local repeaters. Repeater frequencies, offsets and tones change, so get current ones from RepeaterBook (repeaterbook.com, or its phone app, which works offline once downloaded) and confirm them with a local club before you program. CHIRP can also import repeaters directly from RepeaterBook by location.

## Cable trouble
If Windows shows the cable but CHIRP errors out ("radio did not respond" or a Device Manager error on a "Prolific" port), you likely have a counterfeit Prolific chip cable. Newer Prolific drivers deliberately refuse them. Fixes: buy a cable that states a genuine FTDI or CH340 chip, or install an older Prolific driver version. Also try: volume turned up, a different USB port, and pushing the radio plug in harder.

## Caution
Owning and programming a Baofeng is legal, but transmitting on 2 m/70 cm ham frequencies requires an FCC Amateur license (see [[C-07]]). The only exception is a real emergency with imminent threat to life or property when normal communications are unavailable (FCC §97.403). These radios are not FCC-certified for FRS/GMRS, so don't use them as family-band walkie-talkies.

## Field note
Before you edit anything, always download and save the radio's existing memory first. Some Baofeng variants hold factory calibration settings; if an upload goes wrong you can restore from that backup instead of ending up with a radio that won't transmit or receive correctly.

## See also
[[C-04]] [[C-05]] [[C-06]] [[C-07]] [[C-08]]

## Sources
CHIRP project documentation; FCC 47 CFR Part 97 (§97.403); FCC Part 95 (FRS/GMRS); ARRL; RepeaterBook

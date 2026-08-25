# weatherbot V1.1 — the Dead-Bucket Kill Engine

One trade, executed well: **when a fact about the past proves a bucket dead, sell it
before the crowd finishes reading.** No winner-picking, no trajectory opinions, no
forecasting. Retrospective moments only.

## V1.1 audit addendum (2026-08-25)

- **FIXED: six-hour group gate.** Synoptic METARs are stamped :51–:56 of the PRIOR
  hour (1751Z carries the 18Z groups); the old hour gate missed all of them. The
  sixhr channel is a **2-minute cliff**: measured across 64 days, 14 kills worth
  $1,360 existed at wire+2 min and every one was gone by wire+3. You need ≤2-min
  parsing (NWWS-OI push, or 5s polling inside :51–:56) to win this channel.
- **Out-of-sample verified** (Jun 15–Jul 18): edge replicates; rate gap vs August
  is Poisson noise. Pooled planning numbers: **0.33–0.55 tradeable signals/day,
  ~$58–79/day mean** (upper figures require the fast sixhr path), ~73% zero days,
  ~$176/trade, capital <$500. Bottom-tail kills on cool days are a real second
  face of the edge (Chicago Jul 4: "85° or below" bid 95¢ at proof of 85).
- **OMO lag corrected**: measured 2.3 min typical on the archived wire (was
  modeled 8). OMO precision closed at spec+wire level: the FAA feed's temp is the
  5-min average in whole °C — 78-vs-79 is unrecoverable from it, ever. Exact
  readings at multiples of 5 °C (25 °C = 77) are the only precision moments.
- **KXLOW series**: registered shells, zero markets ever listed. low_sim.py is
  built and waits; add the universe census to catch launch day.

## The hidden-data thesis

The settlement quantity — the whole-°F daily max, computed as the max of the
5-minute-smoothed 1-minute stream — exists **continuously inside the ASOS station**
but is published only at discrete, known times through lossy encodings:

- SPECIs never trigger on temperature → a peak between hourly METARs is invisible.
  Measured: **66% of days** the settlement max never printed in any METAR.
- The only sub-hourly public wire (MADIS OMO, 5-min) transmits **whole °C** —
  the ±0.9°F fuzz means it often can't prove the number even when it moves.
- NYC and Denver aren't on that wire at all.

So doomed buckets stay priced alive after they are factually dead — median **109
minutes** in NYC/DEN — until a text product (DSM at :15 past, METAR at :51–:54,
6-hr groups at synoptic hours) lands, and then the market repricings collectively
and persistently within **1–3 minutes**. The profit belongs to whoever parses the
bulletin first with settlement-exact decoding.

## Quantified edge (measured, Jul 19 – Aug 17 2026, red-teamed)

| Metric | Value |
|---|---|
| Fat kill events (bid ≥70¢ at proof), NYC+DEN | 7 / 30 days (n=7 — treat as count, not rate) |
| All kills with bid ≥10¢ at proof, NYC+DEN | 9 / 30 days (median executable bid **82¢**, spreads 1–3¢) |
| Covered-city residual (OMO/METAR kills) | ~5 / 30 days, mostly Austin heat tails |
| Blindness window (touch → first public proof) | median **109 min** (NYC/DEN) |
| Collapse after proof | median **1.0 min**; 100% of ≥40¢ prints inside 3 min |
| Printed volume ≥40¢ post-proof | 113–493 contracts/event (VWAP 45–74¢) |
| Taker fee (0.07·p·(1−p)) | ≈1–2¢/contract at these prices (~1.5% drag) |
| Realistic per-event capture (150-lot, first in line) | **$100–140 net** (replay-verified: NYC Jul 24 $137, DEN Aug 11 $121) |
| Max loss per event (proof wrong / QC correction) | size × (100−bid) ≈ **$12–45 per 150-lot** |
| Order of magnitude, current depth, full speed | **~$0.8–2.5k/month** + growth as Kalshi volume grows |
| Reaction budget | collapse ≈ 20–60 s for first movers; IEM polling adds 2–5 s, NWWS-OI push ≈ 1–3 s → a 20-second assumption is realistic |

Known caveats: single summer month; DEN carries a DSM-cadence data-break caveat;
depth beyond printed trades unknown until the live collector accrues.

## Architecture

```
decode.py       settlement-exact rules: half-up, T-group decode, whole-C floors,
                streaming 5-min Smoother. Self-testing.
feeds.py        DSMFeed (IEM AFOS, window-polled) · MetarFeed (aviationweather,
                T-group + 6-hr groups) · OMOFeed (MADIS hfmetar, whole-C floors,
                If-Modified-Since). All emit ProofEvents: "max >= L".
market.py       Kalshi public data: boards, quotes, orderbook (yes_dollars =
                the resting bids our kill consumes), taker-fee model.
strategy.py     KillEngine: monotone proven-max ratchet per city-day; fires
                SELL_YES on buckets with kill_level <= proven max. Guards:
                dedupe · top-tail exclusion · spread filter (≤5¢) ·
                min-bid (15¢) · physical-plausibility guard (DSM/OMO claim may
                not exceed METAR-visible max by >7°F — replay-calibrated so
                Denver's +21°F diurnal ratchet passes but corruption is held).
paper.py        Paper execution: snapshots the LIVE book at intent time,
                simulates the fill vs displayed depth, appends to
                paper_ledger.jsonl for settlement P&L.
exec_live.py    Real orders (BUY NO = sell YES). Hard-disabled unless
                WEATHERBOT_LIVE=yes + KALSHI_KEY_ID + KALSHI_PRIVATE_KEY.
                RSA-PSS request signing included.
run.py          Scheduler: tight polling only inside reveal windows
                (DSM :15±90s per city, METAR minute+5min, OMO 60s), idle
                otherwise; warm-start seeds the day's proven max; state
                persists across restarts (no refiring).
replay_test.py  Proof it works: decode self-test, guard units, and full
                replays of NYC Jul 24 + DEN Aug 11 against the actual archived
                wire products and historical books.
```

## Run

```
pip install netCDF4 numpy cryptography     # OMO feed + live signing (paper works without)
python3 replay_test.py                     # must print ALL REPLAYS PASSED
python3 run.py --once                      # single warm pass now
python3 run.py                             # paper-mode daemon
```

## Go-live checklist

1. **Paper for 2–4 weeks.** Ledger must show: intents fire inside the first
   minute of reveals, simulated fills at bid within 2¢ of tape VWAP, zero
   guard breaches. That distribution is the go/no-go.
2. **Kalshi API key**: create in account settings → set `KALSHI_KEY_ID`,
   `KALSHI_PRIVATE_KEY` (PEM path). Leave `WEATHERBOT_LIVE` unset until (1) passes.
3. **NWWS-OI application** (NOAA Weather Wire, free): replaces AFOS polling with
   push delivery measured in seconds — the single biggest latency upgrade.
4. **Verify DEN DSM cadence this week** (broke Aug 6: hourly → 2/day). The
   hourly-sweep flag in config covers both regimes.
5. **Sizing**: flat stakes, ≤0.25–0.5% of bankroll per event until n>30 live
   events; never exceed displayed depth; the spread filter is not optional.
6. **Corrections risk**: DSMs are occasionally reissued. The engine only acts on
   max *increases* and the plausibility guard holds outliers; a downward
   correction after a fill is the residual risk — bounded at (100−bid)/contract.

## Explicitly out of scope for V1 (V2 roadmap)

Winner-leg buying · trajectory-readjustment trades · ambiguity-settlement trades ·
the NYC/DEN private sensor ring (the PHL actor's game) · LAX decode-war fades.
V1 does one thing: kill what is already dead, faster than the room.

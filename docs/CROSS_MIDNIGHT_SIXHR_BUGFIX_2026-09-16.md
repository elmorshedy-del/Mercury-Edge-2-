# Cross-midnight six-hour maximum bug — KDEN 2026-09-15

Date of fix: 2026-09-16

## Summary

Mercury Edge 2 made two paper fills in the Denver Sep 15 daily-high market after an invalid hard-proof state was created from a six-hour METAR maximum whose time window crossed Denver's climate-day midnight.

The critical bug was not the Celsius-to-Fahrenheit decoder and not the Kalshi bucket kill arithmetic. The bug was **day attribution**: `MetarFeed` assigned every six-hour maximum to the climate date containing the midpoint of the six-hour window (`obs - 3h`). That is not logically valid when the six-hour window spans two climate dates because the `1snTxTxTx` group reports only the maximum value, not the time inside the six-hour window when that maximum occurred.

The fix is deliberately fail-closed: a six-hour maximum is allowed to become a day-specific `ProofEvent(channel="sixhr")` only when the full nominal six-hour synoptic window lies inside one Local Standard Time climate date. If the window crosses climate midnight, Mercury logs that the group was held and does not let it advance `proven_max`.

## Incident timeline

### 1. Six-hour report created the bad 73°F ratchet

Mercury journal, 2026-09-15:

- **11:57:10.876871 UTC** — KDEN six-hour proof recorded as `level_f=73`, `climate_date=2026-09-15`.
- Source METAR: **`KDEN 151153Z`**.
- Raw remarks contain **`10228`**. The six-hour maximum group therefore reports **+22.8°C**, which correctly decodes to **73°F**.

Archived raw METAR example:

`METAR KDEN 151153Z 35011KT 10SM OVC021 13/01 A3025 RMK AO2 SLP171 T01330006 10228 20133 51029`

The decoder was correct. `22.8°C -> 73°F` is not the defect.

### 2. Why 73°F was not valid proof for Sep 15

The 11:53Z METAR carries the **12Z synoptic six-hour group**. Its nominal maximum window is approximately **06Z-12Z**.

Denver climate products use Local Standard Time. With KDEN configured at UTC-7, that window maps to approximately:

- **23:00 Sep 14 LST** ->
- **05:00 Sep 15 LST**

Therefore the window crosses the Sep 14 / Sep 15 climate-day boundary.

The six-hour group tells us that 73°F occurred somewhere inside that entire window. It does **not** tell us whether 73°F occurred during the pre-midnight Sep 14 hour or during the post-midnight Sep 15 portion. It therefore cannot by itself prove `Sep 15 daily max >= 73°F`.

The previous code used:

```python
cd6 = self._climate_date(obs - timedelta(hours=3))
```

That midpoint heuristic collapsed a two-date interval into one date and incorrectly promoted the entire 73°F value to Sep 15.

### 3. The later DSM contradicted that day assignment

The NWS Denver DSM archived at **12:16 UTC** contains:

`KDEN DS 0500 15/09 690007/ ...`

Meaning the Sep 15 running maximum through 05:00 LST was **69°F**, occurring at **00:07 LST**.

Archive:
https://mesonet.agron.iastate.edu/wx/afos/p.php?e=202609151216&pil=DSMDEN

Mercury did not ingest that DSM until **13:12:35.047815 UTC**, when its journal recorded:

- channel: `dsm`
- `level_f=69`
- detail: `DS 0500 max 69F @0007 LST`

Because the strategy's proven-max ratchet is intentionally monotone, the later valid 69°F DSM could not reduce the already-corrupted `proven_max[2026-09-15] = 73`.

### 4. The corrupted 73°F ratchet authorized two fills

At **13:12:35 UTC**, the lower DSM event caused the engine to retry buckets using the stored `proven_max=73`.

Paper fills:

1. `KXHIGHDEN-26SEP15-B70.5` — **70° to 71° YES**
   - action: `SELL_YES`
   - simulated fill: **6.5 contracts**
   - average: **16.92¢**
   - reason string: `proof dsm: max>=73F kills [70° to 71°]`
   - final result: **loss**, because the Sep 15 high was 71°F.

2. `KXHIGHDEN-26SEP15-T70` — **69° or below YES**
   - action: `SELL_YES`
   - simulated fill: **272.89 contracts**
   - average: **16.98¢**
   - reason string: `proof dsm: max>=73F kills [69° or below]`
   - final result: this happened to win because the day later reached 71°F, but the entry was still **not justified by valid evidence at entry time**.

This distinction matters: settlement outcome does not retroactively make an invalid proof valid.

### 5. Final climate result

The official NWS Denver climate summary for **September 15, 2026** reported:

- maximum: **71°F**
- time: **4:37 PM LST**

Archive:
https://mesonet.agron.iastate.edu/wx/afos/p.php?e=202609160738&pil=CLIDEN

So the 70-71°F bucket was the winning YES bucket and Mercury's SELL YES paper trade was a real losing trade.

## Why surrounding observations matter

The surrounding hourly/SPECI observations and the DSM made the 73°F six-hour value look like a historical maximum from the pre-midnight portion rather than a new-day maximum. Mercury's journal after the climate-day boundary included approximately:

- 07:53Z METAR: 68°F
- 08:35Z SPECI: 62°F
- 08:53Z METAR: 59°F
- 09:53Z METAR: 57°F
- 10:53Z METAR: 57°F
- 11:53Z METAR: 56°F
- DSM: Sep 15 running max 69°F at 00:07 LST

For a human reviewing the sequence, the 73°F six-hour value is clearly not compatible with being a known post-midnight Sep 15 observation.

However, the live kill engine should not need a probabilistic reconstruction from neighboring hourlies to remain safe. The simpler and stronger rule is structural: **if a six-hour maximum's window spans two climate dates, it is not day-specific hard proof at all.** A later DSM, exact hourly observation, or another date-specific product can establish the new day's hard floor.

## Code change

Old behavior:

```python
# midpoint heuristic
cd6 = self._climate_date(obs - timedelta(hours=3))
out.append(ProofEvent(..., cd6, ..., "sixhr", ...))
```

New behavior:

1. Infer the nominal synoptic cycle end by rounding the :51-:56 report forward to the 00/06/12/18Z cycle.
2. Set `window_start = cycle_end - 6h`.
3. Convert both the beginning of the window and `cycle_end - epsilon` to the station's Local Standard Time climate date.
4. If those two dates differ, hold the six-hour value and emit no hard `sixhr` ProofEvent.
5. If they match, use that common climate date and preserve the existing hard-proof behavior.

This keeps all unambiguous six-hour opportunities while preventing a cross-midnight maximum from contaminating the next day's monotone proof ratchet.

## Regression coverage

`research/test_cross_midnight_sixhr.py` contains two deterministic, network-free checks:

1. **KDEN 151153Z / 10228 / 73°F / 12Z cycle**
   - nominal 06Z-12Z window crosses midnight in MST
   - expected: **no `sixhr` hard ProofEvent**

2. **KDEN 151753Z / 10200 / 68°F / 18Z cycle**
   - nominal 12Z-18Z window is 05:00-11:00 MST, entirely Sep 15
   - expected: **one `sixhr` hard ProofEvent for Sep 15 at 68°F**

The test was first run against the old logic and failed exactly as expected: the old code emitted a Sep 15 73°F hard proof for the cross-midnight case. After the guard was added, both the cross-midnight rejection and same-day acceptance tests passed.

## Separate observability issue exposed by this incident

The paper ledger shows a confusing combination:

- reason string: `max>=73F`
- `proof_level_f`: `69`

That is because the 69°F DSM was the **retry trigger**, while the stored monotone ratchet at 73°F was the **authorizing level**. `Intent.reason` describes the stored ratchet, but `Intent.proof` points at the later trigger event. This mismatch did not cause the bad trade; the corrupted 73°F ratchet did. It should be treated as a separate provenance/ledger clarity issue in future hardening so a review can distinguish `authorizing_proof` from `retry_trigger`.

## Safety principle established by this fix

A hard kill requires proof whose temporal support can be assigned entirely to the contract's climate date.

**Value precision is not enough. Time-domain precision matters too.**

For six-hour maxima:

- same-climate-date window -> eligible hard proof
- cross-climate-date window -> informational only; wait for day-specific confirmation

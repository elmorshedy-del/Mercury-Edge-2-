# ASOS Phone Playbook — KLAX / KDEN Baseline

**Recorded:** 2026-09-27  
**Project:** Mercury Edge 2 / ASOS voice transport  
**Branch:** `feature/asos-voice-transport`

> [!IMPORTANT]
> This document preserves a prior Grok test set supplied by the project owner so the experiments do not have to be rediscovered from scratch.
>
> **Do not treat the Grok results below as ground truth.** They are a working baseline / hypothesis set. Every timing, call-drop behavior, station behavior, and operational rule should be independently reproduced by Mercury Edge before being promoted to production logic.
>
> In particular, claims such as “the box cannot be held longer,” “:00 is always optimal,” and “matching latency is 53–70 s” are **not immutable constraints**. They may reflect the tested Twilio method, recording workflow, station behavior, or call setup and should be optimized independently.

## Status labels

- **GROK-BASELINE** — prior result supplied by the project owner; useful but unverified by Mercury Edge.
- **MERCURY-REPRODUCED** — independently reproduced by our own current system.
- **OPEN** — still needs a controlled experiment.

---

## GROK-BASELINE — Full supplied result set

### ASOS phone playbook: KLAX and KDEN

Listen-only tests on an upgraded Twilio account. Goal: hear the current clock-minute temperature as early as possible, keep coverage when the box drops the call, and see if the voice feed is a 1-minute observation rather than the hourly METAR.

### Exact Grok transport / measurement method

**This historical Grok work did not use Railway or DigitalOcean.**

- API requests were issued directly from Grok's execution environment with `curl` against `api.twilio.com`.
- Twilio's own network originated the PSTN leg.
- From: +16602439589 (PN65078e22bc42686fa01bae8aa8f0b4c9).
- Twilio account was full/upgraded, not trial.
- Audio capture used **Twilio Recordings**.
- After the call, the recording was downloaded into the execution environment.
- Speech recognition used **Vosk word-level ASR**.
- Event clock = Twilio call `start_time` + word/recording offset.
- **No Twilio Media Streams WebSocket.**
- **No Railway application server.**
- **No DigitalOcean host.**
- Railway was available as a tool/skill but was not used for these Grok phone experiments.
- Credentials were not saved by Grok.

This distinction is important: the Grok timing data came from post-call recording analysis with word-level timestamps, whereas Mercury's 2026-09-27 reproduction used a live Railway callback/transcription path. The two pipelines have different measurement and transport overheads and must not be treated as directly interchangeable.

US outbound voice is $0.014 / connected minute. Number rent is $1.15 / month. Unanswered calls did not bill talk time.

### What “good” means

| Term | Meaning |
|---|---|
| Matching temp | Spoken valid minute = current clock minute when “temperature” is first heard |
| Latency | that hear-time − MM:00:00Z |
| Cycle 1 / cycle 2 | first vs second weather pass in one hold |
| Wire METAR | hourly/SPECI on Aviation Weather (:53 at these fields) |

We do not use first-temp-after-answer as matching temp. On both airports that first temp is usually MM−1.

---

## KLAX — Los Angeles

ASOS: +13106026051  
Confirmed working from cell and from Twilio.  
+13105681486 (other listing): no-answer.

### Holds

| Call | Fire | Answer | End | Dur |
|---|---:|---:|---:|---:|
| Early map | — | 10:58:51Z | 11:00:06Z | 75 s |
| Map | — | 11:07:39Z | 11:08:42Z | 63 s |
| Map | — | 11:09:39Z | 11:10:44Z | 65 s |
| :00 | 11:32:00.2Z | 11:32:03Z | 11:33:18Z | 75 s |
| :00 | 11:34:00.2Z | 11:34:03Z | 11:35:28Z | 85 s |
| :00 | 11:36:00.2Z | 11:36:03Z | 11:37:34Z | 91 s |
| :10 | 11:44:10.0Z | 11:44:13Z | 11:45:43Z | 90 s |

Twilio always answered ~3 s after fire. The box then dropped at ~63–91 s. Pause/TimeLimit of 600 s did not keep the line.

### Loop geometry (stable)

| Interval | Measured |
|---|---:|
| ZULU → next ZULU | 30.2–30.4 s |
| TEMP → next TEMP | 30.3–30.6 s |
| ZULU → TEMP (same pass) | 10.4–10.7 s |

On pickup the recording starts near the header, not at a random point: first zulu ~10 s after answer, first temp ~20 s after answer.

### `:00` series (the schedule test)

Answer always :03. Cycle 1 = previous minute. Cycle 2 = new minute.

| Answer | Cycle 1 zulu / temp | Cycle 2 zulu / temp | Matching temp? |
|---|---|---|---|
| 11:32:03 | 1131Z / 18°C @ 11:32:33.5 | 1132Z @ 11:32:52.8 / 18°C @ 11:33:05.8 | no — slipped to 11:33 |
| 11:34:03 | 1133Z / 18°C @ 11:34:43.0 | 1134Z @ 11:35:02.4 / 18°C @ 11:35:15.3 | no — slipped to 11:35 |
| 11:36:03 | 1135Z / 18°C @ 11:36:20.0 | 1136Z @ 11:36:39.9 / 18°C @ 11:36:52.9 | yes — 52.9 s |

Best matching temp: 52.9 s after :00.  
New zulu appears ~:40–:53. New temp ~10.5 s later (:50–:66).

### `:10` comparison (11:44:10 fire)

| Event | Clock | Spoken |
|---|---:|---|
| ZULU | 11:44:19.3Z | 1143Z (still MM−1) |
| TEMP 19°C | 11:44:32.7Z | 1143 |
| ZULU | 11:44:52.4Z | 1144Z |
| TEMP 19°C | 11:45:05.4Z | 1144 — already 11:45 |

:10 did not make cycle 1 the new minute. New temp was 65 s after 11:44:00 and missed the matching window. Keep :00.

### Wire vs phone

Hourly METAR during the morning tests was still 1053Z. Phone was speaking 1107 / 1109 / 1131–1144. This is a 1-minute voice product, not a stuck hourly METAR.

### LAX play

1. POST at MM:00 → To +13106026051.
2. Discard cycle 1.
3. Take the first temp after zulu flips to MM.
4. On completed, redial (below).
5. Do not dial at :10 for speed.

---

## KDEN — Denver

ASOS that works: +17192041223  
ASOS that does not (from this CID): +13033420838 no-answer.  
ATIS (not this feed): +13033420819 answered; letter Foxtrot; not 1-minute OMO.

719-204-1223 was busy while a human was on the line, then connected once the line was free.

### Hold

| Call | Answer | End | Dur |
|---|---:|---:|---:|
| 13:55:25Z | 13:55:25Z | 13:56:55Z | 90 s (hit TimeLimit; better than LAX’s early drop) |

### Events

| Event | Clock | Spoken |
|---|---:|---|
| ZULU | 13:55:27.8Z | 1354Z |
| TEMP | 13:55:38.4Z | 13°C / 55°F |
| ZULU | 13:55:59.2Z | 1355Z |
| TEMP | 13:56:09.8Z | 13°C (69.8 s after 13:55:00; clock 13:56) |
| ZULU | 13:56:30.6Z | 1355Z |
| TEMP | 13:56:41.2Z | 13°C |

Joined mid-loop. Minute flipped mid-call 1354 → 1355.

### Loop vs LAX

| Interval | DEN | LAX |
|---|---:|---:|
| Cycle | 31.4 s | 30.4 s |
| ZULU → TEMP | 10.6 s | 10.5 s |

Same class of machine.

### Wire vs phone

METAR KDEN 221353Z 12.8°C / 55°F at 7:53 AM MDT. Phone 13°C, A3020, DA 6,200 ft at 1354/1355Z. That is the morning airport obs, not the afternoon 80s high.

No DEN :00 grid yet. Geometry matches LAX, so use the same clock until measured otherwise.

### DEN play

1. POST at MM:00 → To +17192041223 only.
2. Discard cycle 1.
3. Take cycle-2 temp after zulu = MM.
4. Redial on completed.
5. Ignore ATIS 303-342-0819. Ignore 303-342-0838 from this CID unless it starts answering.

---

## Redial — both airports

One trunk. Same From. No second Twilio number.

| Situation | Result |
|---|---|
| Second call while anyone is still on the ASOS | busy (~1 s) |
| Two Twilio calls to the same To at once | busy |
| First call completed, then immediate POST | connects |
| busy after a drop | wait 2–5 s, retry |
| no-answer | wait 5–10 s, one retry; don’t hammer |

Pseudo-flow:

```text
call A in-progress
call A → completed
POST call B     # same From, same To, now
if busy: sleep 3s; POST again
```

Instant means the instant Twilio marks completed, not overlapping A. The ~57 s LAX gap after 11:08:42 was operator delay, not a required cool-off.

---

## Stations that failed this CID

| Station | Number | Result |
|---|---|---|
| KPHL ASOS | +12154929617 | no-answer 55 s and 90 s |
| KPNE ASOS | +12158979068 | busy, then 219 s hold (2 min voice product: 2228Z then 2230Z; skipped 2229Z) |
| KDEN ASOS alt | +13033420838 | no-answer |

KPNE proved a phone can speak non-hourly times. It is not the LAX/DEN 30 s loop.

---

## GROK-BASELINE analysis

1. Both LAX and DEN phones are 1-minute ASOS voice, not hourly METAR playback. Valid times move inside an hour (1136, 1355, not only :53).
2. Loop is ~30–31 s. Temperature is a fixed ~10.5 s after “zulu” in the same pass. You can stamp temp without waiting for zulu once you know the pass is the new minute.
3. Pickup restarts near the header. First temp ≈ answer + 20 s, and that temp is usually yesterday’s minute (MM−1) if you answered at :03.
4. The new minute shows up on cycle 2, ~40–53 s after :00, temp ~10.5 s after that.
5. Matching-temp latency is ~50–70 s, not +3 s and not “20 s after answer.” 20 s is the wrong minute. 60 s on the early LAX maps was an artifact of answering at :39 (39 + 20).
6. :00 is the right land; :10 is not faster.
7. You cannot hold the line. Coverage = drop + immediate redial.
8. DEN morning 13°C was correct. 80s F is the day high, not 8 AM MDT at KDEN.

---

## GROK-BASELINE conclusions

| Decision | Choice |
|---|---|
| LAX number | +13106026051 |
| DEN number | +17192041223 |
| When to fire | MM:00 UTC |
| Which temp to use | Second cycle only |
| Redial | Same From, on completed; 3 s retry if busy |
| Extra Twilio number | No |
| Media Streams / +3 s race | Not supported by this path |
| Expected matching latency | ~53–70 s after :00 |
| vs hourly METAR | Phone is minutes newer inside the hour |

Operational one-liner:

```text
at MM:00  call LAX +13106026051  and/or  DEN +17192041223
          From +16602439589   Record  TimeLimit 90
          ignore first TEMP
          take first TEMP after ZULU == MM
on completed  POST again immediately
on busy       wait 3s, POST again
```

Grok's proposed next measurement: a DEN :00 grid (three minutes), not more LAX :10 or another PN.

---

# MERCURY-REPRODUCED evidence

## Methodology difference vs Grok baseline

The Mercury reproduction below intentionally used a **different transport** from Grok:

- Mercury: Twilio outbound PSTN → live Twilio transcription callbacks → Railway parser.
- Grok baseline: direct Twilio REST call → Twilio Recording → download recording → Vosk word timestamps.

Therefore:

1. Grok's word timestamps may be better for reconstructing the exact moment a word was heard on the PSTN audio.
2. Mercury live callback arrival includes transcription/callback processing delay and is not automatically equivalent to acoustic hear-time.
3. A future controlled comparison should run the **same call with Twilio Recording enabled** while also collecting the live path, then compare:
   - acoustic word time from recording,
   - live transcription callback time,
   - parsed-proof time.
4. Claims about call drops should be reproduced under the direct-recording method before attributing them to Railway, Media Streams, or the ASOS box itself.

## 2026-09-27 KLAX 60-second smoke test

Current Mercury Edge independently reproduced the end-to-end phone path using the Railway `mercury-asos-voice-shadow` service.

### Transport

- Twilio account authentication succeeded.
- Outbound POST for KLAX returned HTTP 201.
- Twilio successfully fetched `/twilio/answer/KLAX`.
- KLAX ASOS audio was transcribed live and posted to `/twilio/transcription/KLAX`.
- The parser produced a structured ASOS voice proof.

### Heard content

Observed final ASR chunks included:

```text
Sky condition. Clear temperature 2 5 Celsius due Point 21 celsius,
altimeter 2 Niner 8 3.
```

and:

```text
Los Angeles. International Airport. Automated weather observation
2 3 3 5 Zulu wind 2, 4 0 at 1 2 ...
```

### Safe matched proof

- Valid minute: **23:35Z**
- Temperature: **25°C**
- Safe whole-F floor used by Mercury: **77°F**
- Complete matched proof available at approximately **23:36:50.320Z**
- Observation-to-proof latency for this smoke call: **~110.3 s**

This was slower than the Grok baseline because the call joined mid-loop and the first complete safe pairing required the loop to come around.

### Interesting but not yet counted as a temperature proof

Mercury then heard:

```text
Automated weather observation 2 3 3 6 Zulu ...
```

at approximately **23:36:54.506Z**, about **54.5 s after 23:36:00Z**.

That is useful evidence that the spoken valid minute can advance well before the hourly METAR. However, the matching 23:36 temperature had not yet been independently paired in a safe same-loop proof at that exact time, so **54.5 s is not counted as a temperature-proof latency**.

### Audit correction: invalidated pre-fix rows

The persistent `/data/asos_voice_shadow.jsonl` contains two pre-fix accepted rows for `KLAX 23:36Z` around `23:36:54.38–54.39Z` (reported latency ~54.4 s). **These rows are invalidated for latency analysis.**

Reason: they were created before the loop-boundary parser fix and could pair the new `23:36Z` header with the previous `23:35Z` temperature. They must not be counted as confirmed temperature proofs or source-race wins.

The confirmed safe smoke-test evidence remains the `23:35Z / 25°C / 77°F` observation. Future runs use the loop-boundary-safe parser.

### Parser bug found and fixed

The first live implementation could accidentally combine:

- the **new loop's Zulu timestamp**, with
- the **previous loop's temperature**

because Twilio delivers the voice in separate utterance chunks.

Mercury now fails closed unless:

1. a valid Zulu timestamp is identified,
2. the temperature occurs **after that Zulu timestamp**, and
3. the temperature occurs **before the next “automated weather observation” header**.

A regression test was added for this exact cross-loop failure mode.

---

# OPEN experiments / do not assume

The following Grok conclusions are leads, not production facts:

1. **Can LAX call duration be extended?**  
   Grok observed ~63–91 s drops even with a 600 s Twilio Pause/TimeLimit. Test whether this is ASOS-side hangup, Twilio behavior, recording/TwiML behavior, transcription behavior, or something fixable.

2. **Is MM:00 universally optimal?**  
   Reproduce a controlled KLAX grid and run a KDEN :00 grid. Search neighboring fire offsets if useful rather than assuming :00 forever.

3. **Is cycle 1 always MM−1?**  
   Treat as an observed pattern, not a rule. Gate by spoken Zulu minute, not by cycle number alone.

4. **Does KLAX/KDEN always update every minute?**  
   Measure consecutive valid times over longer holds/redials. Detect repeats and skipped minutes explicitly.

5. **Is the loop phase stable?**  
   Measure ZULU→TEMP and ZULU→next-ZULU distributions over many calls and times of day.

6. **Can continuous coverage be improved beyond drop + redial?**  
   Try TwiML/recording/transcription variants, direct audio capture, or other legal listen-only transport paths. Do not treat “cannot hold” as settled.

7. **What is the true earliest usable proof?**  
   Race phone valid-time + temperature against Synoptic, TGFTP, AviationWeather, MADIS, and any future CSS-Wx OMO path on the same observation minute.

8. **KDEN controlled grid**  
   Reproduce at least three consecutive MM:00 starts. This is the most valuable next station-specific measurement suggested by the prior run set.

---

# Storage / related live records

The live ASOS voice shadow service uses the persistent Railway volume mounted at `/data`.

Relevant live files:

- `/data/asos_voice_shadow.jsonl` — accepted structured ASOS voice proofs / voice status records.
- `/data/twilio_shadow_budget.json` — cost-cap reservation ledger.
- `/data/synoptic_shadow.jsonl` — Synoptic shadow/race observations.

This document is the narrative baseline; the JSONL files remain the machine/audit record for actual Mercury runs.


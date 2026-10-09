# Low-latency ASOS observation sources — research (2026-10-09)

Question: how can Mercury reliably receive the **same public ASOS observation**
that the HF-ASOS telephone line speaks, as soon as it exists, using legitimate,
non-disruptive paths — and how do the alternatives compare on latency,
reliability, coverage, cost and complexity?

Stations in scope (from `engine/config.json`): KNYC, KDEN, KPHL, KMDW, KAUS, KMIA, KLAX.

---

## 1. Bottom line

1. **The voice outlets are the only public path that delivers the 1-minute
   observation in tens of seconds.** Every machine-readable 1-minute feed
   (FAA → MADIS → Synoptic/vendors) currently arrives **~2–5 min** after the
   observation. Nothing public delivers it in single-digit seconds.
2. **The voice message is whole °C, the same precision as the OMO wire.**
   The ASOS guide's own examples read "TEMPERATURE TWO ZERO CELSIUS". The phone
   wins on latency, not precision. Exact whole-°F values still only come from
   the METAR T-group, the 6-hour groups, DSM and CLI.
3. **For your seven stations there is no 1-minute radio broadcast to receive
   with an SDR.** KNYC isn't an airport. KDEN, KMDW, KAUS and KLAX publish the
   ASOS as phone-only. At KPHL (133.4) and KMIA (119.15) the ASOS frequency is
   the D-ATIS frequency, and FAA rules forbid the two broadcasting at the same
   time. SDR helps only for ATIS (hourly) and FIS-B (minutes).
4. **KNYC has no 1-minute or 5-minute machine feed at all.** It is absent from
   the public MADIS files, and Wethr.net lists no 5-min/1-min feed for it. For
   Central Park the phone line is the *only* public minute-level path. That is
   why it is congested, and why no amount of engineering on other feeds
   replaces it for NYC.
5. **The highest-value untested route is the FAA's own SWIM feed.** CSS-Wx
   publishes a dataset called *"Surface Weather Observations – One Minute
   Observations (OMO)"* ("generated every minute") plus METAR/SPECI. It sits
   upstream of MADIS, so it should beat the 2–5 min MADIS path, but its
   latency, public (SCDS) availability and KNYC coverage are **unverified**.
   Measure it before relying on it.
6. **Settlement changed.** Since late Aug 2026 every series in the config
   (KXHIGHNY/DEN/PHIL/CHI/AUS/MIA/LAX, KXLOWNY) resolves to **The Weather
   Company** (`weather.com/kalshi`), not the NWS CLI directly. TWC's portal
   still keys on the NWS CLI (`cliId`) and marks values preliminary → official.
   See §3.

**Recommended stack:** phone (fast, best-effort; only where the line carries
OMO) → FAA CSS-Wx OMO (to be measured) → MADIS/Synoptic OMO (2–5 min, whole °C)
for the minute layer; NWWS-OI + D-ATIS + CSS-Wx METAR for the exact-°F hourly,
SPECI and 6-hour layer; DSM via NWWS-OI with IEM AFOS as fallback. Details in §6.

---

## 2. Facts that constrain every option

| Fact | Source |
|---|---|
| The ASOS computes the 5-min average temperature once a minute, rounds to whole °F (half up), converts to 0.1 °C. METAR body and OMO carry whole °C; the T-group carries 0.1 °C. | ASOS User's Guide §3.1.2 |
| Each One-Minute Observation (OMO) covers the 60 s ending at M+00 and **is released at M+23 s**. | ASOS User's Guide §5.2 |
| "The information contained in the ground-to-air radio message and the telephone dial-in message are identical." Spoken at 100 wpm, temperature in whole °C. | ASOS User's Guide §6.5 |
| At **staffed/towered** sites the facility chooses whether voice outlets carry the **Last Transmitted Observation (METAR/SPECI)** or the **OMO**. **Unstaffed sites must always broadcast OMO.** The ASOS defaults to OMO after a reboot. The setting governs the telephone too: in LTO mode the phone goes quiet after a COR until the next METAR. | FAA JO 7900.5E, App. H and §3.7 note |
| The ASOS radio broadcast must not run simultaneously with ATIS. | FAA JO 7900.5E App. H a(1) |
| ATIS is updated on receipt of each official hourly/special observation, not every minute. | AIM 7-1; cfinotebook summary |
| The FAA passes OMO temperature to NWS in whole °C, while ASOS records whole °F. | IEM news #1290; Synoptic HF-ASOS docs |
| NCEI's 1-minute archive has whole-°F fidelity but is collected by phone and "delayed by 12-36 hours". | IEM news #1469 |

Consequences for the engine:

- A voice or OMO reading of *c* °C proves `max ≥ wholeC_floor(c)`, as
  `decode.py` already does. It is exact only when *c* is a multiple of 5.
- Latency floor for any 1-minute path: the observation exists at M+00 and is
  released at M+23 s.

---

## 3. Settlement source changed to The Weather Company

Verified on 2026-10-06 from Kalshi's public API:

- `GET /trade-api/v2/series/KXHIGHNY` returns `settlement_sources: [{"name": "The
  Weather Company", "url": "https://weather.com/kalshi"}]`. KXHIGHDEN, KXHIGHPHIL,
  KXHIGHCHI, KXHIGHAUS, KXHIGHMIA, KXHIGHLAX and KXLOWNY show the same; all
  updated 2026-10-01.
- Market `rules_primary`: *"If the maximum temperature recorded at New York City
  (CLINYC) for Oct 6, 2026, is greater than 70° fahrenheit according to The
  Weather Company…"*. `rules_secondary` warns that preliminary TWC data "may be
  subject to rounding and conversion differences from the final reported value."
- Contract terms (GLOBALTEMPERATURE) list the Source Agencies in order: TWC,
  then NWS, then the national weather service. Only the first official
  non-preliminary report counts.
- TWC's portal API (`weather.com/kalshi/api/climate/primary?date=…`) returns
  per-station `maxTemp`/`minTemp` keyed by the NWS `cliId`, with
  `status: preliminary | official`. It reads as a relay of the NWS CLI. A
  third-party write-up dates the switch to 2026-08-27.

Implications (not investigated further here):

- The physical observation is still the ASOS, so this research stands.
- `docs/README.md` and `research/` assume NWS-CLI settlement. Re-validate the
  decode rules against TWC "official" values for post-Aug-27 days.
- `weather.com/kalshi` preliminary values may be a new reveal trigger the
  market reacts to. It is worth logging their update times next to DSM/CLI.

---

## 4. Path-by-path findings

### 4.1 ASOS telephone dial-in (current method)

- **What:** the same voice message as the radio. It carries the OMO at
  unstaffed sites, and OMO *or* the last METAR at towered sites (facility's
  choice).
- **Latency (estimate, not measured here):** OMO released at M+23 s. You then
  wait for the loop to reach the temperature, plus transcription, so the new
  value should be heard **~30–90 s after the minute ends**. Your ~45 s loop
  (two loops ≈ 90 s) sets the spread; your own call logs can tighten this. It
  is the only public route in the tens-of-seconds class.
- **Reliability:** each station publishes one dial-in number, and busy signals
  are inherent. The ASOS guide describes "a dial-in telephone number provided at
  each ASOS location"; I found no documentation of multiple voice ports. Auto
  disconnect after ~2 loops is site behaviour you can't change.
- **Precision:** whole °C.
- **Published numbers (Chart Supplement via AirNav):**
  | Station | ASOS voice outlets | D-ATIS |
  |---|---|---|
  | KDEN | phone only, 719-204-1223 | 125.6 arr / 134.025 dep |
  | KPHL | 133.4 (= ATIS arr freq), phone 267-404-1002 | 133.4 arr / 135.925 dep |
  | KMDW | phone only, 773-884-4424 | 132.75 |
  | KAUS | phone only, 512-369-7881 | 124.4 |
  | KMIA | 119.15 (= ATIS arr freq), phone 645-231-5974 | 119.15 arr / 133.675 dep |
  | KLAX | phone only, 310-602-6051 | 133.8 arr / 135.65 dep |
  | KNYC | not an airport; no Chart Supplement entry (you already have the number) | — |
- **OMO vs METAR mode at towered sites:** all six airports are towered, so their
  phones may be in METAR mode while the tower is open. Check by logging the
  spoken Zulu time. If it advances every minute the line is OMO; if it sticks
  at the METAR time (:51–:56) the line adds nothing over METAR feeds. KNYC is
  unstaffed and must be OMO.
- **Ways to improve access without crowding other callers:**
  1. **Call only when it can change a decision.** Use the OMO wire or METARs to
     arm calls only when the running max is within one whole-°C step of a live
     bucket boundary, during the plausible peak window. This cuts call volume
     an order of magnitude and frees the line for others.
  2. **Hang up as soon as you've heard the first new-minute readout.** Don't
     ride the second loop if you already have the value.
  3. **Back off on busy** with jittered exponential retry (e.g. 5 s, 10 s,
     20 s, capped). Never dial one number from parallel trunks.
  4. **Validate each transcription** against the spoken Zulu time and the
     previous minute (ASOS itself flags >10 °F/2-min jumps as missing). Treat
     the phone as a *trigger*, not a proof, until the value is plausible.
  5. **Ask NWS directly** whether KNYC's one-minute data can be obtained from a
     networked source (ASOS Program / AOMC, aomc@noaa.gov). The ASOS guide says
     "OMO data from all ASOS locations will be made available to users upon
     request" in the final network design. It costs one email.
- **Not an option:** the ASOS "remote user dial-in port" (modem, password,
  authorized users only); toll-free relay services (AnyAWOS-style), which bridge
  to the same single line and add no capacity.

### 4.2 ASOS VHF ground-to-air broadcast + SDR

- **Ideal in principle:** a continuous, contention-free copy of the phone
  message. The AIM describes AWOS broadcasts as a 20–30 s message updated each
  minute, engineered for 25 NM; ASOS ground-to-air works the same way. Receiving US aviation-band broadcasts is
  generally lawful; get your own legal advice on republishing.
- **For these stations: not available.** See the table in §4.1. KPHL/KMIA's
  ASOS frequency carries ATIS whenever ATIS runs, and JO 7900.5E forbids
  simultaneous ASOS + ATIS broadcast.
- **Where it does help:** an SDR on the ATIS frequency gives an independent
  path for the hourly METAR/SPECI. It duplicates D-ATIS (§4.3), so only bother
  if you want an internet-independent copy. (KPHL and KMIA are towered and listed
  as continuously attended, so their ASOS audio would only go out if ATIS were off.)

### 4.3 ATIS / D-ATIS

- **What:** updated per official hourly/special observation. D-ATIS text
  includes the full METAR remarks **with the T-group**. Example, KDEN 1453Z:
  `18/01 … T01830011`, i.e. 18.3 °C = 65 °F exact.
- **Access:** `https://atis.info/api/KDEN` (redirected from
  `datis.clowd.io/api/KDEN`) returns JSON for arr/dep with `updatedAt`. All
  six airports have D-ATIS. KNYC has none.
- **Latency:** set by when the controller publishes the new ATIS after the
  METAR, so it can lead or lag NWS distribution. **Unmeasured — log it next to
  NWWS receipt times.**
- **Role:** a cheap, independent second source for METAR/SPECI exact-°F proofs
  and the 6-hour groups at the synoptic hours. Not minute data.

### 4.4 FAA SWIM — CSS-Wx (highest-priority experiment)

- **What:** Common Support Services–Weather is "the single provider of weather
  data … within the NAS". Its agreement-portal dataset list includes
  **"Surface Weather Observations – One Minute Observations (OMO) – Surface
  observations from AWOS/ASOS that are generated every minute"** and
  **"Surface Weather Observations – METAR/SPECI"**. Delivery is JMS (Solace);
  non-gridded products come as IWXXM/USWX/FAAWX XML.
- **Why it matters:** OMOs flow ASOS → FAA ADAS → WMSCR, and MADIS gets them
  *from* WMSCR and batch-processes every 5 min. CSS-Wx is FAA-side real-time
  messaging, so it is the most plausible public machine path faster than
  2–5 min.
- **Access routes:**
  - *SCDS* (SWIM Cloud Distribution Service): free, public, self-service at
    `portal.swim.faa.gov`, JMS over the internet, approvals often automatic.
    The rules are non-NAS-impacting use only, compression on, no duplicate
    subscriptions, and >200 GB/day users must redistribute internally.
    **Whether the CSS-Wx OMO dataset is on SCDS is unconfirmed.** FAA material
    says Wx products would go to non-NAS consumers "via combination of …
    NESG interfaces and SCDS".
  - *NESG/NEMS* (agreement portal `aa.data.faa.gov`): the dataset is listed
    there. This route uses a VPN and is aimed at airlines, vendors and research
    institutions, so expect paperwork and lead time.
- **Unknowns to measure:** end-to-end latency (OMO M+23 s → JMS receipt),
  temperature precision in the XML, station coverage (KNYC likely absent, like
  the MADIS feed it shares a collection chain with), and outage history.
- **Cost:** free. **Complexity:** medium (JMS/Solace client, XML parsing,
  FAA account and agreements).

### 4.5 FIS-B (ADS-B UAT 978 MHz) via SDR

- **What:** free FAA uplink. The AIM product table lists METAR/SPECI with a
  "1 minute (where available)" update interval and a 5-minute transmission
  interval, plus D-ATIS ("as available" / 1 min). Surface stations carry METARs
  within a 100 NM look-ahead.
- **Receive with:** RTL-SDR + 978 MHz antenna + `dump978`/`fisb-978` +
  `fisb-decode` or `uat978_wx_test`. Needs line of sight to a UAT ground
  station near each metro.
- **Latency:** up to the 5-min transmission interval on top of upstream delay,
  so **minutes**. **Precision:** METAR-format, whole °C for 1-minute updates.
- **Role:** internet-independent fallback for METAR-class data in a metro where
  you host hardware. Low priority.

### 4.6 MADIS 1-minute ASOS ("HFMETAR"/OMO) — what the engine's `OMOFeed` uses

- **What:** FAA WMSCR → MADIS since 2015; the full 1-minute set has been
  processed since Nov 2017. "No restrictions. All observations are publicly
  accessible." Hourly files, current and previous hour reprocessed every
  5 min.
- **Public HTTP files** (`madisPublic1/data/LDAD/hfmetar/netCDF/`): checked on
  2026-10-09. They hold **5-minute samples** (12 per station-hour) in whole °C.
  KDEN, KPHL, KMDW, KAUS, KMIA, KLAX, KLGA, KJFK and KEWR are present. **KNYC
  is absent.** The repo's `config.json` marks KDEN `"omo": false`; that is now
  stale.
- **Measured file freshness (public HTTP):** see §7. The 1-minute set is
  available through MADIS's other distribution methods (not LDM).
- **Reliability:** "experimental". Synoptic reports the source was **down from
  Oct 2023 to Jan 2026**.

### 4.7 NWS text dissemination (METAR/SPECI, DSM, CLI — not OMO)

- **NWWS-OI** (XMPP push, free, credentials can take 30+ days): the product
  list includes `MTR` (METAR) and `DSM`. The NWS recommends ingesting **both**
  NWWS-OI and the satellite PID201 for >98 % availability. Up to 4 planned
  10–90 min server-farm transitions a month. The current access page lists
  `nwws-oi-bldr.weather.gov` and `nwws-oi-cprk.weather.gov`;
  `engine/nwws_adapter.py` hard-codes `nwws-oi.weather.gov`, so add failover
  across the two named hosts. One login works on one host at a time.
- **NOAAPort/SBN** (C-band, Galaxy 31): the full product set, a few seconds
  faster than IDD. **The NWS is soliciting comments on retiring SBN/NOAAPort
  as early as 31 Aug 2027** (RFI due 29 Oct 2026). Don't buy a dish for this.
- **EMWIN** (GOES-East/West HRIT 1694.1 MHz, or an FTP mirror on tgftp): free
  satellite text including observations. A satellite path with no internet
  dependency, but slower and coarser than NWWS-OI.
- **TGFTP / IDD (LDM):** in a 2026 ldm-users thread, NWS/Unidata participants
  rated TGFTP polling (rate-limited) and IDD push as the lowest-latency public
  internet METAR paths; NWWS-OI wasn't compared there. TGFTP does not carry
  HFMETAR.

### 4.8 Commercial services

| Vendor | What you get | Latency (claimed/measured) | Precision | Cost | Notes |
|---|---|---|---|---|---|
| **Synoptic Data** | 1-minute HF-ASOS as stations `<ICAO>1M` (e.g. KSLC1M) via a "low-latency provisional" stream from MADIS; 5-min blended into ASOS network; push streaming | "usually 2–5 min" | whole °C | Commercial, quote-based; 14-day trial | 1M upstream is MADIS, so it shares MADIS outages (2023-10 → 2026-01). In the ldm-users thread a user reported Synoptic sometimes sees METARs before TGFTP, and an NWS participant noted Synoptic has a data agreement with the FAA. |
| **Wethr.net** | Push API: METAR/SPECI, HF-METAR, DSM/CLI events; Wethr High/Low uses OMO (raw OMO "coming soon"); "accelerated" METAR feed (`metar8`) "seconds after they are taken" | Published receipt latency: hourly METAR median 1m11s–2m04s at the 7 stations; OMO median 2m25s, p90 ~3 min | per source | Paid tiers | Best public measurement of who-arrives-when. Accelerated METAR source not disclosed. **Lists no OMO for KNYC.** |
| **minuteTemp** | REST + WebSocket, 72 cities, "every minute where 1-minute data exists" | "~2–3 s after Kalshi receives the station batch" (index product) | °F | $14.99–$89.99/mo | Rebuilds the Kalshi Weather Index used by **hourly** markets. Upstream source undisclosed. |
| **TWC Kalshi portal** | `weather.com/kalshi/api/climate/primary`, `/api/metar` | n/a | whole °F (+°C) | free | The settlement publisher. Monitor it; don't use it as a minute feed. |

None of these delivers 1-minute ASOS faster than the OMO wire they ingest,
except possibly Wethr's undisclosed accelerated METAR path for *hourly/SPECI*
reports.

### 4.9 Ruled out

- **LiveATC / Broadcastify / WebSDR:** LiveATC's terms say "non-commercial
  (personal) use only" and forbid automated retrieval without permission. Feeds
  are volunteer-run and buffered. KiwiSDR is HF-only (≤30 MHz).
- **NOAA Weather Radio:** hourly roundups only.
- **NCEI/IEM 1-minute archive:** whole °F, but 12–36 h late.
- **Private sensors near the station:** a different observation, outside "the
  same public observation" scope (README already lists it as V2).

---

## 5. Comparison matrix

Latency is from observation minute end (M+00) to your process. "Coverage"
counts the seven stations.

| # | Path | Data | Precision | Latency | Reliability | Coverage | Cost | Complexity |
|---|---|---|---|---|---|---|---|---|
| 1 | ASOS phone (Twilio) | OMO voice (or METAR at towered sites in LTO mode) | whole °C | **~30–90 s** when connected | Low–medium: single line, busy at peaks, ~90 s cutoff | 7/7 (KNYC OMO guaranteed; 6 towered = check mode) | ~$0.01–0.02/min telephony | Done |
| 2 | ASOS VHF + SDR | same as phone | whole °C | ~30–60 s | High where it exists | **0/7** | ~$100–300 per site + host | Medium |
| 3 | FAA CSS-Wx OMO (SWIM) | OMO XML | likely whole °C (verify) | **unknown — measure**; plausibly < MADIS | FAA ops system; SCDS has no 24/7 support | ≤6/7 (KNYC likely absent; verify) | Free | Medium |
| 4 | MADIS public / Synoptic 1M / Wethr OMO | OMO | whole °C | ~2–5 min (Wethr median 2m25s) | Medium–low: "experimental", 27-month outage 2023–26 | 6/7 (no KNYC) | Free / paid | Low (already built) |
| 5 | NWWS-OI (+PID201) | METAR/SPECI, DSM, CLI | **exact °F** (T-group, DSM) | seconds after NWS issuance; METAR ≈1–2 min after obs | High with dual ingest | 7/7 | Free | Low (adapter exists) |
| 6 | FAA CSS-Wx METAR/SPECI | METAR | exact °F (T-group) | unknown; upstream of NWSTG | as #3 | 6–7/7 | Free | Medium (shared with #3) |
| 7 | D-ATIS (atis.info) | METAR inside ATIS | exact °F (T-group) | controller-dependent; unmeasured | Medium (third-party API) | 6/7 | Free | Low |
| 8 | Wethr accelerated METAR | METAR | exact °F | "seconds after taken" (vendor claim) | Vendor | 7/7 | Paid | Low |
| 9 | FIS-B via SDR | METAR (1-min where available) | whole °C / T-group | minutes | High locally | depends on site | ~$100 + host | Medium |
| 10 | EMWIN HRIT / NOAAPort dish | text products | exact °F | seconds–minutes | High; **NOAAPort may retire Aug 2027** | 7/7 | $0.3k–5k hardware | High |

Rows 1–4 serve the minute layer (whole °C). Rows 5–10 serve the
exact-°F proof layer.

---

## 6. Recommended architecture

```
                 ┌─────────────────────────── minute layer (whole °C) ───────────────────────────┐
  phone (Twilio) ─┤ fastest, gated by "is a call worth it?"; per-station OMO-mode check          │
  CSS-Wx OMO     ─┤ (after measurement) machine-readable, no line contention                     ├─► OMO floor events
  MADIS/Synoptic ─┤ always-on fallback, 2–5 min                                                  │   (wholeC_floor)
                 └────────────────────────────────────────────────────────────────────────────────┘
                 ┌─────────────────────────── proof layer (exact °F) ───────────────────────────┐
  NWWS-OI (2 hosts) + PID201 ─┐                                                                 │
  CSS-Wx METAR/SPECI ─────────┤ first-arrival wins, dedupe on (ICAO, obs time, T-group)         ├─► metar/sixhr/dsm events
  D-ATIS poll (~15 s, :50–:58)┤                                                                 │
  IEM AFOS / aviationweather ─┘ existing pollers stay as last-resort fallback                   │
                 └────────────────────────────────────────────────────────────────────────────────┘
```

Design rules:

1. **First arrival wins, every source is idempotent.** Key events by
   `(station, obs_minute, channel, value)` so duplicates across paths are free.
   `KillEngine` already ratchets monotonically.
2. **Tag each event with `source` and `seen_ts`.** Log arrival deltas between
   paths. That gives you a live latency league table per station, and it is
   the only way to settle the unknowns in rows 3, 6, 7 and 8.
3. **Phone gating, not phone polling.** Arm a call when (a) the station is in
   its peak window, (b) the running max is within one °C step of a priced
   bucket boundary, and (c) the line was last confirmed in OMO mode.
   Otherwise rely on the wire. This keeps you a light, non-disruptive caller
   and puts your call budget where it pays.
4. **Health checks per source.** Watch for staleness (no new OMO in N min),
   phone busy-rate, NWWS disconnects (expect planned transitions) and MADIS
   outages. On failure, the next layer takes over automatically. Nothing
   upstream of the engine should be single-path.
5. **KNYC special case:** phone is the only minute path. Pair it with fast
   proof-layer ingest (NWWS-OI METAR + 6-hr + DSM), and send the NWS request
   in §4.1 step 5.

---

## 7. Measured here

- **Kalshi settlement sources:** verified via public API (§3).
- **MADIS public 1-minute/5-minute file** (2026-10-09, ~15 min of 20 s
  polling, `scratchpad` script). Interim result after the first 5 minutes: at
  receipt, the newest observation in the file was **~9–15 min old**. At
  15:24:04Z the newest KMIA/KAUS sample was 15:15 and KDEN's was 15:10. The
  `Last-Modified` header alternated between two values (15:16:14 and 15:21:32),
  i.e. load-balanced mirrors serving different file versions. Polling the
  public files is therefore materially slower than the 2–3 min that Wethr and
  Synoptic report for their feeds.
- **Station coverage of the OMO wire:** KNYC absent; the other six present
  (§4.6).
- **D-ATIS content:** KDEN D-ATIS carries the T-group (§4.3).

## 8. Next actions

1. Register on the SWIFT portal (`portal.swim.faa.gov`) and check whether CSS-Wx
   *Surface Weather Observations – OMO* and *METAR/SPECI* are offered on SCDS.
   If not, request them through the FAA agreement portal (NESG). Measure
   latency and coverage for a week.
2. For each towered station, log the phone's spoken Zulu time for a day to
   classify OMO vs METAR mode. Drop phone calls at stations stuck in METAR mode.
3. Get NWWS-OI credentials (pending per `NWWS_APPLICATION.md`). Point the
   adapter at `nwws-oi-bldr` / `nwws-oi-cprk` with failover.
4. Add a D-ATIS poller for the six airports (window :50–:58 and around
   SPECIs) as a second exact-°F path, and log its lead/lag against NWWS.
5. Flip KDEN to `"omo": true` after confirming in a replay that its whole-°C
   floors behave.
6. Email NWS ASOS/AOMC about networked one-minute data for KNYC.
7. Separately: re-validate the decode rules against TWC "official" values for
   days after 2026-08-27.

## 9. Open questions (not verifiable from public docs)

- Number of simultaneous callers per ASOS voice line (no public spec found).
- CSS-Wx OMO latency, precision and KNYC coverage.
- The upstream source of Wethr's "accelerated" METAR feed and of minuteTemp's
  1-minute data.
- D-ATIS publication lag relative to the METAR at each airport.

## Sources

- NWS, *ASOS User's Guide* (aum-toc.pdf): https://www.weather.gov/media/asos/aum-toc.pdf — §3.1.2, §5.2, §6.5, Fig. 4
- FAA Order JO 7900.5E w/ Change 1, *Surface Weather Observing*: https://www.faa.gov/documentLibrary/media/Order/JO_7900.5E_with_Change_1.pdf — App. H, §3.7 note
- FAA AIM ch. 7 §1 (AWOS/ASOS, FIS-B product table): https://www.faa.gov/air_traffic/publications/atpubs/aim_html/chap7_section_1.html
- AirNav airport pages (Chart Supplement data): https://www.airnav.com/airport/KDEN (and KPHL, KMDW, KAUS, KMIA, KLAX)
- FAA Data Agreement Portal, CSS-Wx datasets: https://aa.data.faa.gov/data/service.jsf?uuid=02422d2b-690f-42ba-9ce3-7a72f830f01c
- FAA SCDS guideline v1.1 (2024): https://www.faa.gov/sites/faa.gov/files/air_traffic/technology/swim/governance/SCDS-Guideline-Document_v1.1_09.11.2024
- FAA SCDS user guide: https://files.swim.faa.gov/documents/user_guide.pdf
- FPAW, *CSS-Wx data availability*: https://fpaw.aero/sites/default/files/197/1a5-kratky-fpaw-swim.pdf
- MADIS 1-minute ASOS: https://madis.ncep.noaa.gov/madis_OMO.shtml and variable list https://madis.ncep.noaa.gov/sfc_OMO_variable_list.shtml
- Synoptic, High Frequency ASOS: https://docs.synopticdata.com/services/high-frequency-asos
- IEM news #1290 (HFMETAR precision): https://mesonet.agron.iastate.edu/onsite/news.phtml?id=1290
- IEM news #1469 (1-minute archive): https://mesonet.agron.iastate.edu/onsite/news.phtml?id=1469
- Unidata ldm-users 2026 thread on lowest-latency METAR: https://mailinglists.unidata.ucar.edu/archives/ldm-users/2026/msg00034.html (and msg00035, msg00039)
- NWS NWWS: https://www.weather.gov/nwws/ ; product list https://www.weather.gov/nwws/listofproducts
- NWS NOAAPort (retirement RFI): https://www.weather.gov/noaaport/
- NWS EMWIN: https://www.weather.gov/emwin/
- Wethr.net latency: https://wethr.net/latency ; API docs https://wethr.net/api_docs.php
- minuteTemp: https://minutetemp.com/
- LiveATC terms: https://www.liveatc.net/legal/
- Kalshi API (series/markets) and contract terms: https://api.elections.kalshi.com/trade-api/v2/series/KXHIGHNY ; https://assets.kalshi.com/contract_terms/GLOBALTEMPERATURE.pdf
- TWC Kalshi portal: https://weather.com/kalshi
- D-ATIS API: https://atis.info/api/KDEN
- FIS-B decoders: https://github.com/rand-projects/fisb-decode ; https://github.com/mutability/dump978

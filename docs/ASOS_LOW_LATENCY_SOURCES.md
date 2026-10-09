# Low-latency ASOS observation sources — research (2026-10-09)

Question: how can Mercury reliably receive the **same public ASOS observation**
that the HF-ASOS telephone line speaks, as soon as it exists, using legitimate,
non-disruptive paths — and how do the alternatives compare on latency,
reliability, coverage, cost and complexity?

Stations in scope (from `engine/config.json`): KNYC, KDEN, KPHL, KMDW, KAUS, KMIA, KLAX.

---

## 1. Bottom line

(Updated after a second research pass; see §1A for the measurements.)

0. **The fastest daily-market bots are ~2 minutes ahead of every machine
   1-minute feed (§1B, KLAX case).** Every station on the 1-minute
   (HF-ASOS/OMO) stream reaches Kalshi/Synoptic in one batch about
   **M+2:15–2:40**. **Kalshi republishes the batch for free** at
   `GET /trade-api/v2/live_data/weather/{city}?detailed=true` (keyless), for
   69 airports in 13 metros including KMIA, KPHL, KLAX and KMDW, but **not
   KNYC, KDEN or KAUS**. On KLAX, though, the decisive moves started at
   **M+21 s (Aug 29) and M+53 s (Aug 30)**. Both buckets were at 1¢ before
   the batch existed. The batch is a solid continuous fallback, but it
   **cannot win the single-minute events**; that needs voice-line speed.
1. **The voice outlets are the only public path that delivers the 1-minute
   observation in tens of seconds.** That makes the phone the only way to be
   *ahead* of the M+2:17 batch, by roughly 1–2 minutes. One shared dial-in
   line cannot give one caller continuous coverage without shutting out
   everyone else; the ~90 s auto-disconnect is how the line is shared. So
   constant phone monitoring isn't achievable within the non-monopolizing
   constraint. Use the machine batch for continuous coverage and the phone as
   an opportunistic lead. Polling the public MADIS HTTP files, as `OMOFeed`
   does, measured **9–20 min** here (§7), far behind the batch.
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
5. **The FAA's own SWIM feed is the only machine path that *might* beat the
   batch.** CSS-Wx publishes *"Surface Weather Observations – One Minute
   Observations (OMO)"* ("generated every minute") plus METAR/SPECI. It is
   only worth the effort if it taps the FAA collection before the stage that
   adds most of the 2¼ minutes. Its latency, SCDS availability and KNYC
   coverage are **unverified**. The NESG route is aimed at operational
   industry partners, needs your own VPN connectivity, and takes 3–4 months
   to onboard. Ask the questions in §4.4 before committing.
6. **Settlement changed.** Since late Aug 2026 every series in the config
   (KXHIGHNY/DEN/PHIL/CHI/AUS/MIA/LAX, KXLOWNY) resolves to **The Weather
   Company** (`weather.com/kalshi`), not the NWS CLI directly. TWC's portal
   still keys on the NWS CLI (`cliId`) and marks values preliminary → official.
   See §3.

7. **The constraint may loosen soon.** The NWS ASOS program's own plan for
   "ASOS 2.0" (new Campbell Scientific processors) lists **"IP communications"**
   and **"Ubiquitous access to OMO (goal)"**. Its 2026 milestone is to
   "replace all copper voice and data lines with Internet Protocol
   communications". As of the NWS equipment sheet (Mar–Jul 2025) all seven
   stations still run legacy processors. Ask the ASOS program office what OMO
   access will look like, and whether KNYC is included.

**Recommended stack:** the voice line is the competitive path for
single-minute peaks at OMO-mode stations; per §1B the first movers trade
20–55 s after the minute. Kalshi `live_data/weather` (free) or Synoptic 1M
push (paid) is the continuous fallback at ≈M+2:15–2:40. FAA CSS-Wx OMO is
worth pursuing only if measured under ~30 s. Exact °F comes from NWWS-OI +
D-ATIS + CSS-Wx METAR for the hourly, SPECI and 6-hour reports, and from DSM
via NWWS-OI with IEM AFOS as fallback. Details in §6.

---

## 1A. What the fast bots actually see (measured 2026-10-09)

**Kalshi's own receipt times.** Kalshi's hourly temperature markets settle on
the *Kalshi Weather Index*. Per Kalshi's CFTC filing, its primary source is
"Synoptic the 1M HF-ASOS network 258, air_temp, exact observation minute
only", received over a WebSocket, with a 5-minute receipt deadline. The free
API exposes every member station's reading together with Kalshi's
`received_at_ms`:

| Event minute (UTC) | Stations | Kalshi received |
|---|---|---|
| 15:46 | KLGA1M, KEWR1M, KMIA1M, KPHL1M, KLAX1M, KMDW1M, KORD1M … | 15:48:16–15:48:19 |
| 15:47 | same | 15:49:24–15:49:26 |
| 15:48 | same | 15:50:41–15:50:43 |
| 15:49 | same | 15:51:29–15:51:33 |
| 15:50 | same | 15:52:17–15:52:19 |

- Every 1M station in every city arrives in the **same ~3-second window**,
  about **2 min 16–26 s** after the minute. That points to one upstream batch
  (FAA → MADIS → Synoptic) per minute, so no vendor on this chain can be much
  faster than the chain itself.
- Values are whole-°C conversions (71.6 = 22 °C, 86.0 = 30 °C, 87.8 = 31 °C).
  Same precision as the phone.
- Readings appear on the free API as `code: "pending"` within ~1–2 s of
  Kalshi receiving them. A second sample put receipt at M+2:19 to M+2:36
  (§7), so plan for **≈M+2:15–2:40**.

**Who has what:**

| Station (daily market) | On 1M stream / Kalshi index? | Fastest public minute path |
|---|---|---|
| KNYC | **No** (Kalshi's NYC index uses KLGA, KEWR, KTEB, KCDW, KHPN, KFRG, KSMQ, KISP instead) | phone only |
| KMIA | Yes (miami index) | phone, then Kalshi API ≈M+2:17 |
| KPHL | Yes (phl-delaware-valley) | phone, then Kalshi API |
| KLAX | Yes (la-coastal) | phone, then Kalshi API |
| KMDW | Yes (chicago) | phone, then Kalshi API |
| KDEN | On the 1-min stream (Wethr feed list, MADIS), not in a Kalshi index | phone, then Synoptic 1M push (paid) or MADIS |
| KAUS | On the 1-min stream (Wethr feed list, MADIS), not in a Kalshi index | phone, then Synoptic 1M push (paid) or MADIS |

**So how do bots "react in seconds"?** *Corrected by §1B.* Many react
seconds after the M+2:17 batch (Synoptic push, Kalshi's index API, or vendors
such as Wethr with a 2m25s median). The **first movers on the daily markets
are faster**: on KLAX they traded 21–53 s after the observation minute.
Among public channels, only the ASOS voice line delivers that. The FAA's
CSS-Wx OMO is the only other conceivable channel, and its latency is
unknown. At KNYC no machine stream exists at all, so the voice line is the
only minute-level path. That is why it is busy at peaks.

**The single-line constraint is structural.** Each ASOS publishes one dial-in
number. The ASOS also has a separate *remote-user data modem* that NCEI
dials on an 11-hour cycle to collect the whole-°F 1-minute archive, but
access to it is password-controlled and authorized-only. There is no public
second line. The only fair levers on the voice line are:

- Low call-setup latency, so each attempt reaches the switch quickly.
- Prompt hang-up once the new minute is heard.
- Polite, jittered retry on busy.

None of these turn one shared line into continuous private coverage.

---

## 1B. Case study: KLAX, Aug 29 and Aug 30 2026 (four clocks cross-referenced)

Sources: DSMLAX/CLILAX via IEM AFOS (with issuance times), METAR/SPECI and
MADIS 5-minute HF-METAR via IEM, and Synoptic 1-minute KLAX1M with arrival
times via Kalshi `live_data/weather/la-coastal?detailed=true`. Those points
are a pre-launch backfill (`receipt_basis: synoptic_latency`), so arrival =
observation + Synoptic's measured ingest latency, minute-granular. Trades
come from Kalshi `markets/trades` (exchange timestamps, ms). NCEI's
whole-°F 1-minute archive for KLAX is **missing Aug 27–30**, so it could not
be used.

**Aug 29 (KXHIGHLAX-26AUG29; settled "87° or above")**

| Clock | Time (UTC) | What |
|---|---|---|
| Sensor (ASOS minute label) | **19:31** | KLAX1M = 31 °C (87.8 °F) for **exactly one minute**; 30 °C at 19:30 and 19:32 |
| Official, after the fact | 19:31 (11:31 AM LST) | DSM and CLI: **MAXIMUM 87 at 11:31 AM** |
| Market, first sweep | **19:31:21.166** | One aggressive order swept "87° or above" YES 0.55→0.75 across ~80 levels; 7 ms later "85° to 86°" sold 0.43→0.29 |
| Market, done | 19:32:00–19:32:15 | 85–86° at 0.01–0.07; 87+ at 0.91–0.99 |
| 1-minute machine feed | ≈19:33:15–19:34:00 | Synoptic/Kalshi arrival of the 19:31 reading (backfill says 19:34:00; live tests give M+2:15–2:40) |
| 5-minute HF-METAR | never | 19:30 and 19:35 samples both 30 °C, so the 31 °C minute never appears |
| METAR | 19:53 | T0294 → 85 °F (the hourly METARs never showed 87) |
| First official publication of 87 | 22:07 | DSM (valid to 14:00 LST) |

**Aug 30 (KXHIGHLAX-26AUG30; settled "84° or above")**

| Clock | Time (UTC) | What |
|---|---|---|
| Sensor | **18:12** | KLAX1M first shows 29 °C (84.2 °F), proving max ≥ 84; plateau 18:12–18:18 |
| Official | 18:18 (10:18 AM LST) | DSM/CLI: **MAXIMUM 84 at 10:18 AM** |
| Market, first sweep | **18:12:53.531** | "84° or above" YES 0.74→0.87; "82° to 83°" sold 0.26→0.13 in the same 30 ms |
| Market, done | ~18:13:15 | 82–83° at 0.01–0.04; 84+ at 0.88–0.99 |
| 1-minute machine feed | ≈18:14:15–18:15:00 | arrival of the 18:12 reading |
| METAR | 17:53 / 18:53 | 83 °F / 81 °F (never 84) |

**What the cross-reference establishes**

1. **"Observation time" in these feeds is the sensor minute, not publication
   time.** The 1-minute stream labels the max minute 19:31. The ASOS's own
   DSM/CLI time of max is 11:31 LST, which is 19:31Z. The 5-minute samples
   carry the same labels. Publication (`received_at`) is a separate field,
   2–3 minutes later.
2. **Kalshi/Synoptic would not have been fine for these events.** The
   decisive repricing started 21 s (Aug 29) and 53 s (Aug 30) after the
   sensor minute and was complete about 1–1.5 min before the 1-minute feed
   delivered the reading.
3. **The first movers had the one-minute observation at voice-line speed.**
   No METAR or SPECI was issued near either minute. The 5-minute feed never
   showed the Aug 29 value. The only public outlets carrying the 1-minute
   OMO that fast are the ASOS voice outlets; KLAX's is the phone. A non-public
   FAA data path (e.g. CSS-Wx OMO) can't be ruled out from this data. The
   variable lag (21 s vs 53 s) fits listening to a looping voice message
   better than a fixed-latency data feed.
   - Caveat: 19:31:21 is ~2 s earlier than the ASOS guide's nominal "OMO
     available at M+23 s". So either the voice outlet updates a little
     sooner than that 1998 figure, or the station clock is offset by a few
     seconds.
4. **DSM/CLI "time of max" appears to be the *last* minute the max held.** On
   Aug 30, 29 °C held 18:12–18:18. Since the official max is 84, every one of
   those minutes was 84 °F, yet the reported time is 10:18 LST (18:18Z).
5. **Precision:** 31 °C → {87, 88} °F, floor 87; 29 °C → {84, 85}, floor
   84. In both cases the floor was enough to kill the bucket below, which is
   why the market could act on a whole-°C voice reading.

**Implication for Mercury:** for single-minute peaks at OMO-mode stations,
competing requires the voice line (or a proven sub-30 s data path). The free
Kalshi batch is the continuous fallback, and it still beats MADIS polling by
an order of magnitude.

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
- **Ways to improve access without crowding other callers:** (Gating calls
  on expectations was dropped: jumps arrive unannounced. The continuous layer
  is now the machine batch in §1A.)
  1. **Cut call-setup latency, not call count.** When the line frees, the
     first INVITE to reach the far-end switch wins. Measure Twilio's
     dial-to-answer time per number. Compare with a SIP trunk from a carrier
     interconnecting in the station's LATA (NYC for KNYC); one well-placed
     attempt beats many slow ones.
  2. **Hang up as soon as you've heard the first new-minute readout.** Don't
     ride the second loop if you already have the value.
  3. **Back off on busy** with jittered retry (a few seconds, capped). Never
     dial one number from parallel trunks.
  4. **Validate each transcription** against the spoken Zulu time and the
     previous minute (ASOS itself flags >10 °F/2-min jumps as missing). Treat
     the phone as a *trigger*, not a proof, until the value is plausible.
  5. **Ask NWS directly** whether KNYC's one-minute data can be obtained from a
     networked source (ASOS Program / AOMC, aomc@noaa.gov). The ASOS guide says
     "OMO data from all ASOS locations will be made available to users upon
     request" in the final network design. It costs one email.
- **Not an option:** the ASOS "remote user dial-in port" (modem, password,
  authorized users only; NCEI's modem bank dials ~960 ASOS on an 11-hour cycle
  for the whole-°F 1-minute archive); toll-free relay services (AnyAWOS-style),
  which bridge to the same single line and add no capacity.
- **Coming change:** the ASOS program plans to replace "all copper voice and
  data lines with Internet Protocol communications" alongside ASOS 2.0
  (2026 milestone). How the public dial-in will behave after that (capacity,
  numbers, or retirement) isn't published. Ask the ASOS PMO
  (suad.asos.pmo@noaa.gov) and watch for service change notices.

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
    there. Per the FAA's own FPAW briefing, "NESG SWIM connections are
    reserved for industry partners that require operational data usage (e.g.,
    airlines, vendors, etc.)". The consumer must establish its own IP service
    connection (VPN) to the FAA security gateway. Onboarding takes "3wks –
    month" for the test environment and **"3–4 months"** for operations. This
    matches what you were told: in practice it's a commercial/research
    channel, and the cost is your connectivity and engineering. FAA SWIM data
    itself is free.
- **Unknowns to measure:** end-to-end latency (OMO M+23 s → JMS receipt),
  temperature precision in the XML, station coverage (KNYC likely absent, like
  the MADIS feed it shares a collection chain with), and outage history.
  Given the M+2:17 single-batch pattern in §1A, CSS-Wx only helps if it taps
  the FAA collection *before* the stage that adds most of those two minutes.
  Ask that directly.
- **Questions to put to the FAA** (Data-To-Industry@faa.gov, or via the SWIFT
  portal):
  1. Is the CSS-Wx OMO dataset offered on SCDS, or NESG only?
  2. What is typical latency from observation minute to JMS publication?
  3. Is KNYC included, and are temperatures whole °C or finer?
  4. Can a non-operational research/commercial consumer subscribe?
- **Cost:** data free; SCDS free; NESG requires your own VPN/connectivity
  setup. **Complexity:** medium (JMS/Solace client, XML parsing, FAA account
  and agreements).

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
- **Measured file freshness (public HTTP):** 9–20 min in a 15-minute test
  (§7). The full 1-minute set is offered through MADIS's other distribution
  methods (not LDM), and vendors get it in 2–5 min.
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
| **Kalshi `live_data/weather`** | Free, keyless REST: per-minute city index plus, with `detailed=true`, every member station's 1-minute reading (`pending` before final), `received_at_ms`, QC code; 13 metros, 69 stations | ≈M+2:17 receipt (measured, §1A) + publication lag (§7) | whole °C (shown in °F) | Free | Covers KMIA, KPHL, KLAX, KMDW (+KLGA, KEWR, KORD, …); not KNYC/KDEN/KAUS. Same batch the hourly-market bots use. |
| **Synoptic Data** | 1-minute HF-ASOS as stations `<ICAO>1M` (e.g. KSLC1M) via a "low-latency provisional" stream from MADIS; 5-min blended into ASOS network; **push streaming** (WebSocket, "within 2 seconds" of Synoptic availability, higher-tier commercial plans) | "usually 2–5 min"; Kalshi receives it at ≈M+2:17 | whole °C | Commercial, quote-based; 14-day trial | 1M upstream is MADIS, so it shares MADIS outages (2023-10 → 2026-01). In the ldm-users thread a user reported Synoptic sometimes sees METARs before TGFTP, and an NWS participant noted Synoptic has a data agreement with the FAA. |
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
| 4a | **Kalshi `live_data/weather` (detailed)** | OMO via Synoptic 1M | whole °C | **≈M+2:17** + publication lag (§7) | Same upstream as 4b; Kalshi-run | 4/7 (MIA, PHL, LAX, MDW) | **Free** | Low |
| 4b | Synoptic 1M push / Wethr OMO | OMO | whole °C | ≈M+2:17 (Kalshi's receipt of Synoptic push); Wethr median 2m25s | Medium–low: "experimental", 27-month outage 2023–26 | 6/7 (no KNYC) | Paid | Low |
| 4c | MADIS public HTTP files (current `OMOFeed`) | 5-min OMO subset | whole °C | **9–20 min measured** (§7) | as 4b | 6/7 (no KNYC) | Free | Built |
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
  phone (Twilio) ─┤ opportunistic lead (≈M+0:30–1:30) when the line is free; OMO-mode stations  │
  Kalshi live_data┤ continuous, free, ≈M+2:17 (MIA/PHL/LAX/MDW); poll ~:15–:35 s past each min ├─► OMO floor events
  Synoptic 1M push┤ same batch for DEN/AUS (paid), ≤2 s after Synoptic has it                    │   (wholeC_floor)
  CSS-Wx OMO     ─┤ (after measurement) only if it beats the M+2:17 batch                         │
  MADIS HTTP     ─┤ last resort (measured 9–20 min)                                               │
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
3. **The machine batch is the continuous layer; the phone is the lead.**
   Jumps are unpredictable, so gating calls on expectations doesn't work.
   But a single shared line can't be held continuously either. Run the
   machine batch continuously for every station that has it. That bounds
   your worst case at ≈M+2:17, the same as the bots. Treat the phone as a
   bonus that sometimes gets you ~1–2 min ahead, with fast call setup, prompt
   hang-up and jittered retry on busy. Only call stations whose line is
   confirmed in OMO mode.
4. **Health checks per source.** Watch for staleness (no new OMO in N min),
   phone busy-rate, NWWS disconnects (expect planned transitions) and MADIS
   outages. On failure, the next layer takes over automatically. Nothing
   upstream of the engine should be single-path.
5. **KNYC special case:** phone is the only minute path. Pair it with fast
   proof-layer ingest (NWWS-OI METAR + 6-hr + DSM). Watch the eight NYC-area
   1M stations on Kalshi's free NYC index (KLGA, KEWR, KTEB, …) as a
   *context* signal only; they are not the settlement station. Send the NWS
   request in §4.1 step 5.

---

## 7. Measured here

- **Kalshi settlement sources:** verified via public API (§3).
- **MADIS public 1-minute/5-minute file** (2026-10-09, ~15 min of 20 s
  polling, 15:20–15:36Z, KDEN/KMIA/KAUS):
  | File `Last-Modified` | First seen | Newest sample in file | Age of newest sample at receipt |
  |---|---|---|---|
  | 15:16:14 | 15:20:36 | 15:05 (KDEN 15:00) | 15–20 min |
  | 15:16:14 / 15:21:32 | 15:24:04 | 15:15 (KDEN 15:10) | 9–14 min |
  | 15:26:44 | 15:27:31 | 15:15 (KDEN 15:10) | 12–17 min |
  | 15:32:12 | 15:32:20 | 15:15 | 17 min |

  The file is rewritten roughly every 5 min, as MADIS documents. Newly arrived
  samples lag well behind, though: the 15:20 and 15:25 samples had not appeared
  by 15:33. `Last-Modified` also alternated between two values on successive
  requests, which suggests load-balanced mirrors serving different versions.
  **Polling the public HTTP files gave 9–20 min latency in this window**, far
  worse than the 2–3 min that Wethr and Synoptic report for their own OMO
  feeds and the 2.3 min this repo measured earlier. This is a single
  15-minute sample, so treat it as a warning, not a rate. Before trusting
  `OMOFeed`, log `seen_ts − obs_ts` for a week. If it looks like this, take the
  OMO layer from a push source (Synoptic 1M, CSS-Wx) instead.
- **Kalshi `live_data/weather` (free) timing**, two samples on 2026-10-09:
  - 15:46–15:50Z (5 minutes, 5 cities): Kalshi `received_at` **M+2:16 to
    M+2:26**, with all stations in one ~3 s window.
  - 15:55–15:58Z (4 minutes, NYC and Miami polled alternately every 3 s, so
    each city every 6 s; 52 station-minutes): `received_at` **M+2:19 to
    M+2:36** (median M+2:27).
  - Reading first visible on the free API: median **3.3 s** (max 5.8 s) after
    Kalshi's receipt. That is within the 6 s poll spacing, so Kalshi
    publishes within ~1–2 s.
  - **Total observation-minute → free API: ≈2m20s–2m40s.** A 1 s poll in the
    batch window would put you within ~1 s of anyone on Synoptic's push
    stream.
- **Station coverage of the OMO wire:** KNYC absent; the other six present
  (§4.6).
- **D-ATIS content:** KDEN D-ATIS carries the T-group (§4.3).

## 8. Next actions

1. **Today, free:** add a `KalshiIndexFeed` that polls
   `live_data/weather/{city}?last_sec=180&detailed=true` for miami,
   phl-delaware-valley, la-coastal and chicago once a second during the
   batch window (≈:10–:40 s past each minute). Emit `omo_floor` events from
   the KMIA1M, KPHL1M, KLAX1M and KMDW1M readings, `pending` included.
   That replaces the 9–20 min MADIS path with ≈M+2:17 at zero cost. Per §1B
   this is a fallback layer: it arrives after the first movers on
   single-minute peaks. Send the
   requests authenticated so they count against a published budget (Basic
   tier: 200 read tokens/s, 10 per request); limits for keyless calls aren't
   published.
2. **For KDEN/KAUS:** get a Synoptic quote for push streaming of KDEN1M and
   KAUS1M (network 258). It's the same batch Kalshi consumes.
3. Register on the SWIFT portal (`portal.swim.faa.gov`) and check whether
   CSS-Wx *Surface Weather Observations – OMO* and *METAR/SPECI* are offered
   on SCDS. If not, put the §4.4 questions to Data-To-Industry@faa.gov before
   committing to a 3–4 month NESG onboarding. Measure latency against the
   M+2:17 batch.
4. For each towered station, log the phone's spoken Zulu time for a day to
   classify OMO vs METAR mode. Drop phone calls at stations stuck in METAR mode.
5. Measure Twilio dial-to-answer time per ASOS number and compare a
   local-interconnect SIP trunk (§4.1). Faster setup is the only fair lever on
   a shared line.
6. Get NWWS-OI credentials (pending per `NWWS_APPLICATION.md`). Point the
   adapter at `nwws-oi-bldr` / `nwws-oi-cprk` with failover.
7. Add a D-ATIS poller for the six airports (window :50–:58 and around
   SPECIs) as a second exact-°F path, and log its lead/lag against NWWS.
8. Flip KDEN to `"omo": true` after confirming in a replay that its whole-°C
   floors behave.
9. Email the NWS ASOS program office (suad.asos.pmo@noaa.gov; AOMC
   aomc@noaa.gov) about (a) networked one-minute data for KNYC and (b) the
   ASOS 2.0 "ubiquitous access to OMO" goal and what the copper-to-IP
   change means for the public dial-in.
10. Separately: re-validate the decode rules against TWC "official" values for
    days after 2026-08-27.

## 9. Open questions (not verifiable from public docs)

- Rate limits for keyless `live_data` calls (authenticated budgets are
  published), and whether Kalshi's API terms cover this use. Check before
  production.
- What the ASOS 2.0 copper-to-IP change does to the public dial-in, and when
  "ubiquitous access to OMO" ships; whether KNYC will have it.
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

Second-pass sources (2026-10-09):

- Kalshi API, Get Weather Index: https://docs.kalshi.com/api-reference/live-data/get-weather-index (endpoint `https://external-api.kalshi.com/trade-api/v2/live_data/weather/{city}`)
- Kalshi CFTC self-certification, Kalshi Weather Index methodology (Greater Boston config; primary source "Synoptic the 1M HF-ASOS network 258", WebSocket receipt, D = 300 s): https://www.cftc.gov/filings/ptc/ptc10012630809.pdf
- Kalshi API rate limits: https://docs.kalshi.com/getting_started/rate_limits
- minuteTemp, Kalshi Weather Index explained (member stations per city): https://minutetemp.com/docs/kalshi-weather-index
- Synoptic push streaming: https://docs.synopticdata.com/services/push-streaming ; latency: https://docs.synopticdata.com/services/latency-of-observation-data-on-the-synoptic-platfo
- NWS ASOS PM briefing to FPAW (2023), ASOS 2.0 "IP communications", "Ubiquitous access to OMO (goal)", copper→IP by end of 2026: https://fpaw.aero/sites/default/files/163/2-boutin-decadal-look-asos-lifecycle-upgrades.pdf
- NWS Nebraska, ASOS 2.0 update (2026): https://engineering.uiowa.edu/sites/engineering.uiowa.edu/files/2026-03/HeartlandConferenceBrief.pdf
- Campbell Scientific ASOS 2.0 case study (Jan 2026): https://www.campbellsci.com/resources/case-studies/us-asos-weather-network
- NWS ASOS FAQ (207 FAA sites → AWOS-C, 2025–2029) and equipment sheet: https://www.weather.gov/asos/faq.html ; https://www.weather.gov/media/asos/ASOS%20Sites%20by%20Equipment%20As%20Of%203_18_2025%20-%20T-Td%207_1_2025.xlsx
- NCEI archive request describing the modem-bank collection of ASOS 1-/5-minute data (11-hour dial cycle, ~960 sites): https://www.ncei.noaa.gov/archive/atrac/export/2022-01-13T14-11-44.pdf?id=65639

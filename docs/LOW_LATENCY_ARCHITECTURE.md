# Mercury Edge 2 — Low-Latency Race Architecture

Status: **shadow branch only** (`feature/ultra-low-latency-race-engine`).
Production `main` is intentionally unchanged until shadow measurements prove the new path.

## Objective

Minimize the only latency chain that matters economically:

`weather source first makes proof available -> Mercury receives/decodes -> in-memory kill decision -> Kalshi order accepted`

The architecture races independent sources. There is no assumption that one vendor is fastest for every product. The first **valid** proof wins; later duplicates are useful for audit/redundancy.

## Critical-path invariants

1. No serial city loop.
2. No sleep for one station can delay another station.
3. No board discovery after a proof.
4. No Kalshi quote/orderbook REST request after a proof.
5. No private-key file read/parse after a proof.
6. No fresh TLS connection after a proof when REST fallback is used.
7. No disk journal/paper simulation before live submission.
8. SPECI is watched continuously, not only in the routine hourly METAR window.
9. DSM polling starts the release hunt; observing the new product ends the hunt. A short elapsed-time window never silently ends it.
10. Every source records first-seen time so source rankings are empirical, not assumed.

## Source ladder

### A. Routine METAR / SPECI / six-hour maximum

**Best candidate to obtain:** FAA Common Support Services Weather (CSS-Wx), direct subscription for `Surface Weather Observations - METAR/SPECI` over JMS/NEMS. The FAA portal explicitly exposes this dataset to service consumers. Exact source-to-consumer latency must be benchmarked after access; do not assume it is faster until measured.

**Best immediate public race candidate:** NWS TGFTP per-station raw METAR file with an independent persistent connection and short polling interval. This bypasses Mercury's existing AviationWeather scheduling/window architecture. IEM's current low-latency guidance explicitly warns that its NOAAPORT/LDM METAR feed still carries the FAA->NWS->satellite legacy latency and says a direct FAA Internet feed is faster.

**Optional commercial competitor:** Synoptic Push Streaming. Their standard METAR/SPECI dataset is generally available within about three minutes of sampling, and their WebSocket push layer advertises delivery within about two seconds of the observation becoming deliverable on Synoptic.

**Fallback:** AviationWeather Data API, continuously independent per station rather than only in a five-minute hourly window.

Six-hour maxima ride the same raw METAR message, so whichever METAR wire wins also wins the six-hour proof.

### B. One-minute / high-frequency ASOS (OMO)

**Best upstream candidate to obtain:** FAA CSS-Wx `Surface Weather Observations - One Minute Observations (OMO)`, delivered through the FAA's JMS/NEMS subscription system. This is the most important access request because it is closer to the FAA source than MADIS/Synoptic public products. Exact latency is unknown until an account/queue is provisioned and benchmarked.

**Commercial race candidate:** Synoptic full HF-ASOS + Push Streaming. Their documentation currently describes HF-ASOS availability latency as usually 2–5 minutes in normal operation; their push layer then adds at most roughly a couple of seconds after deliverable accessibility.

**MADIS LDM candidate:** Request the public 5-minute `sfc-hfmetar` dataset over LDM. The user's previous application selected LDM transport but had `sfc-hfmetar: n`; correct that. Do not expect public 1-minute access from this path based on the NOAA support response.

**Immediate fallback:** MADIS public HF-METAR HTTPS netCDF files. The new worker isolates this from the city loop and aggressively checks batch boundaries. It remains upstream-batch-limited and should not be mistaken for a true 1-minute wire.

### C. DSM

DSM is a separate NWS text-product race; it is not replaced by FAA OMO.

**Push candidate:** IEM LDM `IDS|DDPLUS`, which IEM documents as containing DSM collectives matching `^CDUS27`. This removes Mercury's IEM web polling delay once the product enters that feed, although it does **not** remove the underlying NWS/NOAAPORT dissemination latency.

**NWWS-OI candidate:** NWWS Open Interface is XMPP push and NWS describes NWWS text dissemination as within ten seconds of product issuance. However NWWS does not carry every NWS product and WFOs control exclusions. Do not make NWWS-OI the sole DSM path until each required DSM PIL is observed reliably on the stream.

**Immediate fallback:** IEM AFOS HTTP. The new DSM worker baselines old products, starts a release hunt, polls independently, and does not stop until a new product is observed or a long explicit safety timeout/alert is reached.

**Extreme hardware option:** direct SBN/NOAAPORT satellite ingest. This is justified only if measurements show meaningful edge after upstream issuance and internet LDM/NWWS distribution. It is not the first engineering step.

### D. Kalshi market data and order submission

**Market data now implemented:** authenticated `orderbook_delta` WebSocket on Kalshi's dedicated external API host. Full snapshots + deltas live in RAM. The kill engine therefore reads a local dictionary instead of making a quote REST request after proof.

**Order path now implemented as fallback:** V2 event-order endpoint over one persistent HTTP/2 client, with the RSA private key loaded once. A YES `ask` at the strategy's minimum acceptable YES price is economically the same kill trade as the previous sell-YES/buy-NO action.

**Final target:** Kalshi FIX order entry. Current Kalshi docs expose `mm.fix.elections.kalshi.com:8228` (`KalshiNR`) for order entry without retransmission. FIX is available by default to Premier-tier members and otherwise by request. For the race executor this should beat reconstructing/authenticating individual REST requests and gives a persistent exchange session.

**Optional final network step:** ask Kalshi about AWS PrivateLink only after FIX is provisioned and region measurements justify it.

## Deployment topology

Current production Railway is in **SFO / US West**. That is inappropriate for an east-coast NOAA/NWS/Kalshi latency race.

Do not move the existing dashboard/service first. Deploy a separate **shadow race worker in Railway US East** (or an AWS us-east VM), while production remains untouched. Run the same source probe from US East and optionally one comparison node in US West. Choose region from measured end-to-end source + Kalshi RTT rather than intuition.

Long term:

- `mercury-console`: current dashboard, API, research, persistent files; latency-insensitive.
- `mercury-race`: tiny always-on east-coast process; weather wires + Kalshi WS/FIX + kill decision only.
- async telemetry path from race -> console/storage.

## Code on this branch

- `engine/fast_sources.py`: concurrent TGFTP, AviationWeather, MADIS-HF and DSM release workers.
- `engine/fast_kalshi.py`: in-memory Kalshi WebSocket book + persistent HTTP/2 V2 executor.
- `engine/race_runtime.py`: isolated shadow-by-default critical-path runtime.
- `research/source_race_probe.py`: records source first-seen timestamps; never trades.
- `tests/test_race_engine.py`: parser and in-memory-book unit tests.
- `.github/workflows/race-engine.yml`: compile + self-test + unit-test checks.

## Access work still external to code

The code cannot invent endpoints/credentials for feeds that require agreements. The next external access requests are:

1. FAA CSS-Wx: request both `Surface Weather Observations - One Minute Observations (OMO)` and `Surface Weather Observations - METAR/SPECI`; obtain the WSDD/JMS/NEMS connection details, then implement the exact adapter.
2. NOAA MADIS: correct the LDM request to include `sfc-hfmetar: y` for the permitted public five-minute product.
3. IEM: request an LDM `IDS|DDPLUS` feed for DSM redundancy/push.
4. NWS: obtain NWWS-OI credentials and empirically verify all required DSM products are present before treating it as primary.
5. Kalshi: request FIX access; use port 8228 `KalshiNR` for the low-latency order session if approved.

## Benchmark criteria before live cutover

For each weather observation/product, record:

- observation/product issue timestamp where meaningful;
- first-seen timestamp on every competing Mercury wire;
- source HTTP/JMS/XMPP receive/parse duration;
- first Kalshi orderbook timestamp that reflects the information;
- Mercury proof-to-decision microseconds;
- order-send timestamp;
- Kalshi matching-engine `ts_ms` / FIX execution-report timestamp;
- whether a >=15c stale YES bid existed at first proof and how long it survived.

The primary score is not average provider latency. It is **how often a source reaches Mercury while executable stale liquidity still exists, and by how many milliseconds/seconds it beats the market repricing**.

## Source references

- FAA CSS-Wx Agreement Portal: https://aa.data.faa.gov/data/service.jsf?uuid=02422d2b-690f-42ba-9ce3-7a72f830f01c
- IEM LDM low-latency guidance: https://mesonet.agron.iastate.edu/request/ldm.php
- NWS NWWS FAQ: https://www.weather.gov/nwws/faq
- Synoptic HF-ASOS: https://docs.synopticdata.com/services/high-frequency-asos
- Synoptic latency / Push Streaming: https://docs.synopticdata.com/services/latency-of-observation-data-on-the-synoptic-platfo
- Kalshi WebSocket orderbook: https://docs.kalshi.com/websockets/orderbook-updates
- Kalshi V2 orders: https://docs.kalshi.com/api-reference/orders/create-order-v2
- Kalshi FIX connectivity: https://docs.kalshi.com/fix/connectivity

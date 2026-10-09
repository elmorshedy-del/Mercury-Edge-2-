# Commercial and Paid Vendors of Real-Time US ASOS One-Minute Observations (OMO / HF-ASOS)

Research date: 2026-10-09. Scope: products that deliver ASOS one-minute data, as distinct from hourly METAR or 5-minute HF-METAR. Target stations: KNYC, KLAX, KMIA, KPHL, KMDW, KDEN, KAUS.

## Q1. Which vendors sell real-time 1-minute ASOS/AWOS data?

### Takeaway
I found only a few commercial products that carry real-time ASOS one-minute data, and they all trace back to the same public FAA→MADIS stream:
- **Synoptic Data**: the `1M` network (e.g. `KLAX1M`), sold through its Weather API and its Push Streaming tier.
- **Products built on Synoptic or MADIS**: Kalshi's free `live_data/weather` index, minuteTemp, and Wethr.net. Wethr.net uses OMO for highs and lows but does not yet sell raw OMO through its API.

Large enterprise weather vendors publish no ASOS 1-minute product that I could find. This covers DTN, Vaisala/Xweather, Baron, Tomorrow.io, AccuWeather, Earth Networks, IBM/The Weather Company, AVWX, CheckWX and FlightAware. The only other sellers of one-minute data are the FAA-approved AWOS (not ASOS) data providers, which serve non-federal AWOS airports, not the target ASOS stations.

### Cited Findings

**Synoptic Data: the primary commercial source**
- Synoptic has received "the full 1-minute data, as a low-latency provisional and real-time data stream from MADIS" since 2019. It puts these readings in a separate network whose station IDs carry a `1M` suffix (KSLC → `KSLC1M`), available "only for stations which have reported the HF-ASOS data." — [Synoptic HF-ASOS docs](https://docs.synopticdata.com/services/high-frequency-asos)
- Since 2017 Synoptic has also blended a 5-minute subset of HF-ASOS (also via MADIS) into its ASOS/AWOS network. The `hfmetars` argument filters that subset out. — [Synoptic HF-ASOS docs](https://docs.synopticdata.com/services/high-frequency-asos)
- "HF-ASOS data was unavailable from its source between October 2023 and January 2026. We have established a new connection with NWS and FAA which should provide reliable access to this dataset. We will continue to categorize the dataset as experimental." Synoptic also says: "We do not recommend developing applications solely based on the consumption of HF-ASOS data." — [Synoptic HF-ASOS docs](https://docs.synopticdata.com/services/high-frequency-asos)
- Precision: "Temperatures are expressed in whole degrees celsius." "Wind speeds are a 2 minute average, even when looking at 1-minute observations." The observations "do not adhere to the METAR standard, and must not be used for aviation." — [Synoptic HF-ASOS docs](https://docs.synopticdata.com/services/high-frequency-asos)
- Push Streaming is a WebSocket service, "available for customers with our higher tier commercial accounts." It draws on more than 260 networks and over 120,000 active stations. — [Synoptic Push Streaming docs](https://docs.synopticdata.com/services/push-streaming)

**Kalshi: free redistribution of Synoptic-sourced readings**
- Kalshi's `GET /trade-api/v2/live_data/weather/{city}` serves "the Kalshi-computed city temperature index — the canonical minute-resolution series behind hourly temperature markets." With `detailed=true`, each point carries "every member station's reported reading and quality-control disposition," and trailing minutes still inside the receipt deadline appear as `incomplete` points with raw readings. — [Kalshi API changelog](https://docs.kalshi.com/changelog)
- Per-station fields include `source`, `temp_f`, `obs_time_ms` and `received_at_ms`. — [Kalshi Get Weather Index docs](https://docs.kalshi.com/api-reference/live-data/get-weather-index)
- The changelog states the upstream directly. Backfilled points are marked `receipt_basis: synoptic_latency` because "those minutes judged the receipt deadline against `observation_time + Synoptic ingest latency` instead of Kalshi's local receipt clock." — [Kalshi API changelog](https://docs.kalshi.com/changelog)

**minuteTemp (prediction-market tool)**
- Advertises "ASOS 1-MIN" and "18 settlement stations on 1-minute data," with 77 settlement stations tracked. Its marketing alternately claims 61 and 72 cities. — [minuteTemp home](https://minutetemp.com/)
- Claim: "Each minute's provisional index lands about 2–3 seconds after Kalshi receives the station batch, well before the minute turns official 5 minutes later." — [minuteTemp home](https://minutetemp.com/)
- Its docs say it "displays real NWS station observations polled every 60 seconds." — [minuteTemp NWS data doc](https://minutetemp.com/docs/nws-data); [minuteTemp reading-dashboard doc](https://minutetemp.com/docs/reading-dashboard)
- Source disclosed only as "official METAR observations and ASOS stations." — [minuteTemp home](https://minutetemp.com/)

**Wethr.net (prediction-market tool)**
- Ingests OMO for 93 stations: "the one-minute observation feed for the 93 stations that carry it." — [Wethr API docs](https://www.wethr.net/edu/api-docs)
- "Raw One Minute Observation data is not yet available via the API (REST or Push). We anticipate making OMO data available in the coming months." OMO is used only inside the Wethr High/Low values, under the source label `omo`. — [Wethr API docs](https://www.wethr.net/edu/api-docs)
- The paid-features page repeats: "OMO not included; derivative data updates in real time." — [Wethr paid features](https://wethr.net/paid-features)
- Raw OMO is visible only in the web UI and charts. A Sep 24, 2026 update added views of missing and out-of-range OMO for pro+ users and a "1-minute-gaps" chart option. — [Wethr update log](https://wethr.net/updates)

**Other prediction-market tools (no 1-minute ASOS)**
- **METAR.ws**: WebSocket METAR/SPECI stream "shortly after publication." It is an early beta with no latency guarantee, and other observation networks are "not yet available." — [METAR.ws](https://metar.ws/)
- **Polymeteo**: METAR from aviationweather.gov at ~hourly or 30-min granularity. — [Polymeteo](https://www.polymeteo.com/)
- **PolyWeather**: "updated every 1–5 minutes" from METAR plus ASOS. — [PolyWeather](https://polyweather.ai/)
- **Temprr**: METAR/TAF plus native national networks; recomputes every 60s. — [Temprr](https://temprr.trade/)
- **wxsignals**: station data marked "SOON." — [wxsignals](https://wxsignals.com/)
- **Apify actors**: hourly METAR from aviationweather.gov and IEM. — [Apify bigdavidson actor](https://apify.com/bigdavidson/metar-nws-weather-station-observations/api); [Apify evolve-data actor](https://apify.com/evolve-data/weather-station-data/api)
- **Apify `gratified_ashram/kalshi-weather-index`**: resells Kalshi's minute index per row. — [Apify Kalshi Weather Index actor](https://apify.com/gratified_ashram/kalshi-weather-index)
- **WeatherEdge (prilo-weatheredge.com)**: a calibrated-model product, not a feed. Its blog backtested a year of OMO for seven cities and concluded "faster and finer didn't win — fusing feeds into a calibrated probability did." It reports "multi-week gaps" in the OMO archive and a bogus 53°F spike in one city. — [WeatherEdge OMO backtest](https://www.prilo-weatheredge.com/blog/faster-weather-data-omo-not-the-edge)

**Enterprise weather vendors (no ASOS 1-minute product found)**
- **DTN**: Observation API covers "over 70,000 weather stations worldwide for near real-time and historical data." No 1-minute ASOS product is mentioned. — [DTN Weather API](https://www.dtn.com/resources/api-data-integrations/weather-api/)
- **AccuWeather for Business**: advertises WebSocket streaming and webhooks for "current & real-time weather data." No ASOS 1-minute product is mentioned. — [AccuWeather for Business](https://business.accuweather.com/products/weather-data-integrations/)
- **Earth Networks**: its own network of ">10,000 stations that are exclusive to Earth Networks and update with live data every two seconds." These are proprietary sensors, not ASOS. — [Earth Networks ENcast PDF](https://earthnetworks.com/Portals/0/pdf/ENcast_Overview_final.pdf)
- **Baron, Tomorrow.io, Vaisala Xweather**: listed in the NWS enterprise vendor directory with generic descriptions. Nothing indicates 1-minute ASOS. — [NWS enterprise software list](https://www.weather.gov/enterprise/weather-data-software-5a)

**FAA-approved AWOS data providers (AWOS only, not ASOS)**
- The FAA list (v.12.16.25) of third-party providers for WMSCR:
  - All Weather Inc. (AWI)
  - DBT Transportation Services ("DBT acquired Vaisala's U.S. AWOS business in 2016")
  - Mackinac Software dba anyAWOS
  - Remote Systems Integration (RSI Net)
  - University Research Foundation (URF)
  - Source: [FAA WMSCR provider list PDF](https://www.faa.gov/airports/planning_capacity/non_federal/resources/wmscr_list.pdf)
- Under AC 150/5220-16E, AWOS III/IV owners must supply data to an FAA-approved third-party provider (or their state aviation service), which relays the one-minute observation to WMSCR. — [FAA AC 150/5220-16E](https://www.faa.gov/documentLibrary/media/Advisory_Circular/AC_150_5220-16E.pdf) (as summarized in search results)
- anyAWOS claims it "is the only provider updating weather once every minute and displaying it on a custom web screen in real time" for its AWOS customers. It says "the national network will only take weather three times per hour." — [anyAWOS Why](https://www.anyawos.com/WhyanyAWOS.html); [anyAWOS Advantages](https://www.anyawos.com/Advantages.html)

**Free and archival contrast (not commercial)**
- IEM serves NCEI's monthly one-minute ASOS archive, "available up until: 17 Sep 2026," so it is not real time. — [IEM 1-min download](https://mesonet.agron.iastate.edu/request/asos/1min.phtml)
- MetService (New Zealand) sells a 1-minute observations API. It is not US ASOS. — [MetService 1min obs API](https://developer.metservice.com/docs/api-catalog/1min-obs-api/)

### Inferences
- Every US commercial or quasi-commercial real-time OMO product I found ultimately draws on one upstream path: FAA WMSCR → NOAA MADIS → Synoptic. The intermediaries are Synoptic itself, Kalshi (via Synoptic), minuteTemp (very likely via Kalshi or Synoptic; see Q3), and Wethr.net (source undisclosed, but its latency matches MADIS/Synoptic).
- Buying from a "big-name" vendor would therefore be unlikely to give faster or better 1-minute ASOS data than going to Synoptic directly.
- No major aviation-data vendor publicly markets ASOS OMO as a product. That includes Jeppesen/Boeing, Collins/ARINC, SITA, L3Harris, Leidos and Universal Weather; none appeared in any search.
- The non-federal AWOS providers (anyAWOS, RSI, AWI, DBT, URF) carry true one-minute AWOS data, possibly with lower latency to their own web pages. However, none of the target stations (KNYC, KLAX, KMIA, KPHL, KMDW, KDEN, KAUS) are non-federal AWOS, so these providers are not a path to target-station OMO.

### Gaps
- I could not confirm whether DTN, Vaisala/Xweather, Baron, Spire, Tomorrow.io, Meteomatics, IBM/TWC, CheckWX, AVWX or FlightAware ingest MADIS OMO internally. None documents it publicly; a definitive "no" would need sales contact.
- I found no public evidence on Jeppesen, Collins/ARINC, SITA, Leidos (FAA flight-service/WMSCR-adjacent contracts) or L3Harris (CSS-Wx, FTI). It remains unknown whether any of them redistributes OMO commercially.
- "Harris WINS" could not be identified. Searches returned only Harris's WARP, CSS-Wx, OASIS and FTI programs. — [GPS World on CSS-Wx contract](https://www.gpsworld.com/faa-awards-harris-238m-contract-for-weather-support/); [Microwave Journal on WARP](https://www.microwavejournal.com/articles/4611-harris-corp-s-weather-and-radar-processor-system-in-use-by-controllers)
- Synoptic does not publish an exact count of active `1M` stations. Wethr's count (93) is the best available proxy.

## Q2. What is the latency of each source, and does any vendor have a direct FAA/NWS feed faster than MADIS?

### Takeaway
Measured and documented latency for 1-minute ASOS clusters at about 2m15s–2m40s after the observation minute (Wethr median 2m25s, p90 about 3m). Synoptic documents 2–5 minutes.

I found no vendor that documents or claims a commercial OMO feed meaningfully faster than the MADIS/Synoptic path. The physical floor is set by the ASOS itself, which makes each OMO available locally at M+23s, but OMO "is generally not transmitted long-line beyond the local FAA or NWS communications network node." So the roughly 2 minutes of extra delay comes from the FAA/NWS relay chain, not from vendors.

### Cited Findings

**ASOS hardware: the theoretical floor**
- "OMO information is collected during the 60-second period ending at M+00 and made available to users each minute at M+23 (23 seconds past the current minute)." — [NWS ASOS User's Guide](https://www.weather.gov/media/asos/aum-toc.pdf)
- "The basic difference between the OMO and the METAR/SPECI is that the OMO is generally not transmitted long-line beyond the local FAA or NWS communications network node." — [NWS ASOS User's Guide](https://www.weather.gov/media/asos/aum-toc.pdf)

**MADIS: the upstream for Synoptic**
- "The MADIS team worked with the FAA to establish an operational feed of this data from the FAA Weather Messaging Switching Center Replacement (WMSCR) systems to MADIS." — [MADIS 1-minute ASOS page](https://madis.ncep.noaa.gov/madis_OMO.shtml)
- "Data arrive on a continuous, asynchronous schedule." — [MADIS 1-minute ASOS page](https://madis.ncep.noaa.gov/madis_OMO.shtml)
- MADIS reprocesses the current and previous hour every 5 minutes. — [MADIS 1-minute ASOS page](https://madis.ncep.noaa.gov/madis_OMO.shtml)
- MADIS offers OMO through "all communications methods supported by MADIS except for ldm," with "No restrictions. All observations are publicly accessible." — [MADIS 1-minute ASOS page](https://madis.ncep.noaa.gov/madis_OMO.shtml)

**Synoptic**
- HF-ASOS "when operating normally, usually arrives with between 2 and 5 minutes latency." — [Synoptic HF-ASOS docs](https://docs.synopticdata.com/services/high-frequency-asos)
- Synoptic's own processing adds "under 10 seconds of total latency." — [Synoptic latency doc](https://docs.synopticdata.com/services/latency-of-observation-data-on-the-synoptic-platfo)
- Push Streaming delivers "within 2 seconds of their deliverable accessibility." — [Synoptic latency doc](https://docs.synopticdata.com/services/latency-of-observation-data-on-the-synoptic-platfo)
- The latency service and Data Availability Dashboard expose per-observation latency. — [Synoptic latency doc](https://docs.synopticdata.com/services/latency-of-observation-data-on-the-synoptic-platfo)
- The 5-minute HFMETAR component has latency of "5-9 minutes or more." — [Synoptic docs via search summary](https://docs.synopticdata.com/services/asos-awos-united-states-metar) (search-snippet only; not re-verified on page)

**Wethr.net measured receipt latency (observation stamp → Wethr receipt; trailing window)**

Network-wide:

| Feed | Median | p90 | p99 | Reports · Stations |
|---|---|---|---|---|
| 1-minute (US) | 2m 25s | 2m 59s | 4m 28s | 896,928 · 93 |
| 5-minute (US) | 2m 15s | 2m 24s | 7m 18s | — |
| Hourly METAR (US) | 2m 12s | 2m 59s | 12m 41s | — |
| SPECI (US) | 2m 15s | 3m 04s | — | — |

Source: [Wethr latency page](https://wethr.net/latency)

1-minute latency by target station (median / p90):

| Station | Median | p90 |
|---|---|---|
| KLAX | 2m25s | 3m10s |
| KMIA | 2m25s | 2m51s |
| KPHL | 2m25s | 2m49s |
| KMDW | 2m25s | 2m39s |
| KDEN | 2m24s | 2m39s |
| KAUS | 2m24s | 2m45s |
| KNYC | no 1-minute feed | — |

Source: [Wethr latency page](https://wethr.net/latency)

- Wethr notes that the 5-minute and 1-minute feeds' latency "is dominated by the upstream publishing cadence rather than by transmission jitter." — [Wethr latency page](https://wethr.net/latency)

**Kalshi**
- Kalshi's receipt clock uses Synoptic as its ingest path. Backfill minutes use "Synoptic ingest latency." — [Kalshi API changelog](https://docs.kalshi.com/changelog)

**Is there a direct FAA/NWS feed?**
- FAA SWIM (SCDS) is a "publicly accessible cloud-based infrastructure dedicated to providing real-time SWIM data to the public via Solace JMS messaging," with subscriptions provisioned through the SWIFT portal after signed access agreements. — [FAA SCDS 2019 briefing](https://www.faa.gov/air_traffic/flight_info/aeronav/atiec/media/Presentations/2019/Day%201%20PM%20009%20Melissa%20Matthews%20SCDS.pdf); [FAA SWIFT onboarding](https://www.faa.gov/air_traffic/technology/swim/overview/swift-portal-on-boarding-instructions)
- An FAA SWIM slide lists METAR among WMSCR weather publications. I found no SWIM document listing ASOS OMO / 1-minute ASOS as a SWIM product. — [SWIM PMO slides](https://testcdm.fly.faa.gov/wp-content/uploads/9-SWIM-PMO.pdf) (as summarized in search results)
- In a 2026 Unidata ldm-users thread, a respondent said Synoptic has a special agreement with the FAA and suggested asking the FAA whether other private companies can receive the data. This is a forum opinion, not an official statement. The same thread notes TGFTP does not appear to carry the 5-minute HFMETAR data. — [ldm-users 2026 msg00034](https://mailinglists.unidata.ucar.edu/archives/ldm-users/2026/msg00034.html)

**Wethr.net "accelerated feed" (hourly/special METAR only, not OMO)**
- The feed "regularly delivers hourly and special METARs seconds after they are taken," typically minutes ahead of the standard chain, where "typical chain latency is a few minutes." — [Wethr API docs](https://www.wethr.net/edu/api-docs)
- The docs name no provider. — [Wethr API docs](https://www.wethr.net/edu/api-docs)

### Inferences
- Of the roughly 2m25s median OMO latency, only about 23s is inherent to ASOS (M+23s availability). The other ~2 minutes accrue in the FAA (ADAS/WMSCR) → MADIS → Synoptic chain. Synoptic's own share is under 10 seconds plus up to 2 seconds for push.
- A commercial vendor faster than about 2 minutes would therefore need a tap earlier than MADIS, at WMSCR, the FAA NAS network, or the station itself. No vendor publicly claims this for OMO.
- Synoptic's January 2026 "new connection with NWS and FAA" may have changed its path, but the measured latencies (Wethr 2m25s; Kalshi/Synoptic about 2m15s–2m40s per the background brief) show no sub-2-minute result.
- The fact that Wethr's 1-minute median (2m25s) is about 10s slower than its 5-minute median (2m15s) is consistent with both coming from the same MADIS-type batch path.
- KNYC (Central Park) shows no 1-minute feed in Wethr's table. Kalshi NYC traders likely cannot get OMO for the settlement station from any of these vendors.

### Gaps
- No vendor publishes a measured OMO latency below 2 minutes, and I found no third-party measurement of Synoptic Push Streaming specifically for `1M` stations.
- The provider behind Wethr's "accelerated feed" METARs is undisclosed. The `metar8` label is not explained beyond "Accelerated-feed METAR not yet confirmed by any standard distribution source." Whether it is a SWIM/WMSCR subscription, an FAA dial-in or ATIS scrape, or another path is unknown.
- I could not confirm from FAA primary documents whether SWIM SCDS carries OMO, or whether WMSCR OMO is available to private subscribers other than MADIS and Synoptic.

## Q3. Which vendors do prediction-market weather traders use, and what speed claims do they make (Wethr "accelerated feed / metar8", minuteTemp source)?

### Takeaway
Traders mainly use Wethr.net, minuteTemp, the free Kalshi `live_data/weather` index, and smaller tools (WeatherEdge, METAR.ws, PolyWeather, Temprr, Polymeteo, Apify actors).

- **Wethr.net**: its "seconds after observation" claim applies only to its accelerated hourly/special METAR feed (label `metar8`). Its own measured OMO latency is a 2m25s median.
- **minuteTemp**: its "2–3 seconds" claim is relative to when Kalshi receives the station batch, not to the observation time. Its 1-minute data therefore appears to be Kalshi's Synoptic-sourced index, so it inherits the roughly 2-minute Synoptic latency.

### Cited Findings

**Wethr.net**
- Source labels: `metar`, `hf_metar` ("High-frequency (~5 minute) METAR"), `omo`, `six_hour_high/low`, `dsm`, `cli`, and `metar8` ("Accelerated-feed METAR not yet confirmed by any standard distribution source," NWS logic only). — [Wethr API docs](https://wethr.net/api_docs.php)
- Preliminary observations received only via the accelerated feed are excluded from WU-logic values. — [Wethr API docs](https://www.wethr.net/edu/api-docs)
- API rows carry ingestion timestamps (`metar_received_at`, `hfmetar_received_at`, `dsm_received_at`, `cli_received_at`). The docs present these as "suitable for latency analysis." — [Wethr API docs](https://www.wethr.net/edu/api-docs)

**Wethr.net update log**

| Date | Entry |
|---|---|
| Jul 28, 2026 | "one of our new data sources has reliably provided hourly/special metar data" |
| Jul 23, 2026 | added cloud data for one-minute observations |
| Sep 18, 2026 | 1-minute coverage API |
| Sep 29, 2026 | OMO Feed Status page |
| Sep 30, 2026 | Data Latency page |

Source: [Wethr update log](https://wethr.net/updates)

**Wethr.net OMO status and education pages**
- The OMO status page shows real gaps, e.g. KLGA 15:04Z–15:18Z, Dallas-Fort Worth 11 min, and Kansas City stations over 1h. Missing minutes are counted "after a 2-minute delivery allowance." — [Wethr OMO status](https://wethr.net/omo-status)
- The "OMO Bot" education page says: "Some ASOS stations allow access to near-real-time data via a dial-in phone system, traditionally used by pilots. Bots can automate calls to this system." — [Wethr market bots guide](https://wethr.net/edu/market-bots)

**minuteTemp**
- Plans: "Every minute at 18 settlement stations; every station labeled 1 min, 5 min or hourly." The API is REST + WebSocket (`/ws/api/1m`) with "60s push updates" and "<50ms avg latency" (API response latency, not data latency). — [minuteTemp home](https://minutetemp.com/)
- Speed claims: "Seconds, not minutes — Each minute's provisional index lands about 2–3 seconds after Kalshi receives the station batch." Also: "The only platform that refreshes every minute. Competitors lag by 20 min+." — [minuteTemp home](https://minutetemp.com/)
- It "records settlement outcomes from Kalshi's API." — [minuteTemp settlement doc](https://minutetemp.com/docs/market-settlement)
- It says "No known near-real-time public source combines correct 2-minute averaging with proper Fahrenheit conversion." — [minuteTemp temperature-data doc](https://minutetemp.com/docs/temperature-data)

**Kalshi Weather Index and settlement source (conflicting)**
- minuteTemp says hourly markets settle on the Kalshi Weather Index. — [minuteTemp home](https://minutetemp.com/)
- Kalshi's help center says hourly markets settle on The Weather Company's reported value ("official and final"). — [Kalshi Help: Weather Markets](https://help.kalshi.com/en/articles/13823837-weather-markets)
- **Unresolved conflict**: the same Kalshi help page says daily markets settle on the final NWS Daily Climate Report, while press reports say daily highs and lows have settled on The Weather Company since Aug 14, 2026. — [Kalshi Help: Weather Markets](https://help.kalshi.com/en/articles/13823837-weather-markets); [Gizmodo](https://gizmodo.com/kalshi-teams-up-with-the-weather-co-on-markets-that-are-nearly-impossible-to-insider-trade-2000803871); [Bloomberg](https://www.bloomberg.com/news/articles/2026-08-27/kalshi-weather-odds-are-coming-to-a-weather-app-near-you)

**The Weather Company's role**
- Kalshi/TWC partnership announced around Aug 27, 2026. TWC screens observations against nearby stations and model analysis before settlement and will show Kalshi odds in its apps. — [Bloomberg](https://www.bloomberg.com/news/articles/2026-08-27/kalshi-weather-odds-are-coming-to-a-weather-app-near-you); [Gizmodo](https://gizmodo.com/kalshi-teams-up-with-the-weather-co-on-markets-that-are-nearly-impossible-to-insider-trade-2000803871)
- WeatherEdge asserts TWC's underlying source is still the NWS Climate Report. — [WeatherEdge blog](https://www.prilo-weatheredge.com/blog)
- I found no TWC product selling 1-minute ASOS data.

**Community evidence**
- A Reddit r/Kalshi dashboard author (2+ years ago) claimed data "5-10 minutes ahead of the NWS time series." A commenter asked whether the source differed from NWS "to be able to get 1 min interval readings." — [Reddit r/Kalshi dashboard thread](https://www.reddit.com/r/Kalshi/comments/1hqgcq0/kalshi_weather_market_dashboard) (snippet only)

### Inferences
- **minuteTemp's 1-minute source is very likely Kalshi's public `live_data/weather` feed, so ultimately Synoptic.** Evidence:
  - Its latency claim is anchored to "after Kalshi receives the station batch."
  - It covers 18 stations with 1-minute data. This is consistent with Kalshi index member stations and far fewer than the 93 OMO stations Wethr carries.
  - It "polls every 60 seconds."
  - Its end-to-end latency from the observation minute is therefore about the Kalshi/Synoptic figure (≈2m15s–2m40s) plus 2–3 s. This is an inference: minuteTemp does not name its source.
- Wethr's "seconds after taken" speed applies to METAR/SPECI, not OMO. For OMO, Wethr is no faster than Synoptic and does not resell raw OMO through its API.
- The "OMO Bot" that traders describe is an automated dial-in to ASOS phone lines. It is a per-station, voice-based path, not a vendor product (out of scope here; covered by the phone/VHF research).

### Gaps
- Neither Wethr nor minuteTemp names its OMO upstream. Wethr's 93-station count and latency profile match MADIS, but no statement confirms this.
- I found no vendor marketing a sub-2-minute continuous OMO feed to traders. Absence of evidence is not conclusive; private Discord or enterprise offerings would not show up in search.
- Reddit threads could not be fetched in full; only search snippets were used.

## Q4. What are the pricing tiers and purchase process, and are there restrictions on automated trading use?

### Takeaway
- **Prediction-market tools**: self-serve monthly subscriptions. Wethr.net runs $0–$99/mo plus Enterprise. minuteTemp runs $0–$89.99/mo, with API and WebSocket access from $29.99.
- **Synoptic**: the only true 1-minute data wholesaler. It offers a 14-day trial and three undisclosed commercial tiers. Push Streaming (lowest latency) is limited to "higher tier commercial accounts" and is quote-based (48-hour quote turnaround).
- **MADIS OMO**: public with no restrictions.
- **Automated trading**: I found no explicit prohibition in any document reviewed. minuteTemp and Wethr explicitly market to trading bots.

### Cited Findings

**Wethr.net**

| Tier | Price | API limits | Push API |
|---|---|---|---|
| Free | $0 | — | — |
| Basic | $14.99/mo | — | — |
| Professional | $24.99/mo | 60 req/min, 5,000/day | 5 stations |
| Developer | $99/mo | 300/min, 100,000/day | all stations; also Model Accuracy API and Coverage API |
| Enterprise | not priced | 1,200/min, 500,000/day | — |

- Free accounts see data on a 3-minute delay; paid accounts are "real-time."
- 7-day refund guarantee.
- Sources: [Wethr subscribe](https://wethr.net/subscribe); [Wethr get-wethr](https://wethr.net/get-wethr); [Wethr API docs](https://www.wethr.net/edu/api-docs)
- The Coverage API (DEV+) shows which OMO minutes are missing or rejected, but raw OMO values are not sold via the API. — [Wethr API docs](https://www.wethr.net/edu/api-docs)

**minuteTemp**

| Tier | Price | Data / API |
|---|---|---|
| Free | $0 | 3-min delay, 3 models |
| UI | $14.99/mo ($1.99 7-day trial) | realtime UI, 20 models |
| Starter | $29.99/mo | 15 req/min sustained (~21,600/day), 6 WS subscriptions, realtime WebSocket |
| Pro | $89.99/mo | 100 req/min (~144,000/day), 60 WS subscriptions |

- Annual billing saves 20%; promo code FOUNDER50.
- Sources: [minuteTemp home](https://minutetemp.com/); [minuteTemp dashboard](https://minutetemp.com/dashboard)

**Synoptic**
- "three standard tiers or we can create a custom commercial pricing plan." Value-added services include Quality Control, Push Streaming, Precipitation Service and Esri layer, plus a 14-day free trial. — [Synoptic commercial pricing](https://synopticdata.com/commercial-pricing); [Synoptic pricing](https://synopticdata.com/pricing/)
- A sales rep returns an initial quote within 48 hours. — [Synoptic request a quote](https://synopticdata.com/request-a-quote/) (via search summary)
- Open Access is free for non-commercial use only. — [Synoptic pricing](https://synopticdata.com/pricing/)
- Gold and Silver tiers are sold through GSA Advantage at monthly pricing. Enterprise server response times are "generally much faster than the community server." — [Synoptic GSA schedule](https://synopticdata.com/gsa-schedule/) (via search summary)
- Push Streaming: "available for customers with our higher tier commercial accounts." — [Synoptic Push Streaming docs](https://docs.synopticdata.com/services/push-streaming)

**Kalshi `live_data/weather`**
- Free API endpoint; Synoptic-sourced per the changelog. — [Kalshi API changelog](https://docs.kalshi.com/changelog)

**MADIS OMO**
- "No restrictions. All observations are publicly accessible." Delivered via MADIS methods other than LDM. — [MADIS 1-minute ASOS page](https://madis.ncep.noaa.gov/madis_OMO.shtml)

**Smaller tools**
- Polymeteo: Free (10 req/day) and Trader tiers. — [Polymeteo](https://www.polymeteo.com/)
- Apify actors: per-record pricing (e.g. $0.001–$0.002 per row). — [Apify yawning_manuscript actor](https://apify.com/yawning_manuscript/weather-data-prediction-markets/api)
- WeatherEdge: 7-day free trial, one paid plan. — [WeatherEdge blog](https://www.prilo-weatheredge.com/blog)

**Non-federal AWOS providers**
- Sold to airport owners, not data consumers. Contact via FAA list: anyAWOS (877) 213-9947; RSI (800) 261-1774. — [FAA WMSCR provider list PDF](https://www.faa.gov/airports/planning_capacity/non_federal/resources/wmscr_list.pdf)

**Restrictions on use**
- Wethr's site disclaimer: data "not guaranteed to be accurate, complete, or up-to-date," and use is "at your own risk." — [Wethr paid features](https://wethr.net/paid-features)
- The Wethr API docs list a "Terms, Risk & Disclaimer" section, but its body was not retrievable. — [Wethr API docs](https://www.wethr.net/edu/api-docs)
- Synoptic HF-ASOS must "not be used for aviation" and is not recommended as a sole basis for applications. — [Synoptic HF-ASOS docs](https://docs.synopticdata.com/services/high-frequency-asos)

### Inferences
- For the lowest-latency legitimate OMO, the realistic commercial purchase is a Synoptic commercial contract at a tier that includes Push Streaming, subscribing to `K???1M` stations.
- The expected result is about the same 2m15s–2m40s receipt latency Kalshi sees, because Kalshi itself uses Synoptic, though possibly a few seconds better than polling.
- Wethr and minuteTemp are cheaper, but they add a hop and, for Wethr, do not expose raw OMO via API.
- Because all paths share the MADIS/Synoptic upstream, paying more for a different vendor is unlikely to buy speed for OMO. Speed gains below about 2 minutes would require non-vendor paths (ASOS dial-in or VHF) or an FAA-side arrangement.

### Gaps
- Synoptic's actual tier prices, and the price of Push Streaming, are not published. A quote is needed.
- Synoptic's terms of service regarding use of `1M` data for trading, and any redistribution limits on HF-ASOS, were not found.
- Wethr's Enterprise price and Terms text were not retrievable.
- minuteTemp's terms of service (automated trading, redistribution) were not reviewed.
- No vendor states an explicit prohibition or permission for automated trading use of OMO.

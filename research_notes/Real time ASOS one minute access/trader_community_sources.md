# Trader-community sources and methods for real-time ASOS one-minute data (Kalshi, Polymarket, Robinhood, IBKR)

Scope note: research run 2026-10-09. Reddit pages could not be fetched directly (blocked); Reddit content below comes from search-engine snippets only. Searches on X/Twitter returned only profile pages, with no substantive posts. GitHub code search was blocked in this session (`gh search code` returned HTTP 403, "sessions are bound to their configured repositories"), so GitHub coverage comes from web search of repository READMEs.

## Q1. What do traders say publicly about getting live ASOS/OMO data (phone lines, radio, paid feeds, "minute temp" tools)?

### Takeaway
The trader community openly names the ASOS dial-in voice line as the fastest public read of the settlement sensor. wethr.net's education page describes "OMO bots" that automate calls to it, warns that "often, only one call can access the ASOS line at a time", and calls OMO bots active in some cities. An open-source Polymarket dashboard (July 2026) ships an opt-in Twilio/Telnyx "calling agent" that transcribes the ASOS voice. I found no public first-person post about SDR or VHF reception, private sensors, or sub-minute machine feeds.

### Cited Findings
- wethr.net "Navigating Market Bots & Strategies" lists an **"OMO Bot"**: "Some ASOS stations allow access to near-real-time data via a dial-in phone system, traditionally used by pilots. Bots can automate calls to this system."
  - The stated advantage is reading "the minutes *between*" the public 5-minute readings.
  - The data is spoken in °C, so there is still rounding ambiguity.
  - "Access Limitation: Often, only one call can access the ASOS line at a time."
  - The page warns traders not to leave limit orders exposed near the day's high "especially in cities where OMO bots are known to be active (see City Resources Summary)", because "if the bot hears a new maximum temperature (even just a new rounded °C value) before it's public, it might quickly fill orders." — [wethr.net market bots](https://wethr.net/edu/market-bots)
- The same wethr.net page also catalogues other bot types:
  - "DSM Bot": reacts to NWS Daily Summary Messages, with per-city release times. Examples: KNYC 20:21, 21:21, 05:17Z; KDEN 12:17, 22:17, 23:17, 07:17Z; KLAX 22:08, 01:08, 08:08Z.
  - "6 Hour Bot": 6-hour max in the :51–:54Z METARs at 00/06/12/18Z.
  - "CLI Bot", the "240" market-maker bot, the "UI" bot, the "1-Up" bot.
  - A warning about paid "Entrepreneur's Bot" tools that "repackage public data". — [wethr.net market bots](https://wethr.net/edu/market-bots)
- wethr.net's NWS data guide says the one-minute values "are not publicly displayed on the standard NWS Timeseries page. Accessing these often requires specific methods (like the OMO Bot described on the Market Bots page)." — [wethr.net NWS data guide](https://wethr.net/edu/nws-data-guide)
- GitHub repo **testedmedia/polymarket-weather-command-center** (created 2026-07-11, Apache-2.0) has an optional "CALL AGENT · ADD-ON". Its README says:
  - "US airports publish their ASOS readings on a public automated phone line. Between METAR cycles (30 to 60 minutes), that public phone line is the fastest publicly available read of the exact sensor the market resolves on."
  - How it works: (1) you provision a VoIP number (Twilio, Telnyx or similar); (2) the agent dials the station's ASOS line and transcribes the spoken temperature; (3) the reading is posted with a `phone` source tag.
  - Guardrails: disabled by default; "Scoped firing… inside snipe windows (the 20 to 35 minutes before a METAR publishes near a bucket edge)"; a cost of "$5 to $20/month".
  - "Shared resource discipline. These lines exist for pilots… keep volume to a handful of short calls per day per city. US stations only; international ASOS phone equivalents do not exist."
  - The same README lists "Synoptic HF-ASOS 1-minute feed — Optional — Free open-access tier" and a self-hosted "30-second METAR poller". — [GitHub testedmedia](https://github.com/testedmedia/polymarket-weather-command-center)
- Reddit r/Kalshi thread "Weather is rigged, right?" (post id 1i6yho9, about January 2025; snippet only) includes the claim: "The 1-minute ASOS dataset is only available to those who NWS approves: https://madis.ncep.noaa.gov/madis_OMO.shtml … non-public data sources is…". — [Reddit snippet](https://www.reddit.com/r/Kalshi/comments/1i6yho9/weather_is_rigged_right)
  - This is contradicted by the current MADIS OMO page: "Restrictions: No restrictions. All observations are publicly accessible." — [MADIS 1-minute ASOS](https://madis.ncep.noaa.gov/madis_OMO.shtml)
- r/Kalshi "An Incomplete and Unofficial Guide to Temperature Markets" by u/adulting_dude (about December 2024; snippet only) explains ASOS 5-minute rounding. One reply says the rounding "is a limitation of the software on the ASOS station, not each individual sensor". — [Reddit snippet](https://www.reddit.com/r/Kalshi/comments/1hfvnmj/an_incomplete_and_unofficial_guide_to_temperature)
- r/Kalshi "Monthly Support Megathread – July 2026" (snippet only) contains a user dispute about a daily high ("should capture a daily high of ~82-83°F, not 84°F … the ASOS real-time obs?"). This shows traders comparing live ASOS readings against settlement. — [Reddit snippet](https://www.reddit.com/r/Kalshi/comments/1uszy2n/monthly_support_megathread_july_2026)
- PredictCast (wxmap.io) public-tape posts document sub-second sweeps that came before public publication:
  - **KNYC, 2026-07-13**: "A single aggressive multi-leg sweep at 4:16:15.740 PM EDT repriced the book in under 300 ms." It bought 84–85 YES at 45→96¢, sold 82–83 and bought the 86–87 tail. METAR peaked at about 82.9°F, while the CLI later printed MAX 84°F at 1:41 PM. The sweep came "~18 minutes before that public CLI text". The author speculated the aggressor had "a faster climate feed (WRH/timeseries, AWIPS-class, early CLI)". — [PredictCast KNYC](https://wxmap.io/predictcast/blog/KNYC-416-whale-trade)
  - **KDEN, 2026-08-07**: "At 5:17:24 PM, it reverses. Somebody sweeps B95.5 YES from 10¢ through 89¢ in one burst — 44 fills in a single timestamp." METAR read about 93–94°F; the CLI printed MAX 95°F at 3:36 PM, and the CLI text was "not publish[ed] until 5:29 PM". — [PredictCast KDEN](https://wxmap.io/predictcast/blog/KDEN-517-flash-crash)
- Other public bot write-ups take their observations from METAR, NWS or IEM, or scrapes (AccuWeather, Wunderground) polled every 30 s to 5 min. None claims sub-minute ASOS access:
  - [fsevkli/ProjectKM](https://github.com/fsevkli/ProjectKM) (30-second signal loop on METAR for KNYC, KMDW, KMIA, KAUS, KLAX, KDEN, KPHL)
  - [Ashrith Anumala weather system](https://ashrithanumala.github.io/w/weather-trading-system.html) (5-minute polls)
  - [EddieTGH predictor](https://github.com/EddieTGH/kalshi-weather-predictor) (temperature every 5 minutes)
  - [Nick Rae blog, 2026-03-15, updated 2026-08-27](https://nickrae.net/blog/kalshi-weather-bot.html)
  - [Steve Farmer Substack, 2026-08-12](https://stfarm.substack.com/p/i-audited-my-own-trading-bot-and)

### Inferences
- **DSM timing explains both PredictCast "whale" sweeps better than PredictCast's own guess (my inference).**
  - KNYC: the sweep at 16:16:15 EDT is 20:16:15Z. wethr.net lists KNYC DSM issuances near 20:14Z ([wethr NYC guide](https://wethr.net/edu/market/newyork)) and 20:21Z ([market bots](https://wethr.net/edu/market-bots)).
  - KDEN: the sweep at 5:17:24 PM MDT is 23:17:24Z, which matches the listed Denver DSM time of 23:17Z.
  - DSMs carry the running max derived from one-minute data. Both sweeps are therefore consistent with "DSM bots" reacting to a scheduled NWS text product, not with an exotic channel.
  - Worth checking for the KLAX 2026-08-29/30 events: wethr lists KLAX DSMs at about 22:08, 01:08 and 08:08Z.
- Sweeps 21 s and 53 s after a sensor minute, with no METAR, SPECI or DSM involved, fit the dial-in voice line (live current reading, roughly 1 to 2 calls per minute per line) better than any machine feed in the public record. The community-described OMO-bot pattern matches this.

### Gaps
- No Reddit, X, Discord or HN post was found in which a trader states their own dial-in latency, call cadence, or that they monopolize a line. Reddit and X content could not be read directly.
- I could not access wethr.net's "City Resources Summary" table listing which cities have active OMO bots.
- I found no first-person claims of SDR or VHF ASOS reception, LiveATC/ATIS monitoring, or private sensors placed next to settlement stations.

## Q2. Which tools and products are marketed to weather traders for live station data, and what sources and latencies do they disclose?

### Takeaway
The main paid tools (wethr.net, minuteTemp) market "1-minute"/"OMO" data and speed tiers. Where they disclose a source, it is METAR/ASOS via the public MADIS→Synoptic path, or Kalshi's own `live_data` index feed. minuteTemp's most specific latency claim is "2–3 seconds after Kalshi receives the station batch", which still trails the sensor minute by Kalshi's own receipt latency. No vendor claims phone or radio sourcing. wethr.net added a "much faster" undisclosed hourly/SPECI METAR source in July 2026.

### Cited Findings
- **minuteTemp**:
  - Coverage claims: "ASOS 1-MIN 18 settlement stations updated every minute"; "72 cities", "77 settlement stations tracked", "18 Stations on 1-minute data"; "Every other platform lags by 20 minutes. We update every 60 seconds."
  - On Kalshi's hourly index: "Each minute's provisional index lands about 2–3 seconds after Kalshi receives the station batch, well before the minute turns official 5 minutes later."
  - Delivery and pricing: a WebSocket `/ws/api/1m` stream; "<50ms avg latency" (delivery); the free tier has a "3 min delay".
  - Data provenance as stated: "Sourced from official METAR observations and ASOS stations." — [minuteTemp](https://minutetemp.com/)
- minuteTemp's Kalshi page (read 2026-10-01): 14 of 24 Kalshi daily stations "report every minute". It quotes the contract terms as naming NWS as source agency, with the value "as published on The Weather Company's Kalshi data portal (weather.com/kalshi)". — [minuteTemp Kalshi](https://minutetemp.com/kalshi)
- **wethr.net** paid tiers and API:
  - Paid users see each observation "the instant it reaches Wethr.net servers"; free users wait 3 minutes.
  - "Observations API… OMO not included; derivative data updates in real time." Pro is 60 req/min; Developer ($99/mo) is 300 req/min. — [wethr paid features](https://wethr.net/paid-features); [wethr API docs](https://wethr.net/edu/api-docs) ("Raw OMO data is not currently available through the Observations REST API")
- wethr.net update log, in date order:
  - 2026-07-16: "temperature blind spot" indicator for "non-precise observations (HF-METAR, OMO)".
  - 2026-07-17: Wethr High/Low and Push events name their sources ("metar, hf_metar, omo, 6-hour, dsm, cli").
  - 2026-07-18: personal-weather-station latency improvements.
  - 2026-07-28: "one of our new data sources has reliably provided hourly/special metar data that traditional metar sources fail to obtain during outages between the FAA and NWS". This "much faster data" is shown as "pending" ("mt-p") until "a second source confirms it". The source was not named.
  - 2026-09-18: one-minute data coverage API (missing/rejected minutes); 5-minute ingestion latency fix.
  - 2026-09-29: OMO Feed Status page.
  - 2026-09-30: Data Latency page (7-day and 30-day latency by station and observation type). — [wethr updates](https://wethr.net/updates)
- wethr.net OMO Feed Status snapshot during research: "1 delayed 87 live. No stations with issues right now." — [wethr OMO status](https://wethr.net/omo-status)
- Better Weather Bettor (betterweatherbettor.com) dashboard is labeled "MADIS HF METAR.dat Kalshi Daily Temps", with a linked "Weather Picks" Discord. — [Better Weather Bettor](https://betterweatherbettor.com)
- METAR.ws markets a WebSocket METAR/SPECI push service for Kalshi and Polymarket bots and claims "sub-800ms push delivery". Its own blog says "a report stamped 1200Z may not appear in downstream feeds until 1200:30Z or later." This is METAR/SPECI only, not one-minute data. — [METAR.ws](https://metar.ws/); [METAR.ws blog 2026-06-02](https://metar.ws/blog/metar-schedule-prediction-markets)
- Isocast claims bucket-crossing pushes "within seconds of the reading" for Polymarket cities, with a 60-second refresh and no source disclosed. — [Isocast](https://isocast.dev/)
- Apify actors:
  - evolve-data/weather-station-data uses api.weather.gov, aviationweather.gov and the IEM archive. It says intraday highs come "from hourly and special METAR reports. The official daily value uses 1-minute data and can differ by a degree", and suggests polling "every 5–15 minutes". — [Apify evolve-data](https://apify.com/evolve-data/weather-station-data/api)
  - bigdavidson METAR actor notes Kalshi "resolve[s] per The Weather Company… weather.com/kalshi". — [Apify bigdavidson](https://apify.com/bigdavidson/metar-nws-weather-station-observations)
- Other trader dashboards with no sub-minute claims:
  - Skycast: "may be delayed by 5+ minutes". — [Skycast](https://skycast.site/)
  - wxsignals: station data marked "SOON". — [wxsignals](https://wxsignals.com/)
  - VWeatherStation (KNYC page) and KNYC DSM reader. — [VWeatherStation](https://vweatherstation.com/prediction-markets/new-york/); [KNYC DSM reader](https://knyc-dsm-reader.vercel.app/)
- A third-party MCP tool, "kalshi_weather_edge" on a Twilio MCP gateway, states: "These markets DO NOT settle on the NWS. They settle on The Weather Company (weather.com) at a Kalshi station code such as CLINYC." It reports that on 13 settled KXHIGHNY days to 2026-09-11 "the MARKET beat the forecast" (Brier 0.1008 vs 0.1594). — [PolicyLayer listing](https://policylayer.com/tools/io-github-pipeworx-io-twilio/kalshi-weather-edge)
- **Synoptic (upstream of most tools)**:
  - Full one-minute data has been available since 2019 as network stations with a "1M" suffix (e.g., KSLC1M).
  - "HF-ASOS, when operating normally, usually arrives with between 2 and 5 minutes latency."
  - "HF-ASOS data was unavailable from its source between October 2023 and January 2026."
  - The feed is "experimental", and "brief to several-day outages are not uncommon." — [Synoptic HF-ASOS docs](https://docs.synopticdata.com/services/high-frequency-asos)

### Inferences
- Every marketed "1-minute" product appears to sit downstream of MADIS→Synoptic HF-ASOS or Kalshi's `live_data` endpoint. That matches the roughly 2m15s–2m40s floor observed by the caller.
- No vendor discloses, or plausibly offers, the 21–53 s timing seen at KLAX.
- wethr.net's unnamed July-2026 "faster" METAR source survives FAA–NWS outages. That suggests an FAA-side feed (for example FAA SWIM or a WMSCR-connected provider) rather than NWS/aviationweather.gov. This is speculation; the source is undisclosed.

### Gaps
- wethr.net's Data Latency page returned 404 at `/data-latency`, so I have no latency numbers by observation type.
- minuteTemp does not say where its non-index one-minute data comes from.
- No product page for a "WeatherBets"-style tool disclosing phone or radio sourcing was found.

## Q3. Evidence of private sensors, airport-adjacent radio, other channels, and KNYC Central Park specifics

### Takeaway
I found no public evidence of traders using private sensors or VHF/SDR reception. Official ASOS documentation shows three non-machine-feed outlets for one-minute (OMO) data:
1. the voice dial-in line;
2. the ground-to-air radio voice broadcast;
3. a separate remote data dial-in, where an "Unsigned User" can view the one-minute screen and "Direct Command Mode" needs a remote access code.

The third is an access-controlled NWS maintenance path and should be flagged, not recommended. KNYC is a non-airport station and has no ground-to-air radio. KNYC traders lean on DSM, CLI and 6-hour products, and on the phone line.

### Cited Findings
- **NWS ASOS User's Guide data-outlet chart.** OMO data is available through:
  - OID and remote-user interactive screens, including the "UNSIGNED USER LEVEL";
  - on-site VDU and printer;
  - NWS AFOS/AWIPS and FAA NADIN, as "Selected OMO data provided once every 5 or 15 minutes upon request";
  - "COMPUTER GENERATED VOICE — GROUND-TO-AIR RADIO" and "TELEPHONE DIAL-IN", footnoted "Either OMO or last transmitted METAR/SPECI – Not both".
  - Voice output is "available through FAA radio broadcast to pilots, and general aviation dial-in telephone lines." — [ASOS User's Guide charts](https://www.weather.gov/media/asos/aum-charts2.pdf); [ASOS User's Guide](https://www.weather.gov/media/asos/aum-toc.pdf)
- **NWS ASOS OID training.**
  - "Remote OID users and remote interactive computer users may only sign on as: 1) Unsigned User 2) Technician 3) System Manager."
  - "Using remote access (mainly ProComm dialup), you can dial into the ASOS and view nearly everything you need using the default access 'Unsigned User'."
  - The main screen shows "latest transmitted METAR/SPECI and current 1-Minute data". — [NWS ASOS OID training](https://www.weather.gov/media/surface/ASOS_OID_final111612.pdf)
- ASOS software release notes: "The DCM [Direct Command Mode, remote access] requires only a remote access code and not a password." DCM supports downloading 12-hour archive data. — [ASOS release notes 2.6A](https://www.weather.gov/media/asos/ASOS%20Implementation/relnoteprocup.pdf); [2.7A](https://www.weather.gov/media/asos/ASOS%20Implementation/relnotewind.pdf)
- 2009 AMS ASOS sustainment paper:
  - "The basic difference between the OMO and the METAR and SPECI is that the OMO is not transmitted long-line beyond the FAA communications network."
  - "Remote access to ASOS is through dial in lines used primarily for remote monitoring, maintenance, and data archiving."
  - "Existing ASOS configurations do not have the operational capability to distribute data over an Internet Protocol (IP) network." — [AMS paper](https://ams.confex.com/ams/pdfpapers/145078.pdf)
- MADIS gets OMO from the "FAA Weather Message Switching Center Replacement System (WMSCR)". The operational feed has been live since 2015-10-27, with all one-minute obs processed since November 2017. "current and previous hour's data are processed every 5 minutes." — [MADIS OMO](https://madis.ncep.noaa.gov/madis_OMO.shtml)
- The FAA lists approved third-party WMSCR/NADIN service providers. This is for non-federal AWOS uplink, but it shows WMSCR-connected commercial firms exist: All Weather Inc., DBT Transportation Services, Mackinac Software (anyAWOS), Remote Systems Integration, University Research Foundation. — [FAA WMSCR provider list](https://www.faa.gov/airports/planning_capacity/non_federal/resources/wmscr_list.pdf); [FAA WMSCR FAQ](https://www.faa.gov/airports/planning_capacity/non_federal/doc/awos_wmscr_faq.pdf)
- wethr.net added personal-weather-station (PWS) feeds and a "Neighboring Stations Map" ("Stations 30 miles west just jumped 3°F. Yours is next."). Traders are using nearby non-official sensors for anticipation, but not as a proxy for the settlement sensor. — [wethr paid features](https://wethr.net/paid-features); [wethr updates](https://wethr.net/updates)
- **KNYC specifics**:
  - wethr.net's KNYC schedule: CLI about 06:32 UTC ±18 min; 24-hour-high METAR about 04:51 UTC; hourly METAR at :51; DSMs at about 05:13, 05:28, 20:14 and 21:13 UTC; 6-hour max METARs at 05:51, 11:51, 17:51 and 23:51 UTC.
  - KNYC "is located in the heart of Manhattan within Central Park", unlike airport stations. — [wethr KNYC guide](https://wethr.net/edu/market/newyork)
  - Kalshi daily NYC settles on CLINYC (Central Park). Polymarket NYC uses KLGA. — [Turbine blog 2026-09-08](https://www.turbinefi.com/blog/how-to-trade-kalshi-weather-markets-2026); [temprr](https://temprr.trade/blog/polymarket-weather-resolution-stations)
  - METAR.ws describes KNYC as an NWS climate station rather than an airport. — [METAR.ws](https://metar.ws/)
  - The 2026-07-13 KNYC sweep came while METAR showed about 82.9°F and the eventual CLI MAX was 84°F. The one-minute max was not visible in public machine feeds. — [PredictCast KNYC](https://wxmap.io/predictcast/blog/KNYC-416-whale-trade)

### Inferences
- For KNYC (no airport, no ground-to-air radio, no HF-ASOS "1M" feed per the caller's background), the realistic sub-minute channels are:
  - **the public voice dial-in line**;
  - **the remote data dial-in "Unsigned User" screen**. This is an NWS remote-maintenance interface. Using it without NWS authorization would be bypassing access controls, and it should be treated as off-limits.
  - Everything else (DSM, CLI, 6-hour/24-hour max) is scheduled text.
- **Monopolizing the shared dial-in voice line** is a fairness and acceptable-use concern. wethr.net and testedmedia both note the line is single-access and meant for pilots.
- Kalshi's Appendix C bars "NWS/FAA personnel and contractors responsible for operating, maintaining… the… member stations" from trading the NYC index (see Q4). That signals Kalshi treats insider access via station maintenance channels as material nonpublic information (MNPI) risk.

### Gaps
- I did not confirm whether each target station (KNYC, KLAX, KMIA, KPHL, KMDW, KDEN, KAUS) has a remote data modem line that is still active today, or whether "Unsigned User" access still works without a code. ASOS software has changed since those documents.
- No evidence was found for or against traders using LiveATC ATIS streams, VHF ASOS broadcasts, or private sensors at these airports.

## Q4. Public statements by Kalshi (docs, CFTC filings, rules) on data sources, fairness and latency; The Weather Company's role since August 2026

### Takeaway
Kalshi's CFTC filing for the NYC Weather Index (2026-09-09) names Synoptic Data PBC's HF-ASOS network 258 (KLGA1M and others) as the primary source. Eligibility is set by Kalshi's receipt time, with a 300-second deadline. The filing bars Synoptic staff and station maintainers from trading. The Weather Company (TWC) became Kalshi's settlement data partner by announcement on 2026-08-27. Sources conflict on whether daily high/low markets now settle on TWC or on the NWS CLI.

### Cited Findings
- **CFTC filing ptc09092624308** (KalshiEX, 2026-09-09; NYCWINDEX, "Will the Kalshi Weather Index for New York City be…"):
  - Members: eight ASOS stations — KLGA, KEWR, KTEB, KCDW, KHPN, KFRG, KSMQ, KISP — each with weight 0.125.
  - "the primary source is the station's one-minute high-frequency ASOS air temperature record (station identifiers KLGA1M, KEWR1M…) delivered through Synoptic Data PBC (HF-ASOS network 258). A primary record is eligible for event minute t only if its observation time equals t exactly."
  - Fallback is the prior-minute HF-ASOS reading, then the official METAR/SPECI T-group (max age 75 min). "Generated or derived products (including HFMETAR) are not eligible fallbacks (hfmetars=0)."
  - "Receipt time is authoritative for eligibility; provider latency telemetry is diagnostic only." The eligibility deadline is "t + D, where D = 300 seconds."
  - Quorum: at least 7 members and at least 0.875 weight. Initial offsets: KLGA1M +1.0°C, KEWR1M +1.0, KTEB1M +1.0, KCDW1M 0, KHPN1M −1.0, KFRG1M 0, KSMQ1M −1.0, KISP1M 0.
  - Confidential appendices include "Appendix G (Confidential) – Agreement with Synoptic".
  - Appendix C trading prohibitions, "In addition to the general prohibition against trading on material nonpublic information": exchange personnel; "Synoptic Data PBC employees and affiliates"; "NWS/FAA personnel and contractors responsible for operating, maintaining, calibrating, or repairing the seven named member stations"; and "Households and MNPI recipients of any of the above." — [CFTC filing PDF](https://www.cftc.gov/filings/ptc/ptc09092624308.pdf)
- **Kalshi API docs** (`GET /live_data/weather/{city}`):
  - The index is the "canonical minute-resolution series behind hourly temperature markets."
  - `detailed=true` exposes per-station readings such as `KMIA1M` with `source` `hf_asos` ("exact-minute primary") or `metar`. QC codes include `late` ("received after the deadline; diagnostic only").
  - Trailing minutes "still inside their receipt deadline" are served as `incomplete`/`pending`.
  - The calibrations endpoint publishes weights and offsets, re-estimated weekly. — [Kalshi Get Weather Index](https://docs.kalshi.com/api-reference/live-data/get-weather-index.md); [Kalshi calibrations](https://docs.kalshi.com/api-reference/live-data/get-weather-index-calibrations.md)
- **TWC partnership press release (2026-08-27)**:
  - "Kalshi will use The Weather Company's enterprise-grade weather data feeds as its trusted source for verifying weather-related market outcomes."
  - "Every value we deliver carries a documented method… whether it comes from one official station or is derived from several observation sources" (Dr. James Belanger).
  - "Kalshi's climate and weather vertical… pacing toward $1.1 billion in annualized volume." — [The Weather Company](https://www.weathercompany.com/news/kalshi-and-twco-partner)
- weather.com/kalshi is TWC's portal: "Official Climate Reports — Access verified climate observations from official government climate stations" (Hourly Temps, Daily Climate). — [weather.com/kalshi](https://weather.com/kalshi)
- **Conflicting accounts of the daily settlement source**:
  - Kalshi Help Center: "Daily high/low temperature markets settle based on the final climate report issued by the National Weather Service… Hourly temperature markets settle on readings from The Weather Company." For hourly markets, "Settlement processes approximately 25-35 minutes after the market closes." — [Kalshi Help](https://help.kalshi.com/en/articles/13823837-weather-markets)
  - Turbine (2026-09-08): KXHIGHNY's live rules text says the high is determined "according to The Weather Company" (weather.com/kalshi), while the linked rulebook PDF still names NWS. — [Turbine](https://www.turbinefi.com/blog/how-to-trade-kalshi-weather-markets-2026)
  - nextpredict: daily temperature has been on TWC "since Aug. 14, 2026". — [nextpredict](https://nextpredict.io/prediction-markets/weather)
  - minuteTemp (read 2026-10-01): contract terms name NWS as source agency, and the rules cite the value as published on weather.com/kalshi. — [minuteTemp Kalshi](https://minutetemp.com/kalshi)
- OddsShopper (2026-08-13): "nobody has a private line to the data that settles it… The data… is a public document." — [OddsShopper](https://www.oddsshopper.com/articles/prediction-markets/kalshi-nws-data-behind-the-market)
- CFTC RAINM Amendment 3 (2026-09-02): "Only the first qualifying Daily Climate Report is determinative." — [CFTC RAINM](https://www.cftc.gov/filings/orgrules/rules09022622999.pdf)

### Inferences
- Kalshi's own index uses Synoptic HF-ASOS with a 300 s receipt deadline. Kalshi therefore treats a roughly 2–5 minute provider latency as normal, and designs settlement around receipt time rather than sensor time.
- Any channel that reads the sensor live (phone, radio) is structurally faster than the data Kalshi itself waits for.
- The MNPI clause plus the station-maintainer ban suggest Kalshi regards privileged station access as insider information. Publicly broadcast data (voice line, ground-to-air radio) is not covered by those named bans. That is my reading, not a legal conclusion.

### Gaps
- I did not find a separate CFTC filing for the Los Angeles, Miami or other city index configurations, or the daily-temperature rule amendment that moved to TWC.
- I did not find a Kalshi statement on latency fairness or phone-line use.
- TWC's own ingest path and latency are not public.

## Q5. Other legitimate real-time channels not already covered (beyond phone dial-in, VHF ASOS/ATIS, D-ATIS, FIS-B, MADIS/Synoptic, NWWS/NOAAPort/EMWIN, FAA SWIM CSS-Wx)

### Takeaway
A few additional channels appear in the sources:
- FAA WMSCR/NADIN (where OMO originates; reachable only through FAA-approved providers or agencies);
- the Kalshi `live_data` index endpoint itself (provisional pending minutes);
- METAR WebSocket push services;
- scheduled DSM products;
- nearby PWS/mesonet sensors as leading indicators.

The ASOS remote data dial-in ("Unsigned User"/DCM) exists, but it is an access-controlled maintenance interface and should not be treated as a legitimate trader channel.

### Cited Findings
- **FAA WMSCR → NADIN.** The ASOS chart shows OMO flowing to WMSCR and NADIN-II. MADIS ingests OMO from WMSCR, and the FAA maintains a list of approved WMSCR third-party providers. — [ASOS charts](https://www.weather.gov/media/asos/aum-charts2.pdf); [MADIS OMO](https://madis.ncep.noaa.gov/madis_OMO.shtml); [FAA WMSCR list](https://www.faa.gov/airports/planning_capacity/non_federal/resources/wmscr_list.pdf)
- **Kalshi `live_data` with `detailed=true`.** It exposes `pending` raw station readings on `incomplete` trailing minutes before QC. This is an official, public, low-latency view of what Kalshi has received. — [Kalshi docs](https://docs.kalshi.com/api-reference/live-data/get-weather-index.md)
- **ASOS DSMs.** These are scheduled intra-day summaries with running max and min, at per-station UTC times. They are a recognized market-moving channel ("DSM Bot"). — [wethr market bots](https://wethr.net/edu/market-bots)
- **WebSocket METAR push** (METAR.ws, sub-800 ms push after publication). — [METAR.ws](https://metar.ws/)
- **Personal weather stations and neighbouring stations** as leading indicators (wethr.net PWS latency upgrade, 2026-07-18; Neighboring Stations Map). — [wethr updates](https://wethr.net/updates); [wethr paid features](https://wethr.net/paid-features)
- **ASOS remote data dial-in.** Remote users can sign on as "Unsigned User", and the screen shows "current 1-Minute data". DCM "requires only a remote access code and not a password." The access codes are distributed by NWS regional ASOS staff ("Check with your Regional ASOS System Mgr or ESA/ASOS Eltech for the necessary passwords"). — [NWS OID training](https://www.weather.gov/media/surface/ASOS_OID_final111612.pdf); [ASOS release notes](https://www.weather.gov/media/asos/ASOS%20Implementation/relnoteprocup.pdf)
  - **Flag: using this without NWS authorization would mean bypassing access controls on federal maintenance infrastructure.**
- **FAA WSP/TDWR interface.** ASOS has a dedicated serial port that feeds wind data (updated every 10 s) to FAA systems. It is an FAA-internal path, not public, and wind-only. — [ASOS release notes v2.79](https://www.weather.gov/media/asos/ASOS%20Implementation/release_notes.279_final.pdf)

### Inferences
- I found no new public, machine-readable channel faster than Synoptic or MADIS for one-minute temperature.
- The only sub-minute public channels remain the audio outputs: the dial-in voice line and, at airports that have one, the ground-to-air ASOS radio.
- A WMSCR/NADIN-connected commercial feed could plausibly carry OMO faster than MADIS. Only the FAA-approved providers or agency partners could confirm this, and none advertises OMO resale to traders.

### Gaps
- No public latency figure for WMSCR/NADIN OMO delivery, nor whether approved providers resell OMO, was found.
- I could not verify whether TWC receives a faster feed than Synoptic.
- I found no trader discussion of LiveATC or ATIS audio streams, ACARS, or airline datalink as temperature sources.

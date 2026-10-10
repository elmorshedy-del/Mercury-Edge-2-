# ASOS public dial-in line: demand, contention and the rules that govern it

Research date 2026-10-10. Scope: why the public ASOS voice line is busy at peak times, how "who gets the line" is decided, and what FAA/NWS rules say. Constraint followed throughout: this is explanation only. Nothing here recommends redial timing, parallel callers, holding the line, defeating the disconnect, or using the password-protected remote-user modem port. The queueing maths describes what the caller observes; it is not a recipe for winning the line.

Background not repeated here (see `research_notes/Real time ASOS one minute access/telephony_official_access.md`, `trader_community_sources.md`, and `reports/Real time ASOS one minute access.md`): one published number per site, 100 wpm voice, OMO vs METAR voice mode, ASOS 2.0 status, MADIS/Synoptic latency, the remote-user port restrictions, and the KLAX first-mover case.

Notation: λ = call-attempt rate, h = mean holding time per connected call (about 90 s, plus a few seconds of ringing), A = λ·h (offered load in Erlangs), B = probability an attempt hears busy, θ = redial rate of one blocked caller (1/θ = mean redial interval), ρ = carried load.

---

## 1. Teletraffic model: a single line with no queue (Erlang B, N = 1), about 90 s holding time

### Takeaway
A single line with no queue and no call waiting is Erlang's loss system with one server. The probability that an attempt hears busy is B = A/(1+A), and this also equals the fraction of time the line is occupied. The formula holds for any holding-time distribution, so a near-fixed ~90 s call is covered. Busy probability rises steeply at low load: it is 13% at 6 attempts per hour, 60% at 1 attempt per minute, and 88% at 5 attempts per minute. Capacity is capped at 3600/h ≈ 40 connected calls per hour, or about 38 per hour once a few seconds of ringing are counted. Past roughly 1 attempt per minute, extra attempts almost all hear busy and add almost no completed calls.

### Cited Findings
- **Erlang B formula.** Erlang's B-formula E₁,ₙ(A) gives loss probability for n circuits at offered traffic A. For n = 1 it reduces to E₁,₁(A) = A/(1+A). — [ITU-T E.800-series Supplement 1, "Table of the Erlang formula" (1988)](https://www.itu.int/rec/dologin_pub.asp?id=T-REC-E.800SerSup1-198811-I%21%21PDF-E&lang=s&type=items); [Iversen, *Teletraffic Engineering and Network Planning*, DTU 2015, ch. 4](https://backend.orbit.dtu.dk/ws/files/118473571/Teletraffic_34342_V_B_Iversen_2015.pdf)
- **Insensitivity.** "Erlang's B-formula, which above is derived under the assumption of exponentially distributed holding times, is valid for arbitrary holding time distributions… all classical loss systems with full accessibility are insensitive to the holding time distribution." The deterministic ~90 s ASOS call is therefore covered exactly, given Poisson arrivals. — [Iversen 2015, §4.6.2](https://backend.orbit.dtu.dk/ws/files/118473571/Teletraffic_34342_V_B_Iversen_2015.pdf)
- **Forced disconnect is a standard telephony protection.** "If a control path is occupied longer than a given time, a forced disconnection of the call will take place. This makes it impossible for a single call to block vital parts of the exchange." — [Iversen 2015, ch. 1](https://backend.orbit.dtu.dk/ws/files/118473571/Teletraffic_34342_V_B_Iversen_2015.pdf)
- **Minimum required capacity of an automated-weather phone answerer is one call.** "Typically, the telephone-answering device should have the capability to answer five calls at a time… The minimum requirement is that the system answers a single call." This is the FAA standard for non-federal AWOS. It does not govern federal ASOS, but it is the closest published design rule. — [FAA AC 150/5220-16E ¶3.20.a(7), dated 03/10/2017](https://www.faa.gov/documentLibrary/media/Advisory_Circular/AC_150_5220-16E.pdf)
- **Single-line behaviour in practice.** "Often, only one call can access the ASOS line at a time." — [wethr.net "Navigating Market Bots & Strategies," updated 2026-02-15](https://wethr.net/edu/market-bots)

**Worked table (calculation, this note).** Computed from B = A/(1+A) with h = 90 s, so A = λ[per min] × 1.5. Under Poisson arrivals, occupancy equals B (PASTA). Completed calls per hour = 60λ(1−B).

| Attempts/min (all callers) | Attempts/hr | A (Erlang) | Busy probability B | Line occupancy | Completed calls/hr |
|---|---|---|---|---|---|
| 0.05 | 3 | 0.075 | 7.0% | 7.0% | 2.8 |
| 0.1 | 6 | 0.15 | 13.0% | 13.0% | 5.2 |
| 0.25 | 15 | 0.375 | 27.3% | 27.3% | 10.9 |
| 0.5 | 30 | 0.75 | 42.9% | 42.9% | 17.1 |
| **1** | 60 | 1.5 | **60.0%** | 60.0% | 24.0 |
| 2 | 120 | 3.0 | 75.0% | 75.0% | 30.0 |
| **5** | 300 | 7.5 | **88.2%** | 88.2% | 35.3 |
| **10** | 600 | 15 | **93.8%** | 93.8% | 37.5 |
| **20** | 1,200 | 30 | **96.8%** | 96.8% | 38.7 |
| **40** | 2,400 | 60 | **98.4%** | 98.4% | 39.3 |
| limit | — | — | → 100% | → 100% | → 40.0 (3600/90) |

Sensitivity to holding time at 1 and 5 attempts/min:

| h | 1/min | 5/min |
|---|---|---|
| 60 s | B = 50.0% | 83.3% |
| 90 s | 60.0% | 88.2% |
| 120 s | 66.7% | 90.9% |

### Inferences
- **Poisson assumption.** The table is exact only if the combined attempt stream is close to Poisson (many independent callers). Bots that redial on fixed timers violate this, and §2 handles that case. Confidence that the table is the right first-order description of "how busy vs how much load": high.
- **Ringing counts as occupancy.** The AC requires an answer "prior to completion of the second ring", and the line is seized from the moment it rings. The effective h is therefore ~90 s of audio plus a few seconds of ringing (~94 s). That moves capacity from 40 to about 38 connected calls per hour. Confidence: medium-high. The ASOS answer delay is not documented; the AWOS rule is used as a proxy.
- **Low background load already produces busy signals.** Even with no bots, 6 pilot calls per hour (one every 10 minutes) gives about a 13% chance of a busy signal. During a frontal passage, when many pilots call at once, it is higher. This fits pilot anecdotes from before prediction markets existed (§3). Confidence: high.

### Gaps
- No public measurement of call attempts or occupancy on any ASOS line was found. No FAA/NWS or carrier statistics either. The λ values above are illustrative, not measured.
- The number of voice ports, hunt or rollover groups, and any call-waiting configuration per site are undocumented. The model assumes one line.

---

## 2. Redialers and retrial-queue theory: why busy signals multiply, and how "who gets the line" is decided

### Takeaway
Blocked callers who redial form an "orbit". The relevant model is the retrial queue (Falin & Templeton 1997; Artalejo & Gómez-Corral 2008), not Erlang B. Two results explain what a caller sees.

1. **With persistent callers, redials multiply attempts but not completed calls.** For the M/M/1 retrial queue, line occupancy equals the fresh demand ρ = λ_fresh·h, whatever the redial rate. Faster redialing mostly multiplies the attempts that hear busy. Example: at ρ = 0.5 with 5 s redials, 95% of attempts hear busy although the line is idle half the time. A high personal busy rate therefore does not by itself prove many distinct callers.
2. **There is no FIFO queue.** When the line frees, the next call setup to reach the terminating switch takes it. Each waiting caller's chance of winning is roughly proportional to its own attempt rate, θ_i/(λ_fresh + Σθ_j). With fixed-interval redialers, the fastest one wins somewhat more than its proportional share.

A single automated caller that re-dials soon after every disconnect can, alone, keep the line about 90% occupied. That pushes human callers' success rate down sharply.

### Cited Findings
- **Definition and relevance to telephony.** "The application of auto-repeat facilities in telephone systems… have led to growing interest in retrial queueing models." In the basic model, "any customer who finds all servers busy upon arrival is obliged to leave the service area, but he repeats his demand after an exponential time" (the classical retrial policy). Kosten is quoted there: "any theoretical result that does not take into consideration this repetition effect should be considered suspect." — [Artalejo & Gómez-Corral, *Retrial Queueing Systems: A Computational Approach*, Springer 2008, DOI 10.1007/978-3-540-78725-9](https://link.springer.com/book/10.1007/978-3-540-78725-9); [sample chapter text](http://download.e-bookshelf.de/download/0000/0129/09/L-G-0000012909-0002346216.pdf)
- **Standard monograph.** Falin & Templeton, *Retrial Queues* (Chapman & Hall, 1997) covers the single-server model's stationary distribution, waiting time, and multiclass and non-persistent variants. — [Routledge listing](https://www.routledge.com/Retrial-Queues/Falin-Templeton/p/book/9780412785504)
- **Classical policy.** Under the classical retrial policy, "each blocked customer stays in the orbit for an exponentially distributed time independently of other customers. As a result, the retrial rate is proportional to the number of customers in the orbit". This "naturally arises from… call center and telephone exchange system, where customers in the orbit act independently because a retrial customer cannot observe the behavior of the others." Multiclass models with class-specific retrial rates μ_k exist. — [Tuan, "Retrial Queueing Models: A Survey on Theory and Applications"](http://infoshako.sk.tsukuba.ac.jp/~tuan/papers/Tuan_chapter_ver3.pdf)
- **Waiting-time model.** In the M/G/1 retrial queue the virtual waiting time analysis "is intricate because customers in the orbit operate under a random order discipline". That is, there is no FIFO. — [Artalejo & López-Herrero, "The M/G/1 retrial queue: an information theoretic approach" (2005)](https://exa.ai/library/publication/k8c6gltl7tq)
- **Empirical subscriber persistence (classic telephone data).** In Ordrup measurements:
  - "If a subscriber experience blocking or B–busy there is 70% probability that the call is repeated within an hour."
  - "The probability of success decreases with the number of call–attempts, while the persistence increases."
  - Persistence rose from 0.41 after the 1st attempt to 0.74 after the 5th.
  - "In countries with an overloaded telecommunication network… a big percentage of the call–attempts will be repeated call–attempts."
  - Simple model: attempts per call intent = 1/(1 − B·b), where b is persistence. — [Iversen 2015, §1.10, Table 1.3, Example 1.10.2](https://backend.orbit.dtu.dk/ws/files/118473571/Teletraffic_34342_V_B_Iversen_2015.pdf)
- **Repeat attempts in ITU traffic engineering.** With "capabilities for automatic repetition," service characterisation "needs the introduction of a supplementary variable, namely the repetition rate, to evaluate the number of call attempts per call demand." — [ITU-T (CCITT) E.711 (1988)](https://www.itu.int/rec/dologin_pub.asp?id=T-REC-E.711-198811-S%21%21PDF-E&lang=f&type=items)
- **Third-party relays already treat ASOS/AWOS busy signals as routine.** A patented commercial relay that dials AWOS/ASOS numbers for pilots includes busy wait-and-retry loops. — [US Patent 7,088,241](https://www.freepatentsonline.com/7088241.html)

**Calculation (this note): M/M/1 retrial queue, h = 90 s, classical retrial policy.** Closed form (standard M/G/1 classical-retrial result, Falin & Templeton ch. 1): P(line busy) = ρ, and E[orbit] = λ²E[S²]/(2(1−ρ)) + λρ/(θ(1−ρ)). I verified this numerically by solving the truncated CTMC; the two agreed to 3 decimals in every case below. "Attempts per call" = 1 + θ·E[wait].

| Fresh demand (calls/hr wanting one connection) | ρ = occupancy | Mean redial interval | Attempts/hr | Attempts per completed call | Share of attempts hearing busy | Mean wait to connect |
|---|---|---|---|---|---|---|
| 10 | 0.25 | 120 s | 16 | 1.6 | 37% | 70 s |
| 10 | 0.25 | 5 s | 73 | 7.3 | 86% | 32 s |
| 20 | 0.50 | 120 s | 55 | 2.8 | 64% | 210 s |
| 20 | 0.50 | 30 s | 100 | 5.0 | 80% | 120 s |
| 20 | 0.50 | 5 s | 400 | 20 | 95% | 95 s |
| 30 | 0.75 | 120 s | 188 | 6.3 | 84% | 630 s |
| 30 | 0.75 | 5 s | 1,740 | 58 | 98% | 285 s |
| ≥ 40 | ≥ 1 | any | unbounded | — | → 100% | unstable: orbit grows until callers give up |

**Calculation (this note): who seizes a freed line.**
- **Exponential redials:** with competing exponential clocks, caller i wins the next idle period with probability θ_i/(λ_fresh + Σθ_j). That is exactly proportional to attempt rate.
- **Fixed-interval redialers** with random phase (Monte Carlo, 200k trials), comparing a rate-proportional share with the simulated share:

| Redial intervals | Rate-proportional share | Simulated share |
|---|---|---|
| 5 s vs 15 s | 0.75 / 0.25 | 0.83 / 0.17 |
| 3 s vs 30 s | 0.91 / 0.09 | 0.95 / 0.05 |
| 2 s, 10 s, 60 s, 120 s | 0.80 / 0.16 / 0.03 / 0.01 | 0.88 / 0.10 / 0.02 / 0.01 |

**Calculation (this note): mixed callers.** Discrete-event simulation over 200 h. Pilots: Poisson, 6 fresh calls/hr; they retry on busy after Exp(60 s) and give up after 5 tries. Each "bot" re-calls a fixed interval after its own call ends or after a busy. Holding time 90 s plus 4 s ringing.

| Persistent automated callers (redial interval) | Line occupancy | Pilots who connect within 5 tries | Pilot attempts hearing busy | Connections/hr taken by the bot(s) |
|---|---|---|---|---|
| none | 16% | 98.5% | 26% | — |
| one, 600 s | 27% | 97.4% | 40% | 4.4 |
| one, 60 s | 66% | 85.3% | 68% | 20.4 |
| one, 10 s | 91% | 35.5% | 92% | 32.7 |
| two, 10 s and 30 s | 93% | 29.5% | 93% | 25.3 + 8.5 |
| three, 3 s / 10 s / 60 s | 98% | 11.2% | 98% | 27.1 + 8.4 + 1.3 |

### Inferences
- **"Who gets the line" mechanics** (high confidence on mechanism; medium on carrier details):
  - A plain business line (POTS or its VoIP equivalent) without call waiting or a hunt group has no queue.
  - When the ASOS hangs up, the line returns to idle at the terminating central office or SIP endpoint. The first call setup that arrives afterwards is offered to the line; everyone else gets busy (SIP 486 Busy Here on VoIP legs).
  - The winner is decided by arrival order at the terminating switch. In effect this is random among callers, weighted by how often each one attempts, with network post-dial delay adding jitter.
  - Nothing remembers how long anyone has waited, and the caller who just finished can win again if it re-attempts first.
- **Why the line is busy "most of the time" at peaks** (high confidence on mechanism; medium on attribution):
  - With a single line, about 40 calls/hr of genuine demand saturates it.
  - Far less is needed if even one automated caller re-calls continuously: in the simulation, a single 10 s re-caller holds the line ~91% of the time.
  - Busy reports therefore do not need many bots. One or two persistent callers per station during market-sensitive windows are enough to explain near-constant busy signals.
- **Your own busy rate overstates congestion if you redial quickly.** In the retrial model, the share of attempts that hear busy rises toward 100% as the redial interval shrinks, even though occupancy stays at ρ. Inferring "how many others are calling" from one's own busy count is biased upward. Confidence: high; this follows directly from the model.
- **Who bears the cost** (high confidence):
  - A pilot who calls once or twice and then gives up (low persistence, the Iversen-style human pattern) is the caller most hurt by automated persistence.
  - In the simulation, pilot success within 5 tries fell from ~98% with no bots to ~36% with one 10 s re-caller.
  - This externality is why the design intent (§4) is short, auto-disconnected calls.
- **Limits of the model** (medium confidence):
  - Bots that stop calling when markets are not near a bucket edge make demand strongly time-varying. The stationary results apply within a peak window, not across a whole day.
  - Callers who give up (impatient or non-persistent retrial models in Falin & Templeton) keep an overloaded line stable at about 100% occupancy instead of an infinitely growing orbit.

### Gaps
- No trace data (call detail records) exists publicly for any ASOS number, so redial intervals, number of distinct callers, and bot vs human split cannot be measured from outside.
- Carrier-side behaviour was not verified: whether any carrier rate-limits or analytics-blocks repeated short calls to these numbers, or returns "busy" for its own congestion.

---

## 3. Who calls these lines and when: pilots, hobbyists, prediction-market traders and bots

### Takeaway
- **Pilots** have used ASOS/AWOS phone lines for decades and reported busy signals before prediction markets existed, typically when "a crazy front is coming through."
- **Trader demand is now documented in community sources, not mainstream media:**
  - wethr.net's bot guide names an "OMO Bot" that "automate[s] calls" to ASOS dial-in lines and warns of "cities where OMO bots are known to be active."
  - An open-source Polymarket dashboard (July 2026) ships a Twilio/Telnyx calling agent that fires in pre-METAR "snipe windows."
- **No mainstream outlet was found reporting on bettors tying up ASOS phone lines.** This covered Bloomberg, WSJ, NYT, Axios, 404 Media, The Verge, Business Insider and local news. 2026 weather-market coverage centres on the Paris CDG sensor-tampering case and the Kalshi–Weather Company partnership.
- **Peak windows (inferred):**
  - afternoon hours near the daily maximum;
  - the 20–35 minutes before hourly METARs and around 6-hour-max, DSM and CLI release times;
  - days when the running high sits near a bucket edge;
  - weather-event periods, for pilots.
- The bot share of callers cannot be measured publicly. For KNYC, a non-airport station, essentially all callers must be non-pilots.

### Cited Findings
- **Pilots: busy lines predate prediction markets** (2016): "The only downside to using the phone number is that it will be busy sometimes...usually when a crazy front is coming through and there are a bunch of us all trying to see how strong the winds are at that exact second." — [Pilots of America, "Phone number for ATIS?" (Sep 2016)](https://www.pilotsofamerica.com/community/threads/phone-number-for-atis.98234/)
- **Pilots value the line's immediacy** (2023):
  - "If you listen to an AWOS/ASOS on the radio, or call it on the phone, the weather is up-to-the-minute current. However, if you bring it up in an app… the recency of the report varies widely."
  - One pilot asked Flight Service to call the local AWOS number because ADS-B METARs were stale. — [Pilots of America (Sep 2023)](https://www.pilotsofamerica.com/community/threads/awos-asos-timeliness-on-internet-ads-b.144418/)
- **Pilots use the phone when a station is not reaching the network** (2022): "ASOS is broadcasting on vhf & telephone but not connected to the internet… Called the asos line; it's fine." — [Pilots of America (Dec 2022)](https://www.pilotsofamerica.com/community/threads/asos-prob-notam-or-no.141149/)
- **Relay services add callers to the same line.** The anyAWOS toll-free bridge (free with ads, later fee-based) connects callers to station lines; it was discussed by pilots in 2005 and 2007. — [Pilots of America (2005)](https://www.pilotsofamerica.com/community/threads/why-awoss-dont-make-it-to-metars.4288/); [Pilots of America (2007)](https://www.pilotsofamerica.com/community/threads/weather-over-phone.13957/)
- **Trader community, OMO bots** (updated 2026-02-15):
  - "Some ASOS stations allow access to near-real-time data via a dial-in phone system, traditionally used by pilots. Bots can automate calls to this system."
  - "Often, only one call can access the ASOS line at a time."
  - Traders are warned about limit orders "when the current temperature is near the day's high, especially in cities where OMO bots are known to be active."
  - The same page lists the competing scheduled triggers by city. DSM release times include KNYC 20:21/21:21/05:17Z, KMDW 21:17/22:17/06:17Z, KDEN 12:17/22:17/23:17/07:17Z and KLAX 22:08/01:08/08:08Z. 6-hour max METARs arrive at 23:51–23:54Z, 05:51–05:54Z, 11:51–11:54Z and 17:51–17:54Z. — [wethr.net market bots](https://wethr.net/edu/market-bots)
- **Open-source calling agent** (repo created 2026-07-11):
  - "US airports publish their ASOS readings on a public automated phone line… the fastest publicly available read of the exact sensor the market resolves on."
  - The agent "dials the target station's ASOS line… and transcribes the spoken temperature" via a user-provisioned Twilio/Telnyx number.
  - It is disabled by default, with "Scoped firing… inside snipe windows (the 20 to 35 minutes before a METAR publishes near a bucket edge)."
  - "Shared resource discipline. These lines exist for pilots… keep volume to a handful of short calls per day per city."
  - Budget: "$5 to $20/month." — [GitHub testedmedia/polymarket-weather-command-center](https://github.com/testedmedia/polymarket-weather-command-center)
- **GitHub code search** for "ASOS" + "twilio" + "kalshi" (run 2026-10-10) returned only that repository plus unrelated API-list READMEs. No other public calling-bot code was found. — [GitHub code search via API, query `"ASOS" twilio temperature kalshi`](https://github.com/search?q=%22ASOS%22+twilio+temperature+kalshi&type=code)
- **Demand driver, market size.**
  - Kalshi's climate and weather vertical has "grown 500 percent year over year" and is expected to "bring in $1.1 billion in trading volume this year." — [The Independent (2026-08-27)](https://www.independent.co.uk/news/world/americas/kalshi-weather-channel-betting-partnership-b3040492.html)
  - The vertical is "pacing toward $1.1 billion in annualized volume." — [The Weather Company (2026-08-27)](https://www.weathercompany.com/news/kalshi-and-twco-partner)
- **Demand driver, minute-level settlement.** Kalshi hourly temperature markets settle on a minute-resolution index built from one-minute ASOS data delivered through Synoptic, with a 300 s receipt deadline. This rewards minute-level reads at member stations throughout the day, not only near the daily max. — [CFTC filing ptc09092624308 (2026-09-09)](https://www.cftc.gov/filings/ptc/ptc09092624308.pdf); [Kalshi API, Get Weather Index](https://docs.kalshi.com/api-reference/live-data/get-weather-index.md)
- **Timing of daily-max events at settlement stations** (examples):
  - KNYC CLI MAX 84°F at 1:41 PM on 2026-07-13;
  - KDEN CLI MAX 95°F at 3:36 PM on 2026-08-07.
  - Both days had sub-second market sweeps later in the afternoon. — [PredictCast KNYC](https://wxmap.io/predictcast/blog/KNYC-416-whale-trade); [PredictCast KDEN](https://wxmap.io/predictcast/blog/KDEN-517-flash-crash)
- **KNYC is not an airport.** It "is located in the heart of Manhattan within Central Park." — [wethr.net KNYC guide](https://wethr.net/edu/market/newyork). It is described as an NWS climate station rather than an airport. — [METAR.ws](https://metar.ws/)
- **Mainstream 2026 coverage of weather-bet integrity is about sensor tampering, not phone lines.**
  - Météo-France filed a complaint over suspected "tampering of an automated data processing system" at Paris CDG (April 6 and 15, 2026 spikes).
  - Polymarket switched Paris to Le Bourget on April 19.
  - — [NPR/KNPR (2026-04-23)](https://knpr.org/npr/2026-04-23/french-police-probe-suspected-weather-device-tampering-after-odd-polymarket-bet); [AOL/Benzinga (2026-04-23)](https://www.aol.com/finance/trader-manipulates-city-weather-sensor-135804086.html); [WSJ (2026-04-23)](https://trk.wsj.com/click/45367545.389914/aHR0cHM6Ly93d3cud3NqLmNvbS9idXNpbmVzcy91bnVzdWFsLXdlYXRoZXItYmV0cy1vbi1wb2x5bWFya2V0LXNwdXItZnJlbmNoLWludmVzdGlnYXRpb24tYjc5OWJlYzg_bW9kPWRqZW1NYXJrZXRzQU0/69651b6a35d2bc3467bdc0c1B18dd4335)
- **Partnership coverage.** Gizmodo framed the Kalshi–TWC partnership as weather markets being "nearly impossible to insider trade," with no mention of phone lines. — [Gizmodo (2026-08-27)](https://gizmodo.com/kalshi-teams-up-with-the-weather-co-on-markets-that-are-nearly-impossible-to-insider-trade-2000803871)
- **Most public weather bots poll machine feeds** (METAR/NWS/Open-Meteo every 30 s to 10 min), not phones. Examples:
  - [fsevkli/ProjectKM](https://github.com/fsevkli/ProjectKM) (30 s signal loop on METAR for KNYC, KMDW, KMIA, KAUS, KLAX, KDEN, KPHL);
  - [alteregoeth-ai/weatherbot](https://github.com/alteregoeth-ai/weatherbot) (stops every 10 min, scan hourly);
  - [kaina404/polymarket-kalshi-weather-bot](https://github.com/kaina404/polymarket-kalshi-weather-bot) (every 5 min).

### Inferences
- **Busiest windows** (medium confidence; derived from the incentives and schedules above, not from line measurements):
  1. **Local afternoon near the daily max**, roughly 12:00–17:00 local in summer, when the running high is near a bucket edge. The OMO-bot warning is explicitly about "near the day's high."
  2. **Pre-METAR windows.** The only documented scheduling rule (testedmedia) fires 20–35 minutes before a METAR, i.e. roughly :16–:36 past the hour for :51–:56 METARs. This suggests mid-hour clustering for that tool, rather than top-of-hour.
  3. **Around 6-hour-max METARs** (:51Z at 00/06/12/18Z) and **DSM/CLI release times**, when traders want to front-run a scheduled product.
  4. **Hourly-index markets** spread demand across all daylight hours at index member stations.
  5. **Weather events** (fronts, storms) for pilot traffic.
- **Bot share of callers** (medium confidence; no direct measurement exists):
  - **KNYC (Central Park):** essentially all callers should be non-aviation (traders, hobbyists, curious public), because there is no airport.
  - **Large airline airports (KLAX, KDEN, KMIA, KPHL):** pilot use of the ASOS phone is probably small. Airline crews use ATIS/D-ATIS and datalink, and GA traffic is light. Peak-time busy signals there are therefore more plausibly trader-driven than pilot-driven.
  - **GA-heavy fields (KMDW, KAUS):** a larger pilot share is plausible.
  - Under the §2 model, one persistent automated caller suffices to make a line busy ~90% of the time. The observed peak busy pattern is consistent with a small number of automated callers per station, not dozens.
- **Media gap** (high confidence in the absence, as of 2026-10-10): no mainstream outlet has reported on bettors calling ASOS lines. The practice appears known within the trader community (wethr.net, open-source code, and the KLAX first-mover timing in the companion report) but has not drawn press or agency attention.

### Gaps
- Reddit and X could not be read directly. Searches returned no first-person post stating a call cadence or describing line contention between traders. Discord content is inaccessible.
- wethr.net's "City Resources Summary" listing which cities have active OMO bots was not retrieved. The station-level bot presence therefore remains unknown.
- No pilot complaint linking busy ASOS lines to bettors was found on pilot forums, AOPA, AVweb or FAA channels.

---

## 4. Official FAA/NWS rules, statements and policy about the phone lines, disconnect behaviour and congestion

### Takeaway
No FAA or NWS statement, notice, Service Change Notice, NOTAM policy, call limit, number removal, FOIA release, OIG/GAO report or congressional mention about bettors or automated callers tying up ASOS phone lines was found.

The governing texts all frame the line as an aviation service:
- the ASOS User's Guide ("FAA sponsored telephone dial-in access" for "the general aviation public");
- AIM 7-1-10 (numbers published in the Chart Supplement);
- FAA AC 150/5220-16E (AWOS: answer before the 2nd ring, join the audio in progress, disconnect after two complete transmissions, typically 5 simultaneous calls, minimum 1);
- FAA JO 7900.5E Appendix H (towered sites may voice the METAR or the OMO; unstaffed sites must voice the OMO; ASOS defaults to OMO after reboot).

The newest related FAA action is a Federal Register notice (2026-10-06) for a public Surface Weather Status Dashboard covering AWOS/ASOS outages and erroneous data. It says nothing about phone congestion.

### Cited Findings
- **Purpose and audience (NWS).**
  - Voice messages "are made available to the general aviation public through FAA sponsored telephone dial-in access. The information contained in the ground-to-air radio message and the telephone dial-in message are identical. ASOS computer-generated voice observations are spoken at the rate of 100 words per-minute."
  - "At unstaffed locations, the OMO is used; at FAA towered locations the OMO or METAR may be used at the discretion of the air traffic controller."
  - Voice messages "are also made available to the aviation community through telephone number provided for dial-in."
  - — [ASOS User's Guide (NWS, 1998), §6.5 and ch. 5](https://www.weather.gov/media/asos/aum-toc.pdf)
- **Pilot-facing rule (FAA AIM 7-1-10, Weather Observing Programs).**
  - AWOS "transmits a 20 to 30 second weather message updated each minute… Most AWOS sites also have a dial‐up capability so that the minute‐by‐minute weather messages can be accessed via telephone."
  - System information including "phone number" is "published… in the Chart Supplement."
  - ASOS/AWOS data outlets include "Computer‐generated voice (available through FAA radio broadcast to pilots, and dial‐in telephone line)." — [FAA AIM ch. 7 §1](https://www.faa.gov/air_traffic/publications/atpubs/aim_html/chap7_section_1.html)
- **Design rule for automated-weather phone answerers (non-federal AWOS)**, FAA AC 150/5220-16E (03/10/2017) ¶3.20.a(7):
  - "As an option, the voice system may contain an automatic telephone answering device that should permit user access to the voice message via the public telephone system."
  - "The incoming call should be answered prior to completion of the second ring, and the audio signal in progress at the time the call is received should be placed on line."
  - "The voice subsystem should automatically disconnect when the weather observation has been completely transmitted twice."
  - "Typically, the telephone-answering device should have the capability to answer five calls at a time… The minimum requirement is that the system answers a single call."
  - Maintenance check: "Telephone. Check to ensure it answers on second ring; is clear; provides two complete messages and disconnects." — [AC 150/5220-16E](https://www.faa.gov/documentLibrary/media/Advisory_Circular/AC_150_5220-16E.pdf)
- **Voice-outlet mode rules (FAA JO 7900.5E, 01/15/2020, with Change 1), Appendix H "Automated Weather System Operation and Broadcast":**
  - During hours of operation, facilities with ATIS and broadcast capability may set the system to broadcast "the Last Transmitted Observation (METAR/SPECI) or the One-Minute-Observation data (OMO) at the discretion of the Air Traffic Facility."
  - During hours of nonoperation they must "Ensure the one minute observation (OMO) data is broadcast on all automated weather system communications outlets."
  - "Unstaffed locations must always be set to broadcast the OMO data. NOTE: ASOS defaults to the One-Minute-Observation after a system reboot."
  - The procedure to switch is OID → CMD → VOICE → TYPE. — [FAA JO 7900.5E](https://www.faa.gov/documentLibrary/media/Order/JO_7900.5E_with_Change_1.pdf)
- **Telephone broadcast can go unavailable after corrections** (JO 7900.5E ¶3.7 NOTE): "When a COR is issued, if the ASOS/AWOS-C is set to broadcast the Last Transmitted Observation (LTO), the telephone broadcast will be unavailable until the next METAR/SPECI is issued. If… set to broadcast the One-Minute Observation (OMO), the telephone broadcast is not affected." — [FAA JO 7900.5E](https://www.faa.gov/documentLibrary/media/Order/JO_7900.5E_with_Change_1.pdf)
- **NOTAM rules cover outages, not congestion** (FAA JO 7930.2 ch. 5 §5):
  - "Accept NOTAM information on Automated Surface Observing System (ASOS) only from the NWS Weather Forecast Office."
  - Listed NOTAM conditions include system failure, missing elements, commissioning ("When commissioning an automated system that has a frequency/telephone number, include that information in the NOTAM"), and an inoperative broadcast frequency. — [FAA JO 7930.2, Services NOTAMs](https://www.faa.gov/air_traffic/publications/atpubs/notam_html/chap5_section_5.html)
- **Phone-line outages are tracked as a service element.**
  - The FAA WeatherCams station-status page shows NOTAMs such as "SVC AUTOMATED WX BCST SYSTEM VIS NOT AVBL DIAL PHONE LINE UNAVBL" (Clearwater Air Park, a non-federal AWOS, effective 2026-09-23).
  - Many federal ASOS sites show "Non-FAA Lines, Circuits, or Leased/Provisioned Services (LPS)" outages. — [FAA WeatherCams stations](https://weathercams.faa.gov/stations)
- **New FAA reporting channel** (Federal Register notice 2026-10-06):
  - A "congressionally mandated" Surface Weather Status Dashboard on the WeatherCams site where "Anyone may use the publicly available webform" to report AWOS/ASOS "outages and erroneous data."
  - Verified reports create trouble tickets in the Remote Monitoring and Logging System; status is displayed "within 30 minutes."
  - The FAA estimates ~1,825 reports a year; comments are due Nov 5, 2026. — [AVweb (2026-10-06)](https://avweb.com/aviation-news/faa-wants-pilots-to-flag-bad-awos-data/); [V-1X summary](https://v-1x.com/news/faa-developing-dashboard-for-pilot-reports-of-awos-data-problems-tz1ua4)
- **Maintenance and remote access use a separate port.**
  - "When an ASOS site malfunctions, the AOMC investigates by remote dial access to the site."
  - "If any change(s) occurs to any element of a site's 11 data files, the ASOS automatically dials the AOMC to upload the new configuration."
  - ASOS requests a time update every 60 days. — [NWSI 30-2111 (archived edition)](https://www.weather.gov/media/directives/030_pdfs_archived/pd03021011d.pdf)
  - The remote-user port is restricted to "Authorized remote users (with modem-equipped computers and the proper access code/password)." — [ASOS User's Guide](https://www.weather.gov/media/asos/aum-toc.pdf)
- **ATIS-side FAA orders.** The two ATIS sections reviewed contain no telephone-access provisions: FAA Order JO 7110.65 ch. 2 §9 (ATIS) and JO 7210.3 ch. 10 §4. — [JO 7110.65 ch. 2 §9](https://www.faa.gov/air_traffic/publications/atpubs/atc_html/chap2_section_9.html); [JO 7210.3 ch. 10 §4](https://www.faa.gov/air_traffic/publications/atpubs/foa_html/chap10_section_4.html)
- **Policy on equitable service** (relevant if anyone asks for privileged access): "NWS will not provide an environmental information service to one entity unless it can also be provided to other similar entities." — [NWSPD 1-10](https://www.weather.gov/media/directives/001_pdfs/pd00110curr.pdf)

### Inferences
- **No rule addresses automated callers** (high confidence that no public FAA/NWS statement exists as of 2026-10-10). Searches covered faa.gov, weather.gov, news and aviation press. The governing texts define the audience (general aviation) and the mechanism (short, auto-disconnected calls), but none sets a per-caller limit or mentions non-aviation or automated use.
  - The design intent, stated plainly in the AWOS AC and implied by the ASOS User's Guide, is a shared pilot service in which each call ends automatically so the next caller can get in.
- **Likely agency levers if congestion is noticed** (low-medium confidence; speculative, no precedent found): changing or unpublishing numbers, adding lines, or moving voice to IP under the ASOS 2.0 / "replace all copper voice and data lines" plan (see background file).
  - The new dashboard is for outages and bad data. Persistent busy signals at a station might nonetheless be reported through it by pilots as "service unavailable," which could draw attention to the practice.
- **JO 7900.5E Appendix H matters for traders at towered airports** (high confidence on the rule; site settings unknown). At KLAX, KDEN, KMIA, KPHL, KMDW and KAUS, the tower may set the phone to the last METAR/SPECI during tower hours, in which case the line carries no minute data. KNYC (unstaffed) must voice the OMO.

### Gaps
- No NWS Service Change Notice about ASOS telephone access was found. No FOIA response, OIG/GAO report or congressional mention of ASOS phone congestion was found either.
- The federal ASOS voice-line specification (S100 Site Technical Manual, Engineering Handbook 11) is not public. The ASOS-specific answer and disconnect rule is therefore inferred from the AWOS AC and observed behaviour.
- No newer edition than JO 7900.5E (with Change 1) was confirmed. A later change could exist.

---

## 5. Do the official rules plus single-line capacity fully explain the busy signals and the ~90 s cutoff? Alternative explanations

### Takeaway
Yes, to first order. The ~90 s cutoff matches the published automated-weather design: answer, join the audio in progress, play the observation twice completely, hang up. At 100 wpm, a 45–65 word message gives about 60–105 s depending on where in the loop the caller joins. Single-line Erlang/retrial behaviour, with a small number of persistent callers concentrated in market-sensitive windows, explains frequent busy signals at peaks.

Alternatives exist but are secondary. They mostly produce different signatures: busy all day, ring-no-answer, or the voice playing a METAR that does not advance.

### Cited Findings
- **Disconnect rule.** "Automatically disconnect when the weather observation has been completely transmitted twice"; "the audio signal in progress at the time the call is received should be placed on line." — [AC 150/5220-16E](https://www.faa.gov/documentLibrary/media/Advisory_Circular/AC_150_5220-16E.pdf)
- **Speech rate and message content.** ASOS speaks at 100 wpm. Each message starts with location, "AUTOMATED WEATHER OBSERVATION" and the UTC time, then prefixed elements ("temperature four dew point three"). — [ASOS User's Guide §6.5](https://www.weather.gov/media/asos/aum-toc.pdf)
- **Message length.** An AWOS message is "20 to 30 second[s]… updated each minute." — [FAA AIM 7-1-10](https://www.faa.gov/air_traffic/publications/atpubs/aim_html/chap7_section_1.html)
- **Repeat gap.** AWOS procurement specs output messages "continuously with approximately a 5 second delay." — [Illinois DOT AWOS spec](https://apps.dot.illinois.gov/eplan/desenv/042823/GR012-16A/GR012-16A.pdf)
- **ASOS 2.0 voice hardware.** The new design replaces "the voice and voice computer board" with "the audio card in the [new] computer and the new audio distribution amplifier." — [Hays et al., AMS 2017](https://ams.confex.com/ams/97Annual/webprogram/Manuscript/Paper315698/AMS%20Modernization%20of%20ASOS%20Hardware%20and%20Software%20Paper_FINAL.pdf)
- **Telephone broadcast unavailable** after a COR when in LTO mode (JO 7900.5E ¶3.7 NOTE). — [FAA JO 7900.5E](https://www.faa.gov/documentLibrary/media/Order/JO_7900.5E_with_Change_1.pdf)
- **Line and circuit outages** are common in FAA status data ("Non-FAA Lines, Circuits, or Leased/Provisioned Services"), and phone-line-specific NOTAMs exist. — [FAA WeatherCams stations](https://weathercams.faa.gov/stations)
- **Off-hook or seized-line faults** in ordinary telephony produce a constant busy signal until reset. Example: "Lines may become seized and be unavailable for use without indicators." — [Avaya support note](https://support.avaya.com/public/index?id=SOLN104584&page=content)

**Calculation (this note): holding time implied by the disconnect rule at 100 wpm, assuming a 5 s gap between repeats.**

| Words in message | One play | Two plays + gap | Mean if caller joins mid-message | Maximum |
|---|---|---|---|---|
| 45 | 27 s | 59 s | ~75 s | ~91 s |
| 55 | 33 s | 71 s | ~90 s | ~109 s |
| 65 | 39 s | 83 s | ~105 s | ~127 s |
| 75 | 45 s | 95 s | ~120 s | ~145 s |

A typical temperature-relevant OMO message runs about 50–65 words (ID, time, wind, visibility, sky, temperature, dew point, altimeter, remarks). That predicts roughly 70–105 s, consistent with the observed ~90 s.

### Inferences
- **The ~90 s cutoff is the two-transmission auto-disconnect** (high confidence). The AWOS standard, the AIM message length and the 100 wpm ASOS speech rate together give ~90 s for a typical message. Joining mid-loop explains call-to-call variation of ±15–20 s.
  - The cutoff is not a carrier or VoIP limit; standard VoIP platforms default to multi-hour limits.
  - It is the line-sharing mechanism and should be expected to stay.
- **The busy signals are mainly other callers on a single line** (medium-high confidence). Supporting evidence:
  1. single published number;
  2. community statements that "only one call can access the ASOS line";
  3. documented automated calling tools;
  4. the concentration of busy signals at market-sensitive times, which machine faults would not produce.
  - The Erlang/retrial maths shows one or two persistent automated callers suffice.
- **Alternative explanations to rule in or out** (each with signature and confidence):
  1. **Ringing occupancy.** The line is seized during the ~1–2 ring cycles before answer, so a short busy can occur even right after the previous call ends. Small effect. Confidence: high that it exists, low that it matters.
  2. **Line or circuit fault, or a voice board stuck off-hook.** Produces busy (or fast-busy, or ring-no-answer) continuously for hours or days, at all times of day, often alongside a NOTAM or an FAA status entry. Distinguishable by persistence. Confidence: medium that it happens occasionally; low that it explains peak-only busy.
  3. **Shared line with maintenance or data functions** (AOMC diagnostics, NCEI modem bank on an ~11-hour cycle, ASOS auto-dial to AOMC). The User's Guide describes a separate "remote user dial-in port," so these normally should not occupy the voice number. If a site did share, it would add a few short, irregular busy periods a day, not peak-concentrated ones. Confidence: low.
  4. **Voice outlet in LTO (METAR) mode at a towered airport after a COR.** "Telephone broadcast will be unavailable until the next METAR/SPECI". This presents as no answer or no message rather than busy, and does not affect OMO mode. Confidence: high that the rule exists; low relevance to busy signals.
  5. **Originating-side artefacts.** A VoIP provider may map carrier congestion or a terminating-carrier rejection to a "busy" status, and repeated short calls from one number could be treated as robocalling by carrier analytics. Would show up as "busy" even when another phone gets through. Speculative; no source found. Confidence: low.
  6. **More than one line or a hunt group at some sites** would reduce busy probability. The Erlang B formula with N > 1 applies (AC 150/5220-16E says "typically… five calls at a time" for AWOS). Not documented for these ASOS sites. Confidence: low that the seven stations have more than one line, given community reports.
- **Bottom line** (medium-high confidence):
  - Who gets the line is decided only by which call setup arrives first after the previous caller is disconnected. There is no queue, no priority for pilots, and no fairness mechanism.
  - Each caller's share of connections is roughly proportional to how often it attempts.
  - The two-play disconnect caps any single connection at ~90 s, so the line turns over about 38–40 times an hour.
  - At peaks, a few automated callers can take most of those turnovers.
  - That is an explanation of the observed behaviour, and it is also why the design (and pilots' access) degrades under automated load.

### Gaps
- The actual ASOS (not AWOS) answer and disconnect parameters, voice-port count and telco configuration for KNYC, KLAX, KMIA, KPHL, KMDW, KDEN and KAUS are not public.
- Whether the towered stations' voice outlets are set to OMO or LTO during tower hours (JO 7900.5E App. H) was not verified per site.
- No call-detail or busy-rate data exists publicly to confirm the bot-saturation inference; it rests on the model plus community evidence.

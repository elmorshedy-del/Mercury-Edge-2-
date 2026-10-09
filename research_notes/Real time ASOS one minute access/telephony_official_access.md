# ASOS Telephone Dial-In Capacity and Official/Authorized Access to ASOS One-Minute Data

Scope: facts on (1) how the legacy ASOS public voice dial-in works and what limits it, (2) what ASOS 2.0 and the copper-to-IP migration change, (3) official ways for a third party to get ASOS one-minute (OMO) data, (4) acceptable-use and policy constraints, and (5) who to contact. Research date 2026-10-09. The constraint holds throughout: nothing here is about defeating the auto-disconnect, occupying lines, or bypassing passwords.

---

## 1. Technical: how many simultaneous voice callers does an ASOS dial-in support, and what controls call duration/auto-disconnect?

### Takeaway
No public NWS/FAA document gives the number of simultaneous callers on the legacy ASOS voice dial-in. The ASOS User's Guide describes a single "dial-in telephone number provided at each ASOS location", which is FAA-sponsored and meant for the aviation public. Pilot reports describe single lines that return a busy tone while someone else is listening. The closest official design standard is FAA AC 150/5220-16E for non-federal AWOS: answer before the 2nd ring, disconnect after the observation has played completely twice, "typically" answer 5 calls at once, with a minimum of a single call. That AC does not govern federal ASOS.

### Cited Findings
- **Voice message content and rate.** ASOS computer-generated voice goes out on the ground-to-air (GTA) radio and through "FAA sponsored telephone dial-in access" for "the general aviation public." The GTA and telephone messages are identical. Voice is spoken at 100 words per minute. — [ASOS User's Guide (NWS, 1998), §6.5](https://www.weather.gov/media/asos/aum-toc.pdf)
- **OMO vs METAR, and timing.**
  - Unstaffed sites voice the current OMO. At FAA-towered sites, the controller chooses OMO or METAR. — [ASOS User's Guide §6.5](https://www.weather.gov/media/asos/aum-toc.pdf)
  - The telephone dial-in carries "Either OMO or last transmitted METAR/SPECI – Not both." — [ASOS User's Guide, Figure 4 "Availability of ASOS Data"](https://www.weather.gov/media/asos/aum-charts2.pdf)
  - Each message starts with the location, "AUTOMATED WEATHER OBSERVATION", and the UTC time of the observation. — [ASOS User's Guide §6.5](https://www.weather.gov/media/asos/aum-toc.pdf)
- **Wind and the once-a-minute update.**
  - Wind speed is a 2-minute average, recomputed every 5 seconds and reported once every minute in the OMO and in the voice messages. — [ASOS User's Guide §3.2](https://www.weather.gov/media/asos/aum-toc.pdf)
  - Wind direction in the GTA/telephone voice messages is relative to magnetic north. In METAR it is relative to true north. — [ASOS User's Guide](https://www.weather.gov/media/asos/aum-toc.pdf)
- **One number per site.** "Computer-generated voice messages are made available to local aviation users through ground-to-air broadcast and a dial-in telephone number provided at each ASOS location." — [ASOS User's Guide, Ch. 7](https://www.weather.gov/media/asos/aum-toc.pdf)
- **Line ownership.** The FAA orders the telco circuits for ASOS long-line communications, and NWS connects them to the ACU (historical 2004 implementation plan, Codex modems). This shows the FAA as the telecom sponsor, consistent with "FAA sponsored telephone dial-in access." — [ASOS Communications Transfer Implementation Plan (2004)](https://www.weather.gov/media/asos/ASOS%20Implementation/ACTIP031604new.pdf)
- **Legacy and ASOS 2.0 voice hardware.**
  - Legacy ACU: a VME rack with a "voice and voice computer board" and telephone modems.
  - ASOS 2.0: "the audio card in the [new] computer and the new audio distribution amplifier will replace the voice and voice computer board." The upgrade includes "the upgrade of the data and voice modems."
  - Neither source states the number of voice ports. — [Hays et al., AMS 2017, "Modernization of the ASOS Hardware and Software"](https://ams.confex.com/ams/97Annual/webprogram/Manuscript/Paper315698/AMS%20Modernization%20of%20ASOS%20Hardware%20and%20Software%20Paper_FINAL.pdf)
- **Campbell Scientific ASOS 2.0 parts.** The case study lists "AeroX Audio 105, SDM-SIO2R, CR1000X" as products used. The AeroX Audio 105 is the voice/audio module. — [Campbell Scientific case study PDF](https://s.campbellsci.com/documents/us/case-studies/united-states-asos-weather-network.pdf)
- **Analogous FAA standard (non-federal AWOS only, not ASOS).** "The incoming call should be answered prior to completion of the second ring… The voice subsystem should automatically disconnect when the weather observation has been completely transmitted twice. Typically, the telephone-answering device should have the capability to answer five calls at a time… The minimum requirement is that the system answers a single call." — [FAA AC 150/5220-16E, ¶3.20 voice subsystem](https://www.faa.gov/documentLibrary/media/Advisory_Circular/AC_150_5220-16E.pdf)
- **AWOS procurement specs repeat the 2-play disconnect.** For example: "The voice subsystem shall automatically disconnect when the weather observation has been completely transmitted twice." Messages are "output continuously with approximately a 5 second delay" between repeats. Hook-up to an assigned dial-up number "shall be provided by others." — [Illinois DOT AWOS bid spec](https://apps.dot.illinois.gov/eplan/desenv/042823/GR012-16A/GR012-16A.pdf)
- **Anecdotal, unverified.** A pilot forum answer to "Can AWOS take multiple calls at a time?" says: "Most of the ASOS/ATIS phone relays I've used are single lines. If someone else is listening, you just get a line busy tone." Seen only in a search-result snippet; the page itself could not be fetched. — [r/flying thread](https://www.reddit.com/r/flying/comments/1fmhdrn/can_awos_take_multiple_calls_at_a_time_or_am_i)
- **Third-party relays hit busy lines too.** A commercial patent for a relay service that dials AWOS/ASOS numbers on a pilot's behalf includes explicit "busy" handling with wait/retry loops and callbacks. It treats busy lines as a normal condition. — [US Patent 7,088,241 (Mackinac Software)](https://www.freepatentsonline.com/7088241.html)

### Inferences
- **Treat each ASOS public voice number as one line, one caller at a time, until a specific site says otherwise.** Evidence: one number per site, pilot reports of busy tones, and a single "voice board" in the legacy ACU. A bot holding the line shuts out pilots.
- **The ~2-loop (~90 s) auto-disconnect matches the FAA's stated design intent for automated weather phone lines.** For AWOS that intent is written down (AC 150/5220-16E): free the line for the next caller.
- **The ~90 s figure is consistent with the published speech rate.** At 100 wpm, a 60–75-word message lasts roughly 40–45 s; two plays plus about 5 s of gap is about 90 s.
- **The disconnect behavior is set inside the ACU voice software and hardware**, not by the phone company. No public parameter for it was found.

### Gaps
- No primary source gives the legacy ASOS voice port count, hunt/rollover groups, or the exact disconnect logic (number of loops, timer). The S100 ASOS Site Technical Manual (1,423 pp.) and the 1998 ASOS Software User's Manual (313 pp.) are cited in the AMS 2017 paper but are not public. NWS says Engineering Handbook #11 "is not available to the general public." — [ASOS FAQ](https://www.weather.gov/asos/FAQ.html)
- Per-site variation (some sites may have extra lines or rollover installed by the airport or FAA) could not be confirmed.
- Whether the AeroX Audio 105 supports multiple simultaneous phone callers is not documented in public sources found.

---

## 2. What happens to the public dial-in under ASOS 2.0 / copper-to-IP, and what is the deployment status for KNYC, KLAX, KMIA, KPHL, KMDW, KDEN, KAUS?

### Takeaway
The ASOS program's goal was to deploy ASOS 2.0 and "replace all copper voice and data lines with Internet Protocol communications" by end of CY2026, with "ubiquitous access to OMO" listed only as a goal. As of 2026, though:
- Campbell Scientific says the agencies are still in final acceptance testing.
- The ASOS 2.0 design paper says the first iteration keeps dial-up modems for external communications.
- No NWS document found says what happens to the public voice numbers (VoIP, more lines, new numbers, or retirement).

For the seven stations, NWS's equipment spreadsheet still shows legacy ACUs everywhere, and its "ASOS 2.0 In Service Dates" tab is empty. KMDW and KAUS are FAA-owned, so they could fall under the FAA's 207-site ASOS→AWOS-C transition (2025–2029) instead of ASOS 2.0. The site list could not be located.

### Cited Findings
- **ASOS PM's strategic goals (2023).**
  - "By end of 2026: Design, validate and deploy all ACU/DCP/SCA Replacements (aka ASOS 2.0) – Replace all copper voice and data lines with Internet Protocol communications."
  - ASOS 2.0 "Retains… METAR/SPECI/OMO, 5-Min, SHEF" and "Adds… IP communications – Ubiquitous access to OMO (goal)."
  - The project table lists a priority-1 "TDM to IP Upgrade" alongside the ACU/DCP replacement.
  - — [K. Boutin, ASOS PM, FPAW 2023 "Decadal Look at ASOS Lifecycle Upgrades"](https://fpaw.aero/sites/default/files/163/2-boutin-decadal-look-asos-lifecycle-upgrades.pdf)
- **Same timeline restated in March 2026** (NWS Nebraska). ASOS 2.0 "allows for an upgrade to modern IP communications… expanding the availability and periodicity of ASOS data." — [NWS ASOS 2.0 Update, Heartland Conference brief (2026-03)](https://engineering.uiowa.edu/sites/engineering.uiowa.edu/files/2026-03/HeartlandConferenceBrief.pdf)
- **Same FY26 goals in an NWS Southern Region briefing:** "Replace all copper voice & data lines w/IP comms." — [V. Murphy, NWS, "An Update on the ASOS Program"](https://www.weather.gov/media/lix/gcaws/Presentation1Murphy.pdf)
- **ASOS 2.0 design paper on external communications.**
  - "In this first iteration the expanded data will not be available to a wider audience due to the continued use of dial up modems for external communications."
  - Legacy modems "associated with the interfaces that are located on the site" are kept, because replacing them "would require the replacement of the modems on the other end of the line too."
  - — [Hays et al., AMS 2017](https://ams.confex.com/ams/97Annual/webprogram/Manuscript/Paper315698/AMS%20Modernization%20of%20ASOS%20Hardware%20and%20Software%20Paper_FINAL.pdf)
- **ASOS 2.0 data retention.** Legacy ASOS wiped raw sensor data every 12 hours. ASOS 2.0 keeps "all data… for that same 30 day timeframe" in SQLite. — [Hays et al., AMS 2017](https://ams.confex.com/ams/97Annual/webprogram/Manuscript/Paper315698/AMS%20Modernization%20of%20ASOS%20Hardware%20and%20Software%20Paper_FINAL.pdf)
- **Earlier (2009) sustainment paper.**
  - "Dial-in connections will not be required when ASOS is connected to an IP network."
  - "In order for OMO data to be made available to NOAA partners, the NWS and FAA must implement the technology refresh, revise its policies and procedures, and implement changes to the communications and data processing backbones."
  - — [AMS 2009 ASOS sustainment paper](https://ams.confex.com/ams/pdfpapers/145078.pdf)
- **Hardware delivered; acceptance testing ongoing (2026).**
  - Campbell delivered 1,529 units (700 ACUs, 799 DCPs, 50 SCAs) "by 2025," for up to 750 sites.
  - "At the time of this writing, the agencies are conducting their final acceptance testing… This case study will be updated following deployment." Web version dated 2026-01-12; PDF footer 04/23/2026.
  - — [Campbell Scientific case study (web)](https://www.campbellsci.com/resources/case-studies/us-asos-weather-network); [PDF](https://s.campbellsci.com/documents/us/case-studies/united-states-asos-weather-network.pdf)
- **NWS ASOS Current Events page is stale.** Its latest SLEP item (Aug 2023) says the project was entering System Acceptance Testing in fall 2023 and OT&E in spring 2024. There is no newer ASOS 2.0 deployment notice. — [weather.gov/asos Current Events](https://www.weather.gov/asos/CurrentEvents.html)
- **FAA ASOS→AWOS-C transition.**
  - "Why is the NWS and FAA transitioning 207 ASOS sites to AWOS-C? The FAA funding budgeted for this upgrade is insufficient to recondition all 570 FAA ASOS locations… The decision to transition to the AWOS-C in lieu of ASOS 2.0 was therefore a budgetary decision by the FAA."
  - Schedule: "start date of 2025 and lasts through 2029." "There are no NWS plans to transition ASOS to AWOS."
  - The FAQ's "complete list" link only points back to the equipment spreadsheet page.
  - — [NWS ASOS FAQ](https://www.weather.gov/asos/FAQ.html)
  - A Dec 2025 forum post confirms the list link only yields the all-sites spreadsheet. — [Weather Observers forum](https://wxobservers.freeforums.net/thread/1517/transitioning-asos-awos)
  - Commentary (Nov 2025) says AWOS-C lacks some ASOS climate capabilities. — [Balanced Wx (A. Gerard)](https://balancedweather.substack.com/p/another-federal-contract-cancelation)
- **Owners and status of the seven stations.** NWS spreadsheet "ASOS Sites by Equipment As Of 3_18_2025"; the page notes T/Td updated 13 Aug 2025. — [NWS ASOS Equip page](https://www.weather.gov/asos/asosequip.html); [spreadsheet](https://www.weather.gov/media/asos/ASOS%20Sites%20by%20Equipment%20As%20Of%203_18_2025.xlsx)

  | Site | WFO | Owner (EQ_OWNER) | Legacy ACU activation | OIDs / VDUs | HMP-155 T/Td install |
  |---|---|---|---|---|---|
  | KNYC (NEW YORK) | OKX | NWS | 1995-07-18 | 1 / 1 | 2025-01-28 |
  | KLAX (LOS ANGELES) | LOX | NWS | 1996-07-26 | 1 / 2 | not yet (1088/DTS-1) |
  | KMIA (MIAMI INTL) | MFL | NWS | 1995-07-14 | 2 / 1 | not yet (1088/DTS-1) |
  | KPHL (PHILADELPHIA) | PHI | NWS | 1995-03-27 | 2 / 4 | 2024-08-14 |
  | KMDW (CHICAGO MIDWAY (FAA)) | LOT | FAA | 1997-03-07 | 2 / 3 | 2025-06-11 |
  | KDEN (DENVER INTL AP) | BOU | NWS | 1993-09-03 | 1 / 1 | 2025-03-04 |
  | KAUS (BERGSTROM (FAA)) | EWX | FAA | 1997-05-13 | 1 / 3 | 2025-07-09 |

  - The "ASOS 2.0 In Service Dates" tab has a header row and no entries. — same spreadsheet.
- **Ownership split.** About 650 CONUS ASOS are FAA-owned and about 350 NWS-owned. AWOS-C is "FAA owned and maintained… Just like an ASOS. Have an OID." — [V. Murphy, NWS](https://www.weather.gov/media/lix/gcaws/Presentation1Murphy.pdf)
- **FAA AWOS-C contact:** "FAA AWOS PM: Mr. Steve Kim steve.kim@faa.gov." — [NWS ASOS FAQ](https://www.weather.gov/asos/FAQ.html)

### Inferences
- **Deployment timing.** As of the latest public data, none of the seven stations had a recorded ASOS 2.0 in-service date. With acceptance testing still under way in April 2026, field deployment at these sites in 2026 is uncertain, and the end-2026 "all copper → IP" goal looks likely to slip. That is an inference from the empty in-service tab and the Campbell statement.
- **NWS-owned sites (KNYC, KLAX, KMIA, KPHL, KDEN) are the natural ASOS 2.0 candidates.** KMDW and KAUS (FAA-owned) are exposed to the AWOS-C decision. If they move to AWOS-C, their one-minute output path, voice line, and phone numbers may change, and ASOS-style 1-minute archives (NCEI modem bank) may not carry over.
- **Short-term effect of ASOS 2.0 on the phone line.** Because ASOS 2.0's first iteration keeps dial-up modems externally and replaces the "voice board" with an audio card plus distribution amplifier, the public voice dial-in will probably keep working the same way (one published number, OMO/METAR voice, auto-disconnect) right after the ACU swap. Multi-caller or VoIP changes, if any, would arrive with the separate TDM-to-IP telecom project, timing unknown.
- **"Ubiquitous access to OMO (goal)" plus the FAQ's "proxy" plan (Section 3) are the official future replacement for phone scraping.** They should be watched rather than worked around.

### Gaps
- No NWS/FAA document found says whether public voice numbers will be kept, changed, moved to VoIP, or retired under copper-to-IP, or whether multiple simultaneous callers will be supported.
- The 207-site AWOS-C list was not located publicly; whether KMDW or KAUS is on it is unknown.
- No site-by-site ASOS 2.0 install schedule was found (no NWS Service Change Notice located).
- AeroX Audio 105 capabilities (phone ports, concurrency) were not found in public Campbell documentation.

---

## 3. Official mechanisms for third parties to get authorized access to ASOS one-minute data

### Takeaway
There is no public program that grants private parties credentials to the ASOS remote-user (modem) port. That port is password-protected for NWS/AOMC/technician use. NWS's own FAQ says: "Can I connect directly to an ASOS…? Currently this is not possible, however there are plans to make high-frequency ASOS data available through a proxy."

The authorized routes today are:
1. **MADIS "1-minute ASOS" feed**: from FAA WMSCR, unrestricted, account required, minutes of latency. Synoptic is a commercial precedent; it re-established an NWS/FAA connection in January 2026.
2. **NCEI one-minute archive**: DSI 6405/6406, collected by NCEI's modem bank on an 11-hour cycle under an NWS SLA. Too slow for trading.
3. **On-airport, non-interactive display hookup** (user-provided monitor showing OMO data), which the ASOS design allows. It requires a physical presence at the airport and agency coordination.

NOAA/NWS partnership policy requires equitable treatment ("will not provide an information service to one entity unless it can also be provided to other similar entities"). A bespoke, privileged real-time feed for one trading firm is therefore unlikely. Asking for a generally available service (the "proxy" or public OMO dissemination) is the policy-consistent request.

### Cited Findings
- **NWS official answer.** "Can I connect directly to an ASOS to get its data or weather observations? Currently this is not possible, however there are plans to make high-frequency ASOS data available through a proxy. When it is ready to debut into the production environment, it will be announced." — [NWS ASOS FAQ](https://www.weather.gov/asos/FAQ.html)
- **Remote-user port is password-gated.**
  - "Authorized remote users (with modem-equipped computers and the proper access code/password) may also acquire a wide variety of OID screen displays through the ASOS remote user dial-in port."
  - Remote users may sign on only as "Unsigned User," "Technician," or "System Manager."
  - — [ASOS User's Guide §6.1, Ch. 7](https://www.weather.gov/media/asos/aum-toc.pdf)
- **How NWS staff use the remote port.** Remote access is "mainly ProComm dialup… default access 'Unsigned User'." Passwords come from "your Regional ASOS System Mgr or ESA/ASOS Eltech," and "very few people outside of NWSH and the RHs can access an ASOS using the System Manager level." — [NWS ASOS OID training (J. Jones, 2012)](https://www.weather.gov/media/surface/ASOS_OID_final111612.pdf)
- **Remote-port security (software v3.10):**
  - Warning banner before the remote access code prompt.
  - Passwords encrypted; expire in 60 days.
  - "When anyone dials in to ASOS remotely and doesn't enter any response it will be counted as an attempt to deny service… If there are five or more attempts then a message will be logged in the Audit Log." Driven by NIST 800-53.
  - — [ASOS v3.10 Release Notes](https://www.weather.gov/media/asos/ASOS%20Implementation/release_notes_310_final.pdf)
- **High-resolution archive is for maintenance.** It "is available for review at the ASOS OID or to authorized remote users… primarily intended for maintenance troubleshooting purposes and should not be used as valid meteorological data without extensive evaluation." — [ASOS User's Guide §5.7](https://www.weather.gov/media/asos/aum-toc.pdf)
- **On-airport display hookup** (an official mechanism for on-site users):
  - "Other users, such as fixed base operators, may interface with the ASOS by providing their own off-the-shelf, non-interactive video monitors. Up to 50 such monitors can be interfaced with ASOS at a single airport. The data… is identical to the data displayed on the VDU."
  - The VDU "displays the most current OMO data, the last transmitted METAR, and auxiliary data… refreshed automatically once every minute."
  - "Remote monitor hook-up can be made available to airlines and other external users on the airport."
  - — [ASOS User's Guide §6.2, Ch. 7](https://www.weather.gov/media/asos/aum-toc.pdf)
- **Long-line OMO in the original design.** "Selected OMO data provided once every 5 or 15 minutes upon request" to NWS AFOS/AWIPS; the FAA got OMOs via ADAS. — [ASOS User's Guide, Figure 4 and network data-flow figures](https://www.weather.gov/media/asos/aum-charts2.pdf)
- **OMO historically not distributed beyond the FAA.** "The OMO is not transmitted long-line beyond the FAA communications network and FAA systems… many users have stated a need for the OMO data." — [AMS 2009 ASOS sustainment paper](https://ams.confex.com/ams/pdfpapers/145078.pdf)
- **MADIS 1-minute ASOS (official, public).**
  - Source: "operational feed (FAA Weather Message Switching Center Replacement System (WMSCR))". MADIS has processed all 1-minute observations since Nov 2017.
  - "Data arrive on a continuous, asynchronous schedule, and the current and previous hour's data are processed every 5 minutes." Available "with all communications methods supported by MADIS except for ldm."
  - Restrictions: "No restrictions. All observations are publicly accessible." OMO messages "do not conform to the METAR data standard."
  - — [MADIS 1-minute ASOS page](https://madis.ncep.noaa.gov/madis_OMO.shtml)
- **MADIS account process.**
  - Access requires a Data Application (lists "1-minute ASOS" as a dataset) sent to NCEP.List.MADIS_Support@noaa.gov.
  - "Data Applications received by COB Thursday (21:00 UTC) will be processed the following Monday."
  - Real-time access via FTP, OPeNDAP, or Text/XML; "users who require a continuous datafeed will get better performance by accessing the data via ftp or LDM."
  - — [MADIS Data Application](https://madis.ncep.noaa.gov/data_application.shtml); [MADIS restrictions](https://madis.ncep.noaa.gov/madis_restrictions.shtml)
- **Commercial precedent (Synoptic Data).**
  - Receives HF-ASOS/OMO via MADIS; full 1-minute stream since 2019.
  - "HF-ASOS data was unavailable from its source between October 2023 and January 2026. We have established a new connection with NWS and FAA which should provide reliable access to this dataset."
  - Latency "usually… between 2 and 5 minutes." Temperatures in whole °C. The feed is "experimental… brief to several-day outages are not uncommon."
  - — [Synoptic HF-ASOS docs](https://docs.synopticdata.com/services/high-frequency-asos)
- **NCEI modem bank (archive, not real-time).**
  - "ASOS 1-minute and 5-minute data along with ASOS System Log (SysLog) files collected via NCEI's dial-in modem bank. The system dials out on an 11-hour cycle to approximately 960 ASOS stations."
  - "We collect and archive these data largely at the request and funding of the NWS… There is an SLA with NWS."
  - "System Log files can only be made available to selected NWS personnel." System owner: Blake Lasher/Fengying Sun.
  - — [NCEI ATRAC record (2022)](https://www.ncei.noaa.gov/archive/atrac/export/2022-01-13T14-11-44.pdf?id=65639)
  - Public access: NCEI processes station data "within one day of the observations." Contact NCEI.Orders@noaa.gov, 828-271-4800. — [NCEI DSI-6405 documentation](https://www.ncei.noaa.gov/data/automated-surface-observing-system-one-minute-pg1/doc/asos-1min-pg1_documentation.pdf); [NCEI metadata](https://www.ncei.noaa.gov/access/metadata/landing-page/bin/iso?id=gov.noaa.ncdc%3AC00386)
- **NOAA equity principle.** "NOAA will be equitable in dealings with various classes of entities and will not show favoritism toward any particular entity within a class… NOAA will not provide an information service to one entity unless it can also be provided to other similar entities." NOAA commits to "open and unrestricted access to publicly-funded observations… in a timely manner." — [NAO 216-112 Partnership Policy](https://www.noaa.gov/organization/administration/nao-216-112-policy-on-partnerships-in-provision-of-environmental)
- **NWS Policy Directive 1-10:**
  - "NWS will not provide an environmental information service to one entity unless it can also be provided to other similar entities."
  - "NWS will strive to negotiate the least restrictive dissemination terms within any data sharing agreements (see NWSPD 1-12)."
  - When asked for services, "NWS will explain existing NWS services… and inform the requester that others in the… enterprise may be able to meet the requester's needs."
  - NWS gives "notice and opportunity for input" on new or changed significant services.
  - — [NWSPD 1-10](https://www.weather.gov/media/directives/001_pdfs/pd00110curr.pdf)
- **NOAA Open Data Dissemination (NODD)** puts NOAA datasets on AWS/GCP/Azure, free and without registration. Contact NODD@NOAA.GOV. (No evidence found that ASOS 1-minute data is currently on NODD.) — [NODD FAQ](https://prod-01-alb-www-noaa.woc.noaa.gov/big-data-project-frequently-asked-questions)
- **Historical context (1995):** "Currently, up-to-the-minute ASOS readings are available only by telephoning individual ASOS units or by listening to local ground-to-air…" — [National Academies, "Aviation Weather Services" (1995), App. E](https://www.nationalacademies.org/read/5037/chapter/14)

### Inferences
- **Remote-port credentials are not a realistic legitimate path for a private trading bot.** No program issues them, they are held by NWS staff and regional ASOS managers, and failed or blank logins are logged as denial-of-service attempts. Asking is legitimate, but an approval would conflict with the NWSPD 1-10 equity rule unless offered to everyone.
- **Fastest official one-minute path today is MADIS.** It runs at roughly 2–5 min latency (per Synoptic), with outages, and FAA-WMSCR-sourced coverage may not include every NWS-owned site. It does not reach "tens of seconds." The NWS "proxy" for high-frequency ASOS data is the official route that might, but it has no announced date.
- **On-airport monitor hookup could give near-real-time OMO legitimately**, since the VDU shows the current OMO, refreshed each minute. It needs physical installation at the airport, airport/FAA/NWS coordination, and possibly a lease; the right contact is the local WFO's ASOS focal point or electronics staff. Whether NWS/FAA would approve a non-aviation commercial user is unknown, and ASOS 2.0 may change these interfaces.
- **The policy-aligned request:**
  - ask NWS to publish OMO (whole-°C/°F, minute-by-minute) through MADIS/IDP/NODD at low latency for everyone, and to commit to the FAQ "proxy";
  - comment through NWS's Service Change Notice / NWSPD 1-10 consultation process when that service is proposed.

### Gaps
- No public precedent was found of NWS/FAA granting a private company, university, or media outlet direct real-time access to an ASOS remote-user port or a dedicated OMO line. Synoptic and IEM rely on MADIS and NCEI products, not direct ASOS access.
- No CRADA, MOU, or "NWS Partners" program specific to ASOS OMO was found. Whether a CRADA could fund an early OMO "proxy" pilot is unknown.
- No timeline was found for the FAQ's "proxy" for high-frequency ASOS data.
- Whether the MADIS 1-minute feed includes all seven target stations (especially the NWS-owned ones) and its current latency were not verified here. Another research stream may cover this.

---

## 4. FAA/NWS policy statements on automated or excessive calling of ASOS phone lines, and what counts as acceptable use

### Takeaway
No explicit published FAA or NWS policy on automated or excessive calling of the public ASOS voice line was found. The service is described as FAA-sponsored telephone access for the "general aviation public" and "local aviation users." The design (one published number; disconnect after the observation plays twice, per the FAA's AWOS standard) is meant to share a scarce line among pilots. For the password-protected remote-user port, ASOS software logs silent or no-response dial-ins as "attempt[s] to deny service" and shows a federal warning banner. Acceptable use therefore means single, short, infrequent calls that let the system hang up, back off on busy, and stay off the remote-user port.

### Cited Findings
- **Intended audience.** Voice dial-in is "made available to the general aviation public through FAA sponsored telephone dial-in access." — [ASOS User's Guide §6.5](https://www.weather.gov/media/asos/aum-toc.pdf)
- "…made available to local aviation users through ground-to-air broadcast and a dial-in telephone number provided at each ASOS location." — [ASOS User's Guide, Ch. 7](https://www.weather.gov/media/asos/aum-toc.pdf)
- **Pilots are pointed to published numbers.** The pilot guide says to "refer to… the FAA's Airport/Facility Directory… for ASOS broadcast frequency, dial-in telephone number." — [ASOS Guide for Pilots](https://wpaflys.info/aviation_academy_files/Handouts/Weather/asosbook.pdf)
- **Design intent of the auto-disconnect** (FAA standard for non-federal AWOS): disconnect "when the weather observation has been completely transmitted twice"; minimum capability "answers a single call." — [FAA AC 150/5220-16E](https://www.faa.gov/documentLibrary/media/Advisory_Circular/AC_150_5220-16E.pdf)
- **Remote-port audit rules** (applies to the modem port, not the public voice number):
  - "SECURITY RC – PROVIDE A SECURITY WARNING MESSAGE TO THOSE ACCESSING ASOS REMOTELY."
  - "When anyone dials in to ASOS remotely and doesn't enter any response it will be counted as an attempt to deny service."
  - — [ASOS v3.10 Release Notes](https://www.weather.gov/media/asos/ASOS%20Implementation/release_notes_310_final.pdf)
- **The modem port is shared with operational users.** AOMC and NWS technicians use remote dial access to diagnose faults, disable sensors, and clear faults ("the AOMC investigates by remote dial access to the site"). NCEI's modem bank dials ~960 sites on an 11-hour cycle. — [NWSI 30-2111 ASOS Maintenance (Jan 2025)](https://www.weather.gov/media/directives/030_pdfs/pd03021011curr.pdf); [NCEI ATRAC](https://www.ncei.noaa.gov/archive/atrac/export/2022-01-13T14-11-44.pdf?id=65639)
- **Third-party relays exist and treat busy lines as normal.** Examples: a patented commercial relay that dials AWOS/ASOS numbers for pilots with busy-retry logic; a former toll-free "anyawos" service that was "free to contact one ASOS/AWOS site per call." — [US Patent 7,088,241](https://www.freepatentsonline.com/7088241.html); [Stormtrack thread](https://stormtrack.org/threads/get-asos-awos-weather-observation-with-toll-free-number.5327)

### Inferences
- **Practical well-behaved-use rules** derived from the above:
  - at most one concurrent call per station;
  - never hold or extend a call, and let the ASOS disconnect;
  - on busy, back off with jitter and do not redial immediately;
  - cap calls per station per hour, especially around weather events and top-of-hour METAR times when pilots call most;
  - never dial the remote-user modem number;
  - prefer official data feeds (MADIS, the future proxy) for anything continuous.
- A bot that keeps a public line busy for long stretches works against the line's stated aviation-safety purpose. If noticed, it could prompt FAA/NWS action (for example, number changes). This is an inference; no enforcement precedent was found.
- Because calls to the remote-user port without credentials are logged as denial-of-service attempts, probing that port should be avoided entirely.

### Gaps
- No FAA order, AIM paragraph, NWS directive, or Chart Supplement note was found that explicitly addresses automated, high-frequency, or commercial calling of ASOS voice numbers.
- No published call-volume statistics or busy-rate data for ASOS lines was found.
- The legal status of commercial automated calling to these federal lines (e.g., telecom terms) was not researched and is out of scope.

---

## 5. Who to contact, and what to ask

### Takeaway
The main contact is the NWS ASOS Program Management Office (Office of Observations, Surface and Upper Air Division) at suad.asos.pmo@noaa.gov, about the high-frequency-data "proxy," ASOS 2.0/IP timing, and the future of the voice lines. MADIS Support handles the official 1-minute feed today. The FAA AWOS PM (Steve Kim) can say whether KMDW/KAUS are going to AWOS-C. NCEI handles the archive. AOMC is the operational trouble desk, not a data-access office.

### Cited Findings
- **ASOS Program Management Office:** suad.asos.pmo@noaa.gov. The National Program Manager's March 2025 memo also points to the ASOS website's "Public Form – ASOS Issue Report." — [weather.gov/asos Current Events](https://www.weather.gov/asos/CurrentEvents.html)
- **ASOS Program Manager (as of 2023):** Ken Boutin, NWS Office of Observations, Surface and Upper Air Division, 1325 East-West Hwy #4224, Silver Spring, MD 20910; office (301) 427-9777. — [FPAW 2023 presentation](https://fpaw.aero/sites/default/files/163/2-boutin-decadal-look-asos-lifecycle-upgrades.pdf)
- **AOMC** (24/7 operational monitoring and single point of contact for operational issues): aomc@noaa.gov, (800) 242-8194 or (800) 242-8895. — [ASOS FAQ](https://www.weather.gov/asos/FAQ.html); [ASOS Contact Us](https://www.weather.gov/asos/contactus.html)
- **FAA AWOS Program Manager (AWOS-C transition):** Steve Kim, steve.kim@faa.gov. — [ASOS FAQ](https://www.weather.gov/asos/FAQ.html)
- **MADIS Support (1-minute ASOS accounts, latency, coverage):** NCEP.List.MADIS_Support@noaa.gov. — [MADIS](https://madis.ncep.noaa.gov/); [Data Application](https://madis.ncep.noaa.gov/data_application.shtml)
- **NCEI (1-minute archive, DSI 6401/6405/6406):** NCEI.Orders@noaa.gov, 828-271-4800. The ATRAC record names Blake Lasher/Fengying Sun as system owners and Rich Baldwin as requester of the access modernization. — [NCEI DSI-6405 doc](https://www.ncei.noaa.gov/data/automated-surface-observing-system-one-minute-pg1/doc/asos-1min-pg1_documentation.pdf); [ATRAC](https://www.ncei.noaa.gov/archive/atrac/export/2022-01-13T14-11-44.pdf?id=65639)
- **NOAA Open Data Dissemination:** NODD@NOAA.GOV. — [NODD FAQ](https://prod-01-alb-www-noaa.woc.noaa.gov/big-data-project-frequently-asked-questions)
- **Local WFO responsibilities:**
  - WFOs that own the seven sites: OKX (KNYC), LOX (KLAX), MFL (KMIA), PHI (KPHL), LOT (KMDW), BOU (KDEN), EWX (KAUS). — [ASOS equipment spreadsheet](https://www.weather.gov/media/asos/ASOS%20Sites%20by%20Equipment%20As%20Of%203_18_2025.xlsx)
  - Regional ASOS specialists and ETs maintain the sites. — [NWSI 30-2111](https://www.weather.gov/media/directives/030_pdfs/pd03021011curr.pdf)
- **NWS consults the public before new or changed significant information services** (NWSPD 1-10; Service Change Notices under NWSI 10-1805). — [NWSPD 1-10](https://www.weather.gov/media/directives/001_pdfs/pd00110curr.pdf)

### Inferences — suggested questions
1. **ASOS PMO (suad.asos.pmo@noaa.gov):**
   - What is the status and timeline of the FAQ's "plans to make high-frequency ASOS data available through a proxy"?
   - Will it carry OMO every minute, and with what expected latency and access method (MADIS/IDP, NODD cloud, API)?
   - Will it cover KNYC, KLAX, KMIA, KPHL, KDEN (NWS-owned)?
   - When will ASOS 2.0 be in service at those five sites?
   - Under the "replace copper voice/data lines with IP" plan, will the public voice dial-in numbers be kept, changed, moved to VoIP, or retired, and will they support more than one simultaneous caller?
   - What call frequency on the public voice line does the program consider acceptable for non-aviation automated users?
2. **FAA AWOS PM (steve.kim@faa.gov):**
   - Are KMDW and KAUS among the 207 ASOS→AWOS-C transition sites, and when?
   - Will AWOS-C keep a public phone line and a one-minute data output (via WMSCR/MADIS)?
3. **MADIS Support:**
   - Current end-to-end latency for the 1-minute ASOS dataset, and which of the seven stations are included.
   - Recommended continuous-feed method (FTP vs Text/XML; LDM not offered for this dataset) and planned improvements.
   - Whether the January 2026 NWS/FAA reconnection (cited by Synoptic) is now operational.
4. **Local WFO / regional ASOS focal point:**
   - Whether a non-interactive, user-provided VDU-equivalent monitor hookup (the User's Guide allows up to 50 per airport) can be approved for a non-aviation commercial user, and what airport, FAA, and NWS approvals and costs apply. Ask also whether ASOS 2.0 keeps that interface.
5. **NCEI (NCEI.Orders@noaa.gov):**
   - Whether modernization of the 1-minute collection (beyond the 11-hour modem cycle) is planned once ASOS 2.0/IP is deployed.
6. **Framing for all of these:** ask for a generally available service rather than exclusive access. That is consistent with the NAO 216-112 / NWSPD 1-10 equity rule and more likely to get a substantive answer.

### Gaps
- Ken Boutin's role as ASOS PM in 2026 was not confirmed; the 2023 listing may be out of date.
- No named contact was found for the "high-frequency ASOS data via proxy" project.
- Phone and email contacts are taken from public NWS/FAA pages and presentations; they may change.

# Pilot/Aviation Apps, Datalink, AWOS Networks and Audio Relays: Who Exposes Live One-Minute ASOS/AWOS?

Scope: EFB/pilot apps, cockpit datalink (FIS-B, SiriusXM, Garmin Connext), AWOS vendor/network web portals, ASOS/AWOS/ATIS voice relays, and airport-ops products, plus how they source the data. Focus is US ASOS stations, especially KNYC, KLAX, KMIA, KPHL, KMDW, KDEN and KAUS. Notes are current as of 2026-10-09.

Bottom line across all questions: no mainstream pilot app or datalink found here shows the ASOS one-minute observation as data. They show METAR/SPECI, plus D-ATIS or transcribed ATIS in some apps. The "1-minute weather" pilots use is still the station's own voice output, heard over the VHF ground-to-air radio or the dial-up phone line. Apps add it only as phone numbers to tap, phone-bridge services (anyAWOS), or AI transcription of phone/radio audio (ATIS Relay, ForeFlight T-ATIS). The only machine-readable near-real-time one-minute ASOS feed found is the FAA WMSCR → NOAA MADIS "OMO/HF-ASOS" stream, which Synoptic resells. It has about 2–5 minutes of latency, carries an experimental status, and was down from Oct 2023 to Jan 2026. Live, seconds-latency one-minute web data exists only for non-federal AWOS sites on vendor clouds such as Mesotech AWOS Live, and none of those are the target ASOS stations.

---

## Q1. Do ForeFlight, Garmin Pilot, FltPlan Go, WingX, Avare, FlyQ, iFly, Aerovie, SkyVector, Windy, AeroWeather and similar apps show 1-minute ASOS/AWOS? If they offer "1-minute weather", do they dial the station or relay audio?

### Takeaway
No major EFB was found to display one-minute ASOS/AWOS data. ForeFlight said so explicitly in 2016. Its 2025–2026 releases add D-ATIS and AI-transcribed ATIS ("T-ATIS"), not one-minute ASOS. Where apps offer anything "1-minute", they surface the station's phone number or frequency (tap to dial) or transcribe ATIS/AWOS audio taken from phone lines. Third-party "AWOS by phone" services connect your call to the station's own voice line, and their latency is set by the phone call and the voice loop.

### Cited Findings
- **ForeFlight (explicit statement, 2016):** "At the moment, ForeFlight only provides the latest official observations that are disseminated in the form of a METAR or SPECI. In other words, we don't currently provide the 1-minute weather you'd get over the phone or on the radio broadcast." ForeFlight pulls observations "once each minute… directly from our interface with NOAA" and typically ingests a METAR 4–5 minutes after issuance. The blog also says ASOS SPECIs are throttled to 5-minute intervals, and that the hourly ASOS ob begins at :47:20 and is ready by :53:20. — [ForeFlight Blog, "Aging Surface Observations" (2016-11-10)](https://blog.foreflight.com/2016/11/10/aging-surface-observations/)
- **ForeFlight 18.1 (Feb 2026):** adds "Transcribed ATIS" (T-ATIS): "the latest ATIS at over 80 U.S. airports with AI-powered transcriptions, along with the original audio recording". It is included with the Premium and Performance plans. The same release moves D-ATIS (over 75 major US airports) to the Essential plan. The view also lists the ATIS frequency and phone number. — [ForeFlight 18.1 release notes](https://www.foreflight.com/releases/18-1)
- The ForeFlight release history through 18.8 (Oct 2026), including 18.3 (icing/turbulence layers), 18.5 and 18.6 (ClearNOTAMs, ChatGPT connector), shows no one-minute or high-frequency surface-observation feature in the headlines. — [ForeFlight Release History](https://ga.foreflight.com/releases); [ForeFlight 18.6](https://foreflight.com/releases/18-6)
- **Garmin Pilot (June 2026):** new features are a Daily Weather forecast tab, a turbulence layer and a Database Concierge UI. Its Weather tab lists "METARs, TAFs and MOS forecasts". No one-minute observations are mentioned. — [Garmin Newsroom (2026-06-16)](https://www.garmin.com/en-US/newsroom/press-release/aviation/garmin-adds-daily-weather-and-other-features-to-garmin-pilot-app/)
- **Phone numbers in apps:** ForeFlight shows ATIS and ASOS/AWOS phone numbers under Airports > Info > Weather & Advisory. Class B and larger Class C airports usually have separate ATIS and ASOS phone numbers, listed in the Chart Supplement and in ForeFlight, Garmin Pilot and Stratus Insight. One phone line takes one call at a time, so busy signals are common in bad weather. — [TxTop Aviation, "How to Get the Current Weather" (2020)](https://txtopaviation.com/how-to-get-the-current-weather/)
- **AeroWeather:** each airfield's Location tab has a communications section with the AWOS phone number, and the app can read a forecast aloud. It does not stream the AWOS itself. — [Pilots of America thread (Dec 2024)](https://www.pilotsofamerica.com/community/threads/does-anyone-know-of-a-livestream-audio-for-metars.149600/)
- **"Nearest Weather Station" (iOS/watchOS):** lists nearby ASOS/AWOS "from FAA sources" with frequency and phone number. Tapping the number "will initiate a phone call to allow you to hear the ASOS or AWOS report on the watch or connected phone." It uses FAA data as of each release. — [App Store listing](https://apps.apple.com/us/app/nearest-weather-station/id1576982599)
- **"Airports" app (iOS/Android):** has a button to call the ATIS telephone line (Europe and US). — [airportsapp.info](https://airportsapp.info/)
- **Reliability of phone numbers:** "we've found many of the phone numbers no longer work, particularly for the smaller airports." — [Pilot Institute (2023)](https://pilotinstitute.com/atis-vs-awos-vs-asos/)
- **anyAWOS (Mackinac Software), a phone-bridge service:**
  - Launched Feb 2004 as toll-free 877-269-2967 (877-any-AWOS). You key in a 3-letter ID and "will be connected to that airport's AWOS or ATIS", originally after a short ad. — [AVweb (2004-02-08)](https://avweb.com/briefs/need-awos-just-call-on-your-cellphone/)
  - Became subscription-only from Feb 6, 2006 at $5.95/month, after sponsorship failed and the FAA declined a DUAT-style subsidy. — [AVweb (2006-01-11)](https://avweb.com/briefs/awos-telephone-service-to-switch-to-pay-only/)
  - Current pricing page: $5.95/month or $65/year, with "Direct connection to the live AWOS", TAFs and 7-day forecasts, and busy-line wait/retry. — [anyAWOS Subscribe](https://www.anyawos.com/Subscribe.html); [How to use](https://www.anyawos.com/HowToUse.html)
  - Its FAQ attributes delay to dialing time and to "many AWOS systems pause after a complete report before starting the next report". A busy signal means the remote AWOS line is in use. — [anyAWOS FAQ](https://www.anyawos.com/SubscFAQ.html)
  - **Implementation (patent US7088241):** a central computer either plays a current digital observation if it has one, or looks up the AWOS phone number in a crowd-maintained database and "transfers the call, bridges the user's call to the AWOS call, or otherwise plays the current AWOS system generated voice to user". The patent groups AWOS, ASOS and ATIS together as "AWOS" systems. — [Patent US7088241 (FreePatentsOnline)](https://www.freepatentsonline.com/7088241.html)
- **AIM baseline (how the 1-minute voice product works):** AWOS "transmits a 20 to 30 second weather message updated each minute… Most AWOS sites also have a dial-up capability so that the minute-by-minute weather messages can be accessed via telephone." ASOS/AWOS "will provide continuous minute-by-minute observations." The VHF broadcast is engineered for 25 NM and 10,000 ft AGL. — [AIM 7-1-10 (faraim.org PDF)](https://faraim.org/faa/aim/chapter-7/section-7-1-10.pdf)
- **ASOS output configuration (important for ASOS at towered airports):** in the NWS ASOS User's Manual data-outlet chart, the telephone dial-in and ground-to-air radio voice carry "Either OMO or last transmitted METAR/SPECI – Not both". OMO on the computer long-line is "Selected OMO data provided once every 5 or 15 minutes upon request." ADAS (the FAA's AWOS/ASOS Data Acquisition System) and WMSCR are the FAA distribution path. — [NWS ASOS AUM charts (aum-charts2.pdf)](https://www.weather.gov/media/asos/aum-charts2.pdf)

### Inferences
- The "1-minute weather" features in apps are dialers (phone number plus tap-to-call) or transcribers of ATIS audio. None ingests the ASOS one-minute observation as structured data. Apps that pull from NOAA (aviationweather.gov / ADDS) or FIS-B are limited to METAR/SPECI, so typical age is up to about 65 minutes at ASOS stations, per ForeFlight's own description.
- At ASOS airports, the phone or radio voice may be set to read the last METAR/SPECI instead of the one-minute observation (per the AUM footnote). Any audio-based capture for KLAX, KMIA, KPHL, KMDW, KDEN or KAUS would need a per-station check of which mode the ASOS phone line uses.
- anyAWOS-style bridging gives seconds-level freshness, since it is the station's own voice. Its constraints are dialing and connect time, the 20–30 s message loop, single-line busy contention, and the need for speech-to-text before any automation.

### Gaps
- No primary-source feature pages were found for FltPlan Go, WingX, Avare, FlyQ, iFly, Aerovie, SkyVector or Windy showing one-minute data. Nothing indicates they do; their published weather is METAR/TAF from NOAA or FIS-B. This is a negative finding, not explicitly confirmed by each vendor.
- anyAWOS's current operational status is unclear: its homepage footer reads "© 2011 anyAWOS", while the subscription pages are still live. No API was found.
- The research did not confirm whether the ASOS phone lines at the target stations play the one-minute observation or the last METAR. KNYC (Central Park) is not an airport and no pilot-facing VHF broadcast was found; whether it has a public dial-in line was not verified here.

---

## Q2. Datalink: does the FIS-B "1 Minute AWOS" product exist, what does it cover, how often, and can a ground SDR receive it? Do SiriusXM Aviation, Garmin Connext and similar services carry any 1-minute ASOS?

### Takeaway
"1 Minute AWOS" appears in the AIM FIS-B table only as a non-basic, "expanded set" product: 1-minute update and 10-minute transmission interval. The FIS-B contractor (Harris, now L3Harris) told RTCA SC-206 in Dec 2016 that it would not implement it. Later product rollouts (2017–2018) do not include it, and no evidence was found that it is broadcast today. FIS-B METAR/SPECI goes out on a 5-minute transmission cycle, and the FAA describes METARs as "typically generated once an hour". SiriusXM rebroadcasts METARs every 12 minutes, and Garmin Connext delivers METAR/TAF on request every 5–10 minutes. None of these carry ASOS one-minute data. Ground SDR decoding of FIS-B is possible with hobby tools but only yields METAR/SPECI.

### Cited Findings
- **AIM FIS-B table:**
  - "1 Minute AWOS" has update interval "1 minute", transmission interval "10 minutes", Basic Product "No". Footnote 3: intervals for the "expanded set" "may be adjusted based on FAA and vendor agreement on the final product formats and performance requirements."
  - The same table lists METAR/SPECI with update interval "1 minute (where available), As Available otherwise", transmission interval 5 minutes, Basic Product Yes. D-ATIS (non-basic) has a 1-minute transmission interval.
  - Sources: [FAA AIM Ch. 7 §1](https://www.faa.gov/air_traffic/publications/atpubs/aim_html/chap7_section_1.html); [FAA AIM Ch. 4 §5 (4-5-9)](https://www.faa.gov/air_traffic/publications/atpubs/aim_html/chap4_section_5.html)
- **1-minute AWOS dropped by the contractor:** at RTCA SC-206 (Dec 2016), "The original plan was to update the MOPS with five new products that Harris was put under contract for. But Harris is not going to implement one of them, 1-minute AWOS." The remaining four were Lightning, Cloud Tops, Turbulence and Icing. — [RTCA SC-206 46th meeting summary (Dec 2016)](https://www.rtca.org/wp-content/uploads/2020/08/sc-206_dec_2016_summary.pdf)
- **Earlier plans:**
  - AOPA (Aug 2016): "The FAA is also studying uplinking one-minute automated weather observation station (AWOS) observations". — [AOPA (2016-08-10)](https://aopa.org/news-and-media/all-news/2016/august/10/fis-b-advisory-service-adding-data-curtailing-older-notams)
  - A 2013 CFI blog listed "1 minute AWOS" among the products FIS-B "may soon receive". — [jdpricecfi (2013)](https://jdpricecfi.wordpress.com/2013/07/01/ads-b-configuration-choices-2/)
- **2018 rollout:** AOPA's 2018 list of six new FIS-B products (CWA, cloud tops, G-AIRMET, icing, lightning, turbulence) has no AWOS product. — [AOPA Pilot (Aug 2018)](https://aopa.org/news-and-media/all-news/2018/august/pilot/ads-b-fis-b-new-features)
- **FAA's own METAR description:** the FAA ADS-B pilot page describes the FIS-B METAR product as "Reports are typically generated once an hour", with a 250–500 NM look-ahead. It also warns FIS-B "lacks sufficient resolution and updating capability necessary for tactical aerial maneuvering". — [FAA ADS-B In Pilot Applications](https://www.faa.gov/air_traffic/technology/adsb/pilot)
- **Data source:** a 2014 Exelis (FIS-B operator) presentation diagrams "WSI FIS-B Data Source" feeding the control stations. FIS-B products are therefore assembled from a weather vendor's feed, not from the ASOS stations directly. — [Exelis "FIS-B: Status & Future" (2014)](https://expydoc.com/doc/4267467/sbs-radios)
- **Receiver vendors:** METARs transmit every 5 minutes (citing AIM 7-1-11). — [Sporty's Stratus FAQ](https://www.sportys.com/stratusfaq)
- **Boldmethod:** "ADS-B updates text reports approximately every 5 minutes," while ASOS is "updated every minute… When you tune in to ASOS, you're getting the most up-to-date weather". — [Boldmethod](https://www.boldmethod.com/learn-to-fly/weather/asos-weather-ads-b-weather-difference/)
- **Ground SDR reception:** fisb-decode is "a back-end system for processing FIS-B… messages transmitted on 978 Mhz" that "roughly follows the DO-358B standard". Its repo topics include dump978, rtl-sdr and stratux. It carries a warning that it is "NOT intended for actual flight use… strictly a fun hobby program". — [rand-projects/fisb-decode (GitHub)](https://github.com/rand-projects/fisb-decode)
- **Ground-level reception limits:** "Ground tower signals, including weather (FIS-B), can not be received on the ground unless an ADS-B tower is located on the airfield. For most locations you need to be 2000-3000 feet in the air for reception." — [GRT Avionics Stratux Supplement](http://grtavionics.com/media/StratuxSupplement.pdf)
- **SiriusXM Aviation:** "Dynamic elements like radar and lightning are updated every 2.5 minutes… other more stable data elements could be updated every 60+ minutes." — [SiriusXM Aviation FAQ](https://listenercare.siriusxm.com/prweb/autoredirect/app/ExternalKM/help/SupportCenter/article/KC-2720/Aviation-and-ForeFlight-General-FAQs); [SiriusXM vs ADS-B](https://www.siriusxm.com/aviation/siriusxm-ads-b)
- **SiriusXM and FIS-B in Garmin G1000 NXi:** SiriusXM METARs broadcast every 12 minutes (90-minute expiration), and FIS-B METARs every 5 minutes. "METARs reflect hourly observations; non-routine updates include the code 'SPECI'." — [Garmin G1000 NXi Pilot's Guide §6–7 (hosted by dbq.edu)](https://www.dbq.edu/media/Academics/VPAcademicAffairs/AcademicDepartments/Aviation/G1000-NXi-Pilot's-Guide-Sections-6---7.pdf)
- **Garmin Connext (GSR 56 Iridium):** weather is "requested on demand", with updates every 10 minutes ($79.99/mo plan) or every 5 minutes ($174.99 and $249.95/mo plans). Products are METAR/TAF ("METARs are generally issued hourly. SPECIs… more frequently"). The source is a community wiki, so pricing may be dated. — [Phenom Pilots wiki](https://www.phenompilots.org/wiki/garmin-connext-satellite-services)

### Inferences
- In practice FIS-B gives METAR/SPECI only, at roughly 5-minute rebroadcast plus upstream vendor latency. A dump978/fisb-decode ground station near a target airport would not yield one-minute ASOS. The AIM wording "1 minute (where available)" for METAR is best read as source polling cadence, not one-minute observations; the FAA's own product description says METARs are hourly.
- None of the satellite datalinks (SiriusXM, Connext) offer one-minute surface observations.
- Spidertracks was named in the brief but no weather product evidence was found. It is primarily a flight tracking service, so this was not pursued.

### Gaps
- No post-2016 FAA or L3Harris statement explicitly says "1 Minute AWOS is not broadcast" was found. The conclusion rests on the 2016 RTCA minutes, the 2018 rollout list and the absence of any decoder or app support. DO-358B's product table (paywalled) was not reviewed.
- The exact meaning of "1 minute (where available)" for FIS-B METAR is not defined in the AIM.

---

## Q3. Do AWOS networks or vendor servers publish 1-minute data online, and do any cover or neighbor the target stations?

### Takeaway
Yes, but only for AWOS (mostly non-federal), not ASOS. Mesotech's AWOS Live cloud gives each customer airport a public https://[ICAO].awos.live page updated about every 5 seconds. SAI and Vaisala AviMet offer similar per-airport web displays. These are per-site vendor displays with "advisory only" disclaimers and no published API. The target stations are all NWS/FAA ASOS, so these networks do not cover them. Non-federal AWOS one-minute data otherwise reaches the public only as voice (radio/phone); WMSCR gets just a METAR every 20 minutes.

### Cited Findings
- **Mesotech AWOS Live:**
  - "Truly live data… up-to-the-second data"; "Your airport's URL is: https://[ICAO ID].awos.live"; a comparison table claims "DATA UPDATE FREQUENCY < 5 SECONDS" versus "5–15 minutes" for competing AWOS internet displays. — [Mesotech AWOS Live](https://mesotech.com/pages/awos-live)
  - Product page: "Updated every 5 seconds. No app required". The system also provides "VHF ground-to-air voice broadcast" and "Voice reports via telephone". — [Mesotech Airport Weather Advisor](https://mesotech.com/products/airport-weather-advisor)
  - Live example pages: KMQS, KART, KBRY and GACA, showing 5-sec/2-min/10-min wind tabs. Disclaimer: "The data displayed is for advisory purposes only and is not to be used for flight planning or operations." — [kmqs.awos.live](https://kmqs.awos.live/home); [kart.awos.live](https://kart.awos.live/home); [kbry.awos.live](https://kbry.awos.live/home); [gaca.awos.live](https://gaca.awos.live/home)
- **SAI AWOS online displays:** a 2014 forum post cites saiawos.com/onlinelist.php (e.g., 1B1 Columbia County, NY). Another poster notes "coverage is pretty sparse" and "there isn't a way to access that for an arbitrary airport". — [Pilots of America (2014)](https://www.pilotsofamerica.com/community/threads/can-awos-asos-data-be-accessed-online.70465/)
- **Vaisala AviMet Weather Display:** "delivers real-time and historical AWOS data to airport personnel… When the display is interfaced with an FAA commissioned AWOS or ASOS, it delivers certified weather information". It has a web feature "viewed from anywhere". — [Vaisala AviMet Weather Display datasheet](http://www.spinet.sk/datasheet/vaisala/avimet_wea_display_en.pdf)
- **anyAWOS as aggregator:** pitches to AWOS owners ("send your weather to the world"), noting "Many AWOS stations do not report their weather nationally". It hosts a map of "more than a thousand stations". — [anyAWOS home](https://anyawos.com/)
- **How non-federal AWOS data reaches the national system (NTSB docket, FAA/WMSCR answers):**
  - "Every non-Federal AWOS generates METARs 3 times an hour, which are forwarded… to WMSCR every twenty minutes, typically around minutes 17, 37 and 57". One provider handling 600+ sites spreads uploads at about 10 per minute.
  - "Verbal METAR messages containing the current one minute METAR information are available to the public directly from the site's AWOS via dial up phone lines and VHF broadcasts."
  - For Federal AWOS, data is available "as METARs issued once an hour, as SPECIs… and as one-minute observations available as voiced messages via dial up phone line or VHF radio".
  - WMSCR collects METARs from "some 1100+ non-Federal AWOS locations".
  - Source: [NTSB Docket DCA18MM028, Meteorology Attachment 7](https://data.ntsb.gov/Docket/Document/docBLOB?FileExtension=.PDF&FileName=8+-+Meteorology+-+Attachment+7+to+the+Factual+Report-Master.PDF&ID=40483158)
- **Same docket, on clocks:** AWI's CTO said that apart from the AWI AWOS 3000, non-federal AWOS lack GPS clock sync, and "Automated Surface Observing Systems are in the same boat". — [NTSB Docket DCA18MM028](https://data.ntsb.gov/Docket/Document/docBLOB?FileExtension=.PDF&FileName=8+-+Meteorology+-+Attachment+7+to+the+Factual+Report-Master.PDF&ID=40483158)
- **Synoptic:** "AWOS stations are not available for HF data." HF (one-minute) data exists only for ASOS. — [Synoptic HF-ASOS docs](https://docs.synopticdata.com/services/high-frequency-asos)

### Inferences
- Live sub-minute web data exists only at AWOS sites that bought a vendor cloud display. KLAX, KMIA, KPHL, KMDW, KDEN, KAUS and KNYC are ASOS (federal), so these portals cannot serve them. A non-federal AWOS near a target could serve as a proxy indicator only, and it is a different sensor and site.
- Scraping vendor pages such as awos.live would raise ToS and "advisory only" issues. No public API or licensing terms were found.

### Gaps
- No AWOS Live (or similar) site list was found for the metro areas of the targets (NYC, LA, Miami, Philadelphia, Chicago, Denver, Austin). It is unknown which nearby non-federal AWOS have public live pages.
- No state DOT AWOS network with a public one-minute feed was verified for 2025–2026 (e.g., the IEM notes historical Iowa AWOS one-minute data from 1995–2011 only — [IEM download](https://mesonet.agron.iastate.edu/request/download.phtml)).

---

## Q4. Does any service relay ASOS/AWOS/ATIS voice audio over the internet legally, with an API or commercial license? What is the latency?

### Takeaway
LiveATC carries some ATIS feeds at the target airports (KMDW, KDEN arrival, KLAX arrival) and a few ASOS/AWOS feeds elsewhere. Its terms forbid commercial use, automated retrieval and redistribution apps without a contract. ATIS Relay and ForeFlight T-ATIS dial ATIS phone lines (some are AWOS) and AI-transcribe them on demand in about 80 seconds, with no public API. At the large target airports the ATIS is the hourly or special ATIS (D-ATIS), not the ASOS one-minute observation. No licensed, API-accessible relay of ASOS one-minute audio for the target stations was found.

### Cited Findings
- **LiveATC feeds:** KMDW ATIS 132.750, KDEN ATIS (Arrival) 125.600 and KLAX ATIS (Arrival) 133.800 are listed as feeds, along with "KDTO ASOS/ATIS". — [LiveATC freq 132](https://www.liveatc.net/search/f.php?freq=132); [freq 125](https://www.liveatc.net/search/f.php?freq=125); [freq 133](https://www.liveatc.net/search/f.php?freq=133); [freq 119](https://www.liveatc.net/search/f.php?freq=119)
- LiveATC also hosts some AWOS feeds (e.g., KSOP AWOS 127.575, archived) and solicits volunteer feeders running a scanner/SDR, antenna and Raspberry Pi. — [LiveATC KSOP](https://www.liveatc.net/search/?icao=ksop); [LiveATC home](https://www.liveatc.net/)
- **LiveATC Terms of Use (key limits):**
  - "for non-commercial (personal) use only".
  - "You can't produce and distribute a dedicated desktop or mobile application designed to make the LiveATC.net Services directly available, without the consent of or a contract with LiveATC.net."
  - "not… for any aviation, commercial, operational… activity that relies on the availability, validity, or accuracy".
  - Access only "with an interactive web browser… and not with any program, collection agent, or 'robot'… unless you are granted permission".
  - Source: [LiveATC Terms of Use](https://www.liveatc.net/legal/)
- **Forum view:** a LiveATC feed host never considered anyone would want ASOS/AWOS streamed, "since you can accomplish that by just calling it on the phone", though LiveATC does archive such feeds. — [Pilots of America (Dec 2024)](https://www.pilotsofamerica.com/community/threads/does-anyone-know-of-a-livestream-audio-for-metars.149600/)
- **ATIS Relay:**
  - Covers "162+ US airports" by SMS (866-671-9172 / 833-648-2847) or iOS app. D-ATIS airports respond "within seconds". Phone-ATIS airports are "transcribed on-demand… approximately 80 seconds for dialing and transcription". It warns when ATIS disagrees with METAR, and recent transcripts include AWOS messages (e.g., "Montgomery Gibbs Executive Airport AWOS"). — [atisrelay.com](https://www.atisrelay.com/); [How to use](https://atisrelay.com/how_to); [Airports list](https://atisrelay.com/airports)
  - FAQ: "D-ATIS received through the internet or through this service is usually delayed 5-8 minutes"; ATIS "updated 53 minutes after the hour". — [ATIS Relay FAQ](https://www.atisrelay.com/faq)
  - Pricing: free tier; ATIS Relay Plus $5.99/month or $24.99/year. Disclaimer: "not an official FAA weather data source and is not intended for operational use." — [App Store](https://apps.apple.com/us/app/atis-relay/id6479165645)
  - Built by a solo developer (Torrey Systems LLC), "a passion project that doesn't even pay for itself". No API is advertised. — [ATIS Relay About](https://www.atisrelay.com/about)
- **ForeFlight T-ATIS:** AI transcription plus original audio at 80+ airports (Feb 2026, Premium/Performance plans). — [ForeFlight 18.1](https://www.foreflight.com/releases/18-1)
- **Other audio and transcription layers:** SkyListening says its streams are "Pulled directly from LiveATC.net mounts" with AI captions. — [SkyListening](https://skylistening.com/) AviATC offers ATC/ATIS listening with transcripts. — [AviATC](https://aviatc.net/) Talon "Radio Scanner Text Feeds" is an open-source real-time transcription of Broadcastify scanner audio. — [feeds.talonvoice.com](https://feeds.talonvoice.com/)
- **Wikipedia overview:** AWOS voice messages (radio, and optional phone) are "updated at least once per minute", and the FAA's ADAS "polls the systems remotely… disseminating them… in METAR format". — [Wikipedia: Automated airport weather station](https://en.wikipedia.org/wiki/Automated_airport_weather_station)

### Inferences
- The ATIS feeds at KLAX, KMDW and KDEN on LiveATC carry the ATIS weather, which is the hourly or special observation, not the minute-by-minute ASOS. They do not provide one-minute data. Separate ASOS VHF frequencies at large towered airports may be absent or unmonitored by LiveATC; that was not verified per station.
- A compliant automated one-minute audio path for a target ASOS would likely need either (a) a direct call to the station's ASOS dial-in line (public, but one line, contention-limited), or (b) your own VHF receiver within about 25 NM if the ASOS has a broadcast frequency. Both require speech-to-text and give about 1 minute of freshness plus the message loop time. LiveATC-based scraping is barred by its ToS without permission.
- ATIS Relay and T-ATIS show that on-demand phone-dial plus AI transcription is commercially viable (about 80 s end to end). Applied to an ASOS one-minute line, that would mean seconds to about 1.5 minutes of latency, versus 2–5 minutes for MADIS/Synoptic HF-ASOS (see Q5).

### Gaps
- No LiveATC listing was checked for KMIA, KPHL or KAUS, or for any dedicated ASOS (as opposed to ATIS) feed at the seven targets.
- No service offering a commercial license or API for ASOS one-minute audio was found. LiveATC commercial-contract terms are not public.
- No source here confirms whether ATIS Relay covers ASOS one-minute lines at the target airports; they are likely D-ATIS airports, which ATIS Relay serves from FAA D-ATIS.

---

## Q5. Do airline, FBO or airport-ops products (ACE-IDS/IDS, SAWS, Vaisala AviMet, etc.) or related feeds give third parties live ASOS one-minute data?

### Takeaway
No airport-ops product was found that offers third parties a licensed live ASOS one-minute feed. Products like Vaisala's AviMet display can interface with an ASOS on site, but they serve that airport's own staff and web display. The machine-accessible route for ASOS one-minute data runs from ASOS through FAA ADAS/WMSCR to NOAA MADIS ("OMO"/HF-ASOS), with MADIS and resellers such as Synoptic downstream. Synoptic reports 2–5 minutes of latency when the feed is up. The feed is labeled experimental and was down from Oct 2023 to Jan 2026. A 5-minute subset ("HF-METAR") runs about 5–15 minutes behind.

### Cited Findings
- **MADIS OMO feed:**
  - Since Oct 27, 2015 there is an "operational feed (FAA Weather Message Switching Center Replacement System (WMSCR)) to MADIS", and "MADIS started processing and handling all 1 minute observations in November 2017."
  - Data "arrive on a continuous, asynchronous schedule, and the current and previous hour's data are processed every 5 minutes"; it is available via all MADIS methods "except for ldm".
  - "Restrictions: No restrictions. All observations are publicly accessible."
  - OMOs "are binary messages that do not conform to the METAR data standard… should not be considered to be METAR observations." The page was last updated 15 March 2017.
  - Source: [MADIS 1-minute ASOS (OMO) page](https://madis.ncep.noaa.gov/madis_OMO.shtml)
- **Synoptic HF-ASOS:**
  - "HF-ASOS data was unavailable from its source between October 2023 and January 2026. We have established a new connection with NWS and FAA."
  - "Since 2019 Synoptic has received the full 1-minute data, as a low-latency provisional and real-time data stream from MADIS", exposed as station ID + "1M" (e.g., KSLC1M).
  - Latency "usually… between 2 and 5 minutes".
  - Experimental: "brief to several-day outages are not uncommon… We do not recommend developing applications solely based on the consumption of HF-ASOS data."
  - Precision: temperatures in whole °C; winds are 2-minute averages.
  - Coverage: "Most of the major commercial airports are ASOS, and do have the HF service."
  - Source: [Synoptic HF-ASOS docs](https://docs.synopticdata.com/services/high-frequency-asos)
- **Synoptic HFMETAR (5-minute subset):** "latency of 5-9 minutes or more… delivered in 5-minute batches". Formal METARs are available "within 3 minutes". The push streaming service cannot exclude HFMETAR as of June 2026. — [Synoptic ASOS/AWOS docs](https://docs.synopticdata.com/services/asos-awos-united-states-metar)
- **Start of 5-minute public release:** "The FAA started sending the data at 15Z on Tuesday, June 28[, 2016]… due to processing, the FAA delays the 5 minute reports by up to 10 minutes". On whether 1-minute obs would follow: "Due to bandwidth and processing, not in the foreseeable future." — [Weather Pulse / AllisonHouse blog (2016-07-02)](https://www.weatherpulse.com/blog/view/700/hourly-updates-how-about-every-5-minutes-instead)
- **Third-party 5-minute display:** the site says "The 5-minute feed reaches the public networks about 10–15 minutes after the observation; nothing public is faster" (sources: IEM, NWS API, MADIS). This is the site author's own claim and is contradicted for the one-minute stream by Synoptic's 2–5 minute figure. — [scorvec.com ASOS 5-minute page](https://scorvec.com/asos5.html)
- **Other HF-METAR resellers:** METAR.ws "metar.obs10" channel ("United States… updates every 5 minutes and is known locally as HF-METAR"). — [METAR.ws docs](https://docs.metar.ws/channels/frequent-observations) WindBorne ASOS API has an `include_high_frequency` flag for "high-frequency MADIS observations". — [WindBorne API docs](https://api.windbornesystems.com/forecasts/version_1/context/asos/)
- **Archive (not real time):** NCEI DSI-6405/6406 one-minute data for about 900 ASOS stations, in station-month files. — [NCEI DSI-6405 documentation](https://www.ncei.noaa.gov/data/automated-surface-observing-system-one-minute-pg1/doc/asos-1min-pg1_documentation.pdf) The IEM one-minute archive runs through 08 Oct 2026, i.e., about a 1-day lag as of today. — [IEM ASOS 1-min download](https://mesonet.agron.iastate.edu/request/asos/1min.phtml)
- **ASOS AUM chart:** OMO is available on the ASOS's own user/OID screens and the long-line outlet ("Selected OMO data provided once every 5 or 15 minutes upon request"), with ADAS/WMSCR as the FAA distribution path. — [NWS ASOS AUM charts](https://www.weather.gov/media/asos/aum-charts2.pdf)
- **Vaisala AviMet Weather Display:** can be "interfaced with an FAA commissioned AWOS or ASOS", with a web-viewable display. — [Vaisala datasheet](http://www.spinet.sk/datasheet/vaisala/avimet_wea_display_en.pdf)

### Inferences
- For the target ASOS stations, the lowest-latency machine-readable source found is MADIS OMO / Synoptic "K___1M" at about 2–5 minutes, when the experimental feed is up. The audio path (phone/VHF) is fresher, measured in seconds, but must be transcribed, and it may carry the last METAR rather than the one-minute observation depending on ASOS configuration.
- Airport-side displays (AviMet, ACE-IDS in towers) read the ASOS directly, but no program was found that resells or exposes those connections to third parties. Access would require an on-airport arrangement with the FAA/NWS or the airport operator.
- Because MADIS says "No restrictions", the MADIS/Synoptic path appears to be the only clearly authorized automated route for live one-minute ASOS. Its experimental status and the 2023–2026 outage are material reliability risks.

### Gaps
- No public documentation was found on third-party access to FAA ACE-IDS/IDS, SAWS or ASOS OID/long-line ports. These look like FAA-internal or site-restricted interfaces, but no policy document was located to confirm it.
- It was not verified whether all seven target stations (especially KNYC, which is ASOS but not an airport) currently report OMO/HF-ASOS into MADIS after the Jan 2026 restoration.
- Current end-to-end MADIS OMO latency (versus Synoptic's 2–5 minute figure) was not independently measured here.

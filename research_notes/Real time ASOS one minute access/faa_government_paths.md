# FAA-side (Government) Machine Distribution of ASOS One-Minute Observations (OMO) in Real Time

Research date: 2026-10-09. Scope: US only, FAA/NWS distribution channels, legitimate access paths only.

## Overall: Does any FAA/NWS channel deliver OMO to non-government users with latency under ~30 s?

### Takeaway
No. No FAA or NWS channel is documented to deliver ASOS OMOs to non-government users within ~30 s of the observation minute. The best candidate is the CSS-Wx "Surface Weather Observations - One Minute Observations (OMO)" JMS dataset. It is listed on the FAA Data Agreement Portal, but today it is reachable only through a NESG/VPN SWIM connection, which is restricted and takes months to set up. No FAA source publishes its latency. The free public cloud service (SCDS) does not carry CSS-Wx yet. The SWIFT Portal's own news item, dated 07/22/26, projects CSS-Wx joining SCDS in Q4 2026. Every government OMO product found reports temperature in whole °C.

### Cited Findings
- The FAA Data Agreement Portal's CSS-Wx Data Subscription lists the dataset "Surface Weather Observations - One Minute Observations (OMO) - Surface observations from AWOS/ASOS that are generated every minute." It sits alongside METAR/SPECI, TAF, PIREP and the other datasets, and each dataset has an "Acknowledgment Version 1.4" and a "Request Access" button. The service is described as JMS access through NEMS consumer queues, with non-gridded products in IWXXM, USWX or FAAWX XML. — [FAA Agreement Portal, CSS-Wx](https://aa.data.faa.gov/data/service.jsf?uuid=02422d2b-690f-42ba-9ce3-7a72f830f01c)
- The live SWIFT Portal shows a "Coming Soon to SCDS..." news item dated "07/22/26": "The SWIM Program Office has refined its projections for Common Support Services - Weather (CSS-Wx), which is expected to join the SCDS family of SWIM data products in Q4 2026." This text was retrieved 2026-10-09 from the portal's JavaScript bundle (`/assets/index.80a349d1.js`). — [SWIFT Portal](https://portal.swim.faa.gov/)
- The same portal bundle lists the SCDS subscription product catalog as STDDS, ITWS, TFMS, TBFM, TFDM, SFDPS and AIM FNS/NMS. CSS-Wx and OMO are absent. CSS-Wx appears only as Web Coverage/Feature/Map/Tile services in the discovery list, and as a status component. — [SWIFT Portal](https://portal.swim.faa.gov/)
- SCDS user documentation lists the selectable SWIM product types as "STDDS, ITWS, TFMS, TBFM, SFDPS, and AIM FNS". — [SWIFT Portal User Guide](https://support.swim.faa.gov/hc/en-us/article_attachments/21841227898516); [SCDS User Guide](https://files.swim.faa.gov/documents/user_guide.pdf)
- The ASOS itself makes OMO available at M+23 s: "OMO information is collected during the 60-second period ending at M+00 and made available to users each minute at M+23 (23 seconds past the current minute)." — [ASOS User's Guide (NWS)](https://www.weather.gov/media/asos/aum-toc.pdf)

### Inferences
- A sub-30 s government feed would require that the ADAS → WMSCR → CSS-Wx → NEMS/NESG chain add less than about 7 s beyond the ASOS's own M+23 s release. No document gives the CSS-Wx OMO latency, so this is unverified. It is plausible but unproven that CSS-Wx JMS is materially faster than MADIS (about 134 s; see below). The only way to know is to measure a live NESG subscription, or an SCDS subscription once CSS-Wx arrives there.
- Even a fast CSS-Wx feed would still carry whole-°C temperatures. It cannot provide better precision than the existing public 1-minute stream.

### Gaps
- No FAA document found states CSS-Wx OMO end-to-end latency, its publication cadence (per message or batched), or its SLA.
- It is unknown which CSS-Wx products will go on SCDS in Q4 2026. In particular, it is not known whether OMO will be included or will stay NESG-only.

---

## Is the CSS-Wx OMO product (or any OMO/1-minute ASOS product) available on SCDS / the SWIFT portal today?

### Takeaway
Not as of 2026-10-09. SCDS carries no CSS-Wx products. The FAA projects CSS-Wx joining SCDS in Q4 2026, having already slipped that projection: "refined its projections". It is not stated whether OMO will be among the products. Today OMO is obtainable from the FAA only as a CSS-Wx JMS subscription over a NESG (VPN or dedicated circuit) connection, approved through the Data Agreement Portal and SWIM on-ramping.

### Cited Findings
- SWIFT Portal news (07/22/26): CSS-Wx "is expected to join the SCDS family of SWIM data products in Q4 2026". — [SWIFT Portal](https://portal.swim.faa.gov/)
- SCDS products available today: STDDS, ITWS, TFMS, TBFM, TFDM, SFDPS and AIM. There is no CSS-Wx entry. — [SWIFT Portal](https://portal.swim.faa.gov/)
- FAA SWIM briefing to FPAW (Oct 2024): "A variety of Wx data products will be made available to Non-NAS Consumers via combination of Solace NESG interfaces and the SWIM Cloud Distribution Service (SCDS)". "Web Service-based Wx SWIM Services will NOT be made available to Non-NAS Consumers". "NEMS will support consumers at all NESGs • Via VPN over internet at Atlantic City and Oklahoma City • Via dedicated telco dropped to Atlanta and Salt Lake City". — [FPAW, Kratky, SWIM/CSS-Wx data availability](https://fpaw.aero/sites/default/files/197/1a5-kratky-fpaw-swim.pdf)
- In the same briefing, the CSS-Wx C-Node JMS Service is listed in NSRR with "Documentation to be uploaded". WSDDs exist for WCS/WFS/WMS (SE05 RevF). — [FPAW, Kratky](https://fpaw.aero/sites/default/files/197/1a5-kratky-fpaw-swim.pdf)
- SWIFT #15 (Aug 2021): "Working with SWIM to finalize CSS-Wx Producer on-ramping form – Publish information to SWIM, e.g., NWP, OMO". "CSS-Wx/NWP weather products are scheduled to be available on SWIM in 2024". Users outside the FAA "obtain products through Subscription Service – JMS destination is configured specifically for subscriber – Products distributed to subscriber as received". — [SWIFT #15 presentation](https://www.faa.gov/air_traffic/technology/swim/swift/2021-august-19-swift-15-meeting-presentation.pdf)
- SWIFT #15 Q&A: CSS-Wx data "will publish data to SWIM through the NAS Enterprise Security Gateway. Data will be made available to those user with access to SWIM via cloud as well." On METAR/TAF: "There are discussions on whether the FAA should provide that, or whether to direct community to NWS as the authoritative source". — [SWIFT #15 Q&A](https://www.faa.gov/media/19466)
- SWIFT support FAQ (2019): "Yes, SCDS will offer large weather products (e.g. NWP/CSS-WX out-of-band weather) as they become available on the NESG." — [SWIFT Portal Support](https://support.swim.faa.gov/hc/en-us/articles/360034503551-Will-large-weather-products-be-available-via-SCDS)
- CSS-Wx program status (FPAW, Oct 2024): "Recently reached Initial Operating Capability (IOC) milestone – Includes centralized processing at Atlanta and Salt Lake City"; "Data is onramped onto operational SWIM"; "Working toward In-Service Decision (ISD) milestone in first half of CY25". — [FPAW, Murphy, Intro to FAA NextGen Weather](https://fpaw.aero/sites/default/files/197/1a1-murphy-introduction-faa-nextgen-wx-systems.pdf)
- NAS EA Weather roadmap (v20) shows project G05C.01-06 CSS-Wx running from 2023 Q1 to 2025 Q4. — [NAS Infrastructure Roadmaps v20 – Weather](https://www.faa.gov/sites/faa.gov/files/NAS-Infrastructure-Roadmaps-v20-Weather.pdf)
- SCDS is "intended for non-National Airspace System (NAS), non-Operational use", and "All products provided by SCDS have been pre approved for public release by the NDRB". — [SWIM Users Forum, May 2022](https://www.faa.gov/sites/faa.gov/files/2022-12/2022-May-SWIM-Users-Forum-Briefing.pdf)

### Inferences
- The OMO dataset already has an acknowledgment form on aa.data.faa.gov, and CSS-Wx data was "onramped onto operational SWIM" by Oct 2024. That suggests OMO is live on NESG today. No source explicitly confirms external NESG consumers are receiving OMO now.
- The SCDS projection has already been "refined" (moved) at least once, so Q4 2026 should be treated as tentative.

### Gaps
- NSRR (nsrr.faa.gov) timed out from this environment, and it needs an account for documents. The CSS-Wx JMS WSDD/PDD for OMO, with message schema, JMS properties, cadence and filtering, was not retrieved.
- No 2025–2026 SWIFT meeting decks (SWIFT 23+) or SWIM Users Forum briefings mentioning CSS-Wx/OMO were found. The faa.gov SWIFT page lists materials only through the Nov 2024 Focus Group.
- It is unconfirmed whether CSS-Wx reached its ISD in 2025.

---

## What is the OMO message format, update rate, latency, station coverage, and temperature precision?

### Takeaway
Native ASOS OMO is a binary-encoded message, generated each minute and released by the ASOS at M+23 s. CSS-Wx translates it into IWXXM XML with FAAWX/IWXXM-US extensions (gml:name `csswxProducts.owl#OMO`), keeping the native units: temperature and dewpoint in whole °C. The public 1-minute stream (MADIS) receives records a median of about 134–139 s after the observation minute, measured on 2026-10-09. In that stream KLAX, KMIA, KPHL, KMDW, KDEN and KAUS are present, but KNYC (Central Park) is absent.

### Cited Findings
- FAA answer to NTSB (Mar 28, 2025, AVP-110): "The ASOS OMO is generated as a binary-encoded message. The ASOS OMO is then sent to the FAA ADAS ... and WMSCR ... in its native format. The ASOS OMO is then sent to the FAA CSS-Wx ... where it is translated into the IWXXM (XML) format for archiving and further distribution." It adds: "Most of the weather parameters are translated using the same units of measure from the ASOS OMO product (ambient and dewpoint temperature in degrees Celsius, wind speed in knots, ...)". Altimeter is converted from inHg to hPa, and SLP is shown to hundredths of hPa after conversion from tenths of inHg. — [NTSB DCA25MA108 Meteorology Attachment 1](https://data.ntsb.gov/Docket/Document/docBLOB?FileExtension=pdf&FileName=WX_DCA25MA108_Attachment_1_redacted-Rel.pdf&ID=18843279)
- The sample CSS-Wx OMO XML in that attachment contains `<gml:name>http://www.faa.gov/ontology/wx/1.0/csswxProducts.owl#OMO</gml:name>`, `<iwxxm:airTemperature uom="Cel">11.0</iwxxm:airTemperature>`, `<iwxxm:dewpointTemperature uom="Cel">-7.0</iwxxm:dewpointTemperature>`, `<iwxxm:qnh uom="hPa">1010.16</iwxxm:qnh>`, and `<faawx:OmoExtension>` with `<iwxxm-us:seaLevelPressure uom="hPa">1009.14</iwxxm-us:seaLevelPressure>`. Temperatures are whole °C rendered with ".0". — [NTSB DCA25MA108 Attachment 1](https://data.ntsb.gov/Docket/Document/docBLOB?FileExtension=pdf&FileName=WX_DCA25MA108_Attachment_1_redacted-Rel.pdf&ID=18843279)
- "The FAA OMO data comes from CSS-Wx which is located at FAA facilities in Atlanta and Salt Lake City." The NTSB-provided file "came from the data archived by CSS-Wx". An updated FAA AJM-331 deck, "ASOS and AWOS-C Reporting and Archiving (3-17-2025).pptx", describes distribution and translation. — [NTSB DCA25MA108 Attachment 1](https://data.ntsb.gov/Docket/Document/docBLOB?FileExtension=pdf&FileName=WX_DCA25MA108_Attachment_1_redacted-Rel.pdf&ID=18843279)
- ASOS User's Guide: the OMO "includes all basic weather parameters found in the body of the METAR plus selected automated remarks", is "made available to users each minute at M+23", and "is generally not transmitted long-line beyond the local FAA or NWS communications network node". — [ASOS User's Guide](https://www.weather.gov/media/asos/aum-toc.pdf)
- MADIS: "1-minute ASOS, also known as One Minute Observations (OMO), are binary messages that do not conform to the METAR data standard (FMH1)". The feed comes from "FAA Weather Message Switching Center Replacement System (WMSCR)" (operational to MADIS since Oct 27, 2015; all 1-minute obs processed since Nov 2017). Coverage is CONUS, with "No restrictions. All observations are publicly accessible." — [MADIS 1-minute ASOS](https://madis.ncep.noaa.gov/madis_OMO.shtml)
- Synoptic: "Temperatures are expressed in whole degrees celsius"; "Wind speeds are a 2 minute average"; AWOS stations are not available for HF data. — [Synoptic HF-ASOS docs](https://docs.synopticdata.com/services/high-frequency-asos)
- Researcher's own measurement, MADIS public file `20261009_1900.gz`: 11,836 records from 1,013 stations. Public HTTPS files contain only the 5-minute-stamped records (minutes 00, 05, ... 55). All temperatures are integer °C stored as K + 0.15. `receivedTime − observationTime` had p5 133 s, median 135 s, p75 139 s, p95 433 s. The 0600Z file (11,977 records) had median 139 s, p95 140 s. — [MADIS public hfmetar netCDF directory](https://madis-data.ncep.noaa.gov/madisPublic1/data/LDAD/hfmetar/netCDF/)
- Researcher's own check of station coverage in those two hours: KLAX, KMIA, KPHL, KMDW, KDEN and KAUS were present (12 records per hour each), as were KJFK, KLGA, KEWR, KTEB, KHPN, KISP, KFRG and KDCA. KNYC was absent in both hours. — [MADIS public hfmetar netCDF directory](https://madis-data.ncep.noaa.gov/madisPublic1/data/LDAD/hfmetar/netCDF/)
- NCEI's separate, non-real-time 1-minute archive (DSI-6405) does include KNYC; KNYC is the doc's own filename example. It covers about 900 ASOS stations. — [NCEI DSI-6405 documentation](https://www.ncei.noaa.gov/data/automated-surface-observing-system-one-minute-pg1/doc/asos-1min-pg1_documentation.pdf)
- Synoptic latency claims conflict. The HF-ASOS page says it "usually arrives with between 2 and 5 minutes latency". The ASOS/AWOS page (June 2026) says the 5-minute HFMETAR component "has latency of 5-9 minutes or more" and is "delivered in 5-minute batches". — [Synoptic HF-ASOS](https://docs.synopticdata.com/services/high-frequency-asos); [Synoptic ASOS/AWOS](https://docs.synopticdata.com/services/asos-awos-united-states-metar)

### Inferences
- The MADIS receipt delay is tightly clustered at about 133–139 s. That suggests a scheduled or batched relay somewhere between ADAS and MADIS rather than random network delay. About 110 s accrues after the ASOS's M+23 s release, and no source says which hop adds it (ADAS poll, WMSCR, CSS-Wx, NWSTG/MADIS).
- KNYC's absence from the MADIS 1-minute feed suggests that Central Park (an NWS-owned, non-airport ASOS) may not send OMOs over the FAA ADAS/WMSCR long-line path. If so, the CSS-Wx OMO product, which is fed from ADAS/WMSCR, would likely lack KNYC as well. This is not verified.
- Whole-°C precision is set by the native binary OMO encoding, so it applies to every government OMO channel: CSS-Wx, MADIS and Synoptic.

### Gaps
- No official CSS-Wx OMO station list was found, so whether CSS-Wx carries KNYC is unconfirmed. Confirming it would require the NSRR CSS-Wx JMS documentation or a sample subscription.
- The AJM-331 "ASOS and AWOS-C Reporting and Archiving (3-17-2025)" deck is referenced but not public.
- KNYC absence was checked in only two hourly files (2026-10-09 0600Z and 1900Z). A multi-day check is advisable.

---

## What are the cost and process for NESG access for a small private company?

### Takeaway
SWIM data itself is free. The consumer pays for its own interface development and for connectivity: a site-to-site VPN over the internet to the Atlantic City or Oklahoma City NESG, or a dedicated circuit to Atlanta or Salt Lake City. On-ramping runs through Data-To-Industry@faa.gov, the aa.data.faa.gov agreements, an On-Ramp Form and qualification testing. It takes about 3–4 months for operational access (FPAW) or 2–6 months (FAA Q&A). NESG connections are "reserved for industry partners that require operational data usage (e.g., airlines, vendors, etc.)", so a non-aviation commercial user's eligibility is at FAA discretion. A sponsor and an FAA contract are needed only for sensitive data.

### Cited Findings
- FAA SWIM Q&A: "Currently there is no cost for data. Costs to develop a SWIM interface are the responsibility of the party interested in consuming the data." On-ramping time: "Typical timeframes range from 2-6 months, depending on the time required for the Consumer to develop a mature interface to SWIM, and for the Consumer to get approval for data consumption from the NAS Data Release Group." — [FAA SWIM Questions & Answers](https://www.faa.gov/air_traffic/technology/swim/questions_answers)
- FPAW SWIM briefing:
  - "NESG SWIM connections are reserved for industry partners that require operational data usage (e.g., airlines, vendors, etc.) • Users who have valid use case for sensitive flight or Collaborative Decision Making (CDM) data • Data otherwise not publicly available"
  - "SCDS is for non-operational use of SWIM data (e.g., developers, data scientists, etc.)"
  - The listed steps are: contact Data-To-Industry@faa.gov; complete agreements at aa.data.faa.gov; establish a VPN connection in the desired environment (R&D, virtual FNTB, FNTB, OPS); create a Consumer On-Ramp Form; and schedule qualification testing.
  - Timeframes: "FNTB 3wks – month (L7 conn doc and VPN connection) • OPS – 3-4 months as a consumer • Note these timeframes are dependent on engineer availability and backlog of pending orders".
  - — [FPAW, Kratky](https://fpaw.aero/sites/default/files/197/1a5-kratky-fpaw-swim.pdf)
- The same briefing describes the operational process: "Once approve, order is sent to the vendor for prioritization/implementation. The service must be ordered before any work can begin by the vendor • Once ordered, SWIM will work with consumers to configure network requirements (VPN to the OPS NESG /IP Supplemental form updates/coordinating with FTI Security to enable the VPN)". — [FPAW, Kratky](https://fpaw.aero/sites/default/files/197/1a5-kratky-fpaw-swim.pdf)
- Sensitive data: "Non-Government, non-FAA Entities ... The requesting user must have an active contract with the FAA ... the requesting user, FAA Sponsor, and NAS Data Release Board (NDRB) enter a legal agreement". — [FPAW, Kratky](https://fpaw.aero/sites/default/files/197/1a5-kratky-fpaw-swim.pdf)
- SWIM PMO process: "Consumers email connection request to common mailbox [Data-to-Industry@faa.gov] to enter into the SWIM consumer on-ramping process • Assigned a POC". The steps include "R&D implementation and testing • FNTB implementation and verification • OPS implementation, orders, and cutover • Hand-off to NEMC". — [FAA ATIEC SWIM PMO briefing](https://www.faa.gov/sites/faa.gov/files/air_traffic/technology/swim/news/ATIEC-SWIM-PMO.pdf)
- FAA "Getting Access to SWIM": services not supported by the SWIFT Portal must be requested at Data-To-Industry@faa.gov, and "Your request will be reviewed in accordance with FAA policy." — [FAA Get Connected](https://www.faa.gov/air_traffic/technology/swim/products/get_connected)
- The Data Agreement Portal's contact address is AJRDDataRequests@faa.gov. Its Terms of Service say: "If you wish to redistribute any information gained through this Service, you may not characterize it as FAA data." The FAA "may suspend or stop providing our Services ... without any prior notification", and "We make no representations or warranties ... about the suitability, reliability, availability, timeliness". — [FAA Agreement Portal](https://aa.data.faa.gov/data/service.jsf?uuid=02422d2b-690f-42ba-9ce3-7a72f830f01c)
- If OMO later reaches SCDS, the SCDS rules are: free of charge ("This allows the FAA to continue to provide SWIM data service free of charge"), JMS with mandatory compression, a 200 GB/day or 2 TB/month high-volume threshold, no duplicate subscriptions, and use that is not NAS-impacting. Subscriptions require the user to sign a Service Access Agreement and are auto-approved. — [SCDS General Guideline v1.1 (Sep 2024)](https://www.faa.gov/sites/faa.gov/files/air_traffic/technology/swim/governance/SCDS-Guideline-Document_v1.1_09.11.2024); [SWIM Users Forum Sep 2023](https://www.faa.gov/sites/faa.gov/files/2023-09/2023-September-SWIM-Users-Forum-Briefing.pdf)
- SWIFT on-boarding (Jan 2024): create an FAA Data Access Account at aa.data.faa.gov and a portal account (same email); "Subscription requests are reviewed, approved within 72 hours". — [SWIFT Portal On-boarding Instructions](https://support.swim.faa.gov/hc/en-us/article_attachments/360096864051)

### Inferences
- Every CSS-Wx dataset on aa.data.faa.gov, OMO included, carries the same standard "Acknowledgment Version 1.4". That suggests OMO is not classed as sensitive, so no FAA sponsor or contract should be needed. The gating factor would instead be the "operational data usage" NESG eligibility policy and SWIM engineering backlog.
- For a small non-aviation firm, the realistic FAA path is to wait for CSS-Wx on SCDS (free, self-service, but non-operational use only). A NESG request would need to argue that the data is "otherwise not publicly available". That argument holds until SCDS carries it, but approval is discretionary.

### Gaps
- No dollar figures were found for NESG VPN or dedicated-circuit connectivity (FTI/NBPS/L3Harris circuit pricing), or for any FAA-imposed fee. The FAA states only that data is free and that interface costs fall on the consumer.
- No document explicitly says whether a non-aviation commercial entity (e.g., a trading or analytics firm) is eligible for a NESG connection. The only statement is the "reserved for industry partners that require operational data usage" wording.

---

## Are there other FAA systems that redistribute OMO/1-minute data to external parties (ADAS, WMSCR/NADIN, WARP, ITWS, etc.)? Any documented latency?

### Takeaway
Internally, ADAS (hosted at ARTCCs) polls each ASOS every minute and feeds minute-by-minute observations to WARP and ITWS, and OMOs flow through WMSCR to CSS-Wx and to NOAA/MADIS. No external, commercial redistribution of OMO from ADAS, WMSCR/NADIN, WARP or ITWS was found. WARP is being retired in favor of CSS-Wx, and CSS-Wx is planned to subsume WMSCR/ADAS functions. No hop-level latency figures were found.

### Cited Findings
- MITRE (2005): "Each ADAS also maintains interfaces to Weather Message Switching Center Replacement (WMSCR) to provide hourly AWOS/ASOS data, and interfaces to the local ARTCC Weather and Radar Processor (WARP) and up to 6 Integrated Terminal Weather System (ITWS) Product Generator (PG) sites, to provide minute-by-minute observations." The ADAS link uses the NADIN II packet-switched network with ISO TP4. "ADAS requests data from the ASOS every minute and every hour" (HDLC-NRM, ASOS interface at 2.4 kbps). — [MITRE, Potential IP Solutions for Networking Selected FAA Weather Systems](https://www.mitre.org/sites/default/files/pdf/05_0468.pdf)
- NWS TIN 05-29 (2005): moving 40 FAA Service Level A/B ASOSes from AWIPS to ADAS "also supports FAA Integrated Weather Information System /ITWS/ acquisition of ASOS one-minute observations". — [NWS TIN 05-29](https://www.weather.gov/media/notification/tins/tin05-29asos_transfer.pdf)
- NWS (2023): "FAA is responsible for all ASOS comms via the ASOS/AWOS Data Acquisition System (ADAS)". — [NWS, Murphy, ASOS Program Update (Feb 2023)](https://www.weather.gov/media/lix/gcaws/Presentation1Murphy.pdf)
- FAA architecture: surface stations' data "are received by CSS-Wx via the Weather Messaging Switching Center Replacement and the AWOS Data Acquisition System"; "SWIM will also provide digital NWP products to AWD external web and to other external aviation users, such as Flight Services and airlines via the NESG." — [FAA NextGen Weather Architecture](https://www.faa.gov/nextgen/programs/weather/architecture)
- NextGen Weather Work Package 2: "Four legacy weather systems will be subsumed (WMSCR, ADAS, WIFS, ALDARS)". — [FPAW 2018, NextGen Weather Systems](https://fpaw.aero/sites/default/files/123/alfred-nextgen-weather-fpaw-july-2018_0.pdf)
- The plan to "Transition All User Systems from Using WARP/CIWS to CSS-Wx in 2025" lists ITWS among the internal consumers moving to CSS-Wx (for gridded NOAA data and MDCRS). — [FPAW, Brown, Transition of Legacy Weather Data Consumers (Oct 2024)](https://fpaw.aero/sites/default/files/197/1a3-brown-nextgen-wx-user-transition.pdf)
- ITWS on SCDS today offers only "Standard" and "Alerts" product groups. No ITWS SCDS product was found that republishes ASOS OMO. — [SWIFT Portal](https://portal.swim.faa.gov/)
- WMSCR has historically served "External users (External to the NAS)" via Service A/NADIN gateways, e.g., commercial airlines. The verification scope listed meteorological information and NOTAMs; OMO is not mentioned. — [DTIC, WMSCR test plan (1992)](https://apps.dtic.mil/sti/tr/pdf/ADA257219.pdf)
- FAA Weather Observation Research (FPAW Oct 2024): a CASS device bridges the ASOS/AWOS HDLC port to ADAS over IP/LTE as R&D. It notes "One-minute rain gauge information could become available to a 'listener'" and "alternative data distribution paradigms". This is research, not a service. — [FPAW, Passetti, WOR briefing](https://fpaw.aero/sites/default/files/197/3b1-passetti-wor-briefing-fpaw.pdf)
- FAA Surface Weather Status Dashboard (Federal Register, Oct 6 2026): an information collection for voluntary reports of AWOS/ASOS outages and erroneous data, to "publish the status onto the FAA's Surface Weather Status Dashboard". This is status only, not observation data. — [Federal Register 2026-20483](https://www.federalregister.gov/documents/2026/10/06/2026-20483/agency-information-collection-activities-requests-for-comments-clearance-of-a-new-approval-of)

### Inferences
- The only FAA-sanctioned external OMO product found is CSS-Wx OMO via SWIM. ADAS, WMSCR, WARP and ITWS are internal or legacy consumers. No ARINC/SITA/Collins resale of OMO was documented.

### Gaps
- No document gives ADAS poll timing within the minute, WMSCR forwarding cadence, or CSS-Wx publication delay for OMO.
- No evidence was found either way on whether any WMSCR/NADIN external subscriber (airline or vendor) receives raw OMOs.

---

## Does any NWS channel (AWIPS/LDAD, WFO 5/15-min OMO polling, NOAAPort, NWWS) carry OMO to the public?

### Takeaway
Only MADIS, which is public, unrestricted and HTTPS-based, together with redistributors such as Synoptic. The ASOS-era AWIPS design gave WFOs "selected OMO data ... once every 5 or 15 minutes upon request", which is internal. MADIS explicitly excludes LDM for this dataset, and no evidence was found of OMO on NOAAPort or NWWS. The MADIS feed was down from October 2023 to January 2026, per Synoptic, and is still labeled experimental.

### Cited Findings
- ASOS data-outlet chart: OMO via NWS AWIPS is "Selected OMO data provided once every 5 or 15 minutes upon request"; SHEF is "Available through FAA ADAS interface". — [ASOS Data Flow charts (NWS)](https://www.weather.gov/media/asos/aum-charts2.pdf)
- ASOS User's Guide: "Future communication links will allow each NWS WFO to access the OMO data from selected ASOS locations every 5-minutes when operating in the 'warning' mode, or every 15-minutes when operating in the 'alert' mode." — [ASOS User's Guide](https://www.weather.gov/media/asos/aum-toc.pdf)
- Unidata (2021), answering a request for KNYC OMO in AWIPS CAVE: "The One Minute Observations are distributed through MADIS ... we don't have access to the MADIS data here at Unidata." — [Unidata AWIPS support archive](https://support.unidata.ucar.edu/archives/awips/msg01024.html)
- MADIS 1-minute ASOS: "the current and previous hour's data are processed every 5 minutes ... These data are available with all communications methods supported by MADIS except for ldm." Restrictions: "No restrictions." — [MADIS 1-minute ASOS](https://madis.ncep.noaa.gov/madis_OMO.shtml)
- MADIS release notes: March 2023 (v4.0.8), "The ingestion of HF-ASOS and EDR data moved to MADIS operational systems". May 2025 (v4.0.12), OMO hourly precip changed to PCP1HA. — [MADIS Recent Changes](https://madis.ncep.noaa.gov/madis_recent.shtml)
- NWS SCN 26-03: FTP on madis-data.ncep.noaa.gov was turned off around April 21, 2026, and HTTPS remains with "no additional latency". — [NWS SCN 26-03](https://www.weather.gov/media/notification/pdf_2026/scn26-03_Termination_FTP_on_madis-data.ncep.noaa.gov.pdf)
- Synoptic: "HF-ASOS data was unavailable from its source between October 2023 and January 2026. We have established a new connection with NWS and FAA". The dataset is "experimental ... brief to several-day outages are not uncommon". Since 2019, Synoptic has received "the full 1-minute data, as a low-latency provisional and real-time data stream from MADIS". — [Synoptic HF-ASOS](https://docs.synopticdata.com/services/high-frequency-asos)
- IEM's 1-minute archive comes from NCEI and "is not realtime and is delayed by 18–36 hours or more". — [IEM ASOS page](https://mesonet.agron.iastate.edu/ASOS)

### Inferences
- The public NWS path, ADAS/WMSCR → MADIS, adds about 2m13s–2m19s by the time MADIS receives the record, per the measurement above. That is well outside a 30 s target. The 5-minute processing cadence on the MADIS side can add more delay before user access.
- The "new connection with NWS and FAA" restored in January 2026 may now originate from CSS-Wx rather than WMSCR. That is unverified; MADIS docs still name WMSCR.

### Gaps
- No NWS service change notice was found documenting the Oct 2023 outage or the Jan 2026 restoration, or any change of OMO source system.
- Access terms for the full 1-minute stream that Synoptic receives (versus the 5-minute public netCDF files) were not determined; it may be a MADIS LDAD push or sponsored access.

---

## Is there evidence that the ASOS 2.0 goal of "ubiquitous access to OMO" has been implemented (dates, mechanism, public availability)?

### Takeaway
The goal is real: NWS ASOS PM Ken Boutin's May 2023 FPAW slide lists "Ubiquitous access to OMO (goal)" under what ASOS 2.0 adds, alongside IP communications. Hardware is delivered (1,529 Campbell Scientific units by 2025), and IP conversion of comms lines is scheduled for CY2026. No evidence was found that a public, real-time OMO access mechanism has been implemented as of October 2026.

### Cited Findings
- Boutin (NWS ASOS PM), FPAW, May 16 2023: ASOS 2.0 "Retains: ... METAR/SPECI/OMO, 5-Min, SHEF, summaries"; "Adds: Ceilometer Derived Planetary Boundary Layer Height – Attenuated Backscatter Dataset – IP communications – Ubiquitous access to OMO (goal)". Strategic goal "By end of 2026: Design, validate and deploy all ACU/DCP/SCA Replacements (aka ASOS 2.0) – Replace all copper voice and data lines with Internet Protocol communications". — [FPAW, Boutin, A Decadal Look at ASOS Lifecycle Upgrades](https://fpaw.aero/sites/default/files/163/2-boutin-decadal-look-asos-lifecycle-upgrades.pdf)
- The FPAW Spring 2023 summary says Boutin's update "included upgrades to the central processing systems, replacement sensors, real-time access to one-minute observations, and changes to some of the algorithms". In that summary, the word "ubiquitous" refers to ADS-B Weather (Steve Darr), not OMO. — [FPAW Spring 2023 Summary](https://fpaw.aero/sites/default/files/163/spring-2023-fpaw-meeting-summary.pdf)
- NWS Nebraska (Heartland Conference, Mar 2026): ASOS 2.0 "Includes new hardware and software that allows for an upgrade to modern IP communications, sensor/system integration and expanding the availability and periodicity of ASOS data". Timeline item: "CY2026: ... Replace all copper voice and data lines with Internet Protocol communications". — [NWS ASOS 2.0 Upgrade Project brief](https://engineering.uiowa.edu/sites/engineering.uiowa.edu/files/2026-03/HeartlandConferenceBrief.pdf)
- Campbell Scientific: "By 2025, Campbell Scientific had delivered all 1,529 units to NOAA-NWS, the FAA, and the DoD" under ASOS-SLEP. — [Campbell Scientific case study](https://www.campbellsci.com/resources/case-studies/us-asos-weather-network)
- An NWS WFO presentation (Feb 2023) raised the open question "Will the IP comms protocol for the dissemination of data include the ability to access one minute observations (OMO)?" — [NWS, Murphy (Feb 2023)](https://www.weather.gov/media/lix/gcaws/Presentation1Murphy.pdf)
- A historical policy barrier is documented in an NWS/AMS paper (c. 2009, referencing FY2009 activities): "In order for OMO data to be made available to NOAA partners, the NWS and FAA must implement the technology refresh, revise its policies and procedures, and implement changes to the communications and data processing backbones". It also notes "many users have stated a need for the OMO data". — [McNitt & Facundo, AMS](https://ams.confex.com/ams/pdfpapers/145078.pdf)

### Inferences
- The "ubiquitous access to OMO" goal depends on IP comms (CY2026) and on policy changes. On the FAA side the operative distribution vehicle appears to be CSS-Wx/SWIM. On the NWS side it remains the MADIS path. Neither offers a documented sub-30 s public feed today.

### Gaps
- No NWS service change notice, ASOS 2.0 interface spec, or program statement was found that gives a date or mechanism (API, LDM, NOAAPort, SWIM) for public OMO access after ASOS 2.0 IP cut-over.
- The share of ASOS sites already converted to IP comms as of October 2026 was not found.

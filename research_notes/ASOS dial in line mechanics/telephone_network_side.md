# Telephone-Network Side of ASOS Public Dial-In Numbers (Twilio → PSTN/VoIP → ASOS voice port)

Research date: 2026-10-10. Scope: the network path between a caller (e.g., a Twilio Programmable Voice call) and the analog voice port of an ASOS. The notes cover diagnostics and mechanism only. Nothing here describes holding or monopolizing a line, defeating the auto-disconnect, timing redials to win seizure races, evading carrier spam controls, or accessing the password-protected remote-user modem port.

Method note for original data in this file:
- **Numbers.** Current ASOS numbers were read from AirNav airport pages, which republish FAA Chart Supplement data, on 2026-10-10.
- **Carriers.** Each number's NPA-NXX-X thousands-block was looked up in the LocalCallingGuide XML prefix service, which reflects LERG/number-pooling assignments.
- **History.** Historical numbers come from Wayback Machine captures of the same AirNav pages.

Caveat: the block holder is the carrier that was originally assigned the number block. A number can later be ported to another carrier, so block data shows how a number was *originally* provisioned, not necessarily who serves it today.

---

## 1. What kind of telephone service is an ASOS public number, and who provisions it?

### Takeaway
Historically (1990s through roughly 2023), the ASOS public voice number was an ordinary local-exchange analog line from the incumbent telco. The FAA sponsored it as "FAA sponsored telephone dial-in access," and FAA Technical Operations is responsible for the circuits. There is no evidence of hunt or rotary groups: every site lists one unique number.

That has changed. In an 82-airport sample taken on 2026-10-10:
- **82%** of current ASOS numbers (68 of 82) sit in number blocks held by wholesale VoIP-type CLECs: Bandwidth.com CLEC (58) and Onvoy (10).
- Many of those blocks are in rate centers far from the airport (KDEN's number is a 719 Cañon City number).
- Wayback captures show the old numbers were ILEC (Bell or Frontier) numbers that were replaced between 2023 and 2026.

This strongly suggests a fleet-wide FAA migration of ASOS voice lines off copper POTS onto IP-delivered voice service. That is an inference; no FAA statement was found.

### Cited Findings
- **Service sponsorship (1998 document).**
  - ASOS voice is "made available to the general aviation public through FAA sponsored telephone dial-in access."
  - Ch. 7: "a dial-in telephone number provided at each ASOS location."
  - Computer-generated voice is available "through FAA radio broadcast to pilots, and general aviation dial-in telephone lines."
  - — [ASOS User's Guide (NWS 1998)](https://www.weather.gov/media/asos/aum-toc.pdf); [NCEI copy](https://www.ncei.noaa.gov/data/automated-surface-observing-system-one-minute-pg1/doc/asos_users-guide.pdf)
- **FAA orders the telco circuits** (2004, long-line circuits): "The FAA will order all telco circuits. The NWS will connect to the ASOS ACU." Also: "FAA will order 4-wire, leased circuits as required." — [ASOS Communications Transfer Implementation Plan (2004)](https://www.weather.gov/media/asos/ASOS%20Implementation/ACTIP031604new.pdf)
- **FAA Tech Ops holds responsibility for ASOS telephone circuits** (2019, PAKT Ketchikan).
  - "The Technical Operations Office in Anchorage has the responsibility for PAKT ASOS telephone circuits and the ASOS itself is owned and maintained by the NWS."
  - "AT&T, the primary telephone company for this circuit."
  - The FAA log notes "FAA OWNS MODEM PER FACILITY INFO."
  - — [NTSB docket CEN19MA141, Meteorology Attachment 1](https://data.ntsb.gov/Docket/Document/docBLOB?FileExtension=pdf&FileName=WX_CEN19MA141AB_Attachment_1_redacted-Rel.pdf&ID=8134624)
- **FAA network contracts.**
  - FTI (Harris, now L3Harris, 2002) provided "consolidated telecom services for the 5,000 facilities and 30,000 circuits in the NAS."
  - FENS (Verizon, awarded March 2023, 15 years, about $2.4B) is FTI's successor. — [Verizon press release](https://www.verizon.com/about/news/verizon-public-sector-wins-federal-aviation-administration-fens-contract); [SAM.gov award](https://sam.gov/workspace/contract/opp/7e58b8f050ef40f59761aa3b334528a5/view)
  - FENS is the FAA's means to "shift away from its current setup of relying on time division multiplexing … that typically goes through copper wires." — [Washington Technology (2023-03-28)](https://www.washingtontechnology.com/companies/2023/03/faa-selects-verizon-24b-telecommunications-contract/384517/)
  - The NAS roadmap lists "FTI Sustainment 2" from 2023 to 2027 and a "JRC Strategy Decision for TDM-IP Phase" in 2029 Q1. — [FAA NAS Infrastructure Roadmaps, Communication](https://www.faa.gov/sites/faa.gov/files/NAS-Infrastructure-Roadmaps-v20-Communication.pdf)
- **FAA tracks ASOS outages against leased services.** The FAA WeatherCams station list (Oct 2026) tags federal ASOS outages with the cause category "Non-FAA Lines, Circuits, or Leased/Provisioned Services (LPS): Circuit/Line/IP Cloud." Example: KAMA "Upcoming scheduled outage … Outage will begin at 2026-10-12 06:00z." — [FAA WeatherCams AWOS/ASOS Stations List](https://weathercams.faa.gov/stations)
- **One number per site, no duplicates (original sample, 2026-10-10).** Of 82 major ASOS airports, every one lists exactly one ASOS number, and no number is shared between sites.
  - 27 of 82 list the number alongside a VHF frequency ("WX ASOS: 119.15 (645-231-5974)").
  - 55 are "PHONE"-only.
  - — AirNav pages, e.g., [KDEN](https://www.airnav.com/airport/KDEN), [KMIA](https://www.airnav.com/airport/KMIA), [KPHL](https://www.airnav.com/airport/KPHL)
- **Block holders of current numbers (original sample, n=82, 2026-10-10).**

  | Holder | Count |
  |---|---|
  | Bandwidth.com CLEC, LLC | 58 |
  | Onvoy, LLC | 10 |
  | ILECs (Southwestern Bell 4, BellSouth 3, Qwest 3, Illinois Bell 1, Consolidated Communications VT 1, Verizon New England 1) | 13 |
  | MCImetro (Verizon Business CLEC) | 1 |

  Examples, all from the LocalCallingGuide prefix service ([example query](https://www.localcallingguide.com/xmlprefix.php?npa=719&nxx=204&blocks=1)):
  - KDEN 719-204-1223: Bandwidth, rate center **Cañon City**.
  - KMSP 218-203-0160: Bandwidth, **Brainerd**.
  - KDTW 231-202-2054: Bandwidth, **Mecosta**.
  - KDCA 276-200-0159: Bandwidth, **Wytheville VA**.
  - KPDX 458-212-2405: Bandwidth, **Grants Pass**.
  - KPIT 215-798-0218: Bandwidth, **Philadelphia suburban**.
- **Seven target stations (2026-10-10).** KNYC is not an airport and was not checked.

  | Station | Current number | Block holder (type), rate center | Earlier number (capture date) and holder |
  |---|---|---|---|
  | KLAX | 310-602-6051 | Bandwidth (CLEC), Lomita | 310-568-1486 (2019-07, 2023-06), Pacific Bell (ILEC); changed by 2025-08-16 |
  | KMIA | 645-231-5974 | Bandwidth (CLEC), Miami (645 overlay) | 305-870-0235 (2019-07), BellSouth (ILEC) |
  | KPHL | 267-404-1002 | Bandwidth (CLEC), Perkasie | not checked |
  | KMDW | 773-884-4424 | Illinois Bell (ILEC) | same number in 2022-06 and 2023-04 captures |
  | KDEN | 719-204-1223 | Bandwidth (CLEC), Cañon City | 303-342-1920 (2024-06-04), Qwest (ILEC); changed by 2025-08-13 |
  | KAUS | 512-369-7881 | Southwestern Bell (ILEC), Austin | not checked |

  Sources: [AirNav KLAX](https://www.airnav.com/airport/KLAX); [Wayback KLAX 2019](https://web.archive.org/web/20190709153424/http://www.airnav.com:80/airport/klax); [Wayback KLAX 2023](https://web.archive.org/web/20230611055842/https://www.airnav.com/airport/KLAX); [Wayback KLAX 2025](https://web.archive.org/web/20250816090636/http://www.airnav.com/airport/KLAX); [Wayback KMIA 2019](https://web.archive.org/web/20190704103200/http://airnav.com:80/airport/KMIA); [Wayback KDEN 2024](https://web.archive.org/web/20240604201354/https://airnav.com/airport/kden); [Wayback KDEN 2025](https://web.archive.org/web/20250813172701/https://www.airnav.com/airport/KDEN); [Wayback KORD 2022](https://web.archive.org/web/20220628160409/http://airnav.com/airport/KORD)
- **Other number changes seen in captures.** All old numbers are in ILEC blocks; the new ones are CLEC.
  - KORD: 773-462-0118 (Illinois Bell, 2022/2023) → 773-800-0035 (Bandwidth).
  - KJFK: 718-656-0956 (Verizon NY, 2023-05) → 347-588-1609 (Bandwidth).
  - KLGA: 718-672-6317 (Verizon NY) → 929-229-1994 (Bandwidth).
  - KEWR: 973-621-2892 (Verizon NJ) → 862-381-4743 (Bandwidth).
  - KTEB: 201-393-0855 (Verizon NJ) → 201-473-3130 (Bandwidth).
  - KLGB: 562-424-0572 (Frontier, 2023) → 562-247-0378 (Bandwidth) by 2025-08.
  - KSMO: 310-392-6453 (Frontier; still listed 2025-08) → 310-309-5134 (Teleport Communications America, AT&T's CLEC) by 2026-10.
  - KVNY: 818-904-9213 (Pacific Bell; still listed 2025-08) → 818-464-9794 (Teleport Communications America) by 2026-10.
  - — [Wayback KJFK 2023](https://web.archive.org/web/20230527223600/http://www.airnav.com/airport/KJFK); [Wayback KORD 2023](https://web.archive.org/web/20230430013907/http://www.airnav.com/airport/KORD); current AirNav pages
- **Program goal.** "By end of 2026: … Replace all copper voice and data lines with Internet Protocol communications." — [Boutin, ASOS PM, FPAW 2023](https://fpaw.aero/sites/default/files/163/2-boutin-decadal-look-asos-lifecycle-upgrades.pdf); same FY26 goal: "Replace all copper voice & data lines w/IP comms" — [V. Murphy, NWS](https://www.weather.gov/media/lix/gcaws/Presentation1Murphy.pdf)
- **FAA research on ASOS data over LTE.** "TDM/IP for ASOS and AWOS. A CASS (Conversion Appliance System) device communicates locally to the AWOS-C and ASOS … via the High-Level Data Link Control (HDLC) communications port … provides a bridge to the ADAS via the IP interface over LTE." This covers data, not the voice line. — [FAA Weather Observation Research Program briefing, FPAW](https://fpaw.aero/sites/default/files/197/3b1-passetti-wor-briefing-fpaw.pdf)
- **No hunt-group evidence; pilots describe single-line behaviour.**
  - "Sometimes, you may get a busy tone if someone else is on the line… only one call can go through at a time!" — [TxTop Aviation (2020)](https://txtopaviation.com/how-to-get-the-current-weather/)
  - "The only downside to using the phone number is that it will be busy sometimes… when a crazy front is coming through." — [PilotsOfAmerica (2016)](https://www.pilotsofamerica.com/community/threads/phone-number-for-atis.98234/)
  - Trader community: "often, only one call can access the ASOS line at a time." — [Wethr.net market bots](https://wethr.net/edu/market-bots)
- **Non-federal AWOS standard (does not govern ASOS).** "Typically, the telephone-answering device should have the capability to answer five calls at a time… The minimum requirement is that the system answers a single call." — [FAA AC 150/5220-16E](https://www.faa.gov/documentLibrary/media/Advisory_Circular/AC_150_5220-16E.pdf)
- **FAA ASOS/AWOS list is not machine-readable.** The FAA "Surface Weather Observation Stations (ASOS/AWOS)" page embeds a Tableau dashboard (explore.dot.gov), and CSV export returned HTTP 403. — [FAA ASOS/AWOS page](https://www.faa.gov/air_traffic/weather/asos)

### Inferences
- **Fleet-wide re-provisioning onto IP voice (high confidence that numbers were re-provisioned; medium that the delivery is IP/VoIP).** Every airport whose history was checked (11: KLAX, KDEN, KMIA, KORD, KJFK, KLGA, KEWR, KTEB, KLGB, KSMO, KVNY) swapped an ILEC number for a CLEC number between about 2023 and 2026, and 68 of the 82 sampled current numbers are in Bandwidth or Onvoy blocks, many in rate centers unrelated to the airport. Wholesale CLECs that hand out out-of-area numbers are characteristic of hosted VoIP, SIP or POTS-replacement services, not copper loops from the local central office. This matches the FAA/NWS "replace all copper voice and data lines with IP" goal and FENS's TDM-exit mandate. Which vendor or contract, and whether delivery is fiber/SIP to an ATA or LTE to a cellular POTS-replacement box, is not public.
- **Likely still copper (medium confidence).** KMDW (773-884, Illinois Bell) and KAUS (512-369, Southwestern Bell) are in AT&T ILEC blocks, as are KATL, KSEA, KLIT, KMSY and KELP. These may still be legacy POTS, or they may have been ported to a new provider while keeping the number. Both KMDW and KAUS are in AT&T territory and exposed to AT&T's 2026–2029 copper exit.
- **"Who provisions it" (medium-high confidence).** The FAA (Technical Operations and its telecom contracts) orders and pays for the voice line. The telco or VoIP provider is the FAA's vendor. The NWS owns the ASOS hardware at NWS-sponsored sites but not the circuits. That rests on the 2004 plan, the 2019 NTSB email and the "FAA sponsored" wording; it was not confirmed for the 2023–2026 re-provisioning.
- **Single call appearance (high confidence).** Whatever the access technology, the effective capacity per site appears to be one simultaneous caller, because the ASOS voice subsystem presents one analog port and the observed behaviour is busy on contention. A hosted platform may support several call paths per number, but they converge on one FXS/analog port.
- **Number currency matters for diagnostics (high confidence).** Old numbers (e.g., KDEN 303-342-1920, KLAX 310-568-1486) are no longer published. Dialing a stale number from an old list or app cache would produce "failed"/404/410 or reach an unrelated subscriber, not "busy."

### Gaps
- No FAA or NWS document, contract notice, NOTAM series or Service Change Notice was found announcing or explaining the 2023–2026 ASOS number changes, the vendor, or the access technology (SIP/ATA vs LTE gateway).
- Number-level current carrier (after porting) was not checked; that needs an LNP lookup, e.g., Twilio Lookup line-type intelligence, which was not run here.
- KNYC's number and its block holder were not checked (KNYC is not on AirNav). KPHL's and KAUS's historical numbers were not checked.
- Whether some sites are served by FENS/Verizon-provisioned lines (one MCImetro block at KMEM; two TCG blocks) versus other contracts is unknown.

---

## 2. Busy mechanics: how the network decides "busy" vs. connected, and how other failure modes map

### Takeaway
"Busy" is decided by the terminating element that owns the analog port: the ILEC Class 5 switch for a copper line, or the ATA / hosted-PBX / POTS-replacement gateway for an IP-delivered line. When the port is already off-hook, or is already allocated to a ringing call, the element rejects the new setup with:
- ISUP cause 17 "user busy" in TDM signalling, or
- SIP 486 Busy Here on IP;
- Twilio then reports `CallStatus=busy`, with Debugger code 31486 and Last SIP Response 486.

Network congestion is a different signal: ISUP causes 34/38/41/42/47 map to SIP 503 and the reorder (fast-busy) tone at 120 IPM, and Twilio generally reports `failed`. Analytics-based blocking must now be signalled with SIP 603+ ("Network Blocked") / ISUP 21. A call that rings without answer gives 408/480 or Twilio's own ring timeout, reported as `no-answer`.

### Cited Findings
- **ISUP → SIP mapping (RFC 3398, Dec 2002, §7.2.4.1).**

  | ISUP cause | SIP response |
  |---|---|
  | 1, 2, 3 (unallocated number / no route) | 404 |
  | 16 normal clearing | BYE/CANCEL |
  | 17 user busy | 486 Busy Here |
  | 18 no user responding | 408 |
  | 19, 20, 31 (no answer / subscriber absent / normal unspecified) | 480 |
  | 21 call rejected | 403, or 603 if cause location = user |
  | 22 number changed | 410 (301 if diagnostic present) |
  | 27 destination out of order | 502 |
  | 28 address incomplete | 484 |
  | 34, 38, 41, 42, 47, 58, 88 (resource/congestion) | 503 |
  | 102 recovery on timer expiry | 504 |
  | others | default 500 |

  The gateway may also discard in-band busy media and send a response code "(such as 180 or 486) in its stead." — [RFC 3398](https://www.rfc-editor.org/rfc/rfc3398.html)
- **Tones (North American precise tone plan).**
  - Busy: 480+620 Hz, 0.5 s on / 0.5 s off.
  - Reorder ("fast busy"): same frequencies, 0.25 s on / 0.25 s off. The original plan distinguished 0.2/0.3 s for toll congestion from 0.3/0.2 s for local reorder.
  - Audible ringing: 440+480 Hz, 2 s on / 4 s off.
  - — [Precise tone plan (Wikipedia)](https://en.wikipedia.org/wiki/Precise_Tone_Plan)
  - The federal RUS switch spec gives the same: "Line busy tone shall be low tone interrupted at 60 IPM … Reorder, all paths busy, and no circuit tone shall be low tone interrupted at 120 IPM." — [7 CFR 1755.522](https://www.ecfr.gov/current/title-7/subtitle-B/chapter-XVII/part-1755/section-1755.522)
- **What the tones mean.**
  - "Busy tone indicates that the called line has been reached but it is engaged in another call."
  - "Reorder (Fast Busy) tone indicates that the local switching paths to the calling office or equipment serving the customer are busy or that a toll circuit is not available."
  - — [Cisco VCO/4K, Call Progress Tones](https://docstore.mik.ua/univercd/cc/td/doc/product/tel_pswt/vco_prod/sup_call/sup04.htm)
- **ISUP release with cause.** REL "is also sent (in direct response to an IAM) if the terminating switch determines that the call cannot be completed… the terminating switch provides a cause value… e.g., 'User busy'." — [ISDN User Part (Wikipedia)](https://en.wikipedia.org/wiki/Release_(ISUP))
- **Analytics-blocking signalling (FCC rule, current).**
  - 47 CFR 64.1200(k)(9): a terminating provider that blocks based on analytics "must immediately return, and all voice service providers in the call path must transmit," SIP 603+ (ATIS-1000099) on IP networks, or "ISDN User Part (ISUP) code 21 with the cause location 'user'" on non-IP networks. ISUP 21 maps to SIP 603 or 603+. — [eCFR 47 CFR 64.1200](https://www.ecfr.gov/current/title-47/chapter-I/subchapter-B/part-64/subpart-L/section-64.1200)
  - The March 2025 order requires "exclusive use of SIP code 603+" for analytics blocking. It directs providers to "cease using the standard version of SIP code 603, or SIP codes 607 or 608, for this purpose," with implementation "no later than 12 months" from Federal Register publication (published 2025-03-24). 607 remains for subscriber-directed blocking. — [Federal Register 2025-04811](https://www.federalregister.gov/documents/2025/03/24/2025-04811/advanced-methods-to-target-and-eliminate-unlawful-robocalls)
  - Twilio: 603+ "applies to calls blocked by analytics (like suspected spam). Other types of blocking, such as … DNO lists … aren't affected." — [Twilio blog (2025-09-15)](https://www.twilio.com/en-us/blog/insights/fcc_new_standard)
  - From 2026-04-23, Twilio Elastic SIP Trunking passes the carrier's 603 "Network Blocked" Reason header. Example: `Reason:SIP;cause=603;text="v=analytics1;url=...";location=RLN`. It is visible "by downloading the PCAPs from Twilio console call logs." — [Twilio changelog](https://www.twilio.com/en-us/changelog/elastic-sip-trunking---pass-on-603--reason-header-information-to)
- **Twilio busy detection.**
  - "Twilio relies on the downstream carrier … to signal if a line is busy. If the carrier returns a SIP 'busy' code (such as 486 Busy Here or 600 Busy Everywhere), Twilio will: Set the call's CallStatus to busy … Log the busy event in Voice Insights and Debugger (error code 31486)."
  - "Some carriers do not send a busy SIP code … they may: Play an in-band audio announcement … Let the call ring indefinitely … Route the call to voicemail … the call is marked as completed, no-answer … not busy."
  - "Twilio cannot programmatically detect in-band announcements."
  - — [Twilio Support: Detecting When a Recipient Is Already on Another Call](https://support.twilio.com/hc/en-us/articles/53558413407003-Detecting-When-a-Recipient-Is-Already-on-Another-Call-With-Twilio-Programmable-Voice)
- **Twilio status definitions** (Call resource): `busy` "The caller received a busy signal"; `no-answer` "There was no answer or the call was rejected"; `failed` "The call could not be completed as dialed, most likely because the provided number was invalid." — [Twilio Call resource](https://www.twilio.com/docs/voice/api/call-resource)
  - Support article: `failed` = "Twilio's carriers could not connect the call. Possible causes include the destination is unreachable, or the number may have been input incorrectly"; `busy`, `no-answer`, `canceled`, `failed` are not charged. — [Twilio Support: call statuses](https://support.twilio.com/hc/en-us/articles/223132547-What-are-the-possible-call-statuses-and-what-do-they-mean)
  - Error 34003 ("Callee did not answer") maps to `no-answer`. "The destination rejected the call. Twilio can report a rejected call as no-answer." It advises reviewing "the terminal CallStatus and SipResponseCode values to confirm whether the call timed out or was rejected." — [Twilio error 34003](https://www.twilio.com/docs/api/errors/34003)
- **Voice Insights fields.** The Call Summary resource exposes `properties.last_sip_response_num`, `properties.pdd_ms` (post-dial delay), `properties.disconnected_by` (e.g., "callee"), plus `call_state`, `duration` and `connect_duration`. — [Twilio Voice Insights Call Summary](https://www.twilio.com/docs/voice/voice-insights/api/call/call-summary-resource)

### Inferences
- **Diagnostic decision table** (medium-high confidence; built from the cited mappings, not from a Twilio-published table):

  | What Twilio shows | Likely meaning |
  |---|---|
  | `busy`, Last SIP 486 (or 600), Debugger 31486, short `pdd_ms`, zero connect duration | **Station busy.** The ASOS port is off-hook or already alerting for another caller. |
  | `no-answer` after about the full `Timeout` (default 60 s) with ringing events | Line rang but the ASOS did not answer: ASOS voice board down, line misrouted, or (on a VoIP line) a call-waiting style second call appearance that the ASOS cannot pick up. Not a busy. |
  | `no-answer`/`failed` with 408/480 | No user responding / temporarily unavailable (ISUP 18/19/20/31 equivalents). On IP-delivered lines, e.g. ATA offline or unregistered, or LTE gateway down. |
  | `failed` with 503 (Q.850 34/38/41/42/47 upstream) | **Network or carrier congestion or failure**, not the ASOS line. Audible equivalent is reorder at 120 IPM. Expect it to be uncorrelated with ASOS usage and often to affect other destinations too. |
  | 603 with a Reason header containing `v=analytics1` (603+) | **Analytics-based blocking** by a terminating or intermediate provider. Twilio may surface it as `failed` or `no-answer` (rejected); Programmable Voice mapping is not documented. Plain 603/607 = decline or subscriber-directed block. |
  | 404/410/484 | Number not in service / changed / incomplete (ISUP 1/3/22/28). Check for stale ASOS numbers after the 2023–2026 renumbering. |
  | HTTP 429, error 10004, or long `queue_time` | **Twilio account-side** concurrency or CPS limits; the call never reached the PSTN. |
  | `completed` but the recording contains fast-busy, busy tone or an intercept message | An in-band signal Twilio cannot classify (per Twilio). Detect it from the audio. |

- **Q.850 cause visibility (medium confidence).** Twilio Programmable Voice does not document exposing raw Q.850 cause values. The SIP response code and, on Elastic SIP Trunking, a PCAP Reason header are the practical proxies. On an all-IP path (Twilio → Bandwidth/Onvoy-hosted number → ATA), there may be no ISUP leg at all, so no Q.850 cause is ever generated; the 486 comes straight from the far-end SIP element.
- **STIR/SHAKEN and analytics labelling (medium confidence).** These matter mainly for display and labelling on consumer handsets. An ASOS has no display, so labelling has no effect on it; only outright blocking (603+) would. Analytics blocking on an enterprise or FAA hosted line is possible but less common than on consumer wireless; no evidence it happens on ASOS lines.

### Gaps
- No Twilio document gives a complete SIP-code → CallStatus table (e.g., whether 503 → `failed` and 603 → `failed` or `no-answer` in Programmable Voice). The mappings above are inferred.
- The actual SIP responses returned by ASOS lines were not observed here. The user's own Voice Insights `last_sip_response_num` for busy calls would confirm 486.

---

## 3. Contention: who gets the line when it frees up, and the timing elements

### Takeaway
A single-appearance analog line, whether ILEC POTS or ATA/FXS, has no queue, no camp-on and (normally) no call waiting. Each call setup is evaluated independently at the moment it reaches the terminating element:
- If the port is idle, it is allocated to that call and ringing starts. From that instant the line is busy to everyone else, even before the ASOS answers.
- If the port is off-hook, ringing, or still in its post-release disconnect or guard interval, the new setup gets busy (486 / cause 17).

There is no memory of earlier busy attempts. "Who gets through" is simply whichever setup arrives first after the port returns to idle. Several timing elements separate the end of one call from the next possible seizure:
- the ASOS's own two-loop disconnect (about 90 s);
- on-hook recognition (about 0.8 s or more);
- release signalling to the network;
- equipment guard timing (sub-second to about 1 s);
- for the next caller, post-dial delay plus ringing until the ASOS answers (the AWOS standard is answer before the 2nd ring, i.e. within about 6–8 s at a 2 s on / 4 s off cadence).

### Cited Findings
- **Loop-start line mechanics.**
  - "When the loop is opened and current stops flowing for a certain period of time, the subscriber equipment signals that it has finished using the line; the telephone exchange resets the line to an idle state."
  - Hook flash is "interrupting the loop for a fraction of a second, typically at least 300 ms… shorter than the time required for the on-hook condition."
  - Disconnect supervision (calling party control) "is implemented as an open switching interval (OSI)… Some switching systems remove loop battery voltage for about 250 ms within 6 seconds after the far-end party disconnects."
  - Plain loop start "imposes no requirement to the central office end to inform the subscriber end of distant far-end disconnection conditions."
  - — [Loop start (Wikipedia)](https://en.wikipedia.org/wiki/Loop_start)
  - CPC/forward disconnect "removes an abandoned call from a hold queue or interactive voice response menu"; an analog line "may also send tones, such as a busy signal, reorder tone, or dial tone, to indicate a call has ended." — [Disconnect supervision (Wikipedia)](https://en.wikipedia.org/wiki/Disconnect_supervision)
- **Example detection thresholds** (Cisco VCO analog SLIC port; illustrative of switch/gateway practice): ring generation "2.0 seconds on, 4.0 seconds off"; hookflash detect "Loop open for 300 ms to 800 ms"; disconnect detect "Loop open for > 800 ms." — [Cisco VCO/4K Supervision Signaling](https://docstore.mik.ua/univercd/cc/td/doc/product/tel_pswt/vco_prod/sys_adm/swsaa.htm)
- **Guard timing after release.** "Once a port goes on-hook, it remains idle for a brief period before becoming available for allocation; this delay period is known as guard timing… During guard timing, the port cannot be allocated to another call." The T1 I/O module example is 800 ms. "A call disconnect cannot be declared until the MAX FLASH detect time expires. This can slow down call disconnects." — [Cisco VCO/4K Call Supervision Signaling](https://docstore.mik.ua/univercd/cc/td/doc/product/tel_pswt/vco_prod/sup_call/sup03.pdf); [Supervision Signaling](https://docstore.mik.ua/univercd/cc/td/doc/product/tel_pswt/vco_prod/sys_adm/swsaa.htm)
- **ISUP suspend on called-party clear.** "For ANSI, only network-initiated SUS/RES are allowed. Only called party can send SUS… If the RES is not sent within timer T6 … the controlling exchange will initiate a release procedure." — [Dialogic ISUP Suspend/Resume](https://www.dialogic.com/webhelp/CSP1010/8.4.1_IPN3/ccs_isup_chap_-_suspend_resume.htm)
- **Answer timing standard (non-federal AWOS, analogous).** "The incoming call should be answered prior to completion of the second ring… The voice subsystem should automatically disconnect when the weather observation has been completely transmitted twice." — [FAA AC 150/5220-16E](https://www.faa.gov/documentLibrary/media/Advisory_Circular/AC_150_5220-16E.pdf)
- **Busy semantics.** Busy tone = "the called line has been reached but it is engaged in another call." — [Cisco VCO Call Progress Tones](https://docstore.mik.ua/univercd/cc/td/doc/product/tel_pswt/vco_prod/sup_call/sup04.htm)
- **Twilio ring timeout and PDD.** Outbound API `Timeout` defaults to 60 s (max 600 s), with "a 5-second buffer" in some flows; `<Dial>` defaults to 30 s. — [Twilio Call resource](https://www.twilio.com/docs/voice/api/call-resource); [Twilio error 34003](https://www.twilio.com/docs/api/errors/34003). Voice Insights reports post-dial delay as `pdd_ms`. — [Voice Insights Call Summary](https://www.twilio.com/docs/voice/voice-insights/api/call/call-summary-resource)
- **Prior-art relays treat busy as normal.** A patented AWOS/ASOS relay service implements busy, wait and retry handling. — [US Patent 7,088,241](https://www.freepatentsonline.com/7088241.html)

### Inferences
- **Independent attempts, no queue (high confidence).** On a single-appearance line without call waiting, the outcome of each attempt depends only on the port's state when the setup arrives at the terminating element. Earlier busy attempts confer no priority. This is the classic "blocked calls cleared" loss system.
- **When the line becomes busy (high confidence).** The line is unavailable from the moment alerting begins, not from answer. A caller whose setup arrives while another call is still ringing the ASOS gets busy, even though nobody is listening yet. If the first caller abandons during ringing (CANCEL/REL), the port returns to idle.
- **Release chain at the end of a connected call (medium confidence on the numbers):**
  1. The ASOS finishes two plays and goes on-hook.
  2. The serving switch or ATA recognizes on-hook after its disconnect threshold (roughly ≥0.8 s, often longer if flash detection is enabled).
  3. It signals release: BYE on SIP; REL on ISUP, possibly preceded by SUS and a timed-release wait on ILEC TDM lines.
  4. The port sits in guard state (example 0.8 s) before it can be allocated again.
  - So the line is typically re-seizable about 1–2 s after the ASOS hangs up on IP/ATA lines, possibly several seconds later on ILEC lines with calling-party-control timed release.
  - Twilio's `disconnected_by=callee` with `connect_duration` of about 90 s identifies an ASOS-initiated release.
- **Early caller hang-up may not free the line early (low-medium confidence).** If the caller hangs up first, the ASOS learns of it only if the line provides disconnect supervision (an OSI or polarity reversal, often within a few seconds) and the ASOS voice board honours it. Neither is documented for ASOS. If either is missing, the ASOS may keep the port off-hook until its own two-loop timer ends, so the line stays busy for the full cycle regardless of how long the caller listened. This is a key unknown for estimating contention.
- **Capacity arithmetic** (standard single-server Erlang-B, lost calls cleared; illustrative, high confidence in the math, low in the arrival assumptions).
  - Each successful call occupies the port for about 95–100 s (≤8 s ring, ~90 s playback, ~1–2 s release).
  - With total offered attempts λ per hour from all parties, offered load A ≈ λ × 97/3600 Erlang, and the probability a random attempt finds the line busy is B = A/(1+A):

    | Attempts per hour (λ) | B (chance an attempt is busy) |
    |---|---|
    | 10 | about 21% |
    | 37 | about 50% |
    | 100 | about 73% |

  - Retries after busy add offered load, so real blocking is higher than this Poisson model predicts. Several automated callers per station (Wethr notes "cities where OMO bots are known to be active") can make busy the dominant outcome.
- **Ring and answer phase (medium confidence).** At a 2 s on / 4 s off cadence, an ASOS meeting the "answer before end of 2nd ring" practice answers within about 2–8 s of alerting. On an IP-delivered line, the ATA or gateway generates the ringing locally and Twilio sees 180/183 followed by 200 OK. The ringing timing Twilio observes reflects the far-end equipment, not a central office.

### Gaps
- No ASOS document states whether the ASOS voice port honours disconnect supervision (CPC/OSI) or what its answer-ring count is. The AC is for non-federal AWOS.
- The actual timed-release (T6 / calling-party-control) behaviour of the specific ILEC switches serving KMDW and KAUS, and the guard and disconnect timers of whatever ATA or gateway serves the Bandwidth/Onvoy-numbered sites, are unknown.
- No measured data on the ASOS's ring count before answer or on the end-of-call to re-seizable interval was found. These could be measured passively from Voice Insights (`pdd_ms`, ring duration, `disconnected_by`, timestamps) on normal, low-rate calls.

---

## 4. Copper retirement and IP transition: are ASOS lines migrating, and how does that change busy behaviour?

### Takeaway
Yes. The ASOS program set a goal to replace all copper voice and data lines with IP by end of 2026. FENS (Verizon) is the FAA's TDM-to-IP vehicle, and the FCC (2025–2026) and AT&T (exit most copper by end of 2029; forced migrations from June 2026) are speeding the end of copper POTS. The phone-number evidence (§1) shows most major-airport ASOS numbers already re-provisioned onto CLEC/VoIP-type numbers.

On IP-delivered lines, "busy" is generated by the ATA, hosted platform or POTS-replacement box, not the central office. The usual result is still SIP 486, but behaviour depends on configuration:
- whether call waiting is enabled on the port;
- how many call paths the platform allows per number;
- whether the gateway is offline (480/408 instead of 486).

A POTS-replacement box gives one call appearance per analog port; it does not by itself add callers to a single-port ASOS.

### Cited Findings
- **ASOS program goal.** "By end of 2026: … Replace all copper voice and data lines with Internet Protocol communications"; project table includes "TDM to IP Upgrade." — [Boutin, FPAW 2023](https://fpaw.aero/sites/default/files/163/2-boutin-decadal-look-asos-lifecycle-upgrades.pdf). The ASOS 2.0 design (2017) keeps dial-up modems externally in its first iteration. — [Hays et al., AMS 2017](https://ams.confex.com/ams/97Annual/webprogram/Manuscript/Paper315698/AMS%20Modernization%20of%20ASOS%20Hardware%20and%20Software%20Paper_FINAL.pdf)
- **FAA network transition.** FENS (Verizon, 2023) succeeds FTI and moves the FAA off TDM over copper; FTI Sustainment 2 runs through 2027. — [Washington Technology](https://www.washingtontechnology.com/companies/2023/03/faa-selects-verizon-24b-telecommunications-contract/384517/); [FAA NAS Roadmap](https://www.faa.gov/sites/faa.gov/files/NAS-Infrastructure-Roadmaps-v20-Communication.pdf)
- **FCC deregulation (2025–2026).**
  - March–May 2025 Bureau orders waived the "stand-alone" requirement of the Alternative Options Test and single-service satisfaction of the Adequate Replacement Test, and eliminated filing requirements to grandfather legacy voice.
  - FCC 26-19 (2026) eliminated "all filing requirements in the Commission's network change disclosure rules and … public notices for short-term network changes and copper retirements." It also granted "blanket authorization for carriers to grandfather any legacy voice service" and applied "the 31-day automatic grant period to all discontinuance applications."
  - — [FCC 26-19](https://docs.fcc.gov/public/attachments/FCC-26-19A1.txt)
- **AT&T copper exit.**
  - AT&T "plans to shut down copper-based services across the vast majority of its US territory by the end of 2029," excluding California. Its replacement "AT&T Phone-Advanced" runs on fiber or wireless and includes "call forwarding, caller ID, call waiting." — [Light Reading (2024-12-04)](https://www.lightreading.com/regulatory-politics/how-and-when-at-t-will-kiss-copper-goodbye)
  - The FCC approved discontinuance in about 500 wire centers (about 10% of AT&T's footprint), effective June 2026. — [Light Reading (2025-09-25)](https://www.lightreading.com/broadband/at-t-s-copper-retirement-plan-plows-ahead); [Fierce Network (2025-09-05)](https://www.fierce-network.com/broadband/att-now-making-headway-its-copper-retirement-plan)
  - "Copper phone and broadband services will be discontinued in certain areas beginning this summer. This means it will stop working and the service will be disconnected." — [AT&T blog (2026-04-28)](https://about.att.com/blogs/2026/upgrade-home-phone-and-internet.html)
- **Local example (non-federal AWOS, 2025).**
  - Menomonie, WI: "On April 23, 2025, 24/7 Telecom terminated copper telephone lines to the AWOS." The dial-in had received 585 calls from 2025-01-01 to 04-23 (about 5.2 per day).
  - The city noted that under AC 150/5220-16E telephone dial-up is optional.
  - — [Menomonie airport commission minutes (2025-06-18)](https://menomonie-wi.gov/AgendaCenter/ViewFile/Minutes/_06182025-449) (via search summary)
- **Another IP/cellular dependency (AWOS, 2022 forum anecdote).** A pilot reported an AWOS "not reporting to the internet" after a phone service "upgrade" because "the service used a cell data signal to connect." — [PilotsOfAmerica (2022-12)](https://www.pilotsofamerica.com/community/threads/asos-prob-notam-or-no.141149/)
- **FAA ASOS data over LTE (research).** A CASS device bridges the ASOS ACU HDLC port "to the ADAS via the IP interface over LTE." — [FAA WOR briefing, FPAW](https://fpaw.aero/sites/default/files/197/3b1-passetti-wor-briefing-fpaw.pdf)
- **In-band vs signalled busy.** Some carriers "let the call ring indefinitely" or play an announcement instead of sending 486, and Twilio then reports `no-answer`/`completed`, not `busy`. — [Twilio Support](https://support.twilio.com/hc/en-us/articles/53558413407003-Detecting-When-a-Recipient-Is-Already-on-Another-Call-With-Twilio-Programmable-Voice)

### Inferences
- **The migration is mostly done for big airports (medium-high confidence).** 68 of 82 sampled numbers are CLEC/VoIP-type, with dated changes 2023→2026. Remaining ILEC-numbered sites (KMDW, KAUS, KATL, KSEA, etc.) are candidates for later migration or may already have been ported.
- **How IP delivery changes busy presentation (medium confidence):**
  1. **ATA/FXS port, call waiting disabled.** Second caller gets 486 → Twilio `busy`, as on POTS.
  2. **ATA or POTS-replacement with call waiting enabled.** Second caller gets 180 Ringing while the ASOS, which cannot flash, ignores the call-waiting tone. The caller rings until Twilio's timeout → `no-answer`. Some ATAs re-alert the port when the first call ends, so the waiting call could be answered after a long ring, creating a de facto one-deep queue. AT&T's Phone-Advanced lists call waiting as a feature. The user's report of busy on contention suggests call waiting is off on the lines they call.
  3. **Hosted PBX / SIP platform with several call paths per number but one FXS port.** The platform's own busy logic applies (486 or forward). Effective capacity is still one.
  4. **Gateway offline or LTE outage.** 480/408/503 → `no-answer`/`failed`, not `busy`.
  5. **Cellular POTS-replacement boxes.** Typically one voice call per analog port. Answer and release timing can be slower: on-hook → network release can take seconds over LTE signalling. Not measured.
- **Changing numbers is itself a diagnostic hazard (high confidence).** After re-provisioning, old ILEC numbers are disconnected or reassigned (e.g., AT&T: copper service "will stop working"). Code relying on stale numbers will see `failed`/404/410 or reach the wrong party.

### Gaps
- No FAA/NWS statement on the ASOS voice-line technology after migration (SIP trunk vs ATA vs LTE), its call-waiting configuration, or whether the FAA plans multi-caller capacity.
- Whether the ASOS 2.0 audio card or the AeroX Audio 105 supports more than one telephone caller is not documented (see the companion notes).
- The exact FCC 26-19 adoption date and effective dates were not extracted.

---

## 5. Line-sharing: is the voice dial-in line shared with modem, maintenance or NCEI functions?

### Takeaway
No evidence of sharing. ASOS documents describe the public voice dial-in as a separate interface from the remote-user/maintenance dial-in (modem) port and from the long-line circuit to the FAA (ADAS). AOMC, NWS technicians, the NWS "AUTODIAL" backup and NCEI's archive modem bank all dial the modem/remote port, not the voice number. A voice-line busy therefore indicates another voice caller, a call still alerting, or a release in progress, not data collection.

### Cited Findings
- **Separate interfaces.**
  - The telecommunications interfaces include "the FAA … ADAS, the NWS AWIPS, ASOS voice services (dial-in and very-high frequency radio), Navy air traffic control, and the FAA Weather Systems Processor."
  - "Remote access to ASOS is through dial in lines used primarily for remote monitoring, maintenance, and data archiving."
  - — [AMS 2009 ASOS sustainment paper](https://ams.confex.com/ams/pdfpapers/145078.pdf)
- **Remote-user port distinct from voice.**
  - "Authorized remote users (with modem-equipped computers and the proper access code/password) may also acquire … OID screen displays through the ASOS remote user dial-in port."
  - Voice is a separate output, the computer-generated voice "available through FAA radio broadcast to pilots, and general aviation dial-in telephone lines."
  - — [ASOS User's Guide](https://www.weather.gov/media/asos/aum-toc.pdf)
- **Backup data dial uses a separate line.** The NWS AUTODIAL system "will call up the ASOS at around 2 min after each hour if a METAR hasn't been received… this is using a separate line from the circuit that traditionally sends the observation to the FAA." AOMC "dialed into the site to pull a 12 hour archive." — [NTSB CEN19MA141 Attachment 1](https://data.ntsb.gov/Docket/Document/docBLOB?FileExtension=pdf&FileName=WX_CEN19MA141AB_Attachment_1_redacted-Rel.pdf&ID=8134624)
- **NCEI collects through a modem bank.** "ASOS 1-minute and 5-minute data … collected via NCEI's dial-in modem bank. The system dials out on an 11-hour cycle to approximately 960 ASOS stations." — [NCEI ATRAC record](https://www.ncei.noaa.gov/archive/atrac/export/2022-01-13T14-11-44.pdf?id=65639)
- **Remote-port security.** Remote dial-ins with no response are "counted as an attempt to deny service." — [ASOS v3.10 Release Notes](https://www.weather.gov/media/asos/ASOS%20Implementation/release_notes_310_final.pdf)

### Inferences
- **Not shared (high confidence for legacy ASOS; medium for post-migration sites).** The voice dial-in and the remote/maintenance modem line are separate physical or logical lines with separate numbers. NCEI's 11-hourly collection and AOMC maintenance sessions should not make the voice number busy.
- **The GTA radio does not consume the phone line (medium-high confidence).** It is a parallel audio output fed with the same message; the User's Guide says "The GTA and telephone messages are identical."
- **Re-provisioning risk (low-medium confidence).** If a migration put both the voice port and the modem port behind one POTS-replacement device or one SIP account, shared trunk or call-path limits could in principle couple them. No evidence either way.

### Gaps
- No site wiring diagram or Site Technical Manual extract was found that confirms voice-line and modem-line separation at every site, or describes the post-migration configuration.

---

## 6. Twilio specifics: status reporting, timeouts, repeat-calling limits, and automated/IVR destinations

### Takeaway
Twilio reflects only what the far end signals:
- 486/600 → `busy`, with Debugger 31486.
- No answer within `Timeout` (default 60 s for the REST API, 30 s for `<Dial>`, plus up to a 5 s buffer) → `no-answer`.
- Rejected calls can also show as `no-answer`.
- Carrier failures → `failed`.

Account-level controls also apply: 1 CPS by default for REST-created calls (up to 5 CPS with an approved Business Profile; excess calls are queued, not failed), concurrency limits (error 10004 / HTTP 429), Primary Customer Profile requirements for +1 calling on trunking, and fraud/high-risk destination blocking. No Twilio document found sets a "same destination number" call-rate limit for voice. Analytics blocking by downstream carriers surfaces as 603+ ("Network Blocked"). Calls answered by IVRs or automated systems are `completed` and billed like any answered call.

### Cited Findings
- **Statuses.** `queued`, `ringing`, `in-progress`, `canceled`, `completed`, `busy` ("The caller received a busy signal"), `no-answer` ("There was no answer or the call was rejected"), `failed` ("most likely because the provided number was invalid"). "A completed call indicates that a connection was established… answered by a person, an IVR phone tree menu, or even a voicemail. Completed calls, regardless of the outcome, are charged." — [Twilio Call resource](https://www.twilio.com/docs/voice/api/call-resource)
- **Timeout.** "The default is 60 seconds and the maximum is 600 seconds. For some call flows, we will add a 5-second buffer… a timeout value of 10 seconds could result in an actual timeout closer to 15 seconds." `<Dial>` default is 30 s. — [Twilio Call resource](https://www.twilio.com/docs/voice/api/call-resource); [Twilio Support: call statuses](https://support.twilio.com/hc/en-us/articles/223132547-What-are-the-possible-call-statuses-and-what-do-they-mean)
- **Answering machine detection.** `MachineDetectionTimeout` default 30 s; `AnsweredBy` can be `unknown`. If `SendDigits` is set, `MachineDetection` is ignored. — [Twilio Call resource](https://www.twilio.com/docs/voice/api/call-resource)
- **CPS.** "Calls are rate limited at the account level by Calls Per Second (CPS). Calls beyond your account's CPS limit will be queued and will execute at the CPS rate… By default, each account is granted one CPS… Accounts with an approved Business Profile … can update their CPS up to 5." — [Twilio Call resource](https://www.twilio.com/docs/voice/api/call-resource)
  - On Elastic SIP Trunking, exceeding CPS gives "a failed call with a SIP 503 Trunk CPS limit exceeded response." "Twilio will fail API requests with a 429 error if you exceed your concurrency limit." — [Twilio blog, High Volume Voice (2023)](https://www.twilio.com/en-us/blog/high-volume-voice-considerations)
- **Concurrency (error 10004).** "This error occurs when a new Voice call would exceed the number of active calls allowed on your account… Trial accounts and some upgraded accounts without an approved Primary Customer Profile have reduced concurrency." — [Twilio error 10004](https://www.twilio.com/docs/api/errors/10004)
- **Twilio-side blocking (error 32203, Elastic SIP Trunking).** "Twilio blocked this outbound Elastic SIP Trunking call before it reached the destination… when Twilio identifies the destination as high risk for fraud, cannot complete the call for regulatory reasons, or requires a valid Primary Customer Profile for calls to a +1 destination." — [Twilio error 32203](https://www.twilio.com/docs/api/errors/32203)
- **Downstream analytics blocking.** Twilio passes 603+ responses to SIP endpoints, and from 2026-04-23 the Reason header with redress URL (PCAP-visible). — [Twilio blog (2025-09-15)](https://www.twilio.com/en-us/blog/insights/fcc_new_standard); [Twilio changelog (2026-04-23)](https://www.twilio.com/en-us/changelog/elastic-sip-trunking---pass-on-603--reason-header-information-to)
- **Busy-detection limitations.** "Twilio can only reflect the signaling it receives from the carrier… Always check the CallStatus and 'Last SIP Response' for each call." — [Twilio Support](https://support.twilio.com/hc/en-us/articles/53558413407003-Detecting-When-a-Recipient-Is-Already-on-Another-Call-With-Twilio-Programmable-Voice)
- **Diagnostics fields.** `StatusCallbackEvent` (initiated/ringing/answered/completed), terminal `CallStatus` and `SipResponseCode` — [Twilio error 34003](https://www.twilio.com/docs/api/errors/34003). Voice Insights `last_sip_response_num`, `pdd_ms`, `disconnected_by` — [Voice Insights Call Summary](https://www.twilio.com/docs/voice/voice-insights/api/call/call-summary-resource)

### Inferences
- **The ~90 s cut (high confidence).** A connected call ending at about 90 s with `disconnected_by=callee` and Last SIP 200 is the ASOS's designed two-loop hang-up (FAA AWOS standard: disconnect after two complete transmissions). It is not a Twilio or carrier timeout. Twilio has no 90 s default.
- **Same-number repeat calling (medium confidence).** Twilio's documented limits are account-level (CPS, concurrency, profile and fraud checks), not per-destination. Repeated calls to one number are therefore most likely to be limited downstream: by the terminating provider's analytics (603+), or simply by the single-line busy condition itself. No Twilio voice doc on a per-destination rate cap was found. The SMS per-destination limits (e.g., 10DLC error 30022) do not apply to voice.
- **Automated or IVR destinations (high confidence).** Twilio treats an ASOS answer like any answered call: `completed`, billed, and subject to AMD heuristics if enabled. A continuous synthetic voice may classify as `machine_*` or `unknown`. Nothing in Twilio's docs is specific to automated weather lines.

### Gaps
- No Twilio documentation found on (a) a per-destination call-frequency limit for Programmable Voice, (b) the exact CallStatus mapping for 503 and 603/603+ in Programmable Voice (only Elastic SIP Trunking behaviour is documented), or (c) whether Programmable Voice exposes Q.850 causes or Reason headers outside PCAPs.
- Twilio Support's "Troubleshooting Twilio Programmable Voice Calls that Don't Connect" and the SIP 404/no-answer article returned HTTP 403 and were not read in full.

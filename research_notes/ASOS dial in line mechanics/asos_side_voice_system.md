# ASOS Station-Side Telephone Voice Dial-In System: How the Airport Equipment Answers, Repeats, Disconnects and Returns Busy

Scope: the hardware and software at a US ASOS site (NWS/FAA/DoD) that answers a call to the public ASOS voice number, speaks the observation, and hangs up. AWOS is used only for comparison. Research date: 2026-10-10.

Constraint observed throughout: this covers understanding only. It does not cover defeating the auto-disconnect, holding or monopolizing the line, winning seizure races, or accessing the password-protected remote-user/maintenance port.

Source dating, since several key sources are old:
- ASOS User's Guide: March 1998.
- S100 ASOS Site Technical Manual: AAI/Systems Management Inc.; the July 1998 edition supersedes May 1992.
- FAA Future Telecommunications Plan ("Fuchsia Book"): April 2000.
- ASOS v2.6A release note: Aug 2002.
- ASOS v3.10 release notes: May 2013.
- AMS papers: 2009 and 2017.
- FAA JO 7900.5E: page date 01/15/2020, with Change 1.
- FAA AC 150/5220-16E: 03/10/2017.
- Campbell AeroX Audio105 manual: Rev. 11/2025.
- Campbell ASOS case study: web 2026-01-12, PDF footer 04/23/2026.

---

## 1. Physical architecture: which units handle telephone voice, and how many public voice lines does an ASOS have?

### Takeaway
**Legacy ASOS (in service at all seven target stations per the 2025 equipment sheet) has exactly one public voice dial-in circuit.** The FAA's April 2000 telecommunications plan says each ASOS has three dial-up commercial circuits: two for remote maintenance/data access and one "dedicated to provide computer-generated voice weather messages to public users." It lists the PSTN interface as one channel.

The speech is produced inside the ACU's VME card rack:
- a "Voice Processor Board" (1A2A20);
- a "Voice Recorder/Playback Board" (1A2A21);
- telephone modems in a separate modem/line-driver rack.

The ASOS 2.0 replacement uses Campbell Scientific's AeroX Audio105. Its single RJ11 "VOICE MODEM" socket is wired for "Ring line 1 / Tip line 1" only. Both generations are therefore built for **one caller at a time per public number**.

### Cited Findings

**Voice output, legacy design (1998 documents)**
- ASOS voice reaches users through two outlets: the ground-to-air (GTA) radio, and "FAA sponsored telephone dial-in access" for "the general aviation public." The two messages are identical and spoken at "100 words per-minute." — [ASOS User's Guide (NWS, March 1998), §6.5, p. 54](https://www.weather.gov/media/asos/aum-toc.pdf)
- "Computer-generated voice messages are made available to local aviation users through ground-to-air broadcast and a dial-in telephone number provided at each ASOS location." The same passage separates this from the "ASOS remote user dial-in port" used by "authorized remote users (with modem-equipped computers and the proper access code/password)." — [ASOS User's Guide (1998), Ch. 2/7](https://www.weather.gov/media/asos/aum-toc.pdf)

**Legacy ACU hardware**
- The ACU VME card rack contains a "Voice Processor Board 1A2A20" and a "Voice Recorder/Playback Board 1A2A21." Both are field-replaceable VME cards with front-panel cables, alongside XVME-601 CPU boards and XVME-490 RS-232 SIO boards. — [S100 ASOS Site Technical Manual, Ch. 2 Sec. V "ACU Cabinet Maintenance" (AAI/SMI, 1990s; Scribd copy)](https://www.scribd.com/document/74787732/KXP)
- The ACU has a separate "modem rack" of "individual telephone modems." The continuous self-test (CST) "checks each of the individual telephone modems in the modem rack once every 7 minutes, as long as the modems are not busy (testing a busy modem would disrupt communication)." — [S100, Ch. 2 Sec. V](https://www.scribd.com/document/74787732/KXP)
- Phone-port faults are logged by name, e.g. "AFOS PHONE PORT DOWN." — [S100, Ch. 2 Sec. V](https://www.scribd.com/document/74787732/KXP)
- Bibliographic identity of S100: "Automated Surface Observing System: site technical manual, S 100 / AAI Systems Management Incorporated," ASOS Program Office, NOAA/NWS, [1998]; "supersedes S100 dated May 92." This is from the catalog record as summarized by search results; the record was not opened directly. — [East Carolina University library catalog](https://lib.ecu.edu/catalog-preview/catalog/959152)
- Legacy ACU subassemblies (2017 description):
  - "the VME card rack assembly, the modem AC power rack, the power supply assembly…";
  - the Single Cabinet ASOS has "the modem AC power rack and telephone modems";
  - the ASOS 2.0 work includes "the upgrade of the data and voice modems," and "the audio card in the computer and the new audio distribution amplifier will replace the voice and voice computer board."
  - — [Hays et al., AMS 2017, "Modernization of the ASOS Hardware and Software"](https://ams.confex.com/ams/97Annual/webprogram/Manuscript/Paper315698/AMS%20Modernization%20of%20ASOS%20Hardware%20and%20Software%20Paper_FINAL.pdf)
- The ACU's telecommunications interfaces include "ASOS voice services (dial-in and very-high frequency radio)." "Remote access to ASOS is through dial in lines used primarily for remote monitoring, maintenance, and data archiving." — [McNitt et al., AMS 2009 ASOS overview](https://ams.confex.com/ams/pdfpapers/145078.pdf)

**Line count (FAA, April 2000)**
- "Each ASOS has three dial-up commercial circuits. Two are used for remote maintenance monitoring functions and one is dedicated to provide computer-generated voice weather messages to public users. The AWOS uses a single dial-up circuit to provide both remote maintenance monitoring functions and a computer-generated voice weather message." — [FAA Future Telecommunications Plan "Fuchsia Book," AOP-400, April 2000, §7-02.3.1.2](https://rosap.ntl.bts.gov/view/dot/58105/dot_58105_DS1.pdf)
- Same document: "One dial-up line (used for both AWOS voice output and RMS) will be provided at each AWOS and three (one used for ASOS voice output and two for RMS and data access) at each ASOS location for user dial access." — [FAA Fuchsia Book (2000), §7-02.4.1.2](https://rosap.ntl.bts.gov/view/dot/58105/dot_58105_DS1.pdf)
- Table 7-02-1 (AWOS/ASOS-to-PSTN interface):
  - interface control document RS-496;
  - "No. Channels: 1";
  - service "Dial-up," full duplex, "Local" modem.
  - The PSTN cost line reads "1.2 kbps Dial-up Service via the PSTN (Service Coordinated and Billed by NWS)," with a note "(ASOS Billing transferred to FAA)," and about 2,171 total channels.
  - — [FAA Fuchsia Book (2000), Table 7-02-1 and Table 7-02-4](https://rosap.ntl.bts.gov/view/dot/58105/dot_58105_DS1.pdf)
- The FAA had procured and installed 567 ASOS and the NWS 315. About 400 of the 567 FAA ASOS had VHF radios. — [FAA Fuchsia Book (2000), §7-02.4](https://rosap.ntl.bts.gov/view/dot/58105/dot_58105_DS1.pdf)

**Separation of the maintenance/data lines from the voice line in practice**
- An NWS Alaska Region email in an NTSB docket (2019) says the NWS AUTODIAL backup "will call up the ASOS at around 2 min after each hour if a METAR hasn't been received… this is using a separate line from the circuit that traditionally sends the observation to the FAA."
- The same email says AOMC "dialed into the site to pull a 12 hour archive."
- — [NTSB docket CEN19MA141, Meteorology attachment](https://data.ntsb.gov/Docket/Document/docBLOB?FileExtension=pdf&FileName=WX_CEN19MA141AB_Attachment_1_redacted-Rel.pdf&ID=8134624)
- AOMC "can dial into an ASOS, check its status, and perform various maintenance functions without disturbing" operations. — [NWSI 30-2111 ASOS Maintenance](https://www.weather.gov/media/directives/030_pdfs/pd03021011curr.pdf)

**ASOS 2.0 voice hardware (AeroX Audio105)**
- The AeroX Audio105 is a 2U rack audio controller. It provides:
  - "Five external line return (XLR)/3.5 mm jack analog output channels";
  - "Five independent push-to-talk (PTT)… relay contacts";
  - "Voice modem included for voice broadcast via a telephone line (also known as Public Switched Telephone Network [PSTN])."
  - — [Campbell Scientific AeroX Audio 105 brochure](https://s.campbellsci.com/documents/us/product-brochures/b_aerox-audio105.pdf)
- Its "VOICE MODEM connector":
  - "This RJ11 connector provides a standard telephone line connection that supports voice and DTFM [sic] decoding as required by NOAA (contact factory). The voice modem is connected to COM4 of the single-board computer internally."
  - The pinout table for the VOICE modem socket lists only "Ring line 1" and "Tip line 1"; there is no second line.
  - "The AeroX Audio105 requires an Ethernet connection to an ASOS or AWOS server to control and generate the audio messages."
  - — [AeroX Audio105 Product Manual, Rev. 11/2025, §6.9, §6.12, Table 5-12](https://s.campbellsci.com/documents/us/manuals/aerox-audio105.pdf)
- Redundancy: "redundant operation requires two AeroX Audio105s per audio stream." The second box "will act as a redundant audio box that can take over the audio if the first box fails." — [AeroX Audio105 manual §6.13](https://s.campbellsci.com/documents/us/manuals/aerox-audio105.pdf); [AeroX Audio105 data sheet](https://s.campbellsci.com/documents/us/manuals/aerox-audio105-data-sheet.pdf)
- Campbell lists "AeroX Audio 105, SDM-SIO2R, CR1000X" as the products used in the US ASOS 2.0 (SLEP) program. — [Campbell Scientific case study](https://s.campbellsci.com/documents/us/case-studies/united-states-asos-weather-network.pdf)

**Field reports (anecdotal)**
- "Most of the ASOS/ATIS phone relays I've used are single lines. If someone else is listening, you just get a line busy tone." Seen only in a search-result snippet; the page was not fetchable. — [r/flying thread](https://www.reddit.com/r/flying/comments/1fmhdrn/can_awos_take_multiple_calls_at_a_time_or_am_i)
- "The only downside to using the phone number is that it will be busy sometimes...usually when a crazy front is coming through and there are a bunch of us all trying to see how strong the winds are at that exact second." — [Pilots of America (2016)](https://www.pilotsofamerica.com/community/threads/phone-number-for-atis.98234/)
- "Access Limitation: Often, only one call can access the ASOS line at a time." — [Wethr.net, Navigating Market Bots (updated Feb 2026)](https://wethr.net/edu/market-bots)

### Inferences
- **One public voice line per legacy ASOS, and so one caller at a time.** Confidence: high, about 85%.
  - Basis: the FAA 2000 plan's explicit three-circuit/one-voice-circuit design and "No. Channels: 1"; one published number per site; pilot and trader reports of busy tones.
  - Residual uncertainty: an airport, FAA or telco may have changed individual sites since 2000, for example with a hunt group or a voice-to-IP gateway. No document showing multi-line ASOS voice service was found.
- **Legacy signal chain, reconstructed:**
  1. The ACU CPU builds the message.
  2. The Voice Processor Board concatenates the pre-recorded "ASOS Voice Vocabulary" words (User's Guide Appendix D).
  3. The Voice Recorder/Playback Board (probably for manually recorded/appended voice remarks) feeds audio out.
  4. The audio goes to the GTA radio, and to the dedicated voice telephone interface ("voice modem") in the ACU modem rack, which connects to the single PSTN voice circuit.
  - Confidence: medium. The board names and the "voice modem" term are sourced; the exact signal path and which card handles ring detection and off-hook are not.
- **Remote maintenance, AOMC and NCEI calls go to different circuits than the public voice line** on legacy ASOS (two RMS/data lines plus one voice line). They should not be what makes the public voice number busy. Confidence: medium-high.
  - Contrast: on AWOS (single shared circuit, per the FAA 2000 plan), a maintenance session can make the public line busy.
- **ASOS 2.0 keeps one PSTN voice line per Audio105.** A redundant second Audio105 is hot standby for the same audio stream, not a second caller port. Confidence: medium-high, from the one-pair RJ11 pinout and the redundancy description.

### Gaps
- No public S100 "Theory of Operation" (Section IV) text was found that describes the voice processor or telephone interface: ring detection, off-hook control, number of telephone voice ports, or voice-modem model.
- The legacy ASOS voice-modem make/model and whether it is one port or multi-port were not found.
- Whether any specific site (e.g., the seven target stations) has more than one voice line, a hunt group, or a carrier-side IP conversion could not be determined from public sources. Only the local NWS ET, the regional ASOS focal point or the FAA telecom office would know.
- Whether ASOS 2.0 ACUs carry one or two Audio105 units, and whether multiple Audio105s are ever wired to separate phone lines, is undocumented.

---

## 2. What makes it return busy, and what does a second caller hear?

### Takeaway
With a single analog voice circuit, the central office (or the carrier's IP gateway) returns **busy** to any caller while the ASOS voice port is off-hook with another caller. Twilio records that as status `busy` ("The caller received a busy signal"). The documented and inferred causes of busy, in order of likelihood:
1. **Another caller is connected.** Busy demand peaks during fronts or storms per pilot reports; trader bots and relay services also call these lines.
2. **A stuck or failed voice port or telco fault** holding the line off-hook. This is inferred.
3. Possibly brief internal modem self-tests. This is speculative.

Nothing found indicates the ASOS deliberately rejects calls. Busy is a property of the one-line design.

### Cited Findings
- **One circuit dedicated to public voice per ASOS.** — [FAA Fuchsia Book (2000) §7-02.3.1.2](https://rosap.ntl.bts.gov/view/dot/58105/dot_58105_DS1.pdf)
- **Busy tone when someone else is listening; busy during weather events:**
  - "If someone else is listening, you just get a line busy tone." — [r/flying snippet](https://www.reddit.com/r/flying/comments/1fmhdrn/can_awos_take_multiple_calls_at_a_time_or_am_i)
  - Busy "usually when a crazy front is coming through." — [Pilots of America (2016)](https://www.pilotsofamerica.com/community/threads/phone-number-for-atis.98234/)
- **Third-party demand on the same lines:**
  - Wethr.net documents "OMO Bot[s]" that "automate calls to this system" and warns of "cities where OMO bots are known to be active." — [Wethr.net](https://wethr.net/edu/market-bots)
  - An open-source Polymarket dashboard ships an opt-in ASOS phone-reading agent, provisioned on "Twilio, Telnyx or similar," with a guardrail to "keep volume to a handful of short calls per day per city" because "these lines exist for pilots." — [testedmedia/polymarket-weather-command-center README](https://github.com/testedmedia/polymarket-weather-command-center)
  - A commercial relay patent includes explicit busy wait/retry handling for AWOS/ASOS numbers. — [US Patent 7,088,241](https://www.freepatentsonline.com/7088241.html)
- **Twilio status definitions:**
  - `busy`: "The caller received a busy signal."
  - `no-answer`: "There was no answer or the call was rejected."
  - `completed`: "The call was answered and has ended normally."
  - The ringing `Timeout` defaults to 60 s.
  - — [Twilio Call resource docs](https://www.twilio.com/docs/voice/api/call-resource)
- **Self-test detail.** The ASOS CST checks each telephone modem in the modem rack every 7 minutes "as long as the modems are not busy." — [S100, Ch. 2 Sec. V](https://www.scribd.com/document/74787732/KXP)
- **Telco faults are a known ASOS failure mode.** The NWS describes telco problems interrupting ASOS circuits, for example a 2019 PAKT case with an AOMC log entry "TELCO issue… no modem problems found." — [NTSB docket CEN19MA141](https://data.ntsb.gov/Docket/Document/docBLOB?FileExtension=pdf&FileName=WX_CEN19MA141AB_Attachment_1_redacted-Rel.pdf&ID=8134624)
- **Dead numbers exist.** "We've found many of the phone numbers no longer work, particularly for the smaller airports." — [Pilot Institute (2023)](https://pilotinstitute.com/atis-vs-awos-vs-asos/)
- **Voice-content outage tied to the LTO setting.** "When a COR is issued, if the ASOS/AWOS-C is set to broadcast the Last Transmitted Observation (LTO), the telephone broadcast will be unavailable until the next METAR/SPECI is issued. If… set to broadcast the One-Minute Observation (OMO), the telephone broadcast is not affected." — [FAA JO 7900.5E, ¶3.7 note](https://www.faa.gov/documentLibrary/media/Order/JO_7900.5E_with_Change_1.pdf)

### Inferences
- **What a second caller hears.** Busy, not ring-no-answer, on a plain single business line without hunting or call-forwarding. Confidence: high for legacy copper lines (standard PSTN behavior plus pilot reports).
  - If a site's line has been moved to a carrier VoIP/ATA, a second caller could instead get busy (most common), ring-no-answer, or an intercept, depending on carrier configuration. Confidence: low-medium; no site-specific data.
  - In Twilio terms, expect `busy` for the normal occupied case and `no-answer` if the voice port is dead and the line just rings.
- **The busy rate is not random.** It should rise with pilot demand (weather events, morning flight planning, top of hour) and with automated callers. With several bots per city (per Wethr), a single line can be occupied a large fraction of each minute. Confidence: medium.
- **Persistent busy at odd hours** is more consistent with a stuck off-hook port or telco fault than with demand. That would be an AOMC trouble report (aomc@noaa.gov, 800-242-8194), not something to work around. Confidence: medium.
- **The CST modem test is a low-confidence, unverified contributor** to brief busies. The S100 says tests are skipped when a modem is busy. It does not say whether the public voice-line interface is among the modems tested, or whether a test takes the line off-hook. Treat as speculation.
- **AOMC/NCEI/AUTODIAL calls should not make the public number busy on legacy ASOS** because they use different circuits (Section 1). On AWOS sites with a single shared line they could. Confidence: medium-high.

### Gaps
- No ASOS document describes call-progress behavior: whether the ASOS ever refuses calls, plays a busy or reorder tone itself, or has a "voice unavailable" mode that leaves the line ringing.
- No public measurement of busy rates on ASOS voice lines was found.
- No source says whether any ASOS voice lines have already been converted to VoIP by carriers (copper retirement), which could change second-caller behavior.

---

## 3. Answer, repeat and disconnect logic, and which behaviours are fixed versus site-configurable

### Takeaway
**No public ASOS document states the rings-to-answer, the repeat count, or a disconnect timer for the telephone voice port.** The only written federal standard is for non-federal AWOS (AC 150/5220-16E):
- answer "prior to completion of the second ring";
- put "the audio signal in progress" on line, so the caller joins mid-loop;
- loop with about 5 s between messages;
- "automatically disconnect when the weather observation has been completely transmitted twice";
- annual maintenance checks that the phone "answers on second ring… provides two complete messages and disconnects."

The user's observation (about 90 s, about two loops) fits that same "two complete transmissions" rule, so ASOS very likely implements equivalent logic. The only documented operator-configurable voice settings are:
- the message **type**: Last Transmitted Observation (METAR/SPECI) vs One-Minute Observation, set at the OID via CMD → VOICE → TYPE by ATC/observer;
- site-database voice files ("CMD VOICE/PASSW," "VOICE AIRPORT NAME");
- GTA radio items.

No documented setting for rings, repeat count or call timeout was found.

### Cited Findings

**AWOS standard (non-federal AWOS only; does not govern ASOS)**
- "As an option, the voice system may contain an automatic telephone answering device… The incoming call should be answered prior to completion of the second ring, and the audio signal in progress at the time the call is received should be placed on line. The voice subsystem should automatically disconnect when the weather observation has been completely transmitted twice. Typically, the telephone-answering device should have the capability to answer five calls at a time… The minimum requirement is that the system answers a single call." — [FAA AC 150/5220-16E (03/10/2017), ¶3.20.a(7)](https://www.faa.gov/documentLibrary/media/Advisory_Circular/AC_150_5220-16E.pdf)
- "The voice message should be output continuously with approximately a 5-second delay between the completion of one message and the beginning of the next." — [AC 150/5220-16E ¶3.20.a(2)](https://www.faa.gov/documentLibrary/media/Advisory_Circular/AC_150_5220-16E.pdf)
- "If the voice message is in process of output when the new AWOS observation is received, the output message should be completed without interruption. Voice transmission of the new AWOS observation should begin upon completion of the next delay time." — [AC 150/5220-16E ¶3.20.a(3)](https://www.faa.gov/documentLibrary/media/Advisory_Circular/AC_150_5220-16E.pdf)
- Periodic maintenance check: "(16) Telephone. Check to ensure it answers on second ring; is clear; provides two complete messages and disconnects; and verify aural/audio quality." — [AC 150/5220-16E, maintenance checklist](https://www.faa.gov/documentLibrary/media/Advisory_Circular/AC_150_5220-16E.pdf)
- "Failure to receive an update of certified sensor data for more than 5 minutes should result in the termination of the voice output." — [AC 150/5220-16E ¶3.20.a(6)](https://www.faa.gov/documentLibrary/media/Advisory_Circular/AC_150_5220-16E.pdf)

**ASOS documented voice controls**
- At towered airports "the air traffic controller has the option of selecting for the broadcast weather message either METARs… or OMOs. At non-towered locations, the broadcast weather message defaults to the OMO." — [ASOS User's Guide (1998) §6.5](https://www.weather.gov/media/asos/aum-toc.pdf)
- The telephone dial-in carries "Either OMO or last transmitted METAR/SPECI – Not both." — [ASOS User's Guide Figure 4](https://www.weather.gov/media/asos/aum-charts2.pdf)
- FAA procedure to change the ASOS broadcast:
  1. "On the ASOS Operator Interface Device (OID) Main Screen, Log in using the ATC user id and password."
  2. "In the EDIT Box… select CMD."
  3. "Then Select VOICE."
  4. "Then Select TYPE… (Last Transmitted Observation or One-Minute Observation)."
  - Also: "Unstaffed locations must always be set to broadcast the OMO data." "ASOS defaults to the One-Minute-Observation after a system reboot." During tower non-operation, facilities must "Ensure the one minute observation (OMO) data is broadcast on all automated weather system communications outlets."
  - — [FAA JO 7900.5E, Appendix H](https://www.faa.gov/documentLibrary/media/Order/JO_7900.5E_with_Change_1.pdf)
- Site configuration files the AOMC downloads to an ASOS include "CMD VOICE/PASSW" and "VOICE AIRPORT NAME," alongside "EXTERNAL COMM," "RS-232 COMM," "HARDWARE," etc. (setup screens). — [ASOS Release Note v2.6A (Aug 2002), Appendix Figure A8](https://www.weather.gov/media/asos/ASOS%20Implementation/relnoteprocup.pdf)
- The External Communications page has fields such as "BUSY ATTEMPT TIME: 1," "SEND REPLY TIME(SECS): 120," "ADAS TIMEOUT (SEC): 360," and AOMC phone numbers.
  - These are for ASOS's own data communications (ADAS/AOMC/stations), not the public voice port.
  - They show that telephony timing parameters exist in the site database, but none is documented for the voice line.
  - — [ASOS Release Note v2.6A, Figure A7](https://www.weather.gov/media/asos/ASOS%20Implementation/relnoteprocup.pdf)
- Software v3.10 voice-adjacent changes:
  - "GENERATE GTA RADIO TONE AT TECH LEVEL" (previously System Manager only);
  - a fix for "INACCURATE DATA BASING OF GTA FREQUENCIES."
  - No telephone-voice repeat/disconnect change is listed among the 58 new capabilities and 24 fixes.
  - — [ASOS v3.10 Release Notes (May 2013)](https://www.weather.gov/media/asos/ASOS%20Implementation/release_notes_310_final.pdf)
- The ASOS 2.0 Audio105 voice modem "supports voice and DTFM decoding as required by NOAA." — [AeroX Audio105 manual §6.9](https://s.campbellsci.com/documents/us/manuals/aerox-audio105.pdf)
- "The Microphone input is not usable in the NOAA/FAA configuration"; the HANDSET socket "Supports FAA handset." — [AeroX Audio105 manual](https://s.campbellsci.com/documents/us/manuals/aerox-audio105.pdf)

### Inferences
- **ASOS answers quickly and joins the caller to the running broadcast loop, then disconnects after two complete transmissions.**
  - Confidence: medium-high, about 70%, for "two complete transmissions" as the rule, versus a fixed timer.
  - Basis: the user's own observation of about two loops in about 90 s; the FAA's written AWOS standard and maintenance check; the FAA treating "AWOS/ASOS… as a single component from the telecommunications perspective" (Fuchsia Book §7-02.2.1); and the fact that the phone and GTA messages are the same continuous loop.
  - Rings-to-answer is likely about 1–2 rings. Confidence: low-medium; no ASOS source.
- **Distinguishing count-based from timer-based, by passive observation only.** In ordinary well-behaved calls (no extension attempts), log call duration against the spoken message length.
  - If duration tracks message length (longer when remarks or clouds are added), the rule is "N complete transmissions."
  - If duration is constant (about 90 s) regardless of content, it is a timer.
  - Also log whether audio starts mid-word, which shows "audio in progress placed on line."
  - This is purely diagnostic and changes nothing about how the line behaves.
- **Fixed vs configurable (best current classification):**

| Behaviour | Classification | Confidence | Basis |
|---|---|---|---|
| Number of public voice lines / simultaneous callers (1) | Fixed by site telecom design (one circuit) and hardware (one voice port; ASOS 2.0 one RJ11 pair) | High | FAA 2000 plan; Audio105 pinout |
| Busy to 2nd caller | Fixed by the telco/line (single line, no hunt) | High | Standard PSTN + reports |
| Message type (OMO vs last METAR/SPECI) | **Site-operational setting**: ATC/observer via OID CMD→VOICE→TYPE; unstaffed must be OMO; reboot defaults to OMO | High (documented) | JO 7900.5E App. H |
| Voice airport name, voice "password" file | Site database (AOMC-managed configuration files) | High that the files exist; content unknown | v2.6A release note |
| Manual voice remarks/NOTAMs appended | Operator input (OID keyboard remarks; handset recording) | Medium-high | User's Guide §6.5; Audio105 handset; S100 "Voice Recorder/Playback Board" |
| Rings before answer | Probably fixed in ACU software/voice-modem init | Low-medium | No ASOS source; AWOS standard = before 2nd ring |
| Repeat count / disconnect rule | Probably fixed in ACU software (no documented OID/site parameter) | Medium | Absent from release notes, JO 7900.5E and User's Guide; AWOS standard = twice |
| Speech rate (100 wpm) | Fixed in software | High (documented) | User's Guide |
| Gap between loops (~5 s) | Unknown for ASOS; AWOS standard ~5 s | Low | AC 150/5220-16E |

- **The DTMF decoding on the ASOS 2.0 voice line**, together with the legacy "CMD VOICE/PASSW" configuration file, suggests NOAA requires some authorized touch-tone function on the voice line. A plausible use is authorized recording or control of voice remarks. Confidence: low; inferred, not documented.
  - It is password-gated and not a public feature.
  - Public callers should not send DTMF tones on these lines.
  - This note does not explore it further, consistent with the constraint.
- **ASOS 2.0 call handling is now set by Campbell's AudioServer/WARS software, not legacy firmware**, so repeat count or timeout may become an adjustable parameter there. No public documentation confirms this. Confidence: low.

### Gaps
- No ASOS-specific statement of rings-to-answer, repeat count, inter-message gap, maximum call duration, or whether a call starts mid-message, in any public NWS/FAA document found. That includes the User's Guide, JO 7900.5E, the v2.6A, v2.79 and v3.10 release notes, NWSI 30-2111 and the AMS papers.
- The documents most likely to contain it are not public:
  - S100 Section IV (theory of operation);
  - the ASOS Software User's Manual (SMI 1998, cited in AMS 2017);
  - NWS EHB-11 ("not available to the general public" per the [ASOS FAQ](https://www.weather.gov/asos/FAQ.html));
  - the ASOS 2.0 WARS documentation.
- The full contents of the OID CMD → VOICE menu (beyond TYPE) were not found. GTA radio, voice remarks and a phone-specific setting may exist there.
- Twilio's own call-duration figure includes ring time. Without call logs, the 90 s cannot be split into ring time and audio time.

---

## 4. Message content and length: does two loops plausibly equal about 90 s?

### Takeaway
Yes. At the documented 100 words per minute, a typical OMO voice message of about 55–75 spoken words runs about 33–45 s. Two complete transmissions plus about one 5 s gap is about 70–95 s. If the caller joins mid-message (as the AWOS standard prescribes) and the partial message does not count, add 0–45 s. The observed figure of about 90 s fits a message of about 40–43 s (about 70 words) under a two-complete-plays rule. Messages with more cloud layers, present weather, lightning or density-altitude remarks, or tower-appended remarks will run longer, so call length should vary by tens of seconds if the rule is count-based.

### Cited Findings
- **Message structure and rate.**
  - "ASOS computer-generated voice observations are spoken at the rate of 100 words per-minute."
  - Each message "begins with an identification of the location, the phrase 'AUTOMATED WEATHER OBSERVATION' and the UTC (ZULU) time of the observation."
  - Each element has a verbal prefix (e.g., "temperature four dew point three").
  - Missing elements are spoken as "missing."
  - "After the altimeter setting information is given, the word 'remarks' is spoken," followed by automated remarks (variable visibility, density altitude when > 1,000 ft, lightning) and manually entered remarks.
  - — [ASOS User's Guide (1998) §6.5](https://www.weather.gov/media/asos/aum-toc.pdf)
- **Content.**
  - The voice message contains "the individual reported weather elements normally included in the METAR (except sea-level pressure)."
  - Wind direction is magnetic.
  - It does not say METAR vs SPECI.
  - — [ASOS User's Guide §6.5](https://www.weather.gov/media/asos/aum-toc.pdf)
- **Voice remarks examples:** "density altitude, two thousand five hundred… visibility variable between one and two… wind direction variable between two four zero and three one zero… observer ceiling estimated two thousand broken." — [CFI Notebook (secondary)](https://www.cfinotebook.net/notebook/air-traffic-control/terminal-broadcast-services-and-systems)
- **Tower-added content.** "Control tower personnel may add Notice to Airmen (NOTAM) or other information." — [ASOS Guide for Pilots](https://wpaflys.info/aviation_academy_files/Handouts/Weather/asosbook.pdf)
- **OMO timing inside the minute.** "When the time hits 00 seconds, the ASOS starts processing its memory of recently saved data. This processing ends promptly at 23 seconds after and various displays are updated, products disseminated." — [IEM ASOS precipitation note](https://mesonet.agron.iastate.edu/ASOS/precipnote.phtml)
- **The phone carries the 1-minute value even during the hourly lockout.** "This does not affect the 1-minute weather you receive by calling the voice phone link." — [Twin & Turbine (June 2011)](https://twinandturbine.com/issue/June11/files/basic-html/page22.html)
- **Some lines repeat the METAR instead.** "Some just repeat the latest metar though." — [Stormtrack (2008)](https://stormtrack.org/threads/asos-awos-update-frequency.12572/)
- **AWOS loop structure for comparison:** a continuous loop, about a 5 s gap, and no mid-message switch to new data. — [AC 150/5220-16E ¶3.20.a(2)-(3)](https://www.faa.gov/documentLibrary/media/Advisory_Circular/AC_150_5220-16E.pdf)

### Inferences
- **Worked example (illustrative wording, not a recorded ASOS message):** "[Airport name] automated weather observation, one eight five two zulu. Wind two seven zero at one two, gusts two zero. Visibility one zero. Sky condition few clouds four thousand five hundred, scattered two five thousand. Temperature two niner, dew point one six. Altimeter two niner niner two. Remarks, density altitude three thousand two hundred."
  - About 55–60 words, so about 33–36 s at 100 wpm.
  - Two plays plus a 5 s gap is about 71–77 s.
  - The airport name, extra layers, present weather and remarks plausibly add 5–25 words (3–15 s) per play.
  - A total of about 90 s is therefore well within range. Confidence: medium-high.
- **Implication for minute coverage.** A two-loop call spans about 1.5 minutes. If the voice loop picks up the new OMO only at a message boundary after about :23 s past the minute (by analogy with the AWOS no-interruption rule), one call will usually yield one or two distinct minute values, and sometimes a value is stale by up to one message length. Confidence: medium.
- **METAR mode makes calls minute-uninformative.** If a towered station is in LTO (METAR) mode, the spoken Zulu time stays at the METAR time. This is a site-operational choice, not a line fault. Confidence: high (documented options).

### Gaps
- No recorded ASOS audio with measured message lengths was found. The word counts here are estimates.
- Whether the ASOS voice loop has a fixed inter-message gap, and how fast a new OMO enters the loop (next boundary vs immediate), is undocumented for ASOS.

---

## 5. AWOS comparison: how AWOS phone service is specified, and does ASOS have anything comparable?

### Takeaway
For non-federal AWOS, FAA AC 150/5220-16E specifies:
- answer before the 2nd ring completes;
- join the caller to the audio in progress;
- disconnect after two complete transmissions;
- "typically" answer five calls at once, with a one-call minimum.

These are "should" (advisory) design standards, and the five-call capability depends on the owner provisioning multiple lines. FAA AWOS (per the 2000 plan) used **a single dial-up line shared between voice and remote maintenance**. ASOS instead got three lines, one dedicated to voice. Neither design documents multi-caller service, and no ASOS document mentions a multi-line or hunt-group capability.

### Cited Findings
- **AC 150/5220-16E ¶3.20.a(7)** (answer timing, audio in progress, disconnect after two transmissions, "typically… five calls at a time," "minimum requirement… a single call"). The AC applies to Non-Federal AWOS, including "telephone dial-up service." — [AC 150/5220-16E](https://www.faa.gov/documentLibrary/media/Advisory_Circular/AC_150_5220-16E.pdf)
- **Telephone answering is optional for AWOS.** The processor "should have the ability to provide a computer generated voice weather observation to a ground-to-air radio… As an option, this voice message may also be provided to users via an integral automatic telephone-answering device." — [AC 150/5220-16E ¶3.18](https://www.faa.gov/documentLibrary/media/Advisory_Circular/AC_150_5220-16E.pdf)
- **AWOS line sharing.** "The AWOS uses a single dial-up circuit to provide both remote maintenance monitoring functions and a computer-generated voice weather message." — [FAA Fuchsia Book (2000) §7-02.3.1.2](https://rosap.ntl.bts.gov/view/dot/58105/dot_58105_DS1.pdf)
- **Example procurement spec.** "The voice subsystem shall automatically disconnect when the weather observation has been completely transmitted twice"; messages "output continuously with approximately a 5 second delay"; the dial-up number "shall be provided by others." — [Illinois DOT AWOS bid spec](https://apps.dot.illinois.gov/eplan/desenv/042823/GR012-16A/GR012-16A.pdf)
- **Wikipedia summary of AWOS phone service.** "Optionally, a computer-generated voice message, available over a telephone dial-up modem service. The message is updated at least once per minute." — [Wikipedia, Automated airport weather station](https://en.wikipedia.org/wiki/Automated_airport_weather_station)

### Inferences
- **ASOS has no documented equivalent of the AWOS "five calls" capability.** Its public voice capacity is one call. The AWOS five-call figure is a "typical" vendor capability that still requires the airport to buy multiple lines. Confidence: high that ASOS has none documented; medium on actual AWOS field practice.
- **AWOS-C sites (the FAA's ASOS replacement at 207 sites, 2025–2029) are FAA-owned federal systems.** Their phone behavior would follow FAA AWOS-C specifications, not AC 150/5220-16E (non-federal). They will likely keep the same "two plays then disconnect" convention. Confidence: low-medium; no AWOS-C voice spec was found.

### Gaps
- Vendor AWOS voice-module specs (All Weather Inc., Vaisala, Optical Scientific/DBT, Mesotech) were not retrieved, so the actual multi-line capability of fielded AWOS was not verified.
- No FAA AWOS-C telephone-voice specification was found.
- No check was made on whether AC 150/5220-16E has been superseded by a later edition (16F) as of Oct 2026.

---

## 6. ASOS 2.0 / Campbell Scientific replacement ACU / AeroX Audio105 / AWOS-C / IP transition: any change in caller capacity or VoIP?

### Takeaway
ASOS 2.0 replaces the legacy voice boards with a computer audio card, an audio distribution amplifier and, per Campbell's product list, the AeroX Audio105. Its voice telephone interface is **one analog PSTN line (RJ11, Tip/Ring line 1) on an internal voice modem**, with no SIP/VoIP telephony interface; its only Ethernet port is for control by the ASOS server. Nothing published indicates more simultaneous callers. The program's separate "TDM to IP" goal ("replace all copper voice and data lines with IP communications" by end-2026) is about agency communications. No document says the public voice number will become multi-line or VoIP-native.

Deployment status:
- As of April 2026, Campbell said agencies were "conducting their final acceptance testing."
- NWS's equipment sheet (Mar 2025) has an empty ASOS 2.0 in-service tab.
- All seven target stations remained on legacy ACUs.

### Cited Findings
- **2017 ASOS 2.0 design paper:**
  - "the audio card in the [new] computer and the new audio distribution amplifier will replace the voice and voice computer board";
  - "the upgrade of the data and voice modems";
  - legacy modems for on-site interfaces kept "as upgrading them would require the replacement of the modems on the other end of the line too";
  - "In this first iteration the expanded data will not be available to a wider audience due to the continued use of dial up modems for external communications."
  - — [Hays et al., AMS 2017](https://ams.confex.com/ams/97Annual/webprogram/Manuscript/Paper315698/AMS%20Modernization%20of%20ASOS%20Hardware%20and%20Software%20Paper_FINAL.pdf)
- **AeroX Audio105 interfaces:**
  - one RJ11 VOICE MODEM socket ("Ring line 1," "Tip line 1"), "voice and DTFM decoding as required by NOAA," on COM4;
  - Ethernet "to an ASOS or AWOS server to control and generate the audio messages";
  - five analog audio outputs and five PTT relays (radios and tower audio);
  - an optional hot-standby redundant unit per audio stream.
  - — [AeroX Audio105 manual (Rev. 11/2025)](https://s.campbellsci.com/documents/us/manuals/aerox-audio105.pdf); [brochure](https://s.campbellsci.com/documents/us/product-brochures/b_aerox-audio105.pdf)
- **Campbell delivery and status.** Campbell delivered "700 acquisition control units (ACU), 799 data collection packages (DCP), and 50 single cabinet… (SCA)" for up to 750 sites; products used include "AeroX Audio 105." "At the time of this writing, the agencies are conducting their final acceptance testing." — [Campbell case study (web 2026-01-12; PDF 04/23/2026)](https://www.campbellsci.com/resources/case-studies/us-asos-weather-network); [PDF](https://s.campbellsci.com/documents/us/case-studies/united-states-asos-weather-network.pdf)
- **Program goals:** "By end of 2026: Design, validate and deploy all ACU/DCP/SCA Replacements (aka ASOS 2.0) – Replace all copper voice and data lines with Internet Protocol communications"; adds "IP communications – Ubiquitous access to OMO (goal)"; priority-1 "TDM to IP Upgrade." — [Boutin, FPAW 2023](https://fpaw.aero/sites/default/files/163/2-boutin-decadal-look-asos-lifecycle-upgrades.pdf)
- **2009 sustainment paper:** "Dial-in connections will not be required when ASOS is connected to an IP network." — [AMS 2009](https://ams.confex.com/ams/pdfpapers/145078.pdf)
- **Equipment status.**
  - "ASOS Sites by Equipment As Of 3_18_2025": the "ASOS 2.0 In Service Dates" tab is empty.
  - KNYC, KLAX, KMIA, KPHL and KDEN are NWS-owned; KMDW and KAUS are FAA-owned.
  - All seven are on legacy ACUs.
  - — [NWS ASOS equipment page](https://www.weather.gov/asos/asosequip.html); [spreadsheet](https://www.weather.gov/media/asos/ASOS%20Sites%20by%20Equipment%20As%20Of%203_18_2025.xlsx)
- **FAA AWOS-C transition.** "The NWS and FAA [are] transitioning 207 ASOS sites to AWOS-C… start date of 2025 and lasts through 2029." — [NWS ASOS FAQ](https://www.weather.gov/asos/FAQ.html)

### Inferences
- **The ACU swap alone will not add simultaneous callers.** At an ASOS 2.0 site, the public number will still terminate on one analog voice-modem port, so the one-caller and busy behavior should persist. Confidence: medium-high.
- **Copper-to-IP is likely to be done at the line level (carrier VoIP or ATA feeding the RJ11 port).** That keeps one call at a time unless the agencies deliberately provision more Audio105 voice ports or a different architecture. Confidence: medium. No plan for public-voice capacity was found.
- **Repeat/disconnect rules could change subtly on ASOS 2.0**, since call handling moves to new software and Campbell's AudioServer. NWS presumably specified parity with legacy behavior. Confidence: low-medium.
- **KMDW and KAUS (FAA-owned) are exposed to the AWOS-C transition**, which could change the phone number, the voice behavior and whether voice is OMO-based. The FAA's 207-site list was not found. Confidence on timing: unknown.

### Gaps
- No ASOS 2.0 site-by-site deployment schedule or Service Change Notice was found. Whether any ASOS 2.0 unit is in operational service as of Oct 2026 could not be confirmed.
- How many Audio105 units an ASOS 2.0 ACU contains, and how the public phone line is wired, was not found.
- No document on the future of the public voice numbers (kept, VoIP, multi-line, retired) under TDM-to-IP was found.
- No AWOS-C voice/telephone specification was found.

---

## 7. Which NWS/FAA documents describe the voice/telephone subsystem, and what is publicly available?

### Takeaway
The public record is thin, and most of it is old:
- the 1998 User's Guide covers content, rate and type options;
- one Scribd-hosted chapter of the 1990s S100 Site Technical Manual names the voice boards and modem rack;
- the FAA's 2000 Fuchsia Book gives the three-circuit, one-voice-line design;
- JO 7900.5E covers the OID voice-type procedure;
- release notes give configuration-file names;
- the 2017 AMS paper covers ASOS 2.0 voice hardware changes;
- the Campbell Audio105 manual (2025) gives the new one-line voice modem.

The documents that would answer rings, repeats and timers are not public: the S100 theory sections, the ASOS Software User's Manual, EHB-11, and the ASOS 2.0/WARS specifications.

### Cited Findings
- **ASOS User's Guide (March 1998):** voice content, 100 wpm, OMO vs METAR, one dial-in number per site, remote-user port separate. — [weather.gov](https://www.weather.gov/media/asos/aum-toc.pdf)
- **S100 Site Technical Manual, Ch. 2 Sec. V (1990s, Change 2 era):** Voice Processor Board 1A2A20, Voice Recorder/Playback Board 1A2A21, modem rack, CST modem tests every 7 min. — [Scribd](https://www.scribd.com/document/74787732/KXP)
- **FAA Fuchsia Book (April 2000) Ch. 7-02:** three dial-up circuits per ASOS, one for public voice; AWOS one shared circuit; PSTN interface one channel. — [ROSA P](https://rosap.ntl.bts.gov/view/dot/58105/dot_58105_DS1.pdf)
- **ASOS v2.6A Release Note (Aug 2002):** "CMD VOICE/PASSW" and "VOICE AIRPORT NAME" site files; External Communications page timing fields. — [weather.gov](https://www.weather.gov/media/asos/ASOS%20Implementation/relnoteprocup.pdf)
- **ASOS v3.10 Release Notes (May 2013):** GTA tone at tech level, GTA frequency fix, remote-port security; nothing on telephone repeat/disconnect. — [weather.gov](https://www.weather.gov/media/asos/ASOS%20Implementation/release_notes_310_final.pdf)
- **FAA JO 7900.5E (01/15/2020, with Change 1) Appendix H:** CMD → VOICE → TYPE procedure; unstaffed sites OMO; reboot defaults to OMO; COR/LTO note on telephone broadcast. — [faa.gov](https://www.faa.gov/documentLibrary/media/Order/JO_7900.5E_with_Change_1.pdf)
- **NWSI 30-2111 (ASOS maintenance):** AOMC remote dial-in for diagnostics; no voice-line parameters. — [weather.gov](https://www.weather.gov/media/directives/030_pdfs/pd03021011curr.pdf)
- **EHB-11:** "not available to the general public." — [NWS ASOS FAQ](https://www.weather.gov/asos/FAQ.html)
- **ASOS Software User's Manual (Systems Management Inc., 1998):** cited in the AMS 2017 reference list; not public. — [AMS 2017](https://ams.confex.com/ams/97Annual/webprogram/Manuscript/Paper315698/AMS%20Modernization%20of%20ASOS%20Hardware%20and%20Software%20Paper_FINAL.pdf)
- **Campbell AeroX Audio105 manual (Rev. 11/2025)** and data sheet: the new voice/phone module. — [Campbell](https://s.campbellsci.com/documents/us/manuals/aerox-audio105.pdf)

### Inferences
- **A definitive answer on rings, repeat count and timer needs one of three sources:** the S100 Section IV voice theory pages, the ASOS Software User's Manual, or a direct question to the NWS ASOS Program Office (suad.asos.pmo@noaa.gov) or a regional ASOS electronics technician. Confidence: high that these are the right sources.
- The FAA 2000 plan is the strongest public, primary evidence on line count. Even though it is 26 years old, the ASOS 2.0 papers say external dial-up interfaces were deliberately kept, so the count likely still holds at legacy sites. Confidence: medium-high.

### Gaps
- No FAA JO 6560-series ASOS maintenance order was located that mentions the voice line. NWS, not FAA, maintains ASOS.
- No FAA procurement or SIR document on sam.gov for ASOS voice/ACU replacement telephone requirements was retrieved.
- No ASOS Product Improvement Program document was found that mentions telephone voice changes.
- NWS EHB-11 and the full S100 were not accessible.
- An NWS Training Center ASOS Maintenance Course syllabus was seen in an earlier session's download, but its source URL could not be re-established, so it is not cited. It listed modules on "Ground to Air Radio" and "Codex MODEM for FAA ADAS System and FAA FTI," with no separate telephone-voice module.

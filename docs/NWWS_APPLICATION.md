# NWWS-OI Access — Application & Setup (ready to submit)

**Why this matters:** NWWS-OI posts NWS text products within **~10 seconds of issuance**
(NWS directive NWSPD 10-1701·5). That wins both of our races outright: the DSM slots
(current AFOS polling ≈ wire+1–2 min) and the six-hour-group cliff (dead at wire+3 min).

## How to apply (two routes, same info)

- **Form:** https://www.weather.gov/nwws/nwws_oi_request
- **Email:** NWWS.Issue@noaa.gov  (help: NWWS.help@noaa.gov)

Copy-paste body — fill the brackets:

```
Subject: NWWS-OI Account Request — Single Account

First Name:    [YOUR FIRST NAME]
Last Name:     [YOUR LAST NAME]
Company:       [YOUR NAME / LLC — individual use is authorized]
Address:       [STREET]
City:          [CITY]
State:         [STATE]
Zip:           [ZIP]
Telephone:     [PHONE]
Contact email: [EMAIL]
Account Info:  Single Account

Intended use: Automated real-time monitoring of routine surface observation
text products (METAR collectives and daily summary messages) for selected
ASOS stations, via a self-developed XMPP reader, for quantitative research.
```

Notes: general public use is explicitly authorized; processing can take **10+ days**
(longer on critical-weather days) — submit today. One user_ID works on ONE platform
at a time (a second connection gets denied); run the adapter on one host only.

## Connection parameters (current per weather.gov/nwws/OISetup)

| Setting | Value |
|---|---|
| Domain / server | nwws-oi.weather.gov |
| Port | **5222** (encryption required; legacy was 5223 old-SSL) |
| Resource | nwws |
| MUC room | NWWS @ conference.nwws-oi.weather.gov |
| Auth | your user_ID / password (case-sensitive) |

Each product arrives as one XMPP stanza with attributes: `cccc` (issuing office),
`ttaaii` (WMO header), **`awipsid` (AFOS PIL — e.g. DSMNYC)**, `issue` (ISO UTC),
and the raw product text in the payload. Filter on `awipsid`:
- DSMs: `DSMNYC DSMMDW DSMAUS DSMMIA DSMDEN DSMPHL DSMLAX`
- METARs: collectives with `ttaaii` beginning `SAUS`/`SXUS` containing our ICAOs
  (parse payload with the existing feeds.py regexes — T-groups, 1/2-groups).

Adapter: `nwws_adapter.py` (this package) — plugs the stream into the same
ProofEvent → KillEngine path; AFOS polling remains as automatic fallback.

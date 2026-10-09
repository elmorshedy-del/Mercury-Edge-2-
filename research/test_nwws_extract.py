"""Unit tests for trusted NOAA climate observations extracted from NWWS text."""
import os,sys,unittest
from datetime import datetime,timezone
sys.path.insert(0,os.path.dirname(__file__))
from nwws_extract import extract_evidence,tgftp_url
from nwws_tgftp import infer_issue_stamp,AWIPS_IDS
from nwws_oi_race import RaceRecorder
import tempfile,json


def event(awips,ttaa,raw,issue="2026-10-09T06:32:00Z"):
    return {"awipsid":awips,"ttaaii":ttaa,"raw":raw,
            "issue_utc":issue,"first_seen_utc":"2026-10-09T06:32:27.321Z",
            "product_type":awips[:3]}

NYC_DSM = """CXUS41 KOKX 082044
DSMNYC
KNYC DS 1500 08/10 731403/ 560600// 73/ 56//0014250/00/00/
"""
NYC_CLI = """CDUS41 KOKX 090632
CLINYC

CLIMATE REPORT
NATIONAL WEATHER SERVICE NEW YORK, NY
...THE CENTRAL PARK NY CLIMATE SUMMARY FOR OCTOBER 8 2026...

TEMPERATURE (F)
  YESTERDAY
   MAXIMUM         73    251 PM  87    2007  67      6       72
   MINIMUM         57    626 AM  37    1988  54      3       56
PRECIPITATION (IN)
  YESTERDAY        0.00
THE CENTRAL PARK NY CLIMATE NORMALS FOR TODAY
  MAXIMUM TEMPERATURE (F)   67
"""
DEN_CLI = """CDUS45 KBOU 091238
CLIDEN
CLIMATE REPORT
...THE DENVER CO CLIMATE SUMMARY FOR OCTOBER 9 2026...
TEMPERATURE (F)
  TODAY
   MAXIMUM         65  1005 AM  86 2002 72
   MINIMUM         50
PRECIPITATION (IN)
"""
NO_MAX = """CXUS41 KOKX 090530
DSMNYC
KNYC DS 08/10 M/M//M/M//M/M/
"""


class ClimateExtraction(unittest.TestCase):
    def test_dsm_same_day_read_max_and_clock(self):
        o=extract_evidence(event("DSMNYC","CXUS41",NYC_DSM,"2026-10-08T20:44:00Z"))
        self.assertEqual(o["reason"],"ok")
        self.assertEqual(o["report_key"],"CXUS41:KOKX:082044:DSMNYC")
        self.assertEqual(o["evidence"],[{"station":"KNYC","kind":"DSM",
            "climate_date":"2026-10-08","max_f":73,"max_time_lst":"1403"}])

    def test_cli_yesterday_uses_report_date_not_issue_date(self):
        o=extract_evidence(event("CLINYC","CDUS41",NYC_CLI))
        self.assertEqual(o["reason"],"ok")
        self.assertEqual(o["evidence"][0]["climate_date"],"2026-10-08")
        self.assertEqual(o["evidence"][0]["max_f"],73)

    def test_cli_today_accepted(self):
        o=extract_evidence(event("CLIDEN","CDUS45",DEN_CLI,"2026-10-09T12:38:00Z"))
        self.assertEqual(o["reason"],"ok")
        self.assertEqual(o["evidence"][0]["climate_date"],"2026-10-09")

    def test_cli_never_uses_normal_if_observed_missing(self):
        bad=NYC_CLI.replace("MAXIMUM         73","MAXIMUM         MM")
        self.assertEqual(extract_evidence(event("CLINYC","CDUS41",bad))["reason"],
                         "cli_observed_high_missing")

    def test_wrong_station_dsm_rejected(self):
        bad=NYC_DSM.replace("KNYC DS","KFPR DS")
        self.assertEqual(extract_evidence(event("DSMNYC","CXUS41",bad,"2026-10-08T20:44:00Z"))["reason"],
                         "station_row_missing")

    def test_wrong_wmo_rejected(self):
        o=extract_evidence(event("DSMNYC","CXUS42",NYC_DSM,"2026-10-08T20:44:00Z"))
        self.assertEqual(o["reason"],"wrong_wmo_or_awips_identity")

    def test_inconsistent_header_rejected(self):
        bad=NYC_CLI.replace("CDUS41 KOKX","CDUS41 KPHI")
        self.assertEqual(extract_evidence(event("CLINYC","CDUS41",bad))["reason"],
                         "wrong_wmo_or_awips_identity")

    def test_missing_dsm_high_rejected(self):
        self.assertEqual(extract_evidence(event("DSMNYC","CXUS41",NO_MAX,"2026-10-09T05:30:00Z"))["reason"],
                         "dsm_max_missing")

    def test_negative_dsm_max_supported(self):
        sample=NYC_DSM.replace("731403","051403")
        o=extract_evidence(event("DSMNYC","CXUS41",sample,"2026-10-08T20:44:00Z"))
        self.assertEqual(o["evidence"][0]["max_f"],5)

    def test_old_climate_bulletin_rejected(self):
        stale=NYC_DSM.replace("08/10","04/10")
        o=extract_evidence(event("DSMNYC","CXUS41",stale,"2026-10-09T20:44:00Z"))
        self.assertEqual(o["reason"],"dsm_date_stale_or_invalid")

    def test_tgftp_exact_path(self):
        self.assertEqual(tgftp_url("DSMNYC"),
            "https://tgftp.nws.noaa.gov/data/raw/cx/cxus41.kokx.dsmnyc.txt"
        ) if False else self.assertEqual(tgftp_url("DSMNYC"),
            "https://tgftp.nws.noaa.gov/data/raw/cx/cxus41.kokx.dsmnyc.txt")

    def test_wmo_month_and_year_boundary(self):
        dt=datetime(2027,1,1,0,2,tzinfo=timezone.utc)
        self.assertEqual(infer_issue_stamp("CXUS41 KOKX 312355\nDSMNYC",dt),
                         datetime(2026,12,31,23,55,tzinfo=timezone.utc))

    def test_exact_14_target_products(self):
        self.assertEqual(len(AWIPS_IDS),14)
        self.assertEqual(len(set(AWIPS_IDS)),14)

    def test_real_live_pair_measures_advantage(self):
        with tempfile.TemporaryDirectory() as folder:
            r=RaceRecorder(folder)
            a=extract_evidence(event("DSMNYC","CXUS41",NYC_DSM,
                                     "2026-10-08T20:44:00Z"))
            b=dict(a)
            a["first_seen_utc"]="2026-10-08T20:44:14.869Z"
            b["first_seen_utc"]="2026-10-08T20:44:47.000Z"
            r.observe_race("NWWS",a)
            r.observe_race("TGFTP",b)
            self.assertEqual(len(r.completed_pairs),1)
            import glob
            f=glob.glob(folder+"/nwws-tgftp-matches-*")
            self.assertEqual(len(f),1)
            with open(f[0]) as data:
                result=json.loads(data.read())
            self.assertEqual(result["fair_live_race"],True)
            self.assertAlmostEqual(result["delta_tgftp_minus_nwws_s"],32.131)
            self.assertTrue(result["same_max"])

    def test_initial_ftp_snapshot_not_counted_as_race(self):
        with tempfile.TemporaryDirectory() as folder:
            r=RaceRecorder(folder)
            a=extract_evidence(event("DSMNYC","CXUS41",NYC_DSM,
                                     "2026-10-08T20:44:00Z"))
            r.observe_race("TGFTP",a,bootstrap=True)
            b=dict(a)
            b["first_seen_utc"]="2026-10-09T02:00:00Z"
            r.observe_race("NWWS",b)
            import glob
            with open(glob.glob(folder+"/nwws-tgftp-matches-*")[0]) as f:
                result=json.loads(f.read())
            self.assertFalse(result["fair_live_race"])

    def test_prior_raw_archive_can_be_reprocessed(self):
        with tempfile.TemporaryDirectory() as folder:
            r=RaceRecorder(folder)
            source=event("CLINYC","CDUS41",NYC_CLI)
            source["product_type"]="CLI"
            with open(os.path.join(folder,"nwws-oi-first-seen-20261009.jsonl"),"w") as f:
                f.write(json.dumps(source)+"\n")
            r.backfill_archived_climate() # fails closed on corrupt/archive gaps

    def test_unrelated_product_is_not_evidence(self):
        o=extract_evidence(event("SYNBOU","NZUS99","KDEN 091153Z 15/02"))
        self.assertEqual(o["reason"],"not_target_climate_product")
        self.assertEqual(o["evidence"],[])


if __name__=="__main__":
    unittest.main()

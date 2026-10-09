"""Coverage for exact IEM/NWWS DSM races and regional station-only comparison."""
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime,timezone

sys.path.insert(0,os.path.dirname(__file__))
from nwws_iem import parse_response,_issue_time,_ALL
from nwws_oi_race import RaceRecorder
from nwws_extract import extract_evidence

NOW=datetime(2026,10,8,20,45,0,tzinfo=timezone.utc)
RAW="""999
CXUS41 KOKX 082044
DSMNYC
KNYC DS 1500 08/10 731451/ 561324// 73/ 56// 0/00/00/
"""
REGIONAL="""CXUS41 KOKX 082043
DSMZNY
KNYC DS 1500 08/10 731451/ 561324// 73/ 56// 0/00/00/
KPHL DS 1500 08/10 801328/ 601212// 80/ 60// 0/00/00/
"""
OLDER="""CXUS41 KOKX 082040
DSMNYC
KNYC DS 1500 08/10 701201/ 561324// 70/ 56// 0/00/00/
"""


class IEMRaceTests(unittest.TestCase):
    def test_full_wmo_bulletin_same_identity(self):
        reports=parse_response(RAW,"DSMNYC",NOW)
        self.assertEqual(len(reports),1)
        self.assertEqual(reports[0]["report_key"],"CXUS41:KOKX:082044:DSMNYC")
        self.assertEqual(reports[0]["evidence"][0]["max_f"],73)
        self.assertTrue(reports[0]["wire_identity_verified"])

    def test_regional_is_not_individual_product(self):
        reports=parse_response(REGIONAL,"DSMZNY",NOW)
        self.assertEqual(len(reports),2)
        self.assertEqual({r["station"] for r in reports},{"KNYC","KPHL"})
        self.assertTrue(all(r["report_key"] is None for r in reports))

    def test_wrong_pil_does_not_claim_bulletin(self):
        self.assertEqual(parse_response(RAW,"DSMZNY",NOW),[])

    def test_multiple_sections_cannot_borrow_wrong_header(self):
        combined=OLDER+RAW
        reports=parse_response(combined,"DSMNYC",NOW)
        self.assertEqual(len(reports),2)
        self.assertEqual([r["evidence"][0]["max_f"] for r in reports],[70,73])

    def test_issue_time_year_rollover(self):
        now=datetime(2027,1,1,0,2,tzinfo=timezone.utc)
        self.assertEqual(_issue_time("312355",now),
                         datetime(2026,12,31,23,55,tzinfo=timezone.utc))

    def test_all_target_pils_unique(self):
        self.assertEqual(len(set(_ALL)),len(_ALL))

    def test_exact_bulletin_win_vs_evidence_win_separate(self):
        with tempfile.TemporaryDirectory() as root:
            recorder=RaceRecorder(root)
            nws=extract_evidence({
                "awipsid":"DSMNYC","ttaaii":"CXUS41","raw":RAW,
                "issue_utc":"2026-10-08T20:44:00Z",
                "first_seen_utc":"2026-10-08T20:44:14Z",
                "product_type":"DSM",
            })
            iem=parse_response(REGIONAL,"DSMZNY",NOW)[0]
            recorder.observe_race("NWWS",nws)
            recorder.observe_race("IEM",iem)
            self.assertEqual(len(recorder.completed_pairs),0)
            self.assertEqual(len(recorder.evidence_pairs),1)
            import glob
            with open(glob.glob(root+"/nwws-multisource-races-*")[0]) as f:
                item=json.loads(f.readline())
            self.assertEqual(item["comparison"],"station_evidence")
            self.assertFalse(item["same_bulletin"])
            self.assertEqual(item["winner"],"NWWS")

    def test_identical_bulletin_uses_two_clocks(self):
        with tempfile.TemporaryDirectory() as root:
            recorder=RaceRecorder(root)
            nw=extract_evidence({
                "awipsid":"DSMNYC","ttaaii":"CXUS41","raw":RAW,
                "issue_utc":"2026-10-08T20:44:00Z",
                "first_seen_utc":"2026-10-08T20:44:14Z",
                "product_type":"DSM",
            })
            iem=parse_response(RAW,"DSMNYC",NOW)[0]
            recorder.observe_race("IEM",iem)
            recorder.observe_race("NWWS",nw)
            self.assertEqual(len(recorder.completed_pairs),1)
            self.assertEqual(len(recorder.evidence_pairs),1)
            import glob
            with open(glob.glob(root+"/nwws-multisource-races-*")[0]) as f:
                all_rows=[json.loads(l) for l in f]
            full=[row for row in all_rows if row["same_bulletin"]]
            self.assertEqual(len(full),1)
            self.assertEqual(full[0]["winner"],"NWWS")
            self.assertEqual(full[0]["delta_b_minus_a_s"],46.0)

    def test_bootstrap_does_not_win(self):
        with tempfile.TemporaryDirectory() as root:
            recorder=RaceRecorder(root)
            nw=extract_evidence({
                "awipsid":"DSMNYC","ttaaii":"CXUS41","raw":RAW,
                "issue_utc":"2026-10-08T20:44:00Z",
                "first_seen_utc":"2026-10-08T20:44:14Z",
                "product_type":"DSM",
            })
            iem=parse_response(RAW,"DSMNYC",NOW)[0]
            recorder.observe_race("IEM",iem,bootstrap=True)
            recorder.observe_race("NWWS",nw)
            import glob
            with open(glob.glob(root+"/nwws-multisource-races-*")[0]) as f:
                rows=[json.loads(l) for l in f]
            self.assertTrue(all(not r["fair_live_race"] for r in rows))

if __name__=="__main__":
    unittest.main()

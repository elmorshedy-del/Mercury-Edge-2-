"""Offline NWWS wire-record timestamp/classification tests. No secrets/network."""
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(__file__))
from nwws_oi_race import analyze_product, safe_report_time, RaceRecorder


class NWWSRecorderTests(unittest.TestCase):
    def setUp(self):
        self.t = datetime(2026, 10, 8, 20, 0, 21, tzinfo=timezone.utc)

    def test_station_metar_and_precise_t(self):
        raw = ("SAUS45 KBOU 082000\nMTRDEN\n"
               "KDEN 081953Z 00000KT 10SM CLR 28/01 A3013 RMK AO2 T02780006\n")
        event = analyze_product("MTRDEN", "SAUS45", raw, self.t,
                                "2026-10-08T20:00:03Z", "id-100")
        self.assertEqual(event["product_type"], "METAR_OR_SPECI")
        self.assertIn("KDEN", event["stations"])
        self.assertEqual(event["report_stamps"][0]["obs_utc"], "2026-10-08T19:53:00+00:00")
        self.assertEqual(event["report_stamps"][0]["precision_c"], 27.8)
        self.assertEqual(event["issue_lag_s"], 18.0)
        self.assertEqual(event["report_stamps"][0]["obs_age_s"], 441.0)

    def test_dsm_mapping_no_station_line(self):
        event = analyze_product("DSMLAX", "CXUS46",
                                "CXUS46 KLOX 082015\nDSMLAX\n",
                                self.t, "2026-10-08T20:00:10Z")
        self.assertEqual(event["product_type"], "DSM")
        self.assertEqual(event["stations"], ["KLAX"])

    def test_cli_mapping(self):
        event = analyze_product("CLIDEN","CDUS45",
                                "DENVER AREA CLIMATE REPORT",self.t)
        self.assertEqual(event["product_type"], "CLI")
        self.assertEqual(event["stations"], ["KDEN"])

    def test_omo_cannot_be_inferred_from_metar(self):
        event = analyze_product("MTRPHL","SAUS41",
                                "KPHL 081954Z 10SM CLR 27/15",self.t)
        self.assertEqual(event["product_type"], "METAR_OR_SPECI")
        self.assertNotEqual(event["product_type"], "OMO_CANDIDATE_UNVERIFIED")

    def test_unmatched_airport_not_recorded(self):
        with tempfile.TemporaryDirectory() as folder:
            recorder=RaceRecorder(folder)
            event=analyze_product("TOROKX","WFUS61",
                                  "Tornado warning Nassau County NY",self.t)
            recorder.write(event)
            self.assertEqual(recorder.matched,0)
            self.assertEqual(list(os.scandir(folder)),[])

    def test_deduplicate_identical_wire_payload(self):
        with tempfile.TemporaryDirectory() as folder:
            recorder=RaceRecorder(folder)
            event=analyze_product("CLIDEN","CDUS45",
                                  "KDEN climate today max 82",self.t)
            recorder.write(event)
            recorder.write(event)
            self.assertEqual(recorder.matched,1)
            files=os.listdir(folder)
            self.assertEqual(len(files),1)
            with open(os.path.join(folder,files[0])) as f:
                records=f.readlines()
            self.assertEqual(len(records),1)
            self.assertEqual(json.loads(records[0])["stations"], ["KDEN"])

    def test_year_boundary(self):
        t=datetime(2027,1,1,0,4,0,tzinfo=timezone.utc)
        obs=safe_report_time(31,23,53,t)
        self.assertEqual(obs,datetime(2026,12,31,23,53,tzinfo=timezone.utc))

    def test_invalid_future_observation(self):
        self.assertIsNone(safe_report_time(9,21,0,self.t))

    def test_unknown_aviation_product_no_false_station(self):
        event=analyze_product("MTRXXX","SAUS99",
                              "KORD 081955Z 28010KT 10SM CLR",self.t)
        self.assertEqual(event["stations"],[])
        self.assertEqual(event["report_stamps"],[])


if __name__ == "__main__":
    unittest.main()

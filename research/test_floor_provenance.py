"""Floor source = accepted record-setting evidence, never the METAR reference."""
import os,sys,unittest
from datetime import date,datetime,timezone
sys.path.insert(0,os.path.join(os.path.dirname(os.path.dirname(__file__)),"engine"))
from feeds import ProofEvent
from strategy import CityState,KillEngine

DAY=date(2026,10,9)
SEEN=datetime(2026,10,9,20,44,14,tzinfo=timezone.utc)


def ev(level,channel,source):
    return ProofEvent("KNYC",DAY,level,channel,SEEN,SEEN,
                      detail=source,source=source)


class FloorProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.engine=KillEngine({
            "channels":["metar","dsm","cli","omo_floor","sixhr"],
            "fat_finger_guard_f":7,
        })
        self.state=CityState("KNYC","KXHIGHNY")
        self.empty_buckets=[]
        self.quote=lambda _: (None,None)

    def process(self,level,channel,source):
        return self.engine.on_proof(self.state,ev(level,channel,source),
                                    self.empty_buckets,self.quote)

    def test_nwws_dsm_replaces_lower_metar_floor(self):
        self.process(78,"metar","tgftp")
        self.process(81,"dsm","nwws-oi")
        p=self.state.floor_proof[DAY]
        self.assertEqual(self.state.proven_max[DAY],81)
        self.assertEqual((p["source"],p["channel"],p["level_f"]),
                         ("nwws-oi","dsm",81))
        self.assertEqual(self.state.metar_max[DAY],78)

    def test_later_equal_lower_proofs_do_not_relabel_floor(self):
        self.process(78,"metar","tgftp")
        self.process(81,"dsm","nwws-oi")
        self.process(80,"omo_floor","minutetemp-ws")
        self.process(81,"metar","awc")
        self.assertEqual(self.state.floor_proof[DAY]["source"],"nwws-oi")
        self.assertEqual(self.state.floor_proof[DAY]["channel"],"dsm")

    def test_minutetemp_floor_relabels_when_it_raises_max(self):
        self.process(79,"metar","tgftp")
        self.process(80,"dsm","nwws-oi")
        self.process(82,"omo_floor","minutetemp-ws")
        self.assertEqual(self.state.floor_proof[DAY]["source"],"minutetemp-ws")
        self.assertEqual(self.state.floor_proof[DAY]["channel"],"omo_floor")

    def test_guarded_outlier_never_becomes_floor_source(self):
        self.process(78,"metar","tgftp")
        self.process(100,"dsm","nwws-oi")
        self.assertEqual(self.state.proven_max[DAY],78)
        self.assertEqual(self.state.floor_proof[DAY]["source"],"tgftp")

    def test_madis_floors_share_same_channel(self):
        self.process(75,"omo_floor","madis-hf")
        self.assertEqual(self.state.floor_proof[DAY]["source"],"madis-hf")
        self.assertEqual(self.state.floor_proof[DAY]["channel"],"omo_floor")

    def test_floor_timestamp_and_serialization(self):
        import json
        self.process(81,"dsm","nwws-oi")
        p=self.state.floor_proof[DAY]
        self.assertTrue(p["seen_ts"].startswith("2026-10-09T20:44:14"))
        self.assertEqual(json.loads(json.dumps(p))["level_f"],81)

if __name__=="__main__":
    unittest.main()

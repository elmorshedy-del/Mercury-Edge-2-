"""Security and source-agnostic elimination regressions: no network/secrets."""
import json
import os
import sys
import unittest
from datetime import datetime,timedelta,timezone

ROOT=os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0,os.path.join(ROOT,"engine"))
from proof_bridge import InvalidProof,signature,verify_and_decode
from feeds import ProofEvent
from minutetemp import decode_latest, MinuteTempStream
from strategy import KillEngine,CityState
from market import Bucket

NOW=datetime(2026,10,9,20,45,tzinfo=timezone.utc)
SHARED="test-"+"F"*62
OFFSETS={"KNYC":-5,"KPHL":-5,"KLAX":-8}
DS_PROOF={
    "source":"nwws-oi","kind":"DSM","station":"KNYC",
    "awipsid":"DSMNYC","report_key":"CXUS41:KOKX:092044:DSMNYC",
    "climate_date":"2026-10-09","max_f":81,"max_time_lst":"1451",
    "first_seen_utc":"2026-10-09T20:44:14Z",
    "issue_utc":"2026-10-09T20:44:00Z",
}


def signed(data,secret=SHARED):
    raw=json.dumps(data,sort_keys=True,separators=(",",":")).encode()
    ts=str(int(NOW.timestamp()))
    return raw,{"x-nwws-time":ts,
                "x-nwws-signature":signature(secret,ts,raw)}


class SourceProofTests(unittest.TestCase):
    def test_signed_dsm_maps_into_normalized_channel(self):
        raw,headers=signed(DS_PROOF)
        proof=verify_and_decode(raw,headers,SHARED,OFFSETS,now=NOW)
        self.assertEqual(proof.station,"KNYC")
        self.assertEqual(proof.channel,"dsm")
        self.assertEqual(proof.level_f,81)
        self.assertEqual(proof.source,"nwws-oi")

    def test_bad_signature_rejected(self):
        raw,headers=signed(DS_PROOF,secret="bad"+"x"*40)
        with self.assertRaises(InvalidProof):
            verify_and_decode(raw,headers,SHARED,OFFSETS,now=NOW)

    def test_stale_delivery_rejected(self):
        data=dict(DS_PROOF,first_seen_utc="2026-10-09T20:00:00Z")
        raw,h=signed(data)
        with self.assertRaisesRegex(InvalidProof,"report_not_fresh"):
            verify_and_decode(raw,h,SHARED,OFFSETS,now=NOW)

    def test_future_and_wrong_climate_date_rejected(self):
        data=dict(DS_PROOF,climate_date="2026-10-08")
        raw,h=signed(data)
        with self.assertRaisesRegex(InvalidProof,"not_current_climate_date"):
            verify_and_decode(raw,h,SHARED,OFFSETS,now=NOW)

    def test_wrong_station_rejected(self):
        data=dict(DS_PROOF,station="KORD")
        raw,h=signed(data)
        with self.assertRaisesRegex(InvalidProof,"station_not_configured"):
            verify_and_decode(raw,h,SHARED,OFFSETS,now=NOW)

    def test_bad_temperature_rejected(self):
        for value in (True,80.5,160,-55,"82"):
            with self.subTest(value=value):
                raw,h=signed(dict(DS_PROOF,max_f=value))
                with self.assertRaises(InvalidProof):
                    verify_and_decode(raw,h,SHARED,OFFSETS,now=NOW)

    def test_untrusted_raw_metar_cannot_ride_bridge(self):
        raw,h=signed(dict(DS_PROOF,kind="METAR",awipsid="MTRNYC"))
        with self.assertRaisesRegex(InvalidProof,"unsupported_channel"):
            verify_and_decode(raw,h,SHARED,OFFSETS,now=NOW)

    def test_cli_yesterday_must_not_eliminate(self):
        data=dict(DS_PROOF,kind="CLI",awipsid="CLINYC",
                  report_key="CDUS41:KOKX:092044:CLINYC",
                  max_time_lst=None,climate_date="2026-10-08")
        raw,h=signed(data)
        with self.assertRaises(InvalidProof):
            verify_and_decode(raw,h,SHARED,OFFSETS,now=NOW)

    def test_minutetemp_rest_is_same_omo_channel_as_madis(self):
        obs=NOW-timedelta(seconds=75)
        raw={"data":{"observation":{
            "station_id":"KPHL","observation_time":obs.isoformat(),
            "temp_min_f":77.9,"temperature_f":78.2
        }}}
        event=decode_latest(raw,"KPHL",-5,NOW)
        self.assertIsNotNone(event)
        self.assertEqual((event.level_f,event.channel,event.source),
                         (77,"omo_floor","minutetemp-rest"))
        madis=ProofEvent("KPHL",event.climate_date,77,"omo_floor",
                         obs,NOW,"madis-hf 25C wire","madis-hf")
        self.assertEqual((event.station,event.climate_date,event.channel,event.level_f),
                         (madis.station,madis.climate_date,madis.channel,madis.level_f))

    def test_minutetemp_ws_also_omo_and_not_vendor_specific(self):
        import queue
        import threading
        q=queue.Queue(maxsize=5)
        stream=MinuteTempStream("unused",{"KPHL":-5},q,threading.Event())
        payload={
            "type":"observation","station_id":"KPHL",
            "observation_time":datetime.now(timezone.utc).isoformat(),
            "temp_min_f":79.4,"temperature_f":79.6,
        }
        stream._on_message(json.dumps(payload))
        ev=q.get_nowait()
        self.assertEqual(ev.channel,"omo_floor")
        self.assertEqual(ev.source,"minutetemp-ws")
        self.assertEqual(ev.level_f,79)

    def test_engine_never_branches_on_provider(self):
        day=NOW.date()
        b=Bucket(ticker="EXAMPLE-YES",floor=75,cap=80,kind="bin",
                 subtitle="76-79 F")
        engine=KillEngine({"channels":["omo_floor","dsm","cli","metar"]})
        def make(src,level):
            return ProofEvent("KNYC",day,level,"omo_floor",NOW,NOW,src,src)
        for name in ("madis-hf","minutetemp-rest","minutetemp-ws"):
            with self.subTest(source=name):
                state=CityState("KNYC","KXHIGHNY")
                acts=engine.on_proof(state,make(name,81),[b],lambda _: (25,60))
                self.assertEqual(len(acts),1)
                self.assertEqual(state.proven_max[day],81)
                self.assertEqual(acts[0].proof.source,name)

    def test_faster_provider_advances_same_ratchet(self):
        day=NOW.date()
        engine=KillEngine({"channels":["omo_floor","dsm"]})
        state=CityState("KNYC","KXHIGHNY")
        bucket=Bucket("TEST",75,80,"bin","76-80")
        madis=ProofEvent("KNYC",day,78,"omo_floor",NOW,NOW,"madis-hf","madis-hf")
        faster=ProofEvent("KNYC",day,81,"omo_floor",NOW,NOW,"minutetemp-ws","minutetemp-ws")
        engine.on_proof(state,madis,[bucket],lambda _: (20,30))
        intents=engine.on_proof(state,faster,[bucket],lambda _: (20,30))
        self.assertEqual(state.proven_max[day],81)
        self.assertEqual(len(intents),1)

if __name__=="__main__":
    unittest.main()

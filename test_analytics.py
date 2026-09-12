import unittest
from analytics import build_analytics

DATA = {"games": [
 {"game_id":"G1","opponent":"Idaho","home_away":"HOME","conference_game":True,"official_penalties":{"Montana":7,"Idaho":3},"official_yards":{"Montana":72,"Idaho":30},"crew":{"Referee":"Jeff Rink"},"replay":{"events":0}},
 {"game_id":"G2","opponent":"Drake","home_away":"HOME","conference_game":False,"official_penalties":{"Montana":16,"Drake":6},"official_yards":{"Montana":138,"Drake":30},"crew":{"Referee":"Mike Bezner"},"replay":{"events":2,"overturned":1,"upheld":1}},
 {"game_id":"G3","opponent":"Idaho State","home_away":"AWAY","conference_game":True,"official_penalties":{"Montana":4,"Idaho State":3},"official_yards":{"Montana":52,"Idaho State":25},"crew":{"Referee":"Mike Bezner"},"replay":{"events":0}}
]}

class AnalyticsTests(unittest.TestCase):
 def test_totals(self):
  s=build_analytics(DATA)["overview"]["sample"]
  self.assertEqual(s["games"],3); self.assertEqual(s["montana_penalties"],27); self.assertEqual(s["montana_yards"],262)
  self.assertEqual(s["opponent_penalties"],12); self.assertEqual(s["opponent_yards"],85); self.assertEqual(s["yard_differential"],177)
 def test_splits(self):
  r=build_analytics(DATA)["splits"]
  self.assertEqual(r["home_away"]["home"]["games"],2); self.assertEqual(r["home_away"]["away"]["games"],1)
  self.assertEqual(r["conference"]["conference"]["games"],2); self.assertEqual(r["conference"]["nonconference"]["games"],1)
 def test_crew(self):
  rows=build_analytics(DATA)["crew_history"]; b=next(x for x in rows if x["referee"]=="Mike Bezner")
  self.assertEqual(b["games"],2); self.assertEqual(b["montana_yards"],190); self.assertEqual(b["opponent_yards"],55)
 def test_replay(self):
  r=build_analytics(DATA)["replay"]; self.assertEqual(r["reviews"],2); self.assertEqual(r["overturned"],1); self.assertEqual(r["upheld"],1)

if __name__ == "__main__": unittest.main()

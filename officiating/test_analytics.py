import unittest

from analytics import build_analytics


DATA = {
    "games": [
        {
            "game_id": "G1", "opponent": "Idaho", "home_away": "HOME", "conference_game": True,
            "official_penalties": {"Montana": 7, "Idaho": 3},
            "official_yards": {"Montana": 72, "Idaho": 30},
            "crew": {"Referee": "Jeff Rink"},
            "replay": {"events": 0}, "event_status": "REVIEW_REQUIRED",
        },
        {
            "game_id": "G2", "opponent": "Drake", "home_away": "HOME", "conference_game": False,
            "official_penalties": {"Montana": 16, "Drake": 6},
            "official_yards": {"Montana": 138, "Drake": 30},
            "crew": {"Referee": "Mike Bezner"},
            "replay": {"events": 2, "overturned": 1, "upheld": 1, "stands": 0},
            "event_status": "EVENT_LEVEL_YARDAGE_REVIEW",
        },
        {
            "game_id": "G3", "opponent": "Idaho State", "home_away": "AWAY", "conference_game": True,
            "official_penalties": {"Montana": 4, "Idaho State": 3},
            "official_yards": {"Montana": 52, "Idaho State": 25},
            "crew": {"Referee": "Mike Bezner"},
            "replay": {"events": 0}, "event_status": "SOURCE_RECONCILIATION_REQUIRED",
        },
    ]
}


class AnalyticsTests(unittest.TestCase):
    def test_overview_totals(self):
        result = build_analytics(DATA)
        sample = result["overview"]["sample"]
        self.assertEqual(sample["games"], 3)
        self.assertEqual(sample["montana_penalties"], 27)
        self.assertEqual(sample["montana_yards"], 262)
        self.assertEqual(sample["opponent_penalties"], 12)
        self.assertEqual(sample["opponent_yards"], 85)
        self.assertEqual(sample["yard_differential"], 177)

    def test_controlled_splits(self):
        result = build_analytics(DATA)
        self.assertEqual(result["splits"]["home_away"]["home"]["games"], 2)
        self.assertEqual(result["splits"]["home_away"]["away"]["games"], 1)
        self.assertEqual(result["splits"]["conference"]["conference"]["games"], 2)
        self.assertEqual(result["splits"]["conference"]["nonconference"]["games"], 1)

    def test_crew_history(self):
        rows = build_analytics(DATA)["crew_history"]
        bezner = next(row for row in rows if row["referee"] == "Mike Bezner")
        self.assertEqual(bezner["games"], 2)
        self.assertEqual(bezner["montana_yards"], 190)
        self.assertEqual(bezner["opponent_yards"], 55)

    def test_replay_and_publication(self):
        result = build_analytics(DATA)
        self.assertEqual(result["replay"]["reviews"], 2)
        self.assertEqual(result["replay"]["overturned"], 1)
        self.assertEqual(result["replay"]["upheld"], 1)
        self.assertEqual(result["publication"]["ready"], 0)
        self.assertFalse(result["publication"]["all_event_records_publishable"])


if __name__ == "__main__":
    unittest.main()

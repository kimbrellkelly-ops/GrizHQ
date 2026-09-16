"""Validate that the scoreboard inputs are present. Browser rendering fetches ESPN live events."""
import json
from pathlib import Path

data=json.loads(Path("data.json").read_text())
rankings=data.get("fcs_top25") or data.get("fcs_top20") or []
assert len(rankings) >= 25, f"Expected 25 FCS rankings, found {len(rankings)}"
assert len({str(x.get("team") or x.get("name")) for x in rankings[:25]}) == 25, "Duplicate ranked teams"
print(f"Validated {len(rankings[:25])} ranked FCS teams")

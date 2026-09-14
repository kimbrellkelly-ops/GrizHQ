import json
import sys
from pathlib import Path

DATA = Path("data.json")
REQUIRED = ("passing", "rushing", "receiving", "tackles", "pressure", "special")


def main():
    """Fail closed; never restore stale player statistics.

    The previous version contained a hard-coded fallback snapshot. That meant
    an empty/failed scrape silently republished old leaders, making the site
    appear unchanged. A refresh must either publish freshly parsed official
    leaders or stop before committing data.json.
    """
    obj = json.loads(DATA.read_text(encoding="utf-8"))
    leaders = obj.get("stats", {}).get("leaders", {})
    missing = [name for name in REQUIRED if not isinstance(leaders.get(name), list) or not leaders.get(name)]

    if missing:
        print("ERROR: official player-stat refresh produced empty categories: " + ", ".join(missing))
        print("No stale fallback data will be restored.")
        sys.exit(1)

    print("Stats safety check passed: all player leader categories are populated from the refresh.")


if __name__ == "__main__":
    main()

import json
from pathlib import Path

PATH = Path("data.json")


def main():
    """Repair only the Utah Tech game-log row when needed.

    Do not hard-code cumulative team or player statistics here. Those values
    must come from update_data.py / refresh_player_stats.py so future games can
    update them automatically instead of being overwritten by stale numbers.
    """
    data = json.loads(PATH.read_text(encoding="utf-8"))
    stats = data.setdefault("stats", {})
    game_log = stats.setdefault("game_log", [])

    utah = {
        "week": "Wk 3",
        "opponent": "Utah Tech",
        "result": "W 35-14",
        "montana_yards": 462,
        "opponent_yards": 405,
        "turnovers": "0",
        "notes": "Gillman 147 rushing / 3 TD; Davis 12 rec / 151 yards",
    }

    for item in game_log:
        if str(item.get("opponent", "")).strip().lower() == "utah tech":
            item.update(utah)
            break
    else:
        game_log.append(utah)

    def week_number(item):
        try:
            return int(str(item.get("week", "Wk 99")).split()[-1])
        except Exception:
            return 99

    game_log.sort(key=week_number)
    stats["through"] = f"Through {len([g for g in game_log if g.get('result')])} completed games"

    PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Game-log repair completed; cumulative player stats were preserved.")


if __name__ == "__main__":
    main()

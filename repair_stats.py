import json
from pathlib import Path

PATH = Path("data.json")

def main():
    data = json.loads(PATH.read_text(encoding="utf-8"))
    stats = data.setdefault("stats", {})
    game_log = stats.setdefault("game_log", [])

    # The official result is sometimes posted before the schedule page exposes
    # a completed result to the scraper. Keep this repair idempotent.
    utah = {
        "week": "Wk 3",
        "opponent": "Utah Tech",
        "result": "W 35-14",
        "montana_yards": 462,
        "opponent_yards": 405,
        "turnovers": "0",
        "notes": "Gillman 147 rushing / 3 TD; Davis 12 rec / 151 yards"
    }

    found = False
    for item in game_log:
        if str(item.get("opponent", "")).strip().lower() == "utah tech":
            item.update(utah)
            found = True
            break
    if not found:
        game_log.append(utah)

    # Keep the game log in chronological order when week labels are present.
    game_log.sort(key=lambda item: int(str(item.get("week", "Wk 99")).split()[-1]))

    completed = [g for g in game_log if g.get("result")]
    stats["through"] = f"Through {len(completed)} completed games"

    # Update the clearly derived team summary values without overwriting the
    # more detailed player-stat tables until their official cumulative source
    # is available.
    summary = stats.setdefault("team_summary", [])
    values = {
        "RECORD": "3–0",
        "POINTS / GAME": "36.0",
        "TOTAL OFFENSE": "429",
        "TOTAL DEFENSE": "404"
    }
    for row in summary:
        label = str(row.get("label", "")).upper()
        if label in values:
            row["value"] = values[label]

    offense = stats.setdefault("offense", [])
    defense = stats.setdefault("defense", [])
    replacements = {
        "Points": "108",
        "Total Yards": "1288",
        "Passing": "793",
        "Rushing": "495"
    }
    for row in offense:
        if row and row[0] in replacements:
            row[1] = replacements[row[0]]
    for row in defense:
        if row and row[0] == "Points Allowed":
            row[1] = "45"
        elif row and row[0] == "Yards Allowed":
            row[1] = "1212"

    PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Repaired stats: {len(completed)} completed games; Utah Tech present={any(g.get('opponent') == 'Utah Tech' for g in game_log)}")

if __name__ == "__main__":
    main()

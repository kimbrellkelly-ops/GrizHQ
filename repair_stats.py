import json
from pathlib import Path

PATH = Path("data.json")


def main():
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

    found = False
    for item in game_log:
        if str(item.get("opponent", "")).strip().lower() == "utah tech":
            item.update(utah)
            found = True
            break
    if not found:
        game_log.append(utah)

    def week_number(item):
        try:
            return int(str(item.get("week", "Wk 99")).split()[-1])
        except Exception:
            return 99

    game_log.sort(key=week_number)
    completed = [g for g in game_log if g.get("result")]
    stats["through"] = f"Through {len(completed)} completed games"

    summary = stats.setdefault("team_summary", [])
    summary_values = {
        "RECORD": "3–0",
        "POINTS / GAME": "36.0",
        "TOTAL OFFENSE": "429",
        "TOTAL DEFENSE": "404",
    }
    for row in summary:
        label = str(row.get("label", "")).upper()
        if label in summary_values:
            row["value"] = summary_values[label]

    offense = stats.setdefault("offense", [])
    defense = stats.setdefault("defense", [])
    offense_values = {
        "Points": "108",
        "Total Yards": "1288",
        "Passing": "793",
        "Rushing": "495",
    }
    for row in offense:
        if row and row[0] in offense_values:
            row[1] = offense_values[row[0]]
    for row in defense:
        if row and row[0] == "Points Allowed":
            row[1] = "45"
        elif row and row[0] == "Yards Allowed":
            row[1] = "1212"

    # Official Montana cumulative player leaders after three completed games.
    leaders = stats.setdefault("leaders", {})
    leaders["passing"] = [{
        "player": "Keali'i Ah Yat",
        "line": "67-103 • 793 YDS • 5 TD • 1 INT",
        "extra": "Long: 85",
    }]
    leaders["rushing"] = [{
        "player": "Eli Gillman",
        "line": "49 CAR • 328 YDS • 7 TD",
        "extra": "Avg: 6.7",
    }, {
        "player": "Dylan Paine",
        "line": "20 CAR • 162 YDS • 2 TD",
        "extra": "Avg: 8.1",
    }]
    leaders["receiving"] = [{
        "player": "Brooks Davis",
        "line": "12 REC • 160 YDS • 1 TD",
        "extra": "Long: 33",
    }, {
        "player": "Lekeldrick Bridges",
        "line": "8 REC • 110 YDS • 1 TD",
        "extra": "Long: 53",
    }, {
        "player": "Landon Ransom-Goelz",
        "line": "7 REC • 115 YDS • 0 TD",
        "extra": "Long: 37",
    }, {
        "player": "Eli Gillman",
        "line": "4 REC • 99 YDS • 2 TD",
        "extra": "Long: 85",
    }]

    PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Repaired stats and player leaders: {len(completed)} completed games; Utah Tech present={any(g.get('opponent') == 'Utah Tech' for g in game_log)}")


if __name__ == "__main__":
    main()

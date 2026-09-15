#!/usr/bin/env python3
"""Render the transfer ledger into the visible GrizHQ transfer cards.
The ledger is the source of truth; null stats are rendered explicitly and never
silently replaced with stale HTML values.
"""
from pathlib import Path
import json, re
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "index.html"
LEDGER = ROOT / "transfer_stats.json"
START = "<!-- GRIZ TRANSFERS START -->"
END = "<!-- GRIZ TRANSFERS END -->"

def render_stats(player):
    stats = player.get("stats")
    checked = player.get("verified", player.get("checked", "")) or player.get("updated", "")
    if isinstance(stats, str) and stats.strip():
        value = stats.strip()
    elif isinstance(stats, dict):
        parts=[]
        for key in ("games", "starts", "rush", "rush_yds", "rec", "rec_yds", "pass_yds", "tackles", "tfl", "sacks", "interceptions", "pbu"):
            if key in stats and stats[key] is not None:
                parts.append(f"{key.replace('_',' ')}: {stats[key]}")
        value = " · ".join(parts) if parts else "Not yet verified — no published individual stats"
    else:
        value = "Not yet verified — no published individual stats"
    if checked and "verified" not in value.lower():
        value += f" · Checked {checked}"
    return value

def main():
    ledger=json.loads(LEDGER.read_text(encoding="utf-8"))
    players={p["name"].strip():p for p in ledger.get("players",[])}
    text=INDEX.read_text(encoding="utf-8")
    a=text.find(START); b=text.find(END,a)
    if a<0 or b<0: raise SystemExit("Transfer markers missing")
    section=text[a+len(START):b]
    soup=BeautifulSoup(section,"html.parser")
    root=soup.select_one(".griz-transfers")
    if root is None: raise SystemExit(".griz-transfers missing")
    matched=0; changed=False
    for card in root.select(".griz-transfer-card"):
        h=card.find("h4")
        if not h: continue
        name=h.get_text(" ",strip=True)
        p=players.get(name)
        if not p: continue
        matched += 1
        el=card.select_one(".griz-transfer-line.current span")
        if el is None: continue
        new=render_stats(p)
        if el.get_text(" ",strip=True) != new:
            el.string=new; changed=True
    # make the source/refresh state visible in the section
    note=root.select_one(".griz-transfer-ledger-note")
    if note is None:
        note=soup.new_tag("p", attrs={"class":"griz-transfer-ledger-note"})
        root.insert(1,note)
    note.string=f"Transfer ledger checked {ledger.get('updated','unknown')}. Verified stats are shown when available; unverified players are labeled explicitly."
    changed=True
    if matched == 0:
        raise SystemExit("No transfer cards matched the ledger")
    INDEX.write_text(text[:a+len(START)]+"\n"+str(root)+"\n"+text[b:],encoding="utf-8")
    print(f"Rendered {matched} transfer cards from transfer_stats.json; changed={changed}")

if __name__ == "__main__": main()

#!/usr/bin/env python3
"""Robust Griz transfer-stat updater.
Uses pandas HTML-table parsing and flexible name/column matching."""
from pathlib import Path
import re
import requests
import pandas as pd
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "index.html"
HEADERS = {"User-Agent": "Mozilla/5.0 GrizHQ transfer tracker"}
PLAYERS = [
 ("Malae Fonoti", ["https://mutigers.com/sports/football/stats", "https://mutigers.com/sports/football/stats/2026"], "offense"),
 ("Colin Amick", ["https://cyclones.com/sports/football/stats", "https://cyclones.com/sports/football/stats/2026"], "offense"),
 ("Jose Balver-Mendoza", ["https://nevadawolfpack.com/sports/football/stats", "https://nevadawolfpack.com/sports/football/stats/2026"], "offense"),
 ("Jareb Ramos", ["https://cyclones.com/sports/football/stats", "https://cyclones.com/sports/football/stats/2026"], "defense"),
 ("Caleb Otlewski", ["https://csurams.com/sports/football/stats", "https://csurams.com/sports/football/stats/2026"], "defense"),
 ("Diezel Wilkinson", ["https://uabsports.com/sports/football/stats", "https://uabsports.com/sports/football/stats/2026"], "defense"),
 ("Kyon Loud", ["https://goduke.com/sports/football/stats", "https://goduke.com/sports/football/stats/2026"], "defense"),
 ("Rashid Mansour", ["https://hcuhuskies.com/sports/football/stats", "https://hcuhuskies.com/sports/football/stats/2026"], "defense"),
 ("Terahiti Wolfe", ["https://goviks.com/sports/football/stats/?path=football"], "defense"),
 ("Justus Breston", ["https://goumary.com/sports/football/stats", "https://goumary.com/sports/football/stats/2026"], "defense"),
 ("Micah Harper", ["https://cyclones.com/sports/football/stats", "https://cyclones.com/sports/football/stats/2026"], "defense"),
]

def norm(s): return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", str(s).lower())).strip()
def number(v):
 m = re.search(r"-?\d+(?:\.\d+)?", str(v).replace(",", ""))
 return None if not m else (int(float(m.group())) if float(m.group()).is_integer() else float(m.group()))
def find_table(name, urls):
 target = norm(name); parts = target.split(); last = parts[-1]
 for url in urls:
  try:
   html = requests.get(url, headers=HEADERS, timeout=30).text
   for df in pd.read_html(html):
    df.columns = [norm(" ".join(map(str,c))) if isinstance(c, tuple) else norm(c) for c in df.columns]
    pcols = [c for c in df.columns if c == "player" or c.startswith("player ") or c in ("name", "athlete")]
    if not pcols: continue
    pc = pcols[0]
    for _, row in df.iterrows():
     value = norm(row.get(pc, ""))
     if value == target or value == f"{last} {' '.join(parts[:-1])}" or target in value:
      return row.to_dict(), df.columns.tolist(), url
  except Exception as exc:
   print(f"{name}: {url} unavailable: {exc}")
 return None

def get(row, cols, *keys):
 for key in keys:
  for col in cols:
   if col == key or col.startswith(key + " "):
    return number(row.get(col))
 return None

def line(row, cols, kind):
 gp=get(row,cols,"gp","games played"); gs=get(row,cols,"gs","starts"); out=[]
 if gp is not None: out.append(f"{gp} G")
 if gs is not None: out.append(f"{gs} starts")
 if kind == "offense":
  for keys,label in [(("att",),"rush"),(('yds',),"yds"),(('td',),"TD")]:
   v=get(row,cols,*keys)
   if v is not None: out.append(f"{v} {label}")
 else:
  for keys,label in [(('tot',),"tackles"),(('tfl',),"TFL"),(('sacks',),"sacks"),(('int',),"INT"),(('pbu','bu'),"PBU")]:
   v=get(row,cols,*keys)
   if v is not None: out.append(f"{v} {label}")
 return " · ".join(out) if out else "No player stats posted"

def main():
 results={}; matched=0
 for name,urls,kind in PLAYERS:
  found=find_table(name,urls)
  if not found: print(f"{name}: no matching row"); continue
  row,cols,url=found; results[name]=(line(row,cols,kind),url); matched+=1; print(f"{name}: {results[name][0]} [{url}]")
 if not matched: raise SystemExit("No transfer stats sources returned a matching player row")
 text=INDEX.read_text(encoding="utf-8"); a=text.find("<!-- GRIZ TRANSFERS START -->"); b=text.find("<!-- GRIZ TRANSFERS END -->",a)
 if a<0 or b<0: raise SystemExit("Transfer markers missing")
 section=text[a+len("<!-- GRIZ TRANSFERS START -->"):b]; soup=BeautifulSoup(section,"html.parser"); root=soup.select_one(".griz-transfers")
 changed=False
 for card in root.select(".griz-transfer-card"):
  h=card.find("h4");
  if not h: continue
  name=h.get_text(" ",strip=True)
  if name not in results: continue
  value,_=results[name]; el=card.select_one(".griz-transfer-line.current span")
  if el and el.get_text(" ",strip=True)!=value: el.string=value; changed=True
 if changed: INDEX.write_text(text[:a+len("<!-- GRIZ TRANSFERS START -->")]+"\n"+str(root)+"\n"+text[b:],encoding="utf-8")
 print(f"Transfer tracker: {matched}/{len(PLAYERS)} sources matched; changed={changed}")
if __name__ == "__main__": main()

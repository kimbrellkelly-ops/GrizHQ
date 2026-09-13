import json, re
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

DATA = Path('data.json')
BASE = 'https://gogriz.com'
URL = f'{BASE}/sports/football/stats/2026'
SCHEDULE_URL = f'{BASE}/sports/football/schedule/2026'
HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; GrizHQ/1.0; +https://grizhq.com)'}
CATEGORIES = ('passing', 'rushing', 'receiving', 'tackles', 'pressure', 'special')
BAD = {'player', 'players', 'total', 'totals', 'team', 'team totals', 'opponents', 'opponent', 'montana'}


def clean(value):
    return re.sub(r'\s+', ' ', value or '').strip()


def norm(value):
    return re.sub(r'[^A-Z0-9]+', ' ', clean(value).upper()).strip()


def first_index(headers, *names):
    for name in names:
        for i, header in enumerate(headers):
            if header == name or header.startswith(name + ' '):
                return i
    return None


def table_info(table):
    rows = table.find_all('tr')
    candidates = []
    for row in rows[:8]:
        vals = [norm(cell.get_text(' ', strip=True)) for cell in row.find_all(['th', 'td'])]
        if vals:
            candidates.append(vals)
    headers = max(candidates, key=len, default=[])
    return headers, rows


def categories_for(table):
    headers, _ = table_info(table)
    h = set(headers)
    joined = ' '.join(headers)
    result = []
    if ('CMP' in h or 'COMP' in h) and 'ATT' in h and ('YDS' in h or 'YARD' in h):
        result.append('passing')
    if 'ATT' in h and ('GAIN' in h or 'NET' in h) and ('LOSS' in h or 'AVG' in h):
        result.append('rushing')
    if ('REC' in h or 'RECEPTIONS' in h) and ('YDS' in h or 'YARD' in h):
        result.append('receiving')
    if 'SOLO' in h and ('AST' in h or 'ASSIST' in h) and ('TOT' in h or 'TOTAL' in h):
        result.extend(['tackles', 'pressure'])
    if 'PUNTS' in h or 'PUNTS' in joined or 'FGM' in h or 'FGA' in h or 'RESULT' in h and 'YDS' in h:
        result.append('special')
    return list(dict.fromkeys(result))


def parse_table(table, category):
    headers, rows = table_info(table)
    if len(headers) < 3:
        return []
    name_index = first_index(headers, 'PLAYER', 'NAME')
    if name_index is None:
        name_index = 0

    def value(cells, *names):
        i = first_index(headers, *names)
        return cells[i] if i is not None and i < len(cells) else ''

    result = []
    for tr in rows[1:]:
        cells = [clean(c.get_text(' ', strip=True)) for c in tr.find_all(['td', 'th'])]
        if len(cells) <= name_index:
            continue
        player = cells[name_index]
        if not re.search('[A-Za-z]', player) or player.lower() in BAD or len(player.split()) < 2:
            continue
        if category == 'passing':
            line = f'{value(cells, "CMP", "COMP") or "0"} CMP • {value(cells, "YDS", "YARD") or "0"} YDS • {value(cells, "TD") or "0"} TD • {value(cells, "INT") or "0"} INT'
            extra = f'Long: {value(cells, "LONG")}' if value(cells, 'LONG') else ''
        elif category == 'rushing':
            line = f'{value(cells, "ATT", "CAR", "CARRIES") or "0"} CAR • {value(cells, "NET", "YDS", "YARD") or "0"} YDS • {value(cells, "TD") or "0"} TD'
            extra = f'Avg: {value(cells, "AVG")}' if value(cells, 'AVG') else ''
        elif category == 'receiving':
            line = f'{value(cells, "REC", "RECEPTIONS", "NO") or "0"} REC • {value(cells, "YDS", "YARD") or "0"} YDS • {value(cells, "TD") or "0"} TD'
            extra = f'Long: {value(cells, "LONG")}' if value(cells, 'LONG') else ''
        elif category == 'tackles':
            total = value(cells, 'TOT', 'TKL', 'TOTAL')
            line = f'{total or "0"} TKL • {value(cells, "SOLO") or "0"} SOLO'
            extra = f'{value(cells, "AST", "ASSIST") or "0"} AST'
        elif category == 'pressure':
            line = f'{value(cells, "TFL YDS", "TFL") or "0"} TFL • {value(cells, "SACK YDS", "SACK", "SACKS") or "0"} SACK • {value(cells, "FF") or "0"} FF'
            extra = f'{value(cells, "INT") or "0"} INT • {value(cells, "BRUP", "PBU") or "0"} PBU'
        else:
            punts = value(cells, 'PUNTS', 'PUNTS')
            made = value(cells, 'FGM', 'MADE')
            attempts = value(cells, 'FGA', 'ATT')
            if punts:
                line = f'{punts} PUNTS • {value(cells, "YDS", "YARD") or "0"} YDS • {value(cells, "AVG") or "0"} AVG'
                extra = f'Long: {value(cells, "LONG")}' if value(cells, 'LONG') else ''
            elif made or attempts:
                line, extra = f'{made or "0"}/{attempts or "0"} FG', ''
            else:
                continue
        result.append({'player': player, 'line': line, 'extra': extra})
    return result


def fetch(url):
    response = requests.get(url, headers=HEADERS, timeout=45)
    response.raise_for_status()
    return BeautifulSoup(response.text, 'html.parser')


def main():
    data = json.loads(DATA.read_text(encoding='utf-8'))
    soups = [fetch(URL)]
    try:
        schedule = fetch(SCHEDULE_URL)
        links = []
        for a in schedule.find_all('a', href=True):
            href = urljoin(BASE, a['href'])
            if '/boxscore/' in href and href not in links:
                links.append(href)
        for href in links[:12]:
            try:
                soups.append(fetch(href))
            except requests.RequestException as exc:
                print(f'Boxscore fetch skipped: {href}: {exc}')
    except requests.RequestException as exc:
        print(f'Schedule fetch skipped: {exc}')

    leaders = {key: [] for key in CATEGORIES}
    for soup in soups:
        for table in soup.find_all('table'):
            for category in categories_for(table):
                parsed = parse_table(table, category)
                if not parsed:
                    continue
                if category == 'special':
                    leaders[category].extend(parsed)
                elif not leaders[category]:
                    leaders[category] = parsed

    for category in CATEGORIES:
        unique, seen = [], set()
        for item in leaders[category]:
            key = (item['player'], item['line'], item['extra'])
            if key not in seen:
                seen.add(key)
                unique.append(item)
        leaders[category] = unique[:5]

    missing = [key for key in CATEGORIES if not leaders[key]]
    if missing:
        raise RuntimeError('Official player-stat categories missing: ' + ', '.join(missing))

    stats = data.setdefault('stats', {})
    stats['leaders'] = leaders
    stats['leaders_source'] = URL
    stats['leaders_updated'] = data.get('updated')
    DATA.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print('Official player-stat categories refreshed:', ', '.join(CATEGORIES))


if __name__ == '__main__':
    main()

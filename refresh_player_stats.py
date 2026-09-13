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
BAD = {'player', 'players', 'total', 'team', 'team totals', 'opponents', 'opponent', 'montana'}


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
    context = []
    for node in (table.find_previous(['h1', 'h2', 'h3', 'h4', 'h5', 'caption']), table.find_parent(['section', 'div'])):
        if node:
            context.append(norm(node.get_text(' ', strip=True)))
    return headers, rows, ' '.join(context + [' '.join(' '.join(x) for x in candidates)])


def category_for(table):
    headers, rows, text = table_info(table)
    if ('PASSING' in text or 'CMP' in text or 'COMP' in text) and 'ATT' in text:
        return 'passing'
    if any(x in text for x in ('PUNTING', 'PUNTS', 'FIELD GOAL', 'FGM', 'FGA', 'KICKING')):
        return 'special'
    if ('RECEIVING' in text or 'REC' in text or 'RECEPTIONS' in text) and 'YDS' in text:
        return 'receiving'
    if ('RUSHING' in text or 'CARRIES' in text or 'CAR' in text) and 'YDS' in text:
        return 'rushing'
    if any(x in text for x in ('TACKLES', 'SOLO', 'ASSIST', 'AST')) and any(x in text for x in ('TOT', 'TOTAL', 'AST', 'ASSIST')):
        return 'tackles'
    if any(x in text for x in ('DEFENSE', 'DEFENSIVE', 'TFL', 'SACK', 'PBU', 'PASSES DEFENDED', 'FORCED FUMBLE')):
        return 'pressure'
    return None


def parse_table(table, category):
    headers, rows, _ = table_info(table)
    if len(headers) < 3:
        return []
    name_index = first_index(headers, 'PLAYER', 'NAME') or 0

    def value(cells, *names):
        i = first_index(headers, *names)
        return cells[i] if i is not None and i < len(cells) else ''

    result = []
    for tr in rows[1:]:
        cells = [clean(c.get_text(' ', strip=True)) for c in tr.find_all(['td', 'th'])]
        if len(cells) <= name_index:
            continue
        player = cells[name_index]
        if player.lower() in BAD or len(player.split()) < 2 or not re.search('[A-Za-z]', player):
            continue
        if category == 'passing':
            comp = value(cells, 'C A', 'CMP ATT', 'COMP ATT', 'COMP')
            line = f'{comp or "0"} • {value(cells, "YDS", "YARD") or "0"} YDS • {value(cells, "TD") or "0"} TD • {value(cells, "INT") or "0"} INT'
            extra = f'Long: {value(cells, "LONG")}' if value(cells, "LONG") else ''
        elif category == 'rushing':
            line = f'{value(cells, "ATT", "CAR", "CARRIES") or "0"} CAR • {value(cells, "YDS", "YARD", "NET") or "0"} YDS • {value(cells, "TD") or "0"} TD'
            extra = f'Avg: {value(cells, "AVG")}' if value(cells, "AVG") else ''
        elif category == 'receiving':
            line = f'{value(cells, "REC", "RECEPTIONS", "NO") or "0"} REC • {value(cells, "YDS", "YARD") or "0"} YDS • {value(cells, "TD") or "0"} TD'
            extra = f'Long: {value(cells, "LONG")}' if value(cells, "LONG") else ''
        elif category == 'tackles':
            total = value(cells, 'TOT', 'TKL', 'TOTAL')
            line = f'{total or "0"} TKL • {value(cells, "SOLO") or "0"} SOLO'
            extra = f'{value(cells, "AST", "ASSIST") or "0"} AST'
        elif category == 'pressure':
            line = f'{value(cells, "TFL") or "0"} TFL • {value(cells, "SACK", "SACKS") or "0"} SACK • {value(cells, "FF") or "0"} FF'
            extra = f'{value(cells, "INT") or "0"} INT • {value(cells, "PBU") or "0"} PBU'
        else:
            punts = value(cells, 'PUNTS', 'PUNT')
            made, attempts = value(cells, 'FGM', 'MADE'), value(cells, 'FGA', 'ATT')
            if punts:
                line = f'{punts} PUNTS • {value(cells, "YDS", "YARD") or "0"} YDS • {value(cells, "AVG") or "0"} AVG'
                extra = f'Long: {value(cells, "LONG")}' if value(cells, "LONG") else ''
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
            category = category_for(table)
            if not category:
                continue
            parsed = parse_table(table, category)
            if not parsed:
                continue
            if category == 'special':
                leaders[category].extend(parsed)
            elif not leaders[category]:
                leaders[category] = parsed

    for category in CATEGORIES:
        unique = []
        seen = set()
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

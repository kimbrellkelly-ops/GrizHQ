import json, re
from pathlib import Path

import requests
from bs4 import BeautifulSoup

DATA = Path('data.json')
URL = 'https://gogriz.com/sports/football/stats/2026'
HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; GrizHQ/1.0; +https://grizhq.com)'}
BAD = {
    'player', 'players', 'total', 'team', 'team totals', 'opponents',
    'opponent', 'montana', 'individual', 'individual statistics'
}
CATEGORIES = ('passing', 'rushing', 'receiving', 'tackles', 'pressure', 'special')


def clean(value):
    return re.sub(r'\s+', ' ', value or '').strip()


def first_index(headers, *names):
    for name in names:
        for index, header in enumerate(headers):
            if header == name or header.startswith(name + ' '):
                return index
    return None


def table_headers(table):
    rows = table.find_all('tr')
    if not rows:
        return [], rows, ''
    candidates = []
    for row in rows[:6]:
        values = [clean(cell.get_text(' ', strip=True)).upper()
                  for cell in row.find_all(['th', 'td'])]
        if values:
            candidates.append(values)
    headers = max(candidates, key=len, default=[])
    all_header_text = ' '.join(' '.join(row) for row in candidates)
    return headers, rows, all_header_text


def surrounding_text(table):
    parts = []
    for node in (table.find_previous(['h1', 'h2', 'h3', 'h4', 'h5', 'caption']),
                 table.find_parent(['section', 'div'])):
        if node:
            parts.append(clean(node.get_text(' ', strip=True)).upper())
    return ' '.join(parts)


def category_for(table):
    headers, rows, all_text = table_headers(table)
    text = f'{surrounding_text(table)} {all_text}'
    if ('PASSING' in text or 'CMP' in text or 'COMP' in text) and 'ATT' in text:
        return 'passing'
    if any(token in text for token in ('PUNTING', 'PUNTS', 'PUNT', 'FIELD GOALS', 'FGM', 'FGA')):
        return 'special'
    if ('RECEIVING' in text or 'REC' in text) and 'YDS' in text and ('LONG' in text or 'NO' in text):
        return 'receiving'
    if ('RUSHING' in text or 'CAR' in text or 'ATT' in text) and 'YDS' in text and any(token in text for token in ('GAIN', 'NET', 'AVG')):
        return 'rushing'
    if ('TACKLES' in text or 'SOLO' in text) and any(token in text for token in ('AST', 'ASSIST', 'TOT', 'TOTAL')):
        return 'tackles'
    if any(token in text for token in ('DEFENSE', 'DEFENSIVE', 'TFL', 'SACK', 'FF', 'PBU', 'PASSES DEFENDED')):
        return 'pressure'
    return None


def parse_table(table, category):
    headers, rows, _ = table_headers(table)
    if len(headers) < 3:
        return []
    name_index = first_index(headers, 'PLAYER', 'NAME')
    if name_index is None:
        name_index = 0

    def value(row, *names):
        index = first_index(headers, *names)
        return row[index] if index is not None and index < len(row) else ''

    output = []
    for tr in rows[1:]:
        cells = [clean(cell.get_text(' ', strip=True))
                 for cell in tr.find_all(['td', 'th'])]
        if len(cells) <= name_index:
            continue
        player = cells[name_index]
        if player.lower() in BAD or len(player.split()) < 2 or not re.search('[A-Za-z]', player):
            continue

        if category == 'passing':
            comp = value(cells, 'C-A', 'CMP-ATT', 'COMP-ATT', 'COMP')
            yards = value(cells, 'YDS', 'YARD')
            touchdowns = value(cells, 'TD')
            interceptions = value(cells, 'INT')
            longest = value(cells, 'LONG')
            line = f'{comp or "0"} • {yards or "0"} YDS • {touchdowns or "0"} TD • {interceptions or "0"} INT'
            extra = f'Long: {longest}' if longest else ''
        elif category == 'rushing':
            attempts = value(cells, 'ATT', 'CAR')
            yards = value(cells, 'YDS', 'YARD', 'NET')
            touchdowns = value(cells, 'TD')
            average = value(cells, 'AVG')
            longest = value(cells, 'LONG')
            line = f'{attempts or "0"} CAR • {yards or "0"} YDS • {touchdowns or "0"} TD'
            extra = f'Avg: {average}' if average else (f'Long: {longest}' if longest else '')
        elif category == 'receiving':
            receptions = value(cells, 'REC', 'RECEPTIONS', 'NO')
            yards = value(cells, 'YDS', 'YARD')
            touchdowns = value(cells, 'TD')
            longest = value(cells, 'LONG')
            line = f'{receptions or "0"} REC • {yards or "0"} YDS • {touchdowns or "0"} TD'
            extra = f'Long: {longest}' if longest else ''
        elif category == 'tackles':
            total = value(cells, 'TOT', 'TKL', 'TOTAL')
            solo = value(cells, 'SOLO')
            assists = value(cells, 'AST', 'ASSIST')
            line = f'{total or "0"} TKL • {solo or "0"} SOLO'
            extra = f'{assists or "0"} AST'
        elif category == 'pressure':
            tfl = value(cells, 'TFL')
            sacks = value(cells, 'SACK', 'SACKS')
            forced = value(cells, 'FF')
            interceptions = value(cells, 'INT')
            pbu = value(cells, 'PBU')
            line = f'{tfl or "0"} TFL • {sacks or "0"} SACK • {forced or "0"} FF'
            extra = f'{interceptions or "0"} INT • {pbu or "0"} PBU'
        elif category == 'special':
            punts = value(cells, 'PUNTS', 'PUNT')
            yards = value(cells, 'YDS', 'YARD')
            average = value(cells, 'AVG')
            longest = value(cells, 'LONG')
            inside20 = value(cells, 'IN20', 'INSIDE 20', 'I20')
            made = value(cells, 'FGM', 'MADE')
            attempts = value(cells, 'FGA', 'ATT')
            if punts:
                line = f'{punts} PUNTS • {yards or "0"} YDS • {average or "0"} AVG'
                extra = ' • '.join(part for part in [f'Long: {longest}' if longest else '', f'{inside20} inside 20' if inside20 else ''] if part)
            elif made or attempts:
                line = f'{made or "0"}/{attempts or "0"} FG'
                extra = ''
            else:
                continue
        else:
            continue
        output.append({'player': player, 'line': line, 'extra': extra})
    return output[:5]


def main():
    data = json.loads(DATA.read_text(encoding='utf-8'))
    response = requests.get(URL, headers=HEADERS, timeout=45)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')

    leaders = {key: [] for key in CATEGORIES}
    detected = []
    for table in soup.find_all('table'):
        category = category_for(table)
        if not category:
            continue
        parsed = parse_table(table, category)
        if parsed:
            if category == 'special':
                leaders[category].extend(parsed)
                leaders[category] = leaders[category][:5]
            elif not leaders[category]:
                leaders[category] = parsed
            if category not in detected:
                detected.append(category)

    missing = [key for key in CATEGORIES if not leaders[key]]
    if missing:
        raise RuntimeError('Official player-stat categories missing: ' + ', '.join(missing))

    stats = data.setdefault('stats', {})
    stats['leaders'] = leaders
    stats['leaders_source'] = URL
    stats['leaders_updated'] = data.get('updated')
    DATA.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print('Official player-stat categories refreshed:', ', '.join(detected))


if __name__ == '__main__':
    main()

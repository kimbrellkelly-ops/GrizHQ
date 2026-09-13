import json, re
from pathlib import Path

import requests
from bs4 import BeautifulSoup

DATA = Path('data.json')
URL = 'https://gogriz.com/sports/football/stats/2026'
ROSTER_URL = 'https://gogriz.com/sports/football/roster/2026'
HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; GrizHQ/1.0; +https://grizhq.com)'}
CATEGORIES = ('passing', 'rushing', 'receiving', 'tackles', 'pressure', 'special')
BAD_NAMES = {'player', 'players', 'total', 'totals', 'team', 'team totals', 'opponents', 'opponent', 'montana'}


def clean(value):
    return re.sub(r'\s+', ' ', value or '').strip()


def norm(value):
    return re.sub(r'[^A-Z0-9%]+', ' ', clean(value).upper()).strip()


def name_key(value):
    words = re.findall(r'[A-Z0-9]+', norm(value))
    return ' '.join(sorted(words))


def first_index(headers, *names):
    for name in names:
        for i, header in enumerate(headers):
            if header == name or header.startswith(name + ' '):
                return i
    return None


def table_info(table):
    rows = table.find_all('tr')
    candidates = []
    for row in rows[:10]:
        vals = [norm(cell.get_text(' ', strip=True)) for cell in row.find_all(['th', 'td'])]
        if vals:
            candidates.append(vals)
    tokens = {'PLAYER', 'NAME', 'GP', 'ATT', 'YDS', 'REC', 'SOLO', 'PUNTS', 'FGM'}
    matching = [row for row in candidates if len(set(row) & tokens) >= 2]
    return max(matching, key=len, default=(candidates[0] if candidates else [])), rows


def categories_for(table):
    headers, _ = table_info(table)
    h = set(headers)
    joined = ' '.join(headers)
    result = []
    if ('CMP' in h or 'COMP' in h) and 'ATT' in h and ('YDS' in h or 'YARD' in h):
        result.append('passing')
    if 'ATT' in h and ('GAIN' in h or 'NET' in h) and ('LOSS' in h or 'AVG' in h):
        result.append('rushing')
    if ('REC' in h or 'RECEPTIONS' in h or 'NO' in h) and ('YDS' in h or 'YARD' in h):
        result.append('receiving')
    if 'SOLO' in h and ('AST' in h or 'ASSIST' in h) and ('TOT' in h or 'TOTAL' in h):
        result.extend(['tackles', 'pressure'])
    if 'PUNTS' in h or 'FGM' in h or 'FGA' in h or ('KICK' in joined and 'YDS' in h):
        result.append('special')
    return list(dict.fromkeys(result))


def player_index(headers, cells):
    index = first_index(headers, 'PLAYER', 'NAME')
    if index is not None and index < len(cells):
        return index
    for i, cell in enumerate(cells[:4]):
        value = clean(cell)
        if re.search('[A-Za-z]', value) and (',' in value or len(value.split()) >= 2) and not value.isdigit():
            return i
    return None


def parse_table(table, category, roster_keys):
    headers, rows = table_info(table)
    if len(headers) < 3:
        return []
    result = []
    for tr in rows[1:]:
        cells = [clean(c.get_text(' ', strip=True)) for c in tr.find_all(['td', 'th'])]
        if len(cells) < 3:
            continue
        index = player_index(headers, cells)
        if index is None or index >= len(cells):
            continue
        player = clean(cells[index])
        key = name_key(player)
        if not re.search('[A-Za-z]', player) or player.lower() in BAD_NAMES or len(player.split()) < 2:
            continue
        if player.isdigit() or player.lower().startswith(('total ', 'opponent')):
            continue
        # Critical guard: never publish opponent/team rows or names not on Montana's roster.
        if roster_keys and key not in roster_keys:
            continue

        def value(*names):
            i = first_index(headers, *names)
            return cells[i] if i is not None and i < len(cells) else ''

        if category == 'passing':
            line = f'{value("CMP", "COMP") or "0"} CMP • {value("YDS", "YARD") or "0"} YDS • {value("TD") or "0"} TD • {value("INT") or "0"} INT'
            extra = f'Long: {value("LONG")}' if value('LONG') else ''
        elif category == 'rushing':
            line = f'{value("ATT", "CAR", "CARRIES") or "0"} CAR • {value("NET", "YDS", "YARD") or "0"} YDS • {value("TD") or "0"} TD'
            extra = f'Avg: {value("AVG")}' if value('AVG') else ''
        elif category == 'receiving':
            line = f'{value("REC", "RECEPTIONS", "NO") or "0"} REC • {value("YDS", "YARD") or "0"} YDS • {value("TD") or "0"} TD'
            extra = f'Long: {value("LONG")}' if value('LONG') else ''
        elif category == 'tackles':
            total = value('TOT', 'TKL', 'TOTAL')
            line = f'{total or "0"} TKL • {value("SOLO") or "0"} SOLO'
            extra = f'{value("AST", "ASSIST") or "0"} AST'
        elif category == 'pressure':
            line = f'{value("TFL YDS", "TFL") or "0"} TFL • {value("SACK YDS", "SACK", "SACKS") or "0"} SACK • {value("FF") or "0"} FF'
            extra = f'{value("INT") or "0"} INT • {value("BRUP", "PBU") or "0"} PBU'
        else:
            punts = value('PUNTS')
            made = value('FGM', 'MADE')
            attempts = value('FGA', 'ATT')
            if punts:
                line = f'{punts} PUNTS • {value("YDS", "YARD") or "0"} YDS • {value("AVG") or "0"} AVG'
                extra = f'Long: {value("LONG")}' if value('LONG') else ''
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


def roster_keys_from(soup):
    keys = set()
    for text in soup.stripped_strings:
        value = clean(text)
        if ',' in value and len(value.split()) >= 2:
            keys.add(name_key(value))
        elif len(value.split()) >= 2 and re.search(r'[A-Za-z]', value):
            # Roster names are commonly rendered as "First Last".
            if not any(token in value.lower() for token in ('roster', 'coaches', 'height', 'weight', 'year', 'position')):
                keys.add(name_key(value))
    return keys


def main():
    data = json.loads(DATA.read_text(encoding='utf-8'))
    stats = data.setdefault('stats', {})
    stats_soup = fetch(URL)
    roster_keys = roster_keys_from(fetch(ROSTER_URL))
    leaders = {key: [] for key in CATEGORIES}
    for table in stats_soup.find_all('table'):
        for category in categories_for(table):
            parsed = parse_table(table, category, roster_keys)
            if parsed and not leaders[category]:
                leaders[category] = parsed

    missing = [key for key in CATEGORIES if not leaders[key]]
    if missing:
        raise RuntimeError('Official player-stat categories missing after roster validation: ' + ', '.join(missing))

    stats['leaders'] = {key: values[:5] for key, values in leaders.items()}
    stats['leaders_source'] = URL
    stats['leaders_updated'] = data.get('updated')
    DATA.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print('Official player-stat categories refreshed and roster-validated:', ', '.join(CATEGORIES))


if __name__ == '__main__':
    main()

import json, re
from pathlib import Path

import requests
from bs4 import BeautifulSoup

DATA = Path('data.json')
URL = 'https://gogriz.com/sports/football/stats/2026'
HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; GrizHQ/1.0; +https://grizhq.com)'}
CATEGORIES = ('passing', 'rushing', 'receiving', 'tackles', 'pressure', 'special')
BAD_NAMES = {'player', 'players', 'total', 'totals', 'team', 'team totals', 'opponents', 'opponent', 'montana'}


def clean(value):
    return re.sub(r'\s+', ' ', value or '').strip()


def norm(value):
    return re.sub(r'[^A-Z0-9%]+', ' ', clean(value).upper()).strip()


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
        cells = row.find_all(['th', 'td'])
        vals = [norm(cell.get_text(' ', strip=True)) for cell in cells]
        if vals:
            candidates.append(vals)
    # Prefer the row containing known column labels. Never use a player data row
    # as the header merely because it has the most cells.
    header_tokens = {'PLAYER', 'NAME', 'GP', 'ATT', 'YDS', 'REC', 'SOLO', 'PUNTS', 'FGM'}
    matching = [row for row in candidates if len(set(row) & header_tokens) >= 2]
    headers = max(matching, key=len, default=[])
    if not headers:
        headers = candidates[0] if candidates else []
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
    if ('REC' in h or 'RECEPTIONS' in h or 'NO' in h) and ('YDS' in h or 'YARD' in h):
        result.append('receiving')
    if 'SOLO' in h and ('AST' in h or 'ASSIST' in h) and ('TOT' in h or 'TOTAL' in h):
        result.extend(['tackles', 'pressure'])
    if 'PUNTS' in h or 'FGM' in h or 'FGA' in h or ('KICK' in joined and 'YDS' in h):
        result.append('special')
    return list(dict.fromkeys(result))


def player_index(headers, cells):
    index = first_index(headers, 'PLAYER', 'NAME')
    if index is not None:
        return index
    # GoGriz tables often begin with jersey number and put the player in cell 2.
    for i, cell in enumerate(cells[:4]):
        value = clean(cell)
        if re.search(r'[A-Za-z]', value) and (',' in value or len(value.split()) >= 2) and not value.isdigit():
            return i
    return None


def parse_table(table, category):
    headers, rows = table_info(table)
    if len(headers) < 3:
        return []
    result = []
    for tr in rows[1:]:
        cells = [clean(c.get_text(' ', strip=True)) for c in tr.find_all(['td', 'th'])]
        if len(cells) < 3:
            continue
        name_index = player_index(headers, cells)
        if name_index is None or name_index >= len(cells):
            continue
        player = clean(cells[name_index])
        if not re.search('[A-Za-z]', player) or player.lower() in BAD_NAMES or len(player.split()) < 2:
            continue
        # Exclude team summary/opponent rows and rows whose apparent name is a number.
        if player.lower().startswith(('total ', 'opponent')) or player.isdigit():
            continue

        def value(*names):
            index = first_index(headers, *names)
            return cells[index] if index is not None and index < len(cells) else ''

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


def main():
    response = requests.get(URL, headers=HEADERS, timeout=45)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    leaders = {key: [] for key in CATEGORIES}
    for table in soup.find_all('table'):
        for category in categories_for(table):
            parsed = parse_table(table, category)
            if parsed and not leaders[category]:
                leaders[category] = parsed

    missing = [key for key in CATEGORIES if not leaders[key]]
    if missing:
        raise RuntimeError('Official player-stat categories missing: ' + ', '.join(missing))

    stats = json.loads(DATA.read_text(encoding='utf-8')).setdefault('stats', {})
    stats['leaders'] = {key: values[:5] for key, values in leaders.items()}
    stats['leaders_source'] = URL
    DATA.write_text(json.dumps(json.loads(DATA.read_text(encoding='utf-8')), indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print('Official player-stat categories refreshed:', ', '.join(CATEGORIES))


if __name__ == '__main__':
    main()

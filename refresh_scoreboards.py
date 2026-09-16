import json, re, time
from pathlib import Path
from datetime import date, timedelta
import requests

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'scoreboard' / 'scoreboard-data.json'
ESPN = 'https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard'
WEEKS = [
    ('2026-08-27','2026-08-30','WEEK 0 • AUG 27–30'),
    ('2026-09-03','2026-09-06','WEEK 1 • SEP 3–6'),
    ('2026-09-10','2026-09-13','WEEK 2 • SEP 10–13'),
    ('2026-09-17','2026-09-20','WEEK 3 • SEP 17–20'),
    ('2026-09-24','2026-09-27','WEEK 4 • SEP 24–27'),
    ('2026-10-01','2026-10-04','WEEK 5 • OCT 1–4'),
    ('2026-10-08','2026-10-11','WEEK 6 • OCT 8–11'),
    ('2026-10-15','2026-10-18','WEEK 7 • OCT 15–18'),
    ('2026-10-22','2026-10-25','WEEK 8 • OCT 22–25'),
    ('2026-10-29','2026-11-01','WEEK 9 • OCT 29–NOV 1'),
    ('2026-11-05','2026-11-08','WEEK 10 • NOV 5–8'),
    ('2026-11-12','2026-11-15','WEEK 11 • NOV 12–15'),
    ('2026-11-19','2026-11-22','WEEK 12 • NOV 19–22'),
]


def norm(s):
    s = re.sub(r'\s*\([^)]*\)\s*$', '', str(s or ''))
    return re.sub(r'[^a-z0-9]', '', re.sub(r'\s+', ' ', s).strip().lower())


def same(a, b):
    x, y = norm(a), norm(b)
    return bool(x and y and (x == y or x in y or y in x))


def team_name(t):
    return t.get('team', {}).get('displayName') or t.get('team', {}).get('shortDisplayName') or t.get('team', {}).get('name') or ''


def team_id(t):
    return str(t.get('team', {}).get('id') or t.get('id') or '')


def event_team_ids(ev):
    return {team_id(t) for t in (ev.get('competitions') or [{}])[0].get('competitors', []) if team_id(t)}


def get_json(session, params):
    r = session.get(ESPN, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def fetch_events(session, start, end, groups=None):
    params = {'dates': f'{start.replace("-", "")}-{end.replace("-", "")}', 'limit': 1000}
    if groups:
        params['groups'] = groups
    try:
        payload = get_json(session, params)
        events = payload.get('events') or []
    except Exception:
        events = []
    # Fallback to one day at a time if a date-range request is unavailable.
    if not events:
        cur = date.fromisoformat(start)
        stop = date.fromisoformat(end)
        while cur <= stop:
            p = {'dates': cur.strftime('%Y%m%d'), 'limit': 1000}
            if groups:
                p['groups'] = groups
            try:
                payload = get_json(session, p)
                events.extend(payload.get('events') or [])
            except Exception as exc:
                print(f'WARN {cur}: {exc}')
            cur += timedelta(days=1)
            time.sleep(0.15)
    return events


def compact_event(ev):
    comp = (ev.get('competitions') or [{}])[0]
    teams = comp.get('competitors') or []
    rows = []
    for t in teams:
        team = t.get('team') or {}
        rows.append({
            'id': str(team.get('id') or t.get('id') or ''),
            'name': team.get('displayName') or team.get('shortDisplayName') or team.get('name') or 'Team',
            'shortName': team.get('shortDisplayName') or team.get('abbreviation') or '',
            'abbreviation': team.get('abbreviation') or '',
            'logo': team.get('logo') or (team.get('logos') or [{}])[0].get('href') or '',
            'homeAway': t.get('homeAway') or '',
            'score': t.get('score'),
        })
    st = comp.get('status', {}).get('type', {})
    return {
        'id': str(ev.get('id') or ''),
        'date': ev.get('date') or '',
        'name': ev.get('name') or '',
        'shortName': ev.get('shortName') or '',
        'teams': rows,
        'status': {'state': st.get('state'), 'completed': bool(st.get('completed')), 'detail': st.get('shortDetail') or st.get('detail') or ''},
        'venue': ((comp.get('venue') or {}).get('fullName') or ''),
        'city': ((comp.get('venue') or {}).get('address') or {}).get('city') or '',
        'state': ((comp.get('venue') or {}).get('address') or {}).get('state') or '',
        'broadcasts': [b.get('names', [None])[0] for b in (comp.get('broadcasts') or []) if b.get('names')],
    }


def main():
    data = json.loads((ROOT / 'data.json').read_text(encoding='utf-8'))
    rankings = (data.get('fcs_top25') or data.get('fcs_top20') or [])[:25]
    assert len(rankings) == 25, f'Expected 25 FCS rankings, found {len(rankings)}'

    session = requests.Session()
    session.headers.update({'User-Agent': 'GrizHQ/scoreboard-refresh'})
    all_weeks = []
    for start, end, label in WEEKS:
        events = {}
        for ev in fetch_events(session, start, end):
            if ev.get('id'):
                events[str(ev['id'])] = ev
        # Big Sky group feed is a second source for conference games/nonconference games involving Big Sky teams.
        for ev in fetch_events(session, start, end, groups='20'):
            if ev.get('id'):
                events[str(ev['id'])] = ev
        compact = [compact_event(e) for e in events.values()]
        compact.sort(key=lambda e: e['date'])
        all_weeks.append({'start': start, 'end': end, 'label': label, 'events': compact})
        print(f'{label}: {len(compact)} ESPN events')

    output = {
        'source': 'ESPN College Football scoreboard API',
        'generatedAt': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'rankings': [
            {'rank': int(r.get('rank') or i + 1), 'team': r.get('team') or r.get('name') or ''}
            for i, r in enumerate(rankings)
        ],
        'weeks': all_weeks,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(output, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'Wrote {OUT}')


if __name__ == '__main__':
    main()

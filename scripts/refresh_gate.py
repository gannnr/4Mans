"""Gate ten-minute Actions ticks using NFL kickoff dates, including postseason games."""
import csv,io,json,os,time,urllib.request
from datetime import datetime,timedelta,timezone
from pathlib import Path
from zoneinfo import ZoneInfo
SCHEDULE_URL='https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv'
def kickoff(row):
    if not row.get('gametime'):return None
    return datetime.fromisoformat(row['gameday']+'T'+row['gametime']).replace(tzinfo=ZoneInfo('America/New_York')).astimezone(timezone.utc)
def game_window(rows,now):
    # Covers pregame roster checks, normal games, overtime/delays, and postgame refreshes.
    return any(k and k-timedelta(minutes=30)<=now<=k+timedelta(hours=7) for k in (kickoff(r) for r in rows))
def decide(rows,now,last,manual=False):
    active=game_window(rows,now)
    return manual or active or not last or (now-last).total_seconds()>=3*3600,active

def main():
    now=datetime.now(timezone.utc);data=json.loads(Path('4mans_app_data.json').read_text());season=str(data['nfl_state']['season']);cache=Path('.cache/schedule.csv');cache.parent.mkdir(exist_ok=True)
    # Code-only pushes are filtered in refresh.yml; data commits cannot retrigger this.
    manual=os.getenv('GITHUB_EVENT_NAME') in ('workflow_dispatch','push');rows=[];error=None
    try:
        if not cache.exists() or time.time()-cache.stat().st_mtime>86400:
            req=urllib.request.Request(SCHEDULE_URL,headers={'User-Agent':'4MANS/2.0'})
            with urllib.request.urlopen(req,timeout=20) as r:raw=r.read().decode()
            parsed=list(csv.DictReader(io.StringIO(raw)))
            if not any(x['season']==season for x in parsed):raise ValueError('Current season schedule missing')
            cache.write_text(raw)
        rows=[r for r in csv.DictReader(io.StringIO(cache.read_text())) if r['season']==season and r['game_type'] in ('REG','WC','DIV','CON','SB')]
        if not rows:raise ValueError('No current-season games')
    except Exception as e:error=str(e)
    last=datetime.fromisoformat(data['generated_at'].replace('Z','+00:00'))
    run,active=decide(rows,now,last,manual)
    if error:run=True;active=True;print('Schedule unavailable; refresh rather than risk skipping a game:',error)
    reason='manual' if manual else 'game window' if active else 'three-hour baseline' if run else 'outside game window; saved data is current'
    print(reason)
    if os.getenv('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'],'a') as f:f.write(f'run={str(run).lower()}\ngame_window={str(active).lower()}\n')
if __name__=='__main__':main()

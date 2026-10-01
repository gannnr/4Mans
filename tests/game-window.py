import importlib.util
import tempfile,os,json,io,contextlib
from unittest.mock import patch
from datetime import datetime,timedelta,timezone
from pathlib import Path
s=importlib.util.spec_from_file_location('gate',Path(__file__).resolve().parents[1]/'scripts/refresh_gate.py');g=importlib.util.module_from_spec(s);s.loader.exec_module(g)
fixtures=[{'gameday':'2026-10-01','gametime':'20:15'},{'gameday':'2026-11-01','gametime':'09:30'},{'gameday':'2027-02-07','gametime':'18:30'}]
for row in fixtures:
 k=g.kickoff(row)
 for minutes,expected in [(-31,False),(-30,True),(180,True),(420,True),(421,False)]:assert g.game_window([row],k+timedelta(minutes=minutes))==expected
now=datetime.now(timezone.utc)
assert g.decide([],now,now-timedelta(hours=2))==(False,False)
assert g.decide([],now,now-timedelta(hours=3))==(True,False)
assert g.decide([],now,now,True)==(True,False)
assert g.kickoff(fixtures[0])==datetime(2026,10,2,0,15,tzinfo=timezone.utc)
assert g.kickoff(fixtures[1])==datetime(2026,11,1,14,30,tzinfo=timezone.utc)
original=os.getcwd()
try:
 with tempfile.TemporaryDirectory() as directory:
  os.chdir(directory);Path('.cache').mkdir()
  Path('.cache/schedule.csv').write_text('season,game_type,gameday,gametime\n2026,REG,2026-01-01,12:00\n')
  Path('4mans_app_data.json').write_text(json.dumps({'nfl_state':{'season':'2026'},'generated_at':datetime.now(timezone.utc).isoformat()}))
  for event,expected in [('push',True),('workflow_dispatch',True),('schedule',False)]:
   Path('outputs').write_text('')
   with patch.dict(os.environ,{'GITHUB_EVENT_NAME':event,'GITHUB_OUTPUT':'outputs'}),contextlib.redirect_stdout(io.StringIO()):g.main()
   assert 'run='+str(expected).lower() in Path('outputs').read_text()
finally:os.chdir(original)
print('PASS: updater-code pushes and manual dispatch force refresh; scheduled ticks still respect the baseline.')
print('PASS: kickoff buffers, international morning games, DST change, February postseason, baseline and manual refresh.')

import importlib.util
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
print('PASS: kickoff buffers, international morning games, DST change, February postseason, baseline and manual refresh.')

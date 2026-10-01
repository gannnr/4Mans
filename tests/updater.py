import importlib.util,pathlib,tempfile,os,contextlib,io,sys
sys.dont_write_bytecode=True
root=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('updater',root/'update_4mans.py');u=importlib.util.module_from_spec(spec);spec.loader.exec_module(u)
rows=[{'manager':m['key'],'pf':100 if i<2 else 90-i} for i,m in enumerate(u.MANAGERS)]
u.add_places(rows);assert [r['place'] for r in rows]==[1,1,3,4]
pay,wins=u.current_winnings_snapshot([{'totals':rows}]);assert sum(pay.values())==0;assert pay['nactasty']==5;assert pay['jpagonis']==5
for leader_count in range(1,5):
 r=[{'manager':m['key'],'pf':100 if i<leader_count else 50} for i,m in enumerate(u.MANAGERS)];pay,_=u.current_winnings_snapshot([{'totals':r}]);assert abs(sum(pay.values()))<.000001
u.SEASONS=['2026'];u.CURRENT_YEAR=2026
u.get_json=lambda url,**kw: {'season':'2026','season_type':'regular','week':3,'display_week':4} if url.endswith('/state/nfl') else {'user_id':'1'} if '/user/'in url else {'p'+str(i):{'full_name':'Test Player','position':'WR','team':'TEN'} for i in range(1000)}
u.discover_leagues=lambda *a:[{'league_id':'test','name':'Test League'}]
u.fetch_rosters=lambda *a:[{'roster_id':i+1,'owner_id':m['user_id'],'players':['p1']} for i,m in enumerate(u.MANAGERS)]
u.fetch_members=lambda *a:{}
u.get_matchup_week=lambda lid,week:[{'roster_id':i+1,'matchup_id':i//2,'points':100-i*10 if week==1 else 0,'players':['p1'],'starters':['p1'],'players_points':{'p1':100-i*10 if week==1 else 0}} for i in range(4)] if week in (1,4) else []
u.fetch_stats_feed=lambda *a:{'p1':{'rec':1}};u.fetch_schedule_feed=lambda *a:[];u.fetch_week_stats_feed=lambda *a:{}
original=os.getcwd()
try:
 with tempfile.TemporaryDirectory() as directory:
  os.chdir(directory)
  with contextlib.redirect_stdout(io.StringIO()):u.build()
  import json
  data=json.load(open('4mans_app_data.json'));season=data['seasons']['2026'];league=season['leagues'][0]
  assert data['nfl_state']['display_week']==4
  assert len(league['current_rosters'])==4
  pending=next(w for w in league['weeks'] if w['week']==4);assert pending['awaiting_scores'] is True;assert len(pending['rosters'])==4;assert all(r['pf']==0 for r in pending['rosters'])
  assert len(league['weeks'])==2;assert season['poll_history'][-1]['week']==1
  assert [r['pf'] for r in league['totals']]==[100,90,80,70]
  # A second incremental run reuses old week 1 and preserves PF, PA and player points.
  old_week=next(w for w in league['weeks'] if w['week']==1)
  old_scores=[(r['pf'],r['pa']) for r in old_week['rosters']]
  def later_matchups(lid,week):
   if week==1:raise AssertionError('Old week 1 must not be fetched again')
   return [{'roster_id':i+1,'matchup_id':i//2,'points':0,'players':['p1'],'starters':['p1'],'players_points':{'p1':0}} for i in range(4)] if week==4 else []
  u.get_matchup_week=later_matchups
  with contextlib.redirect_stdout(io.StringIO()):u.build()
  second=json.load(open('4mans_app_data.json'));league2=second['seasons']['2026']['leagues'][0]
  assert [(r['pf'],r['pa']) for r in next(w for w in league2['weeks'] if w['week']==1)['rosters']]==old_scores
  assert [r['pf'] for r in league2['totals']]==[100,90,80,70]
finally:os.chdir(original)
print('PASS: matching Python/browser tie rule, competition ranks, actual display week, pending-week rosters, current ownership snapshot and unchanged cumulative totals.')

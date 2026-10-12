"""Provisional optimal best-ball points; exact position eligibility; no dependencies."""
from math import isfinite
FLEX={"FLEX":{"RB","WR","TE"},"SUPER_FLEX":{"QB","RB","WR","TE"},"REC_FLEX":{"WR","TE"},"WRRB_FLEX":{"WR","RB"},"IDP_FLEX":{"DL","LB","DB","DE","DT","CB","S","SS","FS","EDGE","ILB","OLB"}}
ALIASES={"DL":{"DL","DE","DT","EDGE"},"LB":{"LB","ILB","OLB","EDGE"},"DB":{"DB","CB","S","SS","FS"}}
IGNORED={"BN","IR","TAXI","RESERVE"}
def eligible(slot,data):
    allowed=FLEX.get(slot,ALIASES.get(slot,{slot}))
    positions={str(x).upper() for x in data.get("fantasy_positions") or [] if x}
    if data.get("position"):positions.add(str(data["position"]).upper())
    return bool(positions & allowed)
def bestball_lineup(matchup,roster_positions,player_map):
    slots=[str(s).upper() for s in roster_positions if str(s).upper() not in IGNORED]
    players=list(dict.fromkeys(str(p) for p in matchup.get("players") or [] if p))
    raw=matchup.get("players_points") or {}
    if not slots or not players or len(slots)>30 or any(not isinstance(player_map.get(p),dict) for p in players):return None
    try: points={p:float(raw.get(p,0)) for p in players}
    except (ValueError,TypeError):return None
    if not all(isfinite(v) for v in points.values()):return None
    original={str(p) for p in matchup.get("starters") or [] if p}
    n=len(slots); candidates=players+["__empty_"+str(i) for i in range(n)];m=len(candidates)
    weights=[[(-100000.0 if p.startswith("__empty_") else points[p]+(0.000001 if p in original else 0) if eligible(slot,player_map[p]) else -100000000.0) for p in candidates] for slot in slots]
    u=[0.0]*(n+1);v=[0.0]*(m+1);match=[0]*(m+1);way=[0]*(m+1)
    for i in range(1,n+1):
        match[0]=i;j0=0;minv=[float("inf")]*(m+1);used=[False]*(m+1)
        while True:
            used[j0]=True;i0=match[j0];delta=float("inf");j1=0
            for j in range(1,m+1):
                if not used[j]:
                    cur=-weights[i0-1][j-1]-u[i0]-v[j]
                    if cur<minv[j]:minv[j]=cur;way[j]=j0
                    if minv[j]<delta:delta,j1=minv[j],j
            for j in range(m+1):
                if used[j]:u[match[j]]+=delta;v[j]-=delta
                else:minv[j]-=delta
            j0=j1
            if match[j0]==0:break
        while True:
            j1=way[j0];match[j0]=match[j1];j0=j1
            if j0==0:break
    assignment=[None]*n
    for j in range(1,m+1):
        if match[j]:assignment[match[j]-1]=candidates[j-1]
    chosen=[p for p in assignment if p and not p.startswith("__empty_")]
    if len(chosen)!=n or any(not eligible(s,player_map[p]) for s,p in zip(slots,assignment)):return None
    return {"points":round(sum(points[p] for p in chosen),2),"starters":chosen,"bench":[p for p in players if p not in chosen],"slots":slots}

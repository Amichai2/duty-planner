"""Hourly CP-SAT personnel rostering engine. All times are hours since horizon start."""
from collections import defaultdict
from ortools.sat.python import cp_model


def example():
    people = ([{'id':f'A{i}','team':'1','driver':False,'availability':[[0,48]]} for i in range(1,7)] +
              [{'id':f'B{i}','team':'2','driver':i==1,'availability':[[0,48]]} for i in range(1,17)])
    return {'hours':48,'start_offset_hours':0,'people':people,'tour_size':4,'tour_length':8,'gate_length':2,
            'carmel_team':'2','carmel_size':4,'driver':'B1','carmel_departures':[0,12],
            'carmel_exit_length':1,'carmel_rest':3,'target_rest':8,'min_rest':3,
            'hard_no_repeat_tour_night':True,'hard_no_repeat_any_night':True,
            'time_limit':35,'tour_weight':3,'gate_weight':2,'carmel_weight':1,
            'night_weight':1,'minimize_carmel_changes':True,'patrol_rest_target':16,'enable_patrol_rest_target':True,'enable_carmel_share':True,'history':[],'history_completeness':'partial'}


def validate_input(c):
    h=int(c['hours']); ids=[p['id'] for p in c['people']]
    if not 0 <= int(c.get('start_offset_hours',0)) < 24: raise ValueError('Start offset must be 0–23 hours after 06:00.')
    if any(not 0<=int(d)<24 for d in c['carmel_departures']): raise ValueError('Carmel departures must be clock hours 0–23.')
    if h<8 or h>168: raise ValueError('Planning horizon must be 8–168 hours.')
    if len(ids)!=len(set(ids)) or not ids: raise ValueError('Soldier IDs must be unique and nonempty.')
    if h%int(c['tour_length']) or h%int(c['gate_length']):
        raise ValueError('Horizon must be divisible by tour and gate shift lengths.')
    if int(c['tour_length'])<1 or int(c['gate_length'])<1: raise ValueError('Invalid shift length.')
    if c['driver'] not in ids: raise ValueError('Driver must exist in personnel.')
    if int(c['carmel_size'])<0: raise ValueError('Invalid Carmel size.')
    if str(c['carmel_team'])!='variable' and str(c['carmel_team']) not in {str(p['team']) for p in c['people']}: raise ValueError('Unknown Carmel team.')
    if int(c.get('patrol_rest_target',16))<0: raise ValueError('Patrol rest target cannot be negative.')
    for item in c.get('history',[]):
        if item.get('task') not in ('סיור','ש״ג','כרמל'):raise ValueError('History task must be סיור, ש״ג or כרמל.')
        if item.get('soldier') not in ids:raise ValueError('Unknown soldier in history: '+str(item.get('soldier')))
        a,b=int(item['start']),int(item['end'])
        if not (a<b<=0):raise ValueError('History intervals must end at or before planning start (hour 0).')
    for p in c['people']:
        if not isinstance(p.get('availability',[]),list):raise ValueError('Availability must be a list of windows.')
        for a,b in p.get('availability',[[0,h]]):
            if not (0<=int(a)<int(b)<=h): raise ValueError('Availability windows must fit the horizon.')


def solve(c):
    validate_input(c)
    h=int(c['hours']); people=c['people']; ids=[p['id'] for p in people]
    team={p['id']:str(p['team']) for p in people}; driver=c['driver'];
    avail={p['id']:{t for a,b in p.get('availability',[[0,h]]) for t in range(int(a),int(b))} for p in people}
    tour_len=int(c['tour_length']); gate_len=int(c['gate_length']); size=int(c['tour_size']); car_size=int(c['carmel_size'])
    start_clock=(6+int(c.get('start_offset_hours',0)))%24
    departures={(int(d)-start_clock)%24+k*24 for k in range(0,h//24+2) for d in c['carmel_departures'] if (int(d)-start_clock)%24+k*24<h}
    exit_len=int(c.get('carmel_exit_length',1)); car_rest=int(c['carmel_rest']); min_rest=int(c['min_rest']); target=int(c['target_rest'])
    teams=sorted(set(team.values()))
    model=cp_model.CpModel()
    ts=list(range(0,h,tour_len)); gs=list(range(0,h,gate_len))
    # Each patrol shift is staffed by one organic team.
    use_team={(s,g):model.NewBoolVar(f'team_{s}_{g}') for s in ts for g in teams}
    tour={(i,s):model.NewBoolVar(f'tour_{i}_{s}') for i in ids if i!=driver for s in ts}
    gate={(i,s):model.NewBoolVar(f'gate_{i}_{s}') for i in ids if i!=driver for s in gs}
    variable_car=str(c['carmel_team'])=='variable'
    eligible=[i for i in ids if i!=driver and (variable_car or team[i]==str(c['carmel_team']))]
    car={(i,t):model.NewBoolVar(f'car_{i}_{t}') for i in eligible for t in range(h)}
    car_team={(t,g):model.NewBoolVar(f'car_team_{t}_{g}') for t in range(h) for g in teams} if variable_car else {}
    # An organic Carmel group is required even when the team is variable.
    if variable_car:
        for t in range(h):
            model.Add(sum(car_team[t,g] for g in teams)==1)
            for i in eligible:model.Add(car[i,t]<=car_team[t,team[i]])
    # The driver must be available for every Carmel departure.
    # If a driver is unavailable, reject rather than silently leaving the task uncovered.

    for s in ts:
        model.Add(sum(use_team[s,g] for g in teams)==1)
        model.Add(sum(tour[i,s] for i in ids if (i,s) in tour)==size)
        for i in ids:
            if (i,s) not in tour: continue
            model.Add(tour[i,s]<=use_team[s,team[i]])
            if any(t not in avail[i] for t in range(s,s+tour_len)): model.Add(tour[i,s]==0)
    for s in gs:
        model.Add(sum(gate[i,s] for i in ids if (i,s) in gate)==1)
        for i in ids:
            if (i,s) in gate and any(t not in avail[i] for t in range(s,s+gate_len)): model.Add(gate[i,s]==0)
    for t in range(h):
        model.Add(sum(car[i,t] for i in ids if (i,t) in car)==car_size)
        for i in ids:
            if (i,t) in car and t not in avail[i]: model.Add(car[i,t]==0)
            parts=[]
            if (i,t) in car: parts.append(car[i,t])
            if (i,(t//tour_len)*tour_len) in tour: parts.append(tour[i,(t//tour_len)*tour_len])
            if (i,(t//gate_len)*gate_len) in gate: parts.append(gate[i,(t//gate_len)*gate_len])
            if parts: model.Add(sum(parts)<=1)
        if t in departures and driver not in ids: raise ValueError('Driver missing')
    for d in departures:
        if any(t not in avail[driver] for t in range(d,min(h,d+exit_len))):
            raise ValueError(f'Driver {driver} unavailable for Carmel departure at relative hour {d}.')
    # Activities used for fatigue and night logic: tour/gate and Carmel exits only.
    acts=defaultdict(list)
    for (i,s),v in tour.items(): acts[i].append((s,s+tour_len,v,'tour'))
    for (i,s),v in gate.items(): acts[i].append((s,s+gate_len,v,'gate'))
    # Departure assignment is defined at its start; prevent switching during exit.
    for d in sorted(departures):
        for i in ids:
            if (i,d) not in car: continue
            v=car[i,d]
            for t in range(d,min(h,d+exit_len)):
                model.Add(car[i,t]==v)
            for t in range(max(0,d-car_rest),min(h,d+exit_len+car_rest)):
                if d<=t<d+exit_len: continue
                s=(t//tour_len)*tour_len
                if (i,s) in tour: model.Add(tour[i,s]+v<=1)
                s=(t//gate_len)*gate_len
                if (i,s) in gate: model.Add(gate[i,s]+v<=1)
            acts[i].append((d,min(h,d+exit_len),v,'carmel_exit'))
    # Known prior assignments are fixed facts. They can be incomplete (e.g. patrols only).
    # They are NOT decision variables and never consume new-horizon capacity.
    history_by_id=defaultdict(list)
    history_rest_shortfalls=[]
    history_patrol_shortfalls=[]
    for rec in c.get('history',[]):
        history_by_id[rec['soldier']].append((int(rec['start']),int(rec['end']),rec['task']))
    for i,records in history_by_id.items():
        for hs,he,hk in records:
            if hk=='כרמל':continue  # history Carmel entries denote definition unless explicitly active
            for s,e,v,k in acts[i]:
                gap=s-he
                required=car_rest if k=='carmel_exit' else min_rest
                if gap<required:model.Add(v==0)
                elif gap<target and k!='carmel_exit':
                    shortfalls_var=model.NewBoolVar(f'hist_rest_{i}_{hs}_{s}_{k}')
                    model.Add(shortfalls_var==v)
                    history_rest_shortfalls.append((target-gap)*shortfalls_var)
                if hk=='סיור' and k=='tour' and c.get('enable_patrol_rest_target',True):
                    patrol_target=int(c.get('patrol_rest_target',16))
                    if gap<patrol_target:history_patrol_shortfalls.append((patrol_target-gap)*v)
    # Minimum rest between consecutive active tasks; enforce all pairs for safety.
    shortfalls=list(history_rest_shortfalls)
    for i,events in acts.items():
        for a,(s1,e1,v1,k1) in enumerate(events):
            for s2,e2,v2,k2 in events[a+1:]:
                if s2>=e1: gap=s2-e1
                elif s1>=e2: gap=s1-e2
                else: gap=-1
                required=car_rest if 'carmel_exit' in (k1,k2) else min_rest
                if gap<required: model.Add(v1+v2<=1)
                elif gap<target and k1!='carmel_exit' and k2!='carmel_exit':
                    violation=model.NewBoolVar(f'short_{i}_{s1}_{s2}_{k1}_{k2}')
                    model.Add(violation>=v1+v2-1)
                    shortfalls.append((target-gap)*violation)
    # Real clock nights 00:00–06:00, independent of the planning start.
    nights=[]
    for day in range(-1,h//24+3):
        lo=day*24-start_clock;hi=lo+6
        if lo<h and hi>0:nights.append((max(0,lo),min(h,hi)))
    # Map absolute clock-night windows spanning the past and planning horizon.
    # A night is identified by the calendar day on which 00:00-06:00 occurs.
    # If history has a duty in the preceding night, prohibit the same soldier
    # from working in the immediately following night when enabled.
    history_night=defaultdict(set)
    history_patrol_night=defaultdict(set)
    for i,records in history_by_id.items():
        for hs,he,hk in records:
            if hk not in ('סיור','ש״ג'):continue
            for day in range(-10, h//24+3):
                lo=day*24-start_clock;hi=lo+6
                if hs<hi and he>lo:history_night[i].add(day)
                # Patrol-night definition 22:00-06:00 ending on 'day'.
                if hk=='סיור' and hs<hi and he>lo-2:history_patrol_night[i].add(day)
    for i in ids:
        for s,e,v,k in acts[i]:
            if k not in ('tour','gate'):continue
            for day in range(-1,h//24+3):
                lo=day*24-start_clock;hi=lo+6
                if c.get('hard_no_repeat_any_night',True) and (day-1 in history_night[i] or day+1 in history_night[i]) and s<hi and e>lo:
                    model.Add(v==0)
                if k=='tour' and c.get('hard_no_repeat_tour_night',True) and (day-1 in history_patrol_night[i] or day+1 in history_patrol_night[i]) and s<hi and e>lo-2:
                    model.Add(v==0)
    night_flags={}
    for i in ids:
        for n,(lo,hi) in enumerate(nights):
            active=[v for s,e,v,k in acts[i] if k in ('tour','gate') and s<hi and e>lo]
            flag=model.NewBoolVar(f'night_{i}_{n}')
            if active:
                model.AddMaxEquality(flag,active)
            else: model.Add(flag==0)
            night_flags[i,n]=flag
        for n in range(len(nights)-1):
            if c.get('hard_no_repeat_any_night',True):model.Add(night_flags[i,n]+night_flags[i,n+1]<=1)
            if c.get('hard_no_repeat_tour_night',True):
                x=[v for s,e,v,k in acts[i] if k=='tour' and s<nights[n][1] and e>nights[n][0]]
                y=[v for s,e,v,k in acts[i] if k=='tour' and s<nights[n+1][1] and e>nights[n+1][0]]
                if x and y: model.Add(sum(x)+sum(y)<=1)
    # Soft target: 16 hours (configurable) between successive patrols.
    # Penalize every too-close pair: if a pair is both selected and consecutive,
    # it necessarily appears here, so there is no way to hide a short gap.
    patrol_shortfalls=list(history_patrol_shortfalls)
    if c.get('enable_patrol_rest_target',True):
        desired=int(c.get('patrol_rest_target',16))
        for i in ids:
            for s in ts:
                for u in ts:
                    if u<=s or (i,s) not in tour or (i,u) not in tour:continue
                    gap=u-(s+tour_len)
                    if 0<=gap<desired:
                        v=model.NewBoolVar(f'patrol_rest_short_{i}_{s}_{u}')
                        model.Add(v>=tour[i,s]+tour[i,u]-1)
                        patrol_shortfalls.append((desired-gap)*v)
    # Carmel team share is based on eligible soldier-hours, not just headcounts.
    # The driver is excluded. Use aggregate deviation in soldier-hours to avoid fractions.
    share_deviations=[]
    if variable_car and c.get('enable_carmel_share',True):
        capacity={g:sum(len(avail[i]) for i in eligible if team[i]==g) for g in teams}
        total_capacity=sum(capacity.values())
        if total_capacity>0:
            for g in teams:
                actual=sum(car[i,t] for i in eligible if team[i]==g for t in range(h))
                dev=model.NewIntVar(0,h*car_size*total_capacity,f'carmel_share_deviation_{g}')
                model.AddAbsEquality(dev,actual*total_capacity-h*car_size*capacity[g])
                share_deviations.append(dev)
    # Minimize changes in Carmel definitions and weighted per-person load imbalance.
    changes=[]
    if c.get('minimize_carmel_changes',True):
        for i in ids:
            for t in range(1,h):
                if (i,t) in car:
                    delta=model.NewBoolVar(f'change_{i}_{t}')
                    model.AddAbsEquality(delta,car[i,t]-car[i,t-1]);changes.append(delta)
    weights={'tour':int(c['tour_weight']),'gate':int(c['gate_weight']),'carmel_exit':int(c['carmel_weight'])}
    loads=[]
    for i in ids:
        if i==driver:continue
        weighted=sum((e-s)*weights[k]*v for s,e,v,k in acts[i])
        available=max(1,len(avail[i])); scaled=model.NewIntVar(0,100000,f'load_{i}')
        model.Add(scaled*available>=weighted*100)
        model.Add(scaled*available<=weighted*100+available-1)
        loads.append(scaled)
    spread=model.NewIntVar(0,100000,'load_spread')
    if loads:
        mx=model.NewIntVar(0,100000,'maxload');mn=model.NewIntVar(0,100000,'minload')
        model.AddMaxEquality(mx,loads);model.AddMinEquality(mn,loads);model.Add(spread==mx-mn)
    else:model.Add(spread==0)
    # Soft penalties ordered approximately: rest > load > Carmel changes.
    # Lexicographic-style priority using provable upper bounds for lower tiers.
    # Hard constraints (including repeat-night flags) are already enforced above.
    model.Minimize(sum(shortfalls)*10000000 + sum(patrol_shortfalls)*100000 + spread*10 + sum(share_deviations) + sum(changes))
    solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=float(c.get('time_limit',35));solver.parameters.num_search_workers=8
    status=solver.Solve(model)
    label=solver.StatusName(status)
    if status not in (cp_model.OPTIMAL,cp_model.FEASIBLE):return {'status':label,'message':'No verified feasible roster. Consider relaxing night/rest constraints or changing staffing.'}
    shifts=[]
    for s in ts:
        shifts.append({'task':'סיור','start':s,'end':s+tour_len,'soldiers':[i for i in ids if (i,s) in tour and solver.Value(tour[i,s])],'team':next(g for g in teams if solver.Value(use_team[s,g]))})
    for s in gs:
        shifts.append({'task':'ש״ג','start':s,'end':s+gate_len,'soldiers':[i for i in ids if (i,s) in gate and solver.Value(gate[i,s])],'team':''})
    for t in range(h):
        members=[i for i in ids if (i,t) in car and solver.Value(car[i,t])]
        shifts.append({'task':'כרמל','start':t,'end':t+1,'soldiers':members+[driver],'team':(team[members[0]] if members else ''),'exit':t in departures})
    shifts.sort(key=lambda x:(x['start'],x['task']))
    metrics=[]
    for i in ids:
        p=next(p for p in people if p['id']==i)
        t_hours=sum(tour_len*solver.Value(v) for (j,s),v in tour.items() if j==i)
        g_hours=sum(gate_len*solver.Value(v) for (j,s),v in gate.items() if j==i)
        exits=sum(solver.Value(car[i,d]) for d in departures if (i,d) in car)
        night_hours=sum(max(0,min(e,hi)-max(s,lo))*solver.Value(v) for s,e,v,k in acts[i] if k in ('tour','gate') for lo,hi in nights)
        performed=sorted((s,e,k) for s,e,v,k in acts[i] if solver.Value(v))
        gaps=[performed[j+1][0]-performed[j][1] for j in range(len(performed)-1)]
        patrol_starts=sorted(s for (j,s),v in tour.items() if j==i and solver.Value(v))
        patrol_gaps=[patrol_starts[k+1]-(patrol_starts[k]+tour_len) for k in range(len(patrol_starts)-1)]
        patrol_violations=sum(g<int(c.get('patrol_rest_target',16)) for g in patrol_gaps) if c.get('enable_patrol_rest_target',True) else 0
        active_hours=t_hours+g_hours+exits*exit_len+(sum(1 for d in departures if i==driver)*exit_len if i==driver else 0)
        available_hours=len(avail[i])
        employment_pct=round(100*active_hours/available_hours,2) if available_hours else None
        load=t_hours*weights['tour']+g_hours*weights['gate']+exits*exit_len*weights['carmel_exit']+night_hours*int(c['night_weight'])
        metrics.append({'חייל':i,'צוות':team[i],'נהג':i==driver,'זמינות (שעות)':len(avail[i]),'סיור (שעות)':t_hours,'ש״ג (שעות)':g_hours,'יציאות כרמל':exits,'לילה 00–06 (שעות)':night_hours,'לילות פעילים':sum(solver.Value(night_flags[i,n]) for n in range(len(nights))),'מנוחה מינימלית (שעות)':min(gaps) if gaps else None,'מנוחה מינימלית בין סיורים':min(patrol_gaps) if patrol_gaps else None,'הפרות יעד מנוחה בין סיורים':patrol_violations,'פעילות בפועל (שעות)':active_hours,'אחוז תעסוקה':employment_pct,'עומס משוקלל':load,'עומס לשעת זמינות':round(load/max(1,len(avail[i])),2)})
    car_hours={g:sum(1 for t in range(h) if any((i,t) in car and team[i]==g and solver.Value(car[i,t]) for i in eligible)) for g in teams}
    car_target={g:round(sum(len(avail[i]) for i in eligible if team[i]==g)/max(1,sum(len(avail[i]) for i in eligible))*100,1) for g in teams}
    return {'carmel_team_hours':car_hours,'carmel_target_pct':car_target,'status':label,'shifts':shifts,'metrics':metrics,'objective':solver.ObjectiveValue(),'bound':solver.BestObjectiveBound(),'hours':h,'start_clock_hour':start_clock,'departures':sorted(departures),'history_records':len(c.get('history',[])),'history_completeness':c.get('history_completeness','partial')}


def audit(c,result):
    if 'shifts' not in result:return [{'status':'FAIL','detail':'No solution'}]
    h=int(c['hours']); issues=[]; ids={p['id']:p for p in c['people']}
    for t in range(h):
        tour=[x for x in result['shifts'] if x['task']=='סיור' and x['start']<=t<x['end']]
        gate=[x for x in result['shifts'] if x['task']=='ש״ג' and x['start']<=t<x['end']]
        car=[x for x in result['shifts'] if x['task']=='כרמל' and x['start']==t]
        if len(tour)!=1 or len(tour[0]['soldiers'])!=int(c['tour_size']):issues.append(f'Tour coverage hour {t}')
        if len(gate)!=1 or len(gate[0]['soldiers'])!=1:issues.append(f'Gate coverage hour {t}')
        if len(car)!=1 or len(car[0]['soldiers'])!=int(c['carmel_size'])+1:issues.append(f'Carmel coverage hour {t}')
        if len(tour)==1 and len({ids[i]['team'] for i in tour[0]['soldiers']})!=1:issues.append(f'Organic team hour {t}')
        if len(tour)==1 and len(gate)==1 and len(car)==1:
            all_assigned=tour[0]['soldiers']+gate[0]['soldiers']+car[0]['soldiers']
            if len(all_assigned)!=len(set(all_assigned)):issues.append(f'Overlapping assignment hour {t}')
            for i in all_assigned:
                if not any(a<=t<b for a,b in ids[i].get('availability',[[0,h]])):issues.append(f'Unavailable {i} hour {t}')
    return [{'status':'PASS' if not issues else 'FAIL','detail':v} for v in (issues or ['All coverage, availability, overlap and organic-team checks passed'])]

"""Decisiones locales de adversarios básicos. No controla personajes jugadores."""
import heapq
import combat


def plan(state,source,allow_move=True):
    combat.profile(source)
    if source.get('conditions','').strip():raise ValueError('El adversario tiene condiciones fuera del perfil automático')
    targets=[c for c in state['characters'] if not c['enemy'] and c['hp']>0]
    if not targets:return {'path':[],'target':None}
    board=state['board'];terrain=board['terrain']
    occupied={(c['x'],c['y']) for c in state['characters'] if c['id']!=source['id']}
    opponents=[c for c in state['characters'] if not c['enemy'] and c['hp']>=0]
    def target_at(x,y):
        position={**source,'x':x,'y':y}
        for target in targets:  # Stable campaign order breaks equivalent tactical ties.
            if not combat.adjacent(position,target):continue
            try:combat.basic_pair(position,target,board)
            except ValueError:continue
            return target['id']
        return None
    immediate=target_at(source['x'],source['y'])
    if immediate:return {'path':[],'target':immediate}
    if source['hp']==0 or not allow_move:return {'path':[],'target':None}  # Wait rather than overexert.
    start=(source['x'],source['y'],0)
    queue=[(0,start)];distance={start:0};previous={};goal=None
    while queue:
        cost,node=heapq.heappop(queue)
        if cost!=distance[node]:continue
        x,y,parity=node
        target=target_at(x,y)
        if target:
            goal=(node,target);break
        # Do not leave threatened squares: opportunity attacks are not implemented.
        # Treat even unknown or flat-footed opponents conservatively as threatening.
        if any(combat.adjacent({'x':x,'y':y},c) for c in opponents):continue
        for dx,dy in ((-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)):
            nx,ny=x+dx,y+dy
            if not 0<=nx<20 or not 0<=ny<20 or (nx,ny) in occupied:continue
            tile=terrain.get(f'{nx},{ny}','clear')
            if tile=='wall':continue
            diagonal=bool(dx and dy)
            if diagonal and (terrain.get(f'{x},{ny}')=='wall' or terrain.get(f'{nx},{y}')=='wall'):continue
            step=(3 if diagonal else 2) if tile=='difficult' else (2 if diagonal and parity else 1)
            nxt=(nx,ny,1-parity if diagonal else parity)
            candidate=cost+step
            if candidate>=distance.get(nxt,float('inf')):continue
            distance[nxt]=candidate;previous[nxt]=(node,step)
            heapq.heappush(queue,(candidate,nxt))
    if goal is None:
        raise ValueError('No hay un recorrido de ataque verificable sin posibles ataques de oportunidad, cobertura u otras excepciones')
    node,target=goal;steps=[]
    while node!=start:
        parent,step=previous[node];steps.append(([node[0],node[1]],step));node=parent
    steps.reverse();path=[];spent=0
    for point,step in steps:
        if spent+step>source['speed']:break
        spent+=step;path.append(point)
    if not path:raise ValueError('El terreno requiere un tipo de movimiento todavía no automatizado')
    return {'path':path,'target':target if len(path)==len(steps) else None}

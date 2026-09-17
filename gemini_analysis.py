import json, os, requests
GEMINI_MODEL=os.getenv('GEMINI_MODEL','gemini-3.8-flash')
GEMINI_URL=f'https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent'
ALLOWED_COMPETITIONS={'EPL','La Liga','Serie A','Bundesliga','Ligue 1','UCL'}
ASIAN_TO_MYANMAR={0.0:'D',0.25:'L-50',0.5:'L-100',0.75:'1+50',1.0:'1D',1.25:'1-50',1.5:'1-100',1.75:'2+50',2.0:'2D',2.25:'2-50',2.5:'2-100',2.75:'3+50',3.0:'3D',3.25:'3-50',3.5:'3-100',3.75:'4+50',4.0:'4D',4.25:'4-50',4.5:'4-100',5.0:'5D'}
RULES='''You are the Analysis Football Gemini module.\n1. Analyze only EPL, La Liga, Serie A, Bundesliga, Ligue 1, UCL.\n2. Use only supplied evidence.\n3. Never invent injuries, lineups, odds, form, xG, H2H, news, statistics, market movement or other facts.\n4. Insufficient, weak or contradictory evidence => PASS.\n5. Never alter supplied line or Myanmar odds.\n6. Keep line and Myanmar odds paired exactly.\n7. Never promise profit or force a pick.\n8. Return JSON only.'''
def validate_input(m):
    for k in ('competition','home','away','market','line','myanmar_odds'):
        if m.get(k) in (None,''): return False,f'Missing required field: {k}'
    if m['competition'] not in ALLOWED_COMPETITIONS:return False,'Competition is outside the allowed six.'
    if m['market'] not in {'OU','AH'}:return False,'Market must be OU or AH.'
    if not isinstance(m.get('evidence'),dict) or not m['evidence']:return False,'Evidence must be a non-empty object.'
    return True,'OK'
def _json(text):
    text=text.strip()
    if text.startswith('```'): text='\n'.join(x for x in text.splitlines() if not x.strip().startswith('```')).strip()
    try:return json.loads(text)
    except json.JSONDecodeError:
        a,b=text.find('{'),text.rfind('}')
        if a>=0 and b>a:return json.loads(text[a:b+1])
        raise
def analyze_match(m):
    ok,reason=validate_input(m)
    if not ok:return {'status':'PASS','reason':reason,'competition':m.get('competition'),'home':m.get('home'),'away':m.get('away'),'market':m.get('market'),'line':m.get('line'),'myanmar_odds':m.get('myanmar_odds'),'strength':'PASS'}
    key=os.getenv('GEMINI_API_KEY')
    if not key:raise RuntimeError('GEMINI_API_KEY is not set.')
    prompt={'task':'Analyze this football match using only supplied evidence.','match':m,'required_output_fields':['status','competition','home','away','market','line','myanmar_odds','strength','analysis_mm','risk_mm','final_pick_mm','evidence_used'],'status_values':['PICK','PASS'],'strength_values':['Strong','Good','Moderate','PASS']}
    payload={'contents':[{'role':'user','parts':[{'text':RULES+'\nINPUT:\n'+json.dumps(prompt,ensure_ascii=False)}]}],'generationConfig':{'temperature':0.1,'responseMimeType':'application/json'}}
    r=requests.post(GEMINI_URL,headers={'x-goog-api-key':key,'Content-Type':'application/json'},json=payload,timeout=60); r.raise_for_status(); d=r.json()
    try:text=d['candidates'][0]['content']['parts'][0]['text']
    except (KeyError,IndexError,TypeError) as e:raise RuntimeError(f'Unexpected Gemini response: {d}') from e
    out=_json(text)
    for k in ('competition','home','away','market','line','myanmar_odds'):out[k]=m[k]
    out.setdefault('status','PASS');out.setdefault('strength','PASS');out.setdefault('analysis_mm','');out.setdefault('risk_mm','');out.setdefault('final_pick_mm','');out.setdefault('evidence_used',[])
    if out['status']=='PASS':out['strength']='PASS'
    if out['status'] not in {'PICK','PASS'} or out['strength'] not in {'Strong','Good','Moderate','PASS'}:out['status']='PASS';out['strength']='PASS'
    return out
def run_connection_test():
    m={'competition':'EPL','home':'TEST HOME','away':'TEST AWAY','market':'OU','line':2.5,'myanmar_odds':'L-100','evidence':{'note':'Connection test only; no real football facts.'}}
    out=analyze_match(m)
    assert out['status']=='PASS' and out['line']==2.5 and out['myanmar_odds']=='L-100'
    return out

"""Replay the 34 established safety controls; raw review inputs remain private."""
import argparse,json,os,sys
from pathlib import Path
parser=argparse.ArgumentParser();parser.add_argument('--checkout',type=Path,required=True);parser.add_argument('--evidence',type=Path,required=True);args=parser.parse_args();ROOT=args.checkout;OUT=args.evidence
name_prefix='candidate'
os.environ['OMP_NUM_THREADS']='1';sys.path[:0]=[str(ROOT/'backend'),str(ROOT/'backend/sentiment-analysis')]
from defaketive_sentiment.registry import load_model
m=load_model();results=[]
listing={'name':json.loads((OUT/'fan-input-private.json').read_text())[0]['name']}
cases=[
 ('overheating','The fan worked normally for an hour, then overheated and melted the plug.',True),
 ('smoke','Works well most nights, but smoke came from the motor today.',True),
 ('sparks','It runs normally, but the plug sparked when I connected it.',True),
 ('burn','Good airflow, but the hot cable burned my hand.',True),
 ('shock','It works, but I got an electric shock when touching the fan.',True),
 ('Taglish smoke','Malakas ang hangin pero umusok ang motor.',True),
 ('Filipino shock','Gumagana naman pero nakuryente ako.',True),
 ('Taglish burn','Maganda pero napaso ang kamay ko sa cable.',True),
 ('Taglish overheating','Gumagana nang maayos pero sobrang init at natunaw ang plug.',True),
 ('Taglish sparks','Malakas pero may spark sa plug.',True),
 ('denied overheating','The fan did not overheat.',False),
 ('denied smoke','There was no smoke from the motor.',False),
 ('denied sparks','The plug did not spark.',False),
 ('denied burn','The cable did not burn my hand.',False),
 ('denied shock','I did not get an electric shock.',False),
 ('normal savings','Quiet airflow, tipid sa kuryente, used overnight.',False),
 ('ambient heat','It helps cool my hot room.',False),
 ('savings and genuine shock','Tipid sa kuryente,kaya sulit. Pero nakuryente ako.',True),
 ('long review hazard','Excellent normal airflow. '*250+'Then smoke came from the motor and burned my hand.',True),
 ('English normal/ambient','The room is hot but the fan works normally. The plug has not melted.',False),
 ('Filipino normal/ambient','Gumagana nang maayos ang bentilador. Mainit ang panahon pero presko ang hangin.',False),
 ('Taglish normal/ambient','Sobrang init sa kwarto pero malamig ang hangin ng fan.',False),
 ('Filipino normal powerbank','Gumagana sa powerbank magdamag, hindi maingay at walang usok.',False),
 ('Filipino denied melting','Hindi natunaw ang saksakan. Gumagana nang maayos.',False),
 ('Taglish denied melting','Okay ang fan, hindi natunaw ang plug at walang spark.',False),
 ('English melting','The fan works well, but the plug melted.',True),
 ('Filipino melting','Maayos ang fan. Natunaw ang saksakan.',True),
 ('Taglish melting','Okay ang fan pero natutunaw ang cable.',True),
]
removed=json.loads((OUT/'six-removals-private.json').read_text())
for r in removed:cases.append(('removed '+str(r['report_index'])+'/'+str(r['old_review_index']),r['exact_review'],False))
for name,text,expected in cases:
 specific=next(({'name':r['title']} for r in removed if r['exact_review']==text),listing)
 result=m.analyze(text,5,listing=specific)
 flags=sorted(set(result.get('review_tags',[]))|set(result.get('review_extra_tags',[])))
 actual='safety' in flags
 item={'case':name,'text':text,'expected_safety':expected,'actual_safety':actual,'flags':flags,'initial_sentiment':result['sentiment'],'safety_evidence':result.get('review_evidence',{}).get('safety')}
 results.append(item);print(name,expected,actual,flush=True)
 if name=='Taglish overheating':item['full_analysis']=result
 if actual and name_prefix=='candidate':assert item['safety_evidence']['spans'],name
(OUT/(name_prefix+'-controls-private.json')).write_text(json.dumps(results,ensure_ascii=False,indent=2))
assert all(x['expected_safety']==x['actual_safety'] for x in results),'SAFETY CONTROL FAILED'
print('SAFETY CONTROLS PASS',len(results))

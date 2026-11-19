"""Read-only, product-disjoint five-stage audit; private inputs stay outside Git.

Run matrix/replay/holdout in independent processes for each checkout. Profile-
derived synthetic cases are regressions, not an independent accuracy dataset.
"""
import argparse,collections,csv,hashlib,json,os,re,sqlite3,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('mode',choices=['prepare','matrix','select','replay','holdout','compare']);p.add_argument('--checkout',type=Path,required=True);p.add_argument('--evidence',type=Path,required=True);p.add_argument('--name',default='candidate');p.add_argument('--baseline-name',default='baseline');p.add_argument('--database',type=Path);p.add_argument('--expected-sha256');p.add_argument('--input',type=Path);p.add_argument('--only-indices',help='Refresh complete affected reports in an existing audit checkpoint; never a review limit');a=p.parse_args();root=a.checkout.resolve();out=a.evidence.resolve()
os.environ['OMP_NUM_THREADS']='1';os.environ['DEFAKETIVE_ORIGINAL']=str(root/'backend');sys.path[:0]=[str(root),str(root/'backend'),str(root/'backend/sentiment-analysis'),str(root/'tests')]
from defaketive_sentiment import registry,category_context as cc
from defaketive_sentiment.product_category import classify_listing,CATEGORIES
import dashboard_utils as du
FLAGS=('safety','defect','counterfeit','quality','not_as_described')
def save(name,data): (out/name).write_text(json.dumps(data,ensure_ascii=False,indent=2))
def read(name):return json.loads((out/name).read_text())
def digest(v):return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
def flagset(r):return set(r.get('review_tags') or [])|set(r.get('review_extra_tags') or [])
if a.mode=='prepare':
 if not a.database or not a.expected_sha256:p.error('prepare requires a verified backup and its expected SHA256')
 db=a.database.resolve(strict=True);assert hashlib.sha256(db.read_bytes()).hexdigest()==a.expected_sha256
 out.mkdir(mode=0o700,parents=True,exist_ok=True)
 with sqlite3.connect(db.as_uri()+'?mode=ro',uri=True) as c:
  assert c.execute('pragma integrity_check').fetchone()[0]=='ok';products=[json.loads(r[0]) for r in c.execute('select raw_json from products')]
 holdout=[]
 for filename in ('evaluation/annotated/test_all.csv','evaluation/fresh/label_batch_fresh.csv'):
  with (root/filename).open(encoding='utf-8-sig',newline='') as source:
   holdout.extend({**r,'source_file':filename} for r in csv.DictReader(source) if r.get('sentiment') in ('positive','neutral','negative') and r.get('flags') and r.get('product'))
 save('input-private.json',products);save('holdout-private.json',holdout)
 save('manifest.json',{'backup':str(db),'backup_sha256':a.expected_sha256,'categories':dict(collections.Counter(classify_listing(p) for p in products)),'holdout_policy':'Historical separately labeled data; product-disjoint from development. Label provenance is not newly adjudicated.'});sys.exit()
if a.mode=='select':
 products=read('input-private.json');excluded={r['product'] for r in read('holdout-private.json')};development=[];by=collections.defaultdict(list)
 for i,p in enumerate(products):
  if p.get('name') not in excluded:by[classify_listing(p)].append((i,p))
 selected=set()
 for cat,rows in by.items():
  usable=[(i,p) for i,p in rows if any(str(c.get('content') or '').strip() for c in p.get('comments') or [])]
  if usable:selected.add(min(usable,key=lambda pair:len(pair[1].get('comments') or []))[0])
 for i,p in enumerate(products):
  if p.get('name') in excluded:continue
  if any(re.search(r'\b(?:tipid|matipid)\s+(?:a|sa|ang|ng)?\s*kuryente\b',str(c.get('content') or ''),re.I) for c in p.get('comments') or []):selected.add(i)
  if 'Vone USB Ceiling Fan' in p.get('name',''):selected.add(i)
 selected=sorted(selected);save('selected-indices.json',selected);save('selected-input-sha.json',{str(i):digest(products[i]) for i in selected});print('COMPLETE REPORTS',len(selected),'REVIEWS',sum(len(products[i].get('comments') or []) for i in selected),flush=True)
 # Remove known development fixture products from the independently labeled set.
 dev={products[i]['name'] for i in selected};holdout=[r for r in read('holdout-private.json') if r['product'] not in dev and 'Vone USB Ceiling Fan' not in r['product']]
 unique={digest((r['product'],r['review_text'])):r for r in holdout};save('frozen-holdout-private.json',list(unique.values()));save('split-proof.json',{'development_products':len(dev),'holdout_products':len({r['product'] for r in unique.values()}),'overlap':sorted(dev & {r['product'] for r in unique.values()}),'holdout_rows':len(unique),'code_frozen_before_holdout':True});sys.exit()
if a.mode=='matrix':
 from test_product_category import TITLES,PC3_TITLES
 titles={v:k for k,v in {**TITLES,**PC3_TITLES}.items()};m=registry.load_model();rows=[]
 pairs={'safety':('I love this product! It sparked and burned my hand.','The product did not spark or overheat.'),'defect':('The product is broken and does not work.','The product is not broken and works well.'),'counterfeit':('I received a fake product, not original.','This is original, not fake.'),'quality':('The product is flimsy and poor quality.','Sturdy and excellent quality.'),'not_as_described':('I ordered blue but received red. Wrong item.','I received exactly the color and size I ordered.')}
 for cat,profile in cc._profiles()['profiles'].items():
  cases=[('positive',profile['positive_phrases'][0]),('neutral',profile['expected_behavior_phrases'][0]),('negative',profile['negative_phrases'][0]),('ambiguous',profile['ambiguous_term']),('mixed',profile['positive_phrases'][0]+' but '+profile['negative_phrases'][0]),('Filipino','Maganda at sulit. Pero umusok ang produkto.'),('Taglish','Great quality, satisfied ako! Pero umusok ang product.')]
  cases += [(f'{flag}_{kind}',text) for flag,pair in pairs.items() for kind,text in zip(('reported','denied'),pair)]
  results=[]
  for kind,text in cases:
   r=m.analyze(text,5,listing={'name':titles[cat]});ctx=r['sentiment']['category_context'];fs=flagset(r)
   assert r['label']==r['sentiment']['initial_label'] and not ctx['sentiment_overridden']
   for q in ctx.get('observations') or []:assert text[q['start']:q['end']]==q['text']
   meanings={q['interpretation'] for q in ctx.get('observations') or [] if not q['negated']}
   expected={'positive':'explicit_praise','neutral':'intended_product_behavior','negative':'explicit_complaint'}.get(kind)
   if expected:assert expected in meanings,(cat,kind,'missing literal interpretation')
   if kind=='ambiguous':assert ctx['context_signal'] is None and ctx['abstained'],(cat,kind,'did not abstain')
   issue=None
   if kind.endswith('_reported') and kind[:-9] not in fs:issue='missed_'+kind[:-9]
   if kind.endswith('_denied') and kind[:-7] in fs:issue='false_'+kind[:-7]
   if kind in ('Filipino','Taglish') and 'safety' not in fs:issue='missed_safety'
   if kind=='mixed' and not ctx.get('mixed_feedback'):issue='lost_mixed_feedback'
   results.append({'case':kind,'text':text,'initial':r['sentiment'],'flags':sorted(fs),'issue':issue})
  rows.append({'category':cat,'title':titles[cat],'cases':results,'regression_status':'pass' if not any(r['issue'] for r in results) else 'unresolved_gap'})
 save('category-matrix.json',rows);print('MATRIX',len(rows),sum(len(r['cases']) for r in rows),'GAPS',[(r['category'],[x['issue'] for x in r['cases'] if x['issue']]) for r in rows if r['regression_status']!='pass']);sys.exit()
if a.mode=='replay':
 products=json.loads(a.input.read_text()) if a.input else read('input-private.json');indices=list(range(len(products))) if a.input else read('selected-indices.json');m=registry.load_model();records=[]
 if a.only_indices:
  indices=[int(i) for i in a.only_indices.split(',')]
  records=[r for r in read(a.name+'-reports-private.json') if r['index'] not in indices]
 for i in indices:
  p=products[i];fresh=du.analyze_products([p])[0];view=du.badge_view(fresh,aspects=True)
  for row in (view.get('conclusion') or {}).get('evidence',{}).get('why',[]):
   for quote in row.get('quotes') or []:
    assert any(quote.get('text','').removesuffix('…') in str(c.get('content') or '') for c in p.get('comments') or []),(i,'ungrounded quote')
  records.append({'index':i,'input_sha256':digest(p),'fresh':fresh,'view':view});records.sort(key=lambda r:r['index']);save(a.name+'-reports-private.json',records);print(a.name,i,fresh['product_category'],len(fresh.get('comments') or []),flush=True)
 print('REPLAY COMPLETE',a.name);sys.exit()
if a.mode=='holdout':
 m=registry.load_model();rows=[]
 for r in read('frozen-holdout-private.json'):
  pred=m.analyze(r['review_text'],r['stars'],listing={'name':r['product']});expected=set(r['flags'].split(';'))-{'none'};fs=flagset(pred)
  rows.append({'id':r['id'],'product_hash':digest(r['product']),'category':classify_listing(r['product']),'confidence':r.get('confidence'),'expected_sentiment':r['sentiment'],'actual_sentiment':pred['label'],'expected_flags':sorted(expected),'actual_flags':sorted(fs),'source':r['source_file']})
 save(a.name+'-holdout.json',rows);print('HOLDOUT',len(rows),'PRODUCTS',len({r['product_hash'] for r in rows}),'INITIAL SENTIMENT MATCH',sum(r['expected_sentiment']==r['actual_sentiment'] for r in rows));sys.exit()
if a.mode=='compare':
 before=read(a.baseline_name+'-reports-private.json');after=read(a.name+'-reports-private.json');assert len(before)==len(after);changes=[]
 for x,y in zip(before,after):
  assert x['index']==y['index'] and x['input_sha256']==y['input_sha256'];p,q=x['fresh'],y['fresh'];delta=[]
  assert len(p['comments'])==len(q['comments'])
  for i,(u,v) in enumerate(zip(p['comments'],q['comments'])):
   aa=u.get('sentiment_analysis') or {};bb=v.get('sentiment_analysis') or {}
   assert aa.get('label')==bb.get('label');assert aa.get('sentiment',{}).get('probabilities')==bb.get('sentiment',{}).get('probabilities')
   fa,fb=flagset(aa),flagset(bb)
   if fa!=fb:delta.append({'review':i,'removed':sorted(fa-fb),'added':sorted(fb-fa),'text':u.get('content'),'before':aa,'after':bb})
  state=[x['view']['state'],y['view']['state']];decision=[x['view']['conclusion']['decision'],y['view']['conclusion']['decision']]
  changes.append({'index':x['index'],'category':q['product_category'],'title':q['name'],'reviews':len(q['comments']),'state':state,'decision':decision,'delta':delta})
 prefix='' if a.name=='candidate' else a.name+'-'
 save(prefix+'comparison-private.json',changes);save(prefix+'comparison-summary.json',[{k:v for k,v in row.items() if k!='delta'}|{'flag_changes':[{k:v for k,v in d.items() if k not in ('text','before','after')} for d in row['delta']]} for row in changes]);print('REPORTS',len(changes),'REVIEWS',sum(c['reviews'] for c in changes),'REMOVED SAFETY',sum('safety' in d['removed'] for c in changes for d in c['delta']),'CHANGED DECISIONS',sum(c['decision'][0]!=c['decision'][1] for c in changes))
 for c in changes:
  for d in c['delta']:
   if 'safety' in d['removed']:print('REMOVED SAFETY',c['index'],d['review'],d['text'])
  if c['decision'][0]!=c['decision'][1] or c['state'][0]!=c['state'][1]:print('VERDICT CHANGE',c['index'],c['state'],c['decision'])

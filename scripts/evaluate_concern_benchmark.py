"""Offline evaluation against explicit frozen annotations, never implicit gold.

Input sample is a JSON list containing sample_id, listing_title, review_text,
rating, category, link and sample_group. Labels use the blind annotation CSV
schema. This runner never discovers datasets or opens a reserved file itself.
"""
import argparse,csv,hashlib,json,os,pathlib,socket,subprocess,sys

FLAGS=('safety','defect','counterfeit','quality','not_as_described')
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--sample',required=True);p.add_argument('--labels',required=True);p.add_argument('--label-sha256',required=True);p.add_argument('--out',required=True);args=p.parse_args()
 assert sha(args.labels)==args.label_sha256,'Labels differ from frozen hash'
 sample=json.loads(pathlib.Path(args.sample).read_text(encoding='utf-8-sig'))
 with open(args.labels,encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
 labels={r['sample_id']:r for r in rows};ids={r['sample_id'] for r in sample}
 assert len(labels)==len(rows)==len(ids)==len(sample) and set(labels)==ids
 for r in sample:
  a=labels[r['sample_id']]
  for field in ['listing_title','review_text']:
   raw=r[field];escaped="'"+raw if raw.lstrip().startswith(('=','+','-','@')) else raw
   assert a[field]==escaped,'Source text changed'
  for flag in FLAGS:
   assert a[flag+'_label'] in ('present','absent','ambiguous')
   if a[flag+'_label']=='present':assert a[flag+'_quote'] and a[flag+'_target']
   assert all(q.strip() in r['review_text'] for q in a[flag+'_quote'].split('||') if q.strip())
 for k in list(os.environ):
  if k.startswith('DEFAKETIVE_'):del os.environ[k]
 os.environ.update(DEFAKETIVE_MODEL_MODE='hazard_badges',DEFAKETIVE_SENTIMENT_MODEL='xlmr',DEFAKETIVE_HAZARD_MODEL='learned',DEFAKETIVE_EVIDENCE_POLICY='keep',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',OMP_NUM_THREADS='1')
 def offline(*a,**k):raise RuntimeError('Offline benchmark prohibits network access')
 socket.socket.connect=offline;socket.create_connection=offline
 root=pathlib.Path(args.root).resolve();out=pathlib.Path(args.out);out.mkdir(parents=True,exist_ok=True)
 sys.path.insert(0,str(root/'backend/sentiment-analysis'))
 from defaketive_sentiment.registry import load_model
 model=load_model();results={}
 for i,r in enumerate(sample):
  a=model.analyze(r['review_text'],r.get('rating'),listing={'name':r['listing_title'],'link':r.get('link'),'product_category':r.get('category')})
  assert a['label']==a['sentiment']['initial_label'] and 'calibrated' not in a['sentiment']
  results[r['sample_id']]=a
  if (i+1)%25==0:print(i+1,'/',len(sample),flush=True)
 (out/'predictions.json').write_text(json.dumps(results,ensure_ascii=False),encoding='utf-8')
 metrics=[]
 for group in sorted({r['sample_group'] for r in sample}):
  group_ids=[r['sample_id'] for r in sample if r['sample_group']==group]
  for flag in FLAGS:
   scored=[k for k in group_ids if labels[k][flag+'_label']!='ambiguous']
   pred=lambda k:flag in results[k]['review_tags']+results[k].get('review_extra_tags',[])
   tp=sum(pred(k) and labels[k][flag+'_label']=='present' for k in scored)
   fp=sum(pred(k) and labels[k][flag+'_label']=='absent' for k in scored)
   fn=sum(not pred(k) and labels[k][flag+'_label']=='present' for k in scored)
   metrics.append(dict(sample=group,concern=flag,total=len(group_ids),scored=len(scored),ambiguous_excluded=len(group_ids)-len(scored),support=tp+fn,tp=tp,fp=fp,fn=fn,precision=tp/(tp+fp) if tp+fp else None,recall=tp/(tp+fn) if tp+fn else None,f1=2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None))
 (out/'metrics.json').write_text(json.dumps(metrics,indent=2),encoding='utf-8')
 models=root/'backend/sentiment-analysis/models'
 meta=dict(commit=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip(),sample_sha256=sha(args.sample),labels_sha256=sha(args.labels),model_version=model.model_version,models={str(f.relative_to(models)).replace('\\','/'):sha(f) for f in models.rglob('*') if f.is_file()},settings={k:v for k,v in os.environ.items() if k.startswith('DEFAKETIVE_')},python=sys.version,reference='AI annotations unless separately human-adjudicated; record provenance with label freeze')
 (out/'runtime.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
if __name__=='__main__':main()

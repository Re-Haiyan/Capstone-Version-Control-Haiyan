"""Located safety attribution and qualified evidence, independent of sentiment."""
import re
REVISION='safety-context-1'
LYRIC=re.compile(r'\bif\s+(?:i|you)\s+(?:warned|told)\s+you\b[^.!?]{0,90}?\b(?:burn|hurt)\b',re.I)
QUALIFIED=re.compile(r'\b(?:baka|bka|might|may\s+smoke|fear|afraid|worried|seems|normal|expected|manual)\b',re.I)
AMBIENT=re.compile(r'\b(?:init\s+ng\s+panahon|kasagsagan\s+ng\s+init\s+ng\s+panahon|heat\s+of\s+the\s+day)\b',re.I)
DEBRIS=re.compile(r'\b(?:a\s+piece\s+of\s+)?plastic\s+broke\s+off\s+and\s+stuck\s+to\s+the\s+(?:mat|belt),?\s+we\s+almost\s+stepped\s+on\s+it\b',re.I)
SWITCH=re.compile(r'\bpower\s+switch\s+(?:also\s+)?became\s+defective\s+and\s+we\W?re\s+unable\s+to\s+turn\s+it\s+off\s+without\s+unplugging\b',re.I)
MELT=re.compile(r'\b(?:plug|cable|charger|adapter)\s+melted\b',re.I)

def apply(review,tagged,category):
    chorus=bool(re.search(r'\[chorus\b',review,re.I));cursor=0
    for index,item in enumerate(tagged):
        raw=item['text_raw'];start=review.find(raw,cursor)
        if start>=0:cursor=start+len(raw)
        terms=item.setdefault('terms',[])
        for term in terms:
            if term.get('category')!='safety' or term.get('excluded') or term.get('negated'):continue
            span=term.get('span')
            if not span:continue
            left,right=span
            while right>left and not raw[right-1].isalnum():right-=1
            if chorus and any(m.start()<=left and right<=m.end() for m in LYRIC.finditer(raw)):
                term['excluded']='quoted_lyric';term['interpretation_reason']='Conditional lyric with chorus attribution, not a product incident'
            if any(m.start()<=left and right<=m.end() for m in AMBIENT.finditer(raw)):
                term['evidence_excluded']='ambient weather, not device hazard evidence'
        if 'safety' in item.get('tags',[]) and any(t.get('excluded')=='quoted_lyric' for t in terms):
            if not any(t.get('category')=='safety' and not t.get('excluded') and not t.get('negated') for t in terms):
                item['tags']=[f for f in item['tags'] if f!='safety']
                for key in ['scores','high_confidence']:item.get(key,{}).pop('safety',None)
                item.setdefault('suppressed',{})['safety']='quoted_lyric'
        additions=[]
        if category=='sports_fitness' and re.search(r'\b(?:walking\s*pad|walkpad|treadmill)\b',review,re.I):
            for pattern in [DEBRIS,SWITCH]:
                additions.extend((m,flag) for m in pattern.finditer(raw) for flag in ['safety','defect'])
        if category in {'charger_cable','powerbank','small_appliance','electrical_supplies'}:
            for m in MELT.finditer(raw):
                if re.search(r'\b(?:not|never|hindi|di)\s*$',raw[max(0,m.start()-20):m.start()],re.I):continue
                from .concern_attribution import _reason
                if not _reason(raw,m.span(),'',review):additions.append((m,'safety'))
        for m,flag in additions:
            item['tags']=list(dict.fromkeys([*item.get('tags',[]),flag]))
            terms.append({'ngram':m.group().lower(),'category':flag,'span':list(m.span()),'rule':REVISION,'negated':False,'severity':3})
            item.setdefault('scores',{})[flag]=3.;item.setdefault('high_confidence',{})[flag]=True
        if 'safety' not in item.get('tags',[]):continue
        following=tagged[index+1]['text_raw'] if index+1<len(tagged) else ''
        manual=bool(re.search(r'\b(?:manual|normal|expected)\b',following,re.I))
        if start>=0 and (QUALIFIED.search(raw) or manual):
            end=start+len(raw)
            if manual:
                at=review.find(following,end)
                if at>=0:end=at+len(following)
            for term in terms:
                if term.get('category')=='safety':term['evidence_contextualized']=True
            item.setdefault('evidence_context',[]).append({'category':'safety','text':review[start:end],'review_start':start,'review_end':end,'source':REVISION,'qualification':'retain reported uncertainty or expected-operation context'})

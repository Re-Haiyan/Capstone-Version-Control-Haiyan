"""Literal concern attribution and component failures; no sentiment decisions.

Rules act on individual cues. Every removal retains its original term and reason;
independent current-unit cues and other concern categories remain untouched.
"""
from __future__ import annotations
import re

REVISION = 'attribution-2'
_COMPARISON = re.compile(r'\b(?:unlike|compared to|kumpara sa|di gaya ng|hindi tulad ng)\s+(?:(?:some|other|my old|the old|ibang|dati kong)\b)[^,.;!?]*?(?=[,.;!?]|\b(?:but|pero|this one|this replacement|this cube|this item|itong|ito)\b|$)', re.I)
_OLD = re.compile(r'\b(?:(?:my|the|our)\s+old\s+(?:charger|unit|fan|cube|speaker|cable|power bank)|(?:dati|luma)\s+(?:kong|naming|na)\s+(?:charger|unit|fan|cube|speaker|cable))\b[^,.;!?]*?(?=[,.;!?]|\b(?:but|pero|this replacement|the replacement|itong bago)\b|$)', re.I)
_FEAR = re.compile(r'\b(?:akala|kala|inakala)\s+ko\s+(?:fake|peke)\b|\bi thought (?:it was |this was )?(?:fake|counterfeit)\b', re.I)
_VERIFIED = re.compile(r'^\W*(?:pero|but)\s+(?:verified\s+(?:ang|the)\s+serial|the\s+serial\s+(?:is|was)\s+verified|na-?verify\s+(?:ko\s+)?(?:ang\s+)?serial)\b', re.I)

def _reason(raw, span, following, review):
    start,end=span
    # Existing token provenance can include trailing punctuation.
    while end>start and not raw[end-1].isalnum():end-=1
    for m in re.finditer(r'\b(?:the\s+)?other\s+(?:charger|unit|fan|camera|item|product)\b[^,.;!?]*',raw,re.I):
        if m.start()<=start and end<=m.end():
            return 'explicit other-product subject, not the reviewed item'
    for m in re.finditer(r'\b(?:the\s+)?(?:magnetic\s+part|magnet)\s+is\s+not\s+weak\b',raw,re.I):
        if m.start()<=start and end<=m.end():
            return 'magnetic weakness explicitly negated'
    # A conditional lyric fragment plus an explicit chorus marker identifies
    # quoted speech, not a reported burn. Only remove the located lyric cue;
    # a real incident elsewhere in the same sentence remains independent.
    if re.search(r'\[chorus\b', review, re.I):
        lyric = re.compile(r'\bif\s+(?:i|you)\s+(?:warned|told)\s+you\b[^.!?]{0,90}?\b(?:burn|hurt)\b', re.I)
        if any(m.start()<=start and end<=m.end() for m in lyric.finditer(raw)):
            return 'conditional quoted lyric with chorus attribution, not a product incident'
    for p,reason in [(_COMPARISON,'comparison describes another product, not the reviewed item'),(_OLD,'explicit old-unit subject, not the current replacement')]:
        if p is _OLD and not re.search(r'\b(?:this replacement|the replacement|itong bago|yung bago|this one)\b', review, re.I):continue
        if any(m.start()<=start and end<=m.end() for m in p.finditer(raw)):
            return reason
    fulfilled = re.fullmatch(r'\s*sabi sa listing may (?P<part>cable|kable|charger|adapter|remote|battery) at may (?P=part) sa box[.!]?\s*', raw, re.I)
    if fulfilled and end <= raw.lower().find(' may '):
        return 'the promised accessory is explicitly present in the box'
    for fear in _FEAR.finditer(raw):
        if fear.start()<=start and end<=fear.end() and (_VERIFIED.search(raw[fear.end():]) or _VERIFIED.search(following)):
            return 'earlier fake suspicion explicitly resolved by verified serial'
    return None

# Each pattern asserts a concrete component failure, not generic negative tone.
_FAILURES = [
 ('toys',re.compile(r'\b(?:the\s+)?magnets?\s+(?:fell|fall|falls)\s+out\b|\b(?:natanggal|nahulog|nalaglag)\s+(?:(?:ang|yung|mga)\s+){0,2}(?:magnets?|magneto)\b',re.I)),
 ('small_appliance',re.compile(r'\b(?:biglang\s+)?namamatay\s+(?:(?:ang|yung|itong)\s+)?fan\s+kahit\s+nakasaksak\b|\b(?:fan|it)\s+(?:keeps\s+)?(?:shutting|cutting)\s+off\s+(?:even\s+)?(?:while|when|despite being)\s+plugged\s+in\b',re.I)),
 ('audio',re.compile(r'\b(?:has|have|produces?)\s+no\s+(?:audio|sound)(?!\s+(?:problems?|issues?))\b|\bwalang\s+(?:audio|tunog)\s+(?:(?:ang|yung)\s+)?(?:soundbar|speaker)\b|\b(?:soundbar|speaker)\s+(?:ay\s+)?walang\s+(?:audio|tunog)\b',re.I)),
]
_MISSING = re.compile(r'\b(?:sabi sa listing may|the listing (?:says|includes)|listing says may|nakalagay sa listing may)\s+(?:a\s+)?(?P<part>cable|kable|charger|adapter|remote|battery)\b[^.!?;]{0,50}?\b(?:pero\s+wala\s+sa\s+(?:box|kahon)|but\s+(?:it\s+is\s+)?missing\s+from\s+the\s+box)\b',re.I)

def apply(review, tagged, category):
    """Run after all detectors, before evidence is aggregated. No scores edited."""
    cursor=0
    for index,item in enumerate(tagged):
        raw=item['text_raw'];at=review.find(raw,cursor);cursor=at+len(raw) if at>=0 else cursor
        following=tagged[index+1]['text_raw'] if index+1<len(tagged) else ''
        # A model-only decision can be contradicted by an explicit full-clause
        # subject/negation. Preserve a provenance record; missing evidence alone
        # is never grounds for removing a flag.
        for flag in [*item.get('tags',[]),*item.get('extra_tags',[])]:
            if any(t['category']==flag for t in [*item.get('terms',[]),*item.get('extra_terms',[])]):continue
            if _reason(raw,[0,len(raw)],following,review):
                item.setdefault('extra_terms' if flag in {'quality','not_as_described'} else 'terms',[]).append({'category':flag,'span':[0,len(raw)],'source':'model_only_attributed_clause'})
        terms=[*item.get('terms',[]),*item.get('extra_terms',[])]
        removed=set()
        for term in terms:
            # Unlocated spelling/model cues can still have an explicit whole-clause subject.
            # This is grammatical attribution, never suppression based on missing evidence.
            span=term.get('span') or [0,len(raw)]
            if term.get('excluded') or term.get('negated'):continue
            reason=_reason(raw,span,following,review)
            if reason:
                term['excluded']='attribution';term['interpretation_reason']=reason;removed.add(term['category'])
                item.setdefault('concern_interpretations',[]).append({'category':term['category'],'text':raw[span[0]:span[1]],'reason':reason,'source':REVISION})
        for flag in removed:
            if any(t['category']==flag and not t.get('excluded') and not t.get('negated') for t in terms):continue
            for key in ['tags','extra_tags']:
                item[key]=[t for t in item.get(key,[]) if t!=flag]
            for key in ['scores','high_confidence']:item.get(key,{}).pop(flag,None)
            item.setdefault('suppressed',{})[flag]=REVISION
        if category in {'charger_cable','powerbank','small_appliance','electrical_supplies'}:
            for m in re.finditer(r'\b(?:natunaw|tunaw)\s+(?:(?:ang|yung|mga)\s+){0,2}(?:plug|cable|kable|charger|adapter)\b|\b(?:plug|cable|charger|adapter)\s+melted\b',raw,re.I):
                if re.search(r'\b(?:hindi|di|walang)\s*$',raw[max(0,m.start()-20):m.start()],re.I):continue
                if _reason(raw,m.span(),following,review):continue
                item['tags']=list(dict.fromkeys([*item.get('tags',[]),'safety']))
                item.setdefault('terms',[]).append({'ngram':m.group().lower(),'category':'safety','severity':3,'negated':False,'span':list(m.span()),'rule':REVISION})
                item.setdefault('scores',{})['safety']=3.;item.setdefault('high_confidence',{})['safety']=True
        for kind,pattern in _FAILURES:
            if kind!=category:continue
            for m in pattern.finditer(raw):
                if re.search(r'\b(?:not|never|hindi|di)\s*$',raw[max(0,m.start()-20):m.start()],re.I):continue
                if _reason(raw,m.span(),following,review):continue
                item['tags']=list(dict.fromkeys([*item.get('tags',[]),'defect']))
                item.setdefault('terms',[]).append({'ngram':m.group().lower(),'category':'defect','severity':2,'negated':False,'span':list(m.span()),'rule':REVISION})
                item.setdefault('scores',{})['defect']=2.;item.setdefault('high_confidence',{})['defect']=True
    from .concern_development import add_supported_concerns
    add_supported_concerns(review, tagged, category, _reason)
    # A listing claim and an omitted accessory form one claim across split clauses.
    for m in _MISSING.finditer(review):
        cursor=0
        for item in tagged:
            raw=item['text_raw'];at=review.find(raw,cursor);cursor=at+len(raw) if at>=0 else cursor
            if at>=0 and at<=m.start()<at+len(raw):
                item['extra_tags']=list(dict.fromkeys([*item.get('extra_tags',[]),'not_as_described']))
                item.setdefault('evidence_context',[]).append({'category':'not_as_described','text':m.group(),'review_start':m.start(),'review_end':m.end(),'source':REVISION})
                break

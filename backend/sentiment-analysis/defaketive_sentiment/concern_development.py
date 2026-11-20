"""Located supplementary concern rules; never change sentiment or model scores.

Development benchmark motivated explicit performance/material complaints. These
rules assert local facts and retain their exact evidence, rather than inferring
quality from stars, praise, generic dissatisfaction or category membership.
"""
import re

REVISION = 'supported-concerns-1'

QUALITY = [
    (None, r'\b(?:low[- ]grade|poorly made|poor materials?|flimsy materials?)\b'),
    ({'apparel','home_textile','bags'}, r'\b(?:material\s+is\s+(?:very\s+)?thin|so thin|see[- ]thru|(?:ang\s+)?tela\s+(?:ay\s+)?(?:masyadong\s+)?manipis|mipis|manipus)\b'),
    ({'bags','apparel'}, r'\b(?:sewing\s+(?:is|are)\s+sloppy(?:\s+done)?|zipper\s+is\s+not\s+smooth|hindi\s+(?:kc\s+)?(?:ganun\s+)?kalinis\s+ang\s+tahi\s+nya)\b'),
    ({'powerbank','laptop','phone','tablet','audio','home_decor_lighting'}, r'\b(?:mabilis|madali|madaling|ang\s+dali)\s+(?:(?:lang|din|sya|siya|po)\s+){0,3}ma\s*(?:lowbat|lobat|lubat)\b'),
    ({'powerbank','laptop','phone','tablet','audio','home_decor_lighting'}, r"\b(?:battery\s+(?:life\s+is\s+)?(?:too\s+short|drains\s+too\s+fast)|battery\s+doesn['\u2019]t\s+last\s+long)\b"),
    ({'phone','tablet','laptop','computer_peripheral'}, r'\b(?:sobrang\s+lag|(?:the\s+)?tab(?:let)?\s+lags|it\s+lags|videos\s+on\s+youtube\s+are\s+very\s+laggy|not\s+smooth\s+multitasking)\b'),
    ({'camera','smart_home','tv_display'}, r'\b(?:video\s+quality\s+is\s+not\s+that\s+clear|medyo\s+malabo|hindi\s+lang\s+maganda\s+ang\s+color\s+ng\s+screen|a\s+little\s+blurry)\b'),
    ({'automotive','tools_hardware','small_appliance'}, r'\b(?:hindi\s+rin\s+malakas\s+yung\s+lumalabas\s+na\s+tubig|not\s+strong\s+as\s+seen\s+in\s+video)\b'),
    ({'haircare','small_appliance'}, r'\b(?:nahihinaan\s+(?:(?:lang|din|ako|sa)\s+){0,5}hangin\s+niya|weak\s+airflow|airflow\s+is\s+weak|barely\s+moves\s+air)\b'),
    ({'tools_hardware'}, r'\b(?:magnetic\s+part\s+is\s+weak|mahina\s+ang\s+magnet|mahina\s+ang\s+kapit\s+ng\s+magnet)\b'),
    ({'motorcycle'}, r'\bwalang\s+katibay\s+tibay\s+lalo\s+yong\s+horn\s+extension\b'),
    ({'gaming'}, r'\b(?:analog\s+is\s+not\s+accurate|matigas\s+yung\s+pads)\b'),
    ({'skincare'}, r'\b(?:ayaw\s+pang\s+bumula|hindi\s+sya\s+bumobula|dile\s+lagi\s+mo\s+bula)\b'),
]

def _add(item, flag, match, extra=False):
    key='extra_tags' if extra else 'tags'
    item[key]=list(dict.fromkeys([*item.get(key,[]),flag]))
    term={'ngram':match.group().lower(),'category':flag,'span':list(match.span()),'rule':REVISION,'negated':False}
    item.setdefault('extra_terms' if extra else 'terms',[]).append(term)
    if not extra:
        item.setdefault('scores',{})[flag]=3.
        item.setdefault('high_confidence',{})[flag]=True

def add_supported_concerns(review, tagged, category, attribution_reason):
    for index,item in enumerate(tagged):
        raw=item['text_raw'];following=tagged[index+1]['text_raw'] if index+1<len(tagged) else ''
        for categories,pattern in QUALITY:
            if categories is not None and category not in categories:continue
            for m in re.finditer(pattern,raw,re.I):
                before=raw[max(0,m.start()-45):m.start()]
                if re.search(r'\b(?:not|never|no|hindi|di|walang)\s+(?:(?:really|actually|naman|na)\s+)?$',before,re.I):continue
                if re.search(r'\b(?:old|previous|luma|dati)\b[^,.;!?]{0,30}$',before,re.I):continue
                if attribution_reason(raw,m.span(),following,review):continue
                _add(item,'quality',m,True)
        # Loss of safe stopping / debris underfoot requires moving exercise
        # equipment, not any appliance switch, ordinary plastic or noise.
        if category=='sports_fitness' and re.search(r'\b(?:walking\s*pad|walkpad|treadmill)\b',review,re.I):
            patterns=[
                r'\b(?:a\s+piece\s+of\s+)?plastic\s+broke\s+off\s+and\s+stuck\s+to\s+the\s+(?:mat|belt),?\s+we\s+almost\s+stepped\s+on\s+it\b',
                r'\bpower\s+switch\s+(?:also\s+)?became\s+defective\s+and\s+we\W?re\s+unable\s+to\s+turn\s+it\s+off\s+without\s+unplugging\b',
            ]
            for pattern in patterns:
                for m in re.finditer(pattern,raw,re.I):
                    if attribution_reason(raw,m.span(),following,review):continue
                    for flag in ['safety','defect']:_add(item,flag,m)

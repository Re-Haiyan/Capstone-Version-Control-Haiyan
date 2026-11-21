"""Located supplementary concern rules; never change sentiment or model scores.

Development benchmark motivated explicit performance/material complaints. These
rules assert local facts and retain their exact evidence, rather than inferring
quality from stars, praise, generic dissatisfaction or category membership.
"""
import re

REVISION = 'quality-context-1'

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
QUALITY += [
    ({'small_appliance'}, r'\b(?:wind\s+strength\s*:\s*weak|air\s+coverage\s+is\s+(?:quite\s+)?limited|mahina\s+ang\s+buga|kulang\s+ang\s+hangin)\b'),
    ({'powerbank','charger_cable'}, r'\b(?:antagal\s+magcharge|slow\s+charger|charging\s+speed\s*:\s*not\s+fast\s+charger|(?:hinde|hindi)\s+kaya\s+mag\s*fullcharge)\b'),
    ({'powerbank','camera','small_appliance','phone','tablet','laptop','audio'}, r'\b(?:mabilis|madali|bilis)\s+(?:(?:po|siyang|syang|sya|siya|lang|din)\s+){0,3}(?:mag\s+lowbat|ma\s*lobat|ma\s*lowbat|ma\s*lubat)\b'),
    ({'automotive','household_cleaning','home_textile'}, r'\bwater\s+absorption\s*:\s*(?:sablay|poor|weak)\b'),
    ({'tablet','phone','laptop','computer_peripheral'}, r'\b(?:napakabagal|naglalag\s+gamitin|sobrang\s+laki\s+(?:parin\s+)?ng\s+delay)\b'),
    ({'audio'}, r'\b(?:sobrang\s+laki\s+(?:parin\s+)?ng\s+delay|poor\s+call\s+audio|mahina\s+ang\s+bosis)\b'),
    ({'stationery_books','tablet'}, r'\b(?:the\s+)?screen\s+is\s+(?:a\s+bit\s+)?blurry\b'),
    ({'bags'}, r'\bparang\s+namumuti\s+sya\b'),
    ({'kitchen_dining'}, r'\b(?:very\s+)?poor\s+insul(?:ation|qtion)\b'),
    ({'haircare'}, r'\bfrizzes\s+hair\s+too\b'),
]
THIN=re.compile(r'\b(?:thin|see[- ]thru|mipis|manipus|manipis)\b',re.I)
NEGATIVE_MATERIAL=re.compile(r"\b(?:not\s+happy|not\s+satisfied|poor|flimsy|too\s+thin|pangit|panget|pngit|nd\s+xa\s+mganda|disappoint\w*)\b",re.I)

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
                # Thin fabric can be the desired breathable/airy design. Only
                # a stated material complaint makes this an added concern.
                previous=tagged[index-1]['text_raw'] if index else ''
                if THIN.search(m.group()) and not NEGATIVE_MATERIAL.search(previous+' '+raw):continue
                before=raw[max(0,m.start()-45):m.start()]
                if re.search(r'\b(?:not|never|no|hindi|di|walang)\s+(?:(?:a|really|actually|naman|na)\s+)?$',before,re.I):continue
                if re.search(r'\b(?:other|old|previous|luma|dati)\b[^,.;!?]{0,30}$',before,re.I):continue
                if attribution_reason(raw,m.span(),following,review):continue
                _add(item,'quality',m,True)


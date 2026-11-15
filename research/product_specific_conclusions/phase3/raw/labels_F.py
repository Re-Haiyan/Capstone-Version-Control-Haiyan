# Claude-assisted labels for Phase 3 sheet F (fresh final set). Written AFTER the extractor was frozen (phase3/frozen_extractor.json, commit c163605)
# and BEFORE the extractor was run on any F row. Blind: no system output. Same rules as D1 and D2.
L = {
 "001": "functionality:P texture:P", "006": "seller:N", "007": "appearance:P build:P", "009": "delivery:P", "012": "packaging:N arrival:P",
 "014": "matches_listing:N seller:N", "015": "fragrance:P", "016": "packaging:N", "018": "fragrance:N authenticity:N value:N",
 "022": "freebies:P value:P arrival:P", "023": "matches_listing:N size:N", "024": "arrival:P packaging:P value:P",
 "026": "value:P delivery:P packaging:P", "027": "value:P gentleness:P texture:P", "038": "seller:P", "039": "value:P ease:P size:P",
 "041": "matches_listing:N build:P", "042": "arrival:N matches_listing:N seller:N", "043": "fabric:N matches_listing:N delivery:N",
 "047": "authenticity:N texture:N", "048": "build:N seller:N", "049": "seller:P delivery:P", "050": "size:P", "053": "size:N",
 "055": "arrival:N", "056": "fabric:P size:P appearance:P", "057": "ease:P value:P", "059": "delivery:N seller:N", "060": "value:P build:P",
 "065": "delivery:P", "067": "fragrance:N", "071": "delivery:P", "073": "arrival:P value:P", "076": "delivery:N seller:N",
 "078": "functionality:P delivery:P", "079": "packaging:P", "082": "packaging:P delivery:P value:P", "083": "softness:P fragrance:P",
 "084": "matches_listing:P build:P seller:P delivery:P value:P", "085": "arrival:P value:P softness:P", "086": "value:P size:P fragrance:P",
 "090": "matches_listing:P freebies:N", "091": "matches_listing:N", "093": "arrival:P delivery:P freebies:P", "094": "freebies:P",
 "096": "matches_listing:N freebies:N", "097": "matches_listing:N", "098": "fabric:P", "099": "packaging:P", "100": "delivery:N",
 "101": "build:P authenticity:P value:P functionality:P softness:P fragrance:P delivery:P", "103": "functionality:P value:P",
 "104": "matches_listing:N",
}
MENU = set("""001 002 003 004 005 007 008 010 011 012 013 015 017 019 020 021 025 027 028 029 030 031 032 033 034 035 036 037 040 044 045 046 049 050 051
054 058 061 062 066 069 070 071 072 073 074 075 077 080 081 083 087 088 089 092 095 098 102""".split())

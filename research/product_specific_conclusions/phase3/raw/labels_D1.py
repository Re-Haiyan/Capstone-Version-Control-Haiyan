# Claude-assisted labels for Phase 3 sheet D1 (blind: no system output, no extractor run on these rows before labelling).
# P = positive, N = negative. Rows not listed = none. MENU = row contains a marketplace suggestion list (ignored) or advertising copy.
L = {
 "001": "value:P build:P taste:P", "004": "matches_listing:N seller:N", "006": "delivery:P taste:P", "007": "comfort:P ease:P",
 "008": "charging:N functionality:N", "009": "value:P authenticity:P packaging:P",
 "010": "ease:P performance:P build:P delivery:P seller:P", "016": "functionality:P", "018": "functionality:P delivery:P",
 "019": "value:P", "020": "fabric:P build:P", "023": "functionality:N performance:N build:N", "024": "value:N",
 "026": "delivery:P seller:P", "027": "size:N appearance:P stitching:N", "030": "build:P functionality:P", "031": "comfort:P value:P",
 "032": "build:P value:P", "033": "skin_irritation:N", "034": "authenticity:N build:N", "035": "functionality:P",
 "036": "durability:P size:P", "038": "arrival:N packaging:N functionality:N value:N seller:N", "040": "matches_listing:P",
 "041": "build:N matches_listing:N seller:N", "043": "size:N durability:P", "044": "build:P appearance:P", "045": "authenticity:N taste:N",
 "046": "appearance:P", "049": "charging:P size:P", "050": "durability:P ease:P appearance:P", "051": "appearance:P delivery:P",
 "053": "packaging:P build:N", "054": "build:P functionality:P", "055": "matches_listing:N", "056": "value:P build:P taste:P",
 "058": "functionality:N value:N delivery:N", "059": "delivery:P arrival:P build:P", "060": "value:P functionality:P size:P",
 "061": "size:P durability:P build:P delivery:P", "065": "durability:N value:N", "066": "functionality:P",
 "070": "build:P size:P appearance:P", "071": "authenticity:N texture:N mixability:N", "072": "freebies:N",
 "073": "ease:N", "074": "functionality:P", "075": "taste:P value:P", "076": "appearance:N", "077": "seller:P",
 "078": "matches_listing:N size:N", "079": "seller:N", "080": "arrival:N matches_listing:N value:N", "081": "authenticity:P functionality:P",
 "082": "functionality:P", "083": "appearance:P", "088": "build:P value:P taste:P mixability:P", "089": "durability:P value:P",
 "090": "fragrance:P ease:P value:P", "091": "ease:N", "093": "durability:P value:P", "095": "delivery:N",
 "096": "authenticity:N matches_listing:N build:N", "099": "authenticity:P", "101": "functionality:P value:P",
 "102": "size:P fabric:P", "103": "functionality:P ease:P", "106": "taste:N build:P value:P", "109": "delivery:P sound:P comfort:P",
 "110": "delivery:P packaging:P", "111": "arrival:P", "112": "build:P functionality:P ease:P", "113": "fabric:P size:P appearance:P",
 "119": "build:P value:P", "120": "sound:N comfort:P battery:N value:N", "121": "functionality:P fragrance:P",
 "122": "value:P authenticity:P functionality:P taste:P", "123": "value:P", "124": "taste:P",
 "125": "matches_listing:N battery:N sound:N value:P", "126": "functionality:P fragrance:P texture:P", "127": "size:N build:P",
 "128": "durability:P", "129": "authenticity:N", "130": "size:P", "131": "matches_listing:N arrival:N", "132": "matches_listing:N",
 "135": "sound:P comfort:P battery:P", "137": "delivery:N", "139": "delivery:N build:N", "140": "functionality:P value:N",
 "142": "authenticity:P functionality:P", "143": "authenticity:P packaging:P", "144": "value:P functionality:P build:P durability:P",
}
MENU = set("""002 003 005 011 012 014 015 017 022 025 028 029 042 047 048 049 063 064 067 069 085 086 087 092 097 098 100 102 104 105 107 108 111
114 115 117 123 124 130 133 134 136 138 141 143""".split())

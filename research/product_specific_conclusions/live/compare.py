import json, sys
a = {r["link"]: r for r in json.load(open(sys.argv[1] + ".json", encoding="utf-8")) if "error" not in r}
b = {r["link"]: r for r in json.load(open(sys.argv[2] + ".json", encoding="utf-8")) if "error" not in r}
common = sorted(set(a) & set(b))
fields = sys.argv[3].split(",")
diff = {f: [l for l in common if a[l].get(f) != b[l].get(f)] for f in fields}
print(f"{len(common)} products compared ({sys.argv[1]} vs {sys.argv[2]})")
for f in fields:
    print(f"  {f}: {len(diff[f])} differ")

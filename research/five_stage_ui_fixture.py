import sys,json
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path[:0]=[str(root/'backend'),str(root/'backend/sentiment-analysis')]
import dashboard_utils as du
p=du.analyze_products([{'name':'Five-stage Bluetooth Speaker Fixture','link':'https://www.lazada.com.ph/products/five-stage-fixture.html','platform':'lazada','comments':[{'content':'Clear sound but sound keeps crackling. I love the design! The cable sparked once.','rating':5},{'content':'Clear sound and excellent quality.','rating':5},{'content':'Not yet tested.','rating':3}]}])[0]
p['badge_view']=du.badge_view(p,aspects=True);p['checked_with_current']=True
Path(sys.argv[1]).write_text(json.dumps({'product':p}))

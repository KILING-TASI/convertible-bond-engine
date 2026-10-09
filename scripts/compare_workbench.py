"""Read-only, explicit local reference comparison; no runtime dependency."""
import argparse, hashlib, importlib.util, json, sys
from pathlib import Path
from cbengine.crosscheck import compare
from cbengine.engine import year_fraction
from cbengine.validation import load
p=argparse.ArgumentParser();p.add_argument('reference',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
sys.path.insert(0,str(a.reference.parent))
m=importlib.util.spec_from_file_location('local_workbench_reference',a.reference);ref=importlib.util.module_from_spec(m);m.loader.exec_module(ref)
spec=load(Path('examples/crosscheck-flat.json'));local=compare(spec)['engine']
rows=[{'year':year_fraction(spec['as_of'],c['date']),'amount':c['gross_payment']} for c in spec['cashflows']]
r=ref.calculate({'currency':'CNY','source':spec['source'],'cashFlows':rows,'fullPrice':local['dirty_price'],'faceValue':100,'stockPrice':1,'conversionPrice':1,'discountYield':spec['rate']})
diffs={'dirty_price':r['bondPresentValue']-local['dirty_price'],'modified_duration':r['modifiedDuration']-local['modified_duration'],'dv01':r['dv01']-local['dv01']}
result={'schema_version':'cb-integration-1.0','engine_version':'0.11.0','reference_sha256':hashlib.sha256(a.reference.read_bytes()).hexdigest(),'reference_scope':'local-installed-script; not GitHub main validation','cashflow_years':rows,'differences':diffs,'status':'matched' if all(abs(v)<1e-8 for v in diffs.values()) else 'mismatch','limitations':['flat gross cashflow only; no clause migration or option validation']}
a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
if result['status']!='matched':sys.exit(3)

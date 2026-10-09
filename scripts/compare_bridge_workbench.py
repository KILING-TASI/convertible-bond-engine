"""Explicit local reference integration check. Reference implementation is not copied."""
import argparse,hashlib,importlib.util,json,subprocess,sys
from pathlib import Path
from cbengine.bridge import calculate
from cbengine.validation import load


def compare_reference(spec,reference):
    engine=calculate(spec)
    sys.path.insert(0,str(reference.parent))
    module_spec=importlib.util.spec_from_file_location('explicit_workbench_reference',reference)
    ref=importlib.util.module_from_spec(module_spec);module_spec.loader.exec_module(ref)
    flows=[{'year':row['years'],'amount':row['gross']} for row in engine['cashflows']]
    flat=len({node[1] for node in spec['discount_curve']})==1
    candidates={
       'yield_gross':(ref.yield_rate([(row['years'],row['gross']) for row in engine['cashflows']],engine['dirty_price']),'reference yield_rate helper'),
       'yield_net':(ref.yield_rate([(row['years'],row['net']) for row in engine['cashflows']],engine['dirty_price']),'reference yield_rate helper with explicit net cashflows')}
    if flat:
        r=ref.calculate({'currency':'CNY','source':spec['source'],'cashFlows':flows,'fullPrice':engine['dirty_price'],
          'faceValue':100,'stockPrice':1,'conversionPrice':1,'discountYield':spec['discount_curve'][0][1]})
        for key,field in [('bond_present_value','bondPresentValue'),('zero_curve_parallel_duration','modifiedDuration'),('convexity_parallel','convexity'),('dv01','dv01')]:
            candidates[key]=(r[field],'reference calculate flat annual discountYield')
        candidates['yield_gross']=(r['yieldScenarios'][0]['yieldPct']/100,'reference calculate yieldPct / 100')
    results={}
    for key,(value,method) in candidates.items():
        difference=value-engine[key]
        results[key]={'status':'matched' if abs(difference)<=1e-8 else 'mismatch','engine':engine[key],
                      'reference':value,'difference':difference,'tolerance':1e-8,'reference_method':method}
    if not flat:
        for key in ['bond_present_value','zero_curve_parallel_duration','convexity_parallel','dv01']:
            results[key]={'status':'not-equivalent','reason':'reference calculate accepts a single discountYield, not the supplied nonflat zero curve'}
    try:commit=subprocess.check_output(['git','-C',str(reference.parent),'rev-parse','HEAD'],text=True,stderr=subprocess.DEVNULL).strip()
    except (OSError,subprocess.CalledProcessError):commit=None
    return {'type':'fixed-cashflow-workbench-comparison','method_version':'bridge-reference-check-1.0',
      'input_sha256':engine['input_sha256'],'engine':engine,'reference_sha256':hashlib.sha256(reference.read_bytes()).hexdigest(),
      'reference_commit':commit,'reference_scope':'explicit local working tree; may include uncommitted changes or pending PR',
      'status':'mismatch' if any(r['status']=='mismatch' for r in results.values()) else 'matched-compatible-fields',
      'flat_curve':flat,'comparisons':results,'not_equivalent':['current clause rights','actual exits','complete YTW','conversion value'],
      'not_provided_by_reference':['discount_weighted_average_time'],
      'limitations':['Reference net yield uses its helper with explicit net cashflows; built-in diagnosis has no explicit tax fields.',
                     'Clean/dirty price is normalized before reference calculation; no reference accrual algorithm is validated.']}


def main():
    p=argparse.ArgumentParser();p.add_argument('reference',type=Path);p.add_argument('--input',type=Path,required=True);p.add_argument('--out-dir',type=Path,required=True);a=p.parse_args()
    try:
        if a.out_dir.exists():raise ValueError('output directory exists; choose a new path')
        spec=load(a.input);result=compare_reference(spec,a.reference)
        a.out_dir.mkdir(parents=True,exist_ok=False)
        for name,obj in [('input.json',spec),('result.json',result)]:
            (a.out_dir/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
        if result['status']=='mismatch':p.exit(3)
    except (ValueError,KeyError,TypeError,OSError) as e:p.exit(2,str(e)+'\n')
if __name__=='__main__':main()
